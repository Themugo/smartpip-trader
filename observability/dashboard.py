"""
Observability Dashboard - System Monitoring

Comprehensive system monitoring and metrics collection.
"""

import logging
import psutil
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """A metric snapshot"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
        }


class ObservabilityDashboard:
    """
    Observability dashboard for system monitoring.
    
    Tracks:
    - CPU, Memory, GPU usage
    - Network latency
    - API/WebSocket health
    - Plugin health
    - Database health
    - Custom metrics
    """
    
    def __init__(self, retention_minutes: int = 60):
        self._retention_minutes = retention_minutes
        self._metrics: Dict[str, deque] = {}
        self._custom_metrics: Dict[str, Any] = {}
        
        # System metrics collection
        self._system_baseline = self._collect_system_baseline()
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric value"""
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=1000)
        
        snapshot = MetricSnapshot(
            timestamp=datetime.utcnow(),
            metric_name=name,
            value=value,
            unit=unit,
            tags=tags or {},
        )
        
        self._metrics[name].append(snapshot)
    
    def record_custom(self, key: str, value: Any) -> None:
        """Record a custom metric value"""
        self._custom_metrics[key] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_metric(
        self,
        name: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[MetricSnapshot]:
        """Get metric history"""
        if name not in self._metrics:
            return []
        
        snapshots = list(self._metrics[name])
        
        if since:
            snapshots = [s for s in snapshots if s.timestamp >= since]
        
        return snapshots[-limit:]
    
    def get_latest(self, name: str) -> Optional[MetricSnapshot]:
        """Get latest value for a metric"""
        if name not in self._metrics or not self._metrics[name]:
            return None
        return self._metrics[name][-1]
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        
        # Disk
        disk = psutil.disk_usage("/")
        
        # Network
        network = psutil.net_io_counters()
        
        # Process
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / (1024 * 1024)
        
        metrics = {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "memory_percent": memory_percent,
            "memory_used_mb": memory_used_mb,
            "disk_percent": disk.percent,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "process_memory_mb": process_memory_mb,
        }
        
        # Record metrics
        for name, value in metrics.items():
            unit = "percent" if "percent" in name else "mb" if "mb" in name else "bytes"
            self.record_metric(f"system.{name}", value, unit)
        
        return metrics
    
    def collect_ai_metrics(self) -> Dict[str, Any]:
        """Collect AI-specific metrics"""
        # These would come from AI core
        metrics = {
            "active_models": 1,
            "model_confidence": 75.0,
            "predictions_today": 0,
            "avg_latency_ms": 0,
        }
        
        for name, value in metrics.items():
            self.record_metric(f"ai.{name}", value)
        
        return metrics
    
    def collect_execution_metrics(self) -> Dict[str, Any]:
        """Collect execution metrics"""
        # These would come from execution engine
        metrics = {
            "orders_today": 0,
            "fills_today": 0,
            "avg_execution_latency_ms": 0,
            "slippage_bps": 0,
        }
        
        for name, value in metrics.items():
            self.record_metric(f"execution.{name}", value)
        
        return metrics
    
    def _collect_system_baseline(self) -> Dict[str, float]:
        """Collect baseline system metrics"""
        return {
            "cpu_count": psutil.cpu_count(),
            "total_memory_mb": psutil.virtual_memory().total / (1024 * 1024),
            "total_disk_gb": psutil.disk_usage("/").total / (1024 * 1024 * 1024),
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary for monitoring"""
        system = self.collect_system_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": system.get("cpu_percent", 0),
                "memory_percent": system.get("memory_percent", 0),
                "disk_percent": system.get("disk_percent", 0),
                "uptime_seconds": time.time() - psutil.Process().create_time(),
            },
            "ai": self.collect_ai_metrics(),
            "execution": self.collect_execution_metrics(),
            "custom_metrics": self._custom_metrics,
        }
    
    def get_all_metrics(self) -> Dict[str, List[MetricSnapshot]]:
        """Get all recorded metrics"""
        return {name: list(snapshots) for name, snapshots in self._metrics.items()}
    
    def get_metric_statistics(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        snapshots = self.get_metric(name)
        
        if not snapshots:
            return {}
        
        values = [s.value for s in snapshots]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
        }
