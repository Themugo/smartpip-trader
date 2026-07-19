"""
Feature Store - Reusable Engineered Features

Complete feature store with:
- Version control
- Documentation
- Dependency tracking
- Feature groups
"""

import json
import logging
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Feature types"""
    PRICE = "price"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    ENTROPY = "entropy"
    PATTERN = "pattern"
    LAG = "lag"
    ROLLING = "rolling"
    DERIVATIVE = "derivative"
    CUSTOM = "custom"


class FeatureCategory(Enum):
    """Feature categories"""
    TECHNICAL = "technical"
    STATISTICAL = "statistical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    DERIVED = "derived"


class FeatureStatus(Enum):
    """Feature status"""
    DRAFT = "draft"
    TESTED = "tested"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


@dataclass
class FeatureDependency:
    """Feature dependency"""
    feature_id: str
    version: str
    required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "version": self.version,
            "required": self.required,
        }


@dataclass
class FeatureVersion:
    """A version of a feature"""
    version: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    
    # Code
    code: str = ""
    test_code: str = ""
    
    # Documentation
    description: str = ""
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Validation
    validation_results: Dict[str, Any] = field(default_factory=dict)
    is_validated: bool = False
    
    # Usage stats
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "code": self.code,
            "test_code": self.test_code,
            "description": self.description,
            "parameters": self.parameters,
            "validation_results": self.validation_results,
            "is_validated": self.is_validated,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


@dataclass
class FeatureTest:
    """Feature test case"""
    test_id: str
    name: str
    description: str
    
    # Test data
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Any = None
    
    # Results
    passed: bool = False
    actual_output: Any = None
    error_message: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "description": self.description,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "passed": self.passed,
            "actual_output": self.actual_output,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


@dataclass
class StoredFeature:
    """A stored feature with all its versions"""
    id: str
    name: str
    
    # Classification
    feature_type: FeatureType
    category: FeatureCategory
    
    # Current state
    current_version: str = "1.0.0"
    versions: Dict[str, FeatureVersion] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[FeatureDependency] = field(default_factory=list)
    
    # Documentation
    description: str = ""
    long_description: str = ""
    examples: List[str] = field(default_factory=list)
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    # Status
    status: FeatureStatus = FeatureStatus.DRAFT
    
    # Tests
    tests: List[FeatureTest] = field(default_factory=list)
    
    # Metadata
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Usage
    used_by_features: List[str] = field(default_factory=list)  # Feature IDs that use this
    used_by_models: List[str] = field(default_factory=list)  # Model IDs
    
    # Statistics
    avg_execution_time_ms: float = 0.0
    total_executions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "category": self.category.value,
            "current_version": self.current_version,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "dependencies": [d.to_dict() for d in self.dependencies],
            "description": self.description,
            "long_description": self.long_description,
            "examples": self.examples,
            "tags": self.tags,
            "status": self.status.value,
            "tests": [t.to_dict() for t in self.tests],
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "used_by_features": self.used_by_features,
            "used_by_models": self.used_by_models,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "total_executions": self.total_executions,
        }
    
    def get_current_code(self) -> str:
        """Get the current version code"""
        version = self.versions.get(self.current_version)
        return version.code if version else ""


@dataclass
class FeatureGroup:
    """A group of related features"""
    id: str
    name: str
    description: str
    
    # Features in this group
    feature_ids: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Usage
    use_count: int = 0
    last_used_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "feature_ids": self.feature_ids,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "use_count": self.use_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class FeatureStore:
    """
    Feature Store for reusable engineered features.
    
    Features:
    - Feature registration and versioning
    - Dependency tracking
    - Feature groups
    - Documentation and examples
    - Testing and validation
    - Usage tracking
    - Search and discovery
    """
    
    def __init__(self, storage_path: str = "data/feature_store"):
        self._storage_path = storage_path
        self._features: Dict[str, StoredFeature] = {}
        self._groups: Dict[str, FeatureGroup] = {}
        self._index: Dict[str, List[str]] = defaultdict(list)  # tag -> feature IDs
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_store()
    
    def _load_store(self) -> None:
        """Load feature store"""
        store_file = f"{self._storage_path}/store.json"
        
        try:
            if os.path.exists(store_file):
                with open(store_file, "r") as f:
                    data = json.load(f)
                
                # Load features
                for feat_data in data.get("features", []):
                    feat_data["created_at"] = datetime.fromisoformat(feat_data["created_at"])
                    feat_data["updated_at"] = datetime.fromisoformat(feat_data["updated_at"])
                    
                    # Parse versions
                    for v in feat_data.get("versions", {}).values():
                        v["created_at"] = datetime.fromisoformat(v["created_at"])
                        if v.get("last_used_at"):
                            v["last_used_at"] = datetime.fromisoformat(v["last_used_at"])
                    feat_data["versions"] = {k: FeatureVersion(**v) for k, v in feat_data["versions"].items()}
                    
                    # Parse tests
                    for t in feat_data.get("tests", []):
                        t["created_at"] = datetime.fromisoformat(t["created_at"])
                        if t.get("executed_at"):
                            t["executed_at"] = datetime.fromisoformat(t["executed_at"])
                    feat_data["tests"] = [FeatureTest(**t) for t in feat_data.get("tests", [])]
                    
                    feature = StoredFeature(**feat_data)
                    self._features[feature.id] = feature
                    
                    # Build index
                    for tag in feature.tags:
                        self._index[tag].append(feature.id)
                
                # Load groups
                for group_data in data.get("groups", []):
                    group_data["created_at"] = datetime.fromisoformat(group_data["created_at"])
                    group_data["updated_at"] = datetime.fromisoformat(group_data["updated_at"])
                    if group_data.get("last_used_at"):
                        group_data["last_used_at"] = datetime.fromisoformat(group_data["last_used_at"])
                    group = FeatureGroup(**group_data)
                    self._groups[group.id] = group
                
                logger.info(f"Loaded {len(self._features)} features and {len(self._groups)} groups")
        except Exception as e:
            logger.warning(f"Could not load feature store: {e}")
    
    def _save_store(self) -> None:
        """Save feature store"""
        store_file = f"{self._storage_path}/store.json"
        
        # Rebuild index
        self._index.clear()
        for feat in self._features.values():
            for tag in feat.tags:
                self._index[tag].append(feat.id)
        
        data = {
            "features": [f.to_dict() for f in self._features.values()],
            "groups": [g.to_dict() for g in self._groups.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(store_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Feature Registration
    def register_feature(
        self,
        name: str,
        feature_type: FeatureType,
        category: FeatureCategory,
        code: str,
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[FeatureDependency]] = None,
    ) -> StoredFeature:
        """Register a new feature"""
        feature = StoredFeature(
            id=str(uuid.uuid4()),
            name=name,
            feature_type=feature_type,
            category=category,
            description=description,
            author=author,
            tags=tags or [],
            dependencies=dependencies or [],
        )
        
        # Create initial version
        version = FeatureVersion(
            version="1.0.0",
            created_by=author,
            code=code,
            description=description,
        )
        feature.versions["1.0.0"] = version
        feature.current_version = "1.0.0"
        
        self._features[feature.id] = feature
        self._save_store()
        
        logger.info(f"Registered feature: {name}")
        return feature
    
    def add_version(
        self,
        feature_id: str,
        version: str,
        code: str,
        changelog: str = "",
        created_by: str = "",
        description: Optional[str] = None,
    ) -> Optional[FeatureVersion]:
        """Add a new version to a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        if version in feature.versions:
            logger.warning(f"Version {version} already exists")
            return None
        
        version_obj = FeatureVersion(
            version=version,
            created_by=created_by,
            code=code,
            description=description or changelog,
        )
        
        feature.versions[version] = version_obj
        feature.current_version = version
        feature.updated_at = datetime.now(timezone.utc)
        
        self._save_store()
        return version_obj
    
    def update_feature(
        self,
        feature_id: str,
        description: Optional[str] = None,
        long_description: Optional[str] = None,
        examples: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        status: Optional[FeatureStatus] = None,
    ) -> bool:
        """Update feature metadata"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        if description is not None:
            feature.description = description
        if long_description is not None:
            feature.long_description = long_description
        if examples is not None:
            feature.examples = examples
        if tags is not None:
            feature.tags = tags
        if status is not None:
            feature.status = status
        
        feature.updated_at = datetime.now(timezone.utc)
        self._save_store()
        return True
    
    # Feature Dependencies
    def add_dependency(
        self,
        feature_id: str,
        dependency_id: str,
        version: str = "1.0.0",
        required: bool = True,
    ) -> bool:
        """Add a dependency to a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        # Check for circular dependency
        if self._would_create_cycle(feature_id, dependency_id):
            logger.error("Adding this dependency would create a cycle")
            return False
        
        dep = FeatureDependency(
            feature_id=dependency_id,
            version=version,
            required=required,
        )
        
        feature.dependencies.append(dep)
        
        # Update reverse reference
        dep_feature = self._features.get(dependency_id)
        if dep_feature and feature_id not in dep_feature.used_by_features:
            dep_feature.used_by_features.append(feature_id)
        
        feature.updated_at = datetime.now(timezone.utc)
        self._save_store()
        return True
    
    def _would_create_cycle(self, feature_id: str, dep_id: str) -> bool:
        """Check if adding a dependency would create a cycle"""
        # Get all dependencies of dep_id
        dep_ids = {dep_id}
        to_check = [dep_id]
        
        while to_check:
            current_id = to_check.pop()
            feature = self._features.get(current_id)
            if feature:
                for dep in feature.dependencies:
                    if dep.feature_id == feature_id:
                        return True
                    if dep.feature_id not in dep_ids:
                        dep_ids.add(dep.feature_id)
                        to_check.append(dep.feature_id)
        
        return False
    
    def get_dependency_tree(
        self,
        feature_id: str,
        include_optional: bool = False,
    ) -> Dict[str, Any]:
        """Get full dependency tree for a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return {}
        
        def build_tree(fid: str, depth: int = 0, visited: Optional[Set[str]] = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()
            
            if fid in visited or depth > 10:
                return {"id": fid, "error": "circular or max depth"}
            
            visited.add(fid)
            f = self._features.get(fid)
            if not f:
                return {"id": fid, "error": "not found"}
            
            deps = []
            for dep in f.dependencies:
                if not include_optional and not dep.required:
                    continue
                dep_node = build_tree(dep.feature_id, depth + 1, visited.copy())
                dep_node["version"] = dep.version
                dep_node["required"] = dep.required
                deps.append(dep_node)
            
            return {
                "id": f.id,
                "name": f.name,
                "version": f.current_version,
                "dependencies": deps,
            }
        
        return build_tree(feature_id)
    
    # Feature Testing
    def add_test(
        self,
        feature_id: str,
        name: str,
        description: str,
        input_data: Dict[str, Any],
        expected_output: Any,
    ) -> Optional[FeatureTest]:
        """Add a test case to a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        test = FeatureTest(
            test_id=str(uuid.uuid4()),
            name=name,
            description=description,
            input_data=input_data,
            expected_output=expected_output,
        )
        
        feature.tests.append(test)
        feature.updated_at = datetime.now(timezone.utc)
        self._save_store()
        
        return test
    
    def run_tests(
        self,
        feature_id: str,
        version: Optional[str] = None,
        executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """Run all tests for a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return {"error": "Feature not found"}
        
        version_obj = feature.versions.get(version or feature.current_version)
        if not version_obj:
            return {"error": "Version not found"}
        
        results = {
            "total": len(feature.tests),
            "passed": 0,
            "failed": 0,
            "test_results": [],
        }
        
        for test in feature.tests:
            test.executed_at = datetime.now(timezone.utc)
            
            if executor:
                try:
                    test.actual_output = executor(version_obj.code, test.input_data)
                    # Compare output (simplified)
                    test.passed = str(test.actual_output) == str(test.expected_output)
                except Exception as e:
                    test.passed = False
                    test.error_message = str(e)
            else:
                test.passed = False
                test.error_message = "No executor provided"
            
            if test.passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["test_results"].append(test.to_dict())
        
        # Update validation status
        version_obj.validation_results = results
        version_obj.is_validated = results["failed"] == 0
        
        self._save_store()
        return results
    
    # Feature Groups
    def create_group(
        self,
        name: str,
        description: str,
        feature_ids: Optional[List[str]] = None,
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> FeatureGroup:
        """Create a feature group"""
        group = FeatureGroup(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            feature_ids=feature_ids or [],
            author=author,
            tags=tags or [],
        )
        
        self._groups[group.id] = group
        self._save_store()
        
        return group
    
    def add_to_group(
        self,
        group_id: str,
        feature_ids: List[str],
    ) -> bool:
        """Add features to a group"""
        group = self._groups.get(group_id)
        if not group:
            return False
        
        for fid in feature_ids:
            if fid not in group.feature_ids:
                group.feature_ids.append(fid)
        
        group.updated_at = datetime.now(timezone.utc)
        self._save_store()
        return True
    
    def get_group_features(self, group_id: str) -> List[StoredFeature]:
        """Get all features in a group"""
        group = self._groups.get(group_id)
        if not group:
            return []
        
        return [self._features[fid] for fid in group.feature_ids if fid in self._features]
    
    # Usage Tracking
    def record_usage(
        self,
        feature_id: str,
        version: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> bool:
        """Record feature usage"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        feature.total_executions += 1
        feature.used_by_models.append("unknown")  # Would be actual model ID
        
        # Update version stats
        version_str = version or feature.current_version
        version_obj = feature.versions.get(version_str)
        if version_obj:
            version_obj.usage_count += 1
            version_obj.last_used_at = datetime.now(timezone.utc)
        
        # Update average execution time
        if execution_time_ms > 0:
            n = feature.total_executions
            feature.avg_execution_time_ms = (
                (feature.avg_execution_time_ms * (n - 1) + execution_time_ms) / n
            )
        
        feature.updated_at = datetime.now(timezone.utc)
        self._save_store()
        return True
    
    # Search and Discovery
    def get_feature(self, feature_id: str) -> Optional[StoredFeature]:
        """Get a feature by ID"""
        return self._features.get(feature_id)
    
    def get_by_name(self, name: str) -> Optional[StoredFeature]:
        """Get a feature by name"""
        for feature in self._features.values():
            if feature.name.lower() == name.lower():
                return feature
        return None
    
    def search(
        self,
        query: Optional[str] = None,
        feature_types: Optional[List[FeatureType]] = None,
        categories: Optional[List[FeatureCategory]] = None,
        tags: Optional[List[str]] = None,
        status: Optional[FeatureStatus] = None,
        min_usage: Optional[int] = None,
        limit: int = 50,
    ) -> List[StoredFeature]:
        """Search features"""
        results = list(self._features.values())
        
        if query:
            query_lower = query.lower()
            results = [
                f for f in results
                if query_lower in f.name.lower()
                or query_lower in f.description.lower()
                or any(query_lower in tag.lower() for tag in f.tags)
            ]
        
        if feature_types:
            results = [f for f in results if f.feature_type in feature_types]
        
        if categories:
            results = [f for f in results if f.category in categories]
        
        if tags:
            results = [f for f in results if any(t in f.tags for t in tags)]
        
        if status:
            results = [f for f in results if f.status == status]
        
        if min_usage is not None:
            results = [f for f in results if f.total_executions >= min_usage]
        
        # Sort by usage and name
        results.sort(key=lambda f: (f.total_executions, f.name), reverse=True)
        return results[:limit]
    
    def get_popular_features(self, limit: int = 10) -> List[StoredFeature]:
        """Get most used features"""
        return sorted(
            self._features.values(),
            key=lambda f: f.total_executions,
            reverse=True,
        )[:limit]
    
    def get_production_features(self) -> List[StoredFeature]:
        """Get all production-ready features"""
        return [f for f in self._features.values() if f.status == FeatureStatus.PRODUCTION]
    
    # Export and Import
    def export_feature(
        self,
        feature_id: str,
        include_code: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Export a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        export_data = {
            "metadata": {
                "id": feature.id,
                "name": feature.name,
                "feature_type": feature.feature_type.value,
                "category": feature.category.value,
                "description": feature.description,
                "long_description": feature.long_description,
                "tags": feature.tags,
                "dependencies": [d.to_dict() for d in feature.dependencies],
            },
        }
        
        if include_code:
            export_data["versions"] = {
                v: ver.to_dict() for v, ver in feature.versions.items()
            }
        
        return export_data
    
    def import_feature(
        self,
        data: Dict[str, Any],
        new_id: Optional[str] = None,
    ) -> Optional[StoredFeature]:
        """Import a feature"""
        try:
            metadata = data.get("metadata", {})
            
            feature = StoredFeature(
                id=new_id or str(uuid.uuid4()),
                name=metadata.get("name", ""),
                feature_type=FeatureType(metadata.get("feature_type", "custom")),
                category=FeatureCategory(metadata.get("category", "derived")),
                description=metadata.get("description", ""),
                long_description=metadata.get("long_description", ""),
                tags=metadata.get("tags", []),
            )
            
            # Import versions
            for v_data in data.get("versions", {}).values():
                v_data["created_at"] = datetime.fromisoformat(v_data["created_at"])
                if v_data.get("last_used_at"):
                    v_data["last_used_at"] = datetime.fromisoformat(v_data["last_used_at"])
                version = FeatureVersion(**v_data)
                feature.versions[version.version] = version
            
            self._features[feature.id] = feature
            self._save_store()
            
            return feature
        except Exception as e:
            logger.error(f"Failed to import feature: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get feature store statistics"""
        features = list(self._features.values())
        
        return {
            "total_features": len(features),
            "total_versions": sum(len(f.versions) for f in features),
            "total_tests": sum(len(f.tests) for f in features),
            "by_type": {
                ftype.value: sum(1 for f in features if f.feature_type == ftype)
                for ftype in FeatureType
            },
            "by_status": {
                status.value: sum(1 for f in features if f.status == status)
                for status in FeatureStatus
            },
            "production_ready": sum(1 for f in features if f.status == FeatureStatus.PRODUCTION),
            "total_executions": sum(f.total_executions for f in features),
            "groups": len(self._groups),
        }


import os
