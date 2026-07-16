"""
Snapshot Manager

Manages historical snapshots for point-in-time data recovery.
"""

import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Snapshot:
    """A point-in-time snapshot of data"""
    
    def __init__(
        self,
        snapshot_id: str,
        dataset_id: str,
        version: str,
        timestamp: datetime,
        storage_path: str,
        content_hash: str,
        size_bytes: int,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: str = "",
        description: str = "",
    ):
        self.snapshot_id = snapshot_id
        self.dataset_id = dataset_id
        self.version = version
        self.timestamp = timestamp
        self.storage_path = storage_path
        self.content_hash = content_hash
        self.size_bytes = size_bytes
        self.metadata = metadata or {}
        self.created_by = created_by
        self.description = description
        self.is_frozen = True  # Snapshots are always frozen
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "dataset_id": self.dataset_id,
            "version": self.version,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "storage_path": self.storage_path,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "description": self.description,
            "is_frozen": self.is_frozen,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """Create from dictionary"""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class SnapshotManager:
    """
    Snapshot Manager for point-in-time data recovery.
    
    Features:
    - Scheduled snapshot creation
    - Point-in-time recovery
    - Snapshot retention policies
    - Incremental snapshots
    - Snapshot metadata and search
    """
    
    def __init__(
        self,
        storage_path: str = "data_platform/snapshots",
        retention_days: int = 90,
    ):
        self._storage_path = storage_path
        self._retention_days = retention_days
        self._snapshots: Dict[str, List[Snapshot]] = {}  # dataset_id -> snapshots
        self._snapshot_index: Dict[str, Snapshot] = {}  # snapshot_id -> snapshot
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load snapshot index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                for ds_id, snapshots in data.get("snapshots", {}).items():
                    self._snapshots[ds_id] = [
                        Snapshot.from_dict(s) for s in snapshots
                    ]
                
                # Build index
                for snapshots in self._snapshots.values():
                    for snapshot in snapshots:
                        self._snapshot_index[snapshot.snapshot_id] = snapshot
                
                logger.info(
                    f"Loaded {len(self._snapshot_index)} snapshots "
                    f"for {len(self._snapshots)} datasets"
                )
            except Exception as e:
                logger.warning(f"Could not load snapshot index: {e}")
    
    def _save_index(self) -> None:
        """Save snapshot index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "snapshots": {
                ds_id: [s.to_dict() for s in snapshots]
                for ds_id, snapshots in self._snapshots.items()
            },
            "retention_days": self._retention_days,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create_snapshot(
        self,
        dataset_id: str,
        version: str,
        content: bytes,
        content_hash: str,
        created_by: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """Create a point-in-time snapshot"""
        snapshot_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Store content
        ds_path = f"{self._storage_path}/{dataset_id}"
        os.makedirs(ds_path, exist_ok=True)
        
        storage_path = f"{ds_path}/{snapshot_id}.snapshot"
        with open(storage_path, "wb") as f:
            f.write(content)
        
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            dataset_id=dataset_id,
            version=version,
            timestamp=timestamp,
            storage_path=storage_path,
            content_hash=content_hash,
            size_bytes=len(content),
            metadata=metadata or {},
            created_by=created_by,
            description=description,
        )
        
        if dataset_id not in self._snapshots:
            self._snapshots[dataset_id] = []
        self._snapshots[dataset_id].append(snapshot)
        self._snapshot_index[snapshot_id] = snapshot
        
        self._save_index()
        
        logger.info(
            f"Created snapshot {snapshot_id} for dataset {dataset_id} "
            f"at {timestamp.isoformat()}"
        )
        
        return snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get a snapshot by ID"""
        return self._snapshot_index.get(snapshot_id)
    
    def get_snapshot_content(self, snapshot_id: str) -> Optional[bytes]:
        """Get the content of a snapshot"""
        snapshot = self._snapshot_index.get(snapshot_id)
        if not snapshot:
            return None
        
        try:
            with open(snapshot.storage_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading snapshot content: {e}")
            return None
    
    def get_dataset_snapshots(
        self,
        dataset_id: str,
        include_expired: bool = False,
    ) -> List[Snapshot]:
        """Get all snapshots for a dataset"""
        snapshots = self._snapshots.get(dataset_id, [])
        
        if not include_expired:
            cutoff = datetime.utcnow() - timedelta(days=self._retention_days)
            snapshots = [s for s in snapshots if s.timestamp >= cutoff]
        
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)
    
    def get_snapshot_at(
        self,
        dataset_id: str,
        timestamp: datetime,
    ) -> Optional[Snapshot]:
        """Get the snapshot that was current at a specific time"""
        snapshots = self._snapshots.get(dataset_id, [])
        
        for snapshot in reversed(snapshots):
            if snapshot.timestamp <= timestamp:
                return snapshot
        
        return None
    
    def get_snapshot_nearest(
        self,
        dataset_id: str,
        timestamp: datetime,
        direction: str = "before",  # "before" or "after"
    ) -> Optional[Snapshot]:
        """Get the nearest snapshot to a timestamp"""
        snapshots = self._snapshots.get(dataset_id, [])
        
        if not snapshots:
            return None
        
        nearest = None
        min_diff = None
        
        for snapshot in snapshots:
            diff = abs((snapshot.timestamp - timestamp).total_seconds())
            if min_diff is None or diff < min_diff:
                if direction == "before" and snapshot.timestamp > timestamp:
                    continue
                if direction == "after" and snapshot.timestamp < timestamp:
                    continue
                min_diff = diff
                nearest = snapshot
        
        return nearest
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        snapshot = self._snapshot_index.pop(snapshot_id, None)
        if not snapshot:
            return False
        
        # Remove from dataset list
        if snapshot.dataset_id in self._snapshots:
            self._snapshots[snapshot.dataset_id] = [
                s for s in self._snapshots[snapshot.dataset_id]
                if s.snapshot_id != snapshot_id
            ]
        
        # Remove file
        try:
            if os.path.exists(snapshot.storage_path):
                os.remove(snapshot.storage_path)
        except Exception as e:
            logger.warning(f"Could not remove snapshot file: {e}")
        
        self._save_index()
        return True
    
    def cleanup_expired(self) -> int:
        """Delete expired snapshots based on retention policy"""
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)
        removed = 0
        
        for dataset_id, snapshots in list(self._snapshots.items()):
            for snapshot in list(snapshots):
                if snapshot.timestamp < cutoff:
                    self.delete_snapshot(snapshot.snapshot_id)
                    removed += 1
        
        if removed:
            logger.info(f"Cleaned up {removed} expired snapshots")
        
        return removed
    
    def create_scheduled_snapshot(
        self,
        dataset_id: str,
        version: str,
        content: bytes,
        content_hash: str,
        schedule_type: str = "daily",
        created_by: str = "scheduler",
    ) -> Optional[Snapshot]:
        """
        Create a snapshot based on a schedule.
        
        Prevents creating duplicate snapshots for the same time period.
        """
        now = datetime.utcnow()
        
        # Check for recent snapshot based on schedule
        if schedule_type == "hourly":
            cutoff = now - timedelta(hours=1)
        elif schedule_type == "daily":
            cutoff = now - timedelta(days=1)
        elif schedule_type == "weekly":
            cutoff = now - timedelta(weeks=1)
        elif schedule_type == "monthly":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        if cutoff:
            recent = self.get_snapshot_nearest(dataset_id, cutoff, direction="after")
            if recent:
                logger.debug(f"Recent snapshot exists, skipping creation")
                return None
        
        return self.create_snapshot(
            dataset_id=dataset_id,
            version=version,
            content=content,
            content_hash=content_hash,
            created_by=created_by,
            description=f"Scheduled {schedule_type} snapshot",
            metadata={"schedule_type": schedule_type},
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get snapshot statistics"""
        all_snapshots = list(self._snapshot_index.values())
        total_size = sum(s.size_bytes for s in all_snapshots)
        
        # Count by age
        now = datetime.utcnow()
        age_buckets = {
            "last_day": 0,
            "last_week": 0,
            "last_month": 0,
            "older": 0,
        }
        
        for s in all_snapshots:
            age = (now - s.timestamp).total_seconds()
            if age < 86400:  # 1 day
                age_buckets["last_day"] += 1
            elif age < 604800:  # 1 week
                age_buckets["last_week"] += 1
            elif age < 2592000:  # 1 month
                age_buckets["last_month"] += 1
            else:
                age_buckets["older"] += 1
        
        return {
            "total_snapshots": len(all_snapshots),
            "total_datasets": len(self._snapshots),
            "total_size_bytes": total_size,
            "avg_size_bytes": total_size / len(all_snapshots) if all_snapshots else 0,
            "by_age": age_buckets,
            "retention_days": self._retention_days,
        }
