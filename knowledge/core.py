"""
Knowledge Core
=============

Core classes for the knowledge platform.
"""

import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of knowledge documents"""
    RESEARCH = "research"
    EXPERIMENT = "experiment"
    STRATEGY = "strategy"
    TRADE_REVIEW = "trade_review"
    VALIDATION_REPORT = "validation_report"
    DEPLOYMENT_REPORT = "deployment_report"
    PERFORMANCE_REPORT = "performance_report"
    INCIDENT_REPORT = "incident_report"
    LESSON_LEARNED = "lesson_learned"
    ARCHITECTURE_DECISION = "architecture_decision"
    DEVELOPER_NOTE = "developer_note"
    API_DOCUMENTATION = "api_documentation"
    TUTORIAL = "tutorial"
    BLOG_POST = "blog_post"
    MEETING_NOTES = "meeting_notes"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


@dataclass
class Link:
    """A link between knowledge entries"""
    link_id: str
    source_id: str
    target_id: str
    link_type: str  # "references", "related", "inspired_by", "improved_from", etc.
    strength: float = 1.0  # 0.0 - 1.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """A knowledge document"""
    document_id: str
    title: str
    document_type: DocumentType
    
    # Content
    content: str
    summary: str = ""
    
    # Metadata
    author: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    
    # Tags and categories
    tags: List[str] = field(default_factory=list)
    category: str = ""
    
    # Relationships
    linked_documents: List[str] = field(default_factory=list)  # Document IDs
    linked_entities: Dict[str, List[str]] = field(default_factory=dict)  # entity_type -> IDs
    
    # Status
    status: str = "draft"  # draft, published, archived
    is_public: bool = True
    
    # Quality metrics
    quality_score: float = 0.0
    relevance_score: float = 0.0
    
    # AI-generated content
    ai_summary: str = ""
    ai_tags: List[str] = field(default_factory=list)
    
    # Source tracking
    source_url: str = ""
    source_system: str = ""
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the document"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = time.time()
    
    def add_link(self, target_id: str, link_type: str = "related") -> None:
        """Add a linked document"""
        if target_id not in self.linked_documents:
            self.linked_documents.append(target_id)
            self.updated_at = time.time()
    
    def calculate_hash(self) -> str:
        """Calculate content hash"""
        content = f"{self.document_id}:{self.content}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "document_type": self.document_type.value,
            "summary": self.summary,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "status": self.status,
        }


@dataclass
class KnowledgeEntry:
    """
    A single entry in the knowledge base.
    
    Can represent a document, entity, or concept.
    """
    entry_id: str
    entry_type: str  # "document", "strategy", "model", "feature", "dataset"
    
    # Identification
    name: str
    description: str
    
    # Content
    content: str = ""
    
    # Relationships
    links: List[Link] = field(default_factory=list)
    children: List[str] = field(default_factory=list)  # Entry IDs
    parent_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    # Quality
    quality_score: float = 0.0
    usage_count: int = 0
    
    # Source
    source_document_id: Optional[str] = None
    
    def add_link(
        self,
        target_id: str,
        link_type: str,
        strength: float = 1.0
    ) -> Link:
        """Add a link to another entry"""
        link = Link(
            link_id=str(uuid.uuid4()),
            source_id=self.entry_id,
            target_id=target_id,
            link_type=link_type,
            strength=strength,
        )
        self.links.append(link)
        self.updated_at = time.time()
        return link
    
    def add_tag(self, tag: str) -> None:
        """Add a tag"""
        self.tags.add(tag)
        self.updated_at = time.time()
    
    def record_usage(self) -> None:
        """Record that this entry was accessed/used"""
        self.usage_count += 1
        self.last_accessed = time.time()
    
    def get_related_entries(
        self,
        link_type: Optional[str] = None,
        min_strength: float = 0.0
    ) -> List[str]:
        """Get related entry IDs"""
        related = []
        for link in self.links:
            if link.strength >= min_strength:
                if link_type is None or link.link_type == link_type:
                    related.append(link.target_id)
        return related
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
        }


@dataclass
class EntityReference:
    """Reference to an entity (strategy, model, feature, etc.)"""
    entity_id: str
    entity_type: str  # "strategy", "model", "feature", "dataset"
    name: str
    version: Optional[str] = None


@dataclass
class KnowledgeGraph:
    """Knowledge graph representation"""
    nodes: Dict[str, KnowledgeEntry] = field(default_factory=dict)
    edges: List[Link] = field(default_factory=list)
    
    def add_node(self, entry: KnowledgeEntry) -> None:
        """Add a node to the graph"""
        self.nodes[entry.entry_id] = entry
    
    def add_edge(self, link: Link) -> None:
        """Add an edge to the graph"""
        self.edges.append(link)
    
    def get_neighbors(self, entry_id: str, depth: int = 1) -> List[str]:
        """Get neighboring entries"""
        neighbors = set()
        to_visit = [(entry_id, 0)]
        visited = set()
        
        while to_visit:
            current, d = to_visit.pop(0)
            if current in visited or d > depth:
                continue
            
            visited.add(current)
            
            if current in self.nodes:
                entry = self.nodes[current]
                for link in entry.links:
                    neighbors.add(link.target_id)
                    if d < depth:
                        to_visit.append((link.target_id, d + 1))
        
        return list(neighbors)
