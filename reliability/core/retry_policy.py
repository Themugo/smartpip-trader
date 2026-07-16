"""
Retry Policy Implementation
===========================

Provides configurable retry logic with various strategies.
"""

import asyncio
import time
import logging
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Any, Optional, List, Tuple, Set
from functools import wraps

logger = logging.getLogger(__name__)
T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry backoff strategies"""
    FIXED = "fixed"                  # Fixed delay between retries
    LINEAR = "linear"                # Linear increase in delay
    EXPONENTIAL = "exponential"      # Exponential backoff
    FIBONACCI = "fibonacci"          # Fibonacci backoff
    JITTER = "jitter"                # Random jitter added to delays
    EXPONENTIAL_JITTER = "exponential_jitter"  # Exponential with jitter


@dataclass
class RetryPolicyConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3                 # Maximum retry attempts
    initial_delay: float = 1.0            # Initial delay in seconds
    max_delay: float = 60.0               # Maximum delay cap
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    retryable_exceptions: Tuple[type, ...] = (Exception,)
    non_retryable_exceptions: Tuple[type, ...] = ()
    exponential_base: float = 2.0          # Base for exponential backoff
    jitter_factor: float = 0.5             # Jitter factor (0-1)
    deterministic: bool = False            # For testing, makes retries predictable


@dataclass
class RetryAttempt:
    """Record of a single retry attempt"""
    attempt_number: int
    start_time: float
    end_time: float
    success: bool
    error: Optional[Exception] = None
    latency_ms: float = 0.0


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted"""
    def __init__(self, message: str, attempts: List[RetryAttempt]):
        super().__init__(message)
        self.attempts = attempts


@dataclass
class RetryStats:
    """Statistics for retry monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_retries: int = 0
    total_errors: int = 0
    mean_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    mean_attempts: float = 0.0
    success_rate: float = 100.0
    last_error: Optional[str] = None
    last_error_type: Optional[str] = None


class RetryPolicy:
    """
    Configurable retry policy with multiple backoff strategies.
    
    Supports:
    - Multiple backoff strategies (fixed, linear, exponential, fibonacci, jitter)
    - Configurable retryable/non-retryable exceptions
    - Statistics tracking and monitoring
    - Async and sync function support
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[RetryPolicyConfig] = None
    ):
        self.name = name
        self.config = config or RetryPolicyConfig()
        self._stats = RetryStats()
        self._call_count = 0
        self._attempt_count = 0
    
    @property
    def stats(self) -> RetryStats:
        """Get current statistics"""
        return self._stats
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number.
        
        Uses the configured strategy to determine wait time.
        """
        delay = self.config.initial_delay
        
        if self.config.strategy == RetryStrategy.FIXED:
            pass  # Delay stays as initial_delay
            
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * attempt
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
            
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            a, b = 1, 1
            for _ in range(attempt - 1):
                a, b = b, a + b
            delay = self.config.initial_delay * a
            
        elif self.config.strategy == RetryStrategy.JITTER:
            # Random jitter without exponential growth
            if not self.config.deterministic:
                jitter = random.uniform(
                    -self.config.jitter_factor * delay,
                    self.config.jitter_factor * delay
                )
            else:
                jitter = 0
            delay += jitter
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            # Full exponential backoff with jitter
            exp_delay = self.config.initial_delay * (
                self.config.exponential_base ** (attempt - 1)
            )
            if not self.config.deterministic:
                # Cap jitter to half the delay
                jitter = random.uniform(
                    -self.config.jitter_factor * exp_delay,
                    self.config.jitter_factor * exp_delay
                )
            else:
                jitter = 0
            delay = exp_delay + jitter
        
        # Cap at max delay
        return min(delay, self.config.max_delay)
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if an exception is retryable"""
        # Check non-retryable first (takes precedence)
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        if isinstance(exception, self.config.retryable_exceptions):
            return True
        
        # Default: retry all exceptions not explicitly excluded
        return True
    
    def _record_attempt(
        self,
        attempt: RetryAttempt,
        is_success: bool
    ) -> None:
        """Update statistics with attempt results"""
        self._call_count += 1
        
        if is_success:
            self._stats.successful_calls += 1
        else:
            self._stats.failed_calls += 1
        
        # Update latency stats
        if attempt.latency_ms > self._stats.max_latency_ms:
            self._stats.max_latency_ms = attempt.latency_ms
        
        alpha = 0.1
        self._stats.mean_latency_ms = (
            alpha * attempt.latency_ms +
            (1 - alpha) * self._stats.mean_latency_ms
        )
        
        # Update success rate
        if self._stats.total_calls > 0:
            self._stats.success_rate = (
                self._stats.successful_calls / self._stats.total_calls * 100
            )
        
        # Update mean attempts
        if self._call_count > 0:
            self._stats.mean_attempts = self._attempt_count / self._call_count
    
    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            on_retry: Optional callback called on each retry with (exception, attempt)
            **kwargs: Keyword arguments
            
        Returns:
            Result of successful function call
            
        Raises:
            RetryExhaustedError: When all retries are exhausted
        """
        attempts: List[RetryAttempt] = []
        last_exception: Optional[Exception] = None
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            start_time = time.time()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                end_time = time.time()
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    start_time=start_time,
                    end_time=end_time,
                    success=True,
                    latency_ms=(end_time - start_time) * 1000
                )
                attempts.append(attempt)
                self._record_attempt(attempt, is_success=True)
                
                return result
                
            except Exception as e:
                end_time = time.time()
                self._stats.total_errors += 1
                self._stats.last_error = str(e)
                self._stats.last_error_type = type(e).__name__
                
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    start_time=start_time,
                    end_time=end_time,
                    success=False,
                    error=e,
                    latency_ms=(end_time - start_time) * 1000
                )
                attempts.append(attempt)
                
                # Check if we should retry
                if attempt_num < self.config.max_attempts and self._is_retryable(e):
                    self._stats.total_retries += 1
                    self._attempt_count += 1
                    
                    delay = self._calculate_delay(attempt_num)
                    logger.warning(
                        f"Retry '{self.name}' attempt {attempt_num} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        try:
                            on_retry(e, attempt_num)
                        except Exception as callback_error:
                            logger.error(f"on_retry callback failed: {callback_error}")
                    
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    # No more retries
                    self._attempt_count += 1
                    self._record_attempt(attempt, is_success=False)
                    raise RetryExhaustedError(
                        f"All {self.config.max_attempts} retry attempts exhausted for '{self.name}'",
                        attempts
                    ) from e
        
        # Should not reach here, but just in case
        raise RetryExhaustedError(
            f"All {self.config.max_attempts} retry attempts exhausted for '{self.name}'",
            attempts
        )
    
    def get_health_report(self) -> dict:
        """Get detailed health report for monitoring"""
        return {
            "name": self.name,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "total_retries": self._stats.total_retries,
                "total_errors": self._stats.total_errors,
                "success_rate": round(self._stats.success_rate, 2),
                "mean_latency_ms": round(self._stats.mean_latency_ms, 2),
                "max_latency_ms": round(self._stats.max_latency_ms, 2),
                "mean_attempts": round(self._stats.mean_attempts, 2),
                "last_error": self._stats.last_error,
                "last_error_type": self._stats.last_error_type,
            },
            "config": {
                "max_attempts": self.config.max_attempts,
                "strategy": self.config.strategy.value,
                "initial_delay": self.config.initial_delay,
                "max_delay": self.config.max_delay,
            }
        }


def with_retry(
    name: Optional[str] = None,
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER,
    retryable_exceptions: Tuple[type, ...] = (Exception,),
    non_retryable_exceptions: Tuple[type, ...] = ()
):
    """
    Decorator for applying retry logic to functions.
    
    Usage:
        @with_retry("my-service", max_attempts=5, strategy=RetryStrategy.EXPONENTIAL)
        async def my_function():
            ...
    """
    config = RetryPolicyConfig(
        max_attempts=max_attempts,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        retry_policy = RetryPolicy(name or func.__name__, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_policy.execute(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(retry_policy.execute(func, *args, **kwargs))
        
        # Attach retry policy for monitoring
        if asyncio.iscoroutinefunction(func):
            async_wrapper.retry_policy = retry_policy
            return async_wrapper
        sync_wrapper.retry_policy = retry_policy
        return sync_wrapper
    
    return decorator
