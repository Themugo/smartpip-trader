import os
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import secrets


class SecurityManager:
    """Security manager for system authentication and authorization"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
        if not self.secret_key:
            if os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}:
                raise ValueError("JWT_SECRET_KEY or SECRET_KEY must be set in production")
            self.secret_key = "dev-secret-key-not-for-production"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.api_keys = set(os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else [])
        self.whitelisted_ips = set(os.getenv("WHITELISTED_IPS", "").split(",") if os.getenv("WHITELISTED_IPS") else [])
        self.revoked_tokens: set = set()
        self._revoked_before = 0.0
    
    def _password_hash(self, password: str, salt: bytes) -> str:
        import hashlib
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000).hex()

    def hash_password(self, password: str) -> str:
        """Hash password with PBKDF2-HMAC-SHA256."""
        salt = secrets.token_bytes(16)
        return f"pbkdf2_sha256$310000${salt.hex()}${self._password_hash(password, salt)}"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify PBKDF2 password hash; retain compatibility with legacy bcrypt via a guarded fallback."""
        try:
            scheme, iterations, salt_hex, expected = hashed_password.split("$", 3)
            if scheme != "pbkdf2_sha256":
                raise ValueError("unsupported password hash")
            actual = self._password_hash(plain_password, bytes.fromhex(salt_hex))
            import hmac
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            try:
                from bcrypt import checkpw
                return checkpw(plain_password.encode(), hashed_password.encode())
            except Exception:
                return False

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "iat": now, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token (checks revocation)"""
        if token in self.revoked_tokens:
            return None
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            issued_at = float(payload.get("iat", 0.0))
            if issued_at <= self._revoked_before:
                return None
            return payload
        except jwt.PyJWTError:
            return None
    
    def revoke_token(self, token: str):
        """Revoke a JWT token"""
        self.revoked_tokens.add(token)
    
    def revoke_all_tokens(self):
        """Invalidate all currently issued tokens (e.g. after a credential change)."""
        self.revoked_tokens.clear()
        self._revoked_before = datetime.now(timezone.utc).timestamp()
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        return api_key in self.api_keys
    
    def is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        if not self.whitelisted_ips:
            return True  # Allow all if no whitelist configured
        return ip in self.whitelisted_ips
    
    def generate_api_key(self) -> str:
        """Generate new API key"""
        return secrets.token_urlsafe(32)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable must be set in production")
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable must be set in production")
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(encrypted_data.encode()).decode()
