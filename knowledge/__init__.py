"""
Knowledge Platform
===============

Institutional knowledge system with semantic search and organizational memory.

Features:
- Document storage (research, experiments, strategies, reports)
- Semantic search across all documents
- Cross-linking between related entities
- AI-powered summaries
- Recommendations based on historical work
- Organizational memory that grows over time
"""

__version__ = "1.0.0"

from .core import (
    Document,
    DocumentType,
    KnowledgeEntry,
    Link,
)
from .storage import (
    KnowledgeStore,
    DocumentIndex,
)
from .search import (
    SemanticSearch,
    SearchResult,
    SearchIndex,
)
from .crosslink import (
    CrossLinker,
    LinkType,
)
from .summaries import (
    Summarizer,
    Summary,
)
from .recommendations import (
    RecommendationEngine,
    Recommendation,
)
from .memory import (
    OrganizationalMemory,
    MemoryEntry,
)

__all__ = [
    "Document",
    "DocumentType",
    "KnowledgeEntry",
    "Link",
    "KnowledgeStore",
    "DocumentIndex",
    "SemanticSearch",
    "SearchResult",
    "SearchIndex",
    "CrossLinker",
    "LinkType",
    "Summarizer",
    "Summary",
    "RecommendationEngine",
    "Recommendation",
    "OrganizationalMemory",
    "MemoryEntry",
]
