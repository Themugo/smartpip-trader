from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    alert_id: str
    category: str
    level: str
    title: str
    message: str
    source: str = ""
    timestamp: str = ""
    read: bool = False
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "category": self.category,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "read": self.read,
            "acknowledged": self.acknowledged,
        }


@dataclass
class WebhookConfig:
    webhook_id: str
    url: str
    events: List[str] = field(default_factory=list)
    enabled: bool = True
    secret: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "events": self.events,
            "enabled": self.enabled,
        }


class AlertManager:
    """Manages creation, filtering, and dispatch of alerts."""

    def __init__(self) -> None:
        self._alerts: List[Alert] = []
        self._webhooks: List[WebhookConfig] = []
        self._counter = 0
        self._filters: Dict[str, bool] = {
            "trade": True,
            "risk": True,
            "system": True,
            "info": True,
        }
        self._listeners: List[Callable[[Alert], None]] = []

    def add_listener(self, callback: Callable[[Alert], None]) -> None:
        self._listeners.append(callback)

    def create_alert(self, category: str, level: str, title: str, message: str, source: str = "") -> Alert:
        self._counter += 1
        alert = Alert(
            alert_id=f"AL{self._counter:06d}",
            category=category,
            level=level,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.utcnow().isoformat(),
        )
        self._alerts.append(alert)
        for listener in self._listeners:
            try:
                listener(alert)
            except Exception:
                logger.exception("Alert listener error")
        logger.info("Alert created: [%s/%s] %s", category, level, title)
        return alert

    def get_alerts(self, category: Optional[str] = None, level: Optional[str] = None, unread_only: bool = False) -> List[Dict[str, Any]]:
        result = self._alerts
        if category:
            result = [a for a in result if a.category == category]
        if level:
            result = [a for a in result if a.level == level]
        if unread_only:
            result = [a for a in result if not a.read]
        return [a.to_dict() for a in result[-100:]]

    def mark_read(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.read = True
                return True
        return False

    def acknowledge(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False

    def clear_old(self, max_age_hours: int = 168) -> int:
        cutoff = datetime.utcnow()
        before = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.timestamp > cutoff.isoformat()]
        return before - len(self._alerts)

    def add_webhook(self, url: str, events: List[str], secret: str = "") -> WebhookConfig:
        self._counter += 1
        wh = WebhookConfig(webhook_id=f"WH{self._counter:04d}", url=url, events=events, secret=secret)
        self._webhooks.append(wh)
        logger.info("Webhook added: %s -> %s", wh.webhook_id, url)
        return wh

    def remove_webhook(self, webhook_id: str) -> bool:
        before = len(self._webhooks)
        self._webhooks = [w for w in self._webhooks if w.webhook_id != webhook_id]
        return len(self._webhooks) < before

    def get_webhooks(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._webhooks]

    def set_filter(self, category: str, enabled: bool) -> None:
        self._filters[category] = enabled

    def get_unread_count(self) -> int:
        return sum(1 for a in self._alerts if not a.read)

    def summary(self) -> Dict[str, Any]:
        return {
            "total": len(self._alerts),
            "unread": self.get_unread_count(),
            "by_level": {
                "critical": sum(1 for a in self._alerts if a.level == "critical"),
                "warning": sum(1 for a in self._alerts if a.level == "warning"),
                "info": sum(1 for a in self._alerts if a.level == "info"),
            },
            "webhook_count": len(self._webhooks),
        }


class NotificationsWorkspace(WorkspaceBase):
    """Alert management: trade, risk, system alerts; webhook configuration."""

    def __init__(self) -> None:
        super().__init__("notifications", "Notifications", "notifications")
        self.alert_manager = AlertManager()

    def initialize(self) -> bool:
        logger.info("Notifications workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 2,
            "rows": 2,
            "panels": [
                {"id": "alert_feed", "title": "Alert Feed", "col_span": 1, "row_span": 2, "widget": "alert_list"},
                {"id": "alert_stats", "title": "Alert Summary", "col_span": 1, "row_span": 1, "widget": "stats_grid"},
                {"id": "webhook_config", "title": "Webhooks", "col_span": 1, "row_span": 1, "widget": "config_table"},
            ],
        }

    def on_data_update(self, data: Dict[str, Any]) -> None:
        if "alert" in data:
            a = data["alert"]
            self.alert_manager.create_alert(
                category=a.get("category", "system"),
                level=a.get("level", "info"),
                title=a.get("title", ""),
                message=a.get("message", ""),
                source=a.get("source", ""),
            )

    def get_alerts(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.alert_manager.get_alerts(**kwargs)

    def get_webhooks(self) -> List[Dict[str, Any]]:
        return self.alert_manager.get_webhooks()

    def add_webhook(self, url: str, events: List[str]) -> Dict[str, Any]:
        wh = self.alert_manager.add_webhook(url, events)
        return wh.to_dict()

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["alert_summary"] = self.alert_manager.summary()
        return state
