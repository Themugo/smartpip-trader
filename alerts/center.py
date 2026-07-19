"""
Smart Alert Center - Intelligent Alerting System

Comprehensive alert management:
- Alert generation and prioritization
- Filtering and grouping
- Notification dispatch
- Alert history
"""

import asyncio
import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """Alert categories"""
    MARKET = "market"
    TRADING = "trading"
    RISK = "risk"
    SYSTEM = "system"
    AI = "ai"
    CONNECTION = "connection"
    PERFORMANCE = "performance"
    SECURITY = "security"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass
class Alert:
    """An alert notification"""
    id: str
    title: str
    message: str
    priority: AlertPriority
    category: AlertCategory
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Source information
    source: str = ""
    source_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Related data
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_alert_ids: List[str] = field(default_factory=list)
    
    # Actions
    actions: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "category": self.category.value,
            "status": self.status.value,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
            "related_alert_ids": self.related_alert_ids,
            "actions": self.actions,
        }


class AlertRule:
    """Rule for automatic alert generation"""
    def __init__(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        alert_template: Dict[str, Any],
        priority: AlertPriority = AlertPriority.MEDIUM,
        category: AlertCategory = AlertCategory.SYSTEM,
        cooldown_seconds: int = 60,
        enabled: bool = True,
    ):
        self.name = name
        self.condition = condition
        self.alert_template = alert_template
        self.priority = priority
        self.category = category
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        self._last_triggered: Optional[datetime] = None
    
    def should_trigger(self) -> bool:
        """Check if rule should trigger (respecting cooldown)"""
        if not self.enabled:
            return False
        
        if self._last_triggered:
            elapsed = (datetime.now(timezone.utc) - self._last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
        
        return True
    
    def trigger(self) -> Alert:
        """Trigger the rule and create an alert"""
        self._last_triggered = datetime.now(timezone.utc)
        
        return Alert(
            id=self.alert_template.get("id", ""),
            title=self.alert_template.get("title", "Alert"),
            message=self.alert_template.get("message", ""),
            priority=self.priority,
            category=self.category,
            source=self.alert_template.get("source", ""),
        )


class AlertCenter:
    """
    Smart Alert Center for intelligent alerting.
    
    Features:
    - Multi-channel alerts
    - Priority-based filtering
    - Automatic grouping
    - Notification templates
    - Alert rules
    - History and analytics
    """
    
    def __init__(
        self,
        storage_path: str = "data/alerts",
        max_alerts: int = 10000,
    ):
        self._storage_path = storage_path
        self._max_alerts = max_alerts
        
        self._alerts: deque = deque(maxlen=max_alerts)
        self._rules: Dict[str, AlertRule] = {}
        self._subscribers: Dict[str, List[Callable]] = {
            "on_alert": [],
            "on_acknowledge": [],
            "on_resolve": [],
            "on_dismiss": [],
        }
        self._notification_channels: Dict[str, Callable] = {}
        self._filters: List[Callable[[Alert], bool]] = []
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_alerts()
        self._init_default_rules()
    
    def _load_alerts(self) -> None:
        """Load alerts from storage"""
        alerts_file = os.path.join(self._storage_path, "alerts.json")
        
        if os.path.exists(alerts_file):
            try:
                with open(alerts_file, "r") as f:
                    data = json.load(f)
                
                for alert_data in data.get("alerts", []):
                    alert_data["created_at"] = datetime.fromisoformat(alert_data["created_at"])
                    if alert_data.get("acknowledged_at"):
                        alert_data["acknowledged_at"] = datetime.fromisoformat(alert_data["acknowledged_at"])
                    if alert_data.get("resolved_at"):
                        alert_data["resolved_at"] = datetime.fromisoformat(alert_data["resolved_at"])
                    
                    alert = Alert(**alert_data)
                    self._alerts.append(alert)
                
                logger.info(f"Loaded {len(self._alerts)} alerts")
            except Exception as e:
                logger.error(f"Failed to load alerts: {e}")
    
    def _save_alerts(self) -> None:
        """Save alerts to storage"""
        alerts_file = os.path.join(self._storage_path, "alerts.json")
        
        data = {
            "alerts": [a.to_dict() for a in list(self._alerts)[-5000:]]
        }
        
        try:
            with open(alerts_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")
    
    def _init_default_rules(self) -> None:
        """Initialize default alert rules"""
        # High confidence drop
        self.add_rule(AlertRule(
            name="high_confidence_drop",
            condition=lambda d: d.get("confidence_drop", 0) > 20,
            alert_template={
                "title": "Confidence Drop Detected",
                "message": "AI confidence dropped significantly",
            },
            priority=AlertPriority.MEDIUM,
            category=AlertCategory.AI,
        ))
        
        # Risk limit breach
        self.add_rule(AlertRule(
            name="risk_limit_breach",
            condition=lambda d: d.get("risk_breach", False),
            alert_template={
                "title": "Risk Limit Breach",
                "message": "Trading stopped due to risk limit",
            },
            priority=AlertPriority.CRITICAL,
            category=AlertCategory.RISK,
        ))
        
        # Connection loss
        self.add_rule(AlertRule(
            name="connection_loss",
            condition=lambda d: d.get("connected", True) == False,
            alert_template={
                "title": "Connection Lost",
                "message": "API connection interrupted",
            },
            priority=AlertPriority.HIGH,
            category=AlertCategory.CONNECTION,
        ))
        
        # Drawdown alert
        self.add_rule(AlertRule(
            name="high_drawdown",
            condition=lambda d: d.get("drawdown", 0) > 10,
            alert_template={
                "title": "Elevated Drawdown",
                "message": "Account drawdown exceeds threshold",
            },
            priority=AlertPriority.HIGH,
            category=AlertCategory.RISK,
        ))
    
    def create_alert(
        self,
        title: str,
        message: str,
        priority: AlertPriority,
        category: AlertCategory,
        source: str = "",
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Create and dispatch a new alert.
        
        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority
            category: Alert category
            source: Source of the alert
            source_id: ID of related object
            metadata: Additional metadata
            
        Returns:
            Created Alert
        """
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            priority=priority,
            category=category,
            source=source,
            source_id=source_id,
            metadata=metadata or {},
        )
        
        # Check filters
        for f in self._filters:
            if not f(alert):
                return alert
        
        # Add to alerts
        self._alerts.append(alert)
        
        # Fire callbacks
        self._fire_callbacks("on_alert", alert)
        
        # Dispatch to notification channels
        self._dispatch_to_channels(alert)
        
        # Save
        self._save_alerts()
        
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                self._fire_callbacks("on_acknowledge", alert)
                self._save_alerts()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                self._fire_callbacks("on_resolve", alert)
                self._save_alerts()
                return True
        return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert"""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = AlertStatus.DISMISSED
                self._fire_callbacks("on_dismiss", alert)
                return True
        return False
    
    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        priority: Optional[AlertPriority] = None,
        category: Optional[AlertCategory] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts with optional filtering"""
        alerts = list(self._alerts)
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        if since:
            alerts = [a for a in alerts if a.created_at >= since]
        
        return alerts[-limit:]
    
    def get_active_alerts(
        self,
        priority: Optional[AlertPriority] = None,
    ) -> List[Alert]:
        """Get active (unresolved) alerts"""
        return self.get_alerts(
            status=AlertStatus.ACTIVE,
            priority=priority,
        )
    
    def get_unacknowledged_count(self) -> int:
        """Get count of unacknowledged alerts"""
        return sum(1 for a in self._alerts if a.status == AlertStatus.ACTIVE)
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        self._rules[rule.name] = rule
    
    def remove_rule(self, name: str) -> bool:
        """Remove an alert rule"""
        if name in self._rules:
            del self._rules[name]
            return True
        return False
    
    def evaluate_rules(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate all rules against data"""
        triggered_alerts = []
        
        for rule in self._rules.values():
            if rule.should_trigger():
                try:
                    if rule.condition(data):
                        alert = rule.trigger()
                        triggered_alerts.append(alert)
                        self._alerts.append(alert)
                        self._fire_callbacks("on_alert", alert)
                except Exception as e:
                    logger.error(f"Rule evaluation error for {rule.name}: {e}")
        
        if triggered_alerts:
            self._save_alerts()
        
        return triggered_alerts
    
    def register_channel(
        self,
        name: str,
        handler: Callable[[Alert], None],
    ) -> None:
        """Register a notification channel"""
        self._notification_channels[name] = handler
    
    def _dispatch_to_channels(self, alert: Alert) -> None:
        """Dispatch alert to notification channels"""
        for name, handler in self._notification_channels.items():
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Channel {name} error: {e}")
    
    def add_filter(self, filter_func: Callable[[Alert], bool]) -> None:
        """Add an alert filter"""
        self._filters.append(filter_func)
    
    def on_event(
        self,
        event_type: str,
        callback: Callable,
    ) -> None:
        """Register an event callback"""
        if event_type in self._subscribers:
            self._subscribers[event_type].append(callback)
    
    def _fire_callbacks(self, event_type: str, *args) -> None:
        """Fire registered callbacks"""
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error for {event_type}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        alerts = list(self._alerts)
        
        priority_counts = {}
        category_counts = {}
        status_counts = {}
        
        for alert in alerts:
            priority_counts[alert.priority.value] = (
                priority_counts.get(alert.priority.value, 0) + 1
            )
            category_counts[alert.category.value] = (
                category_counts.get(alert.category.value, 0) + 1
            )
            status_counts[alert.status.value] = (
                status_counts.get(alert.status.value, 0) + 1
            )
        
        return {
            "total_alerts": len(alerts),
            "active_alerts": status_counts.get("active", 0),
            "acknowledged_alerts": status_counts.get("acknowledged", 0),
            "resolved_alerts": status_counts.get("resolved", 0),
            "by_priority": priority_counts,
            "by_category": category_counts,
            "by_status": status_counts,
        }
    
    def cleanup_old_alerts(self, before: datetime) -> int:
        """Remove old resolved/dismissed alerts"""
        before = before or datetime.now(timezone.utc) - timedelta(days=7)
        
        original_count = len(self._alerts)
        
        self._alerts = deque(
            [a for a in self._alerts if not (
                a.status in (AlertStatus.RESOLVED, AlertStatus.DISMISSED) and
                a.created_at < before
            )],
            maxlen=self._max_alerts
        )
        
        removed = original_count - len(self._alerts)
        if removed > 0:
            self._save_alerts()
        
        return removed
