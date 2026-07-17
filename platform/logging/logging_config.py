from __future__ import annotations

import json
import logging
import logging.handlers
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LogCategory(str, Enum):
    TRADE = "trade"
    SYSTEM = "system"
    ERROR = "error"
    AUDIT = "audit"
    PERFORMANCE = "performance"
    RISK = "risk"
    PLUGIN = "plugin"
    API = "api"


@dataclass
class LogRecord:
    timestamp: str
    level: str
    category: str
    logger_name: str
    message: str
    module: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "category": self.category,
            "logger_name": self.logger_name,
            "message": self.message,
            "module": self.module,
            "extra": self.extra,
        }


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "category"):
            log_data["category"] = record.category
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        return json.dumps(log_data, default=str)


class CategoryFilter(logging.Filter):
    """Filter log records by category."""

    def __init__(self, categories: Optional[List[str]] = None) -> None:
        super().__init__()
        self._categories = set(categories) if categories else set()

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._categories:
            return True
        category = getattr(record, "category", "")
        return category in self._categories


class PlatformLogger:
    """Comprehensive structured logging with trade, system, error, and audit loggers."""

    def __init__(
        self,
        log_dir: str = "logs",
        app_name: str = "smartpip",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        console_output: bool = True,
        json_format: bool = True,
    ) -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._app_name = app_name
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: List[logging.Handler] = []
        self._in_memory: List[LogRecord] = []
        self._max_memory = 5000
        self._json_format = json_format
        self._setup_root(console_output)
        self._setup_category_loggers()
        logger.info("PlatformLogger initialized (dir=%s, json=%s)", log_dir, json_format)

    def _setup_root(self, console_output: bool) -> None:
        root = logging.getLogger(self._app_name)
        root.setLevel(logging.DEBUG)
        fmt = StructuredFormatter() if self._json_format else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.handlers.RotatingFileHandler(
            self._log_dir / f"{self._app_name}.log",
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
        self._handlers.append(file_handler)
        if console_output:
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            ))
            console.setLevel(logging.INFO)
            root.addHandler(console)
            self._handlers.append(console)
        self._loggers["root"] = root

    def _setup_category_loggers(self) -> None:
        fmt = StructuredFormatter() if self._json_format else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        for category in LogCategory:
            cat_logger = logging.getLogger(f"{self._app_name}.{category.value}")
            cat_logger.setLevel(logging.DEBUG)
            handler = logging.handlers.RotatingFileHandler(
                self._log_dir / f"{self._app_name}_{category.value}.log",
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(fmt)
            handler.setLevel(logging.DEBUG)
            cat_logger.addHandler(handler)
            self._handlers.append(handler)
            self._loggers[category.value] = cat_logger

    def _log(self, level: str, message: str, category: LogCategory, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        cat_logger = self._loggers.get(category.value, self._loggers["root"])
        log_record = LogRecord(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            level=level,
            category=category.value,
            logger_name=cat_logger.name,
            message=message,
            extra=extra or {},
        )
        self._in_memory.append(log_record)
        if len(self._in_memory) > self._max_memory:
            self._in_memory = self._in_memory[-self._max_memory:]
        log_method = getattr(cat_logger, level.lower(), cat_logger.info)
        log_method(message, **kwargs)

    def trade(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, LogCategory.TRADE, **kwargs)

    def system(self, message: str, level: str = "INFO", **kwargs: Any) -> None:
        self._log(level, message, LogCategory.SYSTEM, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, LogCategory.ERROR, **kwargs)

    def audit(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, LogCategory.AUDIT, **kwargs)

    def performance(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, LogCategory.PERFORMANCE, **kwargs)

    def risk(self, message: str, level: str = "WARNING", **kwargs: Any) -> None:
        self._log(level, message, LogCategory.RISK, **kwargs)

    def plugin(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, LogCategory.PLUGIN, **kwargs)

    def api(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, LogCategory.API, **kwargs)

    def get_recent(self, category: Optional[LogCategory] = None, level: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        records = self._in_memory
        if category:
            records = [r for r in records if r.category == category.value]
        if level:
            records = [r for r in records if r.level == level.upper()]
        return [r.to_dict() for r in records[-limit:]]

    def export_logs(self, category: Optional[LogCategory] = None, format_type: str = "json") -> str:
        records = self.get_recent(category=category, limit=10000)
        if format_type == "json":
            return json.dumps(records, indent=2, default=str)
        lines = [f"[{r['timestamp']}] [{r['level']}] [{r['category']}] {r['message']}" for r in records]
        return "\n".join(lines)

    def set_level(self, level: str, category: Optional[LogCategory] = None) -> None:
        log_level = getattr(logging, level.upper(), logging.INFO)
        if category and category.value in self._loggers:
            self._loggers[category.value].setLevel(log_level)
        elif "root" in self._loggers:
            self._loggers["root"].setLevel(log_level)
        logger.debug("Log level set to %s for %s", level, category.value if category else "root")

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(f"{self._app_name}.{name}")

    def flush(self) -> None:
        for handler in self._handlers:
            if hasattr(handler, "flush"):
                handler.flush()

    def get_stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for r in self._in_memory:
            counts[r.category] = counts.get(r.category, 0) + 1
        return {
            "total_records": len(self._in_memory),
            "by_category": counts,
            "log_dir": str(self._log_dir),
            "logger_count": len(self._loggers),
            "handler_count": len(self._handlers),
        }
