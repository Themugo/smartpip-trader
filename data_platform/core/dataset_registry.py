"""
Dataset Registry

Central registry for managing datasets with full metadata and versioning.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from data_platform.models.dataset import (
    Dataset,
    DatasetMetadata,
    DatasetVersion,
    DataFormat,
    DataSource,
    DataQuality,
    MissingDataReport,
    DuplicateReport,
)

logger = logging.getLogger(__name__)


class DatasetRegistry:
    """
    Dataset Registry for managing all datasets with immutable versioning.
    
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
    
    Features:
    - Immutable dataset versions
    - Automatic validation before use
    - Searchable metadata
    - Retention management
    - Lineage tracking
    """
    
    def __init__(self, storage_path: str = "data_platform/datasets"):
        self._storage_path = storage_path
        self._datasets: Dict[str, Dataset] = {}
        
        # Indexes
        self._by_name: Dict[str, str] = {}
        self._by_source: Dict[str, Set[str]] = {}
        self._by_market: Dict[str, Set[str]] = {}
        self._by_format: Dict[str, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._by_owner: Dict[str, Set[str]] = {}
        self._validated: Set[str] = set()
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load dataset index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                for ds_data in data.get("datasets", []):
                    dataset = Dataset.from_dict(ds_data)
                    self._datasets[dataset.dataset_id] = dataset
                    self._update_indexes(dataset)
                
                self._validated = set(data.get("validated_datasets", []))
                
                logger.info(f"Loaded {len(self._datasets)} datasets from index")
            except Exception as e:
                logger.warning(f"Could not load dataset index: {e}")
    
    def _save_index(self) -> None:
        """Save dataset index"""
        os.makedirs(self._storage_path, exist_ok=True)
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "datasets": [d.to_dict() for d in self._datasets.values()],
            "validated_datasets": list(self._validated),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _update_indexes(self, dataset: Dataset) -> None:
        """Update all indexes for a dataset"""
        meta = dataset.metadata
        
        # Name index
        self._by_name[meta.name.lower()] = meta.dataset_id
        
        # Source index
        source_key = meta.source.value if isinstance(meta.source, DataSource) else meta.source
        if source_key not in self._by_source:
            self._by_source[source_key] = set()
        self._by_source[source_key].add(meta.dataset_id)
        
        # Market index
        if meta.market:
            if meta.market not in self._by_market:
                self._by_market[meta.market] = set()
            self._by_market[meta.market].add(meta.dataset_id)
        
        # Format index
        format_key = meta.format.value if isinstance(meta.format, DataFormat) else meta.format
        if format_key not in self._by_format:
            self._by_format[format_key] = set()
        self._by_format[format_key].add(meta.dataset_id)
        
        # Tag index
        for tag in meta.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(meta.dataset_id)
        
        # Owner index
        if meta.owner:
            if meta.owner not in self._by_owner:
                self._by_owner[meta.owner] = set()
            self._by_owner[meta.owner].add(meta.dataset_id)
    
    def register_dataset(
        self,
        name: str,
        description: str = "",
        market: str = "",
        source: DataSource = DataSource.LIVE,
        source_uri: str = "",
        symbols: Optional[List[str]] = None,
        format: DataFormat = DataFormat.PARQUET,
        owner: str = "",
        team: str = "",
        tags: Optional[List[str]] = None,
        retention_days: int = 365,
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dataset:
        """
        Register a new dataset.
        
        Returns:
            The registered Dataset
        """
        storage_path = f"{self._storage_path}/{name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        dataset = Dataset(
            name=name,
            description=description,
            market=market,
            source=source,
            owner=owner,
            team=team,
            storage_path=storage_path,
        )
        
        # Set additional metadata
        dataset.metadata.source_uri = source_uri
        dataset.metadata.symbols = symbols or []
        dataset.metadata.format = format
        dataset.metadata.tags = tags or []
        dataset.metadata.retention_days = retention_days
        
        if time_range:
            dataset.metadata.start_time = time_range[0]
            dataset.metadata.end_time = time_range[1]
        
        # Store
        self._datasets[dataset.dataset_id] = dataset
        self._update_indexes(dataset)
        self._save_index()
        
        logger.info(f"Registered dataset: {name} ({dataset.dataset_id})")
        return dataset
    
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        return self._datasets.get(dataset_id)
    
    def get_dataset_by_name(self, name: str) -> Optional[Dataset]:
        """Get dataset by name"""
        dataset_id = self._by_name.get(name.lower())
        return self._datasets.get(dataset_id) if dataset_id else None
    
    def get_dataset_version(
        self,
        dataset_id: str,
        version: Optional[str] = None,
    ) -> Optional[DatasetVersion]:
        """Get specific version of a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        if version:
            for v in dataset.versions:
                if v.version == version:
                    return v
        
        return dataset._current_version
    
    def update_dataset(
        self,
        dataset_id: str,
        description: Optional[str] = None,
        market: Optional[str] = None,
        tags: Optional[List[str]] = None,
        retention_days: Optional[int] = None,
    ) -> Optional[Dataset]:
        """Update dataset metadata"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        if dataset.is_immutable:
            logger.warning(f"Cannot update immutable dataset: {dataset_id}")
            return None
        
        if description is not None:
            dataset.metadata.description = description
        if market is not None:
            dataset.metadata.market = market
        if tags is not None:
            dataset.metadata.tags = tags
        if retention_days is not None:
            dataset.metadata.retention_days = retention_days
        
        dataset.metadata.updated_at = datetime.utcnow()
        self._save_index()
        
        return dataset
    
    def add_dataset_version(
        self,
        dataset_id: str,
        content: bytes,
        change_summary: str = "",
        created_by: str = "",
        statistics: Optional[Dict[str, Any]] = None,
    ) -> Optional[DatasetVersion]:
        """Add a new version to a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        # Compute content hash
        content_hash = hashlib.sha256(content).hexdigest()
        content_size = len(content)
        
        # Compute integrity hash
        dataset.compute_hash(content)
        
        # Update statistics
        if statistics:
            if "tick_count" in statistics:
                dataset.metadata.tick_count = statistics["tick_count"]
            if "row_count" in statistics:
                dataset.metadata.row_count = statistics["row_count"]
            if "column_count" in statistics:
                dataset.metadata.column_count = statistics["column_count"]
        
        dataset.metadata.file_size_bytes = content_size
        
        # Create version
        version = dataset.create_version(
            content_hash=content_hash,
            content_size=content_size,
            change_summary=change_summary,
            created_by=created_by,
        )
        
        # Save content
        self._save_dataset_content(dataset_id, content)
        
        self._save_index()
        logger.info(f"Added version {version.version} to dataset: {dataset.metadata.name}")
        
        return version
    
    def _save_dataset_content(self, dataset_id: str, content: bytes) -> str:
        """Save dataset content to storage"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return ""
        
        os.makedirs(dataset.metadata.storage_path, exist_ok=True)
        version = dataset._current_version
        
        file_path = f"{dataset.metadata.storage_path}/{version.version_id}.{dataset.metadata.format.value}"
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.debug(f"Saved content to: {file_path}")
        return file_path
    
    def validate_dataset(
        self,
        dataset_id: str,
        validator: str = "system",
        quality: Optional[DataQuality] = None,
        missing_report: Optional[MissingDataReport] = None,
        duplicate_report: Optional[DuplicateReport] = None,
        errors: Optional[List[str]] = None,
    ) -> bool:
        """
        Validate a dataset and mark it as validated.
        
        Every dataset must be validated before use.
        """
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        # Check for validation errors
        if errors:
            dataset.metadata.validation_errors = errors
            dataset.metadata.is_validated = False
            logger.warning(f"Dataset {dataset_id} has validation errors: {errors}")
            self._save_index()
            return False
        
        # Set quality metrics
        if quality:
            dataset.metadata.quality_score = quality
        
        if missing_report:
            dataset.metadata.missing_data_report = missing_report
        
        if duplicate_report:
            dataset.metadata.duplicate_report = duplicate_report
        
        # Mark as validated
        dataset.metadata.is_validated = True
        dataset.metadata.validated_at = datetime.utcnow()
        dataset.metadata.validated_by = validator
        dataset.metadata.validation_errors = []
        
        self._validated.add(dataset_id)
        self._save_index()
        
        logger.info(f"Dataset {dataset_id} validated successfully")
        return True
    
    def is_validated(self, dataset_id: str) -> bool:
        """Check if dataset is validated"""
        return dataset_id in self._validated
    
    def require_validated(self, dataset_id: str) -> Dataset:
        """
        Get a dataset, raising an error if not validated.
        
        This ensures experiments only use validated datasets.
        """
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        if not self.is_validated(dataset_id):
            raise ValueError(
                f"Dataset {dataset_id} is not validated. "
                f"Validation is required before use."
            )
        
        return dataset
    
    def freeze_dataset(self, dataset_id: str) -> bool:
        """Freeze a dataset to make it immutable"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        dataset.freeze()
        self._save_index()
        
        logger.info(f"Dataset {dataset_id} frozen (immutable)")
        return True
    
    def archive_dataset(self, dataset_id: str) -> bool:
        """Archive a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        dataset.archive()
        self._save_index()
        
        logger.info(f"Dataset {dataset_id} archived")
        return True
    
    def add_feature_coverage(
        self,
        dataset_id: str,
        feature_id: str,
        coverage: float = 1.0,
    ) -> bool:
        """Add feature coverage to a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        dataset.add_feature(feature_id, coverage)
        self._save_index()
        
        return True
    
    def set_time_range(
        self,
        dataset_id: str,
        start: datetime,
        end: datetime,
    ) -> bool:
        """Set time range for a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        dataset.set_time_range(start, end)
        self._save_index()
        
        return True
    
    def search(
        self,
        query: Optional[str] = None,
        source: Optional[DataSource] = None,
        market: Optional[str] = None,
        format: Optional[DataFormat] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
        validated_only: bool = False,
        immutable_only: bool = False,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_quality_score: Optional[float] = None,
    ) -> List[Dataset]:
        """Search for datasets"""
        results = list(self._datasets.values())
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                d for d in results
                if query_lower in d.metadata.name.lower() or
                   query_lower in d.metadata.description.lower()
            ]
        
        # Filter by source
        if source:
            results = [
                d for d in results
                if d.metadata.source == source
            ]
        
        # Filter by market
        if market:
            results = [
                d for d in results
                if d.metadata.market == market
            ]
        
        # Filter by format
        if format:
            results = [
                d for d in results
                if d.metadata.format == format
            ]
        
        # Filter by tags
        if tags:
            results = [
                d for d in results
                if any(tag in d.metadata.tags for tag in tags)
            ]
        
        # Filter by owner
        if owner:
            results = [
                d for d in results
                if d.metadata.owner == owner
            ]
        
        # Filter validated only
        if validated_only:
            results = [d for d in results if d.dataset_id in self._validated]
        
        # Filter immutable only
        if immutable_only:
            results = [d for d in results if d.is_immutable]
        
        # Filter by time range
        if time_range:
            start, end = time_range
            results = [
                d for d in results
                if d.metadata.start_time and d.metadata.end_time and
                   d.metadata.start_time >= start and d.metadata.end_time <= end
            ]
        
        # Filter by minimum quality score
        if min_quality_score is not None:
            results = [
                d for d in results
                if d.metadata.quality_score.overall_score >= min_quality_score
            ]
        
        return sorted(results, key=lambda d: d.metadata.created_at, reverse=True)
    
    def get_datasets_by_source(self, source: DataSource) -> List[Dataset]:
        """Get all datasets from a specific source"""
        dataset_ids = self._by_source.get(source.value, set())
        return [self._datasets[did] for did in dataset_ids if did in self._datasets]
    
    def get_datasets_by_market(self, market: str) -> List[Dataset]:
        """Get all datasets for a specific market"""
        dataset_ids = self._by_market.get(market, set())
        return [self._datasets[did] for did in dataset_ids if did in self._datasets]
    
    def get_datasets_by_tag(self, tag: str) -> List[Dataset]:
        """Get all datasets with a specific tag"""
        dataset_ids = self._by_tag.get(tag, set())
        return [self._datasets[did] for did in dataset_ids if did in self._datasets]
    
    def get_overlapping_datasets(
        self,
        dataset_id: str,
    ) -> List[Dataset]:
        """Get datasets that overlap in time range with the given dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset or not dataset.metadata.start_time or not dataset.metadata.end_time:
            return []
        
        overlapping = []
        
        for other in self._datasets.values():
            if other.dataset_id == dataset_id:
                continue
            
            if not other.metadata.start_time or not other.metadata.end_time:
                continue
            
            # Check for overlap
            if (
                other.metadata.start_time <= dataset.metadata.end_time and
                other.metadata.end_time >= dataset.metadata.start_time
            ):
                overlapping.append(other)
        
        return overlapping
    
    def get_retention_candidates(self, days_threshold: int = 90) -> List[Dataset]:
        """Get datasets eligible for archiving based on age"""
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        
        return [
            d for d in self._datasets.values()
            if d.metadata.created_at < cutoff and
               not d.metadata.archived_at and
               d.metadata.auto_archive
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset registry statistics"""
        datasets = list(self._datasets.values())
        
        return {
            "total_datasets": len(datasets),
            "validated_datasets": len(self._validated),
            "immutable_datasets": sum(1 for d in datasets if d.is_immutable),
            "archived_datasets": sum(1 for d in datasets if d.metadata.archived_at),
            "by_source": {
                source: len(ids)
                for source, ids in self._by_source.items()
            },
            "by_market": {
                market: len(ids)
                for market, ids in self._by_market.items()
            },
            "by_format": {
                fmt: len(ids)
                for fmt, ids in self._by_format.items()
            },
            "total_versions": sum(len(d.versions) for d in datasets),
            "total_size_bytes": sum(d.metadata.file_size_bytes for d in datasets),
            "total_tick_count": sum(d.metadata.tick_count for d in datasets),
            "average_quality_score": (
                sum(d.metadata.quality_score.overall_score for d in datasets) / len(datasets)
                if datasets else 0
            ),
        }
    
    def list_datasets(
        self,
        validated_only: bool = True,
        immutable_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List all datasets with metadata summary"""
        datasets = self.search(
            validated_only=validated_only,
            immutable_only=immutable_only,
        )
        
        return [
            {
                "dataset_id": d.dataset_id,
                "name": d.metadata.name,
                "description": d.metadata.description,
                "version": d.version,
                "source": d.metadata.source.value if isinstance(d.metadata.source, DataSource) else d.metadata.source,
                "market": d.metadata.market,
                "format": d.metadata.format.value if isinstance(d.metadata.format, DataFormat) else d.metadata.format,
                "is_validated": d.dataset_id in self._validated,
                "is_immutable": d.is_immutable,
                "is_archived": bool(d.metadata.archived_at),
                "tick_count": d.metadata.tick_count,
                "row_count": d.metadata.row_count,
                "quality_score": d.metadata.quality_score.overall_score,
                "feature_count": len(d.metadata.feature_ids),
                "owner": d.metadata.owner,
                "tags": d.metadata.tags,
                "start_time": d.metadata.start_time.isoformat() if d.metadata.start_time else None,
                "end_time": d.metadata.end_time.isoformat() if d.metadata.end_time else None,
                "created_at": d.metadata.created_at.isoformat() if isinstance(d.metadata.created_at, datetime) else d.metadata.created_at,
                "integrity_hash": d.metadata.integrity_hash[:16] + "..." if d.metadata.integrity_hash else None,
            }
            for d in datasets
        ]
    
    def export_datasets(self, dataset_ids: List[str]) -> Dict[str, Any]:
        """Export datasets for sharing or backup"""
        datasets = {
            did: self._datasets[did].to_dict()
            for did in dataset_ids
            if did in self._datasets
        }
        
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "dataset_count": len(datasets),
            "datasets": datasets,
        }


# Type alias for Set
from typing import Set
