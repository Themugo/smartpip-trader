from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncRecord:
    key: str
    local_hash: str
    remote_hash: str = ""
    last_push: str = ""
    last_pull: str = ""
    conflict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "local_hash": self.local_hash,
            "remote_hash": self.remote_hash,
            "last_push": self.last_push,
            "last_pull": self.last_pull,
            "conflict": self.conflict,
        }


@dataclass
class SyncStatus:
    connected: bool = False
    last_sync: str = ""
    pending_push: int = 0
    pending_pull: int = 0
    conflicts: int = 0
    total_synced: int = 0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "last_sync": self.last_sync,
            "pending_push": self.pending_push,
            "pending_pull": self.pending_pull,
            "conflicts": self.conflicts,
            "total_synced": self.total_synced,
            "error_message": self.error_message,
        }


class CloudSync:
    """Local-first cloud sync for user preferences, settings, and strategy configs."""

    def __init__(self, local_dir: str = "cloud_sync_data", remote_endpoint: str = "") -> None:
        self._local_dir = Path(local_dir)
        self._local_dir.mkdir(parents=True, exist_ok=True)
        self._remote_endpoint = remote_endpoint
        self._records: Dict[str, SyncRecord] = {}
        self._status = SyncStatus()
        self._local_store: Dict[str, Any] = {}
        self._load_local()
        logger.info("CloudSync initialized (local=%s, remote=%s)", local_dir, remote_endpoint or "none")

    def _load_local(self) -> None:
        index_path = self._local_dir / "_sync_index.json"
        if index_path.exists():
            try:
                raw = json.loads(index_path.read_text(encoding="utf-8"))
                for key, rec in raw.get("records", {}).items():
                    self._records[key] = SyncRecord(**rec)
                self._local_store = raw.get("store", {})
            except Exception:
                logger.exception("Failed to load sync index")

    def _save_local(self) -> None:
        data = {
            "records": {k: r.to_dict() for k, r in self._records.items()},
            "store": self._local_store,
        }
        (self._local_dir / "_sync_index.json").write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    def _hash_data(self, data: Any) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def push_preferences(self, preferences: Dict[str, Any]) -> bool:
        key = "user_preferences"
        data_hash = self._hash_data(preferences)
        self._local_store[key] = preferences
        record = self._records.get(key, SyncRecord(key=key, local_hash=""))
        record.local_hash = data_hash
        record.last_push = self._timestamp()
        if record.remote_hash and record.remote_hash != data_hash:
            record.conflict = True
            self._status.conflicts += 1
        self._records[key] = record
        self._status.pending_push += 1
        self._save_local()
        logger.info("Preferences pushed locally (hash=%s)", data_hash[:12])
        return True

    def pull_preferences(self) -> Optional[Dict[str, Any]]:
        key = "user_preferences"
        data = self._local_store.get(key)
        if data:
            record = self._records.get(key)
            if record:
                record.last_pull = self._timestamp()
                self._records[key] = record
            self._status.pending_pull = max(0, self._status.pending_pull - 1)
            self._save_local()
            logger.info("Preferences pulled")
        return data

    def sync_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        key = "platform_settings"
        data_hash = self._hash_data(settings)
        old_data = self._local_store.get(key, {})
        self._local_store[key] = settings
        record = self._records.get(key, SyncRecord(key=key, local_hash=""))
        record.local_hash = data_hash
        record.last_push = self._timestamp()
        record.last_pull = self._timestamp()
        self._records[key] = record
        self._status.total_synced += 1
        self._status.last_sync = self._timestamp()
        self._save_local()
        logger.info("Settings synced (hash=%s)", data_hash[:12])
        return {"synced": True, "hash": data_hash, "previous": old_data}

    def push_strategy_config(self, strategy_id: str, config: Dict[str, Any]) -> bool:
        key = f"strategy_{strategy_id}"
        data_hash = self._hash_data(config)
        self._local_store[key] = config
        record = self._records.get(key, SyncRecord(key=key, local_hash=""))
        record.local_hash = data_hash
        record.last_push = self._timestamp()
        self._records[key] = record
        self._status.total_synced += 1
        self._save_local()
        logger.info("Strategy config pushed: %s", strategy_id)
        return True

    def pull_strategy_config(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        key = f"strategy_{strategy_id}"
        return self._local_store.get(key)

    def get_sync_status(self) -> SyncStatus:
        self._status.pending_push = sum(
            1 for r in self._records.values()
            if r.last_push > r.last_pull and not r.conflict
        )
        self._status.pending_pull = sum(
            1 for r in self._records.values()
            if r.last_pull < r.last_push
        )
        return self._status

    def resolve_conflict(self, key: str, use_local: bool = True) -> bool:
        record = self._records.get(key)
        if not record or not record.conflict:
            return False
        record.conflict = False
        if use_local:
            record.remote_hash = record.local_hash
        else:
            record.local_hash = record.remote_hash
        self._records[key] = record
        self._status.conflicts = max(0, self._status.conflicts - 1)
        self._save_local()
        logger.info("Conflict resolved for %s (use_local=%s)", key, use_local)
        return True

    def get_all_records(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records.values()]

    def get_pending_keys(self) -> List[str]:
        return [k for k, r in self._records.items() if r.local_hash != r.remote_hash]

    def clear_local(self) -> int:
        count = len(self._local_store)
        self._local_store.clear()
        self._records.clear()
        self._save_local()
        logger.info("Local sync data cleared (%d entries)", count)
        return count

    def export_all(self) -> Dict[str, Any]:
        return {
            "store": dict(self._local_store),
            "records": {k: r.to_dict() for k, r in self._records.items()},
            "status": self.get_sync_status().to_dict(),
        }

    def import_all(self, data: Dict[str, Any]) -> bool:
        try:
            self._local_store.update(data.get("store", {}))
            for key, rec in data.get("records", {}).items():
                self._records[key] = SyncRecord(**rec)
            self._save_local()
            logger.info("Sync data imported successfully")
            return True
        except Exception:
            logger.exception("Sync import failed")
            return False
