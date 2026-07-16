"""
Event Store Database
====================

Persistent event storage with indexing, compression, and replay support.
"""

import time
import json
import os
import sqlite3
import hashlib
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Set
from contextlib import contextmanager
import logging

from .core import Event, EventType, EventMetadata, EventStore

logger = logging.getLogger(__name__)


@dataclass
class EventQuery:
    """Query parameters for event retrieval"""
    event_types: Optional[Set[EventType]] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    account: Optional[str] = None
    workspace: Optional[str] = None
    strategy_version: Optional[str] = None
    model_version: Optional[str] = None
    since: Optional[float] = None
    until: Optional[float] = None
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    limit: int = 10000
    offset: int = 0
    
    def to_sql_conditions(self) -> tuple:
        """Convert to SQL WHERE conditions"""
        conditions = []
        params = []
        
        if self.event_types:
            type_values = [et.value for et in self.event_types]
            placeholders = ",".join("?" * len(type_values))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(type_values)
        
        if self.correlation_id:
            conditions.append("correlation_id = ?")
            params.append(self.correlation_id)
        
        if self.session_id:
            conditions.append("session_id = ?")
            params.append(self.session_id)
        
        if self.account:
            conditions.append("account = ?")
            params.append(self.account)
        
        if self.workspace:
            conditions.append("workspace = ?")
            params.append(self.workspace)
        
        if self.strategy_version:
            conditions.append("strategy_version = ?")
            params.append(self.strategy_version)
        
        if self.model_version:
            conditions.append("model_version = ?")
            params.append(self.model_version)
        
        if self.since:
            conditions.append("timestamp >= ?")
            params.append(self.since)
        
        if self.until:
            conditions.append("timestamp <= ?")
            params.append(self.until)
        
        if self.start_sequence is not None:
            conditions.append("sequence_number >= ?")
            params.append(self.start_sequence)
        
        if self.end_sequence is not None:
            conditions.append("sequence_number <= ?")
            params.append(self.end_sequence)
        
        return conditions, params


class EventStoreDB:
    """
    Persistent event store with SQLite backend.
    
    Features:
    - Append-only storage
    - Compression
    - Indexing
    - Event replay
    - Integrity validation
    - Time-travel queries
    """
    
    def __init__(self, db_path: str = "./data/events/events.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()
    
    def _ensure_dir(self) -> None:
        """Ensure directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    correlation_id TEXT,
                    session_id TEXT,
                    account TEXT,
                    workspace TEXT,
                    strategy_version TEXT,
                    model_version TEXT,
                    feature_version TEXT,
                    configuration_version TEXT,
                    checksum TEXT NOT NULL,
                    previous_checksum TEXT,
                    payload BLOB NOT NULL,
                    compressed INTEGER DEFAULT 0,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_sequence 
                ON events(sequence_number)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_correlation 
                ON events(correlation_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session 
                ON events(session_id)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def append(self, event: Event) -> None:
        """Append an event to the store"""
        payload_json = event.to_json()
        compressed = len(payload_json) > 1024  # Compress if > 1KB
        
        if compressed:
            payload_bytes = zlib.compress(payload_json.encode())
        else:
            payload_bytes = payload_json.encode()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO events (
                    event_id, event_type, sequence_number, timestamp,
                    correlation_id, session_id, account, workspace,
                    strategy_version, model_version, feature_version,
                    configuration_version, checksum, previous_checksum,
                    payload, compressed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.metadata.event_id,
                event.event_type.value,
                event.metadata.sequence_number,
                event.metadata.timestamp,
                event.metadata.correlation_id,
                event.metadata.session_id,
                event.metadata.account,
                event.metadata.workspace,
                event.metadata.strategy_version,
                event.metadata.model_version,
                event.metadata.feature_version,
                event.metadata.configuration_version,
                event.metadata.checksum,
                event.metadata.previous_checksum,
                payload_bytes,
                1 if compressed else 0,
            ))
            conn.commit()
    
    def get_events(self, query: EventQuery) -> List[Event]:
        """Get events matching query"""
        conditions, params = query.to_sql_conditions()
        
        sql = "SELECT * FROM events"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY sequence_number ASC"
        sql += f" LIMIT {query.limit} OFFSET {query.offset}"
        
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        
        events = []
        for row in rows:
            events.append(self._row_to_event(row))
        
        return events
    
    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert database row to event"""
        payload_bytes = row["payload"]
        if row["compressed"]:
            payload_json = zlib.decompress(payload_bytes).decode()
        else:
            payload_json = payload_bytes.decode()
        
        data = json.loads(payload_json)
        return Event.from_dict(data)
    
    def get_event_count(self, query: Optional[EventQuery] = None) -> int:
        """Get count of events matching query"""
        if query is None:
            query = EventQuery()
        
        conditions, params = query.to_sql_conditions()
        
        sql = "SELECT COUNT(*) FROM events"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
        
        return row[0] if row else 0
    
    def get_sequence_range(
        self,
        start: int,
        end: int
    ) -> List[Event]:
        """Get events by sequence range"""
        query = EventQuery(start_sequence=start, end_sequence=end)
        return self.get_events(query)
    
    def get_last_sequence(self) -> int:
        """Get the last sequence number"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT MAX(sequence_number) FROM events"
            )
            row = cursor.fetchone()
        return row[0] if row and row[0] is not None else -1
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify event chain integrity"""
        errors = []
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM events ORDER BY sequence_number
            """)
            
            expected_checksum = ""
            prev_seq = -1
            
            for row in cursor:
                seq = row["sequence_number"]
                
                # Check sequence continuity
                if seq != prev_seq + 1:
                    errors.append(f"Sequence gap: expected {prev_seq + 1}, got {seq}")
                
                # Check previous checksum
                if row["previous_checksum"] != expected_checksum:
                    errors.append(f"Checksum chain broken at sequence {seq}")
                
                # Verify event checksum
                event = self._row_to_event(row)
                if not event.verify_integrity():
                    errors.append(f"Checksum verification failed at sequence {seq}")
                
                expected_checksum = row["checksum"]
                prev_seq = seq
        
        return {
            "valid": len(errors) == 0,
            "total_events": prev_seq + 1,
            "errors": errors,
        }
    
    def time_travel(
        self,
        at_timestamp: float
    ) -> List[Event]:
        """Get state at a specific point in time"""
        query = EventQuery(until=at_timestamp, limit=100000)
        return self.get_events(query)
    
    def replay(
        self,
        start_sequence: int = 0,
        end_sequence: Optional[int] = None,
        event_types: Optional[Set[EventType]] = None,
        filter_fn: Optional[Callable[[Event], bool]] = None
    ) -> Iterator[Event]:
        """Replay events with optional filtering"""
        if end_sequence is None:
            end_sequence = self.get_last_sequence()
        
        query = EventQuery(
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            event_types=event_types,
            limit=10000,
        )
        
        offset = 0
        while True:
            query.offset = offset
            events = self.get_events(query)
            
            if not events:
                break
            
            for event in events:
                if filter_fn is None or filter_fn(event):
                    yield event
            
            offset += len(events)
            
            if len(events) < query.limit:
                break


class EventReplay:
    """
    Event replay engine for deterministic reconstruction.
    """
    
    def __init__(self, event_store: EventStoreDB):
        self.store = event_store
        self._replay_handlers: Dict[EventType, List[Callable]] = {}
    
    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ) -> None:
        """Register a handler for replay"""
        if event_type not in self._replay_handlers:
            self._replay_handlers[event_type] = []
        self._replay_handlers[event_type].append(handler)
    
    def replay(
        self,
        start_sequence: int = 0,
        end_sequence: Optional[int] = None,
        event_types: Optional[Set[EventType]] = None,
        on_event: Optional[Callable[[Event], None]] = None
    ) -> Dict[str, Any]:
        """Replay events and return statistics"""
        stats = {
            "total_events": 0,
            "by_type": {},
            "handlers_called": 0,
            "errors": [],
            "start_time": time.time(),
            "end_time": 0,
        }
        
        for event in self.store.replay(start_sequence, end_sequence, event_types):
            stats["total_events"] += 1
            
            # Track by type
            etype = event.event_type.value
            stats["by_type"][etype] = stats["by_type"].get(etype, 0) + 1
            
            # Call handlers
            handlers = self._replay_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    handler(event)
                    stats["handlers_called"] += 1
                except Exception as e:
                    stats["errors"].append({
                        "event_id": event.metadata.event_id,
                        "handler": str(handler),
                        "error": str(e),
                    })
            
            # Call global handler
            if on_event:
                try:
                    on_event(event)
                    stats["handlers_called"] += 1
                except Exception as e:
                    stats["errors"].append({
                        "event_id": event.metadata.event_id,
                        "handler": "global",
                        "error": str(e),
                    })
        
        stats["end_time"] = time.time()
        stats["duration_seconds"] = stats["end_time"] - stats["start_time"]
        
        return stats
    
    def compare_replay(
        self,
        original_events: List[Event],
        replayed_events: List[Event]
    ) -> Dict[str, Any]:
        """Compare original execution against replay"""
        diff = {
            "total_original": len(original_events),
            "total_replayed": len(replayed_events),
            "matches": 0,
            "mismatches": [],
            "integrity_score": 0,
        }
        
        # Check counts
        if len(original_events) != len(replayed_events):
            diff["mismatches"].append(
                f"Event count mismatch: {len(original_events)} vs {len(replayed_events)}"
            )
        
        # Compare events
        for i, (orig, replay) in enumerate(zip(original_events, replayed_events)):
            if orig.metadata.event_id == replay.metadata.event_id:
                diff["matches"] += 1
            else:
                diff["mismatches"].append(
                    f"Event {i}: ID mismatch {orig.metadata.event_id} vs {replay.metadata.event_id}"
                )
        
        # Calculate integrity score
        if original_events:
            diff["integrity_score"] = diff["matches"] / len(original_events)
        
        return diff
