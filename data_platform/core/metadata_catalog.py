"""
Metadata Catalog

Searchable metadata system for datasets and features.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class MetadataEntry:
    """A metadata entry in the catalog"""
    
    def __init__(
        self,
        entry_id: str,
        entity_type: str,  # "dataset" or "feature"
        entity_id: str,
        name: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        owner: str = "",
        team: str = "",
    ):
        self.entry_id = entry_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.name = name
        self.metadata = metadata
        self.tags = tags or []
        self.labels = labels or {}
        self.owner = owner
        self.team = team
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
    
    def touch(self) -> None:
        """Update last accessed timestamp"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata"""
        self.metadata.update(updates)
        self.updated_at = datetime.utcnow()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "name": self.name,
            "metadata": self.metadata,
            "tags": self.tags,
            "labels": self.labels,
            "owner": self.owner,
            "team": self.team,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "last_accessed": self.last_accessed.isoformat() if isinstance(self.last_accessed, datetime) else self.last_accessed,
            "access_count": self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetadataEntry":
        """Create from dictionary"""
        for dt_field in ["created_at", "updated_at", "last_accessed"]:
            if dt_field in data and isinstance(data[dt_field], str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        return cls(**data)


class MetadataCatalog:
    """
    Metadata Catalog for searchable metadata across all data assets.
    
    Features:
    - Automatic metadata extraction and indexing
    - Full-text search
    - Faceted search by tags, labels, owner, etc.
    - Usage tracking
    - Metadata versioning
    """
    
    def __init__(self, storage_path: str = "data_platform/catalog"):
        self._storage_path = storage_path
        self._entries: Dict[str, MetadataEntry] = {}
        
        # Indexes for fast lookup
        self._by_entity: Dict[str, str] = {}  # entity_id -> entry_id
        self._by_type: Dict[str, Set[str]] = {}  # entity_type -> entry_ids
        self._by_tag: Dict[str, Set[str]] = {}  # tag -> entry_ids
        self._by_owner: Dict[str, Set[str]] = {}  # owner -> entry_ids
        self._by_team: Dict[str, Set[str]] = {}  # team -> entry_ids
        self._by_name: Dict[str, str] = {}  # name.lower() -> entry_id
        
        # Full-text search index
        self._text_index: Dict[str, Set[str]] = {}  # word -> entry_ids
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load catalog index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                for entry_data in data.get("entries", []):
                    entry = MetadataEntry.from_dict(entry_data)
                    self._entries[entry.entry_id] = entry
                    self._update_indexes(entry)
                
                logger.info(f"Loaded {len(self._entries)} metadata entries")
            except Exception as e:
                logger.warning(f"Could not load catalog index: {e}")
    
    def _save_index(self) -> None:
        """Save catalog index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "entries": [e.to_dict() for e in self._entries.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _update_indexes(self, entry: MetadataEntry) -> None:
        """Update all indexes for an entry"""
        # Entity index
        self._by_entity[entry.entity_id] = entry.entry_id
        
        # Type index
        if entry.entity_type not in self._by_type:
            self._by_type[entry.entity_type] = set()
        self._by_type[entry.entity_type].add(entry.entry_id)
        
        # Tag index
        for tag in entry.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(entry.entry_id)
        
        # Owner index
        if entry.owner:
            if entry.owner not in self._by_owner:
                self._by_owner[entry.owner] = set()
            self._by_owner[entry.owner].add(entry.entry_id)
        
        # Team index
        if entry.team:
            if entry.team not in self._by_team:
                self._by_team[entry.team] = set()
            self._by_team[entry.team].add(entry.entry_id)
        
        # Name index
        self._by_name[entry.name.lower()] = entry.entry_id
        
        # Text index
        self._index_text(entry)
    
    def _index_text(self, entry: MetadataEntry) -> None:
        """Index text content for full-text search"""
        # Words to index
        words = set()
        
        # Name words
        words.update(entry.name.lower().split())
        
        # Metadata words (limited depth)
        def extract_words(obj: Any, depth: int = 0) -> None:
            if depth > 2:
                return
            if isinstance(obj, str):
                words.update(obj.lower().split())
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract_words(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    extract_words(item, depth + 1)
        
        extract_words(entry.metadata)
        extract_words(entry.tags)
        extract_words(entry.labels)
        
        # Update text index
        for word in words:
            if len(word) < 2:  # Skip very short words
                continue
            if word not in self._text_index:
                self._text_index[word] = set()
            self._text_index[word].add(entry.entry_id)
    
    def register(
        self,
        entity_type: str,
        entity_id: str,
        name: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        owner: str = "",
        team: str = "",
    ) -> MetadataEntry:
        """Register an entity in the catalog"""
        # Check if already registered
        if entity_id in self._by_entity:
            entry_id = self._by_entity[entity_id]
            entry = self._entries[entry_id]
            entry.update_metadata(metadata)
            if tags:
                for tag in tags:
                    entry.add_tag(tag)
            if labels:
                entry.labels.update(labels)
            self._save_index()
            return entry
        
        # Create new entry
        entry = MetadataEntry(
            entry_id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            metadata=metadata,
            tags=tags,
            labels=labels,
            owner=owner,
            team=team,
        )
        
        self._entries[entry.entry_id] = entry
        self._update_indexes(entry)
        self._save_index()
        
        logger.info(f"Registered {entity_type} in catalog: {name} ({entity_id})")
        return entry
    
    def get(self, entry_id: str) -> Optional[MetadataEntry]:
        """Get metadata entry by ID"""
        entry = self._entries.get(entry_id)
        if entry:
            entry.touch()
        return entry
    
    def get_by_entity_id(self, entity_id: str) -> Optional[MetadataEntry]:
        """Get metadata entry by entity ID"""
        entry_id = self._by_entity.get(entity_id)
        return self.get(entry_id) if entry_id else None
    
    def update(
        self,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[MetadataEntry]:
        """Update metadata entry"""
        entry = self.get_by_entity_id(entity_id)
        if not entry:
            return None
        
        if metadata:
            entry.update_metadata(metadata)
        if tags is not None:
            entry.tags = tags
        if labels:
            entry.labels.update(labels)
        
        self._save_index()
        return entry
    
    def search(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
        team: Optional[str] = None,
        label_filters: Optional[Dict[str, str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        min_access_count: Optional[int] = None,
        limit: int = 100,
    ) -> List[MetadataEntry]:
        """Search for metadata entries"""
        candidates = set(self._entries.keys())
        
        # Full-text search
        if query:
            query_words = query.lower().split()
            matching_ids = None
            
            for word in query_words:
                word_ids = set()
                # Exact match
                word_ids.update(self._text_index.get(word, set()))
                # Partial match
                for indexed_word, entry_ids in self._text_index.items():
                    if word in indexed_word:
                        word_ids.update(entry_ids)
                
                if matching_ids is None:
                    matching_ids = word_ids
                else:
                    matching_ids &= word_ids
            
            if matching_ids:
                candidates &= matching_ids
            else:
                return []  # No matches
        
        # Filter by entity type
        if entity_type:
            type_ids = self._by_type.get(entity_type, set())
            candidates &= type_ids
        
        # Filter by tags (AND logic)
        if tags:
            for tag in tags:
                tag_ids = self._by_tag.get(tag, set())
                candidates &= tag_ids
        
        # Filter by owner
        if owner:
            owner_ids = self._by_owner.get(owner, set())
            candidates &= owner_ids
        
        # Filter by team
        if team:
            team_ids = self._by_team.get(team, set())
            candidates &= team_ids
        
        # Filter by labels
        if label_filters:
            for key, value in label_filters.items():
                for entry in self._entries.values():
                    if entry.labels.get(key) != value:
                        candidates.discard(entry.entry_id)
        
        # Filter by date range
        if date_range:
            start, end = date_range
            for entry_id in list(candidates):
                entry = self._entries[entry_id]
                if entry.created_at < start or entry.created_at > end:
                    candidates.discard(entry_id)
        
        # Filter by minimum access count
        if min_access_count is not None:
            for entry_id in list(candidates):
                entry = self._entries[entry_id]
                if entry.access_count < min_access_count:
                    candidates.discard(entry_id)
        
        # Sort by relevance (access count) and return
        results = [
            self._entries[eid]
            for eid in candidates
        ]
        results.sort(key=lambda e: (e.access_count, e.updated_at), reverse=True)
        
        return results[:limit]
    
    def search_datasets(self, query: Optional[str] = None, **kwargs) -> List[MetadataEntry]:
        """Search for datasets specifically"""
        return self.search(query=query, entity_type="dataset", **kwargs)
    
    def search_features(self, query: Optional[str] = None, **kwargs) -> List[MetadataEntry]:
        """Search for features specifically"""
        return self.search(query=query, entity_type="feature", **kwargs)
    
    def get_popular(self, entity_type: Optional[str] = None, limit: int = 10) -> List[MetadataEntry]:
        """Get most accessed entries"""
        entries = list(self._entries.values())
        
        if entity_type:
            entries = [e for e in entries if e.entity_type == entity_type]
        
        entries.sort(key=lambda e: e.access_count, reverse=True)
        return entries[:limit]
    
    def get_recent(self, entity_type: Optional[str] = None, limit: int = 10) -> List[MetadataEntry]:
        """Get recently updated entries"""
        entries = list(self._entries.values())
        
        if entity_type:
            entries = [e for e in entries if e.entity_type == entity_type]
        
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[:limit]
    
    def get_by_tag(self, tag: str) -> List[MetadataEntry]:
        """Get all entries with a tag"""
        entry_ids = self._by_tag.get(tag, set())
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def get_by_owner(self, owner: str) -> List[MetadataEntry]:
        """Get all entries owned by a user"""
        entry_ids = self._by_owner.get(owner, set())
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def delete(self, entity_id: str) -> bool:
        """Remove an entry from the catalog"""
        entry_id = self._by_entity.get(entity_id)
        if not entry_id:
            return False
        
        entry = self._entries.pop(entry_id)
        
        # Remove from indexes
        self._by_type[entry.entity_type].discard(entry_id)
        for tag in entry.tags:
            self._by_tag[tag].discard(entry_id)
        if entry.owner:
            self._by_owner[entry.owner].discard(entry_id)
        if entry.team:
            self._by_team[entry.team].discard(entry_id)
        self._by_name.pop(entry.name.lower(), None)
        
        self._save_index()
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        entries = list(self._entries.values())
        
        return {
            "total_entries": len(entries),
            "by_type": {
                et: len(eids)
                for et, eids in self._by_type.items()
            },
            "total_tags": len(self._by_tag),
            "total_owners": len(self._by_owner),
            "total_teams": len(self._by_team),
            "total_words_indexed": len(self._text_index),
            "total_accesses": sum(e.access_count for e in entries),
            "avg_access_count": (
                sum(e.access_count for e in entries) / len(entries)
                if entries else 0
            ),
        }
    
    def export_catalog(self) -> Dict[str, Any]:
        """Export the catalog"""
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "entries": [e.to_dict() for e in self._entries.values()],
            "statistics": self.get_statistics(),
        }
    
    def import_catalog(self, data: Dict[str, Any], merge: bool = True) -> int:
        """Import a catalog"""
        imported = 0
        
        for entry_data in data.get("entries", []):
            entry = MetadataEntry.from_dict(entry_data)
            
            if not merge and entry.entity_id in self._by_entity:
                continue
            
            self._entries[entry.entry_id] = entry
            self._update_indexes(entry)
            imported += 1
        
        if imported:
            self._save_index()
            logger.info(f"Imported {imported} metadata entries")
        
        return imported
