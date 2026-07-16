"""
Message Replay Queue
===================

Provides message replay and event replay capabilities.
"""

import asyncio
import logging
import time
import json
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Generic, TypeVar
from enum import Enum
from collections import deque
from pathlib import Path

logger = logging.getLogger(__name__)
T = TypeVar('T')


class ReplayStatus(Enum):
    """Status of replay operations"""
    PENDING = "pending"
    REPLAYING = "replaying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MessageRecord:
    """A message in the replay queue"""
    id: str
    topic: str
    partition: Optional[int]
    offset: Optional[int]
    key: Optional[str]
    value: Any
    headers: Dict[str, str]
    timestamp: float
    sequence: int
    
    # Replay state
    status: ReplayStatus = ReplayStatus.PENDING
    replay_count: int = 0
    last_replay_at: Optional[float] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "key": self.key,
            "value": self.value,
            "headers": self.headers,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "status": self.status.value,
            "replay_count": self.replay_count,
            "last_replay_at": self.last_replay_at,
            "last_error": self.last_error,
        }


@dataclass
class EventRecord:
    """An event for replay"""
    id: str
    event_type: str
    source: str
    timestamp: float
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    
    # Replay state
    status: ReplayStatus = ReplayStatus.PENDING
    replay_count: int = 0
    replayed_at: Optional[float] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
            "status": self.status.value,
            "replay_count": self.replay_count,
            "replayed_at": self.replayed_at,
            "last_error": self.last_error,
        }


@dataclass
class ReplayStats:
    """Statistics for replay operations"""
    total_messages: int = 0
    pending_messages: int = 0
    replaying_messages: int = 0
    completed_messages: int = 0
    failed_messages: int = 0
    skipped_messages: int = 0
    total_events: int = 0
    pending_events: int = 0
    completed_events: int = 0
    failed_events: int = 0
    last_replay_time: Optional[float] = None


class MessageReplayQueue(Generic[T]):
    """
    Message replay queue with support for replay, skip, and recovery.
    
    Features:
    - Message buffering before processing
    - Guaranteed delivery
    - At-least-once delivery semantics
    - Manual replay control
    - Statistics tracking
    """
    
    def __init__(
        self,
        name: str,
        buffer_size: int = 1000,
        storage_path: Optional[str] = None
    ):
        self.name = name
        self.buffer_size = buffer_size
        self.storage_path = Path(storage_path) if storage_path else Path(f".replay_{name}")
        
        self._buffer: deque = deque(maxlen=buffer_size)
        self._pending: Dict[str, MessageRecord] = {}
        self._completed: Dict[str, MessageRecord] = {}
        self._failed: Dict[str, MessageRecord] = {}
        
        self._stats = ReplayStats()
        self._sequence = 0
        self._lock = asyncio.Lock()
        
        # Handler for processing messages
        self._handler: Optional[Callable] = None
        
        # Ensure storage exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"MessageReplayQueue '{name}' initialized")
    
    def set_handler(
        self,
        handler: Callable[[T], Any]
    ) -> None:
        """Set the message processing handler"""
        self._handler = handler
    
    async def publish(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None,
        offset: Optional[int] = None
    ) -> str:
        """
        Publish a message to the replay queue.
        
        Messages are buffered and can be replayed if processing fails.
        
        Args:
            topic: Message topic
            value: Message value
            key: Optional message key
            headers: Optional message headers
            partition: Optional partition number
            offset: Optional offset
            
        Returns:
            Message ID
        """
        async with self._lock:
            self._sequence += 1
            message_id = str(uuid.uuid4())
            
            message = MessageRecord(
                id=message_id,
                topic=topic,
                partition=partition,
                offset=offset,
                key=key,
                value=value,
                headers=headers or {},
                timestamp=time.time(),
                sequence=self._sequence
            )
            
            self._buffer.append(message)
            self._pending[message_id] = message
            self._stats.total_messages += 1
            self._stats.pending_messages += 1
            
            # Persist to storage
            self._persist_message(message)
            
            return message_id
    
    def _persist_message(self, message: MessageRecord) -> None:
        """Persist message to disk"""
        try:
            msg_file = self.storage_path / f"{message.id}.json"
            with open(msg_file, 'w') as f:
                json.dump(message.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist message {message.id}: {e}")
    
    async def process_next(self) -> Optional[str]:
        """
        Process the next message in the queue.
        
        Returns:
            Message ID if processed, None if queue is empty
        """
        async with self._lock:
            if not self._buffer:
                return None
            
            message = self._buffer.popleft()
            
            if message.status != ReplayStatus.PENDING:
                return message.id
            
            message.status = ReplayStatus.REPLAYING
            self._stats.pending_messages -= 1
            self._stats.replaying_messages += 1
        
        # Process message
        try:
            if self._handler:
                if asyncio.iscoroutinefunction(self._handler):
                    await self._handler(message.value)
                else:
                    self._handler(message.value)
            
            # Mark as completed
            async with self._lock:
                message.status = ReplayStatus.COMPLETED
                message.replay_count += 1
                message.last_replay_at = time.time()
                
                self._stats.replaying_messages -= 1
                self._stats.completed_messages += 1
                self._stats.last_replay_time = time.time()
                
                # Move to completed
                del self._pending[message.id]
                self._completed[message.id] = message
            
            return message.id
            
        except Exception as e:
            # Mark as failed
            async with self._lock:
                message.status = ReplayStatus.FAILED
                message.replay_count += 1
                message.last_replay_at = time.time()
                message.last_error = f"{type(e).__name__}: {e}"
                
                self._stats.replaying_messages -= 1
                self._stats.failed_messages += 1
            
            logger.error(f"Message {message.id} processing failed: {e}")
            return message.id
    
    async def replay_message(self, message_id: str) -> bool:
        """
        Replay a specific message.
        
        Args:
            message_id: Message to replay
            
        Returns:
            True if replay succeeded
        """
        async with self._lock:
            if message_id not in self._pending and message_id not in self._failed:
                logger.warning(f"Message {message_id} not found")
                return False
            
            message = self._pending.get(message_id) or self._failed.get(message_id)
            message.status = ReplayStatus.PENDING
            message.replay_count = 0
            message.last_error = None
            
            if message_id in self._failed:
                del self._failed[message_id]
                self._stats.failed_messages -= 1
            
            self._buffer.append(message)
            self._pending[message_id] = message
            self._stats.pending_messages += 1
        
        return True
    
    async def skip_message(self, message_id: str) -> bool:
        """
        Skip a message without replaying.
        
        Args:
            message_id: Message to skip
            
        Returns:
            True if skipped successfully
        """
        async with self._lock:
            if message_id not in self._pending:
                return False
            
            message = self._pending[message_id]
            message.status = ReplayStatus.SKIPPED
            
            del self._pending[message_id]
            self._buffer.remove(message)
            
            self._stats.pending_messages -= 1
            self._stats.skipped_messages += 1
        
        return True
    
    async def replay_all(
        self,
        topics: Optional[List[str]] = None,
        since: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Replay all pending messages.
        
        Args:
            topics: Optional list of topics to replay
            since: Optional timestamp to replay messages since
            
        Returns:
            Dict with counts of success/failure
        """
        results = {"processed": 0, "failed": 0, "skipped": 0}
        
        # Get messages to replay
        async with self._lock:
            messages_to_replay = [
                m for m in self._buffer
                if m.status == ReplayStatus.PENDING
                and (topics is None or m.topic in topics)
                and (since is None or m.timestamp >= since)
            ]
        
        for message in messages_to_replay:
            await self.replay_message(message.id)
            result = await self.process_next()
            
            if result:
                if message.status == ReplayStatus.COMPLETED:
                    results["processed"] += 1
                elif message.status == ReplayStatus.FAILED:
                    results["failed"] += 1
                else:
                    results["skipped"] += 1
        
        return results
    
    def get_pending(self, limit: Optional[int] = None) -> List[MessageRecord]:
        """Get pending messages"""
        pending = [m for m in self._buffer if m.status == ReplayStatus.PENDING]
        return pending[:limit] if limit else pending
    
    def get_failed(self, limit: Optional[int] = None) -> List[MessageRecord]:
        """Get failed messages"""
        failed = list(self._failed.values())
        return failed[:limit] if limit else failed
    
    def get_stats(self) -> ReplayStats:
        """Get replay statistics"""
        return self._stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health report"""
        return {
            "name": self.name,
            "stats": {
                "total_messages": self._stats.total_messages,
                "pending_messages": self._stats.pending_messages,
                "replaying_messages": self._stats.replaying_messages,
                "completed_messages": self._stats.completed_messages,
                "failed_messages": self._stats.failed_messages,
                "skipped_messages": self._stats.skipped_messages,
                "success_rate": round(
                    self._stats.completed_messages /
                    max(1, self._stats.total_messages) * 100,
                    2
                )
            },
            "buffer_size": len(self._buffer),
            "buffer_capacity": self.buffer_size
        }


class EventReplayLog:
    """
    Event replay log for capturing and replaying events.
    
    Features:
    - Append-only event log
    - Cursor-based replay
    - Event filtering
    - Bulk replay
    """
    
    def __init__(
        self,
        name: str,
        storage_path: Optional[str] = None
    ):
        self.name = name
        self.storage_path = Path(storage_path) if storage_path else Path(f".events_{name}")
        
        self._events: List[EventRecord] = []
        self._stats = ReplayStats()
        self._cursors: Dict[str, int] = {}  # consumer -> last replayed sequence
        self._lock = asyncio.Lock()
        
        self._event_handlers: Dict[str, Callable] = {}
        
        # Ensure storage exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load previous events
        self._load_events()
        
        logger.info(f"EventReplayLog '{name}' initialized with {len(self._events)} events")
    
    def _load_events(self) -> None:
        """Load events from storage"""
        try:
            event_file = self.storage_path / "events.jsonl"
            if event_file.exists():
                with open(event_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            event = EventRecord(
                                id=data["id"],
                                event_type=data["event_type"],
                                source=data["source"],
                                timestamp=data["timestamp"],
                                data=data["data"],
                                metadata=data.get("metadata", {}),
                                status=ReplayStatus(data.get("status", "completed")),
                                replay_count=data.get("replay_count", 0),
                                replayed_at=data.get("replayed_at"),
                                last_error=data.get("last_error")
                            )
                            self._events.append(event)
        except Exception as e:
            logger.error(f"Failed to load events: {e}")
    
    def _persist_event(self, event: EventRecord) -> None:
        """Persist event to storage"""
        try:
            event_file = self.storage_path / "events.jsonl"
            with open(event_file, 'a') as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist event {event.id}: {e}")
    
    def register_handler(
        self,
        event_type: str,
        handler: Callable[[EventRecord], Any]
    ) -> None:
        """Register a handler for an event type"""
        self._event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def emit(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Emit an event to the log.
        
        Args:
            event_type: Type of event
            source: Source of event
            data: Event data
            metadata: Optional metadata
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        
        event = EventRecord(
            id=event_id,
            event_type=event_type,
            source=source,
            timestamp=time.time(),
            data=data,
            metadata=metadata or {}
        )
        
        self._events.append(event)
        self._stats.total_events += 1
        self._persist_event(event)
        
        return event_id
    
    async def replay(
        self,
        consumer: str,
        handler: Optional[Callable] = None,
        event_types: Optional[List[str]] = None,
        since: Optional[float] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Replay events for a consumer.
        
        Args:
            consumer: Consumer ID for cursor tracking
            handler: Optional handler function
            event_types: Optional list of event types to replay
            since: Optional timestamp to replay from
            limit: Optional limit on number of events
            
        Returns:
            Dict with counts of processed events
        """
        results = {"processed": 0, "failed": 0}
        
        # Get replay position
        start_idx = self._cursors.get(consumer, 0)
        
        # Filter events
        events_to_replay = []
        for i, event in enumerate(self._events[start_idx:], start=start_idx):
            if event.status == ReplayStatus.COMPLETED:
                continue
            
            if event_types and event.event_type not in event_types:
                continue
            
            if since and event.timestamp < since:
                continue
            
            events_to_replay.append((i, event))
        
        # Apply limit
        if limit:
            events_to_replay = events_to_replay[:limit]
        
        for idx, event in events_to_replay:
            try:
                # Use specific handler or registered handler
                event_handler = handler or self._event_handlers.get(event.event_type)
                
                if event_handler:
                    if asyncio.iscoroutinefunction(event_handler):
                        await event_handler(event)
                    else:
                        event_handler(event)
                
                event.status = ReplayStatus.COMPLETED
                event.replay_count += 1
                event.replayed_at = time.time()
                
                results["processed"] += 1
                self._stats.completed_events += 1
                
            except Exception as e:
                event.status = ReplayStatus.FAILED
                event.last_error = f"{type(e).__name__}: {e}"
                results["failed"] += 1
                self._stats.failed_events += 1
                
                logger.error(f"Event {event.id} replay failed: {e}")
            
            # Update cursor
            self._cursors[consumer] = idx + 1
        
        return results
    
    def get_cursor(self, consumer: str) -> int:
        """Get replay cursor for a consumer"""
        return self._cursors.get(consumer, 0)
    
    def set_cursor(self, consumer: str, position: int) -> None:
        """Set replay cursor for a consumer"""
        self._cursors[consumer] = position
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[EventRecord]:
        """Get events with optional filtering"""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if source:
            events = [e for e in events if e.source == source]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health report"""
        return {
            "name": self.name,
            "stats": {
                "total_events": self._stats.total_events,
                "pending_events": len([e for e in self._events if e.status == ReplayStatus.PENDING]),
                "completed_events": self._stats.completed_events,
                "failed_events": self._stats.failed_events,
            },
            "consumers": {
                consumer: cursor
                for consumer, cursor in self._cursors.items()
            },
            "event_types": list(self._event_handlers.keys()),
            "storage_size_mb": sum(
                f.stat().st_size
                for f in self.storage_path.glob("**/*")
                if f.is_file()
            ) / 1024 / 1024
        }
