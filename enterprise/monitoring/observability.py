"""
Observability Components

Centralized logging, metrics, and tracing.
"""

import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class LogEntry:
    """Log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    logger: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "logger": self.logger,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "metadata": self.metadata,
        }


@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "type": self.metric_type.value,
        }


@dataclass
class Span:
    """Distributed trace span"""
    span_id: str
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0
    parent_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self):
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class LogAggregator:
    """Aggregates and stores logs"""
    
    def __init__(self, max_entries: int = 10000):
        self._logs: List[LogEntry] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._handlers: List[Callable] = []
    
    def add_handler(self, handler: Callable[[LogEntry], None]):
        """Add log handler"""
        self._handlers.append(handler)
    
    def log(
        self,
        level: LogLevel,
        message: str,
        logger: str,
        **kwargs
    ):
        """Log an entry"""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            logger=logger,
            **kwargs
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_entries:
                self._logs = self._logs[-self._max_entries:]
        
        # Notify handlers
        for handler in self._handlers:
            try:
                handler(entry)
            except:
                pass
    
    def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None,
        logger: Optional[str] = None,
        trace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Query logs"""
        with self._lock:
            results = list(self._logs)
        
        if start_time:
            results = [l for l in results if l.timestamp >= start_time]
        if end_time:
            results = [l for l in results if l.timestamp <= end_time]
        if level:
            results = [l for l in results if l.level == level]
        if logger:
            results = [l for l in results if l.logger == logger]
        if trace_id:
            results = [l for l in results if l.trace_id == trace_id]
        
        return results[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        with self._lock:
            return {
                "total_entries": len(self._logs),
                "by_level": {
                    level.value: sum(1 for l in self._logs if l.level == level)
                    for level in LogLevel
                },
            }


class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record histogram value"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Keep last 1000 values
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def get_metrics(self) -> List[Metric]:
        """Get all current metrics"""
        metrics = []
        
        with self._lock:
            # Counters
            for key, value in self._counters.items():
                name, labels = self._parse_key(key)
                metrics.append(Metric(
                    name=name,
                    value=value,
                    timestamp=datetime.now(timezone.utc),
                    labels=labels,
                    metric_type=MetricType.COUNTER,
                ))
            
            # Gauges
            for key, value in self._gauges.items():
                name, labels = self._parse_key(key)
                metrics.append(Metric(
                    name=name,
                    value=value,
                    timestamp=datetime.now(timezone.utc),
                    labels=labels,
                    metric_type=MetricType.GAUGE,
                ))
            
            # Histograms
            for key, values in self._histograms.items():
                name, labels = self._parse_key(key)
                if values:
                    metrics.append(Metric(
                        name=f"{name}_sum",
                        value=sum(values),
                        timestamp=datetime.now(timezone.utc),
                        labels=labels,
                    ))
                    metrics.append(Metric(
                        name=f"{name}_count",
                        value=len(values),
                        timestamp=datetime.now(timezone.utc),
                        labels=labels,
                    ))
        
        return metrics
    
    @staticmethod
    def _make_key(name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    @staticmethod
    def _parse_key(key: str) -> tuple:
        if "{" not in key:
            return key, {}
        name = key.split("{")[0]
        labels_str = key.split("{")[1].rstrip("}")
        labels = {}
        for part in labels_str.split(","):
            k, v = part.split("=")
            labels[k] = v
        return name, labels


class Tracer:
    """Distributed tracing"""
    
    def __init__(self, service_name: str):
        self._service_name = service_name
        self._spans: Dict[str, Span] = {}
        self._lock = threading.Lock()
    
    def start_span(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Span:
        """Start a new span"""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())[:16]
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            parent_id=parent_id,
        )
        
        with self._lock:
            self._spans[span_id] = span
        
        return span
    
    def finish_span(self, span: Span):
        """Finish a span"""
        span.finish()
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace"""
        with self._lock:
            return [s for s in self._spans.values() if s.trace_id == trace_id]
    
    def get_active_spans(self) -> int:
        """Get count of active (unfinished) spans"""
        with self._lock:
            return sum(1 for s in self._spans.values() if s.end_time is None)


class ObservabilityManager:
    """
    Centralized observability manager.
    
    Combines logging, metrics, and tracing.
    """
    
    def __init__(self, service_name: str):
        self._service_name = service_name
        self._log_aggregator = LogAggregator()
        self._metrics = MetricsCollector()
        self._tracer = Tracer(service_name)
    
    @property
    def logs(self) -> LogAggregator:
        return self._log_aggregator
    
    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics
    
    @property
    def tracer(self) -> Tracer:
        return self._tracer
    
    def log(
        self,
        level: LogLevel,
        message: str,
        **kwargs
    ):
        """Log a message"""
        self._log_aggregator.log(level, message, self._service_name, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get observability status"""
        return {
            "service": self._service_name,
            "logs": self._log_aggregator.get_stats(),
            "metrics": {
                "counters": len(self._metrics._counters),
                "gauges": len(self._metrics._gauges),
                "histograms": len(self._metrics._histograms),
            },
            "tracing": {
                "active_spans": self._tracer.get_active_spans(),
            },
        }
