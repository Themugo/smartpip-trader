import time
import logging
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to prevent API abuse"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for identifier
        
        Args:
            identifier: Unique identifier (e.g., IP, user ID)
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = deque()
        
        # Remove old requests outside the window
        while self.requests[identifier] and self.requests[identifier][0] < now - self.window_seconds:
            self.requests[identifier].popleft()
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        
        logger.warning(f"Rate limit exceeded for {identifier}")
        return False
    
    def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Number of remaining requests
        """
        if identifier not in self.requests:
            return self.max_requests
        
        now = time.time()
        
        # Remove old requests outside the window
        while self.requests[identifier] and self.requests[identifier][0] < now - self.window_seconds:
            self.requests[identifier].popleft()
        
        return self.max_requests - len(self.requests[identifier])
    
    def get_reset_time(self, identifier: str) -> Optional[float]:
        """
        Get time when rate limit will reset
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Unix timestamp of reset time, or None if no requests
        """
        if identifier not in self.requests or not self.requests[identifier]:
            return None
        
        return self.requests[identifier][0] + self.window_seconds
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        if identifier in self.requests:
            del self.requests[identifier]
