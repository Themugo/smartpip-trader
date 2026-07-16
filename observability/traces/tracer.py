"""
Distributed Tracer
=================

OpenTelemetry-style distributed tracing.
"""

import time
import threading
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque
from contextvars import ContextVar

logger = logging.getLogger(__name__)


class SpanKind(Enum):
    """Types of spans"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status codes"""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class Span:
    """A trace span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links,
        }


class Tracer:
    """
    Distributed tracer for request tracing.
    
    Features:
    - Span creation and management
    - Parent-child span relationships
    - Span attributes and events
    - Trace context propagation
    - Sampling support
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
        
        self._spans: Dict[str, Span] = {}
        self._span_stack: List[str] = []  # Stack of active span IDs
        self._traces: Dict[str, List[str]] = {}  # trace_id -> span_ids
        self._lock = threading.Lock()
        self._sample_rate = 1.0  # 100% sampling
        self._max_spans = 10000
        self._callbacks: List[Callable[[Span], None]] = []
        self._initialized = True
    
    def set_sample_rate(self, rate: float) -> None:
        """Set trace sampling rate (0.0 - 1.0)"""
        self._sample_rate = max(0.0, min(1.0, rate))
    
    def add_callback(self, callback: Callable[[Span], None]) -> None:
        """Add a callback for completed spans"""
        self._callbacks.append(callback)
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        sampled: Optional[bool] = None
    ) -> Span:
        """Start a new span"""
        # Determine if this span should be sampled
        if sampled is None:
            sampled = self._should_sample()
        
        if not sampled:
            # Return a no-op span
            return Span(
                trace_id=trace_id or "",
                span_id="",
                parent_span_id=parent_span_id,
                name=name,
                kind=kind,
                start_time=time.time(),
                attributes=attributes or {}
            )
        
        # Generate IDs
        if not trace_id:
            trace_id = uuid.uuid4().hex[:16]
        span_id = uuid.uuid4().hex[:8]
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=time.time(),
            attributes=attributes or {}
        )
        
        with self._lock:
            self._spans[span_id] = span
            
            # Add to trace
            if trace_id not in self._traces:
                self._traces[trace_id] = []
            self._traces[trace_id].append(span_id)
            
            # Update stack
            self._span_stack.append(span_id)
            
            # Cleanup old spans
            self._cleanup_old_spans()
        
        return span
    
    def end_span(self, span: Span) -> None:
        """End a span"""
        if not span.span_id:
            return  # No-op span
        
        span.end_time = time.time()
        
        with self._lock:
            # Remove from stack
            if self._span_stack and self._span_stack[-1] == span.span_id:
                self._span_stack.pop()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(span)
                except Exception as e:
                    logger.error(f"Trace callback error: {e}")
    
    def record_exception(self, span: Span, exception: Exception) -> None:
        """Record an exception in a span"""
        span.status = SpanStatus.ERROR
        span.attributes["error"] = True
        span.attributes["error.type"] = type(exception).__name__
        span.attributes["error.message"] = str(exception)
        
        span.events.append({
            "name": "exception",
            "timestamp": time.time(),
            "attributes": {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            }
        })
    
    def add_event(
        self,
        span: Span,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to a span"""
        span.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def set_attribute(self, span: Span, key: str, value: Any) -> None:
        """Set a span attribute"""
        span.attributes[key] = value
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span"""
        with self._lock:
            if self._span_stack:
                return self._spans.get(self._span_stack[-1])
        return None
    
    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace"""
        with self._lock:
            span_ids = self._traces.get(trace_id, [])
            return [self._spans[sid] for sid in span_ids if sid in self._spans]
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID"""
        with self._lock:
            return self._spans.get(span_id)
    
    def _should_sample(self) -> bool:
        """Determine if a span should be sampled"""
        import random
        return random.random() < self._sample_rate
    
    def _cleanup_old_spans(self) -> None:
        """Remove old spans to prevent memory growth"""
        if len(self._spans) > self._max_spans:
            # Remove oldest completed spans
            spans_to_remove = []
            for span_id, span in self._spans.items():
                if span.end_time and span_id not in self._span_stack:
                    spans_to_remove.append(span_id)
            
            # Remove oldest 10%
            remove_count = len(spans_to_remove) // 10
            for span_id in spans_to_remove[:remove_count]:
                del self._spans[span_id]
                
                # Remove from trace
                for trace_id, span_ids in self._traces.items():
                    if span_id in span_ids:
                        span_ids.remove(span_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracer statistics"""
        with self._lock:
            active = sum(1 for s in self._spans.values() if s.end_time is None)
            error = sum(1 for s in self._spans.values() if s.status == SpanStatus.ERROR)
            
            return {
                "total_spans": len(self._spans),
                "active_spans": active,
                "completed_spans": len(self._spans) - active,
                "error_spans": error,
                "total_traces": len(self._traces),
                "sample_rate": self._sample_rate,
            }


class SpanContext:
    """Context manager for span lifecycle"""
    
    def __init__(self, tracer: Tracer, name: str, kind: SpanKind = SpanKind.INTERNAL, **kwargs):
        self.tracer = tracer
        self.name = name
        self.kind = kind
        self.kwargs = kwargs
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        self.span = self.tracer.start_span(self.name, self.kind, **self.kwargs)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_val:
                self.tracer.record_exception(self.span, exc_val)
            self.tracer.end_span(self.span)


# Global tracer instance
tracer = Tracer()


def trace(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    **kwargs
) -> SpanContext:
    """Decorator/context manager for tracing"""
    return SpanContext(tracer, name, kind, **kwargs)
