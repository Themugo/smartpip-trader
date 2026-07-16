"""
Knowledge Storage
================

Document storage and indexing for the knowledge platform.
"""

import json
import time
import uuid
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
import logging

from .core import Document, DocumentType, KnowledgeEntry, KnowledgeGraph, Link

logger = logging.getLogger(__name__)


@dataclass
class DocumentIndex:
    """Index for fast document lookup"""
    documents: Dict[str, Document] = field(default_factory=dict)
    
    # Indices
    by_type: Dict[str, Set[str]] = field(default_factory=dict)  # type -> doc_ids
    by_tag: Dict[str, Set[str]] = field(default_factory=dict)  # tag -> doc_ids
    by_author: Dict[str, Set[str]] = field(default_factory=dict)  # author -> doc_ids
    by_status: Dict[str, Set[str]] = field(default_factory=dict)  # status -> doc_ids
    
    # Full-text search index (simplified)
    word_index: Dict[str, Set[str]] = field(default_factory=dict)
    
    def add_document(self, doc: Document) -> None:
        """Add a document to the index"""
        self.documents[doc.document_id] = doc
        
        # Update type index
        doc_type = doc.document_type.value
        if doc_type not in self.by_type:
            self.by_type[doc_type] = set()
        self.by_type[doc_type].add(doc.document_id)
        
        # Update tag index
        for tag in doc.tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = set()
            self.by_tag[tag].add(doc.document_id)
        
        # Update author index
        if doc.author:
            if doc.author not in self.by_author:
                self.by_author[doc.author] = set()
            self.by_author[doc.author].add(doc.document_id)
        
        # Update status index
        if doc.status not in self.by_status:
            self.by_status[doc.status] = set()
        self.by_status[doc.status].add(doc.document_id)
        
        # Update word index
        self._index_words(doc)
    
    def _index_words(self, doc: Document) -> None:
        """Index words from document"""
        text = f"{doc.title} {doc.content} {doc.summary}".lower()
        words = set()
        
        # Simple tokenization
        for word in text.split():
            # Remove punctuation
            word = "".join(c for c in word if c.isalnum())
            if len(word) >= 3:
                words.add(word)
        
        for word in words:
            if word not in self.word_index:
                self.word_index[word] = set()
            self.word_index[word].add(doc.document_id)
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index"""
        if doc_id not in self.documents:
            return False
        
        doc = self.documents.pop(doc_id)
        
        # Remove from type index
        doc_type = doc.document_type.value
        if doc_type in self.by_type:
            self.by_type[doc_type].discard(doc_id)
        
        # Remove from tag indices
        for tag in doc.tags:
            if tag in self.by_tag:
                self.by_tag[tag].discard(doc_id)
        
        # Remove from author index
        if doc.author in self.by_author:
            self.by_author[doc.author].discard(doc_id)
        
        # Remove from status index
        if doc.status in self.by_status:
            self.by_status[doc.status].discard(doc_id)
        
        return True
    
    def get_by_type(self, doc_type: str) -> List[Document]:
        """Get documents by type"""
        doc_ids = self.by_type.get(doc_type, set())
        return [self.documents[did] for did in doc_ids if did in self.documents]
    
    def get_by_tag(self, tag: str) -> List[Document]:
        """Get documents by tag"""
        doc_ids = self.by_tag.get(tag, set())
        return [self.documents[did] for did in doc_ids if did in self.documents]
    
    def get_by_author(self, author: str) -> List[Document]:
        """Get documents by author"""
        doc_ids = self.by_author.get(author, set())
        return [self.documents[did] for did in doc_ids if did in self.documents]
    
    def search_words(self, query: str) -> List[Document]:
        """Search by words"""
        words = query.lower().split()
        result_ids = None
        
        for word in words:
            word = "".join(c for c in word if c.isalnum())
            if word in self.word_index:
                if result_ids is None:
                    result_ids = self.word_index[word].copy()
                else:
                    result_ids &= self.word_index[word]
            else:
                return []
        
        if result_ids:
            return [self.documents[did] for did in result_ids if did in self.documents]
        return []


class KnowledgeStore:
    """
    Main storage for knowledge documents.
    """
    
    def __init__(self, storage_path: str = "./data/knowledge"):
        self.storage_path = storage_path
        self.index = DocumentIndex()
        self.graph = KnowledgeGraph()
        
        # Entity indices
        self.entries: Dict[str, KnowledgeEntry] = {}
        self.entries_by_type: Dict[str, List[str]] = {}
        
        # Statistics
        self.stats = {
            "total_documents": 0,
            "total_entries": 0,
            "total_links": 0,
            "by_type": {},
        }
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load index from disk"""
        index_file = os.path.join(self.storage_path, "index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    # Would load full index here
                    pass
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
    
    def _save_index(self) -> None:
        """Save index to disk"""
        index_file = os.path.join(self.storage_path, "index.json")
        try:
            with open(index_file, "w") as f:
                json.dump({"stats": self.stats}, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    # ========== Document Operations ==========
    
    def add_document(self, doc: Document) -> str:
        """Add a document to the store"""
        if not doc.document_id:
            doc.document_id = str(uuid.uuid4())
        
        doc.created_at = time.time()
        doc.updated_at = time.time()
        
        # Save to file
        self._save_document(doc)
        
        # Update index
        self.index.add_document(doc)
        
        # Update stats
        self.stats["total_documents"] += 1
        doc_type = doc.document_type.value
        self.stats["by_type"][doc_type] = self.stats["by_type"].get(doc_type, 0) + 1
        
        self._save_index()
        return doc.document_id
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID"""
        # Check index first
        if doc_id in self.index.documents:
            return self.index.documents[doc_id]
        
        # Try to load from file
        doc_file = os.path.join(self.storage_path, f"{doc_id}.json")
        if os.path.exists(doc_file):
            try:
                with open(doc_file, "r") as f:
                    data = json.load(f)
                    doc = self._document_from_dict(data)
                    self.index.add_document(doc)
                    return doc
            except Exception as e:
                logger.error(f"Failed to load document {doc_id}: {e}")
        
        return None
    
    def update_document(self, doc: Document) -> bool:
        """Update a document"""
        doc.updated_at = time.time()
        doc.version += 1
        
        self._save_document(doc)
        self.stats["total_documents"] += 1
        self._save_index()
        return True
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document"""
        if self.index.remove_document(doc_id):
            # Delete file
            doc_file = os.path.join(self.storage_path, f"{doc_id}.json")
            if os.path.exists(doc_file):
                os.remove(doc_file)
            
            self._save_index()
            return True
        return False
    
    def _save_document(self, doc: Document) -> None:
        """Save document to file"""
        doc_file = os.path.join(self.storage_path, f"{doc.document_id}.json")
        with open(doc_file, "w") as f:
            json.dump(self._document_to_dict(doc), f, indent=2)
    
    def _document_to_dict(self, doc: Document) -> Dict[str, Any]:
        """Convert document to dict"""
        return {
            "document_id": doc.document_id,
            "title": doc.title,
            "document_type": doc.document_type.value,
            "content": doc.content,
            "summary": doc.summary,
            "author": doc.author,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "version": doc.version,
            "tags": doc.tags,
            "status": doc.status,
        }
    
    def _document_from_dict(self, data: Dict) -> Document:
        """Create document from dict"""
        return Document(
            document_id=data["document_id"],
            title=data["title"],
            document_type=DocumentType(data["document_type"]),
            content=data["content"],
            summary=data.get("summary", ""),
            author=data.get("author", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            status=data.get("status", "draft"),
        )
    
    # ========== Knowledge Entry Operations ==========
    
    def add_entry(self, entry: KnowledgeEntry) -> str:
        """Add a knowledge entry"""
        if not entry.entry_id:
            entry.entry_id = str(uuid.uuid4())
        
        entry.created_at = time.time()
        entry.updated_at = time.time()
        
        self.entries[entry.entry_id] = entry
        
        # Index by type
        if entry.entry_type not in self.entries_by_type:
            self.entries_by_type[entry.entry_type] = []
        self.entries_by_type[entry.entry_type].append(entry.entry_id)
        
        # Add to graph
        self.graph.add_node(entry)
        
        # Create reverse links
        for link in entry.links:
            self.graph.add_edge(link)
            self.stats["total_links"] += 1
        
        self.stats["total_entries"] += 1
        return entry.entry_id
    
    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry"""
        entry = self.entries.get(entry_id)
        if entry:
            entry.record_usage()
        return entry
    
    def get_entries_by_type(self, entry_type: str) -> List[KnowledgeEntry]:
        """Get entries by type"""
        entry_ids = self.entries_by_type.get(entry_type, [])
        return [self.entries[eid] for eid in entry_ids if eid in self.entries]
    
    def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str,
        strength: float = 1.0
    ) -> Optional[Link]:
        """Add a link between entries"""
        source = self.entries.get(source_id)
        if not source:
            return None
        
        link = source.add_link(target_id, link_type, strength)
        self.graph.add_edge(link)
        self.stats["total_links"] += 1
        
        # Also link target to source (bidirectional)
        target = self.entries.get(target_id)
        if target:
            target.add_link(source_id, link_type, strength)
        
        return link
    
    def get_related(
        self,
        entry_id: str,
        link_type: Optional[str] = None,
        depth: int = 1
    ) -> List[KnowledgeEntry]:
        """Get related entries"""
        entry = self.entries.get(entry_id)
        if not entry:
            return []
        
        related_ids = entry.get_related_entries(link_type)
        
        # Expand to neighbors if depth > 1
        if depth > 1:
            related_ids = self.graph.get_neighbors(entry_id, depth)
        
        return [
            self.entries[eid]
            for eid in related_ids
            if eid in self.entries
        ]
    
    # ========== Query Operations ==========
    
    def search_documents(
        self,
        query: Optional[str] = None,
        doc_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Document]:
        """Search documents with filters"""
        results = []
        
        # Start with type filter if specified
        if doc_type:
            results = self.index.get_by_type(doc_type)
        else:
            results = list(self.index.documents.values())
        
        # Apply filters
        if tags:
            for tag in tags:
                tagged = self.index.get_by_tag(tag)
                results = [d for d in results if d in tagged]
        
        if author:
            authors_docs = self.index.get_by_author(author)
            results = [d for d in results if d in authors_docs]
        
        if status:
            status_docs = {did for did in self.index.by_status.get(status, set())}
            results = [d for d in results if d.document_id in status_docs]
        
        if query:
            query_docs = set(d.document_id for d in self.index.search_words(query))
            results = [d for d in results if d.document_id in query_docs]
        
        # Sort by updated time
        results.sort(key=lambda d: d.updated_at, reverse=True)
        
        return results[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return {
            "total_documents": self.stats["total_documents"],
            "total_entries": self.stats["total_entries"],
            "total_links": self.stats["total_links"],
            "by_document_type": self.stats["by_type"],
            "by_entry_type": {
                et: len(eids)
                for et, eids in self.entries_by_type.items()
            },
        }
