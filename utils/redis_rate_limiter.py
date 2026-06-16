import redis
import json
import time
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Redis-backed rate limiter for distributed rate limiting"""
    
    def __init__(self, redis_url: str = None, default_window: int = 60, default_limit: int = 100):
        """
        Initialize Redis rate limiter
        
        Args:
            redis_url: Redis connection URL (default: localhost:6379)
            default_window: Default time window in seconds
            default_limit: Default request limit per window
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_window = default_window
        self.default_limit = default_limit
        
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()
            logger.info("Redis rate limiter connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    def is_allowed(self, key: str, limit: int = None, window: int = None) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Request limit per window (uses default if not provided)
            window: Time window in seconds (uses default if not provided)
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        if not self.redis:
            # Fallback to in-memory if Redis unavailable
            return True, {"error": "Redis unavailable, rate limiting disabled"}
        
        limit = limit or self.default_limit
        window = window or self.default_window
        
        current_time = int(time.time())
        window_start = current_time - window
        
        # Redis key for this rate limit
        redis_key = f"ratelimit:{key}"
        
        try:
            # Remove old entries
            self.redis.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            current_count = self.redis.zcard(redis_key)
            
            # Check if limit exceeded
            if current_count >= limit:
                # Get time until reset
                oldest_request = self.redis.zrange(redis_key, 0, 0, withscores=True)
                reset_time = int(oldest_request[0][1]) + window if oldest_request else current_time + window
                
                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset": reset_time,
                    "current": current_count
                }
            
            # Add current request
            self.redis.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiry
            self.redis.expire(redis_key, window)
            
            # Calculate remaining
            remaining = limit - (current_count + 1)
            
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": remaining,
                "reset": current_time + window,
                "current": current_count + 1
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, {"error": "Rate limit check failed, allowing request"}
    
    def cleanup_old_keys(self, pattern: str = "ratelimit:*"):
        """Clean up old rate limit keys"""
        if not self.redis:
            return
        
        try:
            keys = self.redis.keys(pattern)
            for key in keys:
                ttl = self.redis.ttl(key)
                if ttl == -1:  # No expiry set
                    self.redis.expire(key, 3600)  # Set 1 hour expiry
        except Exception as e:
            logger.error(f"Failed to cleanup old keys: {e}")
    
    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get current rate limit statistics for a key"""
        if not self.redis:
            return {"error": "Redis unavailable"}
        
        try:
            redis_key = f"ratelimit:{key}"
            count = self.redis.zcard(redis_key)
            ttl = self.redis.ttl(redis_key)
            
            return {
                "key": key,
                "current_count": count,
                "ttl": ttl,
                "limit": self.default_limit,
                "window": self.default_window
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


class PerIPRateLimiter(RedisRateLimiter):
    """Rate limiter based on IP address"""
    
    def __init__(self, redis_url: str = None, limit_per_ip: int = 100, window: int = 60):
        super().__init__(redis_url, window, limit_per_ip)
        self.limit_per_ip = limit_per_ip
    
    def check_ip(self, ip_address: str) -> tuple[bool, Dict[str, Any]]:
        """Check if IP is allowed"""
        return self.is_allowed(f"ip:{ip_address}", self.limit_per_ip, self.default_window)


class PerAccountRateLimiter(RedisRateLimiter):
    """Rate limiter based on account/user ID"""
    
    def __init__(self, redis_url: str = None, limit_per_account: int = 50, window: int = 60):
        super().__init__(redis_url, window, limit_per_account)
        self.limit_per_account = limit_per_account
    
    def check_account(self, account_id: str) -> tuple[bool, Dict[str, Any]]:
        """Check if account is allowed"""
        return self.is_allowed(f"account:{account_id}", self.limit_per_account, self.default_window)


class WebSocketRateLimiter(RedisRateLimiter):
    """Rate limiter for WebSocket connections"""
    
    def __init__(self, redis_url: str = None, limit_per_ws: int = 30, window: int = 60):
        super().__init__(redis_url, window, limit_per_ws)
        self.limit_per_ws = limit_per_ws
    
    def check_websocket(self, connection_id: str) -> tuple[bool, Dict[str, Any]]:
        """Check if WebSocket connection is allowed"""
        return self.is_allowed(f"ws:{connection_id}", self.limit_per_ws, self.default_window)


class CircuitBreaker:
    """Circuit breaker for abuse protection"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if circuit is open
        """
        if self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                logger.warning("Circuit breaker is open, blocking request")
                return None
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
        }
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker reset to closed state")
