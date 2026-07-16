"""
Feature Store

Feature management with versioning and deduplication.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from data_platform.models.feature import (
    Feature,
    FeatureMetadata,
    FeatureVersion,
    FeatureType,
    FeatureImportance,
    ValidationRecord,
    UsageRecord,
)

logger = logging.getLogger(__name__)


class FeatureStore:
    """
    Feature Store for managing ML features with versioning and deduplication.
    
    Features:
    - Feature versioning
    - Duplicate prevention
    - Dependency tracking
    - Usage history
    - Validation tracking
    - Search and retrieval
    """
    
    def __init__(self, storage_path: str = "data_platform/features"):
        self._storage_path = storage_path
        self._features: Dict[str, Feature] = {}
        self._signatures: Dict[str, str] = {}  # signature -> feature_id
        self._names: Dict[str, str] = {}  # name -> feature_id
        
        # Indexes
        self._by_type: Dict[str, Set[str]] = {}
        self._by_importance: Dict[str, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._by_owner: Dict[str, Set[str]] = {}
        self._by_dataset: Dict[str, Set[str]] = {}  # dataset_id -> feature_ids
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load feature index"""
        index_file = f"{self._storage_path}/index.json"
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                    
                for feature_data in data.get("features", []):
                    feature = Feature.from_dict(feature_data)
                    self._features[feature.feature_id] = feature
                    self._update_indexes(feature)
                
                logger.info(f"Loaded {len(self._features)} features from index")
            except Exception as e:
                logger.warning(f"Could not load feature index: {e}")
    
    def _save_index(self) -> None:
        """Save feature index"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "features": [f.to_dict() for f in self._features.values()],
            "signatures": {s: list(fids) for s, fids in self._get_signature_index().items()},
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _update_indexes(self, feature: Feature) -> None:
        """Update all indexes for a feature"""
        metadata = feature.metadata
        
        # Signature index
        if metadata.signature:
            self._signatures[metadata.signature] = metadata.feature_id
        
        # Name index
        self._names[metadata.name.lower()] = metadata.feature_id
        
        # Type index
        type_key = metadata.feature_type.value
        if type_key not in self._by_type:
            self._by_type[type_key] = set()
        self._by_type[type_key].add(metadata.feature_id)
        
        # Importance index
        importance_key = metadata.importance.value
        if importance_key not in self._by_importance:
            self._by_importance[importance_key] = set()
        self._by_importance[importance_key].add(metadata.feature_id)
        
        # Tag index
        for tag in metadata.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(metadata.feature_id)
        
        # Owner index
        if metadata.owner:
            if metadata.owner not in self._by_owner:
                self._by_owner[metadata.owner] = set()
            self._by_owner[metadata.owner].add(metadata.feature_id)
        
        # Dataset index
        if metadata.source_dataset_id:
            if metadata.source_dataset_id not in self._by_dataset:
                self._by_dataset[metadata.source_dataset_id] = set()
            self._by_dataset[metadata.source_dataset_id].add(metadata.feature_id)
    
    def _get_signature_index(self) -> Dict[str, List[str]]:
        """Get signature to feature_ids mapping"""
        sig_map = {}
        for feature in self._features.values():
            if feature.signature:
                if feature.signature not in sig_map:
                    sig_map[feature.signature] = []
                sig_map[feature.signature].append(feature.feature_id)
        return sig_map
    
    def register_feature(
        self,
        name: str,
        description: str,
        feature_type: FeatureType = FeatureType.DERIVED,
        dependencies: Optional[List[str]] = None,
        source_columns: Optional[List[str]] = None,
        computation_function: str = "",
        owner: str = "",
        team: str = "",
        tags: Optional[List[str]] = None,
        importance: FeatureImportance = FeatureImportance.MEDIUM,
    ) -> Tuple[Feature, bool]:
        """
        Register a new feature.
        
        Returns:
            Tuple of (Feature, is_new)
            - is_new is False if a duplicate signature was found
        """
        # Create feature
        feature = Feature(
            name=name,
            description=description,
            feature_type=feature_type,
            owner=owner,
            team=team,
        )
        
        # Set additional properties
        feature.metadata.dependencies = dependencies or []
        feature.metadata.source_columns = source_columns or []
        feature.metadata.computation_function = computation_function
        feature.metadata.tags = tags or []
        feature.metadata.importance = importance
        feature.metadata.compute_signature()
        
        # Check for duplicates
        is_new = True
        if feature.signature in self._signatures:
            existing_id = self._signatures[feature.signature]
            logger.warning(
                f"Duplicate feature signature detected: {feature.signature}. "
                f"Existing feature: {existing_id}"
            )
            is_new = False
            return self._features[existing_id], is_new
        
        # Check for duplicate name
        name_key = name.lower()
        if name_key in self._names:
            existing_id = self._names[name_key]
            logger.warning(
                f"Duplicate feature name: {name}. "
                f"Existing feature: {existing_id}"
            )
            # Still allow but log warning
        
        # Update dependencies' dependents
        for dep_id in feature.metadata.dependencies:
            if dep_id in self._features:
                dep = self._features[dep_id]
                if feature.feature_id not in dep.metadata.dependents:
                    dep.metadata.dependents.append(feature.feature_id)
        
        # Store and index
        self._features[feature.feature_id] = feature
        self._update_indexes(feature)
        self._save_index()
        
        logger.info(f"Registered feature: {name} ({feature.feature_id})")
        return feature, is_new
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get feature by ID"""
        return self._features.get(feature_id)
    
    def get_feature_by_name(self, name: str) -> Optional[Feature]:
        """Get feature by name"""
        feature_id = self._names.get(name.lower())
        return self._features.get(feature_id) if feature_id else None
    
    def get_feature_by_signature(self, signature: str) -> Optional[Feature]:
        """Get feature by signature"""
        feature_id = self._signatures.get(signature)
        return self._features.get(feature_id) if feature_id else None
    
    def update_feature(
        self,
        feature_id: str,
        description: Optional[str] = None,
        importance: Optional[FeatureImportance] = None,
        tags: Optional[List[str]] = None,
        data_type: Optional[str] = None,
        computation_cost: Optional[float] = None,
    ) -> Optional[Feature]:
        """Update feature metadata"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        if feature.metadata.is_deprecated:
            logger.warning(f"Cannot update deprecated feature: {feature_id}")
            return None
        
        if description is not None:
            feature.metadata.description = description
        if importance is not None:
            feature.metadata.importance = importance
        if tags is not None:
            feature.metadata.tags = tags
        if data_type is not None:
            feature.metadata.data_type = data_type
        if computation_cost is not None:
            feature.metadata.computation_cost = computation_cost
        
        feature.metadata.updated_at = datetime.utcnow()
        self._save_index()
        
        return feature
    
    def create_feature_version(
        self,
        feature_id: str,
        code_hash: str,
        content_hash: str,
        change_summary: str = "",
        created_by: str = "",
        breaking_change: bool = False,
    ) -> Optional[FeatureVersion]:
        """Create a new version of a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        version = feature.create_version(
            code_hash=code_hash,
            content_hash=content_hash,
            change_summary=change_summary,
            created_by=created_by,
            breaking_change=breaking_change,
        )
        
        # Update dependents' lineage levels
        self._update_dependents_lineage(feature_id)
        
        self._save_index()
        logger.info(f"Created version {version.version} for feature: {feature.metadata.name}")
        
        return version
    
    def _update_dependents_lineage(self, feature_id: str) -> None:
        """Update lineage levels for all dependent features"""
        feature = self._features.get(feature_id)
        if not feature:
            return
        
        for dep_id in feature.metadata.dependents:
            dep = self._features.get(dep_id)
            if dep:
                dep.metadata.lineage_level = max(
                    dep.metadata.lineage_level,
                    feature.metadata.lineage_level + 1
                )
                self._update_dependents_lineage(dep_id)
    
    def record_usage(
        self,
        feature_id: str,
        used_by: str,
        use_case: str,
        dataset_id: str,
        performance_impact: Optional[float] = None,
    ) -> Optional[UsageRecord]:
        """Record feature usage"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        record = feature.record_usage(
            used_by=used_by,
            use_case=use_case,
            dataset_id=dataset_id,
            performance_impact=performance_impact,
        )
        
        self._save_index()
        return record
    
    def record_validation(
        self,
        feature_id: str,
        validator: str,
        passed: bool,
        tests_run: List[str],
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Optional[ValidationRecord]:
        """Record feature validation"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        
        record = feature.record_validation(
            validator=validator,
            passed=passed,
            tests_run=tests_run,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )
        
        self._save_index()
        return record
    
    def deprecate_feature(self, feature_id: str) -> bool:
        """Mark feature as deprecated"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        feature.deprecate()
        
        # Update dependents
        for dep_id in feature.metadata.dependents:
            dep = self._features.get(dep_id)
            if dep:
                logger.warning(
                    f"Feature {feature_id} is deprecated. "
                    f"Dependent feature {dep_id} ({dep.metadata.name}) may be affected."
                )
        
        self._save_index()
        return True
    
    def search(
        self,
        query: Optional[str] = None,
        feature_type: Optional[FeatureType] = None,
        importance: Optional[FeatureImportance] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
        dataset_id: Optional[str] = None,
        include_deprecated: bool = False,
        include_experimental: bool = True,
    ) -> List[Feature]:
        """Search for features"""
        results = list(self._features.values())
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                f for f in results
                if query_lower in f.metadata.name.lower() or
                   query_lower in f.metadata.description.lower()
            ]
        
        # Filter by type
        if feature_type:
            results = [
                f for f in results
                if f.metadata.feature_type == feature_type
            ]
        
        # Filter by importance
        if importance:
            results = [
                f for f in results
                if f.metadata.importance == importance
            ]
        
        # Filter by tags
        if tags:
            results = [
                f for f in results
                if any(tag in f.metadata.tags for tag in tags)
            ]
        
        # Filter by owner
        if owner:
            results = [
                f for f in results
                if f.metadata.owner == owner
            ]
        
        # Filter by dataset
        if dataset_id:
            results = [
                f for f in results
                if dataset_id in f.metadata.source_dataset_id
            ]
        
        # Filter deprecated
        if not include_deprecated:
            results = [f for f in results if not f.metadata.is_deprecated]
        
        # Filter experimental
        if not include_experimental:
            results = [f for f in results if not f.metadata.is_experimental]
        
        return sorted(results, key=lambda f: f.metadata.name)
    
    def get_dependencies(self, feature_id: str) -> List[Feature]:
        """Get all dependencies of a feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return []
        
        deps = []
        visited = set()
        to_visit = list(feature.metadata.dependencies)
        
        while to_visit:
            dep_id = to_visit.pop(0)
            if dep_id in visited:
                continue
            visited.add(dep_id)
            
            dep = self._features.get(dep_id)
            if dep:
                deps.append(dep)
                to_visit.extend(dep.metadata.dependencies)
        
        return deps
    
    def get_dependents(self, feature_id: str) -> List[Feature]:
        """Get all features that depend on this feature"""
        feature = self._features.get(feature_id)
        if not feature:
            return []
        
        dependents = []
        visited = set()
        to_visit = list(feature.metadata.dependents)
        
        while to_visit:
            dep_id = to_visit.pop(0)
            if dep_id in visited:
                continue
            visited.add(dep_id)
            
            dep = self._features.get(dep_id)
            if dep:
                dependents.append(dep)
                to_visit.extend(dep.metadata.dependents)
        
        return dependents
    
    def get_features_by_dataset(self, dataset_id: str) -> List[Feature]:
        """Get all features from a dataset"""
        feature_ids = self._by_dataset.get(dataset_id, set())
        return [self._features[fid] for fid in feature_ids if fid in self._features]
    
    def get_feature_lineage(self, feature_id: str, depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
        """Get full lineage information for a feature"""
        if depth >= max_depth:
            return {"max_depth_reached": True}
        
        feature = self._features.get(feature_id)
        if not feature:
            return {}
        
        return {
            "feature": feature.metadata.to_dict(),
            "dependencies": [
                {
                    "feature": dep.metadata.to_dict(),
                    "lineage": self.get_feature_lineage(dep.feature_id, depth + 1, max_depth)
                }
                for dep in self.get_dependencies(feature_id)
            ],
            "dependents": [
                {
                    "feature": dep.metadata.to_dict(),
                    "lineage": self.get_feature_lineage(dep.feature_id, depth + 1, max_depth)
                }
                for dep in self.get_dependents(feature_id)
            ],
        }
    
    def list_features(
        self,
        feature_type: Optional[FeatureType] = None,
        importance: Optional[FeatureImportance] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """List all features with metadata"""
        features = self.search(
            feature_type=feature_type,
            importance=importance,
            include_deprecated=not active_only,
        )
        
        return [
            {
                "feature_id": f.feature_id,
                "name": f.metadata.name,
                "description": f.metadata.description,
                "type": f.metadata.feature_type.value,
                "importance": f.metadata.importance.value,
                "version": f.metadata.version,
                "is_active": f.metadata.is_active,
                "is_deprecated": f.metadata.is_deprecated,
                "owner": f.metadata.owner,
                "tags": f.metadata.tags,
                "dependencies_count": len(f.metadata.dependencies),
                "usage_count": len(f.metadata.usage_history),
                "validation_pass_rate": self._get_validation_pass_rate(f),
                "created_at": f.metadata.created_at.isoformat() if isinstance(f.metadata.created_at, datetime) else f.metadata.created_at,
            }
            for f in features
        ]
    
    def _get_validation_pass_rate(self, feature: Feature) -> float:
        """Calculate validation pass rate"""
        history = feature.metadata.validation_history
        if not history:
            return 1.0  # Assume pass if never validated
        passed = sum(1 for v in history if v.passed)
        return passed / len(history)
    
    def export_features(self, feature_ids: List[str]) -> Dict[str, Any]:
        """Export features for sharing or backup"""
        features = {
            fid: self._features[fid].to_dict()
            for fid in feature_ids
            if fid in self._features
        }
        
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "feature_count": len(features),
            "features": features,
        }
    
    def import_features(self, data: Dict[str, Any], overwrite: bool = False) -> List[str]:
        """Import features from backup"""
        imported = []
        
        for fid, feature_data in data.get("features", {}).items():
            if fid in self._features and not overwrite:
                logger.warning(f"Feature {fid} already exists, skipping")
                continue
            
            feature = Feature.from_dict(feature_data)
            
            # Update indexes
            self._features[fid] = feature
            self._update_indexes(feature)
            
            imported.append(fid)
        
        if imported:
            self._save_index()
            logger.info(f"Imported {len(imported)} features")
        
        return imported
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get feature store statistics"""
        features = list(self._features.values())
        
        return {
            "total_features": len(features),
            "active_features": sum(1 for f in features if f.metadata.is_active),
            "deprecated_features": sum(1 for f in features if f.metadata.is_deprecated),
            "experimental_features": sum(1 for f in features if f.metadata.is_experimental),
            "by_type": {
                (ft.value if hasattr(ft, 'value') else str(ft)): len(fids)
                for ft, fids in self._by_type.items()
            },
            "by_importance": {
                (imp.value if hasattr(imp, 'value') else str(imp)): len(fids)
                for imp, fids in self._by_importance.items()
            },
            "total_dependencies": sum(
                len(f.metadata.dependencies)
                for f in features
            ),
            "total_usage_records": sum(
                len(f.metadata.usage_history)
                for f in features
            ),
            "total_validation_records": sum(
                len(f.metadata.validation_history)
                for f in features
            ),
        }
