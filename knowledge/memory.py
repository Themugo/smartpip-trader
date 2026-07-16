"""
Organizational Memory
====================

Continuous learning and memory system for the organization.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A memory entry in the organizational memory"""
    entry_id: str
    memory_type: str  # "lesson", "pattern", "insight", "decision", "mistake"
    
    # Content
    title: str
    content: str
    context: str  # When/why this was recorded
    
    # Source
    source_entity_id: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    # Tags and categories
    tags: Set[str] = field(default_factory=set)
    category: str = ""
    
    # Impact
    impact_score: float = 0.0  # How impactful this memory is
    times_applied: int = 0  # How many times this has been used/applied
    
    # Quality
    confidence: float = 0.0
    verified: bool = False
    verified_by: Optional[str] = None
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    # Related memories
    related_memories: List[str] = field(default_factory=list)
    
    def record_access(self) -> None:
        """Record that this memory was accessed"""
        self.last_accessed = time.time()
    
    def apply(self) -> None:
        """Record that this memory was applied"""
        self.times_applied += 1
        self.impact_score = min(1.0, self.impact_score + 0.1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "memory_type": self.memory_type,
            "title": self.title,
            "tags": list(self.tags),
            "impact_score": self.impact_score,
            "times_applied": self.times_applied,
            "created_at": self.created_at,
        }


class OrganizationalMemory:
    """
    Organizational memory that continuously grows and improves.
    
    Captures and retains:
    - Lessons learned
    - Patterns discovered
    - Insights gained
    - Decisions made
    - Mistakes to avoid
    """
    
    def __init__(self, knowledge_store=None):
        self.store = knowledge_store
        self._memories: Dict[str, MemoryEntry] = {}
        
        # Index by type
        self._by_type: Dict[str, List[str]] = {}
        
        # Index by tag
        self._by_tag: Dict[str, List[str]] = {}
        
        # Learning callbacks
        self._learning_callbacks: List[Callable] = []
    
    # ========== Memory Management ==========
    
    def add_memory(
        self,
        memory_type: str,
        title: str,
        content: str,
        context: str = "",
        tags: Optional[List[str]] = None,
        category: str = "",
        source_entity_id: Optional[str] = None,
        source_entity_type: Optional[str] = None
    ) -> MemoryEntry:
        """Add a new memory"""
        memory = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            memory_type=memory_type,
            title=title,
            content=content,
            context=context,
            tags=set(tags) if tags else set(),
            category=category,
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
        )
        
        self._memories[memory.entry_id] = memory
        
        # Index by type
        if memory_type not in self._by_type:
            self._by_type[memory_type] = []
        self._by_type[memory_type].append(memory.entry_id)
        
        # Index by tags
        for tag in memory.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(memory.entry_id)
        
        logger.info(f"Added memory: {title}")
        
        # Trigger learning callbacks
        self._trigger_learning(memory)
        
        return memory
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory by ID"""
        memory = self._memories.get(memory_id)
        if memory:
            memory.record_access()
        return memory
    
    def get_memories_by_type(
        self,
        memory_type: str,
        limit: int = 50
    ) -> List[MemoryEntry]:
        """Get memories by type"""
        memory_ids = self._by_type.get(memory_type, [])
        memories = []
        
        for mid in memory_ids[-limit:]:
            memory = self._memories.get(mid)
            if memory:
                memories.append(memory)
        
        return memories
    
    def get_memories_by_tag(
        self,
        tag: str,
        limit: int = 50
    ) -> List[MemoryEntry]:
        """Get memories by tag"""
        memory_ids = self._by_tag.get(tag, [])
        memories = []
        
        for mid in memory_ids[-limit:]:
            memory = self._memories.get(mid)
            if memory:
                memories.append(memory)
        
        return memories
    
    def get_recent_memories(self, limit: int = 20) -> List[MemoryEntry]:
        """Get recent memories"""
        memories = sorted(
            self._memories.values(),
            key=lambda m: m.created_at,
            reverse=True
        )
        return memories[:limit]
    
    def get_most_valuable_memories(self, limit: int = 20) -> List[MemoryEntry]:
        """Get most valuable/impactful memories"""
        memories = sorted(
            self._memories.values(),
            key=lambda m: (m.impact_score, m.times_applied),
            reverse=True
        )
        return memories[:limit]
    
    def get_related_memories(
        self,
        memory_id: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Get memories related to a given memory"""
        memory = self._memories.get(memory_id)
        if not memory:
            return []
        
        # Get directly related
        related_ids = memory.related_memories[:limit]
        related = [self._memories[mid] for mid in related_ids if mid in self._memories]
        
        # Find by shared tags
        if len(related) < limit:
            for other in self._memories.values():
                if other.entry_id == memory_id:
                    continue
                if other.entry_id in related_ids:
                    continue
                
                shared_tags = memory.tags & other.tags
                if shared_tags:
                    related.append(other)
                    if len(related) >= limit:
                        break
        
        return related
    
    # ========== Memory Extraction ==========
    
    def learn_from_incident(
        self,
        incident_description: str,
        lessons: List[str],
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Learn from an incident"""
        memories = []
        
        for lesson in lessons:
            memory = self.add_memory(
                memory_type="lesson",
                title=f"Lesson from incident",
                content=lesson,
                context=incident_description,
                tags=["incident", "lesson"] + (tags or []),
                category="incident",
            )
            memories.append(memory)
        
        return memories
    
    def learn_from_success(
        self,
        success_description: str,
        key_factors: List[str],
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Learn from a success"""
        memories = []
        
        for factor in key_factors:
            memory = self.add_memory(
                memory_type="pattern",
                title=f"Success factor: {factor[:50]}",
                content=factor,
                context=success_description,
                tags=["success", "pattern"] + (tags or []),
                category="success",
            )
            memory.impact_score = 0.8
            memories.append(memory)
        
        return memories
    
    def learn_from_mistake(
        self,
        mistake_description: str,
        root_cause: str,
        correction: str,
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Learn from a mistake"""
        memories = [
            self.add_memory(
                memory_type="mistake",
                title=f"Mistake: {mistake_description[:50]}",
                content=mistake_description,
                context=root_cause,
                tags=["mistake", "avoid"] + (tags or []),
                category="mistake",
            ),
            self.add_memory(
                memory_type="lesson",
                title=f"Correction for previous mistake",
                content=correction,
                context=mistake_description,
                tags=["correction", "lesson"] + (tags or []),
                category="mistake",
            ),
        ]
        
        return memories
    
    def record_decision(
        self,
        decision: str,
        rationale: str,
        outcome: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryEntry:
        """Record a decision for future reference"""
        context = f"Rationale: {rationale}"
        if outcome:
            context += f"\nOutcome: {outcome}"
        
        return self.add_memory(
            memory_type="decision",
            title=f"Decision: {decision[:50]}",
            content=decision,
            context=context,
            tags=["decision"] + (tags or []),
            category="decision",
        )
    
    def record_insight(
        self,
        insight: str,
        evidence: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryEntry:
        """Record an insight"""
        context = ""
        if evidence:
            context = f"Evidence: {evidence}"
        
        return self.add_memory(
            memory_type="insight",
            title=f"Insight: {insight[:50]}",
            content=insight,
            context=context,
            tags=["insight"] + (tags or []),
            category="insight",
        )
    
    # ========== Pattern Recognition ==========
    
    def find_patterns(
        self,
        tags: Optional[List[str]] = None,
        memory_type: Optional[str] = None,
        min_impact: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find common patterns in memories"""
        patterns = []
        
        # Get relevant memories
        memories = list(self._memories.values())
        
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        if tags:
            tag_sets = [set(tags)]
            memories = [m for m in memories if m.tags & tag_sets[0]]
        
        # Find common tag combinations
        tag_counts: Dict[str, int] = {}
        for memory in memories:
            if memory.impact_score < min_impact:
                continue
            for tag in memory.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Return top patterns
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        for tag, count in sorted_tags[:10]:
            if count >= 2:
                patterns.append({
                    "tag": tag,
                    "count": count,
                    "type": "common_tag",
                })
        
        return patterns
    
    def get_wisdom(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get accumulated wisdom"""
        wisdom = {
            "total_memories": len(self._memories),
            "by_type": {},
            "top_lessons": [],
            "mistakes_to_avoid": [],
            "patterns": [],
        }
        
        # Count by type
        for memory_type, memory_ids in self._by_type.items():
            wisdom["by_type"][memory_type] = len(memory_ids)
        
        # Top lessons
        lessons = self.get_memories_by_type("lesson")
        wisdom["top_lessons"] = [
            {"title": m.title, "impact": m.impact_score}
            for m in lessons[:10]
        ]
        
        # Mistakes to avoid
        mistakes = self.get_memories_by_type("mistake")
        wisdom["mistakes_to_avoid"] = [
            {"title": m.title, "content": m.content[:100]}
            for m in mistakes[:10]
        ]
        
        # Top patterns
        wisdom["patterns"] = self.find_patterns()
        
        return wisdom
    
    # ========== Memory Updates ==========
    
    def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a memory"""
        memory = self._memories.get(memory_id)
        if not memory:
            return False
        
        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        
        memory.updated_at = time.time()
        return True
    
    def verify_memory(self, memory_id: str, verified_by: str) -> bool:
        """Verify a memory"""
        memory = self._memories.get(memory_id)
        if not memory:
            return False
        
        memory.verified = True
        memory.verified_by = verified_by
        memory.confidence = min(1.0, memory.confidence + 0.2)
        memory.updated_at = time.time()
        
        return True
    
    def link_memories(self, memory_id1: str, memory_id2: str) -> bool:
        """Link two memories together"""
        memory1 = self._memories.get(memory_id1)
        memory2 = self._memories.get(memory_id2)
        
        if not memory1 or not memory2:
            return False
        
        if memory_id2 not in memory1.related_memories:
            memory1.related_memories.append(memory_id2)
        
        if memory_id1 not in memory2.related_memories:
            memory2.related_memories.append(memory_id1)
        
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        if memory_id not in self._memories:
            return False
        
        memory = self._memories.pop(memory_id)
        
        # Remove from indices
        if memory.memory_type in self._by_type:
            self._by_type[memory.memory_type].remove(memory_id)
        
        for tag in memory.tags:
            if tag in self._by_tag:
                self._by_tag[tag].remove(memory_id)
        
        # Remove from related memories
        for other in self._memories.values():
            if memory_id in other.related_memories:
                other.related_memories.remove(memory_id)
        
        return True
    
    # ========== Learning Callbacks ==========
    
    def on_learning(self, callback: Callable) -> None:
        """Register a learning callback"""
        self._learning_callbacks.append(callback)
    
    def _trigger_learning(self, memory: MemoryEntry) -> None:
        """Trigger learning callbacks"""
        for callback in self._learning_callbacks:
            try:
                callback(memory)
            except Exception as e:
                logger.error(f"Learning callback error: {e}")
    
    # ========== Statistics ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        total = len(self._memories)
        verified = sum(1 for m in self._memories.values() if m.verified)
        
        return {
            "total_memories": total,
            "verified_memories": verified,
            "by_type": {
                mt: len(mids)
                for mt, mids in self._by_type.items()
            },
            "total_tags": len(self._by_tag),
            "total_applications": sum(m.times_applied for m in self._memories.values()),
        }
