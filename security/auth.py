import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from passlib.context import CryptContext
import secrets


class SecurityManager:
    """Security manager for system authentication and authorization"""
    
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.api_keys = set(os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else [])
        self.whitelisted_ips = set(os.getenv("WHITELISTED_IPS", "").split(",") if os.getenv("WHITELISTED_IPS") else [])
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
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
        key = os.getenv("ENCRYPTION_KEY", secrets.token_bytes(32))
        f = Fernet(key)
        return f.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        from cryptography.fernet import Fernet
        key = os.getenv("ENCRYPTION_KEY", secrets.token_bytes(32))
        f = Fernet(key)
        return f.decrypt(encrypted_data.encode()).decode()
