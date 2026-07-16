"""
Dataset Model

Core dataset model with all required metadata fields.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json


class DataFormat(Enum):
    """Supported data formats"""
    PARQUET = "parquet"
    ARROW = "arrow"
    CSV = "csv"
    SQL = "sql"
    OBJECT_STORAGE = "object_storage"
    JSON = "json"


class DataSource(Enum):
    """Data source types"""
    LIVE = "live"
    HISTORICAL = "historical"
    SYNTHETIC = "synthetic"
    AGGREGATED = "aggregated"
    DERIVED = "derived"
    BACKTEST = "backtest"


@dataclass
class MissingDataReport:
    """Report on missing data in a dataset"""
    total_missing: int
    missing_percentage: float
    missing_by_column: Dict[str, Tuple[int, float]]
    missing_time_ranges: List[Dict[str, str]]
    imputation_applied: bool
    imputation_method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_missing": self.total_missing,
            "missing_percentage": self.missing_percentage,
            "missing_by_column": {k: list(v) for k, v in self.missing_by_column.items()},
            "missing_time_ranges": self.missing_time_ranges,
            "imputation_applied": self.imputation_applied,
            "imputation_method": self.imputation_method,
        }


@dataclass
class DuplicateReport:
    """Report on duplicate data in a dataset"""
    total_duplicates: int
    duplicate_percentage: float
    duplicate_rows: List[int]
    duplicate_groups: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duplicates": self.total_duplicates,
            "duplicate_percentage": self.duplicate_percentage,
            "duplicate_row_indices": self.duplicate_rows,
            "duplicate_groups": self.duplicate_groups,
        }


@dataclass
class DataQuality:
    """Data quality metrics"""
    completeness: float = 1.0  # 0-1
    accuracy: float = 1.0  # 0-1
    consistency: float = 1.0  # 0-1
    timeliness: float = 1.0  # 0-1
    validity: float = 1.0  # 0-1
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score"""
        return (
            self.completeness * 0.3 +
            self.accuracy * 0.25 +
            self.consistency * 0.2 +
            self.timeliness * 0.1 +
            self.validity * 0.15
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "completeness": self.completeness,
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "timeliness": self.timeliness,
            "validity": self.validity,
            "overall_score": self.overall_score,
        }


@dataclass
class DatasetMetadata:
    """Complete dataset metadata"""
    # Core identification
    dataset_id: str
    name: str
    description: str
    version: str
    
    # Versioning
    version_major: int = 1
    version_minor: int = 0
    version_patch: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None
    
    # Source information
    source: DataSource = DataSource.LIVE
    source_uri: str = ""
    source_system: str = ""
    
    # Market information
    market: str = ""
    symbols: List[str] = field(default_factory=list)
    
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_zone: str = "UTC"
    
    # Data statistics
    tick_count: int = 0
    row_count: int = 0
    column_count: int = 0
    file_size_bytes: int = 0
    compressed_size_bytes: int = 0
    
    # Quality metrics
    quality_score: DataQuality = field(default_factory=DataQuality)
    missing_data_report: Optional[MissingDataReport] = None
    duplicate_report: Optional[DuplicateReport] = None
    
    # Integrity
    integrity_hash: str = ""
    checksum_algorithm: str = "sha256"
    
    # Schema
    schema_id: Optional[str] = None
    schema_version: str = ""
    
    # Format
    format: DataFormat = DataFormat.PARQUET
    storage_path: str = ""
    
    # Feature coverage
    feature_ids: List[str] = field(default_factory=list)
    feature_coverage: Dict[str, float] = field(default_factory=dict)
    
    # Lineage
    parent_dataset_ids: List[str] = field(default_factory=list)
    derived_from: List[str] = field(default_factory=list)
    
    # Tags and classification
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    classification: str = "internal"
    
    # Retention
    retention_days: int = 365
    auto_archive: bool = True
    archive_threshold_days: int = 90
    
    # Validation
    is_validated: bool = False
    validated_at: Optional[datetime] = None
    validated_by: str = ""
    validation_errors: List[str] = field(default_factory=list)
    
    # Access control
    owner: str = ""
    team: str = ""
    is_public: bool = False
    
    # Immutable reference
    is_immutable: bool = False
    
    def compute_integrity_hash(self, data: bytes) -> str:
        """Compute integrity hash for data"""
        self.integrity_hash = hashlib.sha256(data).hexdigest()
        return self.integrity_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            # Core identification
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            
            # Versioning
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "version_patch": self.version_patch,
            
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            
            # Source information
            "source": self.source.value if isinstance(self.source, DataSource) else self.source,
            "source_uri": self.source_uri,
            "source_system": self.source_system,
            
            # Market information
            "market": self.market,
            "symbols": self.symbols,
            
            # Time range
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "time_zone": self.time_zone,
            
            # Data statistics
            "tick_count": self.tick_count,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "file_size_bytes": self.file_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            
            # Quality metrics
            "quality_score": self.quality_score.to_dict(),
            "missing_data_report": self.missing_data_report.to_dict() if self.missing_data_report else None,
            "duplicate_report": self.duplicate_report.to_dict() if self.duplicate_report else None,
            
            # Integrity
            "integrity_hash": self.integrity_hash,
            "checksum_algorithm": self.checksum_algorithm,
            
            # Schema
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            
            # Format
            "format": self.format.value if isinstance(self.format, DataFormat) else self.format,
            "storage_path": self.storage_path,
            
            # Feature coverage
            "feature_ids": self.feature_ids,
            "feature_coverage": self.feature_coverage,
            
            # Lineage
            "parent_dataset_ids": self.parent_dataset_ids,
            "derived_from": self.derived_from,
            
            # Tags and classification
            "tags": self.tags,
            "labels": self.labels,
            "classification": self.classification,
            
            # Retention
            "retention_days": self.retention_days,
            "auto_archive": self.auto_archive,
            "archive_threshold_days": self.archive_threshold_days,
            
            # Validation
            "is_validated": self.is_validated,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "validated_by": self.validated_by,
            "validation_errors": self.validation_errors,
            
            # Access control
            "owner": self.owner,
            "team": self.team,
            "is_public": self.is_public,
            
            # Immutable reference
            "is_immutable": self.is_immutable,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetMetadata":
        """Create from dictionary"""
        # Handle nested objects
        if "quality_score" in data and isinstance(data["quality_score"], dict):
            data["quality_score"] = DataQuality(**data["quality_score"])
        if "missing_data_report" in data and data["missing_data_report"]:
            data["missing_data_report"] = MissingDataReport(**data["missing_data_report"])
        if "duplicate_report" in data and data["duplicate_report"]:
            data["duplicate_report"] = DuplicateReport(**data["duplicate_report"])
        
        # Handle enums
        if "source" in data and isinstance(data["source"], str):
            data["source"] = DataSource(data["source"])
        if "format" in data and isinstance(data["format"], str):
            data["format"] = DataFormat(data["format"])
        
        # Handle datetime conversion
        for dt_field in ["created_at", "updated_at", "archived_at", "validated_at", "start_time", "end_time"]:
            if dt_field in data and isinstance(data[dt_field], str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        
        return cls(**data)


@dataclass
class DatasetVersion:
    """A specific version of a dataset"""
    version_id: str
    dataset_id: str
    version: str
    
    # Version info
    version_major: int
    version_minor: int
    version_patch: int
    
    # Content
    content_hash: str
    content_size: int
    
    # Metadata snapshot
    metadata_snapshot: Dict[str, Any]
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Status
    is_current: bool = True
    is_frozen: bool = False
    
    # Statistics
    change_summary: str = ""
    rows_added: int = 0
    rows_modified: int = 0
    rows_deleted: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "dataset_id": self.dataset_id,
            "version": self.version,
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "version_patch": self.version_patch,
            "content_hash": self.content_hash,
            "content_size": self.content_size,
            "metadata_snapshot": self.metadata_snapshot,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "is_current": self.is_current,
            "is_frozen": self.is_frozen,
            "change_summary": self.change_summary,
            "rows_added": self.rows_added,
            "rows_modified": self.rows_modified,
            "rows_deleted": self.rows_deleted,
        }


class Dataset:
    """
    Main Dataset class with full metadata and versioning support.
    
    Every dataset contains:
    - Dataset ID
    - Version
    - Creation Date
    - Source
    - Market
    - Time Range
    - Tick Count
    - Quality Score
    - Missing Data Report
    - Duplicate Report
    - Integrity Hash
    - Feature Coverage
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        market: str = "",
        source: DataSource = DataSource.LIVE,
        owner: str = "",
        team: str = "",
        storage_path: str = "",
    ):
        self.metadata = DatasetMetadata(
            dataset_id=str(uuid.uuid4()),
            name=name,
            description=description,
            version="1.0.0",
            source=source,
            market=market,
            owner=owner,
            team=team,
            storage_path=storage_path,
        )
        self.versions: List[DatasetVersion] = []
        self._current_version: Optional[DatasetVersion] = None
    
    @property
    def dataset_id(self) -> str:
        return self.metadata.dataset_id
    
    @property
    def version(self) -> str:
        return self.metadata.version
    
    @property
    def is_validated(self) -> bool:
        return self.metadata.is_validated
    
    @property
    def is_immutable(self) -> bool:
        return self.metadata.is_immutable
    
    def create_version(
        self,
        content_hash: str,
        content_size: int,
        change_summary: str = "",
        created_by: str = "",
    ) -> DatasetVersion:
        """Create a new version of the dataset"""
        # Bump version
        self.metadata.version_patch += 1
        
        version = DatasetVersion(
            version_id=str(uuid.uuid4()),
            dataset_id=self.dataset_id,
            version=self.metadata.version,
            version_major=self.metadata.version_major,
            version_minor=self.metadata.version_minor,
            version_patch=self.metadata.version_patch,
            content_hash=content_hash,
            content_size=content_size,
            metadata_snapshot=self.metadata.to_dict(),
            created_by=created_by,
            change_summary=change_summary,
        )
        
        # Mark previous version as not current
        if self._current_version:
            self._current_version.is_current = False
        
        self.versions.append(version)
        self._current_version = version
        self.metadata.updated_at = datetime.utcnow()
        
        return version
    
    def validate(self, validator: str = "system") -> bool:
        """Mark dataset as validated"""
        self.metadata.is_validated = True
        self.metadata.validated_at = datetime.utcnow()
        self.metadata.validated_by = validator
        return True
    
    def freeze(self) -> None:
        """Make dataset immutable"""
        self.metadata.is_immutable = True
        if self._current_version:
            self._current_version.is_frozen = True
    
    def archive(self) -> None:
        """Archive the dataset"""
        self.metadata.archived_at = datetime.utcnow()
    
    def add_feature(self, feature_id: str, coverage: float = 1.0) -> None:
        """Add feature coverage to dataset"""
        if feature_id not in self.metadata.feature_ids:
            self.metadata.feature_ids.append(feature_id)
        self.metadata.feature_coverage[feature_id] = coverage
    
    def set_time_range(self, start: datetime, end: datetime) -> None:
        """Set dataset time range"""
        self.metadata.start_time = start
        self.metadata.end_time = end
    
    def set_quality(self, quality: DataQuality) -> None:
        """Set quality metrics"""
        self.metadata.quality_score = quality
    
    def set_missing_report(self, report: MissingDataReport) -> None:
        """Set missing data report"""
        self.metadata.missing_data_report = report
    
    def set_duplicate_report(self, report: DuplicateReport) -> None:
        """Set duplicate data report"""
        self.metadata.duplicate_report = report
    
    def compute_hash(self, data: bytes) -> str:
        """Compute and set integrity hash"""
        return self.metadata.compute_integrity_hash(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "versions": [v.to_dict() for v in self.versions],
            "current_version": self._current_version.to_dict() if self._current_version else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dataset":
        """Create from dictionary"""
        dataset = cls(
            name=data["metadata"]["name"],
            description=data["metadata"]["description"],
            market=data["metadata"]["market"],
        )
        dataset.metadata = DatasetMetadata.from_dict(data["metadata"])
        
        if "versions" in data:
            dataset.versions = [
                DatasetVersion(
                    version_id=v["version_id"],
                    dataset_id=v["dataset_id"],
                    version=v["version"],
                    version_major=v["version_major"],
                    version_minor=v["version_minor"],
                    version_patch=v["version_patch"],
                    content_hash=v["content_hash"],
                    content_size=v["content_size"],
                    metadata_snapshot=v["metadata_snapshot"],
                    created_at=datetime.fromisoformat(v["created_at"]) if isinstance(v["created_at"], str) else v["created_at"],
                    created_by=v.get("created_by", ""),
                    is_current=v.get("is_current", True),
                    is_frozen=v.get("is_frozen", False),
                    change_summary=v.get("change_summary", ""),
                    rows_added=v.get("rows_added", 0),
                    rows_modified=v.get("rows_modified", 0),
                    rows_deleted=v.get("rows_deleted", 0),
                )
                for v in data["versions"]
            ]
            
            # Set current version
            for v in dataset.versions:
                if v.is_current:
                    dataset._current_version = v
                    break
        
        return dataset
