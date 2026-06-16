import os
import secrets
from cryptography.fernet import Fernet
from typing import Optional


class EncryptionManager:
    """Encryption manager for sensitive data"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable must be set in production")
        return key.encode()
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        encrypted = self.fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt dictionary values"""
        encrypted = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted[key] = self.encrypt(value)
            else:
                encrypted[key] = value
        return encrypted
    
    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """Decrypt dictionary values"""
        decrypted = {}
        for key, value in encrypted_data.items():
            if isinstance(value, str):
                try:
                    decrypted[key] = self.decrypt(value)
                except Exception:
                    decrypted[key] = value
            else:
                decrypted[key] = value
        return decrypted
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
