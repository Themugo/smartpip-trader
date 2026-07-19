"""
Event Bus - Publish/Subscribe Messaging System

Central event bus for platform-wide communication.
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context for request tracing
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Platform event"""
    type: str
    data: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: EventPriority = EventPriority.NORMAL
    request_id: Optional[str] = None
    source: str = ""
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "request_id": self.request_id,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


@dataclass
class Subscription:
    """Event subscription"""
    id: str
    event_type: str
    handler: Callable[[Event], Any]
    priority: EventPriority = EventPriority.NORMAL
    async_handler: bool = False
    filter_func: Optional[Callable[[Event], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, event: Event) -> bool:
        """Check if this subscription matches the event"""
        if event.priority.value > self.priority.value:
            return False
        if self.filter_func:
            return self.filter_func(event)
        return True


class EventBus:
    """
    Central event bus for platform-wide messaging.
    
    Features:
    - Topic-based subscriptions
    - Wildcard subscriptions
    - Priority-based delivery
    - Async and sync handlers
    - Event filtering
    - Dead letter queue
    - Event history
    """
    
    _instance: Optional["EventBus"] = None
    
    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the event bus"""
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._wildcard_subscriptions: List[Subscription] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._dead_letter_queue: List[Event] = []
        self._handlers_called: Dict[str, int] = defaultdict(int)
        self._handler_errors: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.EventBus")
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[Callable[[Event], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type (supports wildcards: "trade.*", "*", "**")
            handler: Event handler function
            priority: Handler priority
            filter_func: Optional filter function
            metadata: Additional metadata
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        # Determine if handler is async
        is_async = asyncio.iscoroutinefunction(handler)
        
        subscription = Subscription(
            id=subscription_id,
            event_type=event_type,
            handler=handler,
            priority=priority,
            async_handler=is_async,
            filter_func=filter_func,
            metadata=metadata or {},
        )
        
        if "*" in event_type or "?" in event_type:
            self._wildcard_subscriptions.append(subscription)
        else:
            self._subscriptions[event_type].append(subscription)
        
        # Sort by priority (higher first)
        self._subscriptions[event_type].sort(
            key=lambda s: s.priority.value, reverse=True
        )
        
        self._logger.debug(f"Subscribed to {event_type}: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from an event"""
        # Check exact matches
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    self._logger.debug(f"Unsubscribed: {subscription_id}")
                    return True
        
        # Check wildcards
        for sub in self._wildcard_subscriptions:
            if sub.id == subscription_id:
                self._wildcard_subscriptions.remove(sub)
                self._logger.debug(f"Unsubscribed: {subscription_id}")
                return True
        
        return False
    
    def publish(
        self,
        event_type: str,
        data: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        correlation_id: Optional[str] = None,
    ) -> Event:
        """
        Publish an event.
        
        Args:
            event_type: Event type
            data: Event data
            priority: Event priority
            source: Event source
            correlation_id: Optional correlation ID
            
        Returns:
            Published event
        """
        # Create event
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            priority=priority,
            request_id=request_id_ctx.get(),
            source=source,
            correlation_id=correlation_id,
        )
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Find matching subscriptions
        handlers = self._get_matching_subscriptions(event)
        
        # Execute handlers
        for sub in handlers:
            try:
                if sub.async_handler:
                    asyncio.create_task(self._execute_handler(sub, event))
                else:
                    self._execute_handler(sub, event)
                
                self._handlers_called[event_type] += 1
            except Exception as e:
                self._handler_errors[event_type] += 1
                self._logger.error(f"Handler error for {event_type}: {e}")
        
        return event
    
    async def publish_async(
        self,
        event_type: str,
        data: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "",
        correlation_id: Optional[str] = None,
    ) -> Event:
        """Async publish"""
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            priority=priority,
            request_id=request_id_ctx.get(),
            source=source,
            correlation_id=correlation_id,
        )
        
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        handlers = self._get_matching_subscriptions(event)
        
        for sub in handlers:
            try:
                if sub.async_handler:
                    await self._execute_handler_async(sub, event)
                else:
                    self._execute_handler(sub, event)
                
                self._handlers_called[event_type] += 1
            except Exception as e:
                self._handler_errors[event_type] += 1
                self._logger.error(f"Handler error for {event_type}: {e}")
        
        return event
    
    def _get_matching_subscriptions(self, event: Event) -> List[Subscription]:
        """Get all subscriptions matching an event"""
        matches = []
        
        # Exact match
        for sub in self._subscriptions.get(event.type, []):
            if sub.matches(event):
                matches.append(sub)
        
        # Wildcard matches
        for sub in self._wildcard_subscriptions:
            if self._matches_wildcard(event.type, sub.event_type) and sub.matches(event):
                matches.append(sub)
        
        # Sort by priority
        matches.sort(key=lambda s: s.priority.value, reverse=True)
        
        return matches
    
    def _matches_wildcard(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches wildcard pattern"""
        import fnmatch
        
        if pattern == "**":
            return True
        
        return fnmatch.fnmatch(event_type, pattern)
    
    def _execute_handler(self, sub: Subscription, event: Event) -> None:
        """Execute a sync handler"""
        try:
            sub.handler(event)
        except Exception as e:
            self._logger.error(f"Handler error: {e}")
            self._dead_letter_queue.append(event)
    
    async def _execute_handler_async(self, sub: Subscription, event: Event) -> None:
        """Execute an async handler"""
        try:
            if asyncio.iscoroutinefunction(sub.handler):
                await sub.handler(event)
            else:
                sub.handler(event)
        except Exception as e:
            self._logger.error(f"Handler error: {e}")
            self._dead_letter_queue.append(event)
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get event history"""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "total_subscriptions": sum(len(s) for s in self._subscriptions.values()) + len(self._wildcard_subscriptions),
            "handlers_called": dict(self._handlers_called),
            "handler_errors": dict(self._handler_errors),
            "history_size": len(self._event_history),
            "dead_letter_size": len(self._dead_letter_queue),
        }
    
    def clear_dead_letter(self) -> int:
        """Clear dead letter queue"""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count


# Global event bus instance
event_bus = EventBus()


# Common event types
class Events:
    """Common event types"""
    # Trading events
    TRADE_REQUESTED = "trade.requested"
    TRADE_EXECUTED = "trade.executed"
    TRADE_REJECTED = "trade.rejected"
    TRADE_CANCELLED = "trade.cancelled"
    
    # Signal events
    SIGNAL_GENERATED = "signal.generated"
    SIGNAL_AGGREGATED = "signal.aggregated"
    SIGNAL_REJECTED = "signal.rejected"
    
    # Risk events
    RISK_APPROVED = "risk.approved"
    RISK_REJECTED = "risk.rejected"
    RISK_ALERT = "risk.alert"
    KILL_SWITCH = "risk.killswitch"
    
    # AI events
    AI_DECISION = "ai.decision"
    AI_CONFIDENCE = "ai.confidence"
    MODEL_UPDATE = "ai.model_update"
    
    # System events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    MODULE_LOADED = "system.module_loaded"
    MODULE_ERROR = "system.module_error"
    
    # Market events
    MARKET_DATA = "market.data"
    MARKET_REGIME = "market.regime"
    
    # Account events
    ACCOUNT_UPDATE = "account.update"
    BALANCE_CHANGE = "account.balance"
    
    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ERROR = "plugin.error"
