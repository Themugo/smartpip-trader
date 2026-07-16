"""
Data Quarantine
==============

Automated data quarantine management.
"""

import time
import shutil
import os
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

from .core import QuarantineStatus, DataIssue

logger = logging.getLogger(__name__)


class DataQuarantine:
    """
    Manages data quarantine for corrupted or low-quality datasets.
    """
    
    def __init__(
        self,
        quarantine_dir: str = "./data/quarantine",
        original_dir: str = "./data/raw"
    ):
        self.quarantine_dir = quarantine_dir
        self.original_dir = original_dir
        self._ensure_dirs()
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
    
    def _ensure_dirs(self) -> None:
        """Ensure quarantine directories exist"""
        os.makedirs(self.quarantine_dir, exist_ok=True)
        os.makedirs(self.original_dir, exist_ok=True)
    
    def _load_registry(self) -> None:
        """Load quarantine registry"""
        registry_file = os.path.join(self.quarantine_dir, "registry.json")
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r") as f:
                    self._registry = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load quarantine registry: {e}")
    
    def _save_registry(self) -> None:
        """Save quarantine registry"""
        registry_file = os.path.join(self.quarantine_dir, "registry.json")
        try:
            with open(registry_file, "w") as f:
                json.dump(self._registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quarantine registry: {e}")
    
    def quarantine(
        self,
        dataset_id: str,
        file_path: str,
        reason: str,
        issues: List[DataIssue]
    ) -> bool:
        """
        Quarantine a dataset.
        
        Moves the dataset to quarantine and records the reason.
        """
        if not os.path.exists(file_path):
            logger.warning(f"Dataset file not found: {file_path}")
            return False
        
        # Generate quarantine path
        filename = os.path.basename(file_path)
        quarantine_path = os.path.join(
            self.quarantine_dir,
            f"{dataset_id}_{filename}"
        )
        
        try:
            # Move file to quarantine
            shutil.move(file_path, quarantine_path)
            
            # Update registry
            self._registry[dataset_id] = {
                "original_path": file_path,
                "quarantine_path": quarantine_path,
                "quarantined_at": time.time(),
                "reason": reason,
                "status": QuarantineStatus.QUARANTINED.value,
                "issues": [i.to_dict() for i in issues],
                "restored_at": None,
                "restored_to": None,
            }
            
            self._save_registry()
            logger.info(f"Quarantined dataset: {dataset_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to quarantine {dataset_id}: {e}")
            return False
    
    def restore(
        self,
        dataset_id: str,
        restored_to: Optional[str] = None
    ) -> bool:
        """
        Restore a quarantined dataset.
        
        Moves the dataset back to its original location or a new location.
        """
        if dataset_id not in self._registry:
            logger.warning(f"Dataset not in quarantine: {dataset_id}")
            return False
        
        entry = self._registry[dataset_id]
        
        if entry["status"] != QuarantineStatus.QUARANTINED.value:
            logger.warning(f"Dataset not in quarantine status: {dataset_id}")
            return False
        
        try:
            # Determine destination
            if restored_to:
                dest_path = restored_to
            else:
                dest_path = entry["original_path"]
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Move file back
            shutil.move(entry["quarantine_path"], dest_path)
            
            # Update registry
            entry["status"] = QuarantineStatus.RESTORED.value
            entry["restored_at"] = time.time()
            entry["restored_to"] = dest_path
            
            self._save_registry()
            logger.info(f"Restored dataset: {dataset_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore {dataset_id}: {e}")
            return False
    
    def mark_under_review(self, dataset_id: str) -> bool:
        """Mark a dataset as under review"""
        if dataset_id not in self._registry:
            return False
        
        self._registry[dataset_id]["status"] = QuarantineStatus.UNDER_REVIEW.value
        self._save_registry()
        return True
    
    def get_status(self, dataset_id: str) -> Optional[QuarantineStatus]:
        """Get quarantine status"""
        if dataset_id not in self._registry:
            return None
        
        return QuarantineStatus(self._registry[dataset_id]["status"])
    
    def get_entry(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get quarantine entry"""
        return self._registry.get(dataset_id)
    
    def get_quarantined(self) -> List[Dict[str, Any]]:
        """Get all quarantined datasets"""
        return [
            entry for entry in self._registry.values()
            if entry["status"] == QuarantineStatus.QUARANTINED.value
        ]
    
    def get_under_review(self) -> List[Dict[str, Any]]:
        """Get all datasets under review"""
        return [
            entry for entry in self._registry.values()
            if entry["status"] == QuarantineStatus.UNDER_REVIEW.value
        ]
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all quarantine entries"""
        return self._registry.copy()
    
    def delete(self, dataset_id: str) -> bool:
        """Delete a quarantined dataset permanently"""
        if dataset_id not in self._registry:
            return False
        
        entry = self._registry[dataset_id]
        
        try:
            # Delete quarantine file if exists
            if os.path.exists(entry["quarantine_path"]):
                os.remove(entry["quarantine_path"])
            
            # Remove from registry
            del self._registry[dataset_id]
            self._save_registry()
            
            logger.info(f"Deleted quarantined dataset: {dataset_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {dataset_id}: {e}")
            return False
    
    def auto_quarantine(
        self,
        quality_report: Any,
        source_dir: str = "./data/raw"
    ) -> bool:
        """
        Automatically quarantine based on quality report.
        
        Args:
            quality_report: DataQualityReport
            source_dir: Directory containing source files
        """
        if quality_report.status != "fail":
            return False
        
        # Find source file
        dataset_id = quality_report.dataset_id
        source_file = os.path.join(source_dir, f"{dataset_id}.parquet")
        
        if not os.path.exists(source_file):
            source_file = os.path.join(source_dir, f"{dataset_id}.csv")
        
        if not os.path.exists(source_file):
            logger.warning(f"Source file not found for: {dataset_id}")
            return False
        
        # Get critical issues
        reasons = [i.description for i in quality_report.issues if i.severity == "critical"]
        reason = "; ".join(reasons) if reasons else "Quality checks failed"
        
        return self.quarantine(
            dataset_id=dataset_id,
            file_path=source_file,
            reason=reason,
            issues=quality_report.issues
        )
