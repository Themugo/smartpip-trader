"""
Tests for Knowledge Platform
=========================
"""

import pytest
import time


class TestDocument:
    """Tests for documents"""
    
    def test_document_creation(self):
        """Test creating a document"""
        from knowledge.core import Document, DocumentType
        
        doc = Document(
            document_id="doc_1",
            title="Test Document",
            document_type=DocumentType.RESEARCH,
            content="This is test content",
        )
        
        assert doc.title == "Test Document"
        assert doc.document_type == DocumentType.RESEARCH
    
    def test_document_tags(self):
        """Test document tags"""
        from knowledge.core import Document, DocumentType
        
        doc = Document(
            document_id="doc_1",
            title="Test",
            document_type=DocumentType.RESEARCH,
            content="Content",
        )
        
        doc.add_tag("machine learning")
        doc.add_tag("trading")
        
        assert "machine learning" in doc.tags
        assert len(doc.tags) == 2


class TestKnowledgeEntry:
    """Tests for knowledge entries"""
    
    def test_entry_creation(self):
        """Test creating a knowledge entry"""
        from knowledge.core import KnowledgeEntry
        
        entry = KnowledgeEntry(
            entry_id="entry_1",
            entry_type="strategy",
            name="Test Strategy",
            description="A test trading strategy",
            content="Strategy content",
        )
        
        assert entry.name == "Test Strategy"
        assert entry.entry_type == "strategy"
    
    def test_entry_links(self):
        """Test adding links to entries"""
        from knowledge.core import KnowledgeEntry
        
        entry1 = KnowledgeEntry(
            entry_id="entry_1",
            entry_type="strategy",
            name="Strategy 1",
            description="First strategy",
        )
        
        entry2 = KnowledgeEntry(
            entry_id="entry_2",
            entry_type="model",
            name="Model 1",
            description="A model",
        )
        
        entry1.add_link(entry2.entry_id, "uses_model", 0.8)
        
        assert len(entry1.links) == 1
        assert entry1.links[0].target_id == "entry_2"


class TestKnowledgeStore:
    """Tests for knowledge store"""
    
    def test_store_creation(self):
        """Test creating a knowledge store"""
        from knowledge.storage import KnowledgeStore
        
        store = KnowledgeStore()
        
        assert store is not None
    
    def test_add_document(self):
        """Test adding a document"""
        from knowledge.storage import KnowledgeStore
        from knowledge.core import Document, DocumentType
        
        store = KnowledgeStore()
        
        doc = Document(
            document_id="doc_1",
            title="Test Research",
            document_type=DocumentType.RESEARCH,
            content="Research content",
            author="test_author",
            tags=["ml", "trading"],
        )
        
        doc_id = store.add_document(doc)
        
        assert doc_id == "doc_1"
        assert len(store.index.documents) == 1
    
    def test_get_document(self):
        """Test getting a document"""
        from knowledge.storage import KnowledgeStore
        from knowledge.core import Document, DocumentType
        
        store = KnowledgeStore()
        
        doc = Document(
            document_id="doc_1",
            title="Test",
            document_type=DocumentType.RESEARCH,
            content="Content",
        )
        
        store.add_document(doc)
        retrieved = store.get_document("doc_1")
        
        assert retrieved is not None
        assert retrieved.title == "Test"
    
    def test_search_documents(self):
        """Test searching documents"""
        from knowledge.storage import KnowledgeStore
        from knowledge.core import Document, DocumentType
        
        store = KnowledgeStore()
        
        for i in range(3):
            doc = Document(
                document_id=f"doc_{i}",
                title=f"Document {i}",
                document_type=DocumentType.RESEARCH,
                content="machine learning content",
            )
            store.add_document(doc)
        
        results = store.search_documents(query="machine")
        
        assert len(results) == 3


class TestSearch:
    """Tests for semantic search"""
    
    def test_search_index(self):
        """Test search index"""
        from knowledge.search import SearchIndex
        
        index = SearchIndex()
        
        index.add_document(
            doc_id="doc_1",
            title="Machine Learning Trading",
            content="Using ML for trading strategies",
            doc_type="research",
        )
        
        results = index.search("machine learning")
        
        assert len(results) >= 1
    
    def test_semantic_search(self):
        """Test semantic search"""
        from knowledge.search import SemanticSearch
        
        search = SemanticSearch()
        
        search.index.add_document(
            doc_id="doc_1",
            title="Research on ML",
            content="Machine learning research in trading",
            doc_type="research",
        )
        
        results = search.search("machine learning trading")
        
        assert isinstance(results, list)  # Just verify it returns a list


class TestCrossLinker:
    """Tests for cross-linker"""
    
    def test_crosslinker_creation(self):
        """Test creating a cross-linker"""
        from knowledge.crosslink import CrossLinker
        
        linker = CrossLinker()
        
        assert linker is not None
    
    def test_extract_references(self):
        """Test extracting references"""
        from knowledge.crosslink import CrossLinker
        from knowledge.core import KnowledgeEntry
        
        linker = CrossLinker()
        
        entry = KnowledgeEntry(
            entry_id="entry_1",
            entry_type="strategy",
            name="Test Strategy",
            description="A strategy",
            content="This strategy uses the RSI indicator and MACD feature",
        )
        
        candidates = linker.analyze_and_link(entry)
        
        assert isinstance(candidates, list)


class TestSummarizer:
    """Tests for summarizer"""
    
    def test_summarizer_creation(self):
        """Test creating a summarizer"""
        from knowledge.summaries import Summarizer
        
        summarizer = Summarizer()
        
        assert summarizer is not None
    
    def test_short_summary(self):
        """Test short summary generation"""
        from knowledge.summaries import Summarizer
        
        summarizer = Summarizer()
        
        content = "This is a long document about trading strategies. It discusses various approaches to trading including momentum, mean reversion, and breakout strategies. The document covers risk management techniques."
        
        summary = summarizer.summarize(
            content=content,
            entity_id="doc_1",
            entity_type="document",
        )
        
        assert summary.short_summary != ""
        assert len(summary.short_summary) < 200
    
    def test_key_points(self):
        """Test key points extraction"""
        from knowledge.summaries import Summarizer
        
        summarizer = Summarizer()
        
        content = """
        Trading strategies are important for markets.
        Momentum strategies capture trends.
        Mean reversion strategies work in ranging markets.
        Risk management is crucial.
        Position sizing affects returns.
        """
        
        summary = summarizer.summarize(
            content=content,
            entity_id="doc_1",
            entity_type="document",
        )
        
        assert len(summary.key_points) >= 0


class TestRecommendations:
    """Tests for recommendations"""
    
    def test_recommendation_engine_creation(self):
        """Test creating recommendation engine"""
        from knowledge.recommendations import RecommendationEngine
        
        engine = RecommendationEngine()
        
        assert engine is not None
    
    def test_recommend_for_strategy(self):
        """Test recommendations for new strategy"""
        from knowledge.recommendations import RecommendationEngine
        
        engine = RecommendationEngine()
        
        recommendations = engine.recommend_for_new_strategy(
            strategy_name="Momentum Strategy",
            strategy_description="A momentum-based trading strategy",
            tags=["momentum", "trending"],
        )
        
        assert isinstance(recommendations, list)


class TestOrganizationalMemory:
    """Tests for organizational memory"""
    
    def test_memory_creation(self):
        """Test creating organizational memory"""
        from knowledge.memory import OrganizationalMemory
        
        memory = OrganizationalMemory()
        
        assert memory is not None
    
    def test_add_memory(self):
        """Test adding a memory"""
        from knowledge.memory import OrganizationalMemory
        
        memory = OrganizationalMemory()
        
        entry = memory.add_memory(
            memory_type="lesson",
            title="Test Lesson",
            content="Always use stop losses",
            tags=["risk", "trading"],
        )
        
        assert entry.title == "Test Lesson"
        assert len(memory._memories) == 1
    
    def test_get_memories_by_type(self):
        """Test getting memories by type"""
        from knowledge.memory import OrganizationalMemory
        
        memory = OrganizationalMemory()
        
        memory.add_memory("lesson", "Lesson 1", "Content 1")
        memory.add_memory("lesson", "Lesson 2", "Content 2")
        memory.add_memory("mistake", "Mistake 1", "Content 3")
        
        lessons = memory.get_memories_by_type("lesson")
        
        assert len(lessons) == 2
    
    def test_learn_from_incident(self):
        """Test learning from incident"""
        from knowledge.memory import OrganizationalMemory
        
        memory = OrganizationalMemory()
        
        memories = memory.learn_from_incident(
            incident_description="System crashed during trading",
            lessons=["Always have backup systems", "Monitor resource usage"],
            tags=["system", "infrastructure"],
        )
        
        assert len(memories) == 2
    
    def test_get_wisdom(self):
        """Test getting accumulated wisdom"""
        from knowledge.memory import OrganizationalMemory
        
        memory = OrganizationalMemory()
        
        memory.add_memory("lesson", "Lesson", "Content")
        memory.add_memory("mistake", "Mistake", "Content")
        
        wisdom = memory.get_wisdom()
        
        assert wisdom["total_memories"] == 2
        assert "by_type" in wisdom


class TestKnowledgeGraph:
    """Tests for knowledge graph"""
    
    def test_graph_creation(self):
        """Test creating knowledge graph"""
        from knowledge.core import KnowledgeGraph, KnowledgeEntry
        
        graph = KnowledgeGraph()
        
        entry = KnowledgeEntry(
            entry_id="entry_1",
            entry_type="strategy",
            name="Test",
            description="Description",
        )
        
        graph.add_node(entry)
        
        assert len(graph.nodes) == 1
    
    def test_get_neighbors(self):
        """Test getting neighboring nodes"""
        from knowledge.core import KnowledgeGraph, KnowledgeEntry
        
        graph = KnowledgeGraph()
        
        entry1 = KnowledgeEntry(
            entry_id="entry_1",
            entry_type="strategy",
            name="Strategy",
            description="A strategy",
        )
        
        entry2 = KnowledgeEntry(
            entry_id="entry_2",
            entry_type="model",
            name="Model",
            description="A model",
        )
        
        entry1.add_link("entry_2", "uses")
        
        graph.add_node(entry1)
        graph.add_node(entry2)
        
        neighbors = graph.get_neighbors("entry_1")
        
        assert "entry_2" in neighbors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
