"""
Memory Manager - Multi-Layer Memory System

Provides long-term memory with multiple layers for AI trading decisions.
"""

import json
import logging
import os
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory"""
    SHORT_TERM = "short_term"  # Current context (last few minutes)
    SESSION = "session"        # Current session
    HISTORICAL = "historical"  # Historical events
    TRADE = "trade"           # Trade records
    PATTERN = "pattern"       # Pattern recognition
    STRATEGY = "strategy"     # Strategy performance
    FAILURE = "failure"       # Failure records
    REGIME = "regime"         # Market regime changes
    MARKET = "market"         # Market data summaries
    MODEL = "model"           # Model states


@dataclass
class MemoryEntry:
    """A memory entry"""
    id: str
    memory_type: MemoryType
    timestamp: datetime
    
    # Content
    key: str
    value: Any
    embedding: Optional[List[float]] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1
    source: str = ""
    correlation_id: Optional[str] = None
    
    # Relationships
    related_ids: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    
    # Access tracking
    access_count: int = 0
    last_access: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "key": self.key,
            "value": self.value,
            "tags": self.tags,
            "importance": self.importance,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "related_ids": self.related_ids,
            "access_count": self.access_count,
            "last_access": self.last_access.isoformat() if self.last_access else None,
        }


class MemoryLayer:
    """A memory layer with specific retention policy"""
    
    def __init__(
        self,
        memory_type: MemoryType,
        max_size: int = 10000,
        ttl_seconds: Optional[int] = None,
        importance_threshold: float = 0,
    ):
        self.memory_type = memory_type
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.importance_threshold = importance_threshold
        
        self._entries: Dict[str, MemoryEntry] = {}
        self._index: Dict[str, List[str]] = defaultdict(list)  # tag -> entry_ids
        self._access_order: deque = deque()
    
    def add(self, entry: MemoryEntry) -> None:
        """Add an entry to this layer"""
        # Check TTL
        if self.ttl_seconds:
            age = (datetime.now(timezone.utc) - entry.timestamp).total_seconds()
            if age > self.ttl_seconds:
                return
        
        # Check importance threshold
        if entry.importance < self.importance_threshold:
            return
        
        self._entries[entry.id] = entry
        
        # Update index
        for tag in entry.tags:
            if entry.id not in self._index[tag]:
                self._index[tag].append(entry.id)
        
        # Update access order
        if entry.id not in self._access_order:
            self._access_order.append(entry.id)
        
        # Enforce max size
        if len(self._entries) > self.max_size:
            self._evict_oldest()
    
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get an entry"""
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_access = datetime.now(timezone.utc)
        return entry
    
    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Search entries"""
        results = list(self._entries.values())
        
        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._index.get(tag, []))
            results = [e for e in results if e.id in tag_ids]
        
        if since:
            results = [e for e in results if e.timestamp >= since]
        
        if until:
            results = [e for e in results if e.timestamp <= until]
        
        # Sort by importance and recency
        results.sort(
            key=lambda e: (e.importance, e.timestamp),
            reverse=True
        )
        
        return results[:limit]
    
    def _evict_oldest(self) -> None:
        """Evict oldest entries"""
        while len(self._entries) > self.max_size and self._access_order:
            oldest_id = self._access_order.popleft()
            if oldest_id in self._entries:
                entry = self._entries.pop(oldest_id)
                # Remove from index
                for tag in entry.tags:
                    if oldest_id in self._index[tag]:
                        self._index[tag].remove(oldest_id)


class MemoryManager:
    """
    Multi-layer memory system for AI trading.
    
    Layers:
    - Short-term: Last few minutes (60 seconds TTL, 1000 entries)
    - Session: Current session (24 hours, 10000 entries)
    - Historical: All historical (no TTL, 100000 entries)
    - Trade: Trade records (no TTL, 50000 entries)
    - Pattern: Pattern detections (no TTL, 10000 entries)
    - Strategy: Strategy performance (no TTL, 5000 entries)
    - Failure: Failure records (no TTL, 5000 entries)
    - Regime: Market regime changes (no TTL, 1000 entries)
    """
    
    def __init__(self, storage_path: str = "data/memory"):
        self._storage_path = storage_path
        
        # Initialize layers
        self._layers: Dict[MemoryType, MemoryLayer] = {
            MemoryType.SHORT_TERM: MemoryLayer(
                MemoryType.SHORT_TERM,
                max_size=1000,
                ttl_seconds=60,
            ),
            MemoryType.SESSION: MemoryLayer(
                MemoryType.SESSION,
                max_size=10000,
                ttl_seconds=86400,  # 24 hours
            ),
            MemoryType.HISTORICAL: MemoryLayer(
                MemoryType.HISTORICAL,
                max_size=100000,
            ),
            MemoryType.TRADE: MemoryLayer(
                MemoryType.TRADE,
                max_size=50000,
            ),
            MemoryType.PATTERN: MemoryLayer(
                MemoryType.PATTERN,
                max_size=10000,
            ),
            MemoryType.STRATEGY: MemoryLayer(
                MemoryType.STRATEGY,
                max_size=5000,
            ),
            MemoryType.FAILURE: MemoryLayer(
                MemoryType.FAILURE,
                max_size=5000,
            ),
            MemoryType.REGIME: MemoryLayer(
                MemoryType.REGIME,
                max_size=1000,
            ),
            MemoryType.MARKET: MemoryLayer(
                MemoryType.MARKET,
                max_size=50000,
            ),
            MemoryType.MODEL: MemoryLayer(
                MemoryType.MODEL,
                max_size=1000,
            ),
        }
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_memory()
    
    def store(
        self,
        memory_type: MemoryType,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        source: str = "",
        correlation_id: Optional[str] = None,
        related_ids: Optional[List[str]] = None,
    ) -> MemoryEntry:
        """
        Store a memory entry.
        
        Args:
            memory_type: Type of memory
            key: Memory key
            value: Memory value
            tags: Optional tags
            importance: Importance score (0-1)
            source: Source of the memory
            correlation_id: Optional correlation ID
            related_ids: Related memory IDs
            
        Returns:
            Created MemoryEntry
        """
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            memory_type=memory_type,
            timestamp=datetime.now(timezone.utc),
            key=key,
            value=value,
            tags=tags or [],
            importance=importance,
            source=source,
            correlation_id=correlation_id,
            related_ids=related_ids or [],
        )
        
        self._layers[memory_type].add(entry)
        self._persist_entry(entry)
        
        logger.debug(f"Stored memory: {memory_type.value}/{key}")
        return entry
    
    def retrieve(
        self,
        memory_type: MemoryType,
        entry_id: str,
    ) -> Optional[MemoryEntry]:
        """Retrieve a specific memory entry"""
        return self._layers[memory_type].get(entry_id)
    
    def recall(
        self,
        memory_type: MemoryType,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Recall memories matching criteria"""
        return self._layers[memory_type].search(
            query=query,
            tags=tags,
            since=since,
            limit=limit,
        )
    
    def find_similar(
        self,
        memory_type: MemoryType,
        key_pattern: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Find similar memories by key"""
        entries = self._layers[memory_type].search(limit=1000)
        
        # Simple key similarity (could use embeddings)
        similar = []
        for entry in entries:
            if key_pattern.lower() in entry.key.lower():
                similar.append(entry)
                if len(similar) >= limit:
                    break
        
        return similar
    
    def get_recent_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Get recent trades"""
        trades = self.recall(
            MemoryType.TRADE,
            since=datetime.now(timezone.utc) - timedelta(days=30),
            limit=limit * 2,
        )
        
        if symbol:
            trades = [t for t in trades if t.value.get("symbol") == symbol]
        
        return trades[:limit]
    
    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[MemoryEntry]:
        """Get recognized patterns"""
        patterns = self.recall(
            MemoryType.PATTERN,
            limit=limit * 2,
        )
        
        if pattern_type:
            patterns = [p for p in patterns if p.value.get("pattern_type") == pattern_type]
        
        return patterns[:limit]
    
    def get_failures(
        self,
        since: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[MemoryEntry]:
        """Get failure records"""
        return self.recall(
            MemoryType.FAILURE,
            since=since,
            limit=limit,
        )
    
    def get_regime_history(
        self,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """Get market regime history"""
        return self.recall(
            MemoryType.REGIME,
            limit=limit,
        )
    
    def store_trade(
        self,
        trade_data: Dict[str, Any],
    ) -> MemoryEntry:
        """Store a trade record"""
        return self.store(
            memory_type=MemoryType.TRADE,
            key=f"trade_{trade_data.get('id', 'unknown')}",
            value=trade_data,
            tags=["trade", trade_data.get("symbol", "")],
            importance=0.8,
            source="execution_engine",
        )
    
    def store_pattern(
        self,
        pattern_data: Dict[str, Any],
    ) -> MemoryEntry:
        """Store a detected pattern"""
        return self.store(
            memory_type=MemoryType.PATTERN,
            key=f"pattern_{pattern_data.get('pattern_type', 'unknown')}",
            value=pattern_data,
            tags=["pattern", pattern_data.get("pattern_type", "")],
            importance=0.7,
            source="pattern_detector",
        )
    
    def store_failure(
        self,
        failure_data: Dict[str, Any],
    ) -> MemoryEntry:
        """Store a failure record"""
        return self.store(
            memory_type=MemoryType.FAILURE,
            key=f"failure_{failure_data.get('type', 'unknown')}",
            value=failure_data,
            tags=["failure", failure_data.get("type", "")],
            importance=0.9,  # Failures are important
            source=failure_data.get("source", "system"),
        )
    
    def store_regime_change(
        self,
        regime_data: Dict[str, Any],
    ) -> MemoryEntry:
        """Store a market regime change"""
        return self.store(
            memory_type=MemoryType.REGIME,
            key=f"regime_{regime_data.get('regime', 'unknown')}",
            value=regime_data,
            tags=["regime", regime_data.get("regime", "")],
            importance=0.9,
            source="regime_detector",
        )
    
    def _persist_entry(self, entry: MemoryEntry) -> None:
        """Persist entry to disk"""
        memory_dir = os.path.join(self._storage_path, entry.memory_type.value)
        os.makedirs(memory_dir, exist_ok=True)
        
        entry_file = os.path.join(memory_dir, f"{entry.id}.json")
        
        try:
            with open(entry_file, "w") as f:
                json.dump(entry.to_dict(), f)
        except Exception as e:
            logger.error(f"Failed to persist memory entry: {e}")
    
    def _load_memory(self) -> None:
        """Load memory from disk"""
        for memory_type in MemoryType:
            memory_dir = os.path.join(self._storage_path, memory_type.value)
            
            if not os.path.exists(memory_dir):
                continue
            
            try:
                for filename in os.listdir(memory_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(memory_dir, filename)
                        with open(filepath, "r") as f:
                            data = json.load(f)
                        
                        entry = MemoryEntry(
                            id=data["id"],
                            memory_type=MemoryType(data["memory_type"]),
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            key=data["key"],
                            value=data["value"],
                            tags=data.get("tags", []),
                            importance=data.get("importance", 0.5),
                            source=data.get("source", ""),
                            correlation_id=data.get("correlation_id"),
                            related_ids=data.get("related_ids", []),
                        )
                        
                        self._layers[memory_type].add(entry)
                
                logger.info(f"Loaded {memory_type.value} memory")
            except Exception as e:
                logger.error(f"Failed to load {memory_type.value} memory: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        stats = {}
        
        for memory_type, layer in self._layers.items():
            stats[memory_type.value] = {
                "entries": len(layer._entries),
                "max_size": layer.max_size,
                "ttl_seconds": layer.ttl_seconds,
            }
        
        return stats
