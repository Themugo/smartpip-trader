"""
Risk Dashboard
==============

Live dashboard and historical trend analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    refresh_interval: int = 60  # seconds
    history_window: int = 100  # Number of data points
    trend_window: int = 20  # For trend calculation


class RiskDashboard:
    """
    Provides live dashboard data and historical trends.
    """
    
    def __init__(self, registry: Any):
        self.registry = registry
        self.config = DashboardConfig()
        
        # Current state cache
        self.current_metrics: Dict[str, Any] = {}
        self.alerts: List[Dict[str, Any]] = []
        
        # Historical data
        self.portfolio_history: List[float] = []
        self.drawdown_history: List[float] = []
        self.risk_score_history: List[int] = []
        self.pnl_history: List[float] = []
        self.timestamps: List[datetime] = []
    
    def update(self, metrics: Any) -> None:
        """Update dashboard with new metrics"""
        # Store current metrics
        self.current_metrics = {
            "portfolio_value": metrics.portfolio_value,
            "daily_pnl": metrics.daily_pnl,
            "daily_return": metrics.daily_return,
            "current_drawdown": metrics.current_drawdown,
            "max_drawdown": metrics.max_drawdown,
            "risk_score": metrics.risk_score,
            "var_95": metrics.var_95,
            "cvar_95": metrics.cvar_95,
            "volatility": metrics.volatility_30d,
            "sharpe_ratio": metrics.sharpe_ratio,
            "system_state": metrics.system_state.value if hasattr(metrics.system_state, 'value') else str(metrics.system_state),
            "concentration_risk": metrics.concentration_risk,
            "exposure_ratio": metrics.exposure_ratio,
            "positions_count": len(metrics.positions),
            "timestamp": metrics.timestamp.isoformat() if hasattr(metrics.timestamp, 'isoformat') else str(metrics.timestamp)
        }
        
        # Update histories
        self.portfolio_history.append(metrics.portfolio_value)
        self.drawdown_history.append(metrics.current_drawdown)
        self.risk_score_history.append(metrics.risk_score)
        self.pnl_history.append(metrics.daily_pnl)
        self.timestamps.append(datetime.now())
        
        # Trim to window
        max_points = self.config.history_window
        if len(self.portfolio_history) > max_points:
            self.portfolio_history = self.portfolio_history[-max_points:]
            self.drawdown_history = self.drawdown_history[-max_points:]
            self.risk_score_history = self.risk_score_history[-max_points:]
            self.pnl_history = self.pnl_history[-max_points:]
            self.timestamps = self.timestamps[-max_points:]
        
        # Check for alerts
        self._check_alerts(metrics)
    
    def _check_alerts(self, metrics: Any) -> None:
        """Check for alert conditions"""
        # High risk score alert
        if metrics.risk_score > 80:
            self._add_alert("HIGH_RISK", "CRITICAL", f"Risk score is {metrics.risk_score}")
        
        # Large drawdown alert
        if metrics.current_drawdown > 0.10:
            self._add_alert("DRAWDOWN", "WARNING", f"Drawdown is {metrics.current_drawdown:.1%}")
        
        # Circuit breaker alert
        # Would check circuit breaker state here
        
        # State change alerts
        state_alerts = {
            "CRITICAL": "CRITICAL",
            "KILLED": "CRITICAL",
            "ELEVATED": "WARNING"
        }
        state_str = metrics.system_state.value if hasattr(metrics.system_state, 'value') else str(metrics.system_state)
        if state_str in state_alerts:
            self._add_alert("STATE_CHANGE", state_alerts[state_str], f"System state: {state_str}")
    
    def _add_alert(self, alert_type: str, severity: str, message: str) -> None:
        """Add an alert"""
        # Check for duplicate
        for alert in self.alerts[-5:]:
            if alert["type"] == alert_type and alert["message"] == message:
                return
        
        alert = {
            "type": alert_type,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current dashboard state"""
        return {
            "metrics": self.current_metrics,
            "alerts": self.alerts[-10:],
            "summary": self._get_summary()
        }
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        if not self.portfolio_history:
            return {}
        
        return {
            "portfolio": {
                "current": self.portfolio_history[-1],
                "peak": max(self.portfolio_history) if self.portfolio_history else 0,
                "change_1h": self._calculate_change(1),
                "change_24h": self._calculate_change(24),
                "change_7d": self._calculate_change(24 * 7)
            },
            "risk": {
                "current_score": self.risk_score_history[-1] if self.risk_score_history else 50,
                "avg_score": np.mean(self.risk_score_history) if self.risk_score_history else 50,
                "max_score": max(self.risk_score_history) if self.risk_score_history else 50
            },
            "drawdown": {
                "current": self.drawdown_history[-1] if self.drawdown_history else 0,
                "max": max(self.drawdown_history) if self.drawdown_history else 0,
                "avg": np.mean(self.drawdown_history) if self.drawdown_history else 0
            },
            "pnl": {
                "daily": self.pnl_history[-1] if self.pnl_history else 0,
                "total": sum(self.pnl_history),
                "avg_daily": np.mean(self.pnl_history) if self.pnl_history else 0,
                "std_daily": np.std(self.pnl_history) if len(self.pnl_history) > 1 else 0
            }
        }
    
    def _calculate_change(self, hours: int) -> float:
        """Calculate change over time period"""
        if len(self.portfolio_history) < 2:
            return 0.0
        
        # Estimate points per hour
        points_per_hour = len(self.portfolio_history) / max(1, (datetime.now() - self.timestamps[0]).total_seconds() / 3600)
        
        points_back = int(hours * points_per_hour)
        if points_back >= len(self.portfolio_history):
            return 0.0
        
        current = self.portfolio_history[-1]
        past = self.portfolio_history[-points_back]
        
        if past > 0:
            return (current - past) / past
        
        return 0.0
    
    def get_historical_data(
        self,
        metric: str,
        period: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get historical data for a specific metric.
        
        Args:
            metric: Metric name (portfolio, drawdown, risk_score, pnl)
            period: Time period (1h, 24h, 7d, 30d)
        """
        period_hours = {
            "1h": 1,
            "24h": 24,
            "7d": 24 * 7,
            "30d": 24 * 30
        }
        
        hours = period_hours.get(period, 24)
        
        # Get appropriate history
        history_map = {
            "portfolio": self.portfolio_history,
            "drawdown": self.drawdown_history,
            "risk_score": self.risk_score_history,
            "pnl": self.pnl_history
        }
        
        history = history_map.get(metric, [])
        
        # Filter by time
        points_per_hour = len(self.timestamps) / max(1, (datetime.now() - self.timestamps[0]).total_seconds() / 3600) if self.timestamps else 1
        points_back = int(hours * points_per_hour)
        
        if points_back >= len(history):
            filtered_history = history
            filtered_timestamps = self.timestamps
        else:
            filtered_history = history[-points_back:]
            filtered_timestamps = self.timestamps[-points_back:]
        
        return {
            "metric": metric,
            "period": period,
            "data": filtered_history,
            "timestamps": [t.isoformat() for t in filtered_timestamps],
            "statistics": {
                "min": min(filtered_history) if filtered_history else 0,
                "max": max(filtered_history) if filtered_history else 0,
                "mean": np.mean(filtered_history) if filtered_history else 0,
                "std": np.std(filtered_history) if len(filtered_history) > 1 else 0
            }
        }
    
    def get_trend_analysis(self, metric: str = "risk_score") -> Dict[str, Any]:
        """Get trend analysis for a metric"""
        history_map = {
            "portfolio": self.portfolio_history,
            "drawdown": self.drawdown_history,
            "risk_score": self.risk_score_history,
            "pnl": self.pnl_history
        }
        
        history = history_map.get(metric, [])
        
        if len(history) < self.config.trend_window:
            return {"trend": "INSUFFICIENT_DATA", "direction": "unknown"}
        
        # Calculate linear regression
        window = history[-self.config.trend_window:]
        x = np.arange(len(window))
        slope, intercept = np.polyfit(x, window, 1)
        
        # Determine trend
        if abs(slope) < 0.01:  # Threshold for significance
            trend = "STABLE"
        elif slope > 0:
            trend = "IMPROVING" if metric in ["portfolio", "pnl"] else "WORSENING"
        else:
            trend = "WORSENING" if metric in ["portfolio", "pnl"] else "IMPROVING"
        
        return {
            "trend": trend,
            "slope": slope,
            "direction": "up" if slope > 0 else "down",
            "magnitude": abs(slope) * self.config.trend_window,
            "confidence": min(1.0, abs(slope) * 10)
        }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get position summary"""
        positions = self.current_metrics.get("positions", [])
        
        if not positions:
            return {"count": 0, "total_exposure": 0}
        
        return {
            "count": len(positions),
            "total_exposure": sum(abs(p.get("size", 0) * p.get("current_price", 0)) for p in positions),
            "avg_confidence": np.mean([p.get("confidence", 0) for p in positions]) if positions else 0,
            "long_count": sum(1 for p in positions if p.get("direction") == "LONG"),
            "short_count": sum(1 for p in positions if p.get("direction") == "SHORT")
        }
    
    def export_data(self, format: str = "json") -> str:
        """Export dashboard data"""
        data = {
            "export_time": datetime.now().isoformat(),
            "current_state": self.get_current_state(),
            "historical": {
                "portfolio": self.portfolio_history,
                "drawdown": self.drawdown_history,
                "risk_score": self.risk_score_history,
                "pnl": self.pnl_history,
                "timestamps": [t.isoformat() for t in self.timestamps]
            },
            "trends": {
                metric: self.get_trend_analysis(metric)
                for metric in ["portfolio", "drawdown", "risk_score", "pnl"]
            }
        }
        
        if format == "json":
            import json
            return json.dumps(data, indent=2)
        else:
            return str(data)
