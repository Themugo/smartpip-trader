import re
import html
import hashlib
import hmac
import time
import os
import json
from typing import Any, Dict, Optional, List, Set, Literal
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator, Field
from datetime import datetime, timedelta


# Pydantic schema validation models
class TradeRequest(BaseModel):
    """Schema for trade request validation"""
    market: str = Field(..., description="Market symbol")
    direction: Literal["CALL", "PUT"] = Field(..., description="Trade direction")
    amount: float = Field(..., ge=10, le=10000, description="Trade amount")
    confidence: float = Field(..., ge=0, le=100, description="Confidence percentage")
    duration: int = Field(default=2, ge=1, le=60, description="Trade duration in minutes")
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v):
        valid_markets = {
            "R_10", "R_25", "R_50", "R_75", "R_100",
            "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
            "R_100_25S", "R_100_50S"
        }
        if v not in valid_markets:
            raise ValueError(f"Invalid market: {v}")
        return v
    
    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v):
        return v.upper()


class SettingsUpdate(BaseModel):
    """Schema for settings update validation"""
    base_amount: Optional[float] = Field(None, ge=10, le=10000)
    min_confidence: Optional[float] = Field(None, ge=50, le=100)
    stop_loss: Optional[float] = Field(None, ge=0)
    take_profit: Optional[float] = Field(None, ge=0)
    max_consecutive_losses: Optional[int] = Field(None, ge=1, le=10)
    auto_trading: Optional[bool] = None


class MarketSwitchRequest(BaseModel):
    """Schema for market switch validation"""
    market: str = Field(..., description="Target market")
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v):
        valid_markets = {
            "R_10", "R_25", "R_50", "R_75", "R_100",
            "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
            "R_100_25S", "R_100_50S"
        }
        if v not in valid_markets:
            raise ValueError(f"Invalid market: {v}")
        return v


class WebhookPayload(BaseModel):
    """Schema for webhook payload validation"""
    event_type: str = Field(..., description="Event type")
    timestamp: str = Field(..., description="ISO timestamp")
    data: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = Field(None, description="Payload signature")
    nonce: Optional[str] = Field(None, description="Unique nonce for replay prevention")


class InputSanitizer:
    """Enterprise-grade input sanitization middleware to prevent XSS and injection attacks"""
    
    def __init__(self, secret_key: str = None, testing: bool = False):
        self.secret_key = secret_key or os.getenv("SANITIZATION_SECRET_KEY")
        if not self.secret_key:
            if testing:
                # Use a default key for testing
                self.secret_key = "test-secret-key-for-development"
            else:
                raise ValueError("SANITIZATION_SECRET_KEY environment variable must be set in production")
        
        # Replay attack prevention
        self.used_nonces: Set[str] = set()
        self.nonce_expiry = timedelta(minutes=5)
        
        # Whitelist trading symbols
        self.valid_markets: Set[str] = {
            "R_10", "R_25", "R_50", "R_75", "R_100",
            "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
            "R_100_25S", "R_100_50S"
        }
        
        # XSS patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>',
            r'<form[^>]*>.*?</form>',
            r'<input[^>]*>',
            r'<button[^>]*>.*?</button>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>.*?</style>',
            r'<\?php.*?\?>',
            r'<\?.*\?>',
            r'<%.*?%>',
            r'eval\(',
            r'exec\(',
            r'system\(',
            r'passthru\(',
            r'shell_exec\(',
            r'base64_decode\(',
            r'unserialize\(',
            r'file_get_contents\(',
            r'file_put_contents\(',
            r'fopen\(',
            r'fwrite\(',
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",
            r"(\bOR\b|\bAND\b)\s+'[^']+'\s*=\s*'[^']*'",
            r"(\bOR\b|\bAND\b)\s+\"[^\"]+\"\s*=\s*\"[^\"]*\"",
            r";\s*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER)\s",
            r"UNION\s+SELECT",
            r"--",
            r"#",
            r"/\*.*\*/",
            r"xp_cmdshell",
            r"sp_executesql",
        ]
        
        # Command injection patterns
        self.command_patterns = [
            r';\s*(ls|cat|pwd|whoami|id|uname|rm|mv|cp|chmod|chown)\s',
            r'\|\s*(ls|cat|pwd|whoami|id|uname|rm|mv|cp|chmod|chown)\s',
            r'&\s*(ls|cat|pwd|whoami|id|uname|rm|mv|cp|chmod|chown)\s',
            r'\$\(',
            r'`[^`]*`',
            r'\$\{[^}]*\}',
        ]
    
    def sanitize_string(self, input_string: str) -> str:
        """Sanitize a string input"""
        if not isinstance(input_string, str):
            return input_string
        
        # HTML encode
        sanitized = html.escape(input_string)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Remove control characters except newline and tab
        sanitized = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
        
        return sanitized
    
    def sanitize_number(self, input_value: Any) -> Optional[float]:
        """Sanitize numeric input"""
        try:
            return float(input_value)
        except (ValueError, TypeError):
            return None
    
    def sanitize_boolean(self, input_value: Any) -> bool:
        """Sanitize boolean input"""
        if isinstance(input_value, bool):
            return input_value
        if isinstance(input_value, str):
            return input_value.lower() in ('true', '1', 'yes', 'on')
        return bool(input_value)
    
    def check_xss(self, input_string: str) -> bool:
        """Check for XSS patterns"""
        if not isinstance(input_string, str):
            return False
        
        for pattern in self.xss_patterns:
            if re.search(pattern, input_string, re.IGNORECASE | re.DOTALL):
                return True
        return False
    
    def check_sql_injection(self, input_string: str) -> bool:
        """Check for SQL injection patterns"""
        if not isinstance(input_string, str):
            return False
        
        for pattern in self.sql_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        return False
    
    def check_command_injection(self, input_string: str) -> bool:
        """Check for command injection patterns"""
        if not isinstance(input_string, str):
            return False
        
        for pattern in self.command_patterns:
            if re.search(pattern, input_string, re.IGNORECASE):
                return True
        return False
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary values"""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            safe_key = self.sanitize_string(str(key))
            
            # Sanitize value based on type
            if isinstance(value, str):
                # Check for malicious patterns
                if (self.check_xss(value) or 
                    self.check_sql_injection(value) or 
                    self.check_command_injection(value)):
                    raise ValueError(f"Malicious input detected in field: {safe_key}")
                
                sanitized[safe_key] = self.sanitize_string(value)
            elif isinstance(value, (int, float)):
                sanitized[safe_key] = value
            elif isinstance(value, bool):
                sanitized[safe_key] = value
            elif isinstance(value, dict):
                sanitized[safe_key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[safe_key] = self.sanitize_list(value)
            else:
                sanitized[safe_key] = str(value)
        
        return sanitized
    
    def sanitize_list(self, data: list) -> list:
        """Sanitize list values"""
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                # Check for malicious patterns
                if (self.check_xss(item) or 
                    self.check_sql_injection(item) or 
                    self.check_command_injection(item)):
                    raise ValueError("Malicious input detected in list item")
                
                sanitized.append(self.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format (Kenyan)"""
        if not isinstance(phone, str):
            return False
        
        # Kenyan phone format: 254XXXXXXXXX or +254XXXXXXXXX
        pattern = r'^(\+254|254)[0-9]{9}$'
        return re.match(pattern, phone) is not None
    
    def validate_market(self, market: str) -> bool:
        """Validate market symbol"""
        valid_markets = [
            "R_10", "R_25", "R_50", "R_75", "R_100",
            "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
            "R_100_25S", "R_100_50S"
        ]
        
        return market in valid_markets
    
    def validate_direction(self, direction: str) -> bool:
        """Validate trade direction"""
        return direction.upper() in ["CALL", "PUT"]
    
    def validate_amount(self, amount: float) -> bool:
        """Validate trade amount with strict bounds"""
        return isinstance(amount, (int, float)) and 10 <= amount <= 10000
    
    def validate_payload_signature(self, payload: Dict[str, Any], signature: str, timestamp: str) -> bool:
        """Validate payload signature to prevent tampering"""
        try:
            # Check timestamp freshness (prevent replay attacks)
            payload_time = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - payload_time > timedelta(minutes=5):
                return False
            
            # Create signature
            payload_str = json.dumps(payload, sort_keys=True)
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
    
    def check_replay_attack(self, nonce: str) -> bool:
        """Check for replay attacks using nonce"""
        if nonce in self.used_nonces:
            return True  # Replay attack detected
        
        # Add nonce to used set
        self.used_nonces.add(nonce)
        
        # Clean up old nonces periodically
        if len(self.used_nonces) > 10000:
            self.used_nonces.clear()
        
        return False
    
    def validate_strict_bounds(self, value: float, min_val: float, max_val: float) -> bool:
        """Validate numeric value with strict bounds"""
        try:
            num = float(value)
            return min_val <= num <= max_val
        except (ValueError, TypeError):
            return False


def create_sanitize_middleware(sanitizer: InputSanitizer):
    """Create FastAPI middleware for input sanitization"""
    
    async def middleware(request: Request, call_next):
        # Only sanitize POST, PUT, PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get request body
                body = await request.json()
                
                # Sanitize input
                sanitized_body = sanitizer.sanitize_dict(body)
                
                # Replace request body with sanitized version (encode back to bytes)
                request._body = json.dumps(sanitized_body).encode("utf-8")
                
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Malicious input detected", "detail": str(e)}
                )
            except Exception:
                # If sanitization fails, continue with original body
                pass
        
        response = await call_next(request)
        return response
    
    return middleware
