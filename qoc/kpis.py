"""
Operational KPIs
================

Track and report operational KPIs.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class KPISnapshot:
    """Snapshot of KPI values"""
    timestamp: float
    values: Dict[str, float]


class OperationalKPIs:
    """
    Operational Key Performance Indicators.
    
    Tracks:
    - Deployment Frequency
    - Mean Time Between Failures (MTBF)
    - Mean Time To Recovery (MTTR)
    - Prediction Calibration
    - Decision Quality
    - Expected Value
    - Drawdown
    - System Availability
    - Replay Accuracy
    - Strategy Stability
    - Model Drift
    - Resource Utilization
    """
    
    def __init__(self, window_size: int = 1000):
        self._window_size = window_size
        
        # KPI values over time
        self._history: Dict[str, deque] = {}
        
        # Current values
        self._current: Dict[str, float] = {}
        
        # Incident tracking
        self._incidents: List[Dict] = []
        self._last_failure_time: Optional[float] = None
        
        # Initialize metrics
        self._init_metrics()
    
    def _init_metrics(self) -> None:
        """Initialize metric tracking"""
        metrics = [
            "deployment_frequency",  # deployments per day
            "mtbf_hours",  # mean time between failures
            "mttr_minutes",  # mean time to recovery
            "prediction_calibration",  # calibration error (lower is better)
            "decision_quality",  # 0-1 score
            "expected_value",  # expected return
            "max_drawdown",  # current max drawdown
            "system_availability",  # uptime percentage
            "replay_accuracy",  # replay match rate
            "strategy_stability",  # strategy consistency
            "model_drift",  # drift from baseline
            "cpu_utilization",
            "memory_utilization",
            "latency_p50_ms",
            "latency_p95_ms",
            "latency_p99_ms",
        ]
        
        for metric in metrics:
            self._history[metric] = deque(maxlen=self._window_size)
    
    def record(self, metric: str, value: float) -> None:
        """Record a metric value"""
        if metric not in self._history:
            self._history[metric] = deque(maxlen=self._window_size)
        
        self._history[metric].append(KPISnapshot(
            timestamp=time.time(),
            values={metric: value}
        ))
        
        self._current[metric] = value
    
    def record_incident(self, incident: Dict) -> None:
        """Record an incident"""
        incident["started_at"] = time.time()
        self._incidents.append(incident)
        
        if incident.get("status") == "resolved":
            self._resolve_incident(incident)
    
    def _resolve_incident(self, incident: Dict) -> None:
        """Resolve an incident and calculate metrics"""
        if "started_at" not in incident:
            return
        
        # Update failure tracking
        if self._last_failure_time:
            mtbf = (time.time() - self._last_failure_time) / 3600  # hours
            self.record("mtbf_hours", mtbf)
        
        self._last_failure_time = time.time()
        
        # Calculate MTTR
        duration = time.time() - incident["started_at"]
        mttr = duration / 60  # minutes
        self.record("mttr_minutes", mttr)
    
    def get_current(self, metric: str) -> Optional[float]:
        """Get current value of a metric"""
        return self._current.get(metric)
    
    def get_average(
        self,
        metric: str,
        since: Optional[float] = None
    ) -> Optional[float]:
        """Get average value of a metric"""
        if metric not in self._history or not self._history[metric]:
            return None
        
        values = self._history[metric]
        
        if since:
            values = [v for v in values if v.timestamp >= since]
        
        if not values:
            return None
        
        return sum(v.values.get(metric, 0) for v in values) / len(values)
    
    def get_percentile(
        self,
        metric: str,
        percentile: float
    ) -> Optional[float]:
        """Get percentile value of a metric"""
        if metric not in self._history or not self._history[metric]:
            return None
        
        values = sorted(v.values.get(metric, 0) for v in self._history[metric])
        
        if not values:
            return None
        
        idx = int(len(values) * percentile / 100)
        return values[min(idx, len(values) - 1)]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get KPI summary"""
        now = time.time()
        day_ago = now - 86400
        week_ago = now - 604800
        
        return {
            "timestamp": now,
            
            # Current values
            "current": self._current.copy(),
            
            # Averages (last 24h)
            "last_24h": {
                metric: self.get_average(metric, since=day_ago)
                for metric in self._history.keys()
            },
            
            # Averages (last 7 days)
            "last_7d": {
                metric: self.get_average(metric, since=week_ago)
                for metric in self._history.keys()
            },
            
            # Percentiles (last 24h)
            "latency": {
                "p50": self.get_percentile("latency_p50_ms", 50),
                "p95": self.get_percentile("latency_p95_ms", 95),
                "p99": self.get_percentile("latency_p99_ms", 99),
            },
            
            # Incidents
            "incidents": {
                "total": len(self._incidents),
                "last_24h": len([i for i in self._incidents if i.get("started_at", 0) >= day_ago]),
                "last_7d": len([i for i in self._incidents if i.get("started_at", 0) >= week_ago]),
            },
            
            # Reliability
            "reliability": {
                "mtbf_hours": self.get_average("mtbf_hours"),
                "mttr_minutes": self.get_average("mttr_minutes"),
                "availability": self.get_average("system_availability"),
            },
            
            # Trading
            "trading": {
                "expected_value": self.get_average("expected_value"),
                "max_drawdown": self.get_current("max_drawdown"),
                "prediction_calibration": self.get_average("prediction_calibration"),
            },
            
            # Model
            "model": {
                "drift": self.get_current("model_drift"),
                "accuracy": self.get_average("replay_accuracy"),
            },
        }
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get KPI dashboard data"""
        summary = self.get_summary()
        
        # Determine status of each KPI
        statuses = {}
        
        # Availability
        availability = summary["current"].get("system_availability", 1.0)
        statuses["availability"] = "good" if availability >= 0.99 else "warning" if availability >= 0.95 else "critical"
        
        # Latency
        latency_p99 = summary["latency"].get("p99")
        if latency_p99:
            statuses["latency"] = "good" if latency_p99 < 100 else "warning" if latency_p99 < 500 else "critical"
        
        # MTBF
        mtbf = summary["reliability"].get("mtbf_hours")
        if mtbf:
            statuses["mtbf"] = "good" if mtbf >= 168 else "warning" if mtbf >= 24 else "critical"  # 1 week vs 1 day
        
        # MTTR
        mttr = summary["reliability"].get("mttr_minutes")
        if mttr:
            statuses["mttr"] = "good" if mttr < 30 else "warning" if mttr < 120 else "critical"
        
        # Model drift
        drift = summary["model"].get("drift", 0)
        statuses["drift"] = "good" if drift < 0.05 else "warning" if drift < 0.1 else "critical"
        
        return {
            "summary": summary,
            "statuses": statuses,
            "timestamp": time.time(),
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external systems"""
        return {
            metric: [
                {"timestamp": s.timestamp, "value": s.values.get(metric, 0)}
                for s in snapshots
            ]
            for metric, snapshots in self._history.items()
        }
