"""
Data Lake

Unified data storage with format support and automatic management.
"""

import hashlib
import io
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

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

logger = logging.getLogger(__name__)


class DataLake:
    """
    Data Lake - Central storage for all data assets.
    
    Features:
    - Multi-format support (Parquet, Arrow, CSV, JSON, SQL)
    - Object storage support (S3, GCS, Azure, local)
    - Automatic compression
    - Automatic archiving
    - Integrity verification
    - Dataset validation
    - Versioning
    - Lineage tracking
    - Metadata catalog
    
    Every dataset automatically includes:
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
        storage_path: str = "data_platform/lake",
        enable_auto_compress: bool = True,
        enable_auto_archive: bool = True,
        enable_auto_validate: bool = True,
        enable_auto_verify: bool = True,
        default_compression_threshold_mb: float = 10.0,
        default_archive_age_days: int = 90,
    ):
        self._storage_path = storage_path
        
        # Initialize components
        self._registry = DatasetRegistry(storage_path=f"{storage_path}/datasets")
        self._feature_store = FeatureStore(storage_path=f"{storage_path}/features")
        self._schema_registry = SchemaRegistryManager(storage_path=f"{storage_path}/schemas")
        self._catalog = MetadataCatalog(storage_path=f"{storage_path}/catalog")
        self._versioning = DataVersioningManager(storage_path=f"{storage_path}/versions")
        self._lineage = LineageTracker(storage_path=f"{storage_path}/lineage")
        self._snapshots = SnapshotManager(storage_path=f"{storage_path}/snapshots")
        self._compression = CompressionManager(storage_path=f"{storage_path}/compression")
        self._archiver = Archiver(
            storage_path=f"{storage_path}/archives",
            cold_storage_path=f"{storage_path}/cold_storage",
            default_age_days=default_archive_age_days,
        )
        self._integrity = IntegrityVerifier(storage_path=f"{storage_path}/integrity")
        self._validator = DatasetValidator()
        self._formats = FormatManager()
        
        # Configuration
        self._enable_auto_compress = enable_auto_compress
        self._enable_auto_archive = enable_auto_archive
        self._enable_auto_validate = enable_auto_validate
        self._enable_auto_verify = enable_auto_verify
        self._compression_threshold = default_compression_threshold_mb * 1024 * 1024
        
        # Create directories
        os.makedirs(storage_path, exist_ok=True)
        
        logger.info("DataLake initialized")
    
    # ==================== Core Operations ====================
    
    def ingest(
        self,
        data: Any,
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
        validate: bool = True,
        compute_hash: bool = True,
        create_snapshot: bool = True,
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Tuple[Dataset, Dict[str, Any]]:
        """
        Ingest data into the data lake.
        
        Automatically:
        - Validates data (if enabled)
        - Computes integrity hash
        - Creates version
        - Registers lineage
        - Creates snapshot (if enabled)
        - Registers in metadata catalog
        
        Returns:
            Tuple of (Dataset, ingestion_metadata)
        """
        import pandas as pd
        
        # Convert to appropriate format
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, bytes):
            df = self._formats.read(data, format=format.value)
        else:
            df = pd.DataFrame(data)
        
        # Compute statistics
        stats = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
        
        # Convert to bytes for storage
        content = self._serialize(df, format)
        content_size = len(content)
        
        # Check compression threshold
        should_compress = (
            self._enable_auto_compress and
            content_size >= self._compression_threshold
        )
        
        original_size = content_size
        if should_compress:
            content, comp_meta = self._compression.compress(content)
            stats["compression"] = comp_meta
        
        stats["size_bytes"] = len(content)
        
        # Register dataset
        dataset = self._registry.register_dataset(
            name=name,
            description=description,
            market=market,
            source=source,
            source_uri=source_uri,
            symbols=symbols,
            format=format,
            owner=owner,
            team=team,
            tags=tags,
            time_range=time_range,
        )
        
        # Validate if enabled
        validation_result = None
        if validate or self._enable_auto_validate:
            validation_result = self._validator.validate(
                dataset_id=dataset.dataset_id,
                data=df,
                level=ValidationLevel.STANDARD,
            )
            
            self._registry.validate_dataset(
                dataset_id=dataset.dataset_id,
                validator=validation_result.validator,
                quality=validation_result.quality,
                missing_report=validation_result.missing_report,
                duplicate_report=validation_result.duplicate_report,
                errors=[e.message for e in validation_result.errors] if validation_result.errors else None,
            )
        
        # Compute integrity hash
        integrity_hash = ""
        if compute_hash:
            integrity_hash = self._integrity.register(
                dataset_id=dataset.dataset_id,
                content=content,
            )
            stats["integrity_hash"] = integrity_hash
        
        # Add version
        version = self._registry.add_dataset_version(
            dataset_id=dataset.dataset_id,
            content=content,
            change_summary="Initial ingestion",
            created_by=owner,
            statistics=stats,
        )
        
        # Register lineage
        self._lineage.record_dataset_created(
            dataset_id=dataset.dataset_id,
            source=source.value if isinstance(source, DataSource) else source,
            created_by=owner,
        )
        
        # Create snapshot
        if create_snapshot:
            self._snapshots.create_snapshot(
                dataset_id=dataset.dataset_id,
                version=version.version,
                content=content,
                content_hash=version.content_hash,
                created_by=owner,
            )
        
        # Register in metadata catalog
        self._catalog.register(
            entity_type="dataset",
            entity_id=dataset.dataset_id,
            name=name,
            metadata={
                **dataset.metadata.to_dict(),
                "statistics": stats,
            },
            tags=tags or [],
            owner=owner,
            team=team,
        )
        
        # Check archive eligibility
        if self._enable_auto_archive:
            self._archiver.archive_dataset(
                dataset_id=dataset.dataset_id,
                dataset_name=name,
                source_path=dataset.metadata.storage_path,
                created_at=dataset.metadata.created_at,
            )
        
        ingestion_metadata = {
            "dataset_id": dataset.dataset_id,
            "version": version.version,
            "statistics": stats,
            "validation": validation_result.to_dict() if validation_result else None,
            "compressed": should_compress,
            "original_size": original_size,
            "stored_size": len(content),
        }
        
        logger.info(
            f"Ingested dataset {name} "
            f"(rows: {stats['row_count']}, size: {len(content)} bytes)"
        )
        
        return dataset, ingestion_metadata
    
    def read(
        self,
        dataset_id: str,
        version: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> Optional[Any]:
        """
        Read dataset content.
        
        Args:
            dataset_id: Dataset ID
            version: Specific version (latest if None)
            as_of: Read version as of this time
        """
        dataset = self._registry.get_dataset(dataset_id)
        if not dataset:
            return None
        
        # Get version
        if as_of:
            ver = self._versioning.get_version_at(dataset_id, as_of)
        elif version:
            ver = self._versioning.get_dataset_versions(dataset_id)
            ver = next((v for v in ver if v.version == version), None)
        else:
            ver = self._versioning.get_current_version(dataset_id)
        
        if not ver:
            return None
        
        # Get content
        content = self._versioning.get_version_content(ver.version_id)
        if not content:
            return None
        
        # Decompress if needed
        if dataset.metadata.compressed_size_bytes < dataset.metadata.file_size_bytes:
            try:
                content = self._compression.decompress(content, self._compression._default_algorithm)
            except Exception:
                pass
        
        # Deserialize
        return self._deserialize(content, dataset.metadata.format)
    
    def _serialize(self, df: Any, format: DataFormat) -> bytes:
        """Serialize data to bytes"""
        buffer = io.BytesIO()
        self._formats.write(df, buffer, format.value)
        return buffer.getvalue()
    
    def _deserialize(self, content: bytes, format: DataFormat) -> Any:
        """Deserialize bytes to data"""
        return self._formats.read(io.BytesIO(content), format=format.value)
    
    # ==================== Validation ====================
    
    def validate_dataset(
        self,
        dataset_id: str,
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> Any:
        """Validate a dataset"""
        dataset = self._registry.get_dataset(dataset_id)
        if not dataset:
            return None
        
        # Get content
        content = self._read_raw_content(dataset_id)
        if content is None:
            return None
        
        # Read data
        df = self._deserialize(content, dataset.metadata.format)
        
        # Validate
        result = self._validator.validate(
            dataset_id=dataset_id,
            data=df,
            level=level,
        )
        
        # Update registry
        self._registry.validate_dataset(
            dataset_id=dataset_id,
            validator=result.validator,
            quality=result.quality,
            missing_report=result.missing_report,
            duplicate_report=result.duplicate_report,
            errors=[e.message for e in result.errors] if result.errors else None,
        )
        
        return result
    
    def _read_raw_content(self, dataset_id: str) -> Optional[bytes]:
        """Read raw dataset content"""
        ver = self._versioning.get_current_version(dataset_id)
        if not ver:
            return None
        return self._versioning.get_version_content(ver.version_id)
    
    # ==================== Query Operations ====================
    
    def search_datasets(
        self,
        query: Optional[str] = None,
        market: Optional[str] = None,
        source: Optional[DataSource] = None,
        validated_only: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Search for datasets"""
        return self._registry.list_datasets(
            validated_only=validated_only,
        )
    
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        return self._registry.get_dataset(dataset_id)
    
    def require_validated(self, dataset_id: str) -> Dataset:
        """
        Get a dataset, raising an error if not validated.
        
        Every experiment must reference immutable dataset versions.
        """
        return self._registry.require_validated(dataset_id)
    
    # ==================== Feature Operations ====================
    
    def register_feature(
        self,
        name: str,
        description: str,
        feature_type: str = "derived",
        dependencies: Optional[List[str]] = None,
        **kwargs,
    ) -> Tuple[Any, bool]:
        """Register a feature in the feature store"""
        from data_platform.models.feature import FeatureType
        
        ft = FeatureType(feature_type)
        feature, is_new = self._feature_store.register_feature(
            name=name,
            description=description,
            feature_type=ft,
            dependencies=dependencies,
            **kwargs,
        )
        
        # Record lineage
        self._lineage.record_feature_created(
            feature_id=feature.feature_id,
            dependencies=dependencies,
            created_by=kwargs.get("owner", ""),
        )
        
        # Register in catalog
        self._catalog.register(
            entity_type="feature",
            entity_id=feature.feature_id,
            name=name,
            metadata=feature.metadata.to_dict(),
            tags=kwargs.get("tags", []),
            owner=kwargs.get("owner", ""),
            team=kwargs.get("team", ""),
        )
        
        return feature, is_new
    
    # ==================== Schema Operations ====================
    
    def register_schema(
        self,
        name: str,
        fields: List[Dict[str, Any]],
        **kwargs,
    ) -> Any:
        """Register a schema"""
        # Create or get registry
        registry = self._schema_registry.create_registry(
            name=f"{name}_registry",
            domain=kwargs.get("domain", "trading"),
        )
        
        # Create schema
        schema = self._schema_registry.create_schema(
            registry_id=registry.schema_id,
            name=name,
            fields=fields,
            **kwargs,
        )
        
        return schema
    
    def validate_against_schema(
        self,
        registry_id: str,
        data: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate data against a schema"""
        return self._schema_registry.validate_data(registry_id, data)
    
    # ==================== Lineage Operations ====================
    
    def record_transformation(
        self,
        input_dataset_ids: List[str],
        output_dataset_id: str,
        transformation_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a data transformation"""
        self._lineage.record_transformation(
            transformation_id=f"transform_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            input_dataset_ids=input_dataset_ids,
            output_dataset_id=output_dataset_id,
            transformation_type=transformation_type,
            parameters=parameters,
        )
    
    def get_lineage(self, dataset_id: str) -> Dict[str, Any]:
        """Get data lineage for a dataset"""
        return self._lineage.get_data_lineage(dataset_id)
    
    # ==================== Versioning Operations ====================
    
    def create_version(
        self,
        dataset_id: str,
        content: bytes,
        change_summary: str = "",
    ) -> Any:
        """Create a new version of a dataset"""
        dataset = self._registry.get_dataset(dataset_id)
        if not dataset:
            return None
        
        version = self._versioning.create_version(
            dataset_id=dataset_id,
            content=content,
            version=f"{len(dataset.versions) + 1}.0",
            change_summary=change_summary,
        )
        
        # Update integrity
        self._integrity.update_hash(dataset_id, content)
        
        return version
    
    def get_version_history(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get version history for a dataset"""
        versions = self._versioning.get_dataset_versions(dataset_id)
        return [v.to_dict() for v in versions]
    
    # ==================== Maintenance Operations ====================
    
    def verify_integrity(self, dataset_id: str) -> Any:
        """Verify dataset integrity"""
        content = self._read_raw_content(dataset_id)
        if content is None:
            return None
        
        return self._integrity.verify(dataset_id, content)
    
    def run_integrity_checks(self) -> List[Any]:
        """Run pending integrity checks"""
        pending = self._integrity.get_pending_checks()
        results = []
        
        for dataset_id, last_check in pending:
            result = self.verify_integrity(dataset_id)
            if result:
                results.append(result)
        
        return results
    
    def cleanup_expired_snapshots(self) -> int:
        """Clean up expired snapshots"""
        return self._snapshots.cleanup_expired()
    
    def process_archives(self) -> int:
        """Process scheduled archives"""
        return self._archiver.process_deletions()
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive data lake statistics"""
        return {
            "registry": self._registry.get_statistics(),
            "features": self._feature_store.get_statistics(),
            "schemas": self._schema_registry.get_statistics(),
            "catalog": self._catalog.get_statistics(),
            "versioning": self._versioning.get_statistics(),
            "lineage": self._lineage.get_statistics(),
            "snapshots": self._snapshots.get_statistics(),
            "compression": self._compression.get_statistics(),
            "archiver": self._archiver.get_statistics(),
            "integrity": self._integrity.get_statistics(),
            "validation": self._validator.get_statistics(),
        }
    
    # ==================== Accessors ====================
    
    @property
    def registry(self) -> DatasetRegistry:
        """Get dataset registry"""
        return self._registry
    
    @property
    def features(self) -> FeatureStore:
        """Get feature store"""
        return self._feature_store
    
    @property
    def schemas(self) -> SchemaRegistryManager:
        """Get schema registry"""
        return self._schema_registry
    
    @property
    def catalog(self) -> MetadataCatalog:
        """Get metadata catalog"""
        return self._catalog
    
    @property
    def lineage(self) -> LineageTracker:
        """Get lineage tracker"""
        return self._lineage
    
    @property
    def versioning(self) -> DataVersioningManager:
        """Get versioning manager"""
        return self._versioning
    
    @property
    def snapshots(self) -> SnapshotManager:
        """Get snapshot manager"""
        return self._snapshots
    
    @property
    def integrity(self) -> IntegrityVerifier:
        """Get integrity verifier"""
        return self._integrity
    
    @property
    def formats(self) -> FormatManager:
        """Get format manager"""
        return self._formats
