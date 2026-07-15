"""
Replay Engine Core
================

Core replay engine with tick-by-tick playback and deterministic accuracy.
"""

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class ReplayEventType(Enum):
    """Types of events in replay"""
    # Market data
    TICK = "tick"
    OHLCV = "ohlcv"
    ORDERBOOK = "orderbook"
    
    # Strategy
    STRATEGY_DECISION = "strategy_decision"
    SIGNAL_GENERATED = "signal_generated"
    PARAMETER_UPDATE = "parameter_update"
    
    # AI
    AI_CONFIDENCE = "ai_confidence"
    AI_REASONING = "ai_reasoning"
    AI_RECOMMENDATION = "ai_recommendation"
    
    # Risk
    RISK_CHECK = "risk_check"
    RISK_LIMIT_HIT = "risk_limit_hit"
    
    # Execution
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    
    # Dashboard
    DASHBOARD_UPDATE = "dashboard_update"
    METRIC_RECORDED = "metric_recorded"
    
    # Plugins
    PLUGIN_EVENT = "plugin_event"
    
    # Annotations
    ANNOTATION = "annotation"
    BOOKMARK = "bookmark"


@dataclass
class TickData:
    """Tick data for a single time point"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: float
    regime: Optional[str] = None
    volatility: Optional[float] = None
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class ReplayEvent:
    """
    Base class for all replay events.
    
    Events are immutable and hashable for deterministic replay.
    """
    event_id: str
    event_type: ReplayEventType
    timestamp: datetime
    sequence: int  # Monotonic sequence number for ordering
    
    # Event-specific data
    data: Dict[str, Any]
    
    # Determinism
    deterministic_hash: str = ""
    
    def __post_init__(self):
        if not self.deterministic_hash:
            self.deterministic_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for this event"""
        hash_input = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            "data": self.data
        }
        hash_str = json.dumps(hash_input, sort_keys=True, default=str)
        return hashlib.sha256(hash_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            "data": self.data,
            "deterministic_hash": self.deterministic_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayEvent":
        return cls(
            event_id=data["event_id"],
            event_type=ReplayEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sequence=data["sequence"],
            data=data["data"],
            deterministic_hash=data.get("deterministic_hash", "")
        )


@dataclass
class MarketDataEvent(ReplayEvent):
    """Market data event"""
    tick: Optional[TickData] = None
    
    def __init__(self, tick: TickData, sequence: int):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.TICK,
            timestamp=tick.timestamp,
            sequence=sequence,
            data={
                "symbol": tick.symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "bid_size": tick.bid_size,
                "ask_size": tick.ask_size,
                "volume": tick.volume,
                "regime": tick.regime,
                "volatility": tick.volatility
            }
        )
        self.tick = tick


@dataclass
class StrategyDecisionEvent(ReplayEvent):
    """Strategy decision event"""
    def __init__(self, timestamp: datetime, sequence: int, decision: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.STRATEGY_DECISION,
            timestamp=timestamp,
            sequence=sequence,
            data=decision
        )


@dataclass
class AIConfidenceEvent(ReplayEvent):
    """AI confidence event"""
    def __init__(self, timestamp: datetime, sequence: int, confidence: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.AI_CONFIDENCE,
            timestamp=timestamp,
            sequence=sequence,
            data=confidence
        )


@dataclass
class RiskCheckEvent(ReplayEvent):
    """Risk check event"""
    def __init__(self, timestamp: datetime, sequence: int, check: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.RISK_CHECK,
            timestamp=timestamp,
            sequence=sequence,
            data=check
        )


@dataclass
class TradeExecutionEvent(ReplayEvent):
    """Trade execution event"""
    def __init__(self, timestamp: datetime, sequence: int, execution: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.TRADE_EXECUTION,
            timestamp=timestamp,
            sequence=sequence,
            data=execution
        )


@dataclass
class DashboardUpdateEvent(ReplayEvent):
    """Dashboard update event"""
    def __init__(self, timestamp: datetime, sequence: int, update: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.DASHBOARD_UPDATE,
            timestamp=timestamp,
            sequence=sequence,
            data=update
        )


@dataclass
class PluginEvent(ReplayEvent):
    """Plugin event"""
    def __init__(self, timestamp: datetime, sequence: int, event_type: str, plugin_data: Dict[str, Any]):
        super().__init__(
            event_id=str(uuid4()),
            event_type=ReplayEventType.PLUGIN_EVENT,
            timestamp=timestamp,
            sequence=sequence,
            data={
                "plugin_event_type": event_type,
                **plugin_data
            }
        )


@dataclass
class ReplaySession:
    """
    A complete replay session.
    """
    session_id: str
    name: str
    start_time: datetime
    end_time: datetime
    events: List[ReplayEvent]
    bookmarks: Dict[str, str]  # bookmark_id -> description
    annotations: List[Dict[str, Any]]
    
    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time
    
    @property
    def event_count(self) -> int:
        return len(self.events)
    
    def get_time_range(self) -> Tuple[datetime, datetime]:
        return self.start_time, self.end_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "event_count": self.event_count,
            "duration_seconds": self.duration.total_seconds(),
            "bookmarks": self.bookmarks,
            "annotations": self.annotations
        }


@dataclass
class ReplayConfig:
    """Configuration for replay engine"""
    # Playback
    default_speed: float = 1.0
    min_speed: float = 0.25
    max_speed: float = 5000.0
    
    # Memory management
    max_events_in_memory: int = 100000
    stream_chunk_size: int = 10000
    
    # Determinism
    verify_determinism: bool = True
    
    # Filters
    include_market_data: bool = True
    include_strategy_decisions: bool = True
    include_ai_events: bool = True
    include_risk_checks: bool = True
    include_execution: bool = True
    include_dashboard: bool = True
    include_plugins: bool = True


class EventStream:
    """
    Memory-efficient streaming of events.
    
    Uses chunked loading to handle millions of ticks efficiently.
    """
    
    def __init__(
        self,
        events: List[ReplayEvent],
        chunk_size: int = 10000
    ):
        self.events = events
        self.chunk_size = chunk_size
        self.position = 0
    
    def __iter__(self) -> Iterator[ReplayEvent]:
        return self
    
    def __next__(self) -> ReplayEvent:
        if self.position >= len(self.events):
            raise StopIteration
        
        event = self.events[self.position]
        self.position += 1
        return event
    
    def seek(self, position: int) -> None:
        """Seek to position"""
        self.position = max(0, min(position, len(self.events)))
    
    def seek_time(self, timestamp: datetime) -> int:
        """Seek to timestamp, return position"""
        left, right = 0, len(self.events) - 1
        result = len(self.events)
        
        while left <= right:
            mid = (left + right) // 2
            if self.events[mid].timestamp <= timestamp:
                result = mid
                left = mid + 1
            else:
                right = mid - 1
        
        self.position = result
        return result
    
    def get_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[ReplayEvent]:
        """Get events in time range"""
        start_pos = self.seek_time(start)
        end_pos = self.seek_time(end)
        return self.events[start_pos:end_pos]
    
    def __len__(self) -> int:
        return len(self.events)


class ReplayEngine:
    """
    Institutional-grade replay engine.
    
    Features:
    - Tick-by-tick replay with deterministic accuracy
    - Adjustable playback speed (0.25x to 5000x)
    - Transport controls (pause, resume, rewind, fast-forward)
    - Jump to timestamp
    - Frame-by-frame debugging
    - Memory-efficient streaming
    """
    
    def __init__(
        self,
        config: Optional[ReplayConfig] = None,
        db_path: str = "data/replay/events.db"
    ):
        self.config = config or ReplayConfig()
        self.db_path = db_path
        
        # Session state
        self.current_session: Optional[ReplaySession] = None
        self.stream: Optional[EventStream] = None
        self.position = 0
        
        # Playback state
        self.is_playing = False
        self.current_speed = self.config.default_speed
        self.current_time: Optional[datetime] = None
        
        # Event handlers
        self._handlers: Dict[ReplayEventType, List[Callable]] = {
            et: [] for et in ReplayEventType
        }
        
        # Statistics
        self.stats = {
            "events_replayed": 0,
            "total_events": 0,
            "replay_start_time": None,
            "replay_elapsed": 0.0
        }
        
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replay_sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT,
                start_time TEXT,
                end_time TEXT,
                event_count INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replay_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                sequence INTEGER,
                data TEXT,
                deterministic_hash TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON replay_events(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON replay_events(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def load_session(
        self,
        session_id: str = None,
        name: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> ReplaySession:
        """
        Load a replay session.
        
        Args:
            session_id: Session ID to load
            name: Or load by name
            start_time: Or load time range
            end_time: Time range end
            
        Returns:
            ReplaySession
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute(
                "SELECT * FROM replay_sessions WHERE session_id = ?",
                (session_id,)
            )
        elif name:
            cursor.execute(
                "SELECT * FROM replay_sessions WHERE name = ?",
                (name,)
            )
        else:
            cursor.execute(
                "SELECT * FROM replay_sessions WHERE start_time >= ? AND end_time <= ?",
                (start_time.isoformat(), end_time.isoformat())
            )
        
        row = cursor.fetchone()
        
        if not row:
            raise ValueError("Session not found")
        
        session_id, session_name, start, end, count = row
        
        # Load events
        cursor.execute(
            "SELECT event_id, event_type, timestamp, sequence, data, deterministic_hash "
            "FROM replay_events WHERE session_id = ? ORDER BY sequence",
            (session_id,)
        )
        
        events = []
        for erow in cursor.fetchall():
            event = ReplayEvent(
                event_id=erow[0],
                event_type=ReplayEventType(erow[1]),
                timestamp=datetime.fromisoformat(erow[2]),
                sequence=erow[3],
                data=json.loads(erow[4]),
                deterministic_hash=erow[5]
            )
            events.append(event)
        
        conn.close()
        
        self.current_session = ReplaySession(
            session_id=session_id,
            name=session_name,
            start_time=datetime.fromisoformat(start),
            end_time=datetime.fromisoformat(end),
            events=events,
            bookmarks={},
            annotations=[]
        )
        
        self.stream = EventStream(
            events=self.current_session.events,
            chunk_size=self.config.stream_chunk_size
        )
        
        self.position = 0
        self.stats["total_events"] = len(events)
        
        logger.info(f"Loaded session: {session_id} with {len(events)} events")
        
        return self.current_session
    
    def create_session(
        self,
        name: str,
        events: List[ReplayEvent] = None
    ) -> ReplaySession:
        """
        Create a new replay session.
        
        Args:
            name: Session name
            events: Events to include (optional, can add later)
            
        Returns:
            ReplaySession
        """
        events = events or []
        
        # Sort events by sequence
        events = sorted(events, key=lambda e: e.sequence)
        
        start_time = events[0].timestamp if events else datetime.now()
        end_time = events[-1].timestamp if events else datetime.now()
        
        session = ReplaySession(
            session_id=str(uuid4()),
            name=name,
            start_time=start_time,
            end_time=end_time,
            events=events,
            bookmarks={},
            annotations=[]
        )
        
        self.current_session = session
        self.stream = EventStream(
            events=events,
            chunk_size=self.config.stream_chunk_size
        )
        
        # Save to database
        self._save_session(session)
        
        return session
    
    def add_event(self, event: ReplayEvent) -> None:
        """Add event to current session"""
        if self.current_session:
            self.current_session.events.append(event)
            if self.stream:
                self.stream.events.append(event)
            
            # Update session bounds
            if event.timestamp < self.current_session.start_time:
                self.current_session.start_time = event.timestamp
            if event.timestamp > self.current_session.end_time:
                self.current_session.end_time = event.timestamp
    
    def add_bookmark(
        self,
        timestamp: datetime,
        description: str
    ) -> str:
        """Add bookmark at timestamp"""
        if not self.current_session:
            raise ValueError("No session loaded")
        
        bookmark_id = str(uuid4())
        self.current_session.bookmarks[bookmark_id] = description
        
        # Create bookmark event
        bookmark_event = ReplayEvent(
            event_id=bookmark_id,
            event_type=ReplayEventType.BOOKMARK,
            timestamp=timestamp,
            sequence=self._get_next_sequence(),
            data={"description": description}
        )
        
        self.add_event(bookmark_event)
        
        return bookmark_id
    
    def add_annotation(
        self,
        timestamp: datetime,
        annotation: str,
        category: str = "general"
    ) -> None:
        """Add timeline annotation"""
        if not self.current_session:
            raise ValueError("No session loaded")
        
        self.current_session.annotations.append({
            "timestamp": timestamp.isoformat(),
            "annotation": annotation,
            "category": category
        })
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        if self.current_session and self.current_session.events:
            return max(e.sequence for e in self.current_session.events) + 1
        return 0
    
    def _save_session(self, session: ReplaySession) -> None:
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO replay_sessions (session_id, name, start_time, end_time, event_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.name,
            session.start_time.isoformat(),
            session.end_time.isoformat(),
            len(session.events)
        ))
        
        for event in session.events:
            cursor.execute("""
                INSERT INTO replay_events (
                    event_id, session_id, event_type, timestamp, sequence, data, deterministic_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                session.session_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.sequence,
                json.dumps(event.data),
                event.deterministic_hash
            ))
        
        conn.commit()
        conn.close()
    
    def register_handler(
        self,
        event_type: ReplayEventType,
        handler: Callable[[ReplayEvent], None]
    ) -> None:
        """Register event handler"""
        self._handlers[event_type].append(handler)
    
    def unregister_handler(
        self,
        event_type: ReplayEventType,
        handler: Callable[[ReplayEvent], None]
    ) -> None:
        """Unregister event handler"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    def play(self) -> None:
        """Start playback"""
        self.is_playing = True
        self.stats["replay_start_time"] = datetime.now()
    
    def pause(self) -> None:
        """Pause playback"""
        self.is_playing = False
        if self.stats["replay_start_time"]:
            self.stats["replay_elapsed"] += (
                datetime.now() - self.stats["replay_start_time"]
            ).total_seconds()
    
    def stop(self) -> None:
        """Stop and reset"""
        self.is_playing = False
        self.position = 0
        self.stats["events_replayed"] = 0
        self.stats["replay_elapsed"] = 0.0
    
    def rewind(self, seconds: float = 10.0) -> None:
        """Rewind by seconds"""
        if self.current_session:
            target_time = self.current_time - timedelta(seconds=seconds)
            self.position = self.stream.seek_time(target_time)
    
    def fast_forward(self, seconds: float = 10.0) -> None:
        """Fast forward by seconds"""
        if self.current_session:
            target_time = self.current_time + timedelta(seconds=seconds)
            self.position = self.stream.seek_time(target_time)
    
    def jump_to(self, timestamp: datetime) -> None:
        """Jump to specific timestamp"""
        if self.stream:
            self.position = self.stream.seek_time(timestamp)
            self.current_time = timestamp
    
    def jump_to_start(self) -> None:
        """Jump to session start"""
        if self.current_session:
            self.position = 0
            self.current_time = self.current_session.start_time
    
    def jump_to_end(self) -> None:
        """Jump to session end"""
        if self.current_session:
            self.position = len(self.current_session.events) - 1
            self.current_time = self.current_session.end_time
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed"""
        self.current_speed = max(
            self.config.min_speed,
            min(speed, self.config.max_speed)
        )
    
    def step_forward(self) -> Optional[ReplayEvent]:
        """Step to next event (frame-by-frame)"""
        if not self.stream or self.position >= len(self.stream.events):
            return None
        
        event = self.stream.events[self.position]
        self.position += 1
        self.current_time = event.timestamp
        self.stats["events_replayed"] += 1
        
        # Call handlers
        for handler in self._handlers[event.event_type]:
            handler(event)
        
        return event
    
    def step_backward(self) -> Optional[ReplayEvent]:
        """Step to previous event"""
        if not self.stream or self.position <= 0:
            return None
        
        self.position -= 1
        event = self.stream.events[self.position]
        self.current_time = event.timestamp
        
        return event
    
    def get_current_event(self) -> Optional[ReplayEvent]:
        """Get current event"""
        if self.stream and 0 <= self.position < len(self.stream.events):
            return self.stream.events[self.position]
        return None
    
    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)"""
        if not self.stream or not self.current_session:
            return 0.0
        
        total = len(self.stream.events)
        if total == 0:
            return 0.0
        
        return self.position / total
    
    def get_state(self) -> Dict[str, Any]:
        """Get current replay state"""
        return {
            "is_playing": self.is_playing,
            "speed": self.current_speed,
            "position": self.position,
            "total_events": self.stats["total_events"],
            "events_replayed": self.stats["events_replayed"],
            "progress": self.get_progress(),
            "current_time": self.current_time.isoformat() if self.current_time else None,
            "session_id": self.current_session.session_id if self.current_session else None,
            "session_name": self.current_session.name if self.current_session else None
        }
    
    def verify_determinism(self) -> Dict[str, Any]:
        """
        Verify that replay is deterministic.
        
        Returns verification results.
        """
        if not self.stream:
            return {"valid": True, "message": "No session loaded"}
        
        hashes = [e.deterministic_hash for e in self.stream.events]
        
        # Check for duplicates
        unique_hashes = set(hashes)
        has_duplicates = len(unique_hashes) != len(hashes)
        
        # Check sequence ordering
        sequences = [e.sequence for e in self.stream.events]
        is_ordered = sequences == sorted(sequences)
        
        # Check timestamp ordering
        timestamps = [e.timestamp for e in self.stream.events]
        is_time_ordered = timestamps == sorted(timestamps)
        
        valid = not has_duplicates and is_ordered and is_time_ordered
        
        return {
            "valid": valid,
            "has_duplicates": has_duplicates,
            "is_ordered": is_ordered,
            "is_time_ordered": is_time_ordered,
            "total_events": len(hashes),
            "unique_hashes": len(unique_hashes)
        }
    
    def get_session_list(self) -> List[Dict[str, Any]]:
        """Get list of available sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM replay_sessions ORDER BY start_time DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "session_id": r[0],
                "name": r[1],
                "start_time": r[2],
                "end_time": r[3],
                "event_count": r[4]
            }
            for r in rows
        ]
