"""
Alerting System

Alert management with rules, channels, and notifications.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class ChannelType(Enum):
    """Notification channel types"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    """Alert rule definition"""
    rule_id: str
    name: str
    description: str
    
    # Condition
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    evaluation_period: str = "5m"
    
    # Severity
    severity: AlertSeverity = AlertSeverity.WARNING
    
    # Actions
    channels: List[str] = field(default_factory=list)
    auto_resolve: bool = True
    resolve_after_minutes: int = 5
    
    # Status
    enabled: bool = True
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "evaluation_period": self.evaluation_period,
            "severity": self.severity.value,
            "channels": self.channels,
            "auto_resolve": self.auto_resolve,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Alert:
    """Active alert"""
    alert_id: str
    rule_id: str
    rule_name: str
    
    # Alert details
    severity: AlertSeverity
    title: str
    message: str
    
    # Context
    metric_value: float
    threshold: float
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def acknowledge(self):
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now(timezone.utc)
    
    def resolve(self):
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "org_id": self.org_id,
            "status": self.status.value,
            "triggered_at": self.triggered_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
        }


@dataclass
class AlertChannel:
    """Notification channel"""
    channel_id: str
    name: str
    channel_type: ChannelType
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "type": self.channel_type.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


class AlertManager:
    """
    Alert management system.
    
    Features:
    - Rule management
    - Alert evaluation
    - Notification dispatch
    - Alert lifecycle
    """
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._channels: Dict[str, AlertChannel] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._last_evaluations: Dict[str, datetime] = {}
    
    def create_rule(self, rule_data: Dict[str, Any]) -> AlertRule:
        """Create a new alert rule"""
        rule = AlertRule(
            rule_id=f"rule_{uuid.uuid4().hex[:12]}",
            name=rule_data["name"],
            description=rule_data.get("description", ""),
            metric_name=rule_data["metric_name"],
            condition=rule_data["condition"],
            threshold=rule_data["threshold"],
            severity=AlertSeverity(rule_data.get("severity", "warning")),
            channels=rule_data.get("channels", []),
        )
        
        self._rules[rule.rule_id] = rule
        return rule
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get alert rule"""
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """List all rules"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[AlertRule]:
        """Update alert rule"""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        
        for key in ["name", "description", "threshold", "enabled", "channels"]:
            if key in updates:
                setattr(rule, key, updates[key])
        
        rule.updated_at = datetime.now(timezone.utc)
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete alert rule"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def create_channel(
        self,
        name: str,
        channel_type: ChannelType,
        config: Dict[str, Any],
    ) -> AlertChannel:
        """Create notification channel"""
        channel = AlertChannel(
            channel_id=f"chan_{uuid.uuid4().hex[:12]}",
            name=name,
            channel_type=channel_type,
            config=config,
        )
        
        self._channels[channel.channel_id] = channel
        return channel
    
    def list_channels(self) -> List[AlertChannel]:
        """List all channels"""
        return list(self._channels.values())
    
    def evaluate(self, metrics: Dict[str, float]) -> List[Alert]:
        """Evaluate rules against current metrics"""
        triggered_alerts = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # Check if metric exists
            if rule.metric_name not in metrics:
                continue
            
            # Check evaluation window
            last_eval = self._last_evaluations.get(rule.rule_id)
            if last_eval:
                period_minutes = int(rule.evaluation_period.rstrip("m"))
                if datetime.now(timezone.utc) - last_eval < timedelta(minutes=period_minutes):
                    continue
            
            # Evaluate condition
            value = metrics[rule.metric_name]
            should_trigger = self._check_condition(value, rule.condition, rule.threshold)
            
            self._last_evaluations[rule.rule_id] = datetime.now(timezone.utc)
            
            if should_trigger:
                alert = self._trigger_alert(rule, value)
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check if condition is met"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        return False
    
    def _trigger_alert(self, rule: AlertRule, metric_value: float) -> Alert:
        """Trigger a new alert"""
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:12]}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            title=f"{rule.name}: {metric_value} {rule.condition} {rule.threshold}",
            message=rule.description,
            metric_value=metric_value,
            threshold=rule.threshold,
        )
        
        self._alerts[alert.alert_id] = alert
        
        # Notify channels
        for channel_id in rule.channels:
            channel = self._channels.get(channel_id)
            if channel and channel.enabled:
                self._notify_channel(channel, alert)
        
        return alert
    
    def _notify_channel(self, channel: AlertChannel, alert: Alert):
        """Send notification to channel"""
        handlers = self._handlers.get(channel.channel_type.value, [])
        for handler in handlers:
            try:
                handler(channel, alert)
            except:
                pass
    
    def add_notification_handler(
        self,
        channel_type: ChannelType,
        handler: Callable,
    ):
        """Add notification handler"""
        if channel_type.value not in self._handlers:
            self._handlers[channel_type.value] = []
        self._handlers[channel_type.value].append(handler)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.acknowledge()
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        alert = self._alerts.get(alert_id)
        if alert and alert.status != AlertStatus.RESOLVED:
            alert.resolve()
            return True
        return False
    
    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        org_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """Get alerts with filters"""
        alerts = list(self._alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if org_id:
            alerts = [a for a in alerts if a.org_id == org_id]
        
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)[:limit]
    
    def get_active_alert_count(self) -> Dict[str, int]:
        """Get count of active alerts by severity"""
        active = [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]
        return {
            "total": len(active),
            "critical": sum(1 for a in active if a.severity == AlertSeverity.CRITICAL),
            "error": sum(1 for a in active if a.severity == AlertSeverity.ERROR),
            "warning": sum(1 for a in active if a.severity == AlertSeverity.WARNING),
            "info": sum(1 for a in active if a.severity == AlertSeverity.INFO),
        }
