"""
Version Management
=================

Version control and comparison for strategies.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .graph import StrategyGraph

logger = logging.getLogger(__name__)


@dataclass
class StrategyVersion:
    """A version of a strategy"""
    version_id: str
    strategy_id: str
    version_number: str  # e.g., "1.0.0"
    created_at: datetime
    author: str
    message: str
    graph_data: Dict[str, Any]
    hash: str
    parent_version_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "strategy_id": self.strategy_id,
            "version_number": self.version_number,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "message": self.message,
            "graph_data": self.graph_data,
            "hash": self.hash,
            "parent_version_id": self.parent_version_id,
            "tags": self.tags
        }


@dataclass
class VersionDiff:
    """Difference between two strategy versions"""
    from_version: str
    to_version: str
    blocks_added: List[Dict[str, Any]] = field(default_factory=list)
    blocks_removed: List[Dict[str, Any]] = field(default_factory=list)
    blocks_modified: List[Dict[str, Any]] = field(default_factory=list)
    edges_added: List[Dict[str, Any]] = field(default_factory=list)
    edges_removed: List[Dict[str, Any]] = field(default_factory=list)
    parameters_changed: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "blocks_added": self.blocks_added,
            "blocks_removed": self.blocks_removed,
            "blocks_modified": self.blocks_modified,
            "edges_added": self.edges_added,
            "edges_removed": self.edges_removed,
            "parameters_changed": self.parameters_changed
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        parts = []
        
        if self.blocks_added:
            parts.append(f"{len(self.blocks_added)} blocks added")
        if self.blocks_removed:
            parts.append(f"{len(self.blocks_removed)} blocks removed")
        if self.blocks_modified:
            parts.append(f"{len(self.blocks_modified)} blocks modified")
        if self.parameters_changed:
            parts.append(f"{len(self.parameters_changed)} parameter changes")
        
        return ", ".join(parts) if parts else "No changes"


class VersionManager:
    """
    Manages strategy versions and history.
    """
    
    def __init__(self, db_path: str = "data/strategy_builder/versions.json"):
        self.db_path = db_path
        self.versions: Dict[str, List[StrategyVersion]] = {}  # strategy_id -> versions
        self._load_versions()
    
    def _load_versions(self) -> None:
        """Load versions from file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    for strategy_id, versions_data in data.items():
                        self.versions[strategy_id] = [
                            StrategyVersion(
                                version_id=v["version_id"],
                                strategy_id=v["strategy_id"],
                                version_number=v["version_number"],
                                created_at=datetime.fromisoformat(v["created_at"]),
                                author=v["author"],
                                message=v["message"],
                                graph_data=v["graph_data"],
                                hash=v["hash"],
                                parent_version_id=v.get("parent_version_id"),
                                tags=v.get("tags", [])
                            )
                            for v in versions_data
                        ]
            except Exception as e:
                logger.error(f"Failed to load versions: {e}")
    
    def _save_versions(self) -> None:
        """Save versions to file"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        try:
            data = {
                strategy_id: [v.to_dict() for v in versions]
                for strategy_id, versions in self.versions.items()
            }
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save versions: {e}")
    
    def create_version(
        self,
        strategy_id: str,
        graph: StrategyGraph,
        version_number: str,
        author: str,
        message: str,
        tags: List[str] = None
    ) -> StrategyVersion:
        """Create a new version"""
        # Get parent version
        versions = self.versions.get(strategy_id, [])
        parent_id = versions[-1].version_id if versions else None
        
        version = StrategyVersion(
            version_id=str(uuid4()),
            strategy_id=strategy_id,
            version_number=version_number,
            created_at=datetime.now(),
            author=author,
            message=message,
            graph_data=graph.to_dict(),
            hash=graph.get_hash(),
            parent_version_id=parent_id,
            tags=tags or []
        )
        
        if strategy_id not in self.versions:
            self.versions[strategy_id] = []
        
        self.versions[strategy_id].append(version)
        self._save_versions()
        
        logger.info(f"Created version {version_number} for strategy {strategy_id}")
        
        return version
    
    def get_versions(self, strategy_id: str) -> List[StrategyVersion]:
        """Get all versions for a strategy"""
        return self.versions.get(strategy_id, [])
    
    def get_version(
        self,
        strategy_id: str,
        version_id: str = None,
        version_number: str = None
    ) -> Optional[StrategyVersion]:
        """Get a specific version"""
        versions = self.versions.get(strategy_id, [])
        
        if version_id:
            for v in versions:
                if v.version_id == version_id:
                    return v
        elif version_number:
            for v in versions:
                if v.version_number == version_number:
                    return v
        
        return None
    
    def restore_version(
        self,
        strategy_id: str,
        version_id: str
    ) -> Optional[StrategyGraph]:
        """Restore a strategy to a specific version"""
        version = self.get_version(strategy_id, version_id=version_id)
        
        if not version:
            return None
        
        return StrategyGraph.from_dict(version.graph_data)
    
    def compare_versions(
        self,
        strategy_id: str,
        from_version_id: str,
        to_version_id: str
    ) -> Optional[VersionDiff]:
        """Compare two versions"""
        from_version = self.get_version(strategy_id, version_id=from_version_id)
        to_version = self.get_version(strategy_id, version_id=to_version_id)
        
        if not from_version or not to_version:
            return None
        
        from_graph = StrategyGraph.from_dict(from_version.graph_data)
        to_graph = StrategyGraph.from_dict(to_version.graph_data)
        
        diff = VersionDiff(
            from_version=from_version.version_number,
            to_version=to_version.version_number
        )
        
        # Find added blocks
        from_block_ids = set(from_graph.nodes.keys())
        to_block_ids = set(to_graph.nodes.keys())
        
        added_ids = to_block_ids - from_block_ids
        removed_ids = from_block_ids - to_block_ids
        common_ids = from_block_ids & to_block_ids
        
        for node_id in added_ids:
            node = to_graph.nodes[node_id]
            diff.blocks_added.append({
                "node_id": node_id,
                "block": node.block.to_dict()
            })
        
        for node_id in removed_ids:
            node = from_graph.nodes[node_id]
            diff.blocks_removed.append({
                "node_id": node_id,
                "block": node.block.to_dict()
            })
        
        # Find modified blocks
        for node_id in common_ids:
            from_node = from_graph.nodes[node_id]
            to_node = to_graph.nodes[node_id]
            
            if from_node.block.get_hash() != to_node.block.get_hash():
                diff.blocks_modified.append({
                    "node_id": node_id,
                    "from": from_node.block.to_dict(),
                    "to": to_node.block.to_dict()
                })
        
        # Find added/removed edges
        from_edge_ids = set(from_graph.edges.keys())
        to_edge_ids = set(to_graph.edges.keys())
        
        for edge_id in to_edge_ids - from_edge_ids:
            edge = to_graph.edges[edge_id]
            diff.edges_added.append(edge.to_dict())
        
        for edge_id in from_edge_ids - to_edge_ids:
            edge = from_graph.edges[edge_id]
            diff.edges_removed.append(edge.to_dict())
        
        return diff
    
    def get_latest_version(self, strategy_id: str) -> Optional[StrategyVersion]:
        """Get the latest version"""
        versions = self.versions.get(strategy_id, [])
        return versions[-1] if versions else None
    
    def delete_version(
        self,
        strategy_id: str,
        version_id: str
    ) -> bool:
        """Delete a version"""
        versions = self.versions.get(strategy_id, [])
        
        for i, v in enumerate(versions):
            if v.version_id == version_id:
                versions.pop(i)
                self._save_versions()
                return True
        
        return False
    
    def tag_version(
        self,
        strategy_id: str,
        version_id: str,
        tag: str
    ) -> bool:
        """Tag a version"""
        version = self.get_version(strategy_id, version_id=version_id)
        
        if not version:
            return False
        
        if tag not in version.tags:
            version.tags.append(tag)
            self._save_versions()
        
        return True
    
    def get_versions_by_tag(
        self,
        strategy_id: str,
        tag: str
    ) -> List[StrategyVersion]:
        """Get versions with a specific tag"""
        versions = self.versions.get(strategy_id, [])
        return [v for v in versions if tag in v.tags]
    
    def get_statistics(self, strategy_id: str) -> Dict[str, Any]:
        """Get version statistics"""
        versions = self.versions.get(strategy_id, [])
        
        if not versions:
            return {"total_versions": 0}
        
        return {
            "total_versions": len(versions),
            "first_version": versions[0].version_number,
            "latest_version": versions[-1].version_number,
            "contributors": list(set(v.author for v in versions)),
            "tags": list(set(tag for v in versions for tag in v.tags))
        }
