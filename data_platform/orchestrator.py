"""
Data Platform Orchestrator

Unified interface for the SmartPip Data Platform.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from data_platform.core.data_lake import DataLake
from data_platform.core.dataset_registry import DatasetRegistry
from data_platform.core.feature_store import FeatureStore
from data_platform.core.schema_registry import SchemaRegistryManager
from data_platform.core.metadata_catalog import MetadataCatalog
from data_platform.core.versioning import DataVersioningManager
from data_platform.core.lineage import LineageTracker
from data_platform.core.snapshots import SnapshotManager
from data_platform.core.compression import CompressionManager
from data_platform.core.archiver import Archiver
from data_platform.core.integrity import IntegrityVerifier
from data_platform.core.validation import DatasetValidator, ValidationLevel
from data_platform.core.formats import FormatManager
from data_platform.models.dataset import (
    Dataset,
    DataFormat,
    DataSource,
    DataQuality,
)
from data_platform.models.feature import Feature, FeatureType

logger = logging.getLogger(__name__)


class DataPlatformOrchestrator:
    """
    Data Platform Orchestrator - Unified interface for the Data Platform.
    
    Provides a single entry point for all data platform operations
    with automatic integration and coordination between components.
    
    Features:
    - Data Lake: Central storage for all data
    - Feature Store: Feature management with versioning
    - Dataset Registry: Dataset tracking and validation
    - Schema Registry: Data schema management
    - Metadata Catalog: Searchable metadata
    - Data Versioning: Immutable version control
    - Data Lineage: Provenance tracking
    - Feature Lineage: Feature dependencies
    - Historical Snapshots: Point-in-time recovery
    - Compression: Automatic compression
    - Automatic Archiving: Data lifecycle management
    - Automatic Integrity Verification: Data validation
    
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
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        storage_path: str = "data_platform",
        enable_auto_compress: bool = True,
        enable_auto_archive: bool = True,
        enable_auto_validate: bool = True,
        enable_auto_verify: bool = True,
    ):
        """Initialize the Data Platform Orchestrator"""
        if hasattr(self, "_initialized"):
            return
        
        self._initialized = True
        self._storage_path = storage_path
        
        logger.info("Initializing Data Platform Orchestrator...")
        
        # Initialize the Data Lake (which includes all core components)
        self._data_lake = DataLake(
            storage_path=storage_path,
            enable_auto_compress=enable_auto_compress,
            enable_auto_archive=enable_auto_archive,
            enable_auto_validate=enable_auto_validate,
            enable_auto_verify=enable_auto_verify,
        )
        
        # Direct component access for advanced operations
        self._registry = self._data_lake.registry
        self._feature_store = self._data_lake.features
        self._schema_registry = self._data_lake.schemas
        self._catalog = self._data_lake.catalog
        self._versioning = self._data_lake.versioning
        self._lineage = self._data_lake.lineage
        self._snapshots = self._data_lake.snapshots
        self._compression = self._data_lake._compression
        self._archiver = self._data_lake._archiver
        self._integrity = self._data_lake.integrity
        self._validator = self._data_lake._validator
        self._formats = self._data_lake.formats
        
        logger.info("Data Platform Orchestrator initialized successfully")
    
    # ==================== Data Ingestion ====================
    
    def ingest_data(
        self,
        data: Any,
        name: str,
        description: str = "",
        market: str = "",
        source: str = "live",
        format: str = "parquet",
        owner: str = "",
        tags: Optional[List[str]] = None,
        validate: bool = True,
        track_lineage: bool = True,
    ) -> Tuple[Dataset, Dict[str, Any]]:
        """
        Ingest data into the data lake.
        
        Automatically validates, computes integrity hash, creates version,
        tracks lineage, and registers in catalog.
        
        Args:
            data: Data to ingest (DataFrame, list, bytes, or file path)
            name: Dataset name
            description: Dataset description
            market: Market identifier
            source: Data source type
            format: Storage format (parquet, arrow, csv, json)
            owner: Owner identifier
            tags: Tags for the dataset
            validate: Whether to validate the data
            track_lineage: Whether to track lineage
        
        Returns:
            Tuple of (Dataset, ingestion_metadata)
        """
        data_format = DataFormat(format)
        data_source = DataSource(source)
        
        dataset, metadata = self._data_lake.ingest(
            data=data,
            name=name,
            description=description,
            market=market,
            source=data_source,
            format=data_format,
            owner=owner,
            tags=tags or [],
            validate=validate,
        )
        
        logger.info(f"Ingested dataset: {name} ({dataset.dataset_id})")
        return dataset, metadata
    
    # ==================== Data Access ====================
    
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID"""
        return self._registry.get_dataset(dataset_id)
    
    def get_validated_dataset(self, dataset_id: str) -> Dataset:
        """
        Get a validated dataset, raising an error if not validated.
        
        Every experiment must reference immutable validated datasets.
        """
        return self._registry.require_validated(dataset_id)
    
    def read_dataset(
        self,
        dataset_id: str,
        version: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> Optional[Any]:
        """Read dataset content"""
        return self._data_lake.read(dataset_id, version=version, as_of=as_of)
    
    def search_datasets(
        self,
        query: Optional[str] = None,
        market: Optional[str] = None,
        validated_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for datasets"""
        return self._registry.list_datasets(validated_only=validated_only)
    
    # ==================== Feature Operations ====================
    
    def register_feature(
        self,
        name: str,
        description: str,
        feature_type: str = "derived",
        dependencies: Optional[List[str]] = None,
        owner: str = "",
        tags: Optional[List[str]] = None,
    ) -> Tuple[Feature, bool]:
        """
        Register a new feature with versioning and deduplication.
        
        Automatically prevents duplicate engineered features.
        
        Args:
            name: Feature name
            description: Feature description
            feature_type: Type of feature (raw, technical, derived, aggregated, label, metadata)
            dependencies: List of feature IDs this depends on
            owner: Owner identifier
            tags: Tags for the feature
        
        Returns:
            Tuple of (Feature, is_new)
            - is_new is False if a duplicate signature was found
        """
        ft = FeatureType(feature_type)
        
        feature, is_new = self._feature_store.register_feature(
            name=name,
            description=description,
            feature_type=ft,
            dependencies=dependencies or [],
            owner=owner,
            tags=tags or [],
        )
        
        if is_new:
            logger.info(f"Registered new feature: {name} ({feature.feature_id})")
        else:
            logger.warning(f"Duplicate feature detected: {name}")
        
        return feature, is_new
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID"""
        return self._feature_store.get_feature(feature_id)
    
    def search_features(
        self,
        query: Optional[str] = None,
        feature_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for features"""
        ft = FeatureType(feature_type) if feature_type else None
        return self._feature_store.list_features(feature_type=ft)
    
    def get_feature_lineage(self, feature_id: str) -> Dict[str, Any]:
        """Get feature lineage"""
        return self._feature_store.get_feature_lineage(feature_id)
    
    def record_feature_usage(
        self,
        feature_id: str,
        used_by: str,
        use_case: str,
        dataset_id: str,
    ) -> None:
        """Record feature usage for tracking"""
        self._feature_store.record_usage(
            feature_id=feature_id,
            used_by=used_by,
            use_case=use_case,
            dataset_id=dataset_id,
        )
    
    # ==================== Schema Operations ====================
    
    def register_schema(
        self,
        name: str,
        fields: List[Dict[str, Any]],
        domain: str = "trading",
    ) -> Any:
        """Register a data schema"""
        return self._data_lake.register_schema(
            name=name,
            fields=fields,
            domain=domain,
        )
    
    def validate_data(
        self,
        registry_id: str,
        data: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        """Validate data against a schema"""
        return self._schema_registry.validate_data(registry_id, data)
    
    # ==================== Validation ====================
    
    def validate_dataset(
        self,
        dataset_id: str,
        level: str = "standard",
    ) -> Any:
        """
        Validate a dataset before use.
        
        Every dataset must be validated before use.
        """
        validation_level = ValidationLevel(level)
        return self._data_lake.validate_dataset(dataset_id, level=validation_level)
    
    # ==================== Integrity ====================
    
    def verify_dataset_integrity(self, dataset_id: str) -> Any:
        """Verify dataset integrity"""
        return self._data_lake.verify_integrity(dataset_id)
    
    def generate_integrity_manifest(self) -> Dict[str, Any]:
        """Generate integrity manifest for all datasets"""
        return self._integrity.generate_manifest()
    
    # ==================== Lineage ====================
    
    def record_transformation(
        self,
        input_dataset_ids: List[str],
        output_dataset_id: str,
        transformation_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a data transformation for lineage tracking"""
        self._data_lake.record_transformation(
            input_dataset_ids=input_dataset_ids,
            output_dataset_id=output_dataset_id,
            transformation_type=transformation_type,
            parameters=parameters,
        )
    
    def get_data_lineage(self, dataset_id: str) -> Dict[str, Any]:
        """Get data lineage for a dataset"""
        return self._data_lake.get_lineage(dataset_id)
    
    # ==================== Versioning ====================
    
    def create_dataset_version(
        self,
        dataset_id: str,
        content: bytes,
        change_summary: str = "",
    ) -> Any:
        """Create a new immutable version of a dataset"""
        return self._data_lake.create_version(
            dataset_id=dataset_id,
            content=content,
            change_summary=change_summary,
        )
    
    def get_version_history(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get version history for a dataset"""
        return self._data_lake.get_version_history(dataset_id)
    
    # ==================== Search ====================
    
    def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
    ) -> List[Any]:
        """
        Search across all data assets.
        
        Args:
            query: Search query
            entity_type: Filter by type (dataset, feature, schema)
        
        Returns:
            List of matching entries
        """
        if entity_type == "dataset":
            return self._catalog.search_datasets(query=query)
        elif entity_type == "feature":
            return self._catalog.search_features(query=query)
        else:
            return self._catalog.search(query=query)
    
    # ==================== Maintenance ====================
    
    def run_maintenance(self) -> Dict[str, Any]:
        """Run all maintenance tasks"""
        results = {
            "snapshots_cleaned": self._snapshots.cleanup_expired(),
            "archives_processed": self._archiver.process_deletions(),
            "integrity_checks": len(self._data_lake.run_integrity_checks()),
        }
        
        logger.info(f"Maintenance completed: {results}")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all components"""
        return self._data_lake.get_statistics()
    
    # ==================== Accessors ====================
    
    @property
    def data_lake(self) -> DataLake:
        """Get the underlying DataLake instance"""
        return self._data_lake
    
    @property
    def registry(self) -> DatasetRegistry:
        """Get the Dataset Registry"""
        return self._registry
    
    @property
    def features(self) -> FeatureStore:
        """Get the Feature Store"""
        return self._feature_store
    
    @property
    def schemas(self) -> SchemaRegistryManager:
        """Get the Schema Registry"""
        return self._schema_registry
    
    @property
    def catalog(self) -> MetadataCatalog:
        """Get the Metadata Catalog"""
        return self._catalog
    
    @property
    def lineage(self) -> LineageTracker:
        """Get the Lineage Tracker"""
        return self._lineage
    
    @property
    def versioning(self) -> DataVersioningManager:
        """Get the Versioning Manager"""
        return self._versioning
    
    @property
    def snapshots(self) -> SnapshotManager:
        """Get the Snapshot Manager"""
        return self._snapshots
    
    @property
    def integrity(self) -> IntegrityVerifier:
        """Get the Integrity Verifier"""
        return self._integrity
    
    @property
    def formats(self) -> FormatManager:
        """Get the Format Manager"""
        return self._formats


# Global instance
_data_platform: Optional[DataPlatformOrchestrator] = None


def get_data_platform(
    storage_path: str = "data_platform",
    **kwargs,
) -> DataPlatformOrchestrator:
    """
    Get the global Data Platform instance.
    
    Args:
        storage_path: Path to data platform storage
        **kwargs: Additional configuration options
    
    Returns:
        DataPlatformOrchestrator instance
    """
    global _data_platform
    
    if _data_platform is None:
        _data_platform = DataPlatformOrchestrator(
            storage_path=storage_path,
            **kwargs,
        )
    
    return _data_platform


def reset_data_platform() -> None:
    """Reset the global Data Platform instance (for testing)"""
    global _data_platform
    _data_platform = None
