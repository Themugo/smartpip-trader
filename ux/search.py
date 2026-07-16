"""
Search System
============

Global search and saved searches.
"""

import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SearchResultType(Enum):
    """Types of search results"""
    TRADE = "trade"
    ORDER = "order"
    POSITION = "position"
    STRATEGY = "strategy"
    DOCUMENT = "document"
    COMMAND = "command"
    SETTING = "setting"
    PAGE = "page"


@dataclass
class SearchResult:
    """A search result"""
    result_id: str
    type: SearchResultType
    title: str
    description: str
    
    # Relevance
    score: float = 0.0
    highlights: List[str] = field(default_factory=list)
    
    # Navigation
    url: Optional[str] = None
    action: Optional[str] = None  # Command to execute
    
    # Metadata
    icon: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "url": self.url,
        }


@dataclass
class FilterCriteria:
    """Filter for search"""
    field: str
    operator: str  # eq, ne, gt, lt, contains, starts_with
    value: Any
    
    def matches(self, item: Dict[str, Any]) -> bool:
        """Check if item matches filter"""
        field_value = item.get(self.field)
        
        if self.operator == "eq":
            return field_value == self.value
        elif self.operator == "ne":
            return field_value != self.value
        elif self.operator == "gt":
            return field_value > self.value
        elif self.operator == "lt":
            return field_value < self.value
        elif self.operator == "contains":
            return self.value in str(field_value)
        elif self.operator == "starts_with":
            return str(field_value).startswith(self.value)
        
        return False


@dataclass
class SavedSearch:
    """Saved search configuration"""
    search_id: str
    name: str
    query: str
    filters: List[FilterCriteria] = field(default_factory=list)
    
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    
    # Display
    icon: Optional[str] = None
    color: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "search_id": self.search_id,
            "name": self.name,
            "query": self.query,
            "last_used": self.last_used,
            "use_count": self.use_count,
        }


class GlobalSearch:
    """
    Global search across all data.
    """
    
    def __init__(self):
        self._indexes: Dict[SearchResultType, List[Dict[str, Any]]] = {}
        self._saved_searches: Dict[str, SavedSearch] = {}
        self._search_handlers: Dict[SearchResultType, Callable] = {}
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100
    
    # ========== Indexing ==========
    
    def index(
        self,
        result_type: SearchResultType,
        items: List[Dict[str, Any]]
    ) -> None:
        """Index items for searching"""
        self._indexes[result_type] = items
    
    def add_to_index(
        self,
        result_type: SearchResultType,
        item: Dict[str, Any]
    ) -> None:
        """Add a single item to index"""
        if result_type not in self._indexes:
            self._indexes[result_type] = []
        self._indexes[result_type].append(item)
    
    def remove_from_index(
        self,
        result_type: SearchResultType,
        item_id: str
    ) -> bool:
        """Remove an item from index"""
        if result_type not in self._indexes:
            return False
        
        original = len(self._indexes[result_type])
        self._indexes[result_type] = [
            item for item in self._indexes[result_type]
            if item.get("id") != item_id
        ]
        return len(self._indexes[result_type]) < original
    
    # ========== Search ==========
    
    def search(
        self,
        query: str,
        types: Optional[List[SearchResultType]] = None,
        filters: Optional[List[FilterCriteria]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search across all indexed data"""
        results = []
        query_lower = query.lower()
        
        # Determine which types to search
        search_types = types or list(self._indexes.keys())
        
        for result_type in search_types:
            items = self._indexes.get(result_type, [])
            
            for item in items:
                # Apply filters
                if filters:
                    if not all(f.matches(item) for f in filters):
                        continue
                
                # Calculate score
                score = self._calculate_score(item, query_lower)
                
                if score > 0:
                    result = self._item_to_result(item, result_type, score, query_lower)
                    results.append(result)
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Record in history
        if query:
            self._record_search(query, len(results))
        
        return results[:limit]
    
    def _calculate_score(self, item: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for an item"""
        if not query:
            return 0.5
        
        score = 0.0
        
        # Title match (highest weight)
        title = str(item.get("title", "")).lower()
        if query in title:
            score += 0.5
            if title.startswith(query):
                score += 0.3
        
        # Description match
        description = str(item.get("description", "")).lower()
        if query in description:
            score += 0.3
        
        # ID match
        item_id = str(item.get("id", "")).lower()
        if query in item_id:
            score += 0.2
        
        # Symbol match (for trading)
        symbol = str(item.get("symbol", "")).upper()
        if query.upper() in symbol:
            score += 0.4
        
        return score
    
    def _item_to_result(
        self,
        item: Dict[str, Any],
        result_type: SearchResultType,
        score: float,
        query: str
    ) -> SearchResult:
        """Convert indexed item to SearchResult"""
        # Generate highlights
        highlights = []
        for field_name in ["title", "description"]:
            value = str(item.get(field_name, ""))
            if query and query in value.lower():
                # Simple highlight
                highlights.append(value)
        
        return SearchResult(
            result_id=item.get("id", str(uuid.uuid4())),
            type=result_type,
            title=item.get("title", "Untitled"),
            description=item.get("description", ""),
            score=score,
            highlights=highlights[:3],
            url=item.get("url"),
            action=item.get("action"),
            icon=item.get("icon"),
            metadata=item,
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
        )
    
    # ========== Saved Searches ==========
    
    def save_search(
        self,
        name: str,
        query: str,
        filters: Optional[List[FilterCriteria]] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> SavedSearch:
        """Save a search configuration"""
        search = SavedSearch(
            search_id=str(uuid.uuid4()),
            name=name,
            query=query,
            filters=filters or [],
            icon=icon,
            color=color,
        )
        self._saved_searches[search.search_id] = search
        return search
    
    def get_saved_search(self, search_id: str) -> Optional[SavedSearch]:
        """Get a saved search"""
        return self._saved_searches.get(search_id)
    
    def get_all_saved_searches(self) -> List[SavedSearch]:
        """Get all saved searches"""
        return list(self._saved_searches.values())
    
    def execute_saved_search(self, search_id: str) -> List[SearchResult]:
        """Execute a saved search"""
        search = self._saved_searches.get(search_id)
        if not search:
            return []
        
        search.last_used = time.time()
        search.use_count += 1
        
        return self.search(search.query, filters=search.filters)
    
    def delete_saved_search(self, search_id: str) -> bool:
        """Delete a saved search"""
        return self._saved_searches.pop(search_id, None) is not None
    
    # ========== History ==========
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent searches"""
        return self._history[-limit:]
    
    def clear_history(self) -> None:
        """Clear search history"""
        self._history.clear()
    
    def _record_search(self, query: str, result_count: int) -> None:
        """Record a search in history"""
        self._history.append({
            "query": query,
            "result_count": result_count,
            "timestamp": time.time(),
        })
        
        if len(self._history) > self._max_history:
            self._history.pop(0)
