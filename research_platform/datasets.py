"""
Dataset Manager - Data Catalog and Lineage

Complete dataset management with:
- Dataset catalog
- Metadata
- Versioning
- Validation
- Lineage tracking
"""

import json
import logging
import uuid
import hashlib
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Dataset data types"""
    OHLCV = "ohlcv"  # Open, High, Low, Close, Volume
    TICK = "tick"  # Tick data
    ORDERBOOK = "orderbook"  # Order book data
    TRADE = "trade"  # Trade data
    SIGNAL = "signal"  # Signal data
    FEATURE = "feature"  # Feature matrix
    CUSTOM = "custom"


class DatasetStatus(Enum):
    """Dataset status"""
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ValidationLevel(Enum):
    """Data validation levels"""
    NONE = "none"
    BASIC = "basic"  # Schema validation
    STANDARD = "standard"  # Schema + basic statistics
    COMPREHENSIVE = "comprehensive"  # Schema + statistics + outliers


@dataclass
class DataSchema:
    """Schema definition for a dataset"""
    columns: List[str] = field(default_factory=list)
    dtypes: Dict[str, str] = field(default_factory=dict)  # column -> dtype
    nullable: Dict[str, bool] = field(default_factory=dict)
    primary_key: Optional[str] = None
    indexes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "dtypes": self.dtypes,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "indexes": self.indexes,
        }


@dataclass
class DataStatistics:
    """Dataset statistics"""
    row_count: int = 0
    column_count: int = 0
    
    # Numeric columns
    numeric_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Categorical columns
    categorical_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Missing data
    missing_counts: Dict[str, int] = field(default_factory=dict)
    missing_percentages: Dict[str, float] = field(default_factory=dict)
    
    # Uniqueness
    unique_counts: Dict[str, int] = field(default_factory=dict)
    
    # Computed at
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        stats = {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "numeric_stats": self.numeric_stats,
            "categorical_stats": self.categorical_stats,
            "missing_counts": self.missing_counts,
            "missing_percentages": self.missing_percentages,
            "unique_counts": self.unique_counts,
            "computed_at": self.computed_at.isoformat(),
        }
        return stats


@dataclass
class DataQualityReport:
    """Data quality validation report"""
    is_valid: bool = True
    score: float = 100.0  # 0-100
    
    # Issues
    schema_errors: List[str] = field(default_factory=list)
    data_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Quality metrics
    completeness: float = 100.0  # Percentage of non-null values
    accuracy: float = 100.0  # Data accuracy score
    consistency: float = 100.0  # Consistency across time periods
    timeliness: float = 100.0  # Data freshness
    
    # Validation details
    validated_rows: int = 0
    invalid_rows: int = 0
    outlier_count: int = 0
    
    # Computed at
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "schema_errors": self.schema_errors,
            "data_errors": self.data_errors,
            "warnings": self.warnings,
            "completeness": self.completeness,
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "timeliness": self.timeliness,
            "validated_rows": self.validated_rows,
            "invalid_rows": self.invalid_rows,
            "outlier_count": self.outlier_count,
            "validated_at": self.validated_at.isoformat(),
        }


@dataclass
class DataLineageNode:
    """A node in the data lineage graph"""
    node_id: str
    node_type: str  # "dataset", "feature", "model", "notebook"
    name: str
    version: str
    operation: Optional[str] = None  # "created", "transformed", "aggregated"
    
    # Connections
    parents: List[str] = field(default_factory=list)  # Node IDs
    children: List[str] = field(default_factory=list)  # Node IDs
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "version": self.version,
            "operation": self.operation,
            "parents": self.parents,
            "children": self.children,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata,
        }


@dataclass
class DataLineage:
    """Data lineage tracking"""
    graph: Dict[str, DataLineageNode] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.graph.items()},
        }
    
    def add_node(self, node: DataLineageNode) -> None:
        self.graph[node.node_id] = node
    
    def add_edge(self, parent_id: str, child_id: str) -> bool:
        """Add an edge between nodes"""
        if parent_id not in self.graph or child_id not in self.graph:
            return False
        
        if parent_id not in self.graph[child_id].parents:
            self.graph[child_id].parents.append(parent_id)
        if child_id not in self.graph[parent_id].children:
            self.graph[parent_id].children.append(child_id)
        return True
    
    def get_ancestors(self, node_id: str, max_depth: int = 10) -> List[str]:
        """Get all ancestor nodes"""
        ancestors = []
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            
            node = self.graph.get(current)
            if not node:
                continue
            
            for parent_id in node.parents:
                if parent_id not in visited:
                    visited.add(parent_id)
                    ancestors.append(parent_id)
                    queue.append((parent_id, depth + 1))
        
        return ancestors
    
    def get_descendants(self, node_id: str, max_depth: int = 10) -> List[str]:
        """Get all descendant nodes"""
        descendants = []
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            
            node = self.graph.get(current)
            if not node:
                continue
            
            for child_id in node.children:
                if child_id not in visited:
                    visited.add(child_id)
                    descendants.append(child_id)
                    queue.append((child_id, depth + 1))
        
        return descendants


@dataclass
class DatasetVersion:
    """A version of a dataset"""
    version: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    
    # Data info
    row_count: int = 0
    size_bytes: int = 0
    checksum: str = ""
    
    # Changes
    changelog: str = ""
    previous_version: Optional[str] = None
    
    # Statistics
    statistics: Optional[DataStatistics] = None
    quality_report: Optional[DataQualityReport] = None
    
    # Storage
    storage_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "changelog": self.changelog,
            "previous_version": self.previous_version,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "quality_report": self.quality_report.to_dict() if self.quality_report else None,
            "storage_path": self.storage_path,
        }


@dataclass
class DatasetMetadata:
    """Dataset metadata"""
    id: str
    name: str
    description: str
    
    # Classification
    data_type: DataType
    asset_class: str = ""  # e.g., "forex", "crypto", "equity"
    symbol: str = ""  # e.g., "EUR/USD", "BTC/USD"
    timeframe: str = ""  # e.g., "1m", "5m", "1h", "1d"
    
    # Temporal coverage
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_live: bool = False
    
    # Schema
    schema: DataSchema = field(default_factory=DataSchema)
    
    # Status
    status: DatasetStatus = DatasetStatus.DRAFT
    
    # Versions
    current_version: str = "1.0.0"
    versions: Dict[str, DatasetVersion] = field(default_factory=dict)
    
    # Statistics
    latest_statistics: Optional[DataStatistics] = None
    latest_quality_report: Optional[DataQualityReport] = None
    
    # Lineage
    lineage: DataLineage = field(default_factory=DataLineage)
    
    # Metadata
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = ""  # Data source
    license: str = ""  # Data license
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Access
    is_public: bool = False
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type.value,
            "asset_class": self.asset_class,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_live": self.is_live,
            "schema": self.schema.to_dict(),
            "status": self.status.value,
            "current_version": self.current_version,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "latest_statistics": self.latest_statistics.to_dict() if self.latest_statistics else None,
            "latest_quality_report": self.latest_quality_report.to_dict() if self.latest_quality_report else None,
            "lineage": self.lineage.to_dict(),
            "owner": self.owner,
            "tags": self.tags,
            "source": self.source,
            "license": self.license,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_public": self.is_public,
            "access_count": self.access_count,
        }


@dataclass
class Dataset:
    """A registered dataset"""
    metadata: DatasetMetadata
    
    # Current data (in-memory or reference)
    data: Optional[pd.DataFrame] = None
    data_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = self.metadata.to_dict()
        d["has_data"] = self.data is not None
        d["data_path"] = self.data_path
        return d


class DatasetManager:
    """
    Dataset Manager for data catalog and lineage tracking.
    
    Features:
    - Dataset registration and cataloging
    - Version control for datasets
    - Data validation and quality checks
    - Lineage tracking
    - Schema management
    - Metadata management
    """
    
    def __init__(self, storage_path: str = "data/datasets"):
        self._storage_path = storage_path
        self._datasets: Dict[str, Dataset] = {}
        self._index: Dict[str, List[str]] = defaultdict(list)  # tag -> dataset IDs
        self._lineage_graphs: Dict[str, DataLineage] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_catalog()
    
    def _load_catalog(self) -> None:
        """Load dataset catalog"""
        catalog_file = f"{self._storage_path}/catalog.json"
        
        try:
            if os.path.exists(catalog_file):
                with open(catalog_file, "r") as f:
                    data = json.load(f)
                
                for ds_data in data.get("datasets", []):
                    # Parse metadata
                    meta = self._parse_metadata(ds_data)
                    dataset = Dataset(metadata=meta)
                    self._datasets[dataset.metadata.id] = dataset
                    
                    # Build index
                    for tag in meta.tags:
                        self._index[tag].append(meta.id)
                
                logger.info(f"Loaded {len(self._datasets)} datasets from catalog")
        except Exception as e:
            logger.warning(f"Could not load catalog: {e}")
    
    def _parse_metadata(self, data: Dict[str, Any]) -> DatasetMetadata:
        """Parse dataset metadata from dict"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        if data.get("start_date"):
            data["start_date"] = datetime.fromisoformat(data["start_date"])
        if data.get("end_date"):
            data["end_date"] = datetime.fromisoformat(data["end_date"])
        
        # Parse schema
        if "schema" in data:
            data["schema"] = DataSchema(**data["schema"])
        
        # Parse versions
        if "versions" in data:
            for v in data["versions"].values():
                v["created_at"] = datetime.fromisoformat(v["created_at"])
                if v.get("statistics"):
                    v["statistics"]["computed_at"] = datetime.fromisoformat(v["statistics"]["computed_at"])
                    v["statistics"] = DataStatistics(**v["statistics"])
                if v.get("quality_report"):
                    v["quality_report"]["validated_at"] = datetime.fromisoformat(v["quality_report"]["validated_at"])
                    v["quality_report"] = DataQualityReport(**v["quality_report"])
            data["versions"] = {k: DatasetVersion(**v) for k, v in data["versions"].items()}
        
        # Parse lineage
        if "lineage" in data:
            lineage = DataLineage()
            for node_data in data.get("lineage", {}).get("nodes", {}).values():
                node_data["created_at"] = datetime.fromisoformat(node_data["created_at"])
                lineage.add_node(DataLineageNode(**node_data))
            data["lineage"] = lineage
        
        return DatasetMetadata(**data)
    
    def _save_catalog(self) -> None:
        """Save dataset catalog"""
        catalog_file = f"{self._storage_path}/catalog.json"
        
        # Rebuild index
        self._index.clear()
        for ds in self._datasets.values():
            for tag in ds.metadata.tags:
                self._index[tag].append(ds.metadata.id)
        
        data = {
            "datasets": [ds.metadata.to_dict() for ds in self._datasets.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(catalog_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Dataset Registration
    def register_dataset(
        self,
        name: str,
        description: str,
        data_type: DataType,
        schema: DataSchema,
        owner: str = "",
        tags: Optional[List[str]] = None,
        asset_class: str = "",
        symbol: str = "",
        timeframe: str = "",
        source: str = "",
    ) -> Dataset:
        """Register a new dataset"""
        metadata = DatasetMetadata(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            data_type=data_type,
            schema=schema,
            owner=owner,
            tags=tags or [],
            asset_class=asset_class,
            symbol=symbol,
            timeframe=timeframe,
            source=source,
            lineage=DataLineage(),
        )
        
        dataset = Dataset(metadata=metadata)
        self._datasets[dataset.metadata.id] = dataset
        
        # Add to lineage
        root_node = DataLineageNode(
            node_id=dataset.metadata.id,
            node_type="dataset",
            name=name,
            version="1.0.0",
            operation="created",
            created_by=owner,
        )
        dataset.metadata.lineage.add_node(root_node)
        
        self._save_catalog()
        logger.info(f"Registered dataset: {name}")
        
        return dataset
    
    def load_data(
        self,
        dataset_id: str,
        data: pd.DataFrame,
        created_by: str = "",
    ) -> bool:
        """Load data into a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        dataset.data = data
        dataset.data_path = None
        
        # Update statistics
        dataset.metadata.latest_statistics = self._compute_statistics(data)
        
        # Update temporal coverage
        if "timestamp" in data.columns:
            dataset.metadata.start_date = pd.to_datetime(data["timestamp"]).min()
            dataset.metadata.end_date = pd.to_datetime(data["timestamp"]).max()
        
        dataset.metadata.updated_at = datetime.now(timezone.utc)
        self._save_catalog()
        
        return True
    
    def load_from_file(
        self,
        dataset_id: str,
        file_path: str,
        file_format: str = "parquet",
        created_by: str = "",
    ) -> bool:
        """Load data from file"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        try:
            if file_format == "parquet":
                data = pd.read_parquet(file_path)
            elif file_format == "csv":
                data = pd.read_csv(file_path)
            elif file_format == "json":
                data = pd.read_json(file_path)
            else:
                return False
            
            dataset.data = data
            dataset.data_path = file_path
            
            # Update statistics
            dataset.metadata.latest_statistics = self._compute_statistics(data)
            
            # Update temporal coverage
            if "timestamp" in data.columns:
                dataset.metadata.start_date = pd.to_datetime(data["timestamp"]).min()
                dataset.metadata.end_date = pd.to_datetime(data["timestamp"]).max()
            
            dataset.metadata.updated_at = datetime.now(timezone.utc)
            self._save_catalog()
            
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def _compute_statistics(self, data: pd.DataFrame) -> DataStatistics:
        """Compute dataset statistics"""
        stats = DataStatistics(
            row_count=len(data),
            column_count=len(data.columns),
        )
        
        # Numeric columns
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_data = data[col].dropna()
            if len(col_data) > 0:
                stats.numeric_stats[col] = {
                    "mean": float(col_data.mean()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "median": float(col_data.median()),
                    "q25": float(col_data.quantile(0.25)),
                    "q75": float(col_data.quantile(0.75)),
                }
        
        # Categorical columns
        cat_cols = data.select_dtypes(include=["object", "category"]).columns
        for col in cat_cols:
            unique_vals = data[col].dropna().unique()
            stats.categorical_stats[col] = {
                "unique_count": len(unique_vals),
                "top_values": data[col].value_counts().head(5).to_dict(),
            }
        
        # Missing data
        for col in data.columns:
            missing = data[col].isna().sum()
            stats.missing_counts[col] = int(missing)
            stats.missing_percentages[col] = float(missing / len(data) * 100)
        
        # Uniqueness
        for col in data.columns:
            stats.unique_counts[col] = int(data[col].nunique())
        
        return stats
    
    # Version Management
    def create_version(
        self,
        dataset_id: str,
        version: str,
        changelog: str = "",
        created_by: str = "",
    ) -> Optional[DatasetVersion]:
        """Create a new version of a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        if version in dataset.metadata.versions:
            logger.warning(f"Version {version} already exists")
            return None
        
        # Compute version info
        row_count = len(dataset.data) if dataset.data is not None else 0
        checksum = ""
        if dataset.data is not None:
            checksum = hashlib.md5(pd.util.hash_pandas_object(dataset.data).values).hexdigest()
        
        version_obj = DatasetVersion(
            version=version,
            created_by=created_by,
            row_count=row_count,
            checksum=checksum,
            changelog=changelog,
            previous_version=dataset.metadata.current_version,
            statistics=dataset.metadata.latest_statistics,
            quality_report=dataset.metadata.latest_quality_report,
        )
        
        dataset.metadata.versions[version] = version_obj
        dataset.metadata.current_version = version
        dataset.metadata.updated_at = datetime.now(timezone.utc)
        
        self._save_catalog()
        return version_obj
    
    def get_version(self, dataset_id: str, version: str) -> Optional[DatasetVersion]:
        """Get a specific version"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        return dataset.metadata.versions.get(version)
    
    def list_versions(self, dataset_id: str) -> List[DatasetVersion]:
        """List all versions"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return []
        return sorted(
            dataset.metadata.versions.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )
    
    # Data Validation
    def validate_dataset(
        self,
        dataset_id: str,
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> DataQualityReport:
        """Validate a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset or dataset.data is None:
            return DataQualityReport(is_valid=False, score=0.0)
        
        report = DataQualityReport()
        report.validated_rows = len(dataset.data)
        
        # Schema validation
        if level != ValidationLevel.NONE:
            schema_errors = self._validate_schema(dataset.data, dataset.metadata.schema)
            report.schema_errors = schema_errors
            if schema_errors:
                report.is_valid = False
        
        # Data quality checks
        if level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE]:
            # Check for duplicates
            duplicates = dataset.data.duplicated().sum()
            if duplicates > 0:
                report.warnings.append(f"Found {duplicates} duplicate rows")
                report.score -= 5
            
            # Check for missing data
            total_missing = sum(report.validated_rows * dataset.data[col].isna().sum() 
                              for col in dataset.data.columns) / (len(dataset.data.columns) * report.validated_rows)
            report.completeness = (1 - total_missing) * 100
            if report.completeness < 95:
                report.warnings.append(f"Missing data: {100 - report.completeness:.1f}%")
                report.score -= (100 - report.completeness)
        
        # Comprehensive checks
        if level == ValidationLevel.COMPREHENSIVE:
            # Outlier detection using IQR
            for col in dataset.data.select_dtypes(include=[np.number]).columns:
                q1 = dataset.data[col].quantile(0.25)
                q3 = dataset.data[col].quantile(0.75)
                iqr = q3 - q1
                outliers = ((dataset.data[col] < q1 - 3*iqr) | (dataset.data[col] > q3 + 3*iqr)).sum()
                report.outlier_count += int(outliers)
            
            if report.outlier_count > 0:
                report.warnings.append(f"Found {report.outlier_count} outliers")
                report.score -= min(20, report.outlier_count * 0.1)
        
        report.score = max(0, min(100, report.score))
        report.is_valid = report.is_valid and report.score >= 70
        
        # Store report
        dataset.metadata.latest_quality_report = report
        self._save_catalog()
        
        return report
    
    def _validate_schema(
        self,
        data: pd.DataFrame,
        schema: DataSchema,
    ) -> List[str]:
        """Validate data against schema"""
        errors = []
        
        # Check columns
        missing_cols = set(schema.columns) - set(data.columns)
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
        
        extra_cols = set(data.columns) - set(schema.columns)
        if extra_cols:
            errors.append(f"Extra columns: {extra_cols}")
        
        # Check data types
        for col, expected_dtype in schema.dtypes.items():
            if col in data.columns:
                actual_dtype = str(data[col].dtype)
                if expected_dtype not in actual_dtype and actual_dtype not in expected_dtype:
                    errors.append(f"Column '{col}' has wrong dtype: expected {expected_dtype}, got {actual_dtype}")
        
        return errors
    
    # Lineage Tracking
    def add_lineage_node(
        self,
        dataset_id: str,
        node_type: str,
        name: str,
        version: str,
        operation: str,
        created_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Add a node to the lineage graph"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        node_id = str(uuid.uuid4())
        node = DataLineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            version=version,
            operation=operation,
            created_by=created_by,
            metadata=metadata or {},
        )
        
        # Link to parent (root dataset)
        if dataset.metadata.lineage.graph:
            root_id = list(dataset.metadata.lineage.graph.keys())[0]
            dataset.metadata.lineage.add_edge(root_id, node_id)
        
        dataset.metadata.lineage.add_node(node)
        self._save_catalog()
        
        return node_id
    
    def link_lineage(
        self,
        dataset_id: str,
        parent_id: str,
        child_id: str,
    ) -> bool:
        """Link two lineage nodes"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False
        
        return dataset.metadata.lineage.add_edge(parent_id, child_id)
    
    def get_lineage(self, dataset_id: str) -> Optional[DataLineage]:
        """Get lineage graph for a dataset"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        return dataset.metadata.lineage
    
    def get_upstream_datasets(self, dataset_id: str) -> List[str]:
        """Get all upstream datasets in lineage"""
        dataset = self._datasets.get(dataset_id)
        if not dataset or not dataset.metadata.lineage.graph:
            return []
        
        root_id = list(dataset.metadata.lineage.graph.keys())[0]
        return dataset.metadata.lineage.get_ancestors(root_id)
    
    def get_downstream_dependencies(self, dataset_id: str) -> List[str]:
        """Get all downstream dependencies in lineage"""
        dataset = self._datasets.get(dataset_id)
        if not dataset or not dataset.metadata.lineage.graph:
            return []
        
        root_id = list(dataset.metadata.lineage.graph.keys())[0]
        return dataset.metadata.lineage.get_descendants(root_id)
    
    # Search and Retrieval
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID"""
        ds = self._datasets.get(dataset_id)
        if ds:
            ds.metadata.access_count += 1
        return ds
    
    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        data_type: Optional[DataType] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        status: Optional[DatasetStatus] = None,
        owner: Optional[str] = None,
        min_rows: Optional[int] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 50,
    ) -> List[Dataset]:
        """Search datasets"""
        results = list(self._datasets.values())
        
        if query:
            query_lower = query.lower()
            results = [
                ds for ds in results
                if query_lower in ds.metadata.name.lower()
                or query_lower in ds.metadata.description.lower()
            ]
        
        if tags:
            results = [ds for ds in results if any(t in ds.metadata.tags for t in tags)]
        
        if data_type:
            results = [ds for ds in results if ds.metadata.data_type == data_type]
        
        if symbol:
            results = [ds for ds in results if ds.metadata.symbol == symbol]
        
        if timeframe:
            results = [ds for ds in results if ds.metadata.timeframe == timeframe]
        
        if status:
            results = [ds for ds in results if ds.metadata.status == status]
        
        if owner:
            results = [ds for ds in results if owner.lower() in ds.metadata.owner.lower()]
        
        if min_rows is not None:
            if ds.metadata.latest_statistics:
                results = [ds for ds in results 
                          if ds.metadata.latest_statistics.row_count >= min_rows]
        
        if date_range:
            start, end = date_range
            results = [ds for ds in results
                      if ds.metadata.start_date and ds.metadata.end_date
                      and ds.metadata.start_date <= end
                      and ds.metadata.end_date >= start]
        
        # Sort by access count and name
        results.sort(key=lambda ds: (ds.metadata.access_count, ds.metadata.name), reverse=True)
        return results[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        datasets = list(self._datasets.values())
        
        total_rows = sum(
            ds.metadata.latest_statistics.row_count
            for ds in datasets
            if ds.metadata.latest_statistics
        )
        
        return {
            "total_datasets": len(datasets),
            "total_rows": total_rows,
            "by_type": {
                dtype.value: sum(1 for ds in datasets if ds.metadata.data_type == dtype)
                for dtype in DataType
            },
            "by_status": {
                status.value: sum(1 for ds in datasets if ds.metadata.status == status)
                for status in DatasetStatus
            },
            "total_versions": sum(len(ds.metadata.versions) for ds in datasets),
        }
    
    def export_dataset(self, dataset_id: str, format: str = "json") -> Optional[str]:
        """Export dataset metadata"""
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None
        
        return json.dumps(dataset.metadata.to_dict(), indent=2)


import os
