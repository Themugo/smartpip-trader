"""
Data Platform Core

Core modules for the SmartPip Data Platform.
"""

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
from data_platform.core.validation import DatasetValidator
from data_platform.core.formats import FormatHandler
from data_platform.core.data_lake import DataLake

__all__ = [
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
    "FormatHandler",
    "DataLake",
]
