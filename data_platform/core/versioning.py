"""
Data Versioning Manager

Manages version control for datasets with immutable references.
"""

import hashlib
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataVersion:
    """A versioned snapshot of data"""
    
    def __init__(
        self,
        version_id: str,
        dataset_id: str,
        version: str,
        content_hash: str,
        storage_path: str,
        created_at: datetime = None,
        created_by: str = "",
        change_summary: str = "",
        parent_version_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        self.version_id = version_id
        self.dataset_id = dataset_id
        self.version = version
        self.content_hash = content_hash
        self.storage_path = storage_path
        self.created_at = created_at or datetime.utcnow()
        self.created_by = created_by
        self.change_summary = change_summary
        self.parent_version_id = parent_version_id
        self.tags = tags or []
        self.is_frozen = False
        self.is_immutable = True  # All versions are immutable
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "dataset_id": self.dataset_id,
            "version": self.version,
            "content_hash": self.content_hash,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "created_by": self.created_by,
            "change_summary": self.change_summary,
            "parent_version_id": self.parent_version_id,
            "tags": self.tags,
            "is_frozen": self.is_frozen,
            "is_immutable": self.is_immutable,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataVersion":
        """Create from dictionary"""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class DataVersioningManager:
    """
    Data Versioning Manager for immutable dataset versioning.
    
    Features:
    - Immutable version references
    - Content-addressable storage
    - Version lineage tracking
    - Diff-based storage (optional)
    - Reproducible experiments through immutable versions
    """
    
    def __init__(
        self,
        storage_path: str = "data_platform/versions",
        use_content_addressing: bool = True,
    ):
        self._storage_path = storage_path
        self._use_content_addressing = use_content_addressing
        
        # Version storage by dataset
        self._dataset_versions: Dict[str, List[DataVersion]] = {}
        
        # Content-addressable storage
        self._content_store: Dict[str, str] = {}  # hash -> path
        
        # Index
        self._version_index: Dict[str, DataVersion] = {}  # version_id -> version
        
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(f"{storage_path}/content", exist_ok=True)
        
        self._load_index()
    
    def _load_index(self) -> None:
        """Load version index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                # Load versions
                for ds_id, versions in data.get("dataset_versions", {}).items():
                    self._dataset_versions[ds_id] = [
                        DataVersion.from_dict(v) for v in versions
                    ]
                
                # Load content store
                self._content_store = data.get("content_store", {})
                
                # Build version index
                for versions in self._dataset_versions.values():
                    for version in versions:
                        self._version_index[version.version_id] = version
                
                logger.info(
                    f"Loaded {len(self._version_index)} versions "
                    f"for {len(self._dataset_versions)} datasets"
                )
            except Exception as e:
                logger.warning(f"Could not load version index: {e}")
    
    def _save_index(self) -> None:
        """Save version index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "dataset_versions": {
                ds_id: [v.to_dict() for v in versions]
                for ds_id, versions in self._dataset_versions.items()
            },
            "content_store": self._content_store,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute content hash"""
        return hashlib.sha256(content).hexdigest()
    
    def _store_content(self, content: bytes) -> str:
        """Store content in content-addressable storage"""
        content_hash = self._compute_hash(content)
        
        if content_hash not in self._content_store:
            # Store content
            content_path = f"{self._storage_path}/content/{content_hash}"
            with open(content_path, "wb") as f:
                f.write(content)
            self._content_store[content_hash] = content_path
        
        return content_hash
    
    def create_version(
        self,
        dataset_id: str,
        content: bytes,
        version: str,
        created_by: str = "",
        change_summary: str = "",
        tags: Optional[List[str]] = None,
    ) -> DataVersion:
        """
        Create a new immutable version of a dataset.
        
        Returns:
            The created DataVersion
        """
        # Store content
        content_hash = self._store_content(content)
        
        # Get parent version
        parent_version_id = None
        if dataset_id in self._dataset_versions:
            versions = self._dataset_versions[dataset_id]
            if versions:
                parent_version_id = versions[-1].version_id
        
        # Create version
        version_id = str(uuid.uuid4())
        
        version_obj = DataVersion(
            version_id=version_id,
            dataset_id=dataset_id,
            version=version,
            content_hash=content_hash,
            storage_path=self._content_store[content_hash],
            created_by=created_by,
            change_summary=change_summary,
            parent_version_id=parent_version_id,
            tags=tags,
        )
        
        # Store version
        if dataset_id not in self._dataset_versions:
            self._dataset_versions[dataset_id] = []
        self._dataset_versions[dataset_id].append(version_obj)
        
        self._version_index[version_id] = version_obj
        self._save_index()
        
        logger.info(
            f"Created version {version} for dataset {dataset_id} "
            f"(hash: {content_hash[:16]}...)"
        )
        
        return version_obj
    
    def get_version(self, version_id: str) -> Optional[DataVersion]:
        """Get a version by ID"""
        return self._version_index.get(version_id)
    
    def get_dataset_versions(
        self,
        dataset_id: str,
        include_frozen: bool = True,
    ) -> List[DataVersion]:
        """Get all versions for a dataset"""
        versions = self._dataset_versions.get(dataset_id, [])
        if not include_frozen:
            versions = [v for v in versions if not v.is_frozen]
        return versions
    
    def get_current_version(self, dataset_id: str) -> Optional[DataVersion]:
        """Get the current (latest) version of a dataset"""
        versions = self._dataset_versions.get(dataset_id, [])
        return versions[-1] if versions else None
    
    def get_version_at(
        self,
        dataset_id: str,
        timestamp: datetime,
    ) -> Optional[DataVersion]:
        """Get the version that was current at a specific time"""
        versions = self._dataset_versions.get(dataset_id, [])
        
        for version in reversed(versions):
            if version.created_at <= timestamp:
                return version
        
        return None
    
    def get_version_content(self, version_id: str) -> Optional[bytes]:
        """Get the content of a version"""
        version = self._version_index.get(version_id)
        if not version:
            return None
        
        try:
            with open(version.storage_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading version content: {e}")
            return None
    
    def get_version_lineage(
        self,
        dataset_id: str,
        version_id: str,
    ) -> List[DataVersion]:
        """Get the full lineage of a version"""
        lineage = []
        current_id = version_id
        
        while current_id:
            version = self._version_index.get(current_id)
            if not version:
                break
            lineage.append(version)
            current_id = version.parent_version_id
        
        return list(reversed(lineage))
    
    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str,
    ) -> Dict[str, Any]:
        """Compare two versions"""
        v1 = self._version_index.get(version_id_1)
        v2 = self._version_index.get(version_id_2)
        
        if not v1 or not v2:
            return {"error": "Version not found"}
        
        # Get content
        content1 = self.get_version_content(version_id_1)
        content2 = self.get_version_content(version_id_2)
        
        return {
            "version_1": v1.to_dict(),
            "version_2": v2.to_dict(),
            "content_equal": content1 == content2,
            "size_diff": len(content2 or b"") - len(content1 or b""),
            "time_diff_seconds": (
                (v2.created_at - v1.created_at).total_seconds()
                if v1.created_at and v2.created_at else None
            ),
        }
    
    def rollback_to_version(
        self,
        dataset_id: str,
        version_id: str,
    ) -> Optional[DataVersion]:
        """
        Create a new version that rolls back to a previous state.
        
        Note: Original versions are never deleted - we create a new version
        that restores the old content.
        """
        target_version = self._version_index.get(version_id)
        if not target_version:
            return None
        
        # Get current version number
        current_versions = self._dataset_versions.get(dataset_id, [])
        current_version = current_versions[-1] if current_versions else None
        
        # Create new version with target's content
        return self.create_version(
            dataset_id=dataset_id,
            content=self.get_version_content(version_id) or b"",
            version=f"{target_version.version}.rollback",
            created_by="system",
            change_summary=f"Rollback to version {target_version.version}",
            tags=["rollback", f"rolled_back_from_{current_version.version}" if current_version else ""],
        )
    
    def tag_version(
        self,
        version_id: str,
        tag: str,
    ) -> bool:
        """Add a tag to a version"""
        version = self._version_index.get(version_id)
        if not version:
            return False
        
        if tag not in version.tags:
            version.tags.append(tag)
            self._save_index()
        
        return True
    
    def freeze_version(self, version_id: str) -> bool:
        """Freeze a version to prevent any modifications"""
        version = self._version_index.get(version_id)
        if not version:
            return False
        
        version.is_frozen = True
        self._save_index()
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get versioning statistics"""
        total_versions = sum(len(v) for v in self._dataset_versions.values())
        total_content_size = sum(
            os.path.getsize(self._content_store.get(h, ""))
            for h in self._content_store
            if os.path.exists(self._content_store.get(h, ""))
        )
        
        return {
            "total_datasets": len(self._dataset_versions),
            "total_versions": total_versions,
            "total_content_store_size": total_content_size,
            "unique_content_items": len(self._content_store),
            "average_versions_per_dataset": (
                total_versions / len(self._dataset_versions)
                if self._dataset_versions else 0
            ),
        }
    
    def cleanup_unreferenced(self) -> int:
        """Remove unreferenced content from content store"""
        referenced_hashes = set()
        
        for version in self._version_index.values():
            referenced_hashes.add(version.content_hash)
        
        removed = 0
        for content_hash, path in list(self._content_store.items()):
            if content_hash not in referenced_hashes:
                try:
                    os.remove(path)
                    del self._content_store[content_hash]
                    removed += 1
                except Exception as e:
                    logger.warning(f"Could not remove unreferenced content: {e}")
        
        if removed:
            self._save_index()
        
        return removed
