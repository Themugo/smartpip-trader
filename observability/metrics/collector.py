"""
Metrics Collector
================

Prometheus-style metrics collection with counters, gauges, histograms, and summaries.
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricMetadata:
    """Metadata for a metric"""
    name: str
    description: str = ""
    unit: str = ""
    labels: List[str] = field(default_factory=list)


@dataclass
class MetricValue:
    """A single metric value"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class Counter:
    """A monotonically increasing counter"""
    
    def __init__(self, name: str, description: str = "", unit: str = "", labels: List[str] = None):
        self.name = name
        self.metadata = MetricMetadata(name, description, unit, labels or [])
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter"""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key] += amount
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current value"""
        key = self._labels_to_key(labels)
        with self._lock:
            return self._values.get(key, 0)
    
    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Gauge:
    """A value that can go up or down"""
    
    def __init__(self, name: str, description: str = "", unit: str = "", labels: List[str] = None):
        self.name = name
        self.metadata = MetricMetadata(name, description, unit, labels or [])
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value"""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key] = value
    
    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge"""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key] += amount
    
    def dec(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge"""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key] -= amount
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current value"""
        key = self._labels_to_key(labels)
        with self._lock:
            return self._values.get(key, 0)
    
    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Histogram:
    """A histogram of values"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None,
        buckets: List[float] = None
    ):
        self.name = name
        self.metadata = MetricMetadata(name, description, unit, labels or [])
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        self._counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._sums: Dict[str, float] = defaultdict(float)
        self._totals: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation"""
        key = self._labels_to_key(labels)
        with self._lock:
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1
            self._sums[key] += value
            self._totals[key] += 1
    
    def get_stats(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get histogram statistics"""
        key = self._labels_to_key(labels)
        with self._lock:
            total = self._totals.get(key, 0)
            if total == 0:
                return {"count": 0, "sum": 0, "avg": 0}
            
            sum_val = self._sums.get(key, 0)
            return {
                "count": total,
                "sum": sum_val,
                "avg": sum_val / total,
                "buckets": dict(self._counts.get(key, {}))
            }
    
    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Summary:
    """A summary of values with quantiles"""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None,
        quantiles: List[float] = None
    ):
        self.name = name
        self.metadata = MetricMetadata(name, description, unit, labels or [])
        self.quantiles = quantiles or [0.5, 0.9, 0.95, 0.99]
        self._values: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation"""
        key = self._labels_to_key(labels)
        with self._lock:
            self._values[key].append(value)
    
    def get_quantiles(self, labels: Optional[Dict[str, str]] = None) -> Dict[float, float]:
        """Get quantile values"""
        key = self._labels_to_key(labels)
        with self._lock:
            values = sorted(self._values.get(key, []))
            if not values:
                return {q: 0 for q in self.quantiles}
            
            result = {}
            for q in self.quantiles:
                idx = int(len(values) * q)
                idx = min(idx, len(values) - 1)
                result[q] = values[idx]
            return result
    
    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class MetricsCollector:
    """
    Central metrics collector with Prometheus-compatible interface.
    
    Supports:
    - Counters (monotonically increasing)
    - Gauges (up/down values)
    - Histograms (bucket distributions)
    - Summaries (quantile calculations)
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
        
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._summaries: Dict[str, Summary] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        # Pre-register common metrics
        self._register_default_metrics()
    
    def _register_default_metrics(self) -> None:
        """Register default system metrics"""
        # System metrics
        self.register_counter("system_cpu_usage", "CPU usage percentage", "percent")
        self.register_gauge("system_memory_usage", "Memory usage percentage", "percent")
        self.register_gauge("system_disk_usage", "Disk usage percentage", "percent")
        self.register_gauge("system_network_sent", "Network bytes sent", "bytes")
        self.register_gauge("system_network_recv", "Network bytes received", "bytes")
        
        # API metrics
        self.register_counter("api_requests_total", "Total API requests", "requests")
        self.register_histogram("api_request_duration", "API request duration", "seconds")
        
        # Business metrics
        self.register_counter("opportunities_total", "Total opportunities", "count")
        self.register_counter("opportunities_accepted", "Accepted opportunities", "count")
        self.register_counter("opportunities_rejected", "Rejected opportunities", "count")
        self.register_gauge("opportunity_score", "Current opportunity score", "score")
        
        # AI metrics
        self.register_counter("predictions_total", "Total predictions", "count")
        self.register_gauge("prediction_accuracy", "Prediction accuracy", "percent")
        self.register_histogram("prediction_confidence", "Prediction confidence", "percent")
        self.register_gauge("model_drift", "Model drift score", "score")
        
        # Execution metrics
        self.register_counter("orders_total", "Total orders", "count")
        self.register_counter("orders_filled", "Filled orders", "count")
        self.register_counter("orders_rejected", "Rejected orders", "count")
        self.register_histogram("execution_latency", "Execution latency", "seconds")
        self.register_gauge("slippage_bps", "Slippage in basis points", "bps")
        
        # Strategy metrics
        self.register_gauge("strategy_pnl", "Strategy P&L", "currency")
        self.register_gauge("strategy_positions", "Number of positions", "count")
        self.register_histogram("decision_frequency", "Decision frequency", "Hz")
        
        # Queue metrics
        self.register_gauge("queue_length", "Queue length", "count")
        self.register_gauge("queue_processing_time", "Queue processing time", "seconds")
        
        # WebSocket metrics
        self.register_counter("websocket_messages_sent", "WebSocket messages sent", "messages")
        self.register_counter("websocket_messages_received", "WebSocket messages received", "messages")
        self.register_gauge("websocket_connections", "WebSocket connections", "count")
        self.register_histogram("websocket_latency", "WebSocket latency", "seconds")
    
    def register_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None
    ) -> Counter:
        """Register a new counter"""
        with self._lock:
            if name in self._counters:
                return self._counters[name]
            
            counter = Counter(name, description, unit, labels)
            self._counters[name] = counter
            logger.debug(f"Registered counter: {name}")
            return counter
    
    def register_gauge(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None
    ) -> Gauge:
        """Register a new gauge"""
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]
            
            gauge = Gauge(name, description, unit, labels)
            self._gauges[name] = gauge
            logger.debug(f"Registered gauge: {name}")
            return gauge
    
    def register_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None,
        buckets: List[float] = None
    ) -> Histogram:
        """Register a new histogram"""
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]
            
            histogram = Histogram(name, description, unit, labels, buckets)
            self._histograms[name] = histogram
            logger.debug(f"Registered histogram: {name}")
            return histogram
    
    def register_summary(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        labels: List[str] = None,
        quantiles: List[float] = None
    ) -> Summary:
        """Register a new summary"""
        with self._lock:
            if name in self._summaries:
                return self._summaries[name]
            
            summary = Summary(name, description, unit, labels, quantiles)
            self._summaries[name] = summary
            logger.debug(f"Registered summary: {name}")
            return summary
    
    def counter(self, name: str) -> Counter:
        """Get or create a counter"""
        with self._lock:
            if name not in self._counters:
                return self.register_counter(name)
            return self._counters[name]
    
    def gauge(self, name: str) -> Gauge:
        """Get or create a gauge"""
        with self._lock:
            if name not in self._gauges:
                return self.register_gauge(name)
            return self._gauges[name]
    
    def histogram(self, name: str) -> Histogram:
        """Get or create a histogram"""
        with self._lock:
            if name not in self._histograms:
                return self.register_histogram(name)
            return self._histograms[name]
    
    def summary(self, name: str) -> Summary:
        """Get or create a summary"""
        with self._lock:
            if name not in self._summaries:
                return self.register_summary(name)
            return self._summaries[name]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format"""
        metrics = {
            "counters": {},
            "gauges": {},
            "histograms": {},
            "summaries": {},
        }
        
        with self._lock:
            for name, counter in self._counters.items():
                metrics["counters"][name] = {
                    "description": counter.metadata.description,
                    "unit": counter.metadata.unit,
                    "values": dict(counter._values)
                }
            
            for name, gauge in self._gauges.items():
                metrics["gauges"][name] = {
                    "description": gauge.metadata.description,
                    "unit": gauge.metadata.unit,
                    "values": dict(gauge._values)
                }
            
            for name, histogram in self._histograms.items():
                metrics["histograms"][name] = {
                    "description": histogram.metadata.description,
                    "unit": histogram.metadata.unit,
                    "buckets": histogram.buckets,
                    "values": {
                        key: dict(counts)
                        for key, counts in histogram._counts.items()
                    }
                }
            
            for name, summary in self._summaries.items():
                metrics["summaries"][name] = {
                    "description": summary.metadata.description,
                    "unit": summary.metadata.unit,
                    "quantiles": summary.quantiles,
                }
        
        return metrics
    
    def get_prometheus_format(self) -> str:
        """Get metrics in Prometheus text format"""
        lines = []
        
        with self._lock:
            # Counters
            for name, counter in self._counters.items():
                help_line = f"# HELP {name} {counter.metadata.description}"
                type_line = f"# TYPE {name} counter"
                lines.extend([help_line, type_line])
                
                for key, value in counter._values.items():
                    if key:
                        lines.append(f"{name}{{{key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
                lines.append("")
            
            # Gauges
            for name, gauge in self._gauges.items():
                help_line = f"# HELP {name} {gauge.metadata.description}"
                type_line = f"# TYPE {name} gauge"
                lines.extend([help_line, type_line])
                
                for key, value in gauge._values.items():
                    if key:
                        lines.append(f"{name}{{{key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
                lines.append("")
            
            # Histograms
            for name, histogram in self._histograms.items():
                help_line = f"# HELP {name} {histogram.metadata.description}"
                type_line = f"# TYPE {name} histogram"
                lines.extend([help_line, type_line])
                
                for key in histogram._totals:
                    cumulative = 0
                    for bucket in histogram.buckets:
                        cumulative += histogram._counts[key][bucket]
                        le_label = f'le="{bucket}"'
                        if key:
                            lines.append(f"{name}_bucket{{{le_label},{key}}} {cumulative}")
                        else:
                            lines.append(f"{name}_bucket{{{le_label}}} {cumulative}")
                    
                    # +Inf bucket
                    total = histogram._totals[key]
                    if key:
                        lines.append(f"{name}_bucket{{le=\"+Inf\",{key}}} {total}")
                        lines.append(f"{name}_sum{{{key}}} {histogram._sums[key]}")
                        lines.append(f"{name}_count{{{key}}} {total}")
                    else:
                        lines.append(f'{name}_bucket{{le="+Inf"}} {total}')
                        lines.append(f"{name}_sum {histogram._sums[key]}")
                        lines.append(f"{name}_count {total}")
                lines.append("")
        
        return "\n".join(lines)


# Global metrics collector instance
metrics = MetricsCollector()
