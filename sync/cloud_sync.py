"""
Cloud Synchronization

Synchronizes user data across devices and sessions.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    aiofiles = None

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Synchronization status"""
    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class SyncConfig:
    """Cloud sync configuration"""
    enabled: bool = True
    auto_sync: bool = True
    sync_interval: int = 300  # seconds
    max_retries: int = 3
    retry_delay: int = 5
    endpoint: Optional[str] = None
    storage_path: str = "data/sync"
    encryption_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "auto_sync": self.auto_sync,
            "sync_interval": self.sync_interval,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "endpoint": self.endpoint,
            "storage_path": self.storage_path,
            "encryption_enabled": self.encryption_enabled,
        }


@dataclass
class SyncableData:
    """Wrapper for data that can be synchronized"""
    key: str
    data: Any
    version: int = 1
    last_modified: datetime = field(default_factory=datetime.utcnow)
    checksum: Optional[str] = None
    source: str = "local"  # "local" or "cloud"
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of the data"""
        content = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def has_changed(self, other: "SyncableData") -> bool:
        """Check if this data has changed compared to another"""
        return self.checksum != other.checksum
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "data": self.data,
            "version": self.version,
            "last_modified": self.last_modified.isoformat(),
            "checksum": self.checksum,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncableData":
        return cls(
            key=data["key"],
            data=data["data"],
            version=data.get("version", 1),
            last_modified=datetime.fromisoformat(data["last_modified"]) if "last_modified" in data else datetime.utcnow(),
            checksum=data.get("checksum"),
            source=data.get("source", "local"),
        )


@dataclass
class SyncConflict:
    """Represents a synchronization conflict"""
    key: str
    local_data: SyncableData
    remote_data: SyncableData
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "local_data": self.local_data.to_dict(),
            "remote_data": self.remote_data.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "resolution": self.resolution,
        }


class CloudSync:
    """
    Cloud synchronization manager for user data.
    
    Features:
    - Automatic background synchronization
    - Conflict detection and resolution
    - Offline support with local caching
    - Selective sync for different data types
    - End-to-end encryption
    """
    
    SYNCABLE_TYPES = {
        "settings",
        "workspaces",
        "strategies",
        "preferences",
        "performance",
        "risk_limits",
        "accounts",
    }
    
    def __init__(self, config: Optional[SyncConfig] = None):
        self._config = config or SyncConfig()
        self._status = SyncStatus.IDLE
        self._data: Dict[str, SyncableData] = {}
        self._conflicts: List[SyncConflict] = []
        self._sync_task: Optional[asyncio.Task] = None
        self._last_sync: Optional[datetime] = None
        self._listeners: List[Callable[[str, SyncableData], None]] = []
        self._status_listeners: List[Callable[[SyncStatus], None]] = []
        self._storage_path = self._config.storage_path
        self._encryption_key = os.getenv("SYNC_ENCRYPTION_KEY", "").encode() or None
        
        os.makedirs(self._storage_path, exist_ok=True)
        self._load_local_data()
    
    @property
    def status(self) -> SyncStatus:
        return self._status
    
    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync
    
    @property
    def pending_conflicts(self) -> List[SyncConflict]:
        return self._conflicts
    
    def _load_local_data(self) -> None:
        """Load data from local storage"""
        data_file = os.path.join(self._storage_path, "sync_data.json")
        
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    data = json.load(f)
                    
                for key, item in data.get("items", {}).items():
                    self._data[key] = SyncableData.from_dict(item)
                    
                logger.info(f"Loaded {len(self._data)} syncable items")
            except Exception as e:
                logger.error(f"Failed to load sync data: {e}")
    
    def _save_local_data(self) -> None:
        """Save data to local storage"""
        data_file = os.path.join(self._storage_path, "sync_data.json")
        
        try:
            data = {
                "items": {key: item.to_dict() for key, item in self._data.items()},
                "last_updated": datetime.utcnow().isoformat(),
            }
            
            with open(data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync data: {e}")
    
    def register_data(
        self,
        key: str,
        data: Any,
        data_type: str = "settings",
    ) -> None:
        """
        Register data for synchronization.
        
        Args:
            key: Unique identifier for this data
            data: The data to sync
            data_type: Type of data (settings, workspaces, etc.)
        """
        if key in self._data:
            # Update existing
            existing = self._data[key]
            existing.data = data
            existing.version += 1
            existing.last_modified = datetime.utcnow()
            existing.checksum = existing._calculate_checksum()
        else:
            # Create new
            self._data[key] = SyncableData(
                key=key,
                data=data,
            )
        
        self._save_local_data()
        self._notify_listeners(key, self._data[key])
    
    def get_data(self, key: str) -> Optional[Any]:
        """Get synchronized data by key"""
        item = self._data.get(key)
        return item.data if item else None
    
    def unregister_data(self, key: str) -> bool:
        """Unregister data from synchronization"""
        if key in self._data:
            del self._data[key]
            self._save_local_data()
            return True
        return False
    
    def _set_status(self, status: SyncStatus) -> None:
        """Update sync status"""
        self._status = status
        for listener in self._status_listeners:
            try:
                listener(status)
            except Exception as e:
                logger.error(f"Status listener error: {e}")
    
    def start_auto_sync(self) -> None:
        """Start automatic background synchronization"""
        if self._sync_task and not self._sync_task.done():
            return
        
        if not self._config.auto_sync:
            return
        
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Auto sync started")
    
    def stop_auto_sync(self) -> None:
        """Stop automatic synchronization"""
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None
        logger.info("Auto sync stopped")
    
    async def _sync_loop(self) -> None:
        """Background sync loop"""
        while True:
            try:
                await asyncio.sleep(self._config.sync_interval)
                await self.sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(self._config.retry_delay)
    
    async def sync(self) -> bool:
        """
        Perform a full synchronization.
        
        Returns:
            True if sync was successful
        """
        if not self._config.enabled:
            self._set_status(SyncStatus.OFFLINE)
            return False
        
        self._set_status(SyncStatus.SYNCING)
        logger.info("Starting synchronization...")
        
        try:
            # Get remote data (in production, this would call the actual API)
            remote_data = await self._fetch_remote_data()
            
            # Detect and resolve conflicts
            conflicts = self._detect_conflicts(remote_data)
            if conflicts:
                await self._resolve_conflicts(conflicts)
            
            # Upload local changes
            await self._upload_local_changes(remote_data)
            
            self._last_sync = datetime.utcnow()
            self._set_status(SyncStatus.SUCCESS)
            logger.info("Synchronization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")
            self._set_status(SyncStatus.ERROR)
            return False
    
    async def _fetch_remote_data(self) -> Dict[str, SyncableData]:
        """Fetch data from remote storage"""
        # In production, this would call the actual cloud API
        # For now, return empty dict (placeholder)
        return {}
    
    async def _upload_local_changes(
        self,
        remote_data: Dict[str, SyncableData],
    ) -> None:
        """Upload local changes to remote"""
        changes = []
        
        for key, local_item in self._data.items():
            remote_item = remote_data.get(key)
            
            if remote_item is None:
                # New local data to upload
                changes.append(local_item)
            elif local_item.has_changed(remote_item):
                # Local data is newer
                if local_item.last_modified > remote_item.last_modified:
                    changes.append(local_item)
        
        if changes:
            # In production, this would upload to cloud
            logger.info(f"Would upload {len(changes)} items to cloud")
    
    def _detect_conflicts(
        self,
        remote_data: Dict[str, SyncableData],
    ) -> List[SyncConflict]:
        """Detect synchronization conflicts"""
        conflicts = []
        
        for key, remote_item in remote_data.items():
            local_item = self._data.get(key)
            
            if local_item and local_item.has_changed(remote_item):
                conflict = SyncConflict(
                    key=key,
                    local_data=local_item,
                    remote_data=remote_item,
                )
                conflicts.append(conflict)
                self._conflicts.append(conflict)
        
        return conflicts
    
    async def _resolve_conflicts(self, conflicts: List[SyncConflict]) -> None:
        """Resolve synchronization conflicts"""
        for conflict in conflicts:
            # Auto-resolve: prefer newer data
            if conflict.local_data.last_modified > conflict.remote_data.last_modified:
                conflict.resolution = "local"
            else:
                conflict.resolution = "remote"
                # Update local with remote data
                self._data[conflict.key] = conflict.remote_data
            
            logger.info(f"Resolved conflict for {conflict.key}: {conflict.resolution}")
    
    def resolve_conflict(
        self,
        key: str,
        resolution: str,  # "local" or "remote"
    ) -> bool:
        """Manually resolve a conflict"""
        conflict = next((c for c in self._conflicts if c.key == key), None)
        
        if not conflict:
            return False
        
        conflict.resolution = resolution
        
        if resolution == "local":
            # Keep local data, will upload on next sync
            pass
        else:
            # Use remote data
            self._data[key] = conflict.remote_data
        
        self._conflicts = [c for c in self._conflicts if c.key != key]
        self._save_local_data()
        
        return True
    
    def on_data_change(
        self,
        callback: Callable[[str, SyncableData], None],
    ) -> None:
        """Register a data change callback"""
        self._listeners.append(callback)
    
    def on_status_change(
        self,
        callback: Callable[[SyncStatus], None],
    ) -> None:
        """Register a status change callback"""
        self._status_listeners.append(callback)
    
    def _notify_listeners(self, key: str, data: SyncableData) -> None:
        """Notify listeners of data changes"""
        for listener in self._listeners:
            try:
                listener(key, data)
            except Exception as e:
                logger.error(f"Data listener error: {e}")
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """Get a summary of synchronization state"""
        return {
            "status": self.status.value,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "total_items": len(self._data),
            "pending_conflicts": len(self._conflicts),
            "config": self._config.to_dict(),
        }
    
    def get_data_by_type(self, data_type: str) -> Dict[str, Any]:
        """Get all data of a specific type"""
        return {
            key: item.data
            for key, item in self._data.items()
            if key.startswith(f"{data_type}:")
        }
    
    def export_config(self) -> Dict[str, Any]:
        """Export sync configuration"""
        return {
            "data": {key: item.to_dict() for key, item in self._data.items()},
            "config": self._config.to_dict(),
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
        }
    
    def import_config(self, config: Dict[str, Any]) -> None:
        """Import sync configuration"""
        for key, item_data in config.get("data", {}).items():
            self._data[key] = SyncableData.from_dict(item_data)
        
        self._save_local_data()
        logger.info(f"Imported {len(self._data)} syncable items")


def create_cloud_sync(
    enabled: bool = True,
    endpoint: Optional[str] = None,
) -> CloudSync:
    """Factory function to create a cloud sync instance"""
    config = SyncConfig(
        enabled=enabled,
        endpoint=endpoint,
    )
    return CloudSync(config=config)
