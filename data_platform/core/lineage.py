"""
Lineage Tracker

Tracks data and feature lineage for reproducibility and auditability.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class LineageNodeType(Enum):
    """Types of lineage nodes"""
    DATASET = "dataset"
    FEATURE = "feature"
    TRANSFORMATION = "transformation"
    MODEL = "model"
    EXPERIMENT = "experiment"
    ARTIFACT = "artifact"


class LineageEdgeType(Enum):
    """Types of lineage edges"""
    DERIVED_FROM = "derived_from"
    USES = "uses"
    PRODUCES = "produces"
    TRAINS_ON = "trains_on"
    EVALUATED_ON = "evaluated_on"
    REFERENCES = "references"


class LineageEvent:
    """An event in the lineage graph"""
    
    def __init__(
        self,
        event_id: str,
        node_id: str,
        node_type: LineageNodeType,
        event_type: str,
        timestamp: datetime = None,
        actor: str = "",
        details: Optional[Dict[str, Any]] = None,
        upstream_event_ids: Optional[List[str]] = None,
    ):
        self.event_id = event_id
        self.node_id = node_id
        self.node_type = node_type
        self.event_type = event_type
        self.timestamp = timestamp or datetime.utcnow()
        self.actor = actor
        self.details = details or {}
        self.upstream_event_ids = upstream_event_ids or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, LineageNodeType) else self.node_type,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "actor": self.actor,
            "details": self.details,
            "upstream_event_ids": self.upstream_event_ids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageEvent":
        """Create from dictionary"""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("node_type"), str):
            data["node_type"] = LineageNodeType(data["node_type"])
        return cls(**data)


class LineageNode:
    """A node in the lineage graph"""
    
    def __init__(
        self,
        node_id: str,
        name: str,
        node_type: LineageNodeType,
        version: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        created_at: datetime = None,
        created_by: str = "",
    ):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type
        self.version = version
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.created_by = created_by
        
        # Graph structure
        self.upstream: Dict[str, str] = {}  # edge_type -> node_ids
        self.downstream: Dict[str, Set[str]] = {}  # edge_type -> node_ids
    
    def add_upstream(
        self,
        edge_type: LineageEdgeType,
        node_id: str,
    ) -> None:
        """Add an upstream dependency"""
        edge_key = edge_type.value if isinstance(edge_type, LineageEdgeType) else edge_type
        if edge_key not in self.upstream:
            self.upstream[edge_key] = node_id  # Single source per edge type
        else:
            # Multiple sources allowed
            self.upstream[edge_key] = node_id
    
    def add_downstream(
        self,
        edge_type: LineageEdgeType,
        node_id: str,
    ) -> None:
        """Add a downstream dependent"""
        edge_key = edge_type.value if isinstance(edge_type, LineageEdgeType) else edge_type
        if edge_key not in self.downstream:
            self.downstream[edge_key] = set()
        self.downstream[edge_key].add(node_id)
    
    def remove_downstream(
        self,
        edge_type: LineageEdgeType,
        node_id: str,
    ) -> None:
        """Remove a downstream dependent"""
        edge_key = edge_type.value if isinstance(edge_type, LineageEdgeType) else edge_type
        if edge_key in self.downstream:
            self.downstream[edge_key].discard(node_id)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value if isinstance(self.node_type, LineageNodeType) else self.node_type,
            "version": self.version,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "created_by": self.created_by,
            "upstream": self.upstream,
            "downstream": {k: list(v) for k, v in self.downstream.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageNode":
        """Create from dictionary"""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("node_type"), str):
            data["node_type"] = LineageNodeType(data["node_type"])
        if "downstream" in data:
            data["downstream"] = {k: set(v) for k, v in data["downstream"].items()}
        return cls(**data)


class LineageTracker:
    """
    Lineage Tracker for data and feature provenance.
    
    Features:
    - Full data lineage tracking
    - Feature lineage tracking
    - Transformation chain recording
    - Reproducibility support
    - Impact analysis
    - Audit trail
    """
    
    def __init__(self, storage_path: str = "data_platform/lineage"):
        self._storage_path = storage_path
        self._nodes: Dict[str, LineageNode] = {}
        self._events: List[LineageEvent] = []
        
        # Indexes
        self._by_type: Dict[str, Set[str]] = {}
        self._by_name: Dict[str, str] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load lineage index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                # Load nodes
                for node_data in data.get("nodes", []):
                    node = LineageNode.from_dict(node_data)
                    self._nodes[node.node_id] = node
                    self._update_indexes(node)
                
                # Load events
                for event_data in data.get("events", []):
                    self._events.append(LineageEvent.from_dict(event_data))
                
                logger.info(
                    f"Loaded {len(self._nodes)} nodes and "
                    f"{len(self._events)} events"
                )
            except Exception as e:
                logger.warning(f"Could not load lineage index: {e}")
    
    def _save_index(self) -> None:
        """Save lineage index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "events": [e.to_dict() for e in self._events],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _update_indexes(self, node: LineageNode) -> None:
        """Update all indexes for a node"""
        type_key = node.node_type.value if isinstance(node.node_type, LineageNodeType) else node.node_type
        if type_key not in self._by_type:
            self._by_type[type_key] = set()
        self._by_type[type_key].add(node.node_id)
        
        self._by_name[node.name.lower()] = node.node_id
    
    # ==================== Node Operations ====================
    
    def register_node(
        self,
        node_id: str,
        name: str,
        node_type: LineageNodeType,
        version: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        created_by: str = "",
    ) -> LineageNode:
        """Register a new lineage node"""
        if node_id in self._nodes:
            logger.warning(f"Node {node_id} already exists")
            return self._nodes[node_id]
        
        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            version=version,
            metadata=metadata,
            created_by=created_by,
        )
        
        self._nodes[node_id] = node
        self._update_indexes(node)
        self._save_index()
        
        logger.info(f"Registered lineage node: {name} ({node_id})")
        return node
    
    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Get a lineage node"""
        return self._nodes.get(node_id)
    
    def get_node_by_name(self, name: str) -> Optional[LineageNode]:
        """Get a lineage node by name"""
        node_id = self._by_name.get(name.lower())
        return self._nodes.get(node_id) if node_id else None
    
    def update_node(
        self,
        node_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> Optional[LineageNode]:
        """Update a lineage node"""
        node = self._nodes.get(node_id)
        if not node:
            return None
        
        if metadata:
            node.metadata.update(metadata)
        if version:
            node.version = version
        
        self._save_index()
        return node
    
    # ==================== Edge Operations ====================
    
    def link_nodes(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_type: LineageEdgeType,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a lineage link between two nodes"""
        source = self._nodes.get(source_node_id)
        target = self._nodes.get(target_node_id)
        
        if not source or not target:
            logger.warning(f"Source or target node not found")
            return False
        
        # Add edges
        source.add_downstream(edge_type, target_node_id)
        target.add_upstream(edge_type, source_node_id)
        
        # Record event
        self._record_event(
            node_id=target_node_id,
            node_type=target.node_type,
            event_type="lineage_linked",
            details={
                "edge_type": edge_type.value if isinstance(edge_type, LineageEdgeType) else edge_type,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                **(details or {}),
            },
        )
        
        self._save_index()
        logger.info(
            f"Linked {source.name} -> {target.name} ({edge_type.value})"
        )
        return True
    
    def unlink_nodes(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_type: LineageEdgeType,
    ) -> bool:
        """Remove a lineage link"""
        source = self._nodes.get(source_node_id)
        target = self._nodes.get(target_node_id)
        
        if not source or not target:
            return False
        
        edge_key = edge_type.value if isinstance(edge_type, LineageEdgeType) else edge_type
        target.upstream.pop(edge_key, None)
        source.remove_downstream(edge_type, target_node_id)
        
        self._save_index()
        return True
    
    # ==================== Event Operations ====================
    
    def _record_event(
        self,
        node_id: str,
        node_type: LineageNodeType,
        event_type: str,
        actor: str = "",
        details: Optional[Dict[str, Any]] = None,
        upstream_event_ids: Optional[List[str]] = None,
    ) -> LineageEvent:
        """Record a lineage event"""
        event = LineageEvent(
            event_id=str(uuid.uuid4()),
            node_id=node_id,
            node_type=node_type,
            event_type=event_type,
            actor=actor,
            details=details or {},
            upstream_event_ids=upstream_event_ids or [],
        )
        
        self._events.append(event)
        return event
    
    def record_dataset_created(
        self,
        dataset_id: str,
        source: str = "",
        created_by: str = "",
    ) -> LineageEvent:
        """Record dataset creation"""
        node = self.register_node(
            node_id=dataset_id,
            name=dataset_id,
            node_type=LineageNodeType.DATASET,
            metadata={"source": source},
            created_by=created_by,
        )
        
        return self._record_event(
            node_id=dataset_id,
            node_type=LineageNodeType.DATASET,
            event_type="dataset_created",
            actor=created_by,
            details={"source": source},
        )
    
    def record_feature_created(
        self,
        feature_id: str,
        dependencies: Optional[List[str]] = None,
        created_by: str = "",
    ) -> LineageEvent:
        """Record feature creation"""
        node = self.register_node(
            node_id=feature_id,
            name=feature_id,
            node_type=LineageNodeType.FEATURE,
            metadata={"dependencies": dependencies or []},
            created_by=created_by,
        )
        
        # Link to dependencies
        if dependencies:
            for dep_id in dependencies:
                self.link_nodes(
                    source_node_id=dep_id,
                    target_node_id=feature_id,
                    edge_type=LineageEdgeType.DERIVED_FROM,
                )
        
        return self._record_event(
            node_id=feature_id,
            node_type=LineageNodeType.FEATURE,
            event_type="feature_created",
            actor=created_by,
            details={"dependencies": dependencies or []},
        )
    
    def record_transformation(
        self,
        transformation_id: str,
        input_dataset_ids: List[str],
        output_dataset_id: str,
        transformation_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        created_by: str = "",
    ) -> LineageEvent:
        """Record a data transformation"""
        # Create transformation node
        node = self.register_node(
            node_id=transformation_id,
            name=transformation_id,
            node_type=LineageNodeType.TRANSFORMATION,
            metadata={
                "type": transformation_type,
                "parameters": parameters or {},
            },
            created_by=created_by,
        )
        
        # Link inputs
        for input_id in input_dataset_ids:
            self.link_nodes(
                source_node_id=input_id,
                target_node_id=transformation_id,
                edge_type=LineageEdgeType.USES,
                details={"direction": "input"},
            )
        
        # Link output
        self.link_nodes(
            source_node_id=transformation_id,
            target_node_id=output_dataset_id,
            edge_type=LineageEdgeType.PRODUCES,
            details={"direction": "output"},
        )
        
        return self._record_event(
            node_id=transformation_id,
            node_type=LineageNodeType.TRANSFORMATION,
            event_type="transformation_performed",
            actor=created_by,
            details={
                "transformation_type": transformation_type,
                "input_datasets": input_dataset_ids,
                "output_dataset": output_dataset_id,
                "parameters": parameters or {},
            },
            upstream_event_ids=[],
        )
    
    # ==================== Query Operations ====================
    
    def get_upstream_lineage(
        self,
        node_id: str,
        depth: int = -1,
        edge_types: Optional[List[LineageEdgeType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upstream lineage (data sources).
        
        Args:
            node_id: Starting node ID
            depth: Maximum depth (-1 for unlimited)
            edge_types: Filter by specific edge types
        """
        lineage = []
        visited = set()
        
        def traverse(node_id: str, current_depth: int) -> None:
            if node_id in visited:
                return
            if depth >= 0 and current_depth >= depth:
                return
            
            visited.add(node_id)
            node = self._nodes.get(node_id)
            if not node:
                return
            
            lineage.append({
                "node": node.to_dict(),
                "depth": current_depth,
            })
            
            for edge_type_str, source_id in node.upstream.items():
                if edge_types:
                    edge_type = LineageEdgeType(edge_type_str)
                    if edge_type not in edge_types:
                        continue
                traverse(source_id, current_depth + 1)
        
        traverse(node_id, 0)
        return lineage
    
    def get_downstream_lineage(
        self,
        node_id: str,
        depth: int = -1,
        edge_types: Optional[List[LineageEdgeType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get downstream lineage (impact analysis).
        
        Args:
            node_id: Starting node ID
            depth: Maximum depth (-1 for unlimited)
            edge_types: Filter by specific edge types
        """
        lineage = []
        visited = set()
        
        def traverse(node_id: str, current_depth: int) -> None:
            if node_id in visited:
                return
            if depth >= 0 and current_depth >= depth:
                return
            
            visited.add(node_id)
            node = self._nodes.get(node_id)
            if not node:
                return
            
            lineage.append({
                "node": node.to_dict(),
                "depth": current_depth,
            })
            
            for edge_type_str, target_ids in node.downstream.items():
                if edge_types:
                    edge_type = LineageEdgeType(edge_type_str)
                    if edge_type not in edge_types:
                        continue
                for target_id in target_ids:
                    traverse(target_id, current_depth + 1)
        
        traverse(node_id, 0)
        return lineage
    
    def get_full_lineage(self, node_id: str) -> Dict[str, Any]:
        """Get full lineage graph for a node"""
        node = self._nodes.get(node_id)
        if not node:
            return {}
        
        return {
            "node": node.to_dict(),
            "upstream": self.get_upstream_lineage(node_id),
            "downstream": self.get_downstream_lineage(node_id),
        }
    
    def get_data_lineage(self, dataset_id: str) -> Dict[str, Any]:
        """Get data lineage for a dataset"""
        return {
            "dataset_id": dataset_id,
            "sources": self.get_upstream_lineage(
                dataset_id,
                edge_types=[LineageEdgeType.DERIVED_FROM, LineageEdgeType.USES],
            ),
            "derived_datasets": self.get_downstream_lineage(
                dataset_id,
                edge_types=[LineageEdgeType.PRODUCES],
            ),
        }
    
    def get_feature_lineage(self, feature_id: str) -> Dict[str, Any]:
        """Get feature lineage"""
        return {
            "feature_id": feature_id,
            "dependencies": self.get_upstream_lineage(
                feature_id,
                edge_types=[LineageEdgeType.DERIVED_FROM],
            ),
            "dependents": self.get_downstream_lineage(
                feature_id,
                edge_types=[LineageEdgeType.DERIVED_FROM],
            ),
        }
    
    def get_events_for_node(
        self,
        node_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[LineageEvent]:
        """Get events for a specific node"""
        events = [e for e in self._events if e.node_id == node_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_impact_analysis(
        self,
        node_id: str,
        include_types: Optional[List[LineageNodeType]] = None,
    ) -> Dict[str, Any]:
        """Perform impact analysis on a node"""
        downstream = self.get_downstream_lineage(node_id)
        
        if include_types:
            downstream = [
                item for item in downstream
                if LineageNodeType(item["node"]["node_type"]) in include_types
            ]
        
        # Group by type
        by_type: Dict[str, List] = {}
        for item in downstream:
            node_type = item["node"]["node_type"]
            if node_type not in by_type:
                by_type[node_type] = []
            by_type[node_type].append(item["node"])
        
        return {
            "source_node_id": node_id,
            "total_affected": len(downstream),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "affected_nodes": downstream,
        }
    
    def search(
        self,
        query: Optional[str] = None,
        node_type: Optional[LineageNodeType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[LineageNode]:
        """Search lineage nodes"""
        results = list(self._nodes.values())
        
        if query:
            query_lower = query.lower()
            results = [
                n for n in results
                if query_lower in n.name.lower() or
                   query_lower in str(n.metadata).lower()
            ]
        
        if node_type:
            results = [n for n in results if n.node_type == node_type]
        
        if tags:
            results = [
                n for n in results
                if any(tag in n.metadata.get("tags", []) for tag in tags)
            ]
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get lineage statistics"""
        return {
            "total_nodes": len(self._nodes),
            "total_events": len(self._events),
            "by_type": {
                (nt.value if hasattr(nt, 'value') else str(nt)): len(nids)
                for nt, nids in self._by_type.items()
            },
            "avg_upstream_per_node": (
                sum(len(n.upstream) for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
            "avg_downstream_per_node": (
                sum(len(n.downstream) for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
        }
