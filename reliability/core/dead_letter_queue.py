"""
Dead Letter Queue Implementation
================================

Handles failed messages that couldn't be processed successfully.
Supports message replay, inspection, and manual intervention.
"""

import asyncio
import json
import time
import uuid
import logging
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Callable, Any, Optional, List, Dict, Deque
from collections import deque
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Status of a message in the DLQ"""
    PENDING = "pending"          # Awaiting review
    REPLAYING = "replaying"      # Currently being replayed
    REPLAYED = "replayed"        # Successfully replayed
    DEAD = "dead"               # Permanently failed
    ABANDONED = "abandoned"     # Manually abandoned


class FailureReason(Enum):
    """Categories of failure reasons"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


@dataclass
class MessageEnvelope:
    """
    Wrapper for messages in the Dead Letter Queue.
    Contains original message plus metadata for debugging.
    """
    id: str
    original_topic: str
    original_partition: Optional[int]
    original_offset: Optional[int]
    payload: Any
    headers: Dict[str, str]
    metadata: Dict[str, Any]
    status: MessageStatus
    failure_reason: FailureReason
    failure_details: str
    exception_type: Optional[str]
    exception_message: Optional[str]
    retry_count: int
    max_retries: int
    created_at: float
    updated_at: float
    first_failure_at: Optional[float] = None
    last_retry_at: Optional[float] = None
    replayed_at: Optional[float] = None
    processing_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings for JSON serialization
        data['status'] = self.status.value
        data['failure_reason'] = self.failure_reason.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        """Create from dictionary"""
        data['status'] = MessageStatus(data['status'])
        data['failure_reason'] = FailureReason(data['failure_reason'])
        return cls(**data)
    
    def generate_deduplication_key(self) -> str:
        """Generate a key for deduplication"""
        content = f"{self.original_topic}:{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class DLQStats:
    """Statistics for Dead Letter Queue monitoring"""
    total_messages: int = 0
    pending_messages: int = 0
    replaying_messages: int = 0
    replayed_messages: int = 0
    dead_messages: int = 0
    abandoned_messages: int = 0
    total_replay_attempts: int = 0
    successful_replays: int = 0
    failed_replays: int = 0
    oldest_pending_age_seconds: float = 0.0
    mean_processing_time_ms: float = 0.0
    last_activity_time: Optional[float] = None


class DeadLetterQueue:
    """
    Dead Letter Queue for handling failed messages.
    
    Features:
    - Persistent storage of failed messages
    - Configurable retry policies
    - Message replay capability
    - Deduplication
    - Statistics tracking
    - Multiple failure reason categories
    """
    
    def __init__(
        self,
        name: str,
        storage_path: Optional[str] = None,
        max_retries: int = 3,
        default_timeout: float = 30.0
    ):
        self.name = name
        self.storage_path = Path(storage_path) if storage_path else Path(f".dlq_{name}")
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        
        self._messages: Dict[str, MessageEnvelope] = {}
        self._pending_queue: Deque[str] = deque()
        self._stats = DLQStats()
        self._lock = threading.Lock()
        self._replay_handlers: Dict[str, Callable] = {}
        self._on_message_handler: Optional[Callable] = None
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load any persisted messages
        self._load_persisted()
    
    def _generate_id(self) -> str:
        """Generate unique message ID"""
        return f"dlq_{uuid.uuid4().hex[:12]}"
    
    def _persist_message(self, message: MessageEnvelope) -> None:
        """Persist message to disk"""
        try:
            message_file = self.storage_path / f"{message.id}.json"
            with open(message_file, 'w') as f:
                json.dump(message.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist DLQ message: {e}")
    
    def _load_persisted(self) -> None:
        """Load persisted messages on startup"""
        try:
            for message_file in self.storage_path.glob("*.json"):
                try:
                    with open(message_file) as f:
                        data = json.load(f)
                    message = MessageEnvelope.from_dict(data)
                    self._messages[message.id] = message
                    
                    if message.status == MessageStatus.PENDING:
                        self._pending_queue.append(message.id)
                except Exception as e:
                    logger.error(f"Failed to load message {message_file}: {e}")
            
            self._update_stats()
            logger.info(f"Loaded {len(self._messages)} messages from DLQ storage")
        except Exception as e:
            logger.error(f"Failed to load DLQ storage: {e}")
    
    def _update_stats(self) -> None:
        """Update DLQ statistics"""
        self._stats.total_messages = len(self._messages)
        self._stats.pending_messages = sum(
            1 for m in self._messages.values() 
            if m.status == MessageStatus.PENDING
        )
        self._stats.replaying_messages = sum(
            1 for m in self._messages.values() 
            if m.status == MessageStatus.REPLAYING
        )
        self._stats.replayed_messages = sum(
            1 for m in self._messages.values() 
            if m.status == MessageStatus.REPLAYED
        )
        self._stats.dead_messages = sum(
            1 for m in self._messages.values() 
            if m.status == MessageStatus.DEAD
        )
        self._stats.abandoned_messages = sum(
            1 for m in self._messages.values() 
            if m.status == MessageStatus.ABANDONED
        )
        
        # Calculate oldest pending message age
        pending = [
            m for m in self._messages.values() 
            if m.status == MessageStatus.PENDING
        ]
        if pending:
            oldest = min(pending, key=lambda m: m.created_at)
            self._stats.oldest_pending_age_seconds = time.time() - oldest.created_at
        else:
            self._stats.oldest_pending_age_seconds = 0.0
        
        self._stats.last_activity_time = time.time()
    
    def add(
        self,
        topic: str,
        payload: Any,
        exception: Exception,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        failure_reason: Optional[FailureReason] = None,
        max_retries: Optional[int] = None
    ) -> str:
        """
        Add a failed message to the Dead Letter Queue.
        
        Args:
            topic: Original topic/channel name
            payload: The message payload that failed
            exception: The exception that caused the failure
            partition: Original partition (for kafka-style systems)
            offset: Original offset (for kafka-style systems)
            headers: Optional message headers
            metadata: Additional metadata
            failure_reason: Categorized failure reason
            max_retries: Override default max retries
            
        Returns:
            The ID of the added message
        """
        with self._lock:
            message_id = self._generate_id()
            
            # Determine failure reason if not provided
            if failure_reason is None:
                failure_reason = self._categorize_failure(exception)
            
            # Get exception details
            exception_type = type(exception).__name__
            exception_message = str(exception)
            
            now = time.time()
            message = MessageEnvelope(
                id=message_id,
                original_topic=topic,
                original_partition=partition,
                original_offset=offset,
                payload=payload,
                headers=headers or {},
                metadata=metadata or {},
                status=MessageStatus.PENDING,
                failure_reason=failure_reason,
                failure_details=f"{exception_type}: {exception_message}",
                exception_type=exception_type,
                exception_message=exception_message,
                retry_count=0,
                max_retries=max_retries or self.max_retries,
                created_at=now,
                updated_at=now,
                first_failure_at=now
            )
            
            self._messages[message_id] = message
            self._pending_queue.append(message_id)
            
            self._persist_message(message)
            self._update_stats()
            
            logger.warning(
                f"Message added to DLQ '{self.name}': id={message_id}, "
                f"topic={topic}, reason={failure_reason.value}"
            )
            
            # Notify handler if registered
            if self._on_message_handler:
                try:
                    self._on_message_handler(message)
                except Exception as e:
                    logger.error(f"DLQ message handler failed: {e}")
            
            return message_id
    
    def _categorize_failure(self, exception: Exception) -> FailureReason:
        """Categorize an exception into a failure reason"""
        exception_str = str(exception).lower()
        exception_type = type(exception).__name__.lower()
        combined = f"{exception_type} {exception_str}"
        
        if 'timeout' in combined or 'timed out' in combined:
            return FailureReason.TIMEOUT
        if any(term in combined for term in ['connection', 'refused', 'unreachable', 'network']):
            return FailureReason.CONNECTION_ERROR
        if any(term in combined for term in ['validation', 'invalid', 'malformed', 'schema']):
            return FailureReason.VALIDATION_ERROR
        if any(term in combined for term in ['resource', 'memory', 'disk', 'quota', 'limit']):
            return FailureReason.RESOURCE_EXHAUSTED
        if any(term in combined for term in ['logic', 'rule', 'constraint', 'business']):
            return FailureReason.BUSINESS_LOGIC_ERROR
        
        return FailureReason.UNKNOWN
    
    def register_handler(self, topic: str, handler: Callable) -> None:
        """
        Register a replay handler for a topic.
        
        Args:
            topic: Topic name to handle
            handler: Async function(topic, payload, headers) -> bool
        """
        self._replay_handlers[topic] = handler
        logger.info(f"Registered DLQ handler for topic: {topic}")
    
    def set_message_handler(self, handler: Callable[[MessageEnvelope], None]) -> None:
        """Set a handler called when new messages arrive"""
        self._on_message_handler = handler
    
    async def replay(self, message_id: str) -> bool:
        """
        Attempt to replay a single message.
        
        Args:
            message_id: ID of message to replay
            
        Returns:
            True if replay was successful
        """
        with self._lock:
            if message_id not in self._messages:
                logger.error(f"Message {message_id} not found in DLQ")
                return False
            
            message = self._messages[message_id]
            
            if message.status not in [MessageStatus.PENDING, MessageStatus.DEAD]:
                logger.warning(f"Message {message_id} is not replayable (status: {message.status})")
                return False
            
            message.status = MessageStatus.REPLAYING
            message.updated_at = time.time()
            self._persist_message(message)
        
        try:
            # Get handler for this topic
            handler = self._replay_handlers.get(message.original_topic)
            
            if not handler:
                logger.error(f"No handler registered for topic: {message.original_topic}")
                message.status = MessageStatus.DEAD
                message.failure_details = f"No handler for topic: {message.original_topic}"
                self._stats.failed_replays += 1
                return False
            
            # Execute handler
            start_time = time.time()
            success = await handler(
                message.original_topic,
                message.payload,
                message.headers
            )
            processing_time = (time.time() - start_time) * 1000
            
            with self._lock:
                message = self._messages[message_id]
                message.status = MessageStatus.REPLAYED if success else MessageStatus.PENDING
                message.retry_count += 1
                message.last_retry_at = time.time()
                message.replayed_at = time.time() if success else None
                message.processing_time_ms = processing_time
                message.updated_at = time.time()
                
                if not success:
                    # Check if should be marked dead
                    if message.retry_count >= message.max_retries:
                        message.status = MessageStatus.DEAD
                        logger.error(f"Message {message_id} exceeded max retries, marking as dead")
                
                self._persist_message(message)
                self._update_stats()
                
                self._stats.total_replay_attempts += 1
                if success:
                    self._stats.successful_replays += 1
                else:
                    self._stats.failed_replays += 1
                
                return success
                
        except Exception as e:
            logger.error(f"Replay failed for message {message_id}: {e}")
            
            with self._lock:
                message = self._messages[message_id]
                message.status = MessageStatus.DEAD if message.retry_count >= message.max_retries else MessageStatus.PENDING
                message.retry_count += 1
                message.last_retry_at = time.time()
                message.failure_details = f"Replay error: {type(e).__name__}: {e}"
                message.updated_at = time.time()
                self._persist_message(message)
                self._update_stats()
                self._stats.failed_replays += 1
                
                return False
    
    async def replay_all(
        self,
        batch_size: int = 10,
        parallel: bool = True,
        topics: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Replay all pending messages.
        
        Args:
            batch_size: Number of messages to process at once
            parallel: Whether to process messages in parallel
            topics: Optional list of topics to replay (None = all)
            
        Returns:
            Dict with counts of success/failure
        """
        results = {"success": 0, "failure": 0, "skipped": 0}
        
        # Get pending messages
        with self._lock:
            pending_ids = [
                mid for mid in self._pending_queue
                if mid in self._messages
                and self._messages[mid].status == MessageStatus.PENDING
                and (topics is None or self._messages[mid].original_topic in topics)
            ]
        
        if parallel:
            # Process in batches with concurrency
            for i in range(0, len(pending_ids), batch_size):
                batch = pending_ids[i:i + batch_size]
                tasks = [self.replay(mid) for mid in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        results["failure"] += 1
                    elif result:
                        results["success"] += 1
                    else:
                        results["failure"] += 1
        else:
            # Process sequentially
            for mid in pending_ids:
                success = await self.replay(mid)
                if success:
                    results["success"] += 1
                else:
                    results["failure"] += 1
        
        logger.info(f"DLQ replay completed: {results}")
        return results
    
    def abandon(self, message_id: str, reason: str) -> None:
        """
        Manually abandon a message.
        
        Args:
            message_id: ID of message to abandon
            reason: Reason for abandonment
        """
        with self._lock:
            if message_id not in self._messages:
                return
            
            message = self._messages[message_id]
            message.status = MessageStatus.ABANDONED
            message.failure_details = f"Abandoned: {reason}"
            message.updated_at = time.time()
            
            # Remove from pending queue
            if message_id in self._pending_queue:
                self._pending_queue.remove(message_id)
            
            self._persist_message(message)
            self._update_stats()
    
    def get_message(self, message_id: str) -> Optional[MessageEnvelope]:
        """Get a specific message by ID"""
        return self._messages.get(message_id)
    
    def get_pending(self, limit: Optional[int] = None) -> List[MessageEnvelope]:
        """Get pending messages"""
        pending = sorted(
            [m for m in self._messages.values() if m.status == MessageStatus.PENDING],
            key=lambda m: m.created_at
        )
        return pending[:limit] if limit else pending
    
    def get_stats(self) -> DLQStats:
        """Get DLQ statistics"""
        return self._stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        return {
            "name": self.name,
            "stats": {
                "total_messages": self._stats.total_messages,
                "pending_messages": self._stats.pending_messages,
                "replaying_messages": self._stats.replaying_messages,
                "replayed_messages": self._stats.replayed_messages,
                "dead_messages": self._stats.dead_messages,
                "abandoned_messages": self._stats.abandoned_messages,
                "total_replay_attempts": self._stats.total_replay_attempts,
                "successful_replays": self._stats.successful_replays,
                "failed_replays": self._stats.failed_replays,
                "oldest_pending_age_seconds": round(self._stats.oldest_pending_age_seconds, 2),
                "mean_processing_time_ms": round(self._stats.mean_processing_time_ms, 2),
                "replay_success_rate": (
                    self._stats.successful_replays / max(1, self._stats.total_replay_attempts) * 100
                )
            },
            "failure_reasons": {
                reason.value: sum(
                    1 for m in self._messages.values()
                    if m.failure_reason == reason
                )
                for reason in FailureReason
            }
        }
