"""
Strategy Graph
============

Graph structure for visual strategy representation.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from .blocks import Block, BlockType, BlockCategory

logger = logging.getLogger(__name__)


class EdgeType(Enum):
    """Types of connections between blocks"""
    DATA = "data"
    SIGNAL = "signal"
    CONTROL = "control"


@dataclass
class GraphEdge:
    """Connection between two blocks"""
    edge_id: str
    source_block_id: str
    source_port_id: str
    target_block_id: str
    target_port_id: str
    edge_type: EdgeType = EdgeType.DATA
    
    # Metadata
    color: str = "#888888"
    label: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_block_id": self.source_block_id,
            "source_port_id": self.source_port_id,
            "target_block_id": self.target_block_id,
            "target_port_id": self.target_port_id,
            "edge_type": self.edge_type.value,
            "color": self.color,
            "label": self.label
        }


@dataclass
class GraphNode:
    """A node in the strategy graph"""
    node_id: str
    block: Block
    
    # UI state
    selected: bool = False
    locked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "block": self.block.to_dict(),
            "selected": self.selected,
            "locked": self.locked
        }


class StrategyGraph:
    """
    Graph representation of a strategy.
    
    Contains blocks (nodes) and connections (edges).
    """
    
    def __init__(self):
        self.graph_id: str = str(uuid4())
        self.name: str = "Untitled Strategy"
        self.description: str = ""
        self.version: str = "1.0.0"
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        
        # Graph structure
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        
        # Indices for fast lookup
        self._block_index: Dict[str, str] = {}  # block_id -> node_id
        self._outgoing_edges: Dict[str, Set[str]] = {}  # node_id -> set of edge_ids
        self._incoming_edges: Dict[str, Set[str]] = {}  # node_id -> set of edge_ids
    
    def add_node(self, block: Block, node_id: str = None) -> GraphNode:
        """Add a block to the graph"""
        node_id = node_id or str(uuid4())
        
        node = GraphNode(
            node_id=node_id,
            block=block
        )
        
        self.nodes[node_id] = node
        self._block_index[block.block_id] = node_id
        self._outgoing_edges[node_id] = set()
        self._incoming_edges[node_id] = set()
        
        self.updated_at = datetime.now()
        
        logger.info(f"Added node: {node_id} ({block.block_type.value})")
        
        return node
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all connected edges"""
        if node_id not in self.nodes:
            return False
        
        # Remove all connected edges
        edges_to_remove = list(self.get_node_edges(node_id))
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)
        
        # Remove node
        block = self.nodes[node_id].block
        del self._block_index[block.block_id]
        del self._outgoing_edges[node_id]
        del self._incoming_edges[node_id]
        del self.nodes[node_id]
        
        self.updated_at = datetime.now()
        
        return True
    
    def add_edge(
        self,
        source_block_id: str,
        source_port_id: str,
        target_block_id: str,
        target_port_id: str,
        edge_type: EdgeType = EdgeType.DATA,
        edge_id: str = None
    ) -> Optional[GraphEdge]:
        """Add a connection between blocks"""
        # Validate that both blocks exist
        if source_block_id not in self._block_index:
            logger.error(f"Source block not found: {source_block_id}")
            return None
        
        if target_block_id not in self._block_index:
            logger.error(f"Target block not found: {target_block_id}")
            return None
        
        source_node_id = self._block_index[source_block_id]
        target_node_id = self._block_index[target_block_id]
        
        # Check for cycles
        if self._would_create_cycle(source_node_id, target_node_id):
            logger.warning("Edge would create a cycle")
            return None
        
        edge_id = edge_id or str(uuid4())
        
        edge = GraphEdge(
            edge_id=edge_id,
            source_block_id=source_block_id,
            source_port_id=source_port_id,
            target_block_id=target_block_id,
            target_port_id=target_port_id,
            edge_type=edge_type
        )
        
        self.edges[edge_id] = edge
        self._outgoing_edges[source_node_id].add(edge_id)
        self._incoming_edges[target_node_id].add(edge_id)
        
        self.updated_at = datetime.now()
        
        return edge
    
    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge"""
        if edge_id not in self.edges:
            return False
        
        edge = self.edges[edge_id]
        
        source_node_id = self._block_index.get(edge.source_block_id)
        target_node_id = self._block_index.get(edge.target_block_id)
        
        if source_node_id and source_node_id in self._outgoing_edges:
            self._outgoing_edges[source_node_id].discard(edge_id)
        
        if target_node_id and target_node_id in self._incoming_edges:
            self._incoming_edges[target_node_id].discard(edge_id)
        
        del self.edges[edge_id]
        
        self.updated_at = datetime.now()
        
        return True
    
    def _would_create_cycle(self, source_node_id: str, target_node_id: str) -> bool:
        """Check if adding edge would create a cycle"""
        # Check if target can reach source (opposite direction)
        visited = set()
        stack = [target_node_id]
        
        while stack:
            current = stack.pop()
            if current == source_node_id:
                return True
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for edge_id in self._outgoing_edges.get(current, []):
                edge = self.edges.get(edge_id)
                if edge:
                    next_node = self._block_index.get(edge.target_block_id)
                    if next_node:
                        stack.append(next_node)
        
        return False
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)
    
    def get_block(self, block_id: str) -> Optional[Block]:
        """Get a block by ID"""
        node_id = self._block_index.get(block_id)
        if node_id:
            node = self.nodes.get(node_id)
            return node.block if node else None
        return None
    
    def get_node_edges(self, node_id: str) -> List[GraphEdge]:
        """Get all edges connected to a node"""
        edges = []
        
        for edge_id in self._outgoing_edges.get(node_id, set()):
            if edge_id in self.edges:
                edges.append(self.edges[edge_id])
        
        for edge_id in self._incoming_edges.get(node_id, set()):
            if edge_id in self.edges:
                edges.append(self.edges[edge_id])
        
        return edges
    
    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        """Get incoming edges for a node"""
        edges = []
        for edge_id in self._incoming_edges.get(node_id, set()):
            if edge_id in self.edges:
                edges.append(self.edges[edge_id])
        return edges
    
    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Get outgoing edges for a node"""
        edges = []
        for edge_id in self._outgoing_edges.get(node_id, set()):
            if edge_id in self.edges:
                edges.append(self.edges[edge_id])
        return edges
    
    def get_source_nodes(self) -> List[GraphNode]:
        """Get nodes with no incoming edges (entry points)"""
        sources = []
        for node_id, node in self.nodes.items():
            if not self._incoming_edges.get(node_id):
                sources.append(node)
        return sources
    
    def get_sink_nodes(self) -> List[GraphNode]:
        """Get nodes with no outgoing edges (exit points)"""
        sinks = []
        for node_id, node in self.nodes.items():
            if not self._outgoing_edges.get(node_id):
                sinks.append(node)
        return sinks
    
    def topological_sort(self) -> List[GraphNode]:
        """Get topological order of nodes"""
        # Calculate in-degrees
        in_degree = {nid: len(self._incoming_edges.get(nid, set())) for nid in self.nodes}
        
        # Start with nodes with no incoming edges
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []
        
        while queue:
            node_id = queue.pop(0)
            sorted_nodes.append(self.nodes[node_id])
            
            for edge_id in self._outgoing_edges.get(node_id, set()):
                edge = self.edges.get(edge_id)
                if edge:
                    target_node = self._block_index.get(edge.target_block_id)
                    if target_node:
                        in_degree[target_node] -= 1
                        if in_degree[target_node] == 0:
                            queue.append(target_node)
        
        return sorted_nodes
    
    def find_unreachable_blocks(self) -> List[GraphNode]:
        """Find blocks that cannot be reached from inputs"""
        source_nodes = self.get_source_nodes()
        
        # Find all reachable nodes
        reachable = set()
        stack = [n.node_id for n in source_nodes]
        
        while stack:
            node_id = stack.pop()
            if node_id in reachable:
                continue
            
            reachable.add(node_id)
            
            for edge_id in self._outgoing_edges.get(node_id, set()):
                edge = self.edges.get(edge_id)
                if edge:
                    target_node = self._block_index.get(edge.target_block_id)
                    if target_node:
                        stack.append(target_node)
        
        # Find unreachable
        unreachable = [n for nid, n in self.nodes.items() if nid not in reachable]
        
        return unreachable
    
    def get_execution_order(self) -> List[Tuple[int, GraphNode]]:
        """Get execution order with depths"""
        sorted_nodes = self.topological_sort()
        depths = {}
        
        for node in sorted_nodes:
            # Calculate depth based on incoming edges
            max_depth = 0
            for edge in self.get_incoming_edges(node.node_id):
                source_node = self._block_index.get(edge.source_block_id)
                if source_node and source_node in depths:
                    max_depth = max(max_depth, depths[source_node] + 1)
            
            depths[node.node_id] = max_depth
        
        return [(depths[n.node_id], n) for n in sorted_nodes]
    
    def calculate_total_cost(self) -> float:
        """Calculate total estimated computational cost"""
        total = 0.0
        for node in self.nodes.values():
            total += node.block.compute_cost()
        return total
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        category_counts = {}
        for node in self.nodes.values():
            cat = node.block.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "source_nodes": len(self.get_source_nodes()),
            "sink_nodes": len(self.get_sink_nodes()),
            "unreachable_nodes": len(self.find_unreachable_blocks()),
            "category_counts": category_counts,
            "total_cost": self.calculate_total_cost(),
            "execution_depth": max([d for d, _ in self.get_execution_order()], default=0) + 1
        }
    
    def get_hash(self) -> str:
        """Get deterministic hash for the entire graph"""
        graph_data = {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()}
        }
        return hashlib.sha256(
            json.dumps(graph_data, sort_keys=True, default=str).encode()
        ).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()},
            "statistics": self.get_statistics(),
            "hash": self.get_hash()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyGraph":
        """Deserialize from dictionary"""
        graph = cls()
        
        graph.graph_id = data.get("graph_id", str(uuid4()))
        graph.name = data.get("name", "Imported Strategy")
        graph.description = data.get("description", "")
        graph.version = data.get("version", "1.0.0")
        graph.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        graph.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        
        # Restore nodes
        for nid, ndata in data.get("nodes", {}).items():
            block = Block.from_dict(ndata["block"])
            node = GraphNode(
                node_id=nid,
                block=block,
                selected=ndata.get("selected", False),
                locked=ndata.get("locked", False)
            )
            graph.nodes[nid] = node
            graph._block_index[block.block_id] = nid
            graph._outgoing_edges[nid] = set()
            graph._incoming_edges[nid] = set()
        
        # Restore edges
        for eid, edata in data.get("edges", {}).items():
            edge = GraphEdge(
                edge_id=eid,
                source_block_id=edata["source_block_id"],
                source_port_id=edata["source_port_id"],
                target_block_id=edata["target_block_id"],
                target_port_id=edata["target_port_id"],
                edge_type=EdgeType(edata.get("edge_type", "data")),
                color=edata.get("color", "#888888"),
                label=edata.get("label", "")
            )
            graph.edges[eid] = edge
            
            source_node = graph._block_index.get(edge.source_block_id)
            target_node = graph._block_index.get(edge.target_block_id)
            
            if source_node:
                graph._outgoing_edges[source_node].add(eid)
            if target_node:
                graph._incoming_edges[target_node].add(eid)
        
        return graph
    
    def clone(self) -> "StrategyGraph":
        """Create a deep copy of the graph"""
        data = self.to_dict()
        return StrategyGraph.from_dict(data)
