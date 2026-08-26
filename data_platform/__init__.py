"""
Data Platform

Enterprise Data Platform for SmartPip Trading System.

Features:
- Data Lake
- Feature Store
- Dataset Registry
- Schema Registry
- Metadata Catalog
- Data Versioning
- Data Lineage
- Feature Lineage
- Historical Snapshots
- Compression
- Automatic Archiving
- Automatic Integrity Verification
"""

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
    DatasetMetadata,
    DatasetVersion,
    DataFormat,
    DataSource,
    DataQuality,
    MissingDataReport,
    DuplicateReport,
)
from data_platform.models.feature import (
    Feature,
    FeatureMetadata,
    FeatureVersion,
    FeatureType,
    FeatureImportance,
)
from data_platform.models.schema import (
    Schema,
    SchemaField,
    SchemaRegistry,
    FieldType,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "DataLake",
    "DatasetRegistry",
    "FeatureStore",
    "SchemaRegistryManager",
    "MetadataCatalog",
    "DataVersioningManager",
    "LineageTracker",
    "SnapshotManager",
    "CompressionManager",
    "Archiver",
    "IntegrityVerifier",
    "DatasetValidator",
    "ValidationLevel",
    "FormatManager",
    
    # Models
    "Dataset",
    "DatasetMetadata",
    "DatasetVersion",
    "DataFormat",
    "DataSource",
    "DataQuality",
    "MissingDataReport",
    "DuplicateReport",
    "Feature",
    "FeatureMetadata",
    "FeatureVersion",
    "FeatureType",
    "FeatureImportance",
    "Schema",
    "SchemaField",
    "SchemaRegistry",
    "FieldType",
]
