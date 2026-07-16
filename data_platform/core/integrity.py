"""
Integrity Verifier

Automatic integrity verification for datasets.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntegrityStatus(Enum):
    """Integrity verification status"""
    PASSED = "passed"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    PENDING = "pending"
    UNKNOWN = "unknown"


class IntegrityCheck:
    """Record of an integrity check"""
    
    def __init__(
        self,
        check_id: str,
        dataset_id: str,
        timestamp: datetime,
        status: IntegrityStatus,
        hash_computed: str,
        hash_expected: str,
        details: Optional[Dict[str, Any]] = None,
        checked_by: str = "system",
    ):
        self.check_id = check_id
        self.dataset_id = dataset_id
        self.timestamp = timestamp
        self.status = status
        self.hash_computed = hash_computed
        self.hash_expected = hash_expected
        self.details = details or {}
        self.checked_by = checked_by
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "dataset_id": self.dataset_id,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "status": self.status.value if isinstance(self.status, IntegrityStatus) else self.status,
            "hash_computed": self.hash_computed,
            "hash_expected": self.hash_expected,
            "details": self.details,
            "checked_by": self.checked_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrityCheck":
        """Create from dictionary"""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("status"), str):
            data["status"] = IntegrityStatus(data["status"])
        return cls(**data)


class IntegrityVerifier:
    """
    Integrity Verifier for automatic data validation.
    
    Features:
    - Hash-based integrity verification
    - Scheduled integrity checks
    - Corruption detection
    - Integrity history
    - Automatic repair notifications
    """
    
    def __init__(
        self,
        storage_path: str = "data_platform/integrity",
        default_algorithm: str = "sha256",
        check_interval_hours: int = 24,
    ):
        self._storage_path = storage_path
        self._default_algorithm = default_algorithm
        self._check_interval = timedelta(hours=check_interval_hours)
        
        # Registered datasets with their expected hashes
        self._registered: Dict[str, Dict[str, str]] = {}  # dataset_id -> {algorithm -> hash}
        
        # Integrity check history
        self._check_history: Dict[str, List[IntegrityCheck]] = {}  # dataset_id -> checks
        
        # Pending checks
        self._pending_checks: Dict[str, datetime] = {}  # dataset_id -> last_check
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load integrity index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                self._registered = data.get("registered", {})
                
                # Load check history
                for ds_id, checks in data.get("check_history", {}).items():
                    self._check_history[ds_id] = [
                        IntegrityCheck.from_dict(c) for c in checks
                    ]
                
                self._pending_checks = {
                    k: datetime.fromisoformat(v) if isinstance(v, str) else v
                    for k, v in data.get("pending_checks", {}).items()
                }
                
                logger.info(f"Loaded integrity data for {len(self._registered)} datasets")
            except Exception as e:
                logger.warning(f"Could not load integrity index: {e}")
    
    def _save_index(self) -> None:
        """Save integrity index"""
        os.makedirs(self._storage_path, exist_ok=True)
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "registered": self._registered,
            "check_history": {
                ds_id: [c.to_dict() for c in checks]
                for ds_id, checks in self._check_history.items()
            },
            "pending_checks": {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self._pending_checks.items()
            },
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def register(
        self,
        dataset_id: str,
        content: bytes,
        algorithm: Optional[str] = None,
    ) -> str:
        """Register a dataset with its integrity hash"""
        algorithm = algorithm or self._default_algorithm
        hash_value = self._compute_hash(content, algorithm)
        
        if dataset_id not in self._registered:
            self._registered[dataset_id] = {}
        
        self._registered[dataset_id][algorithm] = hash_value
        self._pending_checks[dataset_id] = datetime.utcnow()
        
        self._save_index()
        
        logger.info(f"Registered dataset {dataset_id} with {algorithm} hash: {hash_value[:16]}...")
        return hash_value
    
    def update_hash(
        self,
        dataset_id: str,
        content: bytes,
        algorithm: Optional[str] = None,
    ) -> str:
        """Update the integrity hash for a dataset"""
        algorithm = algorithm or self._default_algorithm
        hash_value = self._compute_hash(content, algorithm)
        
        if dataset_id not in self._registered:
            self._registered[dataset_id] = {}
        
        self._registered[dataset_id][algorithm] = hash_value
        self._pending_checks[dataset_id] = datetime.utcnow()
        
        self._save_index()
        
        return hash_value
    
    def _compute_hash(self, content: bytes, algorithm: str) -> str:
        """Compute hash of content"""
        if algorithm == "sha256":
            return hashlib.sha256(content).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(content).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(content).hexdigest()
        elif algorithm == "blake2b":
            return hashlib.blake2b(content).hexdigest()
        elif algorithm == "blake2s":
            return hashlib.blake2s(content).hexdigest()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    def verify(
        self,
        dataset_id: str,
        content: bytes,
        algorithm: Optional[str] = None,
        checked_by: str = "system",
    ) -> IntegrityCheck:
        """Verify integrity of a dataset"""
        import uuid
        
        algorithm = algorithm or self._default_algorithm
        computed_hash = self._compute_hash(content, algorithm)
        
        expected_hash = self._registered.get(dataset_id, {}).get(algorithm)
        
        if expected_hash is None:
            status = IntegrityStatus.UNKNOWN
        elif computed_hash == expected_hash:
            status = IntegrityStatus.PASSED
        else:
            status = IntegrityStatus.FAILED
        
        check = IntegrityCheck(
            check_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            timestamp=datetime.utcnow(),
            status=status,
            hash_computed=computed_hash,
            hash_expected=expected_hash or "",
            details={
                "algorithm": algorithm,
                "content_size": len(content),
            },
            checked_by=checked_by,
        )
        
        # Record check
        if dataset_id not in self._check_history:
            self._check_history[dataset_id] = []
        self._check_history[dataset_id].append(check)
        
        # Keep only recent history
        if len(self._check_history[dataset_id]) > 100:
            self._check_history[dataset_id] = self._check_history[dataset_id][-100:]
        
        self._pending_checks[dataset_id] = datetime.utcnow()
        self._save_index()
        
        if status == IntegrityStatus.PASSED:
            logger.info(f"Integrity check passed for {dataset_id}")
        else:
            logger.warning(f"Integrity check {status.value} for {dataset_id}")
        
        return check
    
    def verify_file(
        self,
        dataset_id: str,
        file_path: str,
        algorithm: Optional[str] = None,
    ) -> IntegrityCheck:
        """Verify integrity of a file"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return self.verify(dataset_id, content, algorithm)
        except Exception as e:
            logger.error(f"Error verifying file {file_path}: {e}")
            return IntegrityCheck(
                check_id="",
                dataset_id=dataset_id,
                timestamp=datetime.utcnow(),
                status=IntegrityStatus.MISSING,
                hash_computed="",
                hash_expected="",
                details={"error": str(e), "file_path": file_path},
            )
    
    def get_status(
        self,
        dataset_id: str,
        algorithm: Optional[str] = None,
    ) -> IntegrityStatus:
        """Get current integrity status of a dataset"""
        history = self._check_history.get(dataset_id, [])
        if not history:
            if dataset_id in self._registered:
                return IntegrityStatus.PENDING
            return IntegrityStatus.UNKNOWN
        
        latest = history[-1]
        return latest.status
    
    def get_check_history(
        self,
        dataset_id: str,
        limit: int = 100,
    ) -> List[IntegrityCheck]:
        """Get check history for a dataset"""
        history = self._check_history.get(dataset_id, [])
        return history[-limit:]
    
    def get_pending_checks(self) -> List[Tuple[str, datetime]]:
        """Get datasets that need integrity checks"""
        now = datetime.utcnow()
        pending = []
        
        for dataset_id, last_check in self._pending_checks.items():
            if now - last_check >= self._check_interval:
                pending.append((dataset_id, last_check))
        
        return sorted(pending, key=lambda x: x[1])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integrity statistics"""
        total_datasets = len(self._registered)
        total_checks = sum(len(checks) for checks in self._check_history.values())
        
        status_counts = {
            "passed": 0,
            "failed": 0,
            "corrupted": 0,
            "pending": 0,
            "unknown": 0,
        }
        
        for ds_id in self._registered:
            status = self.get_status(ds_id)
            status_counts[status.value] = status_counts.get(status.value, 0) + 1
        
        return {
            "total_registered": total_datasets,
            "total_checks": total_checks,
            "check_interval_hours": self._check_interval.total_seconds() / 3600,
            "by_status": status_counts,
            "pending_checks": len(self.get_pending_checks()),
        }
    
    def generate_manifest(
        self,
        dataset_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate integrity manifest for datasets"""
        if dataset_ids is None:
            dataset_ids = list(self._registered.keys())
        
        manifest = {
            "generated_at": datetime.utcnow().isoformat(),
            "datasets": {},
        }
        
        for ds_id in dataset_ids:
            if ds_id in self._registered:
                manifest["datasets"][ds_id] = {
                    "hashes": self._registered[ds_id],
                    "status": self.get_status(ds_id).value,
                    "last_check": (
                        self._check_history.get(ds_id, [])[-1].timestamp.isoformat()
                        if self._check_history.get(ds_id) else None
                    ),
                }
        
        return manifest
    
    def export_manifest(
        self,
        output_path: str,
        dataset_ids: Optional[List[str]] = None,
    ) -> str:
        """Export integrity manifest to file"""
        manifest = self.generate_manifest(dataset_ids)
        
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Exported integrity manifest to {output_path}")
        return output_path
    
    def import_manifest(
        self,
        manifest_path: str,
    ) -> Dict[str, Any]:
        """Import integrity manifest"""
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        for ds_id, data in manifest.get("datasets", {}).items():
            if "hashes" in data:
                if ds_id not in self._registered:
                    self._registered[ds_id] = {}
                self._registered[ds_id].update(data["hashes"])
        
        self._save_index()
        
        return {
            "imported": len(manifest.get("datasets", {})),
            "datasets": list(manifest.get("datasets", {}).keys()),
        }
