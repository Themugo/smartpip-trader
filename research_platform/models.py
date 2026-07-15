"""
Model Registry - Production ML Model Management

Complete model registry with:
- Candidate models
- Production models
- Archived models
- Rollback support
- Approval workflow
"""

import json
import logging
import uuid
import hashlib
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Model types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    ENSEMBLE = "ensemble"
    RL = "reinforcement_learning"
    CUSTOM = "custom"


class ModelStatus(Enum):
    """Model status in lifecycle"""
    DRAFT = "draft"
    REGISTERED = "registered"
    VALIDATING = "validating"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class ApprovalAction(Enum):
    """Approval workflow actions"""
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REVOKE = "revoke"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"


@dataclass
class ApprovalStep:
    """An approval workflow step"""
    step_id: str
    name: str
    approver_role: str  # e.g., "quant", "risk_manager", "admin"
    
    # Status
    status: str = "pending"  # pending, approved, rejected, skipped
    approver: str = ""
    approved_at: Optional[datetime] = None
    comment: str = ""
    
    # Conditions
    required: bool = True
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "approver_role": self.approver_role,
            "status": self.status,
            "approver": self.approver,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "comment": self.comment,
            "required": self.required,
            "auto_approve_conditions": self.auto_approve_conditions,
        }


@dataclass
class ApprovalWorkflow:
    """Approval workflow configuration"""
    workflow_id: str
    name: str
    description: str
    
    # Steps
    steps: List[ApprovalStep] = field(default_factory=list)
    
    # Status
    current_step: int = 0
    status: str = "pending"  # pending, in_progress, approved, rejected, cancelled
    
    # History
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def is_complete(self) -> bool:
        """Check if workflow is complete"""
        if self.status in ["approved", "rejected", "cancelled"]:
            return True
        
        for step in self.steps:
            if step.required and step.status == "pending":
                return False
        
        return True
    
    def get_current_step(self) -> Optional[ApprovalStep]:
        """Get the current pending step"""
        for step in self.steps:
            if step.status == "pending" and step.required:
                return step
        return None


@dataclass
class ModelVersion:
    """A version of a model"""
    version: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Model artifact
    model_path: str = ""
    model_size_bytes: int = 0
    checksum: str = ""
    
    # Training info
    training_config: Dict[str, Any] = field(default_factory=dict)
    training_duration_seconds: float = 0.0
    
    # Performance
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Validation
    validation_results: Dict[str, Any] = field(default_factory=dict)
    is_validated: bool = False
    
    # Lineage
    training_dataset_id: Optional[str] = None
    feature_ids: List[str] = field(default_factory=list)
    parent_model_id: Optional[str] = None
    parent_version: Optional[str] = None
    
    # Approval
    approval_workflow: Optional[ApprovalWorkflow] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "model_path": self.model_path,
            "model_size_bytes": self.model_size_bytes,
            "checksum": self.checksum,
            "training_config": self.training_config,
            "training_duration_seconds": self.training_duration_seconds,
            "metrics": self.metrics,
            "validation_results": self.validation_results,
            "is_validated": self.is_validated,
            "training_dataset_id": self.training_dataset_id,
            "feature_ids": self.feature_ids,
            "parent_model_id": self.parent_model_id,
            "parent_version": self.parent_version,
            "approval_workflow": self.approval_workflow.to_dict() if self.approval_workflow else None,
        }


@dataclass
class RegisteredModel:
    """A registered model in the registry"""
    id: str
    name: str
    description: str
    model_type: ModelType
    
    # Versions
    current_version: str = "1.0.0"
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    
    # Status
    status: ModelStatus = ModelStatus.DRAFT
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    
    # Usage
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Deployment
    production_deployment_id: Optional[str] = None
    deployment_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance tracking
    inference_count: int = 0
    last_inference_at: Optional[datetime] = None
    avg_inference_time_ms: float = 0.0
    
    # Monitoring
    drift_score: Optional[float] = None
    last_monitored_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type.value,
            "current_version": self.current_version,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "status": self.status.value,
            "config": self.config,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "owner": self.owner,
            "tags": self.tags,
            "production_deployment_id": self.production_deployment_id,
            "deployment_history": self.deployment_history,
            "inference_count": self.inference_count,
            "last_inference_at": self.last_inference_at.isoformat() if self.last_inference_at else None,
            "avg_inference_time_ms": self.avg_inference_time_ms,
            "drift_score": self.drift_score,
            "last_monitored_at": self.last_monitored_at.isoformat() if self.last_monitored_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def get_production_version(self) -> Optional[ModelVersion]:
        """Get the production version"""
        for version in self.versions.values():
            if version.approval_workflow and version.approval_workflow.status == "approved":
                return version
        return None


@dataclass
class DeploymentRecord:
    """Record of a model deployment"""
    deployment_id: str
    model_id: str
    version: str
    
    # Deployment info
    environment: str  # "production", "staging", "development"
    deployed_at: datetime = field(default_factory=datetime.utcnow)
    deployed_by: str = ""
    
    # Status
    status: str = "active"  # active, inactive, rolled_back, failed
    
    # Rollback
    rolled_back_at: Optional[datetime] = None
    rolled_back_by: str = ""
    rollback_reason: str = ""
    
    # Metrics
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "model_id": self.model_id,
            "version": self.version,
            "environment": self.environment,
            "deployed_at": self.deployed_at.isoformat(),
            "deployed_by": self.deployed_by,
            "status": self.status,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "rolled_back_by": self.rolled_back_by,
            "rollback_reason": self.rollback_reason,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ModelRegistry:
    """
    Model Registry for ML model lifecycle management.
    
    Features:
    - Model registration and versioning
    - Candidate management
    - Production deployment
    - Archive management
    - Rollback support
    - Approval workflow
    - Performance tracking
    """
    
    def __init__(self, storage_path: str = "data/model_registry"):
        self._storage_path = storage_path
        self._models: Dict[str, RegisteredModel] = {}
        self._deployments: Dict[str, DeploymentRecord] = {}
        self._workflows: Dict[str, ApprovalWorkflow] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load model registry"""
        registry_file = f"{self._storage_path}/registry.json"
        
        try:
            if os.path.exists(registry_file):
                with open(registry_file, "r") as f:
                    data = json.load(f)
                
                # Load models
                for model_data in data.get("models", []):
                    model_data["created_at"] = datetime.fromisoformat(model_data["created_at"])
                    model_data["updated_at"] = datetime.fromisoformat(model_data["updated_at"])
                    if model_data.get("last_inference_at"):
                        model_data["last_inference_at"] = datetime.fromisoformat(model_data["last_inference_at"])
                    if model_data.get("last_monitored_at"):
                        model_data["last_monitored_at"] = datetime.fromisoformat(model_data["last_monitored_at"])
                    
                    # Parse versions
                    for v_data in model_data.get("versions", {}).values():
                        v_data["created_at"] = datetime.fromisoformat(v_data["created_at"])
                        
                        # Parse approval workflow
                        if v_data.get("approval_workflow"):
                            wf_data = v_data["approval_workflow"]
                            wf_data["created_at"] = datetime.fromisoformat(wf_data["created_at"])
                            wf_data["updated_at"] = datetime.fromisoformat(wf_data["updated_at"])
                            if wf_data.get("completed_at"):
                                wf_data["completed_at"] = datetime.fromisoformat(wf_data["completed_at"])
                            
                            for step in wf_data.get("steps", []):
                                if step.get("approved_at"):
                                    step["approved_at"] = datetime.fromisoformat(step["approved_at"])
                            wf_data["steps"] = [ApprovalStep(**s) for s in wf_data.get("steps", [])]
                            v_data["approval_workflow"] = ApprovalWorkflow(**wf_data)
                        
                        v_data["created_at"] = datetime.fromisoformat(v_data["created_at"])
                        v_data["created_at"] = datetime.fromisoformat(v_data.get("created_at", datetime.utcnow().isoformat()))
                    
                    model_data["versions"] = {
                        k: ModelVersion(**v) for k, v in model_data.get("versions", {}).items()
                    }
                    
                    model = RegisteredModel(**model_data)
                    self._models[model.id] = model
                
                # Load deployments
                for dep_data in data.get("deployments", []):
                    dep_data["deployed_at"] = datetime.fromisoformat(dep_data["deployed_at"])
                    if dep_data.get("rolled_back_at"):
                        dep_data["rolled_back_at"] = datetime.fromisoformat(dep_data["rolled_back_at"])
                    deployment = DeploymentRecord(**dep_data)
                    self._deployments[deployment.deployment_id] = deployment
                
                logger.info(f"Loaded {len(self._models)} models and {len(self._deployments)} deployments")
        except Exception as e:
            logger.warning(f"Could not load registry: {e}")
    
    def _save_registry(self) -> None:
        """Save model registry"""
        registry_file = f"{self._storage_path}/registry.json"
        
        data = {
            "models": [m.to_dict() for m in self._models.values()],
            "deployments": [d.to_dict() for d in self._deployments.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(registry_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Model Registration
    def register_model(
        self,
        name: str,
        description: str,
        model_type: ModelType,
        owner: str = "",
        tags: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        input_schema: Optional[Dict[str, str]] = None,
        output_schema: Optional[Dict[str, str]] = None,
    ) -> RegisteredModel:
        """Register a new model"""
        model = RegisteredModel(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            model_type=model_type,
            owner=owner,
            tags=tags or [],
            config=config or {},
            input_schema=input_schema or {},
            output_schema=output_schema or {},
        )
        
        self._models[model.id] = model
        self._save_registry()
        
        logger.info(f"Registered model: {name}")
        return model
    
    def add_version(
        self,
        model_id: str,
        version: str,
        model_path: str,
        metrics: Dict[str, float],
        created_by: str = "",
        training_config: Optional[Dict[str, Any]] = None,
        training_dataset_id: Optional[str] = None,
        feature_ids: Optional[List[str]] = None,
        parent_version: Optional[str] = None,
    ) -> Optional[ModelVersion]:
        """Add a new version to a model"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        if version in model.versions:
            logger.warning(f"Version {version} already exists")
            return None
        
        # Compute checksum
        checksum = ""
        try:
            with open(model_path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()
            model_size = os.path.getsize(model_path)
        except Exception:
            model_size = 0
        
        version_obj = ModelVersion(
            version=version,
            created_by=created_by,
            model_path=model_path,
            model_size_bytes=model_size,
            checksum=checksum,
            training_config=training_config or {},
            metrics=metrics,
            training_dataset_id=training_dataset_id,
            feature_ids=feature_ids or [],
            parent_model_id=model_id if parent_version else None,
            parent_version=parent_version,
        )
        
        model.versions[version] = version_obj
        model.current_version = version
        model.updated_at = datetime.utcnow()
        
        self._save_registry()
        return version_obj
    
    def get_model(self, model_id: str) -> Optional[RegisteredModel]:
        """Get a model by ID"""
        return self._models.get(model_id)
    
    def get_version(self, model_id: str, version: str) -> Optional[ModelVersion]:
        """Get a specific version"""
        model = self._models.get(model_id)
        if not model:
            return None
        return model.versions.get(version)
    
    # Approval Workflow
    def create_approval_workflow(
        self,
        model_id: str,
        version: str,
        workflow_name: str,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[ApprovalWorkflow]:
        """Create an approval workflow for a model version"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        version_obj = model.versions.get(version)
        if not version_obj:
            return None
        
        # Default workflow steps
        if not steps:
            steps = [
                {"name": "Technical Review", "approver_role": "quant", "required": True},
                {"name": "Risk Assessment", "approver_role": "risk_manager", "required": True},
                {"name": "Final Approval", "approver_role": "admin", "required": True},
            ]
        
        workflow_steps = []
        for i, step_data in enumerate(steps):
            step = ApprovalStep(
                step_id=str(uuid.uuid4()),
                name=step_data.get("name", f"Step {i+1}"),
                approver_role=step_data.get("approver_role", "admin"),
                required=step_data.get("required", True),
                auto_approve_conditions=step_data.get("auto_approve_conditions", {}),
            )
            workflow_steps.append(step)
        
        workflow = ApprovalWorkflow(
            workflow_id=str(uuid.uuid4()),
            name=workflow_name,
            description=f"Approval workflow for {model.name} v{version}",
            steps=workflow_steps,
        )
        
        version_obj.approval_workflow = workflow
        model.updated_at = datetime.utcnow()
        self._save_registry()
        
        return workflow
    
    def submit_for_approval(
        self,
        model_id: str,
        version: str,
        submitted_by: str,
    ) -> bool:
        """Submit a model version for approval"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        version_obj = model.versions.get(version)
        if not version_obj or not version_obj.approval_workflow:
            return False
        
        workflow = version_obj.approval_workflow
        workflow.status = "in_progress"
        workflow.updated_at = datetime.utcnow()
        
        model.status = ModelStatus.VALIDATING
        model.updated_at = datetime.utcnow()
        self._save_registry()
        
        logger.info(f"Submitted {model.name} v{version} for approval")
        return True
    
    def approve_step(
        self,
        model_id: str,
        version: str,
        step_id: str,
        approver: str,
        comment: str = "",
    ) -> bool:
        """Approve a workflow step"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        version_obj = model.versions.get(version)
        if not version_obj or not version_obj.approval_workflow:
            return False
        
        workflow = version_obj.approval_workflow
        
        for step in workflow.steps:
            if step.step_id == step_id:
                step.status = "approved"
                step.approver = approver
                step.approved_at = datetime.utcnow()
                step.comment = comment
                break
        
        workflow.updated_at = datetime.utcnow()
        
        # Check if all required steps are approved
        if workflow.is_complete():
            workflow.status = "approved"
            workflow.completed_at = datetime.utcnow()
            model.status = ModelStatus.APPROVED
        
        model.updated_at = datetime.utcnow()
        self._save_registry()
        
        return True
    
    def reject_workflow(
        self,
        model_id: str,
        version: str,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Reject the approval workflow"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        version_obj = model.versions.get(version)
        if not version_obj or not version_obj.approval_workflow:
            return False
        
        workflow = version_obj.approval_workflow
        workflow.status = "rejected"
        workflow.completed_at = datetime.utcnow()
        workflow.updated_at = datetime.utcnow()
        
        # Add rejection to current step
        current_step = workflow.get_current_step()
        if current_step:
            current_step.status = "rejected"
            current_step.approver = rejected_by
            current_step.comment = reason
        
        model.status = ModelStatus.CANDIDATE
        model.updated_at = datetime.utcnow()
        self._save_registry()
        
        logger.info(f"Rejected {model.name} v{version}: {reason}")
        return True
    
    # Deployment
    def deploy(
        self,
        model_id: str,
        version: str,
        environment: str = "production",
        deployed_by: str = "",
    ) -> Optional[DeploymentRecord]:
        """Deploy a model version"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        version_obj = model.versions.get(version)
        if not version_obj:
            return None
        
        # Check if approved
        if version_obj.approval_workflow and version_obj.approval_workflow.status != "approved":
            logger.warning("Model version must be approved before deployment")
            return None
        
        # Create deployment record
        deployment = DeploymentRecord(
            deployment_id=str(uuid.uuid4()),
            model_id=model_id,
            version=version,
            environment=environment,
            deployed_by=deployed_by,
        )
        
        self._deployments[deployment.deployment_id] = deployment
        
        # Update model
        model.production_deployment_id = deployment.deployment_id
        model.status = ModelStatus.PRODUCTION
        model.updated_at = datetime.utcnow()
        
        # Add to deployment history
        model.deployment_history.append({
            "deployment_id": deployment.deployment_id,
            "version": version,
            "deployed_at": deployment.deployed_at.isoformat(),
            "deployed_by": deployed_by,
        })
        
        self._save_registry()
        
        logger.info(f"Deployed {model.name} v{version} to {environment}")
        return deployment
    
    # Rollback
    def rollback(
        self,
        model_id: str,
        target_version: Optional[str] = None,
        reason: str = "",
        rolled_back_by: str = "",
    ) -> Optional[DeploymentRecord]:
        """Rollback to a previous version"""
        model = self._models.get(model_id)
        if not model:
            return None
        
        # Get current deployment
        current_deployment = None
        if model.production_deployment_id:
            current_deployment = self._deployments.get(model.production_deployment_id)
        
        # Determine target version
        if target_version is None:
            # Find previous production version
            sorted_versions = sorted(
                [(v, obj) for v, obj in model.versions.items() if v != model.current_version],
                key=lambda x: x[1].created_at,
                reverse=True,
            )
            if sorted_versions:
                target_version = sorted_versions[0][0]
            else:
                logger.warning("No previous version to rollback to")
                return None
        
        # Verify target version exists
        if target_version not in model.versions:
            logger.warning(f"Target version {target_version} not found")
            return None
        
        # Mark current deployment as rolled back
        if current_deployment:
            current_deployment.status = "rolled_back"
            current_deployment.rolled_back_at = datetime.utcnow()
            current_deployment.rolled_back_by = rolled_back_by
            current_deployment.rollback_reason = reason
        
        # Deploy target version
        new_deployment = self.deploy(
            model_id=model_id,
            version=target_version,
            environment="production",
            deployed_by=rolled_back_by,
        )
        
        if new_deployment:
            new_deployment.rollback_reason = f"Rollback from v{model.current_version}: {reason}"
        
        return new_deployment
    
    def get_rollback_candidates(
        self,
        model_id: str,
    ) -> List[ModelVersion]:
        """Get versions that can be rolled back to"""
        model = self._models.get(model_id)
        if not model:
            return []
        
        candidates = []
        for version, version_obj in model.versions.items():
            # Can rollback to approved versions that were previously deployed
            if version != model.current_version:
                if version_obj.approval_workflow and version_obj.approval_workflow.status == "approved":
                    candidates.append(version_obj)
        
        return sorted(candidates, key=lambda v: v.created_at, reverse=True)
    
    # Archive
    def archive(
        self,
        model_id: str,
        version: Optional[str] = None,
        reason: str = "",
    ) -> bool:
        """Archive a model or version"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        if version:
            # Archive specific version
            if version in model.versions:
                # Remove from active use
                if model.current_version == version:
                    model.current_version = ""
                model.status = ModelStatus.ARCHIVED
        else:
            # Archive entire model
            model.status = ModelStatus.ARCHIVED
        
        model.updated_at = datetime.utcnow()
        self._save_registry()
        
        logger.info(f"Archived model: {model.name}")
        return True
    
    # Performance Tracking
    def record_inference(
        self,
        model_id: str,
        version: Optional[str] = None,
        latency_ms: float = 0.0,
        error: bool = False,
    ) -> bool:
        """Record model inference"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        version_str = version or model.current_version
        version_obj = model.versions.get(version_str)
        
        model.inference_count += 1
        model.last_inference_at = datetime.utcnow()
        
        # Update average latency
        n = model.inference_count
        model.avg_inference_time_ms = (
            (model.avg_inference_time_ms * (n - 1) + latency_ms) / n
        )
        
        if version_obj:
            version_obj.metrics["inference_count"] = model.inference_count
        
        # Update deployment metrics
        if model.production_deployment_id:
            dep = self._deployments.get(model.production_deployment_id)
            if dep:
                dep.request_count += 1
                if error:
                    dep.error_count += 1
        
        self._save_registry()
        return True
    
    def update_drift_score(
        self,
        model_id: str,
        drift_score: float,
    ) -> bool:
        """Update model drift score"""
        model = self._models.get(model_id)
        if not model:
            return False
        
        model.drift_score = drift_score
        model.last_monitored_at = datetime.utcnow()
        self._save_registry()
        
        # Alert if drift is high
        if drift_score > 0.5:
            logger.warning(f"High drift detected for model {model.name}: {drift_score}")
        
        return True
    
    # Search and Retrieval
    def search_models(
        self,
        query: Optional[str] = None,
        model_types: Optional[List[ModelType]] = None,
        statuses: Optional[List[ModelStatus]] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
        limit: int = 50,
    ) -> List[RegisteredModel]:
        """Search models"""
        results = list(self._models.values())
        
        if query:
            query_lower = query.lower()
            results = [
                m for m in results
                if query_lower in m.name.lower()
                or query_lower in m.description.lower()
            ]
        
        if model_types:
            results = [m for m in results if m.model_type in model_types]
        
        if statuses:
            results = [m for m in results if m.status in statuses]
        
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]
        
        if owner:
            results = [m for m in results if owner.lower() in m.owner.lower()]
        
        # Sort by inference count
        results.sort(key=lambda m: m.inference_count, reverse=True)
        return results[:limit]
    
    def get_production_models(self) -> List[RegisteredModel]:
        """Get all production models"""
        return [m for m in self._models.values() if m.status == ModelStatus.PRODUCTION]
    
    def get_candidate_models(self) -> List[RegisteredModel]:
        """Get all candidate models"""
        return [m for m in self._models.values() if m.status == ModelStatus.CANDIDATE]
    
    def get_archived_models(self) -> List[RegisteredModel]:
        """Get all archived models"""
        return [m for m in self._models.values() if m.status == ModelStatus.ARCHIVED]
    
    def get_deployment_history(
        self,
        model_id: str,
    ) -> List[DeploymentRecord]:
        """Get deployment history for a model"""
        model = self._models.get(model_id)
        if not model:
            return []
        
        return [
            self._deployments.get(dep["deployment_id"])
            for dep in model.deployment_history
            if self._deployments.get(dep["deployment_id"])
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        models = list(self._models.values())
        
        return {
            "total_models": len(models),
            "by_type": {
                mtype.value: sum(1 for m in models if m.model_type == mtype)
                for mtype in ModelType
            },
            "by_status": {
                status.value: sum(1 for m in models if m.status == status)
                for status in ModelStatus
            },
            "production_models": sum(1 for m in models if m.status == ModelStatus.PRODUCTION),
            "total_versions": sum(len(m.versions) for m in models),
            "total_deployments": len(self._deployments),
            "active_deployments": sum(1 for d in self._deployments.values() if d.status == "active"),
            "total_inferences": sum(m.inference_count for m in models),
        }


import os
