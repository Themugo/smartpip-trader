"""
Event Sourcing Core
=================

Core event sourcing infrastructure for deterministic replay and auditability.
"""

import time
import uuid
import hashlib
import json
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """All event types in the platform"""
    # Market Events
    MARKET_TICK = "market.tick"
    MARKET_SNAPSHOT = "market.snapshot"
    FEATURE_CALCULATION = "feature.calculation"
    
    # AI Events
    AI_PREDICTION = "ai.prediction"
    RISK_EVALUATION = "risk.evaluation"
    CONFIDENCE_CALCULATION = "confidence.calculation"
    STRATEGY_DECISION = "strategy.decision"
    
    # Trading Events
    TRADE_APPROVAL = "trade.approval"
    TRADE_REJECTION = "trade.rejection"
    EXECUTION_REQUEST = "execution.request"
    EXECUTION_CONFIRMATION = "execution.confirmation"
    EXECUTION_FAILURE = "execution.failure"
    
    # System Events
    CONFIGURATION_CHANGE = "configuration.change"
    PLUGIN_EVENT = "plugin.event"
    SYSTEM_ALERT = "system.alert"
    HEALTH_EVENT = "health.event"
    
    # Research Events
    RESEARCH_EVENT = "research.event"
    VALIDATION_EVENT = "validation.event"


@dataclass
class EventMetadata:
    """Standard metadata for all events"""
    # Identity
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int = 0
    
    # Time
    timestamp: float = field(default_factory=time.time)
    timestamp_ns: int = 0  # Nanosecond precision
    
    # Correlation
    correlation_id: str = ""
    session_id: str = ""
    
    # Context
    account: str = ""
    workspace: str = ""
    
    # Versions
    strategy_version: str = ""
    model_version: str = ""
    feature_version: str = ""
    configuration_version: str = ""
    
    # Integrity
    checksum: str = ""
    previous_checksum: str = ""
    
    # Source
    source: str = ""
    source_ip: str = ""
    
    def calculate_checksum(self, payload: str) -> str:
        """Calculate event checksum"""
        content = json.dumps({
            "event_id": self.event_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "payload": payload,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class Event:
    """
    Base event class for all platform events.
    
    Every event is:
    - Immutable: Once created, cannot be modified
    - Ordered: Has sequence number for ordering
    - Verifiable: Has checksums for integrity
    - Complete: Contains all context needed for replay
    """
    event_type: EventType
    metadata: EventMetadata
    payload: Dict[str, Any]
    
    # Computed properties
    _checksum: str = field(init=False, repr=False)
    _compressed: bool = field(init=False, repr=False)
    
    def __post_init__(self):
        # Calculate checksum
        payload_str = json.dumps(self.payload, sort_keys=True, default=str)
        self._checksum = self.metadata.calculate_checksum(payload_str)
        self.metadata.checksum = self._checksum
    
    def get_event_id(self) -> str:
        """Get event ID"""
        return self.metadata.event_id
    
    def get_timestamp(self) -> float:
        """Get event timestamp"""
        return self.metadata.timestamp
    
    def get_sequence(self) -> int:
        """Get sequence number"""
        return self.metadata.sequence_number
    
    def get_correlation_id(self) -> str:
        """Get correlation ID"""
        return self.metadata.correlation_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_type": self.event_type.value,
            "metadata": {
                "event_id": self.metadata.event_id,
                "sequence_number": self.metadata.sequence_number,
                "timestamp": self.metadata.timestamp,
                "correlation_id": self.metadata.correlation_id,
                "session_id": self.metadata.session_id,
                "account": self.metadata.account,
                "workspace": self.metadata.workspace,
                "strategy_version": self.metadata.strategy_version,
                "model_version": self.metadata.model_version,
                "feature_version": self.metadata.feature_version,
                "configuration_version": self.metadata.configuration_version,
                "checksum": self.metadata.checksum,
                "previous_checksum": self.metadata.previous_checksum,
            },
            "payload": self.payload,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        metadata = EventMetadata(
            event_id=data["metadata"]["event_id"],
            sequence_number=data["metadata"]["sequence_number"],
            timestamp=data["metadata"]["timestamp"],
            correlation_id=data["metadata"].get("correlation_id", ""),
            session_id=data["metadata"].get("session_id", ""),
            account=data["metadata"].get("account", ""),
            workspace=data["metadata"].get("workspace", ""),
            strategy_version=data["metadata"].get("strategy_version", ""),
            model_version=data["metadata"].get("model_version", ""),
            feature_version=data["metadata"].get("feature_version", ""),
            configuration_version=data["metadata"].get("configuration_version", ""),
            checksum=data["metadata"].get("checksum", ""),
            previous_checksum=data["metadata"].get("previous_checksum", ""),
        )
        
        event_type = EventType(data["event_type"])
        payload = data["payload"]
        
        return cls(event_type=event_type, metadata=metadata, payload=payload)
    
    def verify_integrity(self) -> bool:
        """Verify event integrity"""
        payload_str = json.dumps(self.payload, sort_keys=True, default=str)
        expected = self.metadata.calculate_checksum(payload_str)
        return expected == self.metadata.checksum
    
    def compress(self) -> bytes:
        """Compress event for storage"""
        return zlib.compress(self.to_json().encode())
    
    @classmethod
    def decompress(cls, data: bytes) -> "Event":
        """Decompress event from storage"""
        json_str = zlib.decompress(data).decode()
        return cls.from_dict(json.loads(json_str))


class EventStore:
    """
    In-memory event store for real-time event handling.
    
    For persistent storage, use EventStoreDB.
    """
    
    def __init__(self):
        self._events: List[Event] = []
        self._by_type: Dict[EventType, List[Event]] = {}
        self._by_correlation: Dict[str, List[Event]] = {}
        self._by_session: Dict[str, List[Event]] = {}
        self._sequence: int = 0
        self._last_checksum: str = ""
        
        # Subscribers
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
    
    def append(self, event: Event) -> Event:
        """Append an event to the store"""
        # Set sequence number
        event.metadata.sequence_number = self._sequence
        self._sequence += 1
        
        # Set previous checksum
        event.metadata.previous_checksum = self._last_checksum
        
        # Recalculate checksum with updated metadata
        payload_str = json.dumps(event.payload, sort_keys=True, default=str)
        event.metadata.checksum = event.metadata.calculate_checksum(payload_str)
        self._last_checksum = event.metadata.checksum
        
        # Store event
        self._events.append(event)
        
        # Index by type
        if event.event_type not in self._by_type:
            self._by_type[event.event_type] = []
        self._by_type[event.event_type].append(event)
        
        # Index by correlation
        if event.metadata.correlation_id:
            if event.metadata.correlation_id not in self._by_correlation:
                self._by_correlation[event.metadata.correlation_id] = []
            self._by_correlation[event.metadata.correlation_id].append(event)
        
        # Index by session
        if event.metadata.session_id:
            if event.metadata.session_id not in self._by_session:
                self._by_session[event.metadata.session_id] = []
            self._by_session[event.metadata.session_id].append(event)
        
        # Notify subscribers
        self._notify(event)
        
        return event
    
    def _notify(self, event: Event) -> None:
        """Notify subscribers of new event"""
        # Type-specific subscribers
        for etype, callbacks in self._subscribers.items():
            if etype == event.event_type:
                for callback in callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Event subscriber error: {e}")
        
        # Global subscribers
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Global event subscriber error: {e}")
    
    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None]
    ) -> None:
        """Subscribe to events of a specific type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def subscribe_all(self, callback: Callable[[Event], None]) -> None:
        """Subscribe to all events"""
        self._global_subscribers.append(callback)
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 1000
    ) -> List[Event]:
        """Query events"""
        results = self._events
        
        if event_type:
            results = self._by_type.get(event_type, [])
        
        if correlation_id:
            results = [
                e for e in results
                if e.metadata.correlation_id == correlation_id
            ]
        
        if session_id:
            results = [
                e for e in results
                if e.metadata.session_id == session_id
            ]
        
        if since:
            results = [e for e in results if e.metadata.timestamp >= since]
        
        if until:
            results = [e for e in results if e.metadata.timestamp <= until]
        
        return results[-limit:]
    
    def get_sequence_range(
        self,
        start: int,
        end: int
    ) -> List[Event]:
        """Get events by sequence range"""
        return [
            e for e in self._events
            if start <= e.metadata.sequence_number <= end
        ]
    
    def get_last_event(self) -> Optional[Event]:
        """Get the last event"""
        return self._events[-1] if self._events else None
    
    def count(self) -> int:
        """Get total event count"""
        return len(self._events)
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify event chain integrity"""
        errors = []
        expected_checksum = ""
        
        for i, event in enumerate(self._events):
            # Verify sequence
            if event.metadata.sequence_number != i:
                errors.append(f"Event {i}: sequence mismatch")
            
            # Verify previous checksum
            if event.metadata.previous_checksum != expected_checksum:
                errors.append(f"Event {i}: previous checksum mismatch")
            
            # Verify own checksum
            if not event.verify_integrity():
                errors.append(f"Event {i}: checksum verification failed")
            
            expected_checksum = event.metadata.checksum
        
        return {
            "valid": len(errors) == 0,
            "total_events": len(self._events),
            "errors": errors,
        }
    
    def replay(
        self,
        start_sequence: int = 0,
        end_sequence: Optional[int] = None,
        event_types: Optional[Set[EventType]] = None
    ) -> List[Event]:
        """Get events for replay"""
        if end_sequence is None:
            end_sequence = len(self._events)
        
        events = self._events[start_sequence:end_sequence]
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        return events


@dataclass
class SequenceNumber:
    """Monotonic sequence number generator"""
    _current: int = 0
    
    def next(self) -> int:
        """Get next sequence number"""
        self._current += 1
        return self._current
    
    def current(self) -> int:
        """Get current sequence number"""
        return self._current


# Global event store instance
_global_event_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get the global event store instance"""
    global _global_event_store
    if _global_event_store is None:
        _global_event_store = EventStore()
    return _global_event_store


def set_event_store(store: EventStore) -> None:
    """Set the global event store instance"""
    global _global_event_store
    _global_event_store = store
