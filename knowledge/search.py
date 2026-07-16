"""
Semantic Search
==============

Advanced search capabilities for the knowledge platform.
"""

import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result"""
    result_id: str
    entity_id: str
    entity_type: str  # "document", "strategy", "model", etc.
    title: str
    description: str
    
    # Relevance
    score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    
    # Metadata
    entity: Any = None  # The actual entity object
    created_at: float = 0
    updated_at: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "highlights": self.highlights,
        }


class SearchIndex:
    """
    Index for fast semantic search.
    """
    
    def __init__(self):
        # Inverted index: term -> document IDs with TF
        self.inverted_index: Dict[str, Dict[str, float]] = {}
        
        # Document vectors (simplified TF-IDF)
        self.doc_vectors: Dict[str, Dict[str, float]] = {}
        
        # N-gram index for phrases
        self.ngram_index: Dict[str, Set[str]] = {}
        
        # Metadata indices
        self.by_type: Dict[str, Set[str]] = {}
        self.by_tag: Dict[str, Set[str]] = {}
        self.by_author: Dict[str, Set[str]] = {}
        
        # Document metadata
        self.doc_metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        doc_type: str,
        tags: List[str] = None,
        author: str = "",
        metadata: Dict[str, Any] = None
    ) -> None:
        """Add a document to the search index"""
        # Tokenize
        tokens = self._tokenize(f"{title} {content}")
        tf = self._calculate_tf(tokens)
        
        # Store vector
        self.doc_vectors[doc_id] = tf
        
        # Update inverted index
        for term, freq in tf.items():
            if term not in self.inverted_index:
                self.inverted_index[term] = {}
            self.inverted_index[term][doc_id] = freq
        
        # Index n-grams
        self._index_ngrams(doc_id, title)
        self._index_ngrams(doc_id, content)
        
        # Metadata indices
        if doc_type:
            if doc_type not in self.by_type:
                self.by_type[doc_type] = set()
            self.by_type[doc_type].add(doc_id)
        
        for tag in (tags or []):
            if tag not in self.by_tag:
                self.by_tag[tag] = set()
            self.by_tag[tag].add(doc_id)
        
        if author:
            if author not in self.by_author:
                self.by_author[author] = set()
            self.by_author[author].add(doc_id)
        
        # Store metadata
        self.doc_metadata[doc_id] = {
            "title": title,
            "doc_type": doc_type,
            "tags": tags or [],
            "author": author,
            "metadata": metadata or {},
        }
    
    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index"""
        # Remove from vectors
        self.doc_vectors.pop(doc_id, None)
        
        # Remove from inverted index
        for term in list(self.inverted_index.keys()):
            self.inverted_index[term].pop(doc_id, None)
            if not self.inverted_index[term]:
                del self.inverted_index[term]
        
        # Remove from n-gram index
        for ngram in list(self.ngram_index.keys()):
            self.ngram_index[ngram].discard(doc_id)
            if not self.ngram_index[ngram]:
                del self.ngram_index[ngram]
        
        # Remove from metadata indices
        self.by_type = {k: v - {doc_id} for k, v in self.by_type.items()}
        self.by_type = {k: v for k, v in self.by_type.items() if v}
        
        self.by_tag = {k: v - {doc_id} for k, v in self.by_tag.items()}
        self.by_tag = {k: v for k, v in self.by_tag.items() if v}
        
        self.by_author = {k: v - {doc_id} for k, v in self.by_author.items()}
        self.by_author = {k: v for k, v in self.by_author.items() if v}
        
        # Remove metadata
        self.doc_metadata.pop(doc_id, None)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = [t for t in tokens if t not in stopwords and len(t) >= 2]
        return tokens
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Calculate term frequency"""
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        
        # Normalize
        total = len(tokens)
        if total > 0:
            for token in tf:
                tf[token] = tf[token] / total
        
        return tf
    
    def _index_ngrams(self, doc_id: str, text: str, n: int = 3) -> None:
        """Index n-grams"""
        text = text.lower()
        words = self._tokenize(text)
        
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            if ngram not in self.ngram_index:
                self.ngram_index[ngram] = set()
            self.ngram_index[ngram].add(doc_id)
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search documents"""
        query_tokens = self._tokenize(query)
        query_tf = self._calculate_tf(query_tokens)
        
        # Get candidate documents
        candidates = set()
        for term in query_tokens:
            if term in self.inverted_index:
                candidates.update(self.inverted_index[term].keys())
        
        # Check n-grams
        query_words = query.lower().split()
        for i in range(len(query_words) - 2):
            phrase = ' '.join(query_words[i:i+3])
            if phrase in self.ngram_index:
                candidates.update(self.ngram_index[phrase])
        
        # Apply filters
        if filters:
            filtered = set()
            
            if "type" in filters:
                filtered.update(self.by_type.get(filters["type"], set()))
            
            if "tags" in filters:
                tag_docs = [self.by_tag.get(t, set()) for t in filters["tags"]]
                if tag_docs:
                    filtered.update(set.intersection(*tag_docs))
            
            if "author" in filters:
                filtered.update(self.by_author.get(filters["author"], set()))
            
            candidates &= filtered
        
        # Calculate scores
        scores = []
        for doc_id in candidates:
            if doc_id not in self.doc_vectors:
                continue
            
            # Cosine similarity (simplified)
            score = self._cosine_similarity(query_tf, self.doc_vectors[doc_id])
            
            # Boost exact phrase matches
            for i in range(len(query_words) - 2):
                phrase = ' '.join(query_words[i:i+3])
                if phrase in self.ngram_index and doc_id in self.ngram_index[phrase]:
                    score *= 1.5
            
            scores.append((doc_id, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {"doc_id": doc_id, "score": score}
            for doc_id, score in scores[:limit]
        ]
    
    def _cosine_similarity(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = 0.0
        norm1 = 0.0
        norm2 = 0.0
        
        for term, freq in vec1.items():
            dot_product += freq * vec2.get(term, 0)
            norm1 += freq * freq
        
        for term, freq in vec2.items():
            norm2 += freq * freq
        
        norm1 = norm1 ** 0.5
        norm2 = norm2 ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class SemanticSearch:
    """
    Semantic search across knowledge.
    """
    
    def __init__(self, knowledge_store=None):
        self.store = knowledge_store
        self.index = SearchIndex()
        self._reindex_all()
    
    def _reindex_all(self) -> None:
        """Rebuild the search index"""
        if not self.store:
            return
        
        # Index documents
        for doc in self.store.index.documents.values():
            self.index.add_document(
                doc_id=doc.document_id,
                title=doc.title,
                content=f"{doc.content} {doc.summary}",
                doc_type=doc.document_type.value,
                tags=doc.tags,
                author=doc.author,
            )
        
        # Index entries
        for entry in self.store.entries.values():
            self.index.add_document(
                doc_id=entry.entry_id,
                title=entry.name,
                content=entry.content,
                doc_type=entry.entry_type,
                tags=list(entry.tags),
            )
    
    def search(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform semantic search"""
        results = []
        
        # Build filters
        filters = {}
        if tags:
            filters["tags"] = tags
        if entity_types:
            filters["type"] = entity_types[0] if len(entity_types) == 1 else None
        
        # Search documents
        doc_results = self.index.search(query, filters, limit)
        
        for doc_result in doc_results:
            doc_id = doc_result["doc_id"]
            
            # Try to get document
            doc = self.store.get_document(doc_id) if self.store else None
            entry = self.store.get_entry(doc_id) if self.store else None
            
            entity = doc or entry
            if not entity:
                continue
            
            # Determine type and title
            if doc:
                entity_type = doc.document_type.value
                title = doc.title
                description = doc.summary or doc.content[:200]
            else:
                entity_type = entry.entry_type
                title = entry.name
                description = entry.description
            
            # Generate highlights
            highlights = self._generate_highlights(query, description)
            
            results.append(SearchResult(
                result_id=str(uuid.uuid4()),
                entity_id=doc_id,
                entity_type=entity_type,
                title=title,
                description=description,
                score=doc_result["score"],
                matched_terms=self._tokenize(query),
                highlights=highlights,
                entity=entity,
            ))
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return [t for t in text.split() if len(t) >= 2]
    
    def _generate_highlights(self, query: str, text: str) -> List[str]:
        """Generate search result highlights"""
        query_lower = query.lower()
        text_lower = text.lower()
        
        highlights = []
        
        # Find query terms in text
        for term in self._tokenize(query):
            idx = text_lower.find(term)
            if idx >= 0:
                start = max(0, idx - 30)
                end = min(len(text), idx + len(term) + 30)
                highlight = f"...{text[start:end]}..."
                if highlight not in highlights:
                    highlights.append(highlight)
        
        return highlights[:3]  # Max 3 highlights
    
    def find_similar(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Find similar documents/entries"""
        entity = None
        
        if self.store:
            entity = self.store.get_entry(entity_id)
            if not entity:
                doc = self.store.get_document(entity_id)
                if doc:
                    entity = self.store.get_entry(entity_id)
        
        if not entity:
            return []
        
        # Use content for similarity search
        results = self.search(
            query=f"{entity.name} {entity.description} {entity.content}",
            limit=limit + 1
        )
        
        # Filter out the original
        return [r for r in results if r.entity_id != entity_id][:limit]
    
    def get_recent(self, limit: int = 10) -> List[SearchResult]:
        """Get recently updated documents"""
        if not self.store:
            return []
        
        results = []
        for doc in list(self.store.index.documents.values())[:limit]:
            results.append(SearchResult(
                result_id=str(uuid.uuid4()),
                entity_id=doc.document_id,
                entity_type=doc.document_type.value,
                title=doc.title,
                description=doc.summary,
                score=1.0,
                entity=doc,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            ))
        
        return results
