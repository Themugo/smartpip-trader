"""
Strategy Library - Searchable Catalog

Searchable catalog with metadata, versioning, and import/export.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetadata:
    """Strategy metadata for catalog"""
    id: str
    name: str
    author: str
    version: str
    
    # Description
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Markets
    supported_markets: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    
    # Performance
    performance_summary: Dict[str, float] = field(default_factory=dict)
    
    # Validation
    validation_status: str = "untested"  # untested, testing, validated, production
    
    # Requirements
    required_plugins: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    is_public: bool = False
    rating: float = 0
    downloads: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "supported_markets": self.supported_markets,
            "timeframes": self.timeframes,
            "performance_summary": self.performance_summary,
            "validation_status": self.validation_status,
            "required_plugins": self.required_plugins,
            "parameters": self.parameters,
            "is_public": self.is_public,
            "rating": self.rating,
            "downloads": self.downloads,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StrategyLibrary:
    """
    Strategy Library for managing and sharing strategies.
    
    Features:
    - Searchable catalog
    - Metadata management
    - Version control
    - Import/export
    - Ratings and downloads
    - Tagging
    """
    
    def __init__(self, storage_path: str = "data/strategy_library"):
        self._storage_path = storage_path
        self._strategies: Dict[str, StrategyMetadata] = {}
        self._versions: Dict[str, List[Dict[str, Any]]] = {}  # strategy_id -> versions
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_library()
    
    def _load_library(self) -> None:
        """Load library from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            with open(index_file, "r") as f:
                data = json.load(f)
            
            for meta_data in data.get("strategies", []):
                meta_data["created_at"] = datetime.fromisoformat(meta_data["created_at"])
                meta_data["updated_at"] = datetime.fromisoformat(meta_data["updated_at"])
                
                meta = StrategyMetadata(**meta_data)
                self._strategies[meta.id] = meta
                
                # Load versions
                versions_file = f"{self._storage_path}/versions_{meta.id}.json"
                if os.path.exists(versions_file):
                    with open(versions_file, "r") as f:
                        self._versions[meta.id] = json.load(f)
            
            logger.info(f"Loaded {len(self._strategies)} strategies from library")
        except Exception as e:
            logger.warning(f"Could not load library: {e}")
    
    def _save_library(self) -> None:
        """Save library to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "strategies": [s.to_dict() for s in self._strategies.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_strategy(
        self,
        name: str,
        author: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        supported_markets: Optional[List[str]] = None,
    ) -> StrategyMetadata:
        """Register a new strategy in the library"""
        meta = StrategyMetadata(
            id=str(uuid.uuid4()),
            name=name,
            author=author,
            version="1.0.0",
            description=description,
            tags=tags or [],
            supported_markets=supported_markets or [],
        )
        
        self._strategies[meta.id] = meta
        self._versions[meta.id] = []
        self._save_library()
        
        return meta
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """Get a strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        author: Optional[str] = None,
        validation_status: Optional[str] = None,
        limit: int = 50,
    ) -> List[StrategyMetadata]:
        """Search strategies by various criteria"""
        results = list(self._strategies.values())
        
        if query:
            query_lower = query.lower()
            results = [
                s for s in results
                if query_lower in s.name.lower() or query_lower in s.description.lower()
            ]
        
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]
        
        if markets:
            results = [
                s for s in results
                if any(m in s.supported_markets for m in markets)
            ]
        
        if author:
            results = [s for s in results if author.lower() in s.author.lower()]
        
        if validation_status:
            results = [s for s in results if s.validation_status == validation_status]
        
        # Sort by rating and downloads
        results.sort(key=lambda s: (s.rating, s.downloads), reverse=True)
        
        return results[:limit]
    
    def update_strategy(
        self,
        strategy_id: str,
        updates: Dict[str, Any],
    ) -> Optional[StrategyMetadata]:
        """Update strategy metadata"""
        meta = self._strategies.get(strategy_id)
        if not meta:
            return None
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(meta, key):
                setattr(meta, key, value)
        
        meta.updated_at = datetime.utcnow()
        self._save_library()
        
        return meta
    
    def add_version(
        self,
        strategy_id: str,
        version: str,
        data: Dict[str, Any],
        changelog: str = "",
    ) -> bool:
        """Add a new version"""
        meta = self._strategies.get(strategy_id)
        if not meta:
            return False
        
        version_entry = {
            "version": version,
            "changelog": changelog,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if strategy_id not in self._versions:
            self._versions[strategy_id] = []
        
        self._versions[strategy_id].append(version_entry)
        meta.version = version
        
        # Save versions
        versions_file = f"{self._storage_path}/versions_{strategy_id}.json"
        with open(versions_file, "w") as f:
            json.dump(self._versions[strategy_id], f, indent=2)
        
        self._save_library()
        return True
    
    def get_versions(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a strategy"""
        return self._versions.get(strategy_id, [])
    
    def get_version(self, strategy_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Get a specific version"""
        versions = self._versions.get(strategy_id, [])
        for v in versions:
            if v["version"] == version:
                return v
        return None
    
    def export_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Export a strategy with all its versions"""
        meta = self._strategies.get(strategy_id)
        if not meta:
            return None
        
        return {
            "metadata": meta.to_dict(),
            "versions": self._versions.get(strategy_id, []),
        }
    
    def import_strategy(
        self,
        data: Dict[str, Any],
        new_id: Optional[str] = None,
    ) -> Optional[StrategyMetadata]:
        """Import a strategy from exported data"""
        try:
            meta_data = data["metadata"]
            versions = data.get("versions", [])
            
            # Generate new ID
            if new_id:
                meta_data["id"] = new_id
            else:
                meta_data["id"] = str(uuid.uuid4())
            
            meta_data["created_at"] = datetime.fromisoformat(meta_data["created_at"])
            meta_data["updated_at"] = datetime.utcnow()
            
            meta = StrategyMetadata(**meta_data)
            self._strategies[meta.id] = meta
            self._versions[meta.id] = versions
            
            self._save_library()
            
            return meta
        except Exception as e:
            logger.error(f"Failed to import strategy: {e}")
            return None
    
    def rate_strategy(self, strategy_id: str, rating: float) -> bool:
        """Rate a strategy (1-5 stars)"""
        meta = self._strategies.get(strategy_id)
        if not meta:
            return False
        
        meta.rating = (meta.rating * meta.downloads + rating) / (meta.downloads + 1)
        meta.downloads += 1
        meta.updated_at = datetime.utcnow()
        
        self._save_library()
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        strategies = list(self._strategies.values())
        
        return {
            "total_strategies": len(strategies),
            "public_strategies": sum(1 for s in strategies if s.is_public),
            "by_validation_status": {
                status: sum(1 for s in strategies if s.validation_status == status)
                for status in ["untested", "testing", "validated", "production"]
            },
            "total_downloads": sum(s.downloads for s in strategies),
            "avg_rating": sum(s.rating for s in strategies) / len(strategies) if strategies else 0,
        }
