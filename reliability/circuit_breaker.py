"""
Circuit Breaker
===============

Implements the circuit breaker pattern for fault tolerance.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import threading
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    
    # Monitoring
    window_seconds: float = 60.0
    slow_call_threshold: float = 2.0


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change = time.time()
        
        # Counters
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Callbacks
        self._on_open = on_open
        self._on_close = on_close
        
        # Slow call tracking
        self._slow_calls = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current state"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout_seconds:
                        self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Raises CircuitBreakerError if circuit is open.
        """
        self._total_calls += 1
        
        # Check state
        if self.state == CircuitState.OPEN:
            self._total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN"
            )
        
        # Execute
        try:
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            
            # Check for slow call
            if elapsed > self.config.slow_call_threshold:
                self._slow_calls += 1
            
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        with self._lock:
            self._total_successes += 1
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state"""
        if self._state == new_state:
            return
        
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        
        logger.warning(
            f"Circuit breaker '{self.name}' state change: "
            f"{old_state.value} -> {new_state.value}"
        )
        
        # Execute callbacks
        if new_state == CircuitState.OPEN and self._on_open:
            self._on_open()
        elif new_state == CircuitState.CLOSED and self._on_close:
            self._on_close()
        
        # Reset counters
        if new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._slow_calls = 0
    
    def reset(self) -> None:
        """Manually reset the circuit breaker"""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "total_rejected": self._total_rejected,
                "failure_rate": (
                    self._total_failures / self._total_calls
                    if self._total_calls > 0 else 0
                ),
                "slow_calls": self._slow_calls,
                "last_state_change": self._last_state_change,
            }
    
    def is_available(self) -> bool:
        """Check if circuit breaker allows requests"""
        return self.state != CircuitState.OPEN


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
    
    def register(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Register a circuit breaker"""
        with self._lock:
            if name in self._breakers:
                return self._breakers[name]
            
            breaker = CircuitBreaker(name, config)
            self._breakers[name] = breaker
            return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker"""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all circuit breakers"""
        return [cb.get_stats() for cb in self._breakers.values()]
    
    def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
