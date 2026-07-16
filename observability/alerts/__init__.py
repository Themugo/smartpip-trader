"""
Alerts Package
==============

Alert rules and anomaly detection.
"""

from .alert_manager import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus,
    alert_manager,
    setup_default_alerts,
)

from .anomaly_detector import (
    AnomalyDetector,
    AnomalyResult,
    anomaly_detector,
)

__all__ = [
    "AlertManager",
    "AlertRule",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "alert_manager",
    "setup_default_alerts",
    "AnomalyDetector",
    "AnomalyResult",
    "anomaly_detector",
]
