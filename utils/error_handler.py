import logging
import traceback
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from enum import Enum
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import sys


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    TRADING = "trading"
    ANALYSIS = "analysis"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SmartPipError(Exception):
    """Base exception for SmartPip Trader"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "details": self.details
        }


class NetworkError(SmartPipError):
    """Network-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.HIGH, details)


class DatabaseError(SmartPipError):
    """Database-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.DATABASE, ErrorSeverity.HIGH, details)


class APIError(SmartPipError):
    """API-related errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.API, ErrorSeverity.MEDIUM, details)
        self.status_code = status_code


class ValidationError(SmartPipError):
    """Validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, ErrorCategory.VALIDATION, ErrorSeverity.LOW, details)


class AuthenticationError(SmartPipError):
    """Authentication errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, details)


class AuthorizationError(SmartPipError):
    """Authorization errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH, details)


class TradingError(SmartPipError):
    """Trading-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.TRADING, ErrorSeverity.CRITICAL, details)


class AnalysisError(SmartPipError):
    """Analysis-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.ANALYSIS, ErrorSeverity.MEDIUM, details)


class SystemError(SmartPipError):
    """System-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, details)


class ErrorHandler:
    """Centralized error handler for the system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history = []
        self.max_history = 1000
        self.error_callbacks = {}
        self.circuit_breakers = {}
    
    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle exception and return error response"""
        context = context or {}
        
        # Convert to SmartPipError if not already
        if not isinstance(exception, SmartPipError):
            smartpip_error = self._convert_exception(exception)
        else:
            smartpip_error = exception
        
        # Log error
        self._log_error(smartpip_error, context)
        
        # Add to history
        self._add_to_history(smartpip_error, context)
        
        # Check circuit breaker
        if self._is_circuit_open(smartpip_error.category):
            return self._create_circuit_open_response(smartpip_error.category)
        
        # Execute error callbacks
        self._execute_callbacks(smartpip_error, context)
        
        # Return error response
        return smartpip_error.to_dict()
    
    def _convert_exception(self, exception: Exception) -> SmartPipError:
        """Convert standard exception to SmartPipError"""
        if isinstance(exception, ConnectionError):
            return NetworkError(str(exception), {"original_type": type(exception).__name__})
        elif isinstance(exception, TimeoutError):
            return NetworkError("Request timed out", {"original_type": type(exception).__name__})
        elif isinstance(exception, ValueError):
            return ValidationError(str(exception), {"original_type": type(exception).__name__})
        elif isinstance(exception, PermissionError):
            return AuthorizationError(str(exception), {"original_type": type(exception).__name__})
        else:
            return SystemError(
                str(exception),
                {
                    "original_type": type(exception).__name__,
                    "traceback": traceback.format_exc()
                }
            )
    
    def _log_error(self, error: SmartPipError, context: Dict[str, Any]):
        """Log error with appropriate level"""
        log_data = {
            "error": error.__class__.__name__,
            "message": error.message,
            "category": error.category.value,
            "severity": error.severity.value,
            "context": context
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_data)
        else:
            self.logger.info(log_data)
    
    def _add_to_history(self, error: SmartPipError, context: Dict[str, Any]):
        """Add error to history"""
        self.error_history.append({
            "error": error.to_dict(),
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if needed
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def register_error_callback(
        self,
        category: ErrorCategory,
        callback: Callable[[SmartPipError, Dict[str, Any]], None]
    ):
        """Register callback for specific error category"""
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)
    
    def _execute_callbacks(self, error: SmartPipError, context: Dict[str, Any]):
        """Execute registered callbacks for error category"""
        callbacks = self.error_callbacks.get(error.category, [])
        for callback in callbacks:
            try:
                callback(error, context)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e}")
    
    def set_circuit_breaker(
        self,
        category: ErrorCategory,
        failure_threshold: int = 5,
        timeout_seconds: int = 60
    ):
        """Configure circuit breaker for error category"""
        self.circuit_breakers[category] = {
            "failure_count": 0,
            "failure_threshold": failure_threshold,
            "timeout_seconds": timeout_seconds,
            "last_failure_time": None,
            "state": "closed"  # closed, open, half-open
        }
    
    def _is_circuit_open(self, category: ErrorCategory) -> bool:
        """Check if circuit breaker is open for category"""
        breaker = self.circuit_breakers.get(category)
        if not breaker or breaker["state"] == "closed":
            return False
        
        # Check if timeout has passed
        if breaker["state"] == "open":
            if breaker["last_failure_time"]:
                elapsed = (datetime.now() - datetime.fromisoformat(breaker["last_failure_time"])).total_seconds()
                if elapsed > breaker["timeout_seconds"]:
                    breaker["state"] = "half-open"
                    return False
            return True
        
        return False
    
    def _record_failure(self, category: ErrorCategory):
        """Record failure for circuit breaker"""
        breaker = self.circuit_breakers.get(category)
        if not breaker:
            return
        
        breaker["failure_count"] += 1
        breaker["last_failure_time"] = datetime.now().isoformat()
        
        if breaker["failure_count"] >= breaker["failure_threshold"]:
            breaker["state"] = "open"
            self.logger.warning(f"Circuit breaker opened for {category.value}")
    
    def _record_success(self, category: ErrorCategory):
        """Record success for circuit breaker"""
        breaker = self.circuit_breakers.get(category)
        if not breaker:
            return
        
        if breaker["state"] == "half-open":
            breaker["failure_count"] = 0
            breaker["state"] = "closed"
            self.logger.info(f"Circuit breaker closed for {category.value}")
    
    def _create_circuit_open_response(self, category: ErrorCategory) -> Dict[str, Any]:
        """Create response for open circuit breaker"""
        return {
            "error": "CircuitBreakerOpen",
            "message": f"Service temporarily unavailable due to {category.value} errors",
            "category": category.value,
            "severity": ErrorSeverity.HIGH.value,
            "retry_after": self.circuit_breakers[category]["timeout_seconds"]
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Count by category
        category_counts = {}
        for entry in self.error_history:
            category = entry["error"]["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for entry in self.error_history:
            severity = entry["error"]["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "recent_errors": self.error_history[-10:]
        }
    
    def clear_history(self):
        """Clear error history"""
        self.error_history = []


# Global error handler instance
error_handler = ErrorHandler()


def create_error_middleware():
    """Create FastAPI error handling middleware"""
    
    async def middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except SmartPipError as e:
            error_response = error_handler.handle_exception(e, {"path": request.url.path})
            status_code = getattr(e, 'status_code', 500)
            return JSONResponse(status_code=status_code, content=error_response)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": e.detail})
        except Exception as e:
            error_response = error_handler.handle_exception(e, {"path": request.url.path})
            return JSONResponse(status_code=500, content=error_response)
    
    return middleware


def error_boundary(func: Callable) -> Callable:
    """Decorator for error boundary around functions"""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SmartPipError:
            raise  # Re-raise SmartPipError
        except Exception as e:
            raise error_handler._convert_exception(e) from e
    
    return wrapper


def async_error_boundary(func: Callable) -> Callable:
    """Decorator for async error boundary around functions"""
    
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except SmartPipError:
            raise  # Re-raise SmartPipError
        except Exception as e:
            raise error_handler._convert_exception(e) from e
    
    return wrapper
