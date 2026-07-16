"""
Event Bus
=========

Central event collection and distribution system.
"""

import time
import threading
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events"""
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    
    # Business events
    OPPORTUNITY_DETECTED = "opportunity.detected"
    OPPORTUNITY_ACCEPTED = "opportunity.accepted"
    OPPORTUNITY_REJECTED = "opportunity.rejected"
    TRADE_EXECUTED = "trade.executed"
    TRADE_FILLED = "trade.filled"
    TRADE_REJECTED = "trade.rejected"
    
    # Risk events
    RISK_LIMIT_HIT = "risk.limit_hit"
    RISK_THRESHOLD_BREACH = "risk.threshold_breach"
    RISK_DRAWDOWN_WARNING = "risk.drawdown_warning"
    
    # AI events
    MODEL_PREDICTION = "ai.prediction"
    MODEL_DRIFT_DETECTED = "ai.model_drift"
    MODEL_RETRAINING_STARTED = "ai.retraining_started"
    MODEL_RETRAINING_COMPLETED = "ai.retraining_completed"
    
    # Strategy events
    STRATEGY_ACTIVATED = "strategy.activated"
    STRATEGY_DEACTIVATED = "strategy.deactivated"
    STRATEGY_PNL_UPDATE = "strategy.pnl_update"
    STRATEGY_SIGNAL = "strategy.signal"
    
    # Infrastructure events
    WEBSOCKET_CONNECTED = "websocket.connected"
    WEBSOCKET_DISCONNECTED = "websocket.disconnected"
    API_REQUEST = "api.request"
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    QUEUE_DEPTH_CHANGE = "queue.depth_change"


@dataclass
class Event:
    """An observability event"""
    id: str
    type: EventType
    timestamp: float
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # debug, info, warning, error, critical
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "data": self.data,
            "severity": self.severity,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "correlation_id": self.correlation_id,
        }


class EventBus:
    """
    Central event bus for collecting and distributing events.
    
    Features:
    - Event publishing and subscribing
    - Event filtering
    - Event persistence
    - Async event handling
    - Event aggregation
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
        
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._event_history: deque = deque(maxlen=10000)
        self._events_by_type: Dict[EventType, deque] = {}
        self._lock = threading.Lock()
        self._async_handlers: List[threading.Thread] = []
        self._running = False
        self._event_queue: deque = deque()
        self._initialized = True
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ) -> None:
        """Subscribe to an event type"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ) -> None:
        """Unsubscribe from an event type"""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(handler)
    
    def subscribe_all(self, handler: Callable[[Event], None]) -> None:
        """Subscribe to all events"""
        with self._lock:
            self._global_subscribers.append(handler)
    
    def publish(
        self,
        event_type: EventType,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Event:
        """Publish an event"""
        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            timestamp=time.time(),
            source=source,
            data=data or {},
            severity=severity,
            trace_id=trace_id,
            span_id=span_id,
            correlation_id=correlation_id
        )
        
        # Store in history
        with self._lock:
            self._event_history.append(event)
            
            if event_type not in self._events_by_type:
                self._events_by_type[event_type] = deque(maxlen=1000)
            self._events_by_type[event_type].append(event)
        
        # Dispatch to subscribers
        self._dispatch(event)
        
        return event
    
    def _dispatch(self, event: Event) -> None:
        """Dispatch event to subscribers"""
        # Get handlers
        with self._lock:
            type_handlers = self._subscribers.get(event.type, []).copy()
            global_handlers = self._global_subscribers.copy()
        
        # Call type-specific handlers
        for handler in type_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    pass  # Would need async handling
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        # Call global handlers
        for handler in global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global event handler error: {e}")
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get events from history"""
        if event_type:
            events = list(self._events_by_type.get(event_type, []))
        else:
            events = list(self._event_history)
        
        # Filter by time
        if since:
            events = [e for e in events if e.timestamp >= since]
        if until:
            events = [e for e in events if e.timestamp <= until]
        
        return events[-limit:]
    
    def get_event_counts(
        self,
        since: Optional[float] = None
    ) -> Dict[str, int]:
        """Get event counts by type"""
        counts = {}
        
        with self._lock:
            for event_type, events in self._events_by_type.items():
                filtered = events
                if since:
                    filtered = [e for e in events if e.timestamp >= since]
                counts[event_type.value] = len(filtered)
        
        return counts
    
    def clear_history(self) -> None:
        """Clear event history"""
        with self._lock:
            self._event_history.clear()
            self._events_by_type.clear()


# Helper function for common events
def emit_opportunity_detected(
    symbol: str,
    score: float,
    data: Optional[Dict] = None
) -> Event:
    """Emit opportunity detected event"""
    return event_bus.publish(
        EventType.OPPORTUNITY_DETECTED,
        source="opportunity_detector",
        data={
            "symbol": symbol,
            "score": score,
            **(data or {})
        }
    )


def emit_trade_executed(
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    data: Optional[Dict] = None
) -> Event:
    """Emit trade executed event"""
    return event_bus.publish(
        EventType.TRADE_EXECUTED,
        source="execution_engine",
        data={
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "value": quantity * price,
            **(data or {})
        }
    )


def emit_risk_alert(
    alert_type: str,
    message: str,
    severity: str = "warning",
    data: Optional[Dict] = None
) -> Event:
    """Emit risk alert event"""
    event_type = EventType.RISK_LIMIT_HIT
    if alert_type == "threshold":
        event_type = EventType.RISK_THRESHOLD_BREACH
    elif alert_type == "drawdown":
        event_type = EventType.RISK_DRAWDOWN_WARNING
    
    return event_bus.publish(
        event_type,
        source="risk_manager",
        data={
            "alert_type": alert_type,
            "message": message,
            **(data or {})
        },
        severity=severity
    )


def emit_model_drift(
    model_name: str,
    drift_score: float,
    threshold: float,
    data: Optional[Dict] = None
) -> Event:
    """Emit model drift detected event"""
    return event_bus.publish(
        EventType.MODEL_DRIFT_DETECTED,
        source="model_monitor",
        data={
            "model_name": model_name,
            "drift_score": drift_score,
            "threshold": threshold,
            "exceeded": drift_score > threshold,
            **(data or {})
        },
        severity="warning" if drift_score > threshold else "info"
    )


# Global event bus instance
event_bus = EventBus()
