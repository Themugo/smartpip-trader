"""
Structured Logging
==================

Centralized logging infrastructure with structured logging support.
"""

import logging
import json
import time
import threading
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from contextvars import ContextVar
from collections import deque


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Convert string to LogLevel"""
        level = level.lower()
        for member in cls:
            if member.value == level:
                return member
        return cls.INFO
    
    @classmethod
    def from_logging(cls, level: int) -> "LogLevel":
        """Convert logging level to LogLevel"""
        if level <= logging.DEBUG:
            return cls.DEBUG
        elif level <= logging.INFO:
            return cls.INFO
        elif level <= logging.WARNING:
            return cls.WARNING
        elif level <= logging.ERROR:
            return cls.ERROR
        else:
            return cls.CRITICAL


@dataclass
class LogContext:
    """Context information for logging"""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.span_id:
            result["span_id"] = self.span_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.session_id:
            result["session_id"] = self.session_id
        if self.request_id:
            result["request_id"] = self.request_id
        result.update(self.extra)
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value by key"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)
    
    def __enter__(self) -> "LogContext":
        """Enter context manager"""
        self._previous_context = _trace_context.get()
        _trace_context.set(self)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager"""
        _trace_context.set(self._previous_context)


# Context variable for trace context
_trace_context: ContextVar[LogContext] = ContextVar("trace_context", default=LogContext())


def set_trace_context(context: Optional[LogContext] = None, **kwargs) -> LogContext:
    """Set trace context for logging"""
    if context is None:
        context = LogContext(**kwargs) if kwargs else LogContext()
    _trace_context.set(context)
    return context


def get_trace_context() -> LogContext:
    """Get current trace context"""
    return _trace_context.get()


class StructuredLogger:
    """
    Structured logger with JSON output and context support.
    
    Features:
    - Structured JSON logging
    - Log level filtering
    - Context propagation
    - Multiple output handlers
    - Performance tracking
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._logger = logging.getLogger("smartpip")
        self._logger.setLevel(logging.DEBUG)
        
        # Add console handler if none exists
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self._logger.addHandler(handler)
        
        self._min_level = LogLevel.DEBUG
        self._handlers: List[Callable] = []
        self._history: deque = deque(maxlen=1000)
        self._stats = {
            "debug": 0,
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0
        }
        self._initialized = True
    
    def set_min_level(self, level: LogLevel) -> None:
        """Set minimum log level"""
        self._min_level = level
    
    def add_handler(self, handler: Callable) -> None:
        """Add a custom log handler"""
        self._handlers.append(handler)
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if level should be logged"""
        levels = list(LogLevel)
        return levels.index(level) >= levels.index(self._min_level)
    
    def _format_message(
        self,
        level: LogLevel,
        message: str,
        context: Optional[LogContext] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Format log message as structured data"""
        ctx = context or get_trace_context()
        
        record = {
            "timestamp": time.time(),
            "level": level.value,
            "message": message,
            **ctx.to_dict(),
            **kwargs
        }
        
        return record
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[LogContext] = None,
        **kwargs
    ) -> None:
        """Internal log method"""
        if not self._should_log(level):
            return
        
        record = self._format_message(level, message, context, **kwargs)
        
        # Store in history
        self._history.append(record)
        
        # Update stats
        self._stats[level.value] += 1
        
        # Log to standard logger
        log_method = getattr(self._logger, level.value, self._logger.info)
        log_method(json.dumps(record))
        
        # Call custom handlers
        for handler in self._handlers:
            try:
                handler(record)
            except Exception:
                pass  # Don't let handler errors break logging
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def log_event(
        self,
        event_name: str,
        level: LogLevel = LogLevel.INFO,
        **kwargs
    ) -> None:
        """Log a structured event"""
        self._log(level, f"Event: {event_name}", event_name=event_name, **kwargs)
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get log history"""
        return list(self._history)[-limit:]
    
    def get_stats(self) -> Dict[str, int]:
        """Get log statistics"""
        return self._stats.copy()
    
    def clear_history(self) -> None:
        """Clear log history"""
        self._history.clear()
    
    def get_context(self) -> Dict[str, Any]:
        """Get current trace context as dictionary"""
        return get_trace_context().to_dict()


# Global structured logger instance
structured_logger = StructuredLogger()


def log(
    level: LogLevel,
    message: str,
    **kwargs
) -> None:
    """Convenience function for logging"""
    structured_logger._log(level, message, **kwargs)


def log_event(
    event_name: str,
    level: LogLevel = LogLevel.INFO,
    **kwargs
) -> None:
    """Convenience function for logging events"""
    structured_logger.log_event(event_name, level, **kwargs)
