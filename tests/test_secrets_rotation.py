import unittest
import os
import sys
import tempfile
import json
from datetime import datetime, timezone, timedelta, timedelta
from unittest.mock import patch, mock_open

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.secrets_rotation import SecretsRotation, JWTKeyRotation


class TestSecretsRotation(unittest.TestCase):
    """Test SecretsRotation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for metadata files
        self.temp_dir = tempfile.mkdtemp()
        self.metadata_file = os.path.join(self.temp_dir, "secret_metadata.json")
        
        # Patch the metadata file path
        self.metadata_patcher = patch(
            'utils.secrets_rotation.os.path.exists',
            return_value=False
        )
        self.metadata_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.metadata_patcher.stop()
    
    def test_initialization(self):
        """Test SecretsRotation initializes correctly"""
        rotation = SecretsRotation(rotation_interval_days=30)
        
        self.assertEqual(rotation.rotation_interval, timedelta(days=30))
        self.assertEqual(rotation.secret_metadata, {})
    
    def test_register_secret(self):
        """Test registering a new secret"""
        rotation = SecretsRotation()
        
        rotation.register_secret(
            secret_name="test_api_key",
            secret_type="api_key",
            rotation_interval=30,
            environment="production"
        )
        
        self.assertIn("test_api_key", rotation.secret_metadata)
        metadata = rotation.secret_metadata["test_api_key"]
        self.assertEqual(metadata["type"], "api_key")
        self.assertEqual(metadata["environment"], "production")
        self.assertEqual(metadata["status"], "active")
        self.assertEqual(metadata["version"], 1)
    
    def test_register_secret_custom_interval(self):
        """Test registering secret with custom rotation interval"""
        rotation = SecretsRotation(rotation_interval_days=30)
        
        rotation.register_secret(
            secret_name="custom_interval_key",
            rotation_interval=60
        )
        
        metadata = rotation.secret_metadata["custom_interval_key"]
        self.assertEqual(metadata["rotation_interval_days"], 60)
    
    def test_check_rotation_needed_unregistered(self):
        """Test checking rotation for unregistered secret"""
        rotation = SecretsRotation()
        
        result = rotation.check_rotation_needed("nonexistent_key")
        
        self.assertFalse(result)
    
    def test_check_rotation_needed_not_due(self):
        """Test checking rotation when not due"""
        rotation = SecretsRotation()
        
        rotation.register_secret("new_key", rotation_interval=30)
        
        result = rotation.check_rotation_needed("new_key")
        
        self.assertFalse(result)  # Should not need rotation yet
    
    def test_check_rotation_needed_due(self):
        """Test checking rotation when due"""
        rotation = SecretsRotation()
        
        # Register with past next_rotation
        rotation.secret_metadata["old_key"] = {
            "name": "old_key",
            "type": "api_key",
            "next_rotation": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "rotation_interval_days": 30,
            "status": "active"
        }
        
        result = rotation.check_rotation_needed("old_key")
        
        self.assertTrue(result)
    
    def test_rotate_secret_unregistered(self):
        """Test rotating unregistered secret raises error"""
        rotation = SecretsRotation()
        
        with self.assertRaises(ValueError) as context:
            rotation.rotate_secret("nonexistent")
        
        self.assertIn("not registered", str(context.exception))
    
    def test_rotate_secret_with_generated_value(self):
        """Test rotating secret generates new value"""
        rotation = SecretsRotation()
        rotation.register_secret("api_key", secret_type="api_key")
        
        new_secret = rotation.rotate_secret("api_key")
        
        self.assertIsNotNone(new_secret)
        self.assertIsInstance(new_secret, str)
        self.assertGreater(len(new_secret), 0)
        
        metadata = rotation.secret_metadata["api_key"]
        self.assertEqual(metadata["version"], 2)
        self.assertIn("previous_rotation", metadata)
    
    def test_rotate_secret_with_provided_value(self):
        """Test rotating secret with provided value"""
        rotation = SecretsRotation()
        rotation.register_secret("my_key", secret_type="api_key")
        
        new_secret = rotation.rotate_secret("my_key", new_secret="my_new_secret_value")
        
        self.assertEqual(new_secret, "my_new_secret_value")
    
    def test_rotate_secret_updates_timing(self):
        """Test rotation updates timing metadata"""
        rotation = SecretsRotation()
        rotation.register_secret("timed_key", rotation_interval=30)
        
        original_metadata = rotation.secret_metadata["timed_key"].copy()
        
        rotation.rotate_secret("timed_key")
        
        updated_metadata = rotation.secret_metadata["timed_key"]
        self.assertEqual(updated_metadata["version"], 2)
        self.assertNotEqual(
            updated_metadata["last_rotated"],
            original_metadata["last_rotated"]
        )
    
    def test_revoke_secret_unregistered(self):
        """Test revoking unregistered secret raises error"""
        rotation = SecretsRotation()
        
        with self.assertRaises(ValueError) as context:
            rotation.revoke_secret("nonexistent")
        
        self.assertIn("not registered", str(context.exception))
    
    def test_revoke_secret(self):
        """Test revoking a secret"""
        rotation = SecretsRotation()
        rotation.register_secret("revoke_key")
        
        rotation.revoke_secret("revoke_key")
        
        metadata = rotation.secret_metadata["revoke_key"]
        self.assertEqual(metadata["status"], "revoked")
        self.assertIn("revoked_at", metadata)
    
    def test_get_rotation_status_specific_secret(self):
        """Test getting rotation status for specific secret"""
        rotation = SecretsRotation()
        rotation.register_secret("status_key")
        
        status = rotation.get_rotation_status("status_key")
        
        self.assertIsInstance(status, dict)
        self.assertIn("needs_rotation", status)
        self.assertIn("days_until_rotation", status)
        self.assertIn("name", status)
    
    def test_get_rotation_status_unregistered(self):
        """Test getting status for unregistered secret"""
        rotation = SecretsRotation()
        
        status = rotation.get_rotation_status("nonexistent")
        
        self.assertIn("error", status)
    
    def test_get_rotation_status_all_secrets(self):
        """Test getting rotation status for all secrets"""
        rotation = SecretsRotation()
        rotation.register_secret("key1")
        rotation.register_secret("key2")
        
        status = rotation.get_rotation_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("key1", status)
        self.assertIn("key2", status)
    
    def test_rotate_all_expired(self):
        """Test rotating all expired secrets"""
        rotation = SecretsRotation()
        
        # Register fresh secret (not expired)
        rotation.register_secret("fresh_key")
        
        # Register expired secret
        rotation.secret_metadata["expired_key"] = {
            "name": "expired_key",
            "type": "api_key",
            "next_rotation": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "rotation_interval_days": 30,
            "status": "active",
            "version": 1
        }
        
        rotated = rotation.rotate_all_expired()
        
        self.assertIn("expired_key", rotated)
        self.assertNotIn("fresh_key", rotated)
        self.assertEqual(rotation.secret_metadata["expired_key"]["version"], 2)
    
    def test_rotate_all_expired_none_to_rotate(self):
        """Test rotate_all_expired when nothing needs rotation"""
        rotation = SecretsRotation()
        rotation.register_secret("new_key")
        
        rotated = rotation.rotate_all_expired()
        
        self.assertEqual(len(rotated), 0)
    
    def test_create_environment_scoped_secret(self):
        """Test creating environment-scoped secret"""
        rotation = SecretsRotation()
        
        secret_value = rotation.create_environment_scoped_secret(
            "my_secret",
            "production"
        )
        
        scoped_name = "my_secret_production"
        self.assertIn(scoped_name, rotation.secret_metadata)
        # The secret value is returned but not stored in metadata
        self.assertIsNotNone(secret_value)
        # API key uses secrets.token_urlsafe(32) which produces 43 chars
        self.assertGreater(len(secret_value), 30)
    
    def test_environment_rotation_intervals(self):
        """Test different rotation intervals for environments"""
        rotation = SecretsRotation()
        
        rotation.create_environment_scoped_secret("prod", "production")
        rotation.create_environment_scoped_secret("stag", "staging")
        rotation.create_environment_scoped_secret("dev", "development")
        
        prod_interval = rotation.secret_metadata["prod_production"]["rotation_interval_days"]
        stag_interval = rotation.secret_metadata["stag_staging"]["rotation_interval_days"]
        dev_interval = rotation.secret_metadata["dev_development"]["rotation_interval_days"]
        
        self.assertEqual(prod_interval, 30)
        self.assertEqual(stag_interval, 60)
        self.assertEqual(dev_interval, 90)


class TestGenerateSecret(unittest.TestCase):
    """Test secret generation"""
    
    def test_generate_api_key(self):
        """Test API key generation"""
        rotation = SecretsRotation()
        
        secret = rotation._generate_secret("api_key")
        
        self.assertIsInstance(secret, str)
        self.assertGreater(len(secret), 0)
    
    def test_generate_webhook_secret(self):
        """Test webhook secret generation"""
        rotation = SecretsRotation()
        
        secret = rotation._generate_secret("webhook_secret")
        
        self.assertIsInstance(secret, str)
        # Hex strings have specific length
        self.assertGreater(len(secret), 0)
    
    def test_generate_jwt_key(self):
        """Test JWT key generation"""
        rotation = SecretsRotation()
        
        secret = rotation._generate_secret("jwt_key")
        
        self.assertIsInstance(secret, str)
        self.assertGreater(len(secret), 20)
    
    def test_generate_encryption_key(self):
        """Test encryption key generation"""
        rotation = SecretsRotation()
        
        secret = rotation._generate_secret("encryption_key")
        
        self.assertIsInstance(secret, str)
        self.assertGreater(len(secret), 0)
    
    def test_generate_default_type(self):
        """Test default secret generation"""
        rotation = SecretsRotation()
        
        secret = rotation._generate_secret("unknown_type")
        
        self.assertIsInstance(secret, str)
        self.assertEqual(len(secret), 32)


class TestJWTKeyRotation(unittest.TestCase):
    """Test JWTKeyRotation specialized class"""
    
    def test_initialization(self):
        """Test JWTKeyRotation initializes with correct defaults"""
        rotation = JWTKeyRotation()
        
        # Should use 90-day rotation by default
        self.assertEqual(rotation.rotation_interval, timedelta(days=90))
        self.assertIsNone(rotation.current_key_id)
        self.assertEqual(rotation.previous_keys, {})
    
    def test_rotate_jwt_key(self):
        """Test JWT key rotation"""
        rotation = JWTKeyRotation()
        
        key_id, new_key = rotation.rotate_jwt_key()
        
        self.assertIsNotNone(key_id)
        self.assertIsNotNone(new_key)
        self.assertEqual(rotation.current_key_id, key_id)
        self.assertTrue(key_id.startswith("key_"))
    
    def test_rotate_jwt_key_preserves_previous(self):
        """Test that rotation preserves previous key"""
        rotation = JWTKeyRotation()
        
        # First rotation
        key_id1, key1 = rotation.rotate_jwt_key()
        
        # Second rotation
        key_id2, key2 = rotation.rotate_jwt_key()
        
        # Previous key should be stored
        self.assertIn(key_id1, rotation.previous_keys)
    
    def test_get_valid_keys_current_only(self):
        """Test getting valid keys returns current key"""
        rotation = JWTKeyRotation()
        
        key_id, new_key = rotation.rotate_jwt_key()
        
        # Set environment variable for the key
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            valid_keys = rotation.get_valid_keys()
        
        self.assertIn(key_id, valid_keys)
    
    def test_get_valid_keys_includes_previous_during_transition(self):
        """Test that previous key is included during transition"""
        rotation = JWTKeyRotation()
        
        # First rotation
        key_id1, _ = rotation.rotate_jwt_key()
        
        # Set environment variable
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret"}):
            # Second rotation
            key_id2, _ = rotation.rotate_jwt_key()
            
            valid_keys = rotation.get_valid_keys()
        
        # Both current and previous should be valid
        self.assertIn(key_id1, valid_keys)
        self.assertIn(key_id2, valid_keys)
    
    def test_get_valid_keys_excludes_expired(self):
        """Test that expired previous keys are excluded"""
        rotation = JWTKeyRotation()
        
        # Rotate to set current key
        key_id1, _ = rotation.rotate_jwt_key()
        
        # Manually add a previous key that is expired
        import time
        time.sleep(0.1)  # Ensure different timestamp
        rotation.previous_keys["expired_key"] = {
            "key": "old_secret",
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        }
        
        valid_keys = rotation.get_valid_keys()
        
        # Expired previous key should not be included
        self.assertNotIn("expired_key", valid_keys)
        # Current key should be present
        self.assertIn(key_id1, valid_keys)


if __name__ == "__main__":
    unittest.main()
