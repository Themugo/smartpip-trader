"""
Timeline Manager - Chronological Event Logging

Provides comprehensive event tracking:
- All system events
- Chronological ordering
- Event filtering
- Session storage
- Replay capability
"""

import json
import logging
import os
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events tracked in timeline"""
    # Market events
    TICK_RECEIVED = "tick_received"
    PRICE_UPDATE = "price_update"
    DIGIT_EXTRACTED = "digit_extracted"
    
    # Analysis events
    ANALYZER_OUTPUT = "analyzer_output"
    CONFIDENCE_UPDATE = "confidence_update"
    REGIME_CHANGE = "regime_change"
    PATTERN_DETECTED = "pattern_detected"
    ENTROPY_CHANGE = "entropy_change"
    
    # AI/ML events
    MODEL_UPDATE = "model_update"
    MODEL_TRAINING_START = "model_training_start"
    MODEL_TRAINING_COMPLETE = "model_training_complete"
    PREDICTION_GENERATED = "prediction_generated"
    
    # Signal events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_AGGREGATED = "signal_aggregated"
    SIGNAL_REJECTED = "signal_rejected"
    
    # Risk events
    RISK_VALIDATION = "risk_validation"
    RISK_APPROVED = "risk_approved"
    RISK_REJECTED = "risk_rejected"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    DRAWDOWN_ALERT = "drawdown_alert"
    
    # Trading events
    TRADE_APPROVED = "trade_approved"
    TRADE_REJECTED = "trade_rejected"
    TRADE_EXECUTED = "trade_executed"
    TRADE_EXIT = "trade_exit"
    TRADE_RESULT = "trade_result"
    
    # Plugin events
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    PLUGIN_ERROR = "plugin_error"
    
    # System events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"
    RECONNECTION = "reconnection"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
    # User events
    USER_ACTION = "user_action"
    SETTINGS_CHANGED = "settings_changed"
    WORKSPACE_CHANGED = "workspace_changed"
    
    # Custom events
    CUSTOM = "custom"


class EventSeverity(Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TimelineEvent:
    """A single event in the timeline"""
    id: str
    event_type: EventType
    timestamp: datetime
    severity: EventSeverity = EventSeverity.INFO
    source: str = "system"
    
    # Event data
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Relationships
    parent_id: Optional[str] = None
    related_ids: List[str] = field(default_factory=list)
    
    # Metadata
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Computed
    duration_ms: Optional[float] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def event_type_value(self) -> str:
        return self.event_type.value
    
    @property
    def severity_value(self) -> str:
        return self.severity.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "parent_id": self.parent_id,
            "related_ids": self.related_ids,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "duration_ms": self.duration_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineEvent":
        return cls(
            id=data["id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            severity=EventSeverity(data.get("severity", "info")),
            source=data.get("source", "system"),
            message=data.get("message", ""),
            data=data.get("data", {}),
            parent_id=data.get("parent_id"),
            related_ids=data.get("related_ids", []),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            correlation_id=data.get("correlation_id"),
            duration_ms=data.get("duration_ms"),
        )


class TimelineManager:
    """
    Manages the complete event timeline.
    
    Features:
    - Comprehensive event tracking
    - Chronological ordering
    - Event filtering
    - Session management
    - Storage and replay
    - Real-time subscriptions
    """
    
    def __init__(
        self,
        storage_path: str = "data/timeline",
        max_events: int = 100000,
        session_timeout: int = 3600,
    ):
        self._storage_path = storage_path
        self._max_events = max_events
        self._session_timeout = session_timeout
        
        self._events: deque = deque(maxlen=max_events)
        self._current_session_id: Optional[str] = None
        self._sessions: Dict[str, List[str]] = {}  # session_id -> event_ids
        self._event_index: Dict[str, int] = {}  # event_id -> index
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._correlation_index: Dict[str, List[str]] = {}  # correlation_id -> event_ids
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_recent_events()
    
    def _load_recent_events(self) -> None:
        """Load recent events from storage"""
        recent_file = os.path.join(self._storage_path, "recent_events.json")
        
        if os.path.exists(recent_file):
            try:
                with open(recent_file, "r") as f:
                    data = json.load(f)
                
                for event_data in data.get("events", []):
                    event = TimelineEvent.from_dict(event_data)
                    self._events.append(event)
                    self._event_index[event.id] = len(self._events) - 1
                    
                    # Index by correlation
                    if event.correlation_id:
                        if event.correlation_id not in self._correlation_index:
                            self._correlation_index[event.correlation_id] = []
                        self._correlation_index[event.correlation_id].append(event.id)
                
                logger.info(f"Loaded {len(self._events)} recent events")
            except Exception as e:
                logger.error(f"Failed to load recent events: {e}")
    
    def _save_recent_events(self) -> None:
        """Save recent events to storage"""
        recent_file = os.path.join(self._storage_path, "recent_events.json")
        
        events_to_save = list(self._events)[-10000:]  # Save last 10k events
        
        data = {
            "events": [e.to_dict() for e in events_to_save],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            with open(recent_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recent events: {e}")
    
    def start_session(self, user_id: Optional[str] = None) -> str:
        """Start a new timeline session"""
        self._current_session_id = str(uuid.uuid4())
        self._sessions[self._current_session_id] = []
        
        self.log_event(
            EventType.SESSION_START,
            message=f"Session started: {self._current_session_id}",
            user_id=user_id,
        )
        
        return self._current_session_id
    
    def end_session(self) -> Optional[str]:
        """End the current session"""
        if not self._current_session_id:
            return None
        
        session_id = self._current_session_id
        
        self.log_event(
            EventType.SESSION_END,
            message=f"Session ended: {session_id}",
            session_id=session_id,
        )
        
        # Save session to file
        self._save_session(session_id)
        
        self._current_session_id = None
        return session_id
    
    def _save_session(self, session_id: str) -> None:
        """Save a session's events to file"""
        if session_id not in self._sessions:
            return
        
        session_file = os.path.join(self._storage_path, f"session_{session_id}.json")
        event_ids = self._sessions[session_id]
        
        session_events = [
            self._events[self._event_index[eid]].to_dict()
            for eid in event_ids
            if eid in self._event_index
        ]
        
        data = {
            "session_id": session_id,
            "events": session_events,
            "event_count": len(session_events),
            "started_at": session_events[0]["timestamp"] if session_events else None,
            "ended_at": session_events[-1]["timestamp"] if session_events else None,
        }
        
        try:
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
    
    def log_event(
        self,
        event_type: EventType,
        message: str = "",
        severity: EventSeverity = EventSeverity.INFO,
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> TimelineEvent:
        """
        Log a new event.
        
        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity
            source: Source of the event
            data: Additional event data
            user_id: User who triggered the event
            correlation_id: ID to correlate related events
            parent_id: Parent event ID
            duration_ms: Duration for timed events
            
        Returns:
            Created TimelineEvent
        """
        event = TimelineEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            source=source,
            message=message,
            data=data or {},
            parent_id=parent_id,
            user_id=user_id,
            session_id=self._current_session_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            duration_ms=duration_ms,
        )
        
        # Add to events
        self._events.append(event)
        self._event_index[event.id] = len(self._events) - 1
        
        # Index by correlation
        if event.correlation_id:
            if event.correlation_id not in self._correlation_index:
                self._correlation_index[event.correlation_id] = []
            self._correlation_index[event.correlation_id].append(event.id)
        
        # Add to session
        if self._current_session_id:
            self._sessions[self._current_session_id].append(event.id)
        
        # Notify subscribers
        self._notify_subscribers(event)
        
        return event
    
    def _notify_subscribers(self, event: TimelineEvent) -> None:
        """Notify event subscribers"""
        # Type-specific subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Subscriber error for {event.event_type}: {e}")
        
        # Global subscribers
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Global subscriber error: {e}")
    
    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[TimelineEvent], None],
    ) -> None:
        """Subscribe to specific event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def subscribe_all(
        self,
        callback: Callable[[TimelineEvent], None],
    ) -> None:
        """Subscribe to all events"""
        self._global_subscribers.append(callback)
    
    def unsubscribe(
        self,
        event_type: Optional[EventType],
        callback: Callable,
    ) -> bool:
        """Unsubscribe from events"""
        if event_type:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    return True
                except ValueError:
                    pass
        else:
            try:
                self._global_subscribers.remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def get_events(
        self,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        severity: Optional[EventSeverity] = None,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[TimelineEvent]:
        """
        Get filtered events.
        
        Args:
            event_types: Filter by event types
            since: Events after this time
            until: Events before this time
            severity: Filter by severity
            source: Filter by source
            session_id: Filter by session
            correlation_id: Filter by correlation ID
            limit: Maximum number of events
            
        Returns:
            List of filtered events
        """
        # Get correlation events first if specified
        if correlation_id:
            event_ids = self._correlation_index.get(correlation_id, [])
            events = [
                self._events[self._event_index[eid]]
                for eid in event_ids
                if eid in self._event_index
            ]
            return events[-limit:]
        
        # Filter events
        filtered = []
        for event in reversed(self._events):
            # Type filter
            if event_types and event.event_type not in event_types:
                continue
            
            # Time filters
            if since and event.timestamp < since:
                continue
            if until and event.timestamp > until:
                continue
            
            # Severity filter
            if severity and event.severity != severity:
                continue
            
            # Source filter
            if source and event.source != source:
                continue
            
            # Session filter
            if session_id and event.session_id != session_id:
                continue
            
            filtered.append(event)
            
            if len(filtered) >= limit:
                break
        
        return list(reversed(filtered))
    
    def get_events_by_type(
        self,
        event_type: EventType,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """Get recent events of a specific type"""
        return self.get_events(event_types=[event_type], limit=limit)
    
    def get_trade_timeline(
        self,
        trade_id: str,
    ) -> List[TimelineEvent]:
        """Get complete timeline for a specific trade"""
        # Find all events related to this trade
        related = []
        
        for event in self._events:
            if event.data.get("trade_id") == trade_id:
                related.append(event)
            elif event.data.get("contract_id") == trade_id:
                related.append(event)
        
        return sorted(related, key=lambda e: e.timestamp)
    
    def get_session_events(
        self,
        session_id: Optional[str] = None,
    ) -> List[TimelineEvent]:
        """Get all events for a session"""
        session_id = session_id or self._current_session_id
        if not session_id:
            return []
        
        event_ids = self._sessions.get(session_id, [])
        return [
            self._events[self._event_index[eid]]
            for eid in event_ids
            if eid in self._event_index
        ]
    
    def get_statistics(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get timeline statistics"""
        events = self.get_events(since=since, limit=100000)
        
        # Count by type
        type_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        
        for event in events:
            type_counts[event.event_type.value] = type_counts.get(event.event_type.value, 0) + 1
            severity_counts[event.severity.value] = severity_counts.get(event.severity.value, 0) + 1
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
        
        return {
            "total_events": len(events),
            "event_types": type_counts,
            "severity_distribution": severity_counts,
            "sources": source_counts,
            "oldest_event": events[0].timestamp.isoformat() if events else None,
            "newest_event": events[-1].timestamp.isoformat() if events else None,
            "sessions": len(self._sessions),
        }
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """
        Search events by content.
        
        Args:
            query: Search query
            fields: Fields to search (message, data values)
            limit: Maximum results
            
        Returns:
            Matching events
        """
        query_lower = query.lower()
        results = []
        fields = fields or ["message"]
        
        for event in reversed(self._events):
            # Search message
            if "message" in fields and query_lower in event.message.lower():
                results.append(event)
                continue
            
            # Search data values
            if "data" in fields:
                data_str = json.dumps(event.data).lower()
                if query_lower in data_str:
                    results.append(event)
                    continue
            
            if len(results) >= limit:
                break
        
        return list(reversed(results))
    
    def export_session(
        self,
        session_id: str,
        filepath: str,
    ) -> bool:
        """Export a session to file"""
        events = self.get_session_events(session_id)
        
        data = {
            "session_id": session_id,
            "events": [e.to_dict() for e in events],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return False
    
    def import_session(self, filepath: str) -> Optional[str]:
        """Import a session from file"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            session_id = data.get("session_id", str(uuid.uuid4()))
            
            # Load events
            for event_data in data.get("events", []):
                event_data["session_id"] = session_id
                event = TimelineEvent.from_dict(event_data)
                self._events.append(event)
                self._event_index[event.id] = len(self._events) - 1
            
            self._sessions[session_id] = [
                e["id"] for e in data.get("events", [])
            ]
            
            return session_id
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return None
    
    def cleanup_old_events(self, before: datetime) -> int:
        """Remove events older than specified time"""
        before = before or datetime.now(timezone.utc) - timedelta(days=7)
        
        original_count = len(self._events)
        
        # Remove old events
        while self._events and self._events[0].timestamp < before:
            old_event = self._events.popleft()
            self._event_index.pop(old_event.id, None)
            
            # Clean correlation index
            if old_event.correlation_id:
                corr_list = self._correlation_index.get(old_event.correlation_id, [])
                if old_event.id in corr_list:
                    corr_list.remove(old_event.id)
        
        removed = original_count - len(self._events)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old events")
        
        return removed
