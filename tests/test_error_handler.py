import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.error_handler import (
    ErrorHandler,
    SmartPipError,
    NetworkError,
    DatabaseError,
    APIError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    TradingError,
    AnalysisError,
    SystemError,
    ErrorSeverity,
    ErrorCategory,
    error_boundary
)


class TestSmartPipError(unittest.TestCase):
    """Test SmartPipError base exception class"""
    
    def test_error_creation_with_defaults(self):
        """Test error creation with default values"""
        error = SmartPipError("Test error message")
        
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.category, ErrorCategory.UNKNOWN)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error.details, {})
        self.assertEqual(error.user_message, "Test error message")
        self.assertIsNotNone(error.timestamp)
    
    def test_error_creation_with_custom_values(self):
        """Test error creation with custom values"""
        error = SmartPipError(
            message="Custom error",
            category=ErrorCategory.TRADING,
            severity=ErrorSeverity.CRITICAL,
            details={"key": "value"},
            user_message="User friendly message"
        )
        
        self.assertEqual(error.category, ErrorCategory.TRADING)
        self.assertEqual(error.severity, ErrorSeverity.CRITICAL)
        self.assertEqual(error.details, {"key": "value"})
        self.assertEqual(error.user_message, "User friendly message")
    
    def test_error_to_dict(self):
        """Test error serialization to dictionary"""
        error = SmartPipError(
            message="Test error",
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            details={"field": "test"}
        )
        
        error_dict = error.to_dict()
        
        self.assertEqual(error_dict["error"], "SmartPipError")
        self.assertEqual(error_dict["message"], "Test error")
        self.assertEqual(error_dict["category"], "api")
        self.assertEqual(error_dict["severity"], "high")
        self.assertIn("timestamp", error_dict)
        self.assertEqual(error_dict["details"], {"field": "test"})
    
    def test_error_inheritance_chain(self):
        """Test that all error types inherit from SmartPipError"""
        errors = [
            NetworkError("Network error"),
            DatabaseError("Database error"),
            APIError("API error"),
            ValidationError("Validation error"),
            AuthenticationError("Auth error"),
            AuthorizationError("Authz error"),
            TradingError("Trading error"),
            AnalysisError("Analysis error"),
            SystemError("System error"),
        ]
        
        for error in errors:
            self.assertIsInstance(error, SmartPipError)
            self.assertIsInstance(error, Exception)
    
    def test_specific_error_categories(self):
        """Test that specific error types have correct categories"""
        error_category_pairs = [
            (NetworkError("err"), ErrorCategory.NETWORK),
            (DatabaseError("err"), ErrorCategory.DATABASE),
            (APIError("err"), ErrorCategory.API),
            (ValidationError("err"), ErrorCategory.VALIDATION),
            (AuthenticationError("err"), ErrorCategory.AUTHENTICATION),
            (AuthorizationError("err"), ErrorCategory.AUTHORIZATION),
            (TradingError("err"), ErrorCategory.TRADING),
            (AnalysisError("err"), ErrorCategory.ANALYSIS),
            (SystemError("err"), ErrorCategory.SYSTEM),
        ]
        
        for error, expected_category in error_category_pairs:
            self.assertEqual(error.category, expected_category)
    
    def test_api_error_status_code(self):
        """Test APIError has status_code attribute"""
        error = APIError("API error", status_code=400)
        self.assertEqual(error.status_code, 400)
        
        # Default status code
        error2 = APIError("API error 2")
        self.assertEqual(error2.status_code, 500)
    
    def test_validation_error_field(self):
        """Test ValidationError can store field information"""
        error = ValidationError("Invalid input", field="email")
        self.assertEqual(error.details["field"], "email")


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = ErrorHandler()
        from datetime import datetime, timedelta
        self.datetime = datetime
        self.timedelta = timedelta
    
    def test_handler_initialization(self):
        """Test error handler initializes correctly"""
        self.assertIsNotNone(self.handler.logger)
        self.assertEqual(self.handler.error_history, [])
        self.assertEqual(self.handler.max_history, 1000)
        self.assertEqual(self.handler.error_callbacks, {})
        self.assertEqual(self.handler.circuit_breakers, {})
    
    def test_handle_smartpip_error(self):
        """Test handling a SmartPipError"""
        error = ValidationError("Test validation error")
        response = self.handler.handle_exception(error)
        
        self.assertEqual(response["error"], "ValidationError")
        self.assertEqual(response["message"], "Test validation error")
        self.assertEqual(response["category"], "validation")
        self.assertIn("timestamp", response)
    
    def test_handle_standard_exception(self):
        """Test handling a standard exception"""
        error = ValueError("Invalid value")
        response = self.handler.handle_exception(error)
        
        # Should convert to ValidationError
        self.assertEqual(response["error"], "ValidationError")
        self.assertIn("Invalid value", response["message"])
    
    def test_handle_connection_error(self):
        """Test handling ConnectionError converts to NetworkError"""
        error = ConnectionError("Connection failed")
        response = self.handler.handle_exception(error)
        
        self.assertEqual(response["category"], "network")
        self.assertIn("details", response)
    
    def test_handle_timeout_error(self):
        """Test handling TimeoutError converts to NetworkError"""
        error = TimeoutError("Request timed out")
        response = self.handler.handle_exception(error)
        
        self.assertEqual(response["category"], "network")
    
    def test_handle_permission_error(self):
        """Test handling PermissionError converts to AuthorizationError"""
        error = PermissionError("Access denied")
        response = self.handler.handle_exception(error)
        
        self.assertEqual(response["category"], "authorization")
    
    def test_error_history_tracking(self):
        """Test that errors are added to history"""
        self.handler.handle_exception(ValidationError("Error 1"))
        self.handler.handle_exception(ValidationError("Error 2"))
        
        self.assertEqual(len(self.handler.error_history), 2)
    
    def test_error_history_limit(self):
        """Test that history respects max limit"""
        # Create a handler with small history limit
        handler = ErrorHandler()
        handler.max_history = 5
        
        for i in range(10):
            handler.handle_exception(ValidationError(f"Error {i}"))
        
        self.assertEqual(len(handler.error_history), 5)
        # Should have the last 5 errors
        last_error = handler.error_history[-1]["error"]["message"]
        self.assertIn("Error 9", last_error)
    
    def test_error_stats(self):
        """Test error statistics calculation"""
        self.handler.handle_exception(ValidationError("Error 1"))
        self.handler.handle_exception(ValidationError("Error 2"))
        self.handler.handle_exception(NetworkError("Error 3"))
        
        stats = self.handler.get_error_stats()
        
        self.assertEqual(stats["total_errors"], 3)
        self.assertEqual(stats["by_category"]["validation"], 2)
        self.assertEqual(stats["by_category"]["network"], 1)
        self.assertIn("recent_errors", stats)
    
    def test_error_stats_empty(self):
        """Test error stats when no errors"""
        stats = self.handler.get_error_stats()
        
        self.assertEqual(stats["total_errors"], 0)
    
    def test_clear_history(self):
        """Test clearing error history"""
        self.handler.handle_exception(ValidationError("Error"))
        self.assertEqual(len(self.handler.error_history), 1)
        
        self.handler.clear_history()
        
        self.assertEqual(len(self.handler.error_history), 0)
        self.assertEqual(self.handler.get_error_stats()["total_errors"], 0)
    
    def test_register_error_callback(self):
        """Test registering error callbacks"""
        callback_executed = []
        
        def test_callback(error, context):
            callback_executed.append((error, context))
        
        self.handler.register_error_callback(ErrorCategory.VALIDATION, test_callback)
        
        self.assertIn(ErrorCategory.VALIDATION, self.handler.error_callbacks)
        self.assertEqual(len(self.handler.error_callbacks[ErrorCategory.VALIDATION]), 1)
    
    def test_callback_execution(self):
        """Test that callbacks are executed on errors"""
        callback_executed = []
        
        def test_callback(error, context):
            callback_executed.append(error)
        
        self.handler.register_error_callback(ErrorCategory.VALIDATION, test_callback)
        
        error = ValidationError("Test error")
        context = {"test": "context"}
        self.handler.handle_exception(error, context)
        
        self.assertEqual(len(callback_executed), 1)
        self.assertEqual(callback_executed[0].message, "Test error")
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker setup"""
        self.handler.set_circuit_breaker(
            ErrorCategory.NETWORK,
            failure_threshold=10,
            timeout_seconds=120
        )
        
        breaker = self.handler.circuit_breakers[ErrorCategory.NETWORK]
        self.assertEqual(breaker["failure_threshold"], 10)
        self.assertEqual(breaker["timeout_seconds"], 120)
        self.assertEqual(breaker["state"], "closed")
        self.assertEqual(breaker["failure_count"], 0)
    
    def test_circuit_closed_by_default(self):
        """Test circuit breaker is closed by default"""
        result = self.handler._is_circuit_open(ErrorCategory.NETWORK)
        self.assertFalse(result)
    
    def test_circuit_open_after_threshold(self):
        """Test circuit opens after failure threshold"""
        self.handler.set_circuit_breaker(
            ErrorCategory.API,
            failure_threshold=2,
            timeout_seconds=60
        )
        
        # Simulate failures
        self.handler._record_failure(ErrorCategory.API)
        self.assertFalse(self.handler._is_circuit_open(ErrorCategory.API))
        
        self.handler._record_failure(ErrorCategory.API)
        self.assertTrue(self.handler._is_circuit_open(ErrorCategory.API))
    
    def test_circuit_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout"""
        self.handler.set_circuit_breaker(
            ErrorCategory.DATABASE,
            failure_threshold=1,
            timeout_seconds=0  # Immediate timeout for testing
        )
        
        self.handler._record_failure(ErrorCategory.DATABASE)
        # Circuit should be open
        self.assertEqual(
            self.handler.circuit_breakers[ErrorCategory.DATABASE]["state"],
            "open"
        )
        
        # Manually set last_failure_time to the past to trigger transition
        self.handler.circuit_breakers[ErrorCategory.DATABASE]["last_failure_time"] = (
            self.datetime.now() - self.timedelta(seconds=1)
        ).isoformat()
        
        # Should transition to half-open when checked
        result = self.handler._is_circuit_open(ErrorCategory.DATABASE)
        self.assertFalse(result)
        self.assertEqual(
            self.handler.circuit_breakers[ErrorCategory.DATABASE]["state"],
            "half-open"
        )
    
    def test_circuit_success_resets_from_half_open(self):
        """Test successful request resets circuit breaker from half-open state"""
        self.handler.set_circuit_breaker(
            ErrorCategory.TRADING,
            failure_threshold=1,
            timeout_seconds=60
        )
        
        # Trigger circuit to open
        self.handler._record_failure(ErrorCategory.TRADING)
        self.assertEqual(
            self.handler.circuit_breakers[ErrorCategory.TRADING]["state"],
            "open"
        )
        
        # Manually transition to half-open (simulating timeout)
        self.handler.circuit_breakers[ErrorCategory.TRADING]["last_failure_time"] = (
            self.datetime.now() - self.timedelta(seconds=61)
        ).isoformat()
        self.handler._is_circuit_open(ErrorCategory.TRADING)  # This triggers the transition
        
        # Now in half-open state, success should close it
        self.handler._record_success(ErrorCategory.TRADING)
        self.assertEqual(
            self.handler.circuit_breakers[ErrorCategory.TRADING]["failure_count"],
            0
        )
        self.assertEqual(
            self.handler.circuit_breakers[ErrorCategory.TRADING]["state"],
            "closed"
        )
    
    def test_circuit_open_response(self):
        """Test response when circuit is open"""
        self.handler.set_circuit_breaker(
            ErrorCategory.AUTHENTICATION,
            failure_threshold=1,
            timeout_seconds=60
        )
        self.handler._record_failure(ErrorCategory.AUTHENTICATION)
        
        response = self.handler._create_circuit_open_response(ErrorCategory.AUTHENTICATION)
        
        self.assertEqual(response["error"], "CircuitBreakerOpen")
        self.assertIn("retry_after", response)
        self.assertEqual(response["retry_after"], 60)


class TestErrorBoundary(unittest.TestCase):
    """Test error boundary decorator"""
    
    def test_error_boundary_passes_through_smartpip_errors(self):
        """Test that SmartPipError passes through boundary"""
        @error_boundary
        def raises_smartpip_error():
            raise SmartPipError("Test error")
        
        with self.assertRaises(SmartPipError):
            raises_smartpip_error()
    
    def test_error_boundary_converts_standard_errors(self):
        """Test that standard errors are converted"""
        @error_boundary
        def raises_value_error():
            raise ValueError("Invalid value")
        
        with self.assertRaises(ValidationError) as context:
            raises_value_error()
        
        self.assertIn("Invalid value", str(context.exception))


class TestErrorEnums(unittest.TestCase):
    """Test error severity and category enums"""
    
    def test_error_severity_values(self):
        """Test ErrorSeverity enum values"""
        self.assertEqual(ErrorSeverity.LOW.value, "low")
        self.assertEqual(ErrorSeverity.MEDIUM.value, "medium")
        self.assertEqual(ErrorSeverity.HIGH.value, "high")
        self.assertEqual(ErrorSeverity.CRITICAL.value, "critical")
    
    def test_error_category_values(self):
        """Test ErrorCategory enum values"""
        expected_categories = [
            "network", "database", "api", "validation",
            "authentication", "authorization", "trading",
            "analysis", "system", "unknown"
        ]
        
        for category in expected_categories:
            self.assertTrue(
                any(c.value == category for c in ErrorCategory)
            )


if __name__ == "__main__":
    unittest.main()
