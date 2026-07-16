"""
Tests for Reliability Engineering
================================
"""

import pytest
import time


class TestCircuitBreaker:
    """Tests for circuit breaker"""
    
    def test_initial_state(self):
        """Test circuit breaker initial state"""
        from reliability.circuit_breaker import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker("test")
        
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available() is True
    
    def test_successful_call(self):
        """Test successful call through circuit breaker"""
        from reliability.circuit_breaker import CircuitBreaker
        
        cb = CircuitBreaker("test")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        
        assert result == "success"
        stats = cb.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_successes"] == 1
    
    def test_failure_opens_circuit(self):
        """Test that failures open the circuit"""
        from reliability.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config=config)
        
        def fail_func():
            raise ValueError("fail")
        
        # Trigger failures
        for _ in range(2):
            try:
                cb.call(fail_func)
            except ValueError:
                pass
        
        assert cb.state == CircuitState.OPEN
    
    def test_rejected_when_open(self):
        """Test requests are rejected when open"""
        from reliability.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)
        
        def fail_func():
            raise ValueError("fail")
        
        # Open the circuit
        try:
            cb.call(fail_func)
        except ValueError:
            pass
        
        # Should be rejected now
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not run")


class TestRetryManager:
    """Tests for retry manager"""
    
    def test_successful_retry(self):
        """Test successful execution"""
        from reliability.retry import RetryManager
        
        manager = RetryManager()
        
        result = manager.execute(lambda: "success")
        
        assert result == "success"
    
    def test_retry_on_failure(self):
        """Test retry on transient failure"""
        from reliability.retry import RetryManager, RetryConfig
        
        config = RetryConfig(max_attempts=3)
        manager = RetryManager(config)
        
        attempts = []
        
        def flaky_func():
            attempts.append(len(attempts))
            if len(attempts) < 2:
                raise TimeoutError("temporary")
            return "success"
        
        result = manager.execute(flaky_func)
        
        assert result == "success"
        assert len(attempts) == 2
    
    def test_stats(self):
        """Test retry statistics"""
        from reliability.retry import RetryManager
        
        manager = RetryManager()
        manager.execute(lambda: "success")
        
        stats = manager.get_stats()
        assert stats["total_calls"] == 1


class TestHealthMonitor:
    """Tests for health monitoring"""
    
    def test_register_check(self):
        """Test registering a health check"""
        from reliability.health import HealthMonitor
        
        monitor = HealthMonitor()
        
        monitor.register_check(
            name="test_check",
            component="test_component",
            check_fn=lambda: True,
        )
        
        result = monitor.check()
        
        assert result["status"] == "healthy"
    
    def test_failed_check(self):
        """Test failed health check"""
        from reliability.health import HealthMonitor
        
        monitor = HealthMonitor()
        
        monitor.register_check(
            name="failing_check",
            component="test_component",
            check_fn=lambda: False,
            critical=True,
        )
        
        result = monitor.check()
        
        assert result["status"] == "unhealthy"


class TestRecoveryManager:
    """Tests for recovery management"""
    
    def test_register_policy(self):
        """Test registering a recovery policy"""
        from reliability.recovery import RecoveryManager, RecoveryPolicy, RecoveryAction
        
        manager = RecoveryManager()
        
        policy = RecoveryPolicy(
            name="test_policy",
            condition="failure_count > 5",
            action=RecoveryAction.RESTART,
        )
        
        manager.add_policy(policy)
        
        assert "test_policy" in manager._policies
    
    def test_execute_recovery(self):
        """Test executing recovery"""
        from reliability.recovery import RecoveryManager, RecoveryPolicy, RecoveryAction
        
        manager = RecoveryManager()
        
        # Register handler
        manager.register_handler(
            RecoveryAction.RESTART,
            lambda params: True
        )
        
        # Execute
        record = manager.execute_recovery(
            "restart_on_failure",
            {"failure_count": 10}
        )
        
        assert record.policy_name == "restart_on_failure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
