"""
Structured Logging and Developer Tools

Provides comprehensive logging capabilities:
- Structured JSON logging
- Log levels and filtering
- Log aggregation
- Performance tracking
- Error tracing
"""

import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
import traceback

# Context variables for request tracing
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


class LogLevel(Enum):
    """Log levels"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """Log output formats"""
    TEXT = "text"
    JSON = "json"
    COMPACT = "compact"


@dataclass
class LogEntry:
    """A single log entry"""
    timestamp: datetime
    level: str
    message: str
    module: str
    function: str
    line: int
    request_id: str
    user_id: str
    extra: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "extra": self.extra,
            "error": self.error,
            "stack_trace": self.stack_trace,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class LogCollector:
    """Collects and manages log entries"""
    
    def __init__(self, max_entries: int = 10000):
        self._entries: deque = deque(maxlen=max_entries)
        self._listeners: List[Callable[[LogEntry], None]] = []
        self._filters: List[Callable[[LogEntry], bool]] = []
        self._level_filter: LogLevel = LogLevel.TRACE
    
    def add_entry(self, entry: LogEntry) -> None:
        """Add a log entry"""
        if self._should_include(entry):
            self._entries.append(entry)
            self._notify_listeners(entry)
    
    def _should_include(self, entry: LogEntry) -> bool:
        """Check if entry passes filters"""
        # Level filter
        entry_level = LogLevel[entry.level.upper()]
        if entry_level.value < self._level_filter.value:
            return False
        
        # Custom filters
        for f in self._filters:
            if not f(entry):
                return False
        
        return True
    
    def _notify_listeners(self, entry: LogEntry) -> None:
        """Notify listeners of new entry"""
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass
    
    def set_level_filter(self, level: LogLevel) -> None:
        """Set minimum log level"""
        self._level_filter = level
    
    def add_filter(self, filter_func: Callable[[LogEntry], bool]) -> None:
        """Add a custom filter"""
        self._filters.append(filter_func)
    
    def add_listener(self, listener: Callable[[LogEntry], None]) -> None:
        """Add a listener for new entries"""
        self._listeners.append(listener)
    
    def get_entries(
        self,
        level: Optional[LogLevel] = None,
        since: Optional[datetime] = None,
        module: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Get filtered log entries"""
        entries = list(self._entries)
        
        if level:
            entries = [e for e in entries if e.level.upper() == level.name]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        if module:
            entries = [e for e in entries if module in e.module]
        
        if search:
            search_lower = search.lower()
            entries = [
                e for e in entries
                if search_lower in e.message.lower() or
                   any(search_lower in str(v).lower() for v in e.extra.values())
            ]
        
        return entries[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        entries = list(self._entries)
        
        counts = {}
        for entry in entries:
            counts[entry.level] = counts.get(entry.level, 0) + 1
        
        return {
            "total_entries": len(entries),
            "by_level": counts,
            "oldest": entries[0].timestamp.isoformat() if entries else None,
            "newest": entries[-1].timestamp.isoformat() if entries else None,
        }
    
    def clear(self) -> None:
        """Clear all entries"""
        self._entries.clear()
    
    def export_json(self, filepath: str) -> None:
        """Export logs to JSON file"""
        with open(filepath, "w") as f:
            json.dump([e.to_dict() for e in self._entries], f, indent=2)
    
    def export_csv(self, filepath: str) -> None:
        """Export logs to CSV file"""
        import csv
        
        with open(filepath, "w", newline="") as f:
            fieldnames = ["timestamp", "level", "message", "module", "function", "request_id"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in self._entries:
                writer.writerow({
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level,
                    "message": entry.message,
                    "module": entry.module,
                    "function": entry.function,
                    "request_id": entry.request_id,
                })


class DeveloperLogger:
    """Enhanced logger with structured logging support"""
    
    def __init__(
        self,
        name: str,
        collector: Optional[LogCollector] = None,
        format_type: LogFormat = LogFormat.JSON,
    ):
        self._name = name
        self._logger = logging.getLogger(name)
        self._collector = collector
        self._format_type = format_type
        self._request_id = ""
        self._user_id = ""
    
    @property
    def name(self) -> str:
        return self._name
    
    def set_request_id(self, request_id: str) -> None:
        """Set request context"""
        self._request_id = request_id
        request_id_ctx.set(request_id)
    
    def set_user_id(self, user_id: str) -> None:
        """Set user context"""
        self._user_id = user_id
        user_id_ctx.set(user_id)
    
    def _create_entry(
        self,
        level: str,
        message: str,
        exc_info: Optional[Exception] = None,
        **extra,
    ) -> LogEntry:
        """Create a log entry"""
        # Get caller info
        frame = sys._getframe(2)
        module = frame.f_globals.get("__name__", "unknown")
        
        # Find the actual logging call
        while "logging" in module or module == __name__:
            frame = frame.f_back
            if frame is None:
                break
            module = frame.f_globals.get("__name__", "unknown")
        
        function = frame.f_code.co_name
        line = frame.f_lineno
        
        error = None
        stack_trace = None
        if exc_info:
            if isinstance(exc_info, Exception):
                error = str(exc_info)
                stack_trace = traceback.format_exc()
            else:
                error = str(exc_info[1]) if exc_info[1] else None
                if exc_info[2]:
                    stack_trace = "".join(traceback.format_tb(exc_info[2]))
        
        return LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            module=module,
            function=function,
            line=line,
            request_id=self._request_id or request_id_ctx.get(""),
            user_id=self._user_id or user_id_ctx.get(""),
            extra=extra,
            error=error,
            stack_trace=stack_trace,
        )
    
    def _log(
        self,
        level: str,
        message: str,
        exc_info: Optional[Exception] = None,
        **extra,
    ) -> None:
        """Internal log method"""
        entry = self._create_entry(level, message, exc_info, **extra)
        
        # Add to collector
        if self._collector:
            self._collector.add_entry(entry)
        
        # Output to standard logger
        if self._format_type == LogFormat.JSON:
            output = entry.to_json()
        else:
            output = f"[{entry.timestamp.isoformat()}] {entry.level}: {message}"
            if extra:
                output += f" | {extra}"
        
        getattr(self._logger, level.lower())(output)
    
    def trace(self, message: str, **extra) -> None:
        """Log trace level"""
        self._log("TRACE", message, **extra)
    
    def debug(self, message: str, **extra) -> None:
        """Log debug level"""
        self._log("DEBUG", message, **extra)
    
    def info(self, message: str, **extra) -> None:
        """Log info level"""
        self._log("INFO", message, **extra)
    
    def warning(self, message: str, **extra) -> None:
        """Log warning level"""
        self._log("WARNING", message, **extra)
    
    def error(self, message: str, exc_info: Optional[Exception] = None, **extra) -> None:
        """Log error level"""
        self._log("ERROR", message, exc_info, **extra)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None, **extra) -> None:
        """Log critical level"""
        self._log("CRITICAL", message, exc_info, **extra)


# Global log collector
_global_collector = LogCollector()


def get_log_collector() -> LogCollector:
    """Get the global log collector"""
    return _global_collector


def get_logger(name: str, format_type: LogFormat = LogFormat.JSON) -> DeveloperLogger:
    """Get a developer logger instance"""
    return DeveloperLogger(name, _global_collector, format_type)


def setup_logging(
    level: str = "INFO",
    format_type: LogFormat = LogFormat.JSON,
    log_file: Optional[str] = None,
    max_entries: int = 10000,
) -> LogCollector:
    """
    Setup structured logging for the application.
    
    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format
        log_file: Optional file path for logging
        max_entries: Maximum log entries to keep in memory
        
    Returns:
        The global LogCollector instance
    """
    global _global_collector
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter based on type
    if format_type == LogFormat.JSON:
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
            )
        )
    
    root_logger.addHandler(handler)
    
    # File handler if specified
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        if format_type == LogFormat.JSON:
            file_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
                )
            )
        root_logger.addHandler(file_handler)
    
    # Create new collector
    _global_collector = LogCollector(max_entries=max_entries)
    _global_collector.set_level_filter(LogLevel[level.upper()])
    
    return _global_collector


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: DeveloperLogger, operation: str):
        self._logger = logger
        self._operation = operation
        self._start_time: Optional[float] = None
    
    def __enter__(self):
        self._start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self._start_time
        if exc_type:
            self._logger.error(
                f"{self._operation} failed after {duration*1000:.2f}ms",
                exc_info=exc_val,
            )
        else:
            self._logger.debug(
                f"{self._operation} completed in {duration*1000:.2f}ms"
            )
