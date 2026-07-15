"""
Knowledge Graph - Internal Market Knowledge System

Graph database connecting markets, patterns, trades, strategies, indicators, models, and more.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the knowledge graph"""
    MARKET = "market"
    PATTERN = "pattern"
    TRADE = "trade"
    STRATEGY = "strategy"
    INDICATOR = "indicator"
    MODEL = "model"
    RISK_EVENT = "risk_event"
    REGIME = "regime"
    SUCCESS = "success"
    FAILURE = "failure"
    FEATURE = "feature"
    SIGNAL = "signal"
    REGION = "region"  # Geographic/Time region


class RelationshipType(Enum):
    """Types of relationships"""
    CAUSED = "caused"
    PREDICTED = "predicted"
    CORRELATED_WITH = "correlated_with"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    FOLLOWED_BY = "followed_by"
    CONTRADICTS = "contradicts"
    ENABLED = "enabled"


@dataclass
class Node:
    """A node in the knowledge graph"""
    id: str
    node_type: NodeType
    name: str
    
    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Temporal data
    timestamp: datetime = field(default_factory=datetime.utcnow)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    
    # Confidence
    confidence: float = 1.0
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    # Metadata
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "properties": self.properties,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "tags": self.tags,
        }


@dataclass
class Relationship:
    """A relationship between nodes"""
    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    
    # Properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Strength
    strength: float = 1.0  # 0-1
    
    # Temporal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "properties": self.properties,
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
        }


class KnowledgeGraph:
    """
    Internal knowledge graph for market relationships.
    
    Features:
    - Multi-type nodes and relationships
    - Graph traversal for decision explanation
    - Pattern discovery
    - Correlation analysis
    - Causal inference
    - Semantic search
    """
    
    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._relationships: Dict[str, Relationship] = {}
        
        # Indexes for fast lookup
        self._type_index: Dict[NodeType, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # node_id -> related node_ids
        
        logger.info("Knowledge graph initialized")
    
    def add_node(self, node: Node) -> str:
        """Add a node to the graph"""
        self._nodes[node.id] = node
        
        # Update indexes
        if node.node_type not in self._type_index:
            self._type_index[node.node_type] = set()
        self._type_index[node.node_type].add(node.id)
        
        for tag in node.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(node.id)
        
        return node.id
    
    def add_relationship(self, relationship: Relationship) -> str:
        """Add a relationship"""
        self._relationships[relationship.id] = relationship
        
        # Update adjacency list
        if relationship.source_id not in self._adjacency:
            self._adjacency[relationship.source_id] = set()
        self._adjacency[relationship.source_id].add(relationship.target_id)
        
        if relationship.target_id not in self._adjacency:
            self._adjacency[relationship.target_id] = set()
        self._adjacency[relationship.target_id].add(relationship.source_id)
        
        return relationship.id
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID"""
        return self._nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """Get all nodes of a specific type"""
        node_ids = self._type_index.get(node_type, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]
    
    def get_nodes_by_tags(self, tags: List[str]) -> List[Node]:
        """Get nodes with any of the specified tags"""
        node_ids = set()
        for tag in tags:
            if tag in self._tag_index:
                node_ids.update(self._tag_index[tag])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]
    
    def find_similar_nodes(
        self,
        node_id: str,
        limit: int = 10,
    ) -> List[tuple[Node, float]]:
        """Find similar nodes based on relationships"""
        node = self._nodes.get(node_id)
        if not node:
            return []
        
        # Find nodes with similar relationships
        similar_scores: Dict[str, float] = {}
        
        # Get direct neighbors
        neighbors = self._adjacency.get(node_id, set())
        
        # For each neighbor, find their neighbors
        for neighbor_id in neighbors:
            neighbor_neighbors = self._adjacency.get(neighbor_id, set())
            for nn_id in neighbor_neighbors:
                if nn_id != node_id and nn_id in self._nodes:
                    # Calculate similarity score
                    if nn_id not in similar_scores:
                        similar_scores[nn_id] = 0
                    similar_scores[nn_id] += 0.5
        
        # Sort by score
        sorted_nodes = sorted(
            similar_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [(self._nodes[nid], score) for nid, score in sorted_nodes]
    
    def find_patterns(
        self,
        pattern: List[tuple[NodeType, RelationshipType, NodeType]],
    ) -> List[List[Node]]:
        """Find subgraph patterns"""
        # Simple pattern matching
        # In production, would use graph matching algorithms
        results = []
        
        for node_id, node in self._nodes.items():
            if node.node_type == pattern[0][0]:
                path = [node]
                # Would recursively match pattern
                results.append(path)
        
        return results
    
    def get_related_nodes(
        self,
        node_id: str,
        depth: int = 1,
        relationship_types: Optional[List[RelationshipType]] = None,
    ) -> Dict[str, List[Node]]:
        """Get related nodes up to specified depth"""
        if depth == 0:
            return {}
        
        visited = {node_id}
        result: Dict[str, List[Node]] = {node_id: []}
        current_level = {node_id}
        
        for _ in range(depth):
            next_level = set()
            
            for current_id in current_level:
                related_ids = self._adjacency.get(current_id, set())
                
                for related_id in related_ids:
                    if related_id not in visited:
                        visited.add(related_id)
                        next_level.add(related_id)
                        
                        if related_id in self._nodes:
                            rel_type = self._get_relationship_type(current_id, related_id)
                            
                            if relationship_types is None or rel_type in relationship_types:
                                if related_id not in result:
                                    result[related_id] = []
                                result[related_id].append(self._nodes[related_id])
            
            current_level = next_level
        
        return result
    
    def _get_relationship_type(self, source_id: str, target_id: str) -> Optional[RelationshipType]:
        """Get the relationship type between two nodes"""
        for rel in self._relationships.values():
            if (rel.source_id == source_id and rel.target_id == target_id) or \
               (rel.source_id == target_id and rel.target_id == source_id):
                return rel.relationship_type
        return None
    
    def explain_decision(
        self,
        decision_id: str,
        trade_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Explain a decision using graph traversal"""
        # Find related nodes
        related = self.get_related_nodes(decision_id, depth=3)
        
        explanation = {
            "decision_id": decision_id,
            "factors": [],
            "similar_decisions": [],
            "historical_precedents": [],
        }
        
        # Categorize related nodes
        for node_id, nodes in related.items():
            for node in nodes:
                if node.node_type == NodeType.PATTERN:
                    explanation["factors"].append({
                        "type": "pattern",
                        "name": node.name,
                        "confidence": node.confidence,
                    })
                elif node.node_type == NodeType.INDICATOR:
                    explanation["factors"].append({
                        "type": "indicator",
                        "name": node.name,
                        "value": node.properties.get("value"),
                    })
        
        # Find similar successful decisions
        if decision_id in self._nodes:
            similar = self.find_similar_nodes(decision_id)
            explanation["similar_decisions"] = [
                {"name": n.name, "confidence": s}
                for n, s in similar[:5]
            ]
        
        return explanation
    
    def add_market_data(
        self,
        symbol: str,
        regime: str,
        volatility: float,
        trends: List[str],
    ) -> str:
        """Add market data to the graph"""
        # Create market node
        market = Node(
            id=str(uuid.uuid4()),
            node_type=NodeType.MARKET,
            name=symbol,
            properties={
                "regime": regime,
                "volatility": volatility,
            },
            tags=["market", symbol],
        )
        self.add_node(market)
        
        # Create regime node
        regime_node = Node(
            id=str(uuid.uuid4()),
            node_type=NodeType.REGIME,
            name=regime,
            tags=["regime", regime],
        )
        self.add_node(regime_node)
        
        # Link market to regime
        rel = Relationship(
            id=str(uuid.uuid4()),
            source_id=market.id,
            target_id=regime_node.id,
            relationship_type=RelationshipType.PART_OF,
        )
        self.add_relationship(rel)
        
        return market.id
    
    def add_trade_result(
        self,
        trade_data: Dict[str, Any],
        signal_ids: List[str],
        success: bool,
    ) -> str:
        """Add a trade result and link to signals"""
        # Create trade node
        trade = Node(
            id=str(uuid.uuid4()),
            node_type=NodeType.TRADE if success else NodeType.FAILURE,
            name=f"Trade {trade_data.get('symbol')}",
            properties=trade_data,
            tags=["trade", trade_data.get("symbol", "")],
        )
        self.add_node(trade)
        
        # Link to signals
        for signal_id in signal_ids:
            rel = Relationship(
                id=str(uuid.uuid4()),
                source_id=signal_id,
                target_id=trade.id,
                relationship_type=RelationshipType.CAUSED,
            )
            self.add_relationship(rel)
        
        return trade.id
    
    def query(
        self,
        query_type: str,
        parameters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Query the knowledge graph"""
        if query_type == "market_regime":
            symbol = parameters.get("symbol")
            nodes = self.get_nodes_by_type(NodeType.MARKET)
            return [n.to_dict() for n in nodes if n.properties.get("symbol") == symbol]
        
        elif query_type == "pattern_trades":
            pattern_name = parameters.get("pattern")
            nodes = self.get_nodes_by_type(NodeType.PATTERN)
            return [n.to_dict() for n in nodes if pattern_name in n.name]
        
        elif query_type == "correlated_indicators":
            indicator = parameters.get("indicator")
            nodes = self.get_nodes_by_type(NodeType.INDICATOR)
            return [n.to_dict() for n in nodes if n.name == indicator]
        
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            "total_nodes": len(self._nodes),
            "total_relationships": len(self._relationships),
            "by_type": {
                node_type.value: len(node_ids)
                for node_type, node_ids in self._type_index.items()
            },
            "avg_connections": (
                sum(len(conns) for conns in self._adjacency.values()) / len(self._nodes)
                if self._nodes else 0
            ),
        }
    
    def export_graph(self) -> Dict[str, Any]:
        """Export the entire graph"""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "relationships": [r.to_dict() for r in self._relationships.values()],
            "exported_at": datetime.utcnow().isoformat(),
        }
