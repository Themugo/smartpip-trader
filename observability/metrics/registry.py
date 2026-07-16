"""
Metrics Registry
================

Registry for managing and querying metrics across the platform.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta


@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    metric_type: str  # counter, gauge, histogram, summary
    description: str = ""
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class MetricsRegistry:
    """
    Central registry for all metrics with time-series storage.
    
    Features:
    - Metric definitions and metadata
    - Time-series data storage
    - Aggregation queries
    - Historical data retention
    """
    
    def __init__(self, retention_hours: int = 24):
        self._metrics: Dict[str, MetricDefinition] = {}
        self._data: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10000)))
        self._retention_hours = retention_hours
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def register_metric(
        self,
        name: str,
        metric_type: str,
        description: str = "",
        unit: str = "",
        labels: Optional[List[str]] = None
    ) -> MetricDefinition:
        """Register a new metric"""
        with self._lock:
            if name in self._metrics:
                return self._metrics[name]
            
            definition = MetricDefinition(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                labels=labels or []
            )
            self._metrics[name] = definition
            return definition
    
    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value"""
        with self._lock:
            label_key = self._labels_to_key(labels)
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            self._data[name][label_key].append(point)
            
            # Notify subscribers
            for callback in self._subscribers.get(name, []):
                try:
                    callback(name, value, labels)
                except Exception:
                    pass
    
    def query(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 1000
    ) -> List[MetricPoint]:
        """Query metric values"""
        with self._lock:
            label_key = self._labels_to_key(labels)
            
            if name not in self._data:
                return []
            
            points = list(self._data[name].get(label_key, []))
            
            # Filter by time range
            if since:
                points = [p for p in points if p.timestamp >= since]
            if until:
                points = [p for p in points if p.timestamp <= until]
            
            # Apply limit
            return points[-limit:]
    
    def query_aggregated(
        self,
        name: str,
        since: Optional[float] = None,
        until: Optional[float] = None,
        aggregation: str = "avg"  # avg, sum, min, max, count
    ) -> float:
        """Query aggregated metric value"""
        points = self.query(name, since=since, until=until, limit=10000)
        
        if not points:
            return 0.0
        
        values = [p.value for p in points]
        
        if aggregation == "avg":
            return sum(values) / len(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "min":
            return min(values)
        elif aggregation == "max":
            return max(values)
        elif aggregation == "count":
            return len(values)
        elif aggregation == "last":
            return values[-1]
        
        return 0.0
    
    def query_percentile(
        self,
        name: str,
        percentile: float,
        since: Optional[float] = None,
        until: Optional[float] = None
    ) -> float:
        """Query percentile value"""
        points = self.query(name, since=since, until=until, limit=10000)
        
        if not points:
            return 0.0
        
        values = sorted([p.value for p in points])
        idx = int(len(values) * percentile / 100)
        idx = min(idx, len(values) - 1)
        return values[idx]
    
    def subscribe(
        self,
        name: str,
        callback: Callable[[str, float, Dict], None]
    ) -> None:
        """Subscribe to metric updates"""
        with self._lock:
            self._subscribers[name].append(callback)
    
    def cleanup_old_data(self) -> int:
        """Remove data older than retention period"""
        cutoff = time.time() - (self._retention_hours * 3600)
        removed = 0
        
        with self._lock:
            for metric_name, label_data in self._data.items():
                for label_key, points in label_data.items():
                    while points and points[0].timestamp < cutoff:
                        points.popleft()
                        removed += 1
        
        return removed
    
    def get_metric_info(self, name: str) -> Optional[MetricDefinition]:
        """Get metric definition"""
        with self._lock:
            return self._metrics.get(name)
    
    def list_metrics(self) -> List[MetricDefinition]:
        """List all registered metrics"""
        with self._lock:
            return list(self._metrics.values())
    
    def get_all_series(self, name: str) -> Dict[str, List[Dict]]:
        """Get all time series for a metric"""
        with self._lock:
            if name not in self._data:
                return {}
            
            result = {}
            for label_key, points in self._data[name].items():
                result[label_key] = [
                    {
                        "timestamp": p.timestamp,
                        "value": p.value,
                        "labels": p.labels
                    }
                    for p in points
                ]
            return result
    
    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


# Global registry instance
registry = MetricsRegistry()
