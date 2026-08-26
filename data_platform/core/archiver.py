"""
Archiver

Automatic archiving of old datasets.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ArchiveStatus(Enum):
    """Archive status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPRESSED = "compressed"
    DELETED = "deleted"


class ArchiveRule:
    """Rule for automatic archiving"""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        dataset_pattern: str = "*",
        age_days: int = 90,
        compress: bool = True,
        move_to_cold: bool = False,
        delete_after_days: Optional[int] = None,
        priority: int = 0,
        enabled: bool = True,
    ):
        self.rule_id = rule_id
        self.name = name
        self.dataset_pattern = dataset_pattern
        self.age_days = age_days
        self.compress = compress
        self.move_to_cold = move_to_cold
        self.delete_after_days = delete_after_days
        self.priority = priority
        self.enabled = enabled
    
    def matches(self, dataset_name: str) -> bool:
        """Check if rule matches dataset"""
        import fnmatch
        return fnmatch.fnmatch(dataset_name, self.dataset_pattern)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "dataset_pattern": self.dataset_pattern,
            "age_days": self.age_days,
            "compress": self.compress,
            "move_to_cold": self.move_to_cold,
            "delete_after_days": self.delete_after_days,
            "priority": self.priority,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchiveRule":
        return cls(**data)


class ArchiveRecord:
    """Record of an archive operation"""
    
    def __init__(
        self,
        record_id: str,
        dataset_id: str,
        dataset_name: str,
        archived_at: datetime,
        archive_path: str,
        original_size: int,
        archived_size: int,
        rule_id: str,
        status: ArchiveStatus = ArchiveStatus.ARCHIVED,
        compressed: bool = False,
        deletion_scheduled: Optional[datetime] = None,
    ):
        self.record_id = record_id
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name
        self.archived_at = archived_at
        self.archive_path = archive_path
        self.original_size = original_size
        self.archived_size = archived_size
        self.rule_id = rule_id
        self.status = status
        self.compressed = compressed
        self.deletion_scheduled = deletion_scheduled
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "archived_at": self.archived_at.isoformat() if isinstance(self.archived_at, datetime) else self.archived_at,
            "archive_path": self.archive_path,
            "original_size": self.original_size,
            "archived_size": self.archived_size,
            "rule_id": self.rule_id,
            "status": self.status.value if isinstance(self.status, ArchiveStatus) else self.status,
            "compressed": self.compressed,
            "deletion_scheduled": (
                self.deletion_scheduled.isoformat() if isinstance(self.deletion_scheduled, datetime) else self.deletion_scheduled
            ),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchiveRecord":
        """Create from dictionary"""
        if isinstance(data.get("archived_at"), str):
            data["archived_at"] = datetime.fromisoformat(data["archived_at"])
        if isinstance(data.get("deletion_scheduled"), str):
            data["deletion_scheduled"] = datetime.fromisoformat(data["deletion_scheduled"])
        if isinstance(data.get("status"), str):
            data["status"] = ArchiveStatus(data["status"])
        return cls(**data)


class Archiver:
    """
    Archiver for automatic data archiving.
    
    Features:
    - Configurable archive rules
    - Automatic compression
    - Cold storage migration
    - Scheduled deletion
    - Archive retention policies
    """
    
    def __init__(
        self,
        storage_path: str = "data_platform/archives",
        cold_storage_path: str = "data_platform/cold_storage",
        default_age_days: int = 90,
    ):
        self._storage_path = storage_path
        self._cold_storage_path = cold_storage_path
        self._default_age_days = default_age_days
        
        # Archive rules
        self._rules: List[ArchiveRule] = []
        
        # Archive records
        self._records: Dict[str, ArchiveRecord] = {}  # dataset_id -> record
        
        os.makedirs(storage_path, exist_ok=True)
        os.makedirs(cold_storage_path, exist_ok=True)
        
        self._load_index()
    
    def _load_index(self) -> None:
        """Load archive index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                self._rules = [
                    ArchiveRule.from_dict(r) for r in data.get("rules", [])
                ]
                
                self._records = {
                    r["dataset_id"]: ArchiveRecord.from_dict(r)
                    for r in data.get("records", [])
                }
                
                logger.info(
                    f"Loaded {len(self._rules)} rules and "
                    f"{len(self._records)} archive records"
                )
            except Exception as e:
                logger.warning(f"Could not load archive index: {e}")
    
    def _save_index(self) -> None:
        """Save archive index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "rules": [r.to_dict() for r in self._rules],
            "records": [r.to_dict() for r in self._records.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def add_rule(
        self,
        name: str,
        dataset_pattern: str = "*",
        age_days: Optional[int] = None,
        compress: bool = True,
        move_to_cold: bool = False,
        delete_after_days: Optional[int] = None,
        priority: int = 0,
    ) -> ArchiveRule:
        """Add an archive rule"""
        import uuid
        
        rule = ArchiveRule(
            rule_id=str(uuid.uuid4()),
            name=name,
            dataset_pattern=dataset_pattern,
            age_days=age_days or self._default_age_days,
            compress=compress,
            move_to_cold=move_to_cold,
            delete_after_days=delete_after_days,
            priority=priority,
        )
        
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self._save_index()
        
        logger.info(f"Added archive rule: {name} ({rule.rule_id})")
        return rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an archive rule"""
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        self._save_index()
        return True
    
    def get_matching_rule(self, dataset_name: str) -> Optional[ArchiveRule]:
        """Get the highest priority matching rule for a dataset"""
        for rule in self._rules:
            if rule.enabled and rule.matches(dataset_name):
                return rule
        return None
    
    def archive_dataset(
        self,
        dataset_id: str,
        dataset_name: str,
        source_path: str,
        created_at: datetime,
        rule: Optional[ArchiveRule] = None,
    ) -> Optional[ArchiveRecord]:
        """Archive a dataset"""
        import uuid
        
        if rule is None:
            rule = self.get_matching_rule(dataset_name)
        
        if rule is None:
            logger.debug(f"No matching archive rule for {dataset_name}")
            return None
        
        # Check age
        age = datetime.utcnow() - created_at
        if age.days < rule.age_days:
            logger.debug(f"Dataset {dataset_name} not old enough ({age.days} < {rule.age_days})")
            return None
        
        # Determine archive location
        if rule.move_to_cold:
            archive_dir = self._cold_storage_path
        else:
            archive_dir = self._storage_path
        
        archive_name = f"{dataset_name}_{dataset_id[:8]}_{created_at.strftime('%Y%m%d')}"
        archive_path = f"{archive_dir}/{archive_name}"
        
        # Get original size
        original_size = 0
        if os.path.exists(source_path):
            if os.path.isfile(source_path):
                original_size = os.path.getsize(source_path)
            else:
                for root, dirs, files in os.walk(source_path):
                    for f in files:
                        original_size += os.path.getsize(os.path.join(root, f))
        
        # Copy to archive
        compressed = False
        archived_size = original_size
        
        os.makedirs(archive_path, exist_ok=True)
        
        if os.path.isfile(source_path):
            dest_file = f"{archive_path}/data"
            if rule.compress:
                dest_file += ".gz"
                try:
                    import gzip
                    with open(source_path, "rb") as f_in:
                        with gzip.open(dest_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    compressed = True
                    archived_size = os.path.getsize(dest_file)
                except Exception as e:
                    logger.warning(f"Compression failed: {e}, copying uncompressed")
                    shutil.copy2(source_path, archive_path + "/data")
            else:
                shutil.copy2(source_path, dest_file)
                archived_size = os.path.getsize(dest_file)
        else:
            if rule.compress:
                shutil.make_archive(archive_path, "gztar", source_path)
                compressed = True
                archived_size = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, dirs, files in os.walk(f"{archive_path}.tar.gz")
                    for f in files
                )
                shutil.rmtree(archive_path)
                archive_path = f"{archive_path}.tar.gz"
            else:
                shutil.copytree(source_path, archive_path, dirs_exist_ok=True)
        
        # Schedule deletion if configured
        deletion_scheduled = None
        if rule.delete_after_days:
            deletion_scheduled = created_at + timedelta(days=rule.delete_after_days)
        
        record = ArchiveRecord(
            record_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            archived_at=datetime.utcnow(),
            archive_path=archive_path,
            original_size=original_size,
            archived_size=archived_size,
            rule_id=rule.rule_id,
            status=ArchiveStatus.ARCHIVED,
            compressed=compressed,
            deletion_scheduled=deletion_scheduled,
        )
        
        self._records[dataset_id] = record
        self._save_index()
        
        logger.info(
            f"Archived dataset {dataset_name} "
            f"(original: {original_size}, archived: {archived_size}, "
            f"compression: {archived_size/original_size:.1%})"
        )
        
        return record
    
    def restore_dataset(
        self,
        dataset_id: str,
        restore_path: str,
    ) -> bool:
        """Restore an archived dataset"""
        record = self._records.get(dataset_id)
        if not record:
            logger.warning(f"No archive record for dataset {dataset_id}")
            return False
        
        archive_path = record.archive_path
        
        if not os.path.exists(archive_path):
            logger.error(f"Archive file not found: {archive_path}")
            return False
        
        try:
            os.makedirs(restore_path, exist_ok=True)
            
            if archive_path.endswith(".tar.gz"):
                shutil.extract_archive(archive_path, restore_path)
            elif archive_path.endswith(".gz"):
                import gzip
                output_path = restore_path + "/data"
                with gzip.open(archive_path, "rb") as f_in:
                    with open(output_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                if os.path.isdir(archive_path):
                    shutil.copytree(archive_path, restore_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(archive_path, restore_path)
            
            record.status = ArchiveStatus.ACTIVE
            self._save_index()
            
            logger.info(f"Restored dataset {dataset_id} to {restore_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring dataset: {e}")
            return False
    
    def get_archive_record(self, dataset_id: str) -> Optional[ArchiveRecord]:
        """Get archive record for a dataset"""
        return self._records.get(dataset_id)
    
    def get_candidates(self) -> List[Tuple[str, datetime, ArchiveRule]]:
        """Get datasets eligible for archiving"""
        candidates = []
        
        # This would need integration with DatasetRegistry
        # For now, return stored records that are candidates
        
        for record in self._records.values():
            if record.status == ArchiveStatus.ACTIVE:
                # Check if scheduled for deletion
                if record.deletion_scheduled and record.deletion_scheduled <= datetime.utcnow():
                    candidates.append((record.dataset_id, record.deletion_scheduled, None))
        
        return candidates
    
    def process_deletions(self) -> int:
        """Process scheduled deletions"""
        deleted = 0
        
        for dataset_id, record in list(self._records.items()):
            if record.deletion_scheduled and record.deletion_scheduled <= datetime.utcnow():
                try:
                    if os.path.exists(record.archive_path):
                        if os.path.isdir(record.archive_path):
                            shutil.rmtree(record.archive_path)
                        else:
                            os.remove(record.archive_path)
                    
                    record.status = ArchiveStatus.DELETED
                    deleted += 1
                    
                    logger.info(f"Deleted archived dataset: {record.dataset_name}")
                except Exception as e:
                    logger.error(f"Error deleting archive: {e}")
        
        if deleted:
            self._save_index()
        
        return deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get archiver statistics"""
        active = [r for r in self._records.values() if r.status == ArchiveStatus.ACTIVE]
        archived = [r for r in self._records.values() if r.status == ArchiveStatus.ARCHIVED]
        
        return {
            "total_rules": len(self._rules),
            "total_records": len(self._records),
            "active_archives": len(active),
            "archived_count": len(archived),
            "total_original_size": sum(r.original_size for r in self._records.values()),
            "total_archived_size": sum(r.archived_size for r in archived),
            "compression_ratio": (
                sum(r.archived_size for r in archived) / sum(r.original_size for r in archived)
                if archived else 1.0
            ),
            "scheduled_deletions": sum(
                1 for r in self._records.values()
                if r.deletion_scheduled and r.deletion_scheduled > datetime.utcnow()
            ),
        }
