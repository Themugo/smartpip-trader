from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str = ""
    function: str = ""
    line: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "extra": self.extra,
        }


@dataclass
class APIRequest:
    request_id: str
    method: str
    url: str
    status_code: int = 0
    duration_ms: float = 0.0
    timestamp: str = ""
    request_body: str = ""
    response_body: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class SystemHealth:
    cpu_usage_pct: float = 0.0
    memory_usage_pct: float = 0.0
    active_connections: int = 0
    uptime_seconds: float = 0.0
    error_rate_1h: float = 0.0
    last_heartbeat: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_usage_pct": self.cpu_usage_pct,
            "memory_usage_pct": self.memory_usage_pct,
            "active_connections": self.active_connections,
            "uptime_seconds": self.uptime_seconds,
            "error_rate_1h": self.error_rate_1h,
            "last_heartbeat": self.last_heartbeat,
        }


class DeveloperConsoleWorkspace(WorkspaceBase):
    """Log viewer, API inspector, strategy debugger, system health, manual API calls."""

    def __init__(self, max_logs: int = 2000) -> None:
        super().__init__("developer_console", "Developer Console", "terminal")
        self._logs: deque[LogEntry] = deque(maxlen=max_logs)
        self._api_requests: deque[APIRequest] = deque(maxlen=500)
        self._health = SystemHealth()
        self._start_time = time.time()
        self._filter_level = "DEBUG"
        self._filter_module = ""
        self._debug_points: Dict[str, bool] = {}
        self._request_counter = 0

    def initialize(self) -> bool:
        logger.info("DeveloperConsole workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 2,
            "rows": 3,
            "panels": [
                {"id": "log_viewer", "title": "Log Viewer", "col_span": 2, "row_span": 2, "widget": "log_table"},
                {"id": "system_health", "title": "System Health", "col_span": 1, "row_span": 1, "widget": "gauge_grid"},
                {"id": "api_inspector", "title": "API Inspector", "col_span": 1, "row_span": 1, "widget": "request_list"},
                {"id": "debug_console", "title": "Debug Console", "col_span": 2, "row_span": 1, "widget": "terminal"},
            ],
        }

    def add_log(self, level: str, message: str, module: str = "", function: str = "", line: int = 0, extra: Optional[Dict[str, Any]] = None) -> None:
        from datetime import datetime
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            logger_name=module,
            message=message,
            module=module,
            function=function,
            line=line,
            extra=extra or {},
        )
        self._logs.append(entry)

    def get_logs(self, level: Optional[str] = None, module: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        logs = list(self._logs)
        if level:
            logs = [l for l in logs if l.level == level.upper()]
        if module:
            logs = [l for l in logs if module.lower() in l.module.lower()]
        return [l.to_dict() for l in logs[-limit:]]

    def set_filter(self, level: Optional[str] = None, module: Optional[str] = None) -> None:
        if level is not None:
            self._filter_level = level
        if module is not None:
            self._filter_module = module
        logger.debug("Log filter set: level=%s, module=%s", self._filter_level, self._filter_module)

    def log_api_request(self, method: str, url: str, status_code: int = 0, duration_ms: float = 0.0) -> APIRequest:
        from datetime import datetime
        self._request_counter += 1
        req = APIRequest(
            request_id=f"REQ{self._request_counter:06d}",
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
        )
        self._api_requests.append(req)
        return req

    def get_api_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in list(self._api_requests)[-limit:]]

    def update_health(self, health: Dict[str, Any]) -> None:
        for k, v in health.items():
            if hasattr(self._health, k):
                setattr(self._health, k, v)
        self._health.uptime_seconds = time.time() - self._start_time

    def get_health(self) -> Dict[str, Any]:
        self._health.uptime_seconds = time.time() - self._start_time
        return self._health.to_dict()

    def add_debug_point(self, name: str) -> None:
        self._debug_points[name] = True
        logger.info("Debug point added: %s", name)

    def remove_debug_point(self, name: str) -> bool:
        return self._debug_points.pop(name, None) is not None

    def get_debug_points(self) -> Dict[str, bool]:
        return dict(self._debug_points)

    def execute_manual_command(self, command: str) -> Dict[str, Any]:
        logger.info("Manual command: %s", command)
        return {
            "command": command,
            "status": "received",
            "message": f"Command '{command}' acknowledged",
        }

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["log_count"] = len(self._logs)
        state["state"]["api_request_count"] = len(self._api_requests)
        state["state"]["debug_points"] = list(self._debug_points.keys())
        state["state"]["uptime"] = time.time() - self._start_time
        return state
