"""
Alert Manager
=============

Alert rules engine with severity levels and notifications.
"""

import time
import threading
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """Definition of an alert rule"""
    id: str
    name: str
    description: str = ""
    condition: Callable[[], bool] = field(default=None)
    metric_name: Optional[str] = None
    operator: Optional[str] = None  # gt, lt, eq, gte, lte
    threshold: Optional[float] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    cooldown_seconds: float = 300  # Don't re-fire within this period
    created_at: float = field(default_factory=time.time)
    
    def evaluate(self, metric_value: Optional[float] = None) -> bool:
        """Evaluate if alert should fire"""
        if not self.enabled:
            return False
        
        if self.condition:
            return self.condition()
        
        if self.metric_name and self.operator and self.threshold is not None:
            if metric_value is None:
                return False
            
            if self.operator == "gt":
                return metric_value > self.threshold
            elif self.operator == "lt":
                return metric_value < self.threshold
            elif self.operator == "gte":
                return metric_value >= self.threshold
            elif self.operator == "lte":
                return metric_value <= self.threshold
            elif self.operator == "eq":
                return metric_value == self.threshold
        
        return False


@dataclass
class Alert:
    """A triggered alert"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    status: AlertStatus = AlertStatus.FIRING
    value: Optional[float] = None
    threshold: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "metadata": self.metadata,
            "resolved_at": self.resolved_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
        }


class AlertManager:
    """
    Alert rules engine with notification support.
    
    Features:
    - Alert rule definitions
    - Condition-based evaluation
    - Severity levels
    - Cooldown management
    - Alert acknowledgment
    - Multiple notification channels
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._last_fired: Dict[str, float] = {}  # rule_id -> timestamp
        self._notification_handlers: Dict[AlertSeverity, List[Callable]] = {
            severity: [] for severity in AlertSeverity
        }
        self._global_handlers: List[Callable] = []
        self._initialized = True
    
    def create_rule(
        self,
        name: str,
        description: str = "",
        condition: Optional[Callable[[], bool]] = None,
        metric_name: Optional[str] = None,
        operator: Optional[str] = None,
        threshold: Optional[float] = None,
        severity: AlertSeverity = AlertSeverity.WARNING,
        cooldown_seconds: float = 300
    ) -> AlertRule:
        """Create a new alert rule"""
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            condition=condition,
            metric_name=metric_name,
            operator=operator,
            threshold=threshold,
            severity=severity,
            cooldown_seconds=cooldown_seconds
        )
        
        with self._lock:
            self._rules[rule.id] = rule
        
        return rule
    
    def create_metric_rule(
        self,
        name: str,
        metric_name: str,
        operator: str,
        threshold: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        description: str = "",
        cooldown_seconds: float = 300
    ) -> AlertRule:
        """Create a rule based on metric threshold"""
        return self.create_rule(
            name=name,
            description=description,
            metric_name=metric_name,
            operator=operator,
            threshold=threshold,
            severity=severity,
            cooldown_seconds=cooldown_seconds
        )
    
    def register_notification_handler(
        self,
        severity: AlertSeverity,
        handler: Callable[[Alert], None]
    ) -> None:
        """Register handler for specific severity"""
        with self._lock:
            self._notification_handlers[severity].append(handler)
    
    def register_global_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register handler for all alerts"""
        with self._lock:
            self._global_handlers.append(handler)
    
    def evaluate(self, metric_values: Optional[Dict[str, float]] = None) -> List[Alert]:
        """Evaluate all rules and fire alerts"""
        fired_alerts = []
        current_time = time.time()
        metric_values = metric_values or {}
        
        with self._lock:
            for rule_id, rule in self._rules.items():
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if rule_id in self._last_fired:
                    elapsed = current_time - self._last_fired[rule_id]
                    if elapsed < rule.cooldown_seconds:
                        continue
                
                # Evaluate rule
                metric_value = metric_values.get(rule.metric_name) if rule.metric_name else None
                should_fire = rule.evaluate(metric_value)
                
                if should_fire:
                    # Create alert
                    alert = Alert(
                        id=str(uuid.uuid4()),
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.description or 'Alert triggered'}",
                        timestamp=current_time,
                        value=metric_value,
                        threshold=rule.threshold
                    )
                    
                    self._alerts[alert.id] = alert
                    self._alert_history.append(alert)
                    self._last_fired[rule_id] = current_time
                    fired_alerts.append(alert)
                    
                    # Notify handlers
                    self._notify_handlers(alert)
        
        return fired_alerts
    
    def _notify_handlers(self, alert: Alert) -> None:
        """Notify all handlers of an alert"""
        # Severity-specific handlers
        for handler in self._notification_handlers.get(alert.severity, []):
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
        
        # Global handlers
        for handler in self._global_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    def acknowledge(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert"""
        with self._lock:
            if alert_id not in self._alerts:
                return False
            
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            alert.acknowledged_by = acknowledged_by
            return True
    
    def resolve(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self._lock:
            if alert_id not in self._alerts:
                return False
            
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            return True
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get active (firing) alerts"""
        with self._lock:
            alerts = [
                a for a in self._alerts.values()
                if a.status in [AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED]
            ]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_alert_history(
        self,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alert history"""
        alerts = list(self._alert_history)
        
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        if until:
            alerts = [a for a in alerts if a.timestamp <= until]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        with self._lock:
            active = [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]
            acknowledged = [a for a in self._alerts.values() if a.status == AlertStatus.ACKNOWLEDGED]
            resolved = [a for a in self._alerts.values() if a.status == AlertStatus.RESOLVED]
            
            by_severity = {}
            for severity in AlertSeverity:
                by_severity[severity.value] = len([
                    a for a in active if a.severity == severity
                ])
            
            return {
                "total_rules": len(self._rules),
                "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                "active_alerts": len(active),
                "acknowledged_alerts": len(acknowledged),
                "resolved_alerts": len(resolved),
                "by_severity": by_severity,
            }


# Global alert manager instance
alert_manager = AlertManager()


# Pre-defined alert rules
def setup_default_alerts() -> None:
    """Setup common alert rules"""
    # CPU alerts
    alert_manager.create_metric_rule(
        name="High CPU Usage",
        metric_name="system_cpu_usage",
        operator="gt",
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        description="CPU usage above 80%"
    )
    
    alert_manager.create_metric_rule(
        name="Critical CPU Usage",
        metric_name="system_cpu_usage",
        operator="gt",
        threshold=95.0,
        severity=AlertSeverity.CRITICAL,
        description="CPU usage above 95%"
    )
    
    # Memory alerts
    alert_manager.create_metric_rule(
        name="High Memory Usage",
        metric_name="system_memory_usage",
        operator="gt",
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        description="Memory usage above 80%"
    )
    
    # Strategy P&L alerts
    alert_manager.create_metric_rule(
        name="Large Drawdown",
        metric_name="strategy_drawdown",
        operator="gt",
        threshold=10.0,
        severity=AlertSeverity.WARNING,
        description="Drawdown exceeds 10%"
    )
    
    # Execution alerts
    alert_manager.create_metric_rule(
        name="High Slippage",
        metric_name="slippage_bps",
        operator="gt",
        threshold=5.0,
        severity=AlertSeverity.WARNING,
        description="Slippage exceeds 5 bps"
    )
    
    # Model drift alerts
    alert_manager.create_metric_rule(
        name="Model Drift Detected",
        metric_name="model_drift",
        operator="gt",
        threshold=0.7,
        severity=AlertSeverity.WARNING,
        description="Model drift score elevated"
    )
