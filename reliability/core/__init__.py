"""
Circuit Breaker Implementation
=============================

Prevents cascading failures by stopping requests to failing services.
"""

import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, Any, Dict
from collections import deque
from functools import wraps

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is tripped, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening circuit
    success_threshold: int = 3           # Successes in half-open before closing
    timeout: float = 30.0               # Seconds before trying half-open
    half_open_max_calls: int = 3         # Max calls in half-open state
    excluded_exceptions: tuple = ()      # Exceptions that don't count as failures
    window_size: int = 60               # Sliding window for failure counting (seconds)
    volume_threshold: int = 10           # Minimum calls before counting failures


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    mean_latency: float = 0.0
    error_rate: float = 0.0
    availability: float = 100.0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by tracking service health and blocking
    requests when failure thresholds are exceeded.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        callback: Optional[Callable[[], None]] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = callback
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        self._failure_timestamps: deque = deque()
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition"""
        if self._state == CircuitState.OPEN:
            if self._opened_at and \
               time.time() - self._opened_at >= self.config.timeout:
                return CircuitState.HALF_OPEN
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get current statistics"""
        return self._stats
    
    def _record_failure(self) -> None:
        """Record a failed call"""
        self._stats.failed_calls += 1
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = time.time()
        
        # Add to sliding window
        current_time = time.time()
        self._failure_timestamps.append(current_time)
        
        # Remove old timestamps outside window
        while self._failure_timestamps and \
              current_time - self._failure_timestamps[0] > self.config.window_size:
            self._failure_timestamps.popleft()
        
        # Update state if needed
        if self._state == CircuitState.HALF_OPEN:
            self._set_state(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if len(self._failure_timestamps) >= self.config.failure_threshold:
                if self._stats.total_calls >= self.config.volume_threshold:
                    self._set_state(CircuitState.OPEN)
    
    def _record_success(self) -> None:
        """Record a successful call"""
        self._stats.successful_calls += 1
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._set_state(CircuitState.CLOSED)
    
    def _set_state(self, new_state: CircuitState) -> None:
        """Change circuit state with logging and callback"""
        if self._state == new_state:
            return
            
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1
        self._stats.last_state_change = time.time()
        
        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self._failure_count = 0
        elif new_state == CircuitState.CLOSED:
            self._success_count = 0
            self._failure_timestamps.clear()
            self._stats.consecutive_failures = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
            
        logger.warning(
            f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}"
        )
        
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"Circuit breaker callback failed: {e}")
    
    def _update_stats(self, latency: float) -> None:
        """Update latency and availability statistics"""
        # Update mean latency (exponential moving average)
        alpha = 0.1
        self._stats.mean_latency = (
            alpha * latency + (1 - alpha) * self._stats.mean_latency
        )
        
        # Update error rate
        if self._stats.total_calls > 0:
            self._stats.error_rate = (
                self._stats.failed_calls / self._stats.total_calls * 100
            )
        
        # Update availability
        if self._stats.last_state_change:
            # Calculate availability since last state change
            time_since_change = time.time() - self._stats.last_state_change
            if time_since_change > 0:
                # Simplified availability calculation
                self._stats.availability = max(0, 100 - self._stats.error_rate)
    
    async def call(
        self,
        func: Callable[..., Any],
        *args,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: The function to execute
            *args: Positional arguments for func
            fallback: Optional fallback function when circuit is open
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func or fallback
            
        Raises:
            Exception: If circuit is open and no fallback provided
        """
        current_state = self.state
        
        # Check if call is allowed
        if current_state == CircuitState.OPEN:
            self._stats.rejected_calls += 1
            if fallback:
                logger.info(f"Circuit breaker '{self.name}' open, using fallback")
                return fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit breaker '{self.name}' is open")
        
        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._stats.rejected_calls += 1
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitOpenError(
                    f"Circuit breaker '{self.name}' half-open limit reached"
                )
            self._half_open_calls += 1
        
        # Execute the call
        self._stats.total_calls += 1
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            latency = time.time() - start_time
            self._record_success()
            self._update_stats(latency)
            return result
            
        except self.config.excluded_exceptions:
            # Excluded exceptions don't affect circuit
            latency = time.time() - start_time
            self._update_stats(latency)
            raise
            
        except Exception as e:
            latency = time.time() - start_time
            self._record_failure()
            self._update_stats(latency)
            raise
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report for monitoring"""
        return {
            "name": self.name,
            "state": self.state.value,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "error_rate": round(self._stats.error_rate, 2),
                "availability": round(self._stats.availability, 2),
                "mean_latency_ms": round(self._stats.mean_latency * 1000, 2),
                "consecutive_failures": self._stats.consecutive_failures,
                "state_changes": self._stats.state_changes,
            },
            "timestamps": {
                "last_failure": self._stats.last_failure_time,
                "last_success": self._stats.last_success_time,
                "last_state_change": self._stats.last_state_change,
                "opened_at": self._opened_at,
            }
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable[..., Any]] = None
):
    """
    Decorator for applying circuit breaker to functions.
    
    Usage:
        @circuit_breaker("my-service", config=CircuitBreakerConfig(failure_threshold=3))
        async def my_function():
            ...
    """
    breaker = CircuitBreaker(name, config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, fallback=fallback, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, fallback=fallback, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Also export the config classes
from .retry_policy import RetryPolicy, RetryStrategy, RetryExhaustedError
from .retry_policy import RetryPolicyConfig
from .dead_letter_queue import DeadLetterQueue, MessageStatus, FailureReason
from .rate_limiter import RateLimiter, ResourceQuotaManager, QuotaExceededAction, RateLimitConfig
from .failover import FailoverManager, FailoverStrategy
from .graceful_shutdown import GracefulShutdownHandler
