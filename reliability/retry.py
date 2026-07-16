"""
Retry Management
==============

Automatic retry with exponential backoff.
"""

import time
import random
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Retry backoff strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    multiplier: float = 2.0
    jitter: bool = True
    
    # Retry conditions
    retryable_errors: Set[str] = field(default_factory=lambda: {
        "timeout", "connection_error", "rate_limit"
    })
    non_retryable_errors: Set[str] = field(default_factory=lambda: {
        "validation_error", "authentication_error", "not_found"
    })


@dataclass
class RetryAttempt:
    """Record of a retry attempt"""
    attempt: int
    start_time: float
    end_time: float
    success: bool
    error: Optional[str] = None
    error_message: str = ""


class RetryManager:
    """
    Manages automatic retries with configurable backoff.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempts: List[RetryAttempt] = []
        self._total_retries = 0
        self._total_failures = 0
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with automatic retries.
        """
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self._attempts.append(RetryAttempt(
                attempt=attempt,
                start_time=time.time(),
                end_time=0,
                success=False,
            ))
            
            try:
                result = func(*args, **kwargs)
                self._attempts[-1].end_time = time.time()
                self._attempts[-1].success = True
                return result
                
            except Exception as e:
                self._attempts[-1].end_time = time.time()
                self._attempts[-1].error = type(e).__name__
                self._attempts[-1].error_message = str(e)
                
                last_error = e
                self._total_retries += 1
                
                # Check if we should retry
                if not self._should_retry(e):
                    self._total_failures += 1
                    raise
                
                # Check if we have more attempts
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry {attempt}/{self.config.max_attempts} "
                        f"after {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
        
        self._total_failures += 1
        raise last_error
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should be retried"""
        error_type = type(error).__name__.lower()
        
        # Check non-retryable
        for pattern in self.config.non_retryable_errors:
            if pattern in error_type:
                return False
        
        # Check retryable
        for pattern in self.config.retryable_errors:
            if pattern in error_type:
                return True
        
        # Default: retry
        return True
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt"""
        if self.config.backoff == BackoffStrategy.FIXED:
            delay = self.config.initial_delay_seconds
        elif self.config.backoff == BackoffStrategy.LINEAR:
            delay = self.config.initial_delay_seconds * attempt
        elif self.config.backoff == BackoffStrategy.EXPONENTIAL:
            delay = self.config.initial_delay_seconds * (self.config.multiplier ** (attempt - 1))
        elif self.config.backoff == BackoffStrategy.FIBONACCI:
            # Fibonacci sequence
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            delay = self.config.initial_delay_seconds * a
        else:
            delay = self.config.initial_delay_seconds
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay_seconds)
        
        # Add jitter
        if self.config.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay
    
    def get_attempts(self) -> List[RetryAttempt]:
        """Get all retry attempts"""
        return self._attempts.copy()
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        total = self._total_retries + self._total_failures
        return {
            "total_calls": total + sum(1 for a in self._attempts if a.success),
            "total_retries": self._total_retries,
            "total_failures": self._total_failures,
            "retry_rate": self._total_retries / total if total > 0 else 0,
        }
    
    def reset(self) -> None:
        """Reset statistics"""
        self._attempts.clear()
        self._total_retries = 0
        self._total_failures = 0
