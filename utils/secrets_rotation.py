import os
import json
import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SecretsRotation:
    """Secrets rotation and key lifecycle management"""
    
    def __init__(self, rotation_interval_days: int = 30):
        """
        Initialize secrets rotation manager
        
        Args:
            rotation_interval_days: Default rotation interval in days
        """
        self.rotation_interval = timedelta(days=rotation_interval_days)
        self.secret_metadata: Dict[str, Dict[str, Any]] = {}
        self._load_secret_metadata()
    
    def _load_secret_metadata(self):
        """Load secret metadata from file"""
        metadata_file = "internal-docs/secret_metadata.json"
        try:
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    self.secret_metadata = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load secret metadata: {e}")
            self.secret_metadata = {}
    
    def _save_secret_metadata(self):
        """Save secret metadata to file"""
        metadata_file = "internal-docs/secret_metadata.json"
        try:
            os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
            with open(metadata_file, 'w') as f:
                json.dump(self.secret_metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save secret metadata: {e}")
    
    def register_secret(self, secret_name: str, secret_type: str = "api_key", 
                      rotation_interval: int = None, environment: str = "production"):
        """
        Register a secret for rotation tracking
        
        Args:
            secret_name: Name of the secret
            secret_type: Type of secret (api_key, webhook_secret, jwt_key, etc.)
            rotation_interval: Custom rotation interval in days
            environment: Environment (production, staging, development)
        """
        interval = timedelta(days=rotation_interval) if rotation_interval else self.rotation_interval
        
        self.secret_metadata[secret_name] = {
            "name": secret_name,
            "type": secret_type,
            "environment": environment,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_rotated": datetime.now(timezone.utc).isoformat(),
            "next_rotation": (datetime.now(timezone.utc) + interval).isoformat(),
            "rotation_interval_days": rotation_interval or 30,
            "status": "active",
            "version": 1
        }
        
        self._save_secret_metadata()
        logger.info(f"Registered secret: {secret_name}")
    
    def check_rotation_needed(self, secret_name: str) -> bool:
        """
        Check if a secret needs rotation
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            True if rotation is needed, False otherwise
        """
        if secret_name not in self.secret_metadata:
            logger.warning(f"Secret not registered: {secret_name}")
            return False
        
        metadata = self.secret_metadata[secret_name]
        next_rotation = datetime.fromisoformat(metadata["next_rotation"])
        
        return datetime.now(timezone.utc) >= next_rotation
    
    def rotate_secret(self, secret_name: str, new_secret: str = None) -> str:
        """
        Rotate a secret
        
        Args:
            secret_name: Name of the secret
            new_secret: New secret value (if None, generates one)
            
        Returns:
            New secret value
        """
        if secret_name not in self.secret_metadata:
            raise ValueError(f"Secret not registered: {secret_name}")
        
        metadata = self.secret_metadata[secret_name]
        
        # Generate new secret if not provided
        if new_secret is None:
            new_secret = self._generate_secret(metadata["type"])
        
        # Update metadata
        interval = timedelta(days=metadata["rotation_interval_days"])
        metadata["last_rotated"] = datetime.now(timezone.utc).isoformat()
        metadata["next_rotation"] = (datetime.now(timezone.utc) + interval).isoformat()
        metadata["version"] += 1
        metadata["previous_rotation"] = metadata.get("last_rotated")
        
        self._save_secret_metadata()
        
        logger.info(f"Rotated secret: {secret_name} (version {metadata['version']})")
        
        return new_secret
    
    def _generate_secret(self, secret_type: str) -> str:
        """Generate a new secret based on type"""
        import secrets
        import string
        
        if secret_type == "api_key":
            return secrets.token_urlsafe(32)
        elif secret_type == "webhook_secret":
            return secrets.token_hex(32)
        elif secret_type == "jwt_key":
            return secrets.token_urlsafe(64)
        elif secret_type == "encryption_key":
            return secrets.token_hex(32)
        else:
            # Default: 32-character alphanumeric
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def revoke_secret(self, secret_name: str):
        """
        Revoke a secret
        
        Args:
            secret_name: Name of the secret
        """
        if secret_name not in self.secret_metadata:
            raise ValueError(f"Secret not registered: {secret_name}")
        
        self.secret_metadata[secret_name]["status"] = "revoked"
        self.secret_metadata[secret_name]["revoked_at"] = datetime.now(timezone.utc).isoformat()
        
        self._save_secret_metadata()
        logger.info(f"Revoked secret: {secret_name}")
    
    def get_rotation_status(self, secret_name: str = None) -> Dict[str, Any]:
        """
        Get rotation status for a secret or all secrets
        
        Args:
            secret_name: Name of the secret (if None, returns all)
            
        Returns:
            Rotation status dictionary
        """
        if secret_name:
            if secret_name not in self.secret_metadata:
                return {"error": "Secret not registered"}
            
            metadata = self.secret_metadata[secret_name]
            needs_rotation = self.check_rotation_needed(secret_name)
            
            return {
                **metadata,
                "needs_rotation": needs_rotation,
                "days_until_rotation": (datetime.fromisoformat(metadata["next_rotation"]) - datetime.now(timezone.utc)).days
            }
        else:
            return {
                secret_name: {
                    **metadata,
                    "needs_rotation": self.check_rotation_needed(secret_name),
                    "days_until_rotation": (datetime.fromisoformat(metadata["next_rotation"]) - datetime.now(timezone.utc)).days
                }
                for secret_name, metadata in self.secret_metadata.items()
            }
    
    def rotate_all_expired(self) -> Dict[str, str]:
        """
        Rotate all secrets that need rotation
        
        Returns:
            Dictionary of secret_name -> new_secret
        """
        rotated = {}
        
        for secret_name in list(self.secret_metadata.keys()):
            if self.check_rotation_needed(secret_name):
                try:
                    new_secret = self.rotate_secret(secret_name)
                    rotated[secret_name] = new_secret
                except Exception as e:
                    logger.error(f"Failed to rotate secret {secret_name}: {e}")
        
        return rotated
    
    def create_environment_scoped_secret(self, secret_name: str, environment: str, 
                                       secret_value: str = None) -> str:
        """
        Create an environment-scoped secret
        
        Args:
            secret_name: Base name of the secret
            environment: Environment (production, staging, development)
            secret_value: Secret value (if None, generates one)
            
        Returns:
            Secret value
        """
        scoped_name = f"{secret_name}_{environment}"
        
        # Different rotation intervals for different environments
        rotation_intervals = {
            "production": 30,
            "staging": 60,
            "development": 90
        }
        
        interval = rotation_intervals.get(environment, 30)
        
        self.register_secret(scoped_name, rotation_interval=interval, environment=environment)
        
        if secret_value is None:
            secret_value = self._generate_secret("api_key")
        
        return secret_value


class JWTKeyRotation(SecretsRotation):
    """Specialized JWT key rotation with key rotation support"""
    
    def __init__(self):
        super().__init__(rotation_interval_days=90)
        self.current_key_id = None
        self.previous_keys = {}
    
    def rotate_jwt_key(self) -> tuple[str, str]:
        """
        Rotate JWT signing key
        
        Returns:
            Tuple of (key_id, new_key)
        """
        key_id = f"key_{int(time.time())}"
        new_key = self._generate_secret("jwt_key")
        
        # Store previous key for validation during transition period
        if self.current_key_id:
            self.previous_keys[self.current_key_id] = {
                "key": os.getenv("JWT_SECRET_KEY"),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            }
        
        self.current_key_id = key_id
        
        # Register the new key
        self.register_secret(f"jwt_key_{key_id}", secret_type="jwt_key", rotation_interval=90)
        
        logger.info(f"Rotated JWT key: {key_id}")
        
        return key_id, new_key
    
    def get_valid_keys(self) -> Dict[str, str]:
        """
        Get all valid JWT keys (current + previous for transition)
        
        Returns:
            Dictionary of key_id -> key
        """
        valid_keys = {}
        
        # Add current key
        if self.current_key_id:
            valid_keys[self.current_key_id] = os.getenv("JWT_SECRET_KEY")
        
        # Add previous keys that haven't expired
        current_time = datetime.now(timezone.utc)
        for key_id, key_data in self.previous_keys.items():
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if current_time < expires_at:
                valid_keys[key_id] = key_data["key"]
        
        return valid_keys
