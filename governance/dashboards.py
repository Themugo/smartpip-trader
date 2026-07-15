"""
Governance Dashboards
====================

Dashboards for monitoring governance metrics.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class CalibrationStatus(Enum):
    """Calibration status levels"""
    WELL_CALIBRATED = "well_calibrated"
    SLIGHTLY_DRIFTED = "slightly_drifted"
    DRIFTED = "drifted"
    SIGNIFICANTLY_DRIFTED = "significantly_drifted"


class ModelHealthStatus(Enum):
    """Model health status"""
    HEALTHY = "healthy"
    DEGRADING = "degrading"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class StrategyHealthStatus(Enum):
    """Strategy health status"""
    OPTIMAL = "optimal"
    ACCEPTABLE = "acceptable"
    MARGINAL = "marginal"
    POOR = "poor"


@dataclass
class CalibrationMetric:
    """Calibration metric"""
    timestamp: datetime
    predicted_confidence: float
    actual_confidence: float
    error: float  # predicted - actual
    drift_score: float


@dataclass
class ModelHealthMetric:
    """Model health metric"""
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    latency_ms: float
    error_rate: float


@dataclass
class StrategyHealthMetric:
    """Strategy health metric"""
    timestamp: datetime
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    avg_trade_pnl: float


@dataclass
class DeploymentRecord:
    """Deployment record"""
    deployment_id: str
    timestamp: datetime
    version: str
    component: str  # model, strategy, config
    status: str  # deployed, rolled_back, failed
    deployed_by: str
    environment: str
    changes: List[str]


@dataclass
class ConfigChange:
    """Configuration change"""
    change_id: str
    timestamp: datetime
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: str
    reason: str
    approved_by: Optional[str]


class CalibrationDriftDashboard:
    """
    Dashboard for monitoring calibration drift.
    """
    
    def __init__(self):
        self.metrics: List[CalibrationMetric] = []
        self.drift_threshold = 0.1  # 10% drift threshold
    
    def record(self, predicted: float, actual: float) -> CalibrationMetric:
        """Record a calibration measurement"""
        metric = CalibrationMetric(
            timestamp=datetime.now(),
            predicted_confidence=predicted,
            actual_confidence=actual,
            error=predicted - actual,
            drift_score=abs(predicted - actual)
        )
        self.metrics.append(metric)
        
        # Keep last 1000 metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]
        
        return metric
    
    def get_status(self) -> CalibrationStatus:
        """Get current calibration status"""
        if len(self.metrics) < 10:
            return CalibrationStatus.UNKNOWN
        
        recent = self.metrics[-20:]
        avg_error = np.mean([m.error for m in recent])
        avg_drift = np.mean([m.drift_score for m in recent])
        
        if abs(avg_drift) < 0.02:
            return CalibrationStatus.WELL_CALIBRATED
        elif abs(avg_drift) < 0.05:
            return CalibrationStatus.SLIGHTLY_DRIFTED
        elif abs(avg_drift) < 0.10:
            return CalibrationStatus.DRIFTED
        else:
            return CalibrationStatus.SIGNIFICANTLY_DRIFTED
    
    def get_trend(self) -> Dict[str, Any]:
        """Get calibration trend"""
        if len(self.metrics) < 2:
            return {"trend": "INSUFFICIENT_DATA"}
        
        # Compare first half vs second half
        mid = len(self.metrics) // 2
        first_half = self.metrics[:mid]
        second_half = self.metrics[mid:]
        
        first_avg = np.mean([m.drift_score for m in first_half])
        second_avg = np.mean([m.drift_score for m in second_half])
        
        drift = second_avg - first_avg
        
        if abs(drift) < 0.01:
            trend = "STABLE"
        elif drift > 0:
            trend = "WORSENING"
        else:
            trend = "IMPROVING"
        
        return {
            "trend": trend,
            "first_half_avg_error": first_avg,
            "second_half_avg_error": second_avg,
            "drift_rate": drift,
            "current_status": self.get_status().value
        }
    
    def get_metrics(self, hours: int = 24) -> List[CalibrationMetric]:
        """Get metrics for time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics if m.timestamp >= cutoff]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        status = self.get_status()
        trend = self.get_trend()
        
        recent = self.metrics[-100:] if self.metrics else []
        
        return {
            "status": status.value,
            "trend": trend,
            "metrics_count": len(self.metrics),
            "recent_avg_error": np.mean([m.error for m in recent]) if recent else 0,
            "recent_avg_drift": np.mean([m.drift_score for m in recent]) if recent else 0,
            "alerts": self._generate_alerts(status, trend)
        }
    
    def _generate_alerts(
        self,
        status: CalibrationStatus,
        trend: Dict[str, Any]
    ) -> List[str]:
        """Generate alerts for calibration issues"""
        alerts = []
        
        if status == CalibrationStatus.SIGNIFICANTLY_DRIFTED:
            alerts.append("CRITICAL: Significant calibration drift detected")
        elif status == CalibrationStatus.DRIFTED:
            alerts.append("WARNING: Calibration drift detected")
        
        if trend.get("trend") == "WORSENING" and trend.get("drift_rate", 0) > 0.02:
            alerts.append("WARNING: Calibration is worsening")
        
        return alerts


class ModelHealthDashboard:
    """
    Dashboard for monitoring model health.
    """
    
    def __init__(self):
        self.metrics: List[ModelHealthMetric] = []
        self.model_id: Optional[str] = None
    
    def record(
        self,
        accuracy: float,
        precision: float,
        recall: float,
        f1_score: float,
        latency_ms: float,
        error_rate: float
    ) -> ModelHealthMetric:
        """Record a health measurement"""
        metric = ModelHealthMetric(
            timestamp=datetime.now(),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            latency_ms=latency_ms,
            error_rate=error_rate
        )
        self.metrics.append(metric)
        return metric
    
    def get_status(self) -> ModelHealthStatus:
        """Get current model health status"""
        if len(self.metrics) < 5:
            return ModelHealthStatus.UNKNOWN
        
        recent = self.metrics[-20:]
        avg_accuracy = np.mean([m.accuracy for m in recent])
        avg_error_rate = np.mean([m.error_rate for m in recent])
        
        if avg_accuracy > 0.90 and avg_error_rate < 0.05:
            return ModelHealthStatus.HEALTHY
        elif avg_accuracy > 0.75 and avg_error_rate < 0.15:
            return ModelHealthStatus.DEGRADING
        else:
            return ModelHealthStatus.UNHEALTHY
    
    def get_performance_trend(self) -> Dict[str, Any]:
        """Get performance trend"""
        if len(self.metrics) < 10:
            return {"trend": "INSUFFICIENT_DATA"}
        
        mid = len(self.metrics) // 2
        first = self.metrics[:mid]
        second = self.metrics[mid:]
        
        return {
            "accuracy_trend": np.mean([m.accuracy for m in second]) - np.mean([m.accuracy for m in first]),
            "latency_trend": np.mean([m.latency_ms for m in second]) - np.mean([m.latency_ms for m in first]),
            "error_rate_trend": np.mean([m.error_rate for m in second]) - np.mean([m.error_rate for m in first])
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        recent = self.metrics[-50:] if self.metrics else []
        
        return {
            "status": self.get_status().value,
            "model_id": self.model_id,
            "metrics_count": len(self.metrics),
            "current_metrics": {
                "accuracy": recent[-1].accuracy if recent else 0,
                "f1_score": recent[-1].f1_score if recent else 0,
                "latency_ms": recent[-1].latency_ms if recent else 0,
                "error_rate": recent[-1].error_rate if recent else 0
            },
            "averages": {
                "accuracy": np.mean([m.accuracy for m in recent]) if recent else 0,
                "f1_score": np.mean([m.f1_score for m in recent]) if recent else 0,
                "latency_ms": np.mean([m.latency_ms for m in recent]) if recent else 0,
                "error_rate": np.mean([m.error_rate for m in recent]) if recent else 0
            },
            "performance_trend": self.get_performance_trend()
        }


class StrategyHealthDashboard:
    """
    Dashboard for monitoring strategy health.
    """
    
    def __init__(self):
        self.metrics: List[StrategyHealthMetric] = []
        self.strategy_id: Optional[str] = None
    
    def record(
        self,
        total_return: float,
        sharpe_ratio: float,
        max_drawdown: float,
        win_rate: float,
        trade_count: int,
        avg_trade_pnl: float
    ) -> StrategyHealthMetric:
        """Record a health measurement"""
        metric = StrategyHealthMetric(
            timestamp=datetime.now(),
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            avg_trade_pnl=avg_trade_pnl
        )
        self.metrics.append(metric)
        return metric
    
    def get_status(self) -> StrategyHealthStatus:
        """Get current strategy health status"""
        if len(self.metrics) < 3:
            return StrategyHealthStatus.ACCEPTABLE  # Default
        
        recent = self.metrics[-10:]
        avg_sharpe = np.mean([m.sharpe_ratio for m in recent])
        avg_dd = np.mean([m.max_drawdown for m in recent])
        avg_return = np.mean([m.total_return for m in recent])
        
        if avg_sharpe > 1.5 and avg_dd < 0.10 and avg_return > 0.05:
            return StrategyHealthStatus.OPTIMAL
        elif avg_sharpe > 0.8 and avg_dd < 0.20:
            return StrategyHealthStatus.ACCEPTABLE
        elif avg_sharpe > 0.3:
            return StrategyHealthStatus.MARGINAL
        else:
            return StrategyHealthStatus.POOR
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        recent = self.metrics[-50:] if self.metrics else []
        
        return {
            "status": self.get_status().value,
            "strategy_id": self.strategy_id,
            "metrics_count": len(self.metrics),
            "current_metrics": {
                "total_return": recent[-1].total_return if recent else 0,
                "sharpe_ratio": recent[-1].sharpe_ratio if recent else 0,
                "max_drawdown": recent[-1].max_drawdown if recent else 0,
                "win_rate": recent[-1].win_rate if recent else 0
            },
            "averages": {
                "total_return": np.mean([m.total_return for m in recent]) if recent else 0,
                "sharpe_ratio": np.mean([m.sharpe_ratio for m in recent]) if recent else 0,
                "max_drawdown": np.mean([m.max_drawdown for m in recent]) if recent else 0,
                "win_rate": np.mean([m.win_rate for m in recent]) if recent else 0
            }
        }


class DeploymentHistoryDashboard:
    """
    Dashboard for deployment history.
    """
    
    def __init__(self):
        self.deployments: List[DeploymentRecord] = []
    
    def record_deployment(
        self,
        version: str,
        component: str,
        status: str,
        deployed_by: str,
        environment: str,
        changes: List[str]
    ) -> DeploymentRecord:
        """Record a deployment"""
        record = DeploymentRecord(
            deployment_id=str(uuid4()),
            timestamp=datetime.now(),
            version=version,
            component=component,
            status=status,
            deployed_by=deployed_by,
            environment=environment,
            changes=changes
        )
        self.deployments.append(record)
        return record
    
    def record_rollback(self, deployment_id: str, reason: str) -> None:
        """Record a rollback"""
        for d in self.deployments:
            if d.deployment_id == deployment_id:
                d.status = "rolled_back"
                d.changes.append(f"Rolled back: {reason}")
                break
    
    def get_deployments(
        self,
        component: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50
    ) -> List[DeploymentRecord]:
        """Get deployment history"""
        filtered = self.deployments
        
        if component:
            filtered = [d for d in filtered if d.component == component]
        
        if environment:
            filtered = [d for d in filtered if d.environment == environment]
        
        return sorted(filtered, key=lambda d: d.timestamp, reverse=True)[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get deployment statistics"""
        if not self.deployments:
            return {"total": 0}
        
        total = len(self.deployments)
        successful = sum(1 for d in self.deployments if d.status == "deployed")
        failed = sum(1 for d in self.deployments if d.status == "failed")
        rolled_back = sum(1 for d in self.deployments if d.status == "rolled_back")
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "rolled_back": rolled_back,
            "success_rate": successful / total if total > 0 else 0,
            "rollback_rate": rolled_back / total if total > 0 else 0
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        recent = self.deployments[-20:] if self.deployments else []
        
        return {
            "statistics": self.get_statistics(),
            "recent_deployments": [
                {
                    "id": d.deployment_id,
                    "timestamp": d.timestamp.isoformat(),
                    "version": d.version,
                    "component": d.component,
                    "status": d.status,
                    "environment": d.environment
                }
                for d in sorted(recent, key=lambda x: x.timestamp, reverse=True)
            ]
        }


class ConfigurationChangesDashboard:
    """
    Dashboard for configuration changes.
    """
    
    def __init__(self):
        self.changes: List[ConfigChange] = []
        self._change_listeners: List[callable] = []
    
    def record_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        reason: str,
        approved_by: Optional[str] = None
    ) -> ConfigChange:
        """Record a configuration change"""
        change = ConfigChange(
            change_id=str(uuid4()),
            timestamp=datetime.now(),
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            reason=reason,
            approved_by=approved_by
        )
        self.changes.append(change)
        
        # Notify listeners
        for listener in self._change_listeners:
            listener(change)
        
        return change
    
    def add_change_listener(self, listener: callable) -> None:
        """Add a listener for configuration changes"""
        self._change_listeners.append(listener)
    
    def get_changes(
        self,
        config_key: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ConfigChange]:
        """Get configuration changes"""
        filtered = self.changes
        
        if config_key:
            filtered = [c for c in filtered if c.config_key == config_key]
        
        if since:
            filtered = [c for c in filtered if c.timestamp >= since]
        
        return sorted(filtered, key=lambda c: c.timestamp, reverse=True)[:limit]
    
    def get_value_history(self, config_key: str) -> List[Dict[str, Any]]:
        """Get full history of a config key"""
        changes = [c for c in self.changes if c.config_key == config_key]
        changes = sorted(changes, key=lambda c: c.timestamp)
        
        return [
            {
                "timestamp": c.timestamp.isoformat(),
                "value": c.new_value,
                "changed_by": c.changed_by,
                "reason": c.reason
            }
            for c in changes
        ]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        recent = self.changes[-20:] if self.changes else []
        
        # Group by config key
        by_key = {}
        for c in self.changes:
            by_key[c.config_key] = by_key.get(c.config_key, 0) + 1
        
        return {
            "total_changes": len(self.changes),
            "unique_keys": len(by_key),
            "most_changed": sorted(by_key.items(), key=lambda x: x[1], reverse=True)[:10],
            "recent_changes": [
                {
                    "id": c.change_id,
                    "timestamp": c.timestamp.isoformat(),
                    "key": c.config_key,
                    "old_value": str(c.old_value)[:50],
                    "new_value": str(c.new_value)[:50],
                    "changed_by": c.changed_by,
                    "approved_by": c.approved_by
                }
                for c in sorted(recent, key=lambda x: x.timestamp, reverse=True)
            ]
        }
