import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager


class StructuredLogger:
    """Structured logger with performance tracking and JSON formatting"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Console handler with JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self.logger.info(message, extra={"structured_data": kwargs})
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self.logger.warning(message, extra={"structured_data": kwargs})
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self.logger.error(message, extra={"structured_data": kwargs})
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self.logger.debug(message, extra={"structured_data": kwargs})
    
    @contextmanager
    def track_operation(self, operation_name: str):
        """
        Context manager to track operation duration
        
        Args:
            operation_name: Name of the operation being tracked
        """
        start_time = time.time()
        self.info(f"Started: {operation_name}")
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.info(f"Completed: {operation_name}", duration=duration)


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # Add structured data if available
        if hasattr(record, "structured_data") and record.structured_data:
            log_data.update(record.structured_data)
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# Create default logger instances
system_logger = StructuredLogger("smartpip.system")
trade_logger = StructuredLogger("smartpip.trades")
performance_logger = StructuredLogger("smartpip.performance")
