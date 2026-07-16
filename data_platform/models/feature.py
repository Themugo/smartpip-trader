"""
Feature Model

Feature model with versioning, dependencies, and metadata.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class FeatureImportance(Enum):
    """Feature importance levels"""
    CRITICAL = "critical"  # Must have, core feature
    HIGH = "high"  # Very important
    MEDIUM = "medium"  # Moderately important
    LOW = "low"  # Minor importance
    EXPERIMENTAL = "experimental"  # Testing/evaluation


class FeatureType(Enum):
    """Types of features"""
    RAW = "raw"  # Raw market data
    TECHNICAL = "technical"  # Technical indicators
    DERIVED = "derived"  # Derived/computed features
    AGGREGATED = "aggregated"  # Aggregated metrics
    LABEL = "label"  # Target labels
    METADATA = "metadata"  # Metadata features


@dataclass
class ValidationRecord:
    """Record of feature validation"""
    validation_id: str
    validated_at: datetime
    validator: str
    passed: bool
    tests_run: List[str]
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "validated_at": self.validated_at.isoformat() if isinstance(self.validated_at, datetime) else self.validated_at,
            "validator": self.validator,
            "passed": self.passed,
            "tests_run": self.tests_run,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


@dataclass
class UsageRecord:
    """Record of feature usage"""
    used_at: datetime
    used_by: str  # Experiment/model ID
    use_case: str  # training, inference, backtest
    dataset_id: str
    performance_impact: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "used_at": self.used_at.isoformat() if isinstance(self.used_at, datetime) else self.used_at,
            "used_by": self.used_by,
            "use_case": self.use_case,
            "dataset_id": self.dataset_id,
            "performance_impact": self.performance_impact,
        }


@dataclass
class FeatureMetadata:
    """Complete feature metadata"""
    feature_id: str
    name: str
    description: str
    version: str
    
    # Classification
    feature_type: FeatureType = FeatureType.DERIVED
    importance: FeatureImportance = FeatureImportance.MEDIUM
    
    # Versioning
    version_major: int = 1
    version_minor: int = 0
    version_patch: int = 0
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Feature IDs this depends on
    dependents: List[str] = field(default_factory=list)  # Features that depend on this
    source_columns: List[str] = field(default_factory=list)
    
    # Computation
    computation_cost: float = 0.0  # Relative cost (0-1)
    computation_function: str = ""
    is_computed: bool = True
    
    # Data characteristics
    data_type: str = "float"  # float, int, bool, string
    nullable: bool = True
    value_range: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    null_percentage: float = 0.0
    unique_count: int = 0
    mean: Optional[float] = None
    std: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    # Importance metrics
    feature_importance_score: Optional[float] = None
    correlation_with_target: Optional[float] = None
    mutual_information: Optional[float] = None
    
    # History
    usage_history: List[UsageRecord] = field(default_factory=list)
    validation_history: List[ValidationRecord] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deprecated_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    is_deprecated: bool = False
    is_experimental: bool = False
    
    # Tags
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Access
    owner: str = ""
    team: str = ""
    
    # Lineage
    lineage_level: int = 0  # 0 = raw, 1+ = derived
    source_dataset_id: Optional[str] = None
    
    # Deduplication
    signature: str = ""  # Hash of computation to detect duplicates
    
    def compute_signature(self) -> str:
        """Compute deduplication signature"""
        sig_data = {
            "name": self.name,
            "type": self.feature_type.value,
            "dependencies": sorted(self.dependencies),
            "source_columns": sorted(self.source_columns),
            "computation_function": self.computation_function,
        }
        self.signature = hashlib.sha256(
            str(sig_data).encode()
        ).hexdigest()[:16]
        return self.signature
    
    def add_usage(self, used_by: str, use_case: str, dataset_id: str) -> UsageRecord:
        """Record feature usage"""
        record = UsageRecord(
            used_at=datetime.utcnow(),
            used_by=used_by,
            use_case=use_case,
            dataset_id=dataset_id,
        )
        self.usage_history.append(record)
        return record
    
    def add_validation(
        self,
        validator: str,
        passed: bool,
        tests_run: List[str],
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> ValidationRecord:
        """Record feature validation"""
        record = ValidationRecord(
            validation_id=str(uuid.uuid4()),
            validated_at=datetime.utcnow(),
            validator=validator,
            passed=passed,
            tests_run=tests_run,
            errors=errors or [],
            warnings=warnings or [],
            metrics=metrics or {},
        )
        self.validation_history.append(record)
        return record
    
    def deprecate(self) -> None:
        """Mark feature as deprecated"""
        self.is_deprecated = True
        self.deprecated_at = datetime.utcnow()
        self.is_active = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "feature_type": self.feature_type.value if isinstance(self.feature_type, FeatureType) else self.feature_type,
            "importance": self.importance.value if isinstance(self.importance, FeatureImportance) else self.importance,
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "version_patch": self.version_patch,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "source_columns": self.source_columns,
            "computation_cost": self.computation_cost,
            "computation_function": self.computation_function,
            "is_computed": self.is_computed,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "value_range": self.value_range,
            "null_percentage": self.null_percentage,
            "unique_count": self.unique_count,
            "mean": self.mean,
            "std": self.std,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "feature_importance_score": self.feature_importance_score,
            "correlation_with_target": self.correlation_with_target,
            "mutual_information": self.mutual_information,
            "usage_history": [u.to_dict() for u in self.usage_history],
            "validation_history": [v.to_dict() for v in self.validation_history],
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "deprecated_at": self.deprecated_at.isoformat() if isinstance(self.deprecated_at, datetime) else self.deprecated_at,
            "is_active": self.is_active,
            "is_deprecated": self.is_deprecated,
            "is_experimental": self.is_experimental,
            "tags": self.tags,
            "labels": self.labels,
            "owner": self.owner,
            "team": self.team,
            "lineage_level": self.lineage_level,
            "source_dataset_id": self.source_dataset_id,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureMetadata":
        """Create from dictionary"""
        # Handle enums
        if "feature_type" in data and isinstance(data["feature_type"], str):
            data["feature_type"] = FeatureType(data["feature_type"])
        if "importance" in data and isinstance(data["importance"], str):
            data["importance"] = FeatureImportance(data["importance"])
        
        # Handle nested objects
        if "usage_history" in data:
            data["usage_history"] = [
                UsageRecord(**u) if isinstance(u, dict) else u
                for u in data["usage_history"]
            ]
        if "validation_history" in data:
            data["validation_history"] = [
                ValidationRecord(**v) if isinstance(v, dict) else v
                for v in data["validation_history"]
            ]
        
        return cls(**data)


@dataclass
class FeatureVersion:
    """A specific version of a feature"""
    version_id: str
    feature_id: str
    version: str
    
    # Version info
    version_major: int
    version_minor: int
    version_patch: int
    
    # Content
    content_hash: str
    code_hash: str
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Status
    is_current: bool = True
    is_stable: bool = False
    is_frozen: bool = False
    
    # Changes
    change_summary: str = ""
    breaking_change: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "feature_id": self.feature_id,
            "version": self.version,
            "version_major": self.version_major,
            "version_minor": self.version_minor,
            "version_patch": self.version_patch,
            "content_hash": self.content_hash,
            "code_hash": self.code_hash,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "created_by": self.created_by,
            "is_current": self.is_current,
            "is_stable": self.is_stable,
            "is_frozen": self.is_frozen,
            "change_summary": self.change_summary,
            "breaking_change": self.breaking_change,
        }


class Feature:
    """
    Main Feature class with versioning and deduplication.
    
    Every feature includes:
    - Description
    - Dependencies
    - Importance
    - Usage History
    - Computation Cost
    - Validation History
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        feature_type: FeatureType = FeatureType.DERIVED,
        owner: str = "",
        team: str = "",
    ):
        self.metadata = FeatureMetadata(
            feature_id=str(uuid.uuid4()),
            name=name,
            description=description,
            version="1.0.0",
            feature_type=feature_type,
            owner=owner,
            team=team,
        )
        self.versions: List[FeatureVersion] = []
        self._current_version: Optional[FeatureVersion] = None
        self._dependencies_graph: Dict[str, Set[str]] = {}  # feature_id -> dependencies
    
    @property
    def feature_id(self) -> str:
        return self.metadata.feature_id
    
    @property
    def signature(self) -> str:
        return self.metadata.signature
    
    @property
    def is_duplicate(self) -> bool:
        return bool(self.metadata.signature)
    
    def add_dependency(self, dependency_id: str) -> None:
        """Add a dependency to this feature"""
        if dependency_id not in self.metadata.dependencies:
            self.metadata.dependencies.append(dependency_id)
            self.metadata.lineage_level = max(
                self.metadata.lineage_level,
                self._get_max_dependency_lineage(dependency_id) + 1
            )
    
    def _get_max_dependency_lineage(self, dependency_id: str) -> int:
        """Get max lineage level of dependencies"""
        # This would query the feature store for dependency lineage
        return 0
    
    def create_version(
        self,
        code_hash: str,
        content_hash: str,
        change_summary: str = "",
        created_by: str = "",
        breaking_change: bool = False,
    ) -> FeatureVersion:
        """Create a new version of the feature"""
        # Bump version based on change type
        if breaking_change:
            self.metadata.version_major += 1
            self.metadata.version_minor = 0
            self.metadata.version_patch = 0
        else:
            self.metadata.version_minor += 1
            self.metadata.version_patch = 0
        
        self.metadata.version = f"{self.metadata.version_major}.{self.metadata.version_minor}.{self.metadata.version_patch}"
        
        version = FeatureVersion(
            version_id=str(uuid.uuid4()),
            feature_id=self.feature_id,
            version=self.metadata.version,
            version_major=self.metadata.version_major,
            version_minor=self.metadata.version_minor,
            version_patch=self.metadata.version_patch,
            content_hash=content_hash,
            code_hash=code_hash,
            created_by=created_by,
            change_summary=change_summary,
            breaking_change=breaking_change,
        )
        
        # Mark previous version as not current
        if self._current_version:
            self._current_version.is_current = False
        
        self.versions.append(version)
        self._current_version = version
        self.metadata.updated_at = datetime.utcnow()
        
        # Update signature
        self.metadata.compute_signature()
        
        return version
    
    def record_usage(
        self,
        used_by: str,
        use_case: str,
        dataset_id: str,
        performance_impact: Optional[float] = None,
    ) -> UsageRecord:
        """Record feature usage"""
        record = UsageRecord(
            used_at=datetime.utcnow(),
            used_by=used_by,
            use_case=use_case,
            dataset_id=dataset_id,
            performance_impact=performance_impact,
        )
        self.metadata.usage_history.append(record)
        return record
    
    def record_validation(
        self,
        validator: str,
        passed: bool,
        tests_run: List[str],
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> ValidationRecord:
        """Record feature validation"""
        record = ValidationRecord(
            validation_id=str(uuid.uuid4()),
            validated_at=datetime.utcnow(),
            validator=validator,
            passed=passed,
            tests_run=tests_run,
            errors=errors or [],
            warnings=warnings or [],
            metrics=metrics or {},
        )
        self.metadata.validation_history.append(record)
        
        # Mark as stable if validation passed and enough history
        if passed and len(self.metadata.validation_history) >= 3:
            if all(v.passed for v in self.metadata.validation_history[-3:]):
                self._current_version.is_stable = True if self._current_version else False
        
        return record
    
    def freeze(self) -> None:
        """Freeze feature to prevent further changes"""
        if self._current_version:
            self._current_version.is_frozen = True
    
    def deprecate(self) -> None:
        """Mark feature as deprecated"""
        self.metadata.deprecate()
    
    def get_total_computation_cost(self, dependency_costs: Dict[str, float]) -> float:
        """Calculate total computation cost including dependencies"""
        total = self.metadata.computation_cost
        for dep_id in self.metadata.dependencies:
            total += dependency_costs.get(dep_id, 0)
        return total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "versions": [v.to_dict() for v in self.versions],
            "current_version": self._current_version.to_dict() if self._current_version else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feature":
        """Create from dictionary"""
        metadata = FeatureMetadata.from_dict(data["metadata"])
        
        feature = cls(
            name=metadata.name,
            description=metadata.description,
            feature_type=metadata.feature_type,
            owner=metadata.owner,
            team=metadata.team,
        )
        feature.metadata = metadata
        
        if "versions" in data:
            feature.versions = [
                FeatureVersion(**v) for v in data["versions"]
            ]
            
            # Set current version
            for v in feature.versions:
                if v.is_current:
                    feature._current_version = v
                    break
        
        return feature
