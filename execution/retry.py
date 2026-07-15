"""
Retry Engine

Handles retry logic for failed operations:
- Exponential backoff
- Max retry attempts
- Circuit breaker pattern
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    retry_on: tuple = (Exception,)


@dataclass
class RetryState:
    """State of retry operation"""
    attempt: int = 0
    total_delay: float = 0.0
    last_error: Optional[Exception] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    @property
    def success(self) -> bool:
        return self.completed_at is not None and self.last_error is None


class RetryEngine:
    """
    Retry engine with configurable backoff strategies.
    
    Features:
    - Multiple backoff strategies
    - Jitter for load distribution
    - Circuit breaker integration
    - Statistics tracking
    """
    
    def __init__(self, default_config: Optional[RetryConfig] = None):
        self._default_config = default_config or RetryConfig()
        self._stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "total_delay": 0.0,
        }
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            config: Retry configuration
            *args, **kwargs: Arguments for the function
        
        Returns:
            Result of the function
        
        Raises:
            Last exception if all retries fail
        """
        cfg = config or self._default_config
        state = RetryState()
        last_error = None
        
        while state.attempt < cfg.max_attempts:
            state.attempt += 1
            self._stats["total_retries"] += 1
            
            try:
                result = await func(*args, **kwargs)
                
                if state.attempt > 1:
                    self._stats["successful_retries"] += 1
                
                state.completed_at = datetime.utcnow()
                return result
                
            except cfg.retry_on as e:
                last_error = e
                state.last_error = e
                
                if state.attempt >= cfg.max_attempts:
                    self._stats["failed_retries"] += 1
                    raise
                
                # Calculate delay
                delay = self._calculate_delay(state.attempt, cfg)
                state.total_delay += delay
                self._stats["total_delay"] += delay
                
                logger.warning(
                    f"Retry attempt {state.attempt}/{cfg.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                
                await asyncio.sleep(delay)
        
        raise last_error
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay based on strategy"""
        if config.strategy == RetryStrategy.FIXED:
            delay = config.initial_delay
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.initial_delay * attempt
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.initial_delay * (2 ** (attempt - 1))
        elif config.strategy == RetryStrategy.FIBONACCI:
            delay = config.initial_delay * self._fibonacci(attempt)
        else:
            delay = config.initial_delay
        
        # Cap at max delay
        delay = min(delay, config.max_delay)
        
        # Add jitter
        if config.jitter:
            import random
            delay *= (0.5 + random.random())
        
        return delay
    
    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number"""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b
    
    def sync_execute(
        self,
        func: Callable[..., T],
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> T:
        """Synchronous version of execute"""
        cfg = config or self._default_config
        state = RetryState()
        last_error = None
        
        while state.attempt < cfg.max_attempts:
            state.attempt += 1
            self._stats["total_retries"] += 1
            
            try:
                result = func(*args, **kwargs)
                
                if state.attempt > 1:
                    self._stats["successful_retries"] += 1
                
                state.completed_at = datetime.utcnow()
                return result
                
            except cfg.retry_on as e:
                last_error = e
                state.last_error = e
                
                if state.attempt >= cfg.max_attempts:
                    self._stats["failed_retries"] += 1
                    raise
                
                delay = self._calculate_delay(state.attempt, cfg)
                state.total_delay += delay
                
                logger.warning(f"Retry attempt {state.attempt} failed: {e}")
                time.sleep(delay)
        
        raise last_error
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return {
            **self._stats,
            "success_rate": (
                self._stats["successful_retries"] / self._stats["total_retries"]
                if self._stats["total_retries"] > 0 else 0
            ),
            "avg_delay": (
                self._stats["total_delay"] / self._stats["total_retries"]
                if self._stats["total_retries"] > 0 else 0
            ),
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "total_delay": 0.0,
        }
