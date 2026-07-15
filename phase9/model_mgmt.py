"""
Model Management - ML Model Lifecycle Management

Complete ML model lifecycle from training to deployment.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of ML models"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RL = "reinforcement_learning"
    ENSEMBLE = "ensemble"


class ModelStatus(Enum):
    """Model lifecycle status"""
    DRAFT = "draft"
    TRAINING = "training"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    MONITORING = "monitoring"
    ARCHIVED = "archived"
    FAILED = "failed"


@dataclass
class ModelVersion:
    """A version of a model"""
    version: str
    model_path: str
    metrics: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Training info
    training_data: str = ""
    validation_data: str = ""
    test_data: str = ""
    
    # Timing
    trained_at: datetime = field(default_factory=datetime.utcnow)
    trained_by: str = ""
    
    # Status
    status: ModelStatus = ModelStatus.DRAFT
    
    changelog: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "metrics": self.metrics,
            "trained_at": self.trained_at.isoformat(),
            "status": self.status.value,
        }


@dataclass
class ModelMetadata:
    """Metadata for a model"""
    id: str
    name: str
    model_type: ModelType
    
    # Versions
    versions: List[ModelVersion] = field(default_factory=list)
    current_version: Optional[str] = None
    
    # Metadata
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)
    
    # Statistics
    total_predictions: int = 0
    avg_latency_ms: float = 0
    
    # Status
    status: ModelStatus = ModelStatus.DRAFT
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type.value,
            "current_version": self.current_version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "status": self.status.value,
            "total_predictions": self.total_predictions,
            "versions_count": len(self.versions),
            "created_at": self.created_at.isoformat(),
        }


class ModelManager:
    """
    Model Management for ML model lifecycle.
    
    Features:
    - Model registration
    - Version control
    - Training tracking
    - A/B testing
    - Rollout strategies
    - Performance monitoring
    - Automatic retraining
    - Model comparison
    """
    
    def __init__(self, storage_path: str = "data/models"):
        self._storage_path = storage_path
        self._models: Dict[str, ModelMetadata] = {}
        self._model_functions: Dict[str, Callable] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "on_train_complete": [],
            "on_deploy": [],
            "on_rollback": [],
            "on_drift": [],
        }
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_models()
    
    def _load_models(self) -> None:
        """Load models from storage"""
        index_file = f"{self._storage_path}/index.json"
        
        try:
            with open(index_file, "r") as f:
                data = json.load(f)
            
            for model_data in data.get("models", []):
                model = ModelMetadata(
                    id=model_data["id"],
                    name=model_data["name"],
                    model_type=ModelType(model_data["model_type"]),
                    description=model_data.get("description", ""),
                    author=model_data.get("author", ""),
                    tags=model_data.get("tags", []),
                    status=ModelStatus(model_data.get("status", "draft")),
                )
                self._models[model.id] = model
            
            logger.info(f"Loaded {len(self._models)} models")
        except Exception as e:
            logger.warning(f"Could not load models: {e}")
    
    def _save_models(self) -> None:
        """Save models to storage"""
        index_file = f"{self._storage_path}/index.json"
        
        data = {
            "models": [m.to_dict() for m in self._models.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_model(
        self,
        name: str,
        model_type: ModelType,
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Register a new model"""
        model = ModelMetadata(
            id=str(uuid.uuid4()),
            name=name,
            model_type=model_type,
            description=description,
            author=author,
            tags=tags or [],
        )
        
        self._models[model.id] = model
        self._save_models()
        
        logger.info(f"Registered model: {name}")
        return model.id
    
    def add_version(
        self,
        model_id: str,
        version: str,
        model_path: str,
        metrics: Dict[str, float],
        config: Optional[Dict[str, Any]] = None,
        changelog: str = "",
        trained_by: str = "",
    ) -> bool:
        """Add a new version to a model"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        model_version = ModelVersion(
            version=version,
            model_path=model_path,
            metrics=metrics,
            config=config or {},
            changelog=changelog,
            trained_by=trained_by,
            status=ModelStatus.DRAFT,
        )
        
        model.versions.append(model_version)
        model.updated_at = datetime.utcnow()
        
        # Set as current if first version
        if not model.current_version:
            model.current_version = version
        
        self._save_models()
        return True
    
    def register_function(
        self,
        model_id: str,
        predict_func: Callable,
    ) -> bool:
        """Register the prediction function for a model"""
        if model_id not in self._models:
            return False
        
        self._model_functions[model_id] = predict_func
        return True
    
    def predict(
        self,
        model_id: str,
        input_data: Any,
    ) -> Optional[Any]:
        """Make a prediction using the current model version"""
        func = self._model_functions.get(model_id)
        model = self._models.get(model_id)
        
        if not func or not model:
            return None
        
        # Update statistics
        model.total_predictions += 1
        
        return func(input_data)
    
    def set_current_version(
        self,
        model_id: str,
        version: str,
    ) -> bool:
        """Set the current active version"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        # Verify version exists
        if not any(v.version == version for v in model.versions):
            return False
        
        model.current_version = version
        model.updated_at = datetime.utcnow()
        self._save_models()
        
        logger.info(f"Set current version for {model.name}: {version}")
        return True
    
    def update_version_status(
        self,
        model_id: str,
        version: str,
        status: ModelStatus,
    ) -> bool:
        """Update the status of a model version"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        for v in model.versions:
            if v.version == version:
                v.status = status
                
                # Fire callbacks
                if status == ModelStatus.VALIDATED:
                    self._fire_callback("on_train_complete", model_id, v)
                elif status == ModelStatus.DEPLOYED:
                    self._fire_callback("on_deploy", model_id, v)
                
                model.updated_at = datetime.utcnow()
                self._save_models()
                return True
        
        return False
    
    def deploy(
        self,
        model_id: str,
        version: Optional[str] = None,
    ) -> bool:
        """Deploy a model version"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        # Use specified version or current
        target_version = version or model.current_version
        if not target_version:
            return False
        
        # Update status
        success = self.update_version_status(
            model_id,
            target_version,
            ModelStatus.DEPLOYED,
        )
        
        if success:
            model.status = ModelStatus.DEPLOYED
            self._save_models()
        
        return success
    
    def rollback(
        self,
        model_id: str,
        to_version: Optional[str] = None,
    ) -> bool:
        """Rollback to a previous version"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        # Find a deployed version to rollback to
        if to_version:
            for v in model.versions:
                if v.version == to_version:
                    model.current_version = to_version
                    break
        else:
            # Rollback to previous version
            deployed_versions = [
                v for v in model.versions
                if v.status == ModelStatus.DEPLOYED
            ]
            
            if len(deployed_versions) > 1:
                # Set to second-to-last deployed
                model.current_version = deployed_versions[-2].version
        
        model.updated_at = datetime.utcnow()
        self._save_models()
        
        self._fire_callback("on_rollback", model_id, None)
        return True
    
    def compare_versions(
        self,
        model_id: str,
        version1: str,
        version2: str,
    ) -> Optional[Dict[str, Any]]:
        """Compare two versions of a model"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        v1 = next((v for v in model.versions if v.version == version1), None)
        v2 = next((v for v in model.versions if v.version == version2), None)
        
        if not v1 or not v2:
            return None
        
        # Compare metrics
        comparison = {
            "version1": version1,
            "version2": version2,
            "metrics_comparison": {},
        }
        
        all_metrics = set(v1.metrics.keys()) | set(v2.metrics.keys())
        
        for metric in all_metrics:
            m1 = v1.metrics.get(metric, 0)
            m2 = v2.metrics.get(metric, 0)
            comparison["metrics_comparison"][metric] = {
                "v1": m1,
                "v2": m2,
                "diff": m2 - m1,
                "pct_change": ((m2 - m1) / m1 * 100) if m1 != 0 else 0,
            }
        
        return comparison
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get a model by ID"""
        return self._models.get(model_id)
    
    def get_all_models(
        self,
        status: Optional[ModelStatus] = None,
    ) -> List[ModelMetadata]:
        """Get all models"""
        models = list(self._models.values())
        
        if status:
            models = [m for m in models if m.status == status]
        
        return models
    
    def get_version(
        self,
        model_id: str,
        version: str,
    ) -> Optional[ModelVersion]:
        """Get a specific version"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        return next((v for v in model.versions if v.version == version), None)
    
    def register_callback(
        self,
        event: str,
        callback: Callable,
    ) -> None:
        """Register a callback for model events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _fire_callback(
        self,
        event: str,
        model_id: str,
        version: Optional[ModelVersion],
    ) -> None:
        """Fire callbacks for an event"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(model_id, version)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get model management statistics"""
        models = list(self._models.values())
        
        return {
            "total_models": len(models),
            "by_type": {
                mt.value: sum(1 for m in models if m.model_type == mt)
                for mt in ModelType
            },
            "by_status": {
                ms.value: sum(1 for m in models if m.status == ms)
                for ms in ModelStatus
            },
            "total_predictions": sum(m.total_predictions for m in models),
            "total_versions": sum(len(m.versions) for m in models),
        }
