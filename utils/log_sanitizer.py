import re
import logging
from typing import Any, Dict, Optional

class LogSanitizer:
    """Sanitize sensitive data from logs to prevent information leakage"""
    
    # Patterns to sanitize
    SENSITIVE_PATTERNS = [
        # API tokens
        (r'(api[_-]?token["\']?\s*[:=]\s*["\']?)[\w\-]{20,}', r'\1[REDACTED]'),
        (r'(authorization["\']?\s*[:=]\s*["\']?)[\w\-]{20,}', r'\1[REDACTED]'),
        (r'(bearer["\']?\s*[:=]\s*["\']?)[\w\-]{20,}', r'\1[REDACTED]'),
        
        # Account IDs
        (r'(account[_-]?id["\']?\s*[:=]\s*["\']?)[\w\-]{10,}', r'\1[REDACTED]'),
        (r'(user[_-]?id["\']?\s*[:=]\s*["\']?)[\w\-]{10,}', r'\1[REDACTED]'),
        
        # Email addresses
        (r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]'),
        
        # Phone numbers
        (r'(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', '[PHONE_REDACTED]'),
        
        # Credit card numbers
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]'),
        
        # Passwords
        (r'(password["\']?\s*[:=]\s*["\']?)[^\s\'"]+', r'\1[REDACTED]'),
        (r'(secret["\']?\s*[:=]\s*["\']?)[^\s\'"]+', r'\1[REDACTED]'),
        (r'(key["\']?\s*[:=]\s*["\']?)[^\s\'"]{10,}', r'\1[REDACTED]'),
        
        # Trade IDs
        (r'(trade[_-]?id["\']?\s*[:=]\s*["\']?)[\w\-]{15,}', r'\1[REDACTED]'),
        (r'(contract[_-]?id["\']?\s*[:=]\s*["\']?)[\w\-]{15,}', r'\1[REDACTED]'),
        
        # Balance amounts (optional - uncomment if needed)
        # (r'(balance["\']?\s*[:=]\s*["\']?)\d+\.?\d*', r'\1[REDACTED]'),
        # (r'(profit["\']?\s*[:=]\s*["\']?)\d+\.?\d*', r'\1[REDACTED]'),
        
        # WebSocket tokens
        (r'(ws[_-]?token["\']?\s*[:=]\s*["\']?)[\w\-]{20,}', r'\1[REDACTED]'),
        
        # Session tokens
        (r'(session[_-]?id["\']?\s*[:=]\s*["\']?)[\w\-]{20,}', r'\1[REDACTED]'),
    ]
    
    @classmethod
    def sanitize(cls, message: str) -> str:
        """Sanitize a log message by removing sensitive data"""
        if not isinstance(message, str):
            return str(message)
        
        sanitized = message
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize dictionary values for logging"""
        sanitized = {}
        sensitive_keys = ['token', 'password', 'secret', 'key', 'authorization', 'api_key', 'account_id', 'user_id']
        
        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            else:
                sanitized[key] = value
        
        return sanitized


class SanitizedLogger(logging.Logger):
    """Custom logger that automatically sanitizes sensitive data"""
    
    def __init__(self, name: str, level=logging.NOTSET):
        super().__init__(name, level)
    
    def _log(self, level, msg, args, **kwargs):
        """Override _log to sanitize message before logging"""
        # Sanitize the message
        sanitized_msg = LogSanitizer.sanitize(str(msg))
        
        # Sanitize args if they're dictionaries
        sanitized_args = []
        for arg in args:
            if isinstance(arg, dict):
                sanitized_args.append(LogSanitizer.sanitize_dict(arg))
            else:
                sanitized_args.append(arg)
        
        # Call parent _log with sanitized data
        super()._log(level, sanitized_msg, tuple(sanitized_args), **kwargs)


def get_sanitized_logger(name: str) -> logging.Logger:
    """Get a sanitized logger instance"""
    logger = SanitizedLogger(name)
    return logger
