"""
Anomaly Detection and Security Alerting for SmartPip Trading System
Detects unusual patterns and triggers security alerts
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta, timedelta
from typing import Dict, Any, List, Optional, Callable
from collections import deque
import logging
from monitoring.opentelemetry_config import security_metrics

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in trading metrics and system behavior"""
    
    def __init__(self, window_size: int = 100, threshold_std: float = 3.0):
        """
        Initialize anomaly detector
        
        Args:
            window_size: Size of the sliding window for statistical analysis
            threshold_std: Number of standard deviations for anomaly threshold
        """
        self.window_size = window_size
        self.threshold_std = threshold_std
        
        # Data windows for different metrics
        self.trade_profits = deque(maxlen=window_size)
        self.trade_durations = deque(maxlen=window_size)
        self.api_latencies = deque(maxlen=window_size)
        self.error_rates = deque(maxlen=window_size)
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for anomaly alerts"""
        self.alert_callbacks.append(callback)
    
    def _trigger_alert(self, alert_type: str, severity: str, details: Dict[str, Any]):
        """Trigger alert to all registered callbacks"""
        alert = {
            "type": alert_type,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def detect_profit_anomaly(self, profit: float) -> Optional[Dict[str, Any]]:
        """Detect unusual profit patterns"""
        self.trade_profits.append(profit)
        
        if len(self.trade_profits) < self.window_size:
            return None
        
        # Calculate statistics
        profits = np.array(self.trade_profits)
        mean = np.mean(profits)
        std = np.std(profits)
        
        # Check for anomaly
        if std > 0:
            z_score = abs(profit - mean) / std
            if z_score > self.threshold_std:
                self._trigger_alert(
                    "profit_anomaly",
                    "high" if z_score > 5 else "medium",
                    {
                        "profit": profit,
                        "mean": mean,
                        "std": std,
                        "z_score": z_score,
                        "direction": "unusual_loss" if profit < mean else "unusual_gain"
                    }
                )
                security_metrics.record_xss_attempt("profit_anomaly")
                return {"anomaly": True, "z_score": z_score, "type": "profit"}
        
        return None
    
    def detect_duration_anomaly(self, duration: float) -> Optional[Dict[str, Any]]:
        """Detect unusual trade execution durations"""
        self.trade_durations.append(duration)
        
        if len(self.trade_durations) < self.window_size:
            return None
        
        durations = np.array(self.trade_durations)
        mean = np.mean(durations)
        std = np.std(durations)
        
        if std > 0:
            z_score = abs(duration - mean) / std
            if z_score > self.threshold_std:
                self._trigger_alert(
                    "duration_anomaly",
                    "medium",
                    {
                        "duration": duration,
                        "mean": mean,
                        "std": std,
                        "z_score": z_score
                    }
                )
                return {"anomaly": True, "z_score": z_score, "type": "duration"}
        
        return None
    
    def detect_latency_anomaly(self, latency: float) -> Optional[Dict[str, Any]]:
        """Detect unusual API latencies"""
        self.api_latencies.append(latency)
        
        if len(self.api_latencies) < self.window_size:
            return None
        
        latencies = np.array(self.api_latencies)
        mean = np.mean(latencies)
        std = np.std(latencies)
        
        if std > 0:
            z_score = abs(latency - mean) / std
            if z_score > self.threshold_std:
                self._trigger_alert(
                    "latency_anomaly",
                    "high" if z_score > 5 else "medium",
                    {
                        "latency": latency,
                        "mean": mean,
                        "std": std,
                        "z_score": z_score
                    }
                )
                return {"anomaly": True, "z_score": z_score, "type": "latency"}
        
        return None
    
    def detect_error_spike(self, error_count: int, total_requests: int) -> Optional[Dict[str, Any]]:
        """Detect error rate spikes"""
        error_rate = error_count / total_requests if total_requests > 0 else 0
        self.error_rates.append(error_rate)
        
        if len(self.error_rates) < self.window_size:
            return None
        
        rates = np.array(self.error_rates)
        mean = np.mean(rates)
        std = np.std(rates)
        
        if std > 0:
            z_score = abs(error_rate - mean) / std
            if z_score > self.threshold_std and error_rate > 0.1:  # 10% error threshold
                self._trigger_alert(
                    "error_spike",
                    "critical",
                    {
                        "error_rate": error_rate,
                        "mean": mean,
                        "std": std,
                        "z_score": z_score,
                        "error_count": error_count,
                        "total_requests": total_requests
                    }
                )
                return {"anomaly": True, "z_score": z_score, "type": "error_spike"}
        
        return None
    
    def detect_consecutive_losses(self, losses: int, threshold: int = 5) -> Optional[Dict[str, Any]]:
        """Detect consecutive loss streaks"""
        if losses >= threshold:
            self._trigger_alert(
                "consecutive_losses",
                "high" if losses >= 10 else "medium",
                {
                    "consecutive_losses": losses,
                    "threshold": threshold
                }
            )
            return {"anomaly": True, "losses": losses, "type": "consecutive_losses"}
        
        return None
    
    def detect_rapid_trading(self, trade_count: int, time_window: int, threshold: int = 10) -> Optional[Dict[str, Any]]:
        """Detect unusually rapid trading (potential bot or attack)"""
        if trade_count > threshold:
            self._trigger_alert(
                "rapid_trading",
                "high",
                {
                    "trade_count": trade_count,
                    "time_window": time_window,
                    "threshold": threshold
                }
            )
            return {"anomaly": True, "trade_count": trade_count, "type": "rapid_trading"}
        
        return None


class SecurityAlertManager:
    """Manages security alerts and incident response"""
    
    def __init__(self):
        self.alert_history: List[Dict[str, Any]] = []
        self.active_incidents: Dict[str, Dict[str, Any]] = {}
        self.alert_thresholds = {
            "profit_anomaly": 5,  # alerts per hour
            "latency_anomaly": 10,
            "error_spike": 3,
            "consecutive_losses": 5
        }
    
    def handle_alert(self, alert: Dict[str, Any]):
        """Handle incoming security alert"""
        alert_type = alert["type"]
        severity = alert["severity"]
        
        # Add to history
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Check if this should trigger an incident
        self._check_incident_threshold(alert_type, severity)
        
        # Log alert
        logger.warning(f"Security alert: {alert_type} - {severity}")
        
        # Record metrics
        if alert_type == "xss_attempt":
            security_metrics.record_xss_attempt("anomaly_detection")
        elif alert_type == "sql_injection":
            security_metrics.record_sql_injection_attempt("anomaly_detection")
    
    def _check_incident_threshold(self, alert_type: str, severity: str):
        """Check if alert should trigger an incident"""
        # Count recent alerts of this type
        recent_alerts = [
            a for a in self.alert_history
            if a["type"] == alert_type
            and datetime.fromisoformat(a["timestamp"]) > datetime.now(timezone.utc) - timedelta(hours=1)
        ]
        
        threshold = self.alert_thresholds.get(alert_type, 10)
        
        if len(recent_alerts) >= threshold:
            self._create_incident(alert_type, severity, len(recent_alerts))
    
    def _create_incident(self, alert_type: str, severity: str, alert_count: int):
        """Create a security incident"""
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{alert_type}"
        
        self.active_incidents[incident_id] = {
            "id": incident_id,
            "type": alert_type,
            "severity": severity,
            "alert_count": alert_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "actions_taken": []
        }
        
        logger.critical(f"Security incident created: {incident_id}")
    
    def resolve_incident(self, incident_id: str, resolution: str):
        """Resolve a security incident"""
        if incident_id in self.active_incidents:
            self.active_incidents[incident_id]["status"] = "resolved"
            self.active_incidents[incident_id]["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self.active_incidents[incident_id]["resolution"] = resolution
            logger.info(f"Incident resolved: {incident_id}")
    
    def get_active_incidents(self) -> List[Dict[str, Any]]:
        """Get all active incidents"""
        return [
            incident for incident in self.active_incidents.values()
            if incident["status"] == "active"
        ]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified time period"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


class IncidentWorkflow:
    """Manages incident response workflows"""
    
    def __init__(self):
        self.workflows = {
            "profit_anomaly": self._profit_anomaly_workflow,
            "latency_anomaly": self._latency_anomaly_workflow,
            "error_spike": self._error_spike_workflow,
            "consecutive_losses": self._consecutive_losses_workflow,
            "rapid_trading": self._rapid_trading_workflow
        }
    
    def execute_workflow(self, incident_type: str, incident_data: Dict[str, Any]):
        """Execute incident response workflow"""
        workflow = self.workflows.get(incident_type)
        if workflow:
            return workflow(incident_data)
        else:
            logger.warning(f"No workflow defined for incident type: {incident_type}")
            return None
    
    def _profit_anomaly_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow for profit anomaly incidents"""
        actions = []
        
        # 1. Pause trading temporarily
        actions.append({"action": "pause_trading", "reason": "profit_anomaly_detected"})
        
        # 2. Review recent trades
        actions.append({"action": "review_recent_trades", "count": 20})
        
        # 3. Check market conditions
        actions.append({"action": "check_market_conditions", "market": "all"})
        
        # 4. Notify administrators
        actions.append({"action": "notify_admin", "severity": "high"})
        
        return {"workflow": "profit_anomaly", "actions": actions}
    
    def _latency_anomaly_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow for latency anomaly incidents"""
        actions = []
        
        # 1. Check API health
        actions.append({"action": "check_api_health"})
        
        # 2. Monitor system resources
        actions.append({"action": "monitor_resources"})
        
        # 3. Check network connectivity
        actions.append({"action": "check_network"})
        
        # 4. Scale if needed
        actions.append({"action": "check_scaling_needed"})
        
        return {"workflow": "latency_anomaly", "actions": actions}
    
    def _error_spike_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow for error spike incidents"""
        actions = []
        
        # 1. Pause trading immediately
        actions.append({"action": "pause_trading", "reason": "error_spike"})
        
        # 2. Check system logs
        actions.append({"action": "check_system_logs", "level": "error"})
        
        # 3. Verify database connectivity
        actions.append({"action": "check_database"})
        
        # 4. Verify API connectivity
        actions.append({"action": "check_api_connectivity"})
        
        # 5. Notify administrators
        actions.append({"action": "notify_admin", "severity": "critical"})
        
        return {"workflow": "error_spike", "actions": actions}
    
    def _consecutive_losses_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow for consecutive losses incidents"""
        actions = []
        
        # 1. Activate kill switch
        actions.append({"action": "activate_kill_switch", "reason": "consecutive_losses"})
        
        # 2. Review trading strategy
        actions.append({"action": "review_strategy"})
        
        # 3. Check market regime
        actions.append({"action": "check_market_regime"})
        
        # 4. Notify administrators
        actions.append({"action": "notify_admin", "severity": "high"})
        
        return {"workflow": "consecutive_losses", "actions": actions}
    
    def _rapid_trading_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Workflow for rapid trading incidents"""
        actions = []
        
        # 1. Activate kill switch
        actions.append({"action": "activate_kill_switch", "reason": "rapid_trading"})
        
        # 2. Check for unauthorized access
        actions.append({"action": "check_unauthorized_access"})
        
        # 3. Review API logs
        actions.append({"action": "review_api_logs"})
        
        # 4. Notify administrators
        actions.append({"action": "notify_admin", "severity": "critical"})
        
        return {"workflow": "rapid_trading", "actions": actions}


# Global instances
anomaly_detector = AnomalyDetector()
security_alert_manager = SecurityAlertManager()
incident_workflow = IncidentWorkflow()

# Connect components
anomaly_detector.add_alert_callback(security_alert_manager.handle_alert)
