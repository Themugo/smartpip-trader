"""
Configuration API Routes
=========================

Provides endpoints for configuration management.
"""

import time
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["Configuration"])


# ============= Parameter Definitions =============

class ParameterDefinition(BaseModel):
    name: str
    param_type: str
    default_value: Optional[Any] = None
    description: str = ""
    group: str = "general"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    required: bool = False
    secret: bool = False


# ============= Configuration Values =============

class ConfigValueUpdate(BaseModel):
    name: str
    value: Any
    reason: str = ""


class ConfigBatchUpdate(BaseModel):
    values: Dict[str, Any]
    reason: str = ""


class OverrideRequest(BaseModel):
    name: str
    value: Any
    duration_seconds: float = 3600


# ============= Profiles =============

class CreateProfileRequest(BaseModel):
    name: str
    profile_type: str  # strategy, risk, workspace, custom
    config_data: Dict[str, Any]
    description: str = ""


class ActivateProfileRequest(BaseModel):
    profile_id: str


# ============= Secrets =============

class SetSecretRequest(BaseModel):
    name: str
    value: str
    description: str = ""


# ============= Feature Flags =============

class CreateFlagRequest(BaseModel):
    name: str
    description: str = ""
    enabled: bool = False


class UpdateFlagRequest(BaseModel):
    name: str
    enabled: bool


# ============= Approval =============

class ApprovalSubmitRequest(BaseModel):
    changes: Dict[str, Any]
    approvers: List[str]
    reason: str = ""


class ApprovalActionRequest(BaseModel):
    comment: str = ""


# ============= Snapshot =============

class CreateSnapshotRequest(BaseModel):
    description: str


class RestoreSnapshotRequest(BaseModel):
    snapshot_id: str
    reason: str = ""


# ============= Rollback =============

class RollbackRequest(BaseModel):
    version_number: int
    reason: str = ""


# ============= Routes =============

@router.get("/")
async def get_all_config():
    """Get all configuration values"""
    from config import config_service
    
    return {
        "environment": config_service.get_environment().value,
        "current_version": config_service.get_current_version().__dict__ if config_service.get_current_version() else None,
        "config": config_service.get_all(),
        "overrides": config_service.get_overrides(),
    }


@router.get("/parameters")
async def list_parameters(group: Optional[str] = None):
    """List parameter definitions"""
    from config import config_service, ParameterType
    
    params = config_service.list_parameters(group)
    
    return {
        "parameters": [
            {
                "name": p.name,
                "type": p.param_type.value,
                "default": p.default_value,
                "description": p.description,
                "group": p.group,
                "required": p.required,
                "secret": p.secret
            }
            for p in params
        ]
    }


@router.post("/parameters")
async def register_parameter(param: ParameterDefinition):
    """Register a new parameter"""
    from config import config_service, ParameterType as PT
    
    type_map = {
        "string": PT.STRING,
        "integer": PT.INTEGER,
        "float": PT.FLOAT,
        "boolean": PT.BOOLEAN,
        "json": PT.JSON,
        "secret": PT.SECRET,
    }
    
    param_type = type_map.get(param.param_type, PT.STRING)
    
    from config.core import ConfigParameter
    config_param = ConfigParameter(
        name=param.name,
        param_type=param_type,
        default_value=param.default_value,
        description=param.description,
        group=param.group,
        min_value=param.min_value,
        max_value=param.max_value,
        allowed_values=param.allowed_values,
        required=param.required,
        secret=param.secret
    )
    
    config_service.register_parameter(config_param)
    
    return {"success": True, "parameter": param.name}


@router.get("/{name}")
async def get_config_value(name: str, default: Optional[Any] = None):
    """Get a configuration value"""
    from config import config_service
    
    value = config_service.get(name, default)
    
    if value is None and default is None:
        raise HTTPException(status_code=404, detail=f"Parameter '{name}' not found")
    
    return {"name": name, "value": value}


@router.put("/{name}")
async def set_config_value(
    name: str,
    value: Any = Body(...),
    user: str = Query("api", description="User making the change"),
    reason: str = Query("", description="Reason for change")
):
    """Set a configuration value"""
    from config import config_service
    from config.core import ValidationError
    
    try:
        config_service.set(name, value, user, reason)
        return {"success": True, "name": name, "value": value}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def batch_update_config(
    batch: ConfigBatchUpdate,
    user: str = Query("api")
):
    """Set multiple configuration values"""
    from config import config_service
    from config.core import ValidationError
    
    errors = config_service.set_many(batch.values, user, batch.reason)
    
    if errors:
        return {
            "success": False,
            "errors": [{"parameter": e.parameter, "message": e.message} for e in errors]
        }
    
    return {"success": True, "updated": len(batch.values)}


# ============= Overrides =============

@router.post("/overrides")
async def set_override(override: OverrideRequest, user: str = Query("api")):
    """Set a temporary override"""
    from config import config_service
    
    config_service.set_override(override.name, override.value, override.duration_seconds)
    
    return {
        "success": True,
        "name": override.name,
        "expires_in_seconds": override.duration_seconds
    }


@router.delete("/overrides/{name}")
async def clear_override(name: str):
    """Clear a temporary override"""
    from config import config_service
    
    success = config_service.clear_override(name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"No override found for '{name}'")
    
    return {"success": True}


# ============= Versions =============

@router.get("/versions/")
async def list_versions(limit: int = Query(100)):
    """Get version history"""
    from config import config_service
    
    versions = config_service.get_versions(limit)
    
    return {
        "versions": [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "status": v.status.value,
                "description": v.description,
                "is_immutable": v.is_immutable
            }
            for v in versions
        ]
    }


@router.get("/versions/current")
async def get_current_version():
    """Get current version info"""
    from config import config_service
    
    version = config_service.get_current_version()
    
    if not version:
        raise HTTPException(status_code=404, detail="No current version")
    
    return version.__dict__


@router.post("/rollback")
async def rollback(request: RollbackRequest, user: str = Query("api")):
    """Rollback to a specific version"""
    from config import config_service
    
    success = config_service.rollback(request.version_number, user, request.reason)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Version {request.version_number} not found")
    
    return {"success": True, "version_number": request.version_number}


# ============= Snapshots =============

@router.post("/snapshots")
async def create_snapshot(request: CreateSnapshotRequest, user: str = Query("api")):
    """Create an immutable snapshot"""
    from config import config_service
    
    snapshot = config_service.create_snapshot(request.description, user)
    
    return snapshot.to_dict()


@router.get("/snapshots/")
async def list_snapshots(limit: int = Query(100)):
    """List snapshots"""
    from config import config_service
    
    snapshots = config_service.list_snapshots(limit)
    
    return {
        "snapshots": [s.to_dict() for s in snapshots]
    }


@router.post("/snapshots/restore")
async def restore_snapshot(request: RestoreSnapshotRequest, user: str = Query("api")):
    """Restore from a snapshot"""
    from config import config_service
    
    success = config_service.restore_snapshot(request.snapshot_id, user, request.reason)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Snapshot '{request.snapshot_id}' not found")
    
    return {"success": True, "snapshot_id": request.snapshot_id}


# ============= Profiles =============

@router.get("/profiles/")
async def list_profiles(profile_type: Optional[str] = None):
    """List configuration profiles"""
    from config import config_service
    
    profiles = config_service.list_profiles(profile_type)
    
    return {
        "profiles": [p.to_dict() for p in profiles]
    }


@router.post("/profiles")
async def create_profile(request: CreateProfileRequest, user: str = Query("api")):
    """Create a configuration profile"""
    from config import config_service
    
    profile = config_service.create_profile(
        name=request.name,
        profile_type=request.profile_type,
        config_data=request.config_data,
        user=user,
        description=request.description
    )
    
    return profile.to_dict()


@router.post("/profiles/activate")
async def activate_profile(request: ActivateProfileRequest, user: str = Query("api")):
    """Activate a profile"""
    from config import config_service
    
    success = config_service.activate_profile(request.profile_id, user)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Profile '{request.profile_id}' not found")
    
    return {"success": True}


# ============= Secrets =============

@router.get("/secrets/")
async def list_secrets():
    """List secrets (without values)"""
    from config import config_service
    
    return {
        "secrets": config_service.list_secrets()
    }


@router.post("/secrets")
async def set_secret(request: SetSecretRequest, user: str = Query("api")):
    """Store an encrypted secret"""
    from config import config_service
    
    secret = config_service.set_secret(request.name, request.value, user, request.description)
    
    return {
        "success": True,
        "name": request.name,
        "version": secret.version
    }


@router.get("/secrets/{name}")
async def get_secret(name: str):
    """Get decrypted secret value"""
    from config import config_service
    
    value = config_service.get_secret(name)
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")
    
    return {"name": name, "value": value}


# ============= Feature Flags =============

@router.get("/flags/")
async def list_flags():
    """List all feature flags"""
    from config import config_service
    
    flags = config_service.list_flags()
    
    return {
        "flags": [
            {
                "name": f.name,
                "enabled": f.enabled,
                "rollout_percentage": f.rollout_percentage,
                "description": f.description,
                "created_at": f.created_at,
                "updated_at": f.updated_at
            }
            for f in flags
        ]
    }


@router.post("/flags")
async def create_flag(request: CreateFlagRequest, user: str = Query("api")):
    """Create a feature flag"""
    from config import config_service
    
    flag = config_service.create_feature_flag(
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        user=user
    )
    
    return {
        "success": True,
        "flag_id": flag.flag_id,
        "name": flag.name
    }


@router.put("/flags/{name}")
async def update_flag(
    name: str,
    request: UpdateFlagRequest,
    user: str = Query("api")
):
    """Update a feature flag"""
    from config import config_service
    
    success = config_service.set_flag(name, request.enabled, user)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")
    
    return {"success": True, "name": name, "enabled": request.enabled}


@router.get("/flags/{name}/check")
async def check_flag(name: str, user_id: Optional[str] = None):
    """Check if a flag is enabled"""
    from config import config_service
    
    context = {"user_id": user_id} if user_id else None
    enabled = config_service.is_flag_enabled(name, context)
    
    return {"name": name, "enabled": enabled}


# ============= Approval Workflow =============

@router.get("/approvals/")
async def list_pending_approvals():
    """Get pending approval requests"""
    from config import config_service
    
    requests = config_service.get_pending_approvals()
    
    return {
        "requests": [
            {
                "request_id": r.request_id,
                "version_id": r.version_id,
                "submitted_by": r.submitted_by,
                "submitted_at": r.submitted_at,
                "approvers": r.approvers,
                "changes_summary": r.changes_summary
            }
            for r in requests
        ]
    }


@router.post("/approvals")
async def submit_for_approval(request: ApprovalSubmitRequest, user: str = Query("api")):
    """Submit changes for approval"""
    from config import config_service
    
    approval_request = config_service.submit_for_approval(
        changes=request.changes,
        user=user,
        approvers=request.approvers,
        reason=request.reason
    )
    
    return {
        "success": True,
        "request_id": approval_request.request_id,
        "version_id": approval_request.version_id
    }


@router.post("/approvals/{request_id}/approve")
async def approve_request(
    request_id: str,
    action: ApprovalActionRequest,
    approver: str = Query(...)
):
    """Approve a request"""
    from config import config_service
    
    success = config_service.approve_request(request_id, approver, action.comment)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found or already processed")
    
    return {"success": True}


@router.post("/approvals/{request_id}/reject")
async def reject_request(
    request_id: str,
    action: ApprovalActionRequest,
    approver: str = Query(...)
):
    """Reject a request"""
    from config import config_service
    
    success = config_service.reject_request(request_id, approver, action.comment)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found or already processed")
    
    return {"success": True}


# ============= Audit Trail =============

@router.get("/audit/")
async def get_audit_trail(
    since: Optional[float] = None,
    until: Optional[float] = None,
    user: Optional[str] = None,
    limit: int = Query(100)
):
    """Get audit trail entries"""
    from config import config_service
    
    entries = config_service.get_audit_trail(since, until, user, limit)
    
    return {
        "entries": [e.to_dict() for e in entries]
    }


# ============= Import/Export =============

@router.get("/export")
async def export_config(include_secrets: bool = Query(False)):
    """Export configuration"""
    from config import config_service
    
    return config_service.export_config(include_secrets)


@router.post("/import")
async def import_config(
    data: Dict[str, Any],
    merge: bool = Query(False),
    user: str = Query("api")
):
    """Import configuration"""
    from config import config_service
    
    errors = config_service.import_config(data, user, merge)
    
    return {
        "success": len(errors) == 0,
        "errors": errors
    }


# ============= Environment =============

@router.get("/environment")
async def get_environment():
    """Get current environment"""
    from config import config_service
    
    return {"environment": config_service.get_environment().value}


@router.post("/environment/{env}")
async def set_environment(env: str):
    """Set current environment"""
    from config import config_service, ConfigEnvironment
    
    try:
        environment = ConfigEnvironment(env)
        config_service.set_environment(environment)
        return {"success": True, "environment": env}
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment: {env}. Valid values: development, staging, production, testing"
        )
