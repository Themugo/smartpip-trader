"""
Configuration Core
=================

Centralized configuration service with version history, validation, and secrets management.
"""

import hashlib
import json
import time
import uuid
import logging
import threading
import os
import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Type
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigEnvironment(Enum):
    """Configuration environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigStatus(Enum):
    """Configuration status"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ParameterType(Enum):
    """Parameter data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    SECRET = "secret"  # Encrypted at rest


@dataclass
class ConfigParameter:
    """Definition of a configuration parameter"""
    name: str
    param_type: ParameterType
    default_value: Any = None
    description: str = ""
    group: str = "general"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    required: bool = False
    secret: bool = False
    validation_regex: Optional[str] = None
    env_override: bool = True  # Allow environment variable override


@dataclass
class ConfigVersion:
    """A version of the configuration"""
    version_id: str
    version_number: int
    created_at: float
    created_by: str
    checksum: str  # SHA256 of config content
    environment: ConfigEnvironment
    status: ConfigStatus
    description: str = ""
    is_immutable: bool = False


@dataclass
class ConfigSnapshot:
    """An immutable snapshot of the configuration"""
    snapshot_id: str
    version_id: str
    created_at: float
    created_by: str
    checksum: str
    config_data: Dict[str, Any]
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "version_id": self.version_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "checksum": self.checksum,
            "config_data": self.config_data,
            "description": self.description,
        }


@dataclass
class ConfigProfile:
    """Configuration profile (strategy, risk, workspace, etc.)"""
    profile_id: str
    name: str
    profile_type: str  # strategy, risk, workspace, custom
    config_data: Dict[str, Any]
    version_id: str
    environment: ConfigEnvironment
    created_at: float
    updated_at: float
    created_by: str
    is_active: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "profile_type": self.profile_type,
            "config_data": self.config_data,
            "version_id": self.version_id,
            "environment": self.environment.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "description": self.description,
        }


@dataclass
class AuditEntry:
    """Audit trail entry"""
    entry_id: str
    timestamp: float
    user: str
    action: str  # create, update, delete, activate, rollback
    parameter_path: str  # dot-notation path
    old_value: Any = None
    new_value: Any = None
    environment: Optional[ConfigEnvironment] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "user": self.user,
            "action": self.action,
            "parameter_path": self.parameter_path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "environment": self.environment.value if self.environment else None,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalRequest:
    """Request for configuration approval"""
    request_id: str
    version_id: str
    submitted_by: str
    submitted_at: float
    approvers: List[str]
    status: str  # pending, approved, rejected, cancelled
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[float] = None
    review_comment: str = ""
    changes_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureFlag:
    """Feature flag definition"""
    flag_id: str
    name: str
    description: str = ""
    enabled: bool = False
    rollout_percentage: float = 100.0  # 0-100
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "system"
    environments: List[ConfigEnvironment] = field(default_factory=list)
    
    def is_enabled(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if flag is enabled for given context"""
        if not self.enabled:
            return False
        
        # Check rollout percentage
        if context and "user_id" in context:
            # Deterministic rollout based on user_id
            hash_val = hash(int(context["user_id"])) % 100
            if hash_val > self.rollout_percentage:
                return False
        
        return True


@dataclass
class SecretValue:
    """Encrypted secret value"""
    secret_id: str
    name: str
    encrypted_value: str  # Base64 encoded encrypted value
    version: int = 1
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"
    last_rotated: Optional[float] = None
    expires_at: Optional[float] = None
    description: str = ""


@dataclass
class ConfigGroup:
    """Group of configuration parameters"""
    group_id: str
    name: str
    description: str = ""
    parameters: Dict[str, ConfigParameter] = field(default_factory=dict)
    parent_group: Optional[str] = None
    order: int = 0


class ValidationError(Exception):
    """Configuration validation error"""
    def __init__(self, parameter: str, message: str):
        self.parameter = parameter
        self.message = message
        super().__init__(f"{parameter}: {message}")


class ConfigService:
    """
    Centralized configuration service.
    
    Features:
    - Environment profiles (dev, staging, production)
    - Version history with rollback
    - Parameter validation
    - Audit trail
    - Encrypted secrets
    - Feature flags
    - Approval workflow
    - Temporary overrides
    - Snapshots
    - Import/Export
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._lock = threading.RLock()
        self._environment = ConfigEnvironment.DEVELOPMENT
        
        # Configuration data
        self._config: Dict[str, Any] = {}
        self._parameters: Dict[str, ConfigParameter] = {}
        self._groups: Dict[str, ConfigGroup] = {}
        
        # Versioning
        self._versions: List[ConfigVersion] = []
        self._current_version_id: Optional[str] = None
        self._version_number = 0
        
        # Profiles
        self._profiles: Dict[str, ConfigProfile] = {}
        
        # Secrets (encrypted)
        self._secrets: Dict[str, SecretValue] = {}
        self._secret_key = self._get_or_create_secret_key()
        
        # Feature flags
        self._feature_flags: Dict[str, FeatureFlag] = {}
        
        # Overrides (temporary)
        self._overrides: Dict[str, tuple[Any, float]] = {}  # value, expires_at
        
        # Audit trail
        self._audit_trail: List[AuditEntry] = []
        self._max_audit_entries = 10000
        
        # Approval workflow
        self._approval_requests: Dict[str, ApprovalRequest] = {}
        
        # Callbacks for config changes
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
        # Snapshots
        self._snapshots: Dict[str, ConfigSnapshot] = {}
        
        self._initialized = True
        
        # Initialize default groups
        self._init_default_groups()
    
    def _get_or_create_secret_key(self) -> bytes:
        """Get or create encryption key for secrets"""
        key_path = os.path.expanduser("~/.smartpip/config.key")
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        
        # Generate new key (in production, use proper key management)
        key = os.urandom(32)
        with open(key_path, "wb") as f:
            f.write(key)
        os.chmod(key_path, 0o600)
        return key
    
    def _init_default_groups(self) -> None:
        """Initialize default parameter groups"""
        groups = [
            ConfigGroup("general", "General", "General settings"),
            ConfigGroup("api", "API", "API configuration"),
            ConfigGroup("trading", "Trading", "Trading parameters"),
            ConfigGroup("risk", "Risk Management", "Risk settings"),
            ConfigGroup("strategy", "Strategy", "Strategy parameters"),
            ConfigGroup("execution", "Execution", "Execution settings"),
            ConfigGroup("model", "Model", "AI/ML model settings"),
            ConfigGroup("observability", "Observability", "Monitoring settings"),
            ConfigGroup("security", "Security", "Security settings"),
        ]
        
        for group in groups:
            self._groups[group.name] = group
    
    # ============ Environment ============
    
    def set_environment(self, env: ConfigEnvironment) -> None:
        """Set current environment"""
        with self._lock:
            self._environment = env
    
    def get_environment(self) -> ConfigEnvironment:
        """Get current environment"""
        return self._environment
    
    # ============ Parameters ============
    
    def register_parameter(self, param: ConfigParameter) -> None:
        """Register a configuration parameter"""
        with self._lock:
            self._parameters[param.name] = param
            if param.name not in self._config:
                self._config[param.name] = param.default_value
    
    def get_parameter(self, name: str) -> Optional[ConfigParameter]:
        """Get parameter definition"""
        return self._parameters.get(name)
    
    def list_parameters(self, group: Optional[str] = None) -> List[ConfigParameter]:
        """List parameters, optionally filtered by group"""
        params = list(self._parameters.values())
        if group:
            params = [p for p in params if p.group == group]
        return params
    
    # ============ Values ============
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get configuration value"""
        with self._lock:
            # Check for temporary override
            if name in self._overrides:
                value, expires_at = self._overrides[name]
                if time.time() < expires_at:
                    return value
                else:
                    del self._overrides[name]
            
            # Check environment variable override
            param = self._parameters.get(name)
            if param and param.env_override:
                env_value = os.environ.get(f"SMARTPIP_{name.upper().replace('.', '_')}")
                if env_value is not None:
                    return self._cast_value(env_value, param.param_type)
            
            return self._config.get(name, default)
    
    def set(
        self,
        name: str,
        value: Any,
        user: str = "system",
        reason: str = "",
        validate: bool = True
    ) -> None:
        """Set configuration value"""
        with self._lock:
            old_value = self._config.get(name)
            
            if validate:
                self._validate_value(name, value)
            
            self._config[name] = value
            
            # Create new version
            self._create_version(f"Updated {name}", user)
            
            # Add audit entry
            self._add_audit(
                user=user,
                action="update",
                parameter_path=name,
                old_value=old_value,
                new_value=value,
                reason=reason
            )
            
            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(name, old_value, value)
                except Exception as e:
                    logger.error(f"Config change callback error: {e}")
    
    def _cast_value(self, value: str, param_type: ParameterType) -> Any:
        """Cast string value to parameter type"""
        if param_type == ParameterType.INTEGER:
            return int(value)
        elif param_type == ParameterType.FLOAT:
            return float(value)
        elif param_type == ParameterType.BOOLEAN:
            return value.lower() in ("true", "1", "yes")
        elif param_type == ParameterType.JSON:
            return json.loads(value)
        return value
    
    def _validate_value(self, name: str, value: Any) -> None:
        """Validate a configuration value"""
        param = self._parameters.get(name)
        if not param:
            return  # Unknown parameter, skip validation
        
        # Type validation
        expected_type = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool,
            ParameterType.JSON: dict,
        }.get(param.param_type, str)
        
        if param.param_type != ParameterType.SECRET and not isinstance(value, expected_type):
            raise ValidationError(name, f"Expected {param.param_type.value}, got {type(value).__name__}")
        
        # Range validation
        if param.min_value is not None and value < param.min_value:
            raise ValidationError(name, f"Value {value} below minimum {param.min_value}")
        
        if param.max_value is not None and value > param.max_value:
            raise ValidationError(name, f"Value {value} above maximum {param.max_value}")
        
        # Allowed values
        if param.allowed_values and value not in param.allowed_values:
            raise ValidationError(name, f"Value {value} not in allowed values: {param.allowed_values}")
        
        # Regex validation
        if param.validation_regex:
            import re
            if not re.match(param.validation_regex, str(value)):
                raise ValidationError(name, f"Value does not match pattern: {param.validation_regex}")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        with self._lock:
            return self._config.copy()
    
    def set_many(self, values: Dict[str, Any], user: str = "system", reason: str = "") -> List[ValidationError]:
        """Set multiple values, returning validation errors"""
        errors = []
        
        for name, value in values.items():
            try:
                self.set(name, value, user, reason, validate=True)
            except ValidationError as e:
                errors.append(e)
        
        return errors
    
    # ============ Temporary Overrides ============
    
    def set_override(self, name: str, value: Any, duration_seconds: float = 3600) -> None:
        """Set a temporary override"""
        with self._lock:
            expires_at = time.time() + duration_seconds
            self._overrides[name] = (value, expires_at)
    
    def clear_override(self, name: str) -> bool:
        """Clear a temporary override"""
        with self._lock:
            if name in self._overrides:
                del self._overrides[name]
                return True
            return False
    
    def get_overrides(self) -> Dict[str, Any]:
        """Get all active overrides"""
        with self._lock:
            return {
                name: value
                for name, (value, expires_at) in self._overrides.items()
                if time.time() < expires_at
            }
    
    # ============ Versioning ============
    
    def _create_version(self, description: str, user: str) -> ConfigVersion:
        """Create a new configuration version"""
        self._version_number += 1
        version_id = str(uuid.uuid4())
        
        # Calculate checksum
        config_json = json.dumps(self._config, sort_keys=True)
        checksum = hashlib.sha256(config_json.encode()).hexdigest()
        
        version = ConfigVersion(
            version_id=version_id,
            version_number=self._version_number,
            created_at=time.time(),
            created_by=user,
            checksum=checksum,
            environment=self._environment,
            status=ConfigStatus.ACTIVE,
            description=description
        )
        
        self._versions.append(version)
        self._current_version_id = version_id
        
        return version
    
    def get_current_version(self) -> Optional[ConfigVersion]:
        """Get current version"""
        with self._lock:
            if not self._current_version_id:
                return None
            return next(
                (v for v in self._versions if v.version_id == self._current_version_id),
                None
            )
    
    def get_versions(self, limit: int = 100) -> List[ConfigVersion]:
        """Get version history"""
        with self._lock:
            return sorted(self._versions, key=lambda v: v.version_number, reverse=True)[:limit]
    
    def rollback(self, version_number: int, user: str = "system", reason: str = "") -> bool:
        """Rollback to a specific version"""
        with self._lock:
            version = next(
                (v for v in self._versions if v.version_number == version_number),
                None
            )
            
            if not version:
                return False
            
            # Store current config as new version before rollback
            old_config = self._config.copy()
            
            # Mark current as deprecated
            current = self.get_current_version()
            if current:
                current.status = ConfigStatus.DEPRECATED
            
            # Create new version with description
            self._create_version(f"Rollback to version {version_number}", user)
            
            # Add audit entry
            self._add_audit(
                user=user,
                action="rollback",
                parameter_path="",
                old_value=old_config,
                new_value=self._config,
                reason=reason
            )
            
            return True
    
    # ============ Snapshots ============
    
    def create_snapshot(self, description: str, user: str = "system") -> ConfigSnapshot:
        """Create an immutable snapshot"""
        with self._lock:
            snapshot_id = str(uuid.uuid4())
            version = self.get_current_version()
            version_id = version.version_id if version else ""
            
            config_json = json.dumps(self._config, sort_keys=True)
            checksum = hashlib.sha256(config_json.encode()).hexdigest()
            
            snapshot = ConfigSnapshot(
                snapshot_id=snapshot_id,
                version_id=version_id,
                created_at=time.time(),
                created_by=user,
                checksum=checksum,
                config_data=self._config.copy(),
                description=description
            )
            
            self._snapshots[snapshot_id] = snapshot
            return snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[ConfigSnapshot]:
        """Get a snapshot"""
        return self._snapshots.get(snapshot_id)
    
    def restore_snapshot(self, snapshot_id: str, user: str = "system", reason: str = "") -> bool:
        """Restore from a snapshot"""
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
            if not snapshot:
                return False
            
            old_config = self._config.copy()
            self._config = snapshot.config_data.copy()
            
            # Create new version
            self._create_version(f"Restored from snapshot {snapshot_id[:8]}", user)
            
            # Add audit entry
            self._add_audit(
                user=user,
                action="restore_snapshot",
                parameter_path="",
                old_value=old_config,
                new_value=self._config,
                reason=reason
            )
            
            return True
    
    def list_snapshots(self, limit: int = 100) -> List[ConfigSnapshot]:
        """List snapshots"""
        with self._lock:
            return sorted(self._snapshots.values(), key=lambda s: s.created_at, reverse=True)[:limit]
    
    # ============ Profiles ============
    
    def create_profile(
        self,
        name: str,
        profile_type: str,
        config_data: Dict[str, Any],
        user: str = "system",
        description: str = ""
    ) -> ConfigProfile:
        """Create a configuration profile"""
        with self._lock:
            profile_id = str(uuid.uuid4())
            version = self.get_current_version()
            
            profile = ConfigProfile(
                profile_id=profile_id,
                name=name,
                profile_type=profile_type,
                config_data=config_data,
                version_id=version.version_id if version else "",
                environment=self._environment,
                created_at=time.time(),
                updated_at=time.time(),
                created_by=user,
                description=description
            )
            
            self._profiles[profile_id] = profile
            
            self._add_audit(
                user=user,
                action="create_profile",
                parameter_path=name,
                new_value=config_data,
                reason=description
            )
            
            return profile
    
    def get_profile(self, profile_id: str) -> Optional[ConfigProfile]:
        """Get a profile"""
        return self._profiles.get(profile_id)
    
    def list_profiles(self, profile_type: Optional[str] = None) -> List[ConfigProfile]:
        """List profiles"""
        with self._lock:
            profiles = list(self._profiles.values())
            if profile_type:
                profiles = [p for p in profiles if p.profile_type == profile_type]
            return profiles
    
    def activate_profile(self, profile_id: str, user: str = "system") -> bool:
        """Activate a profile"""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile:
                return False
            
            # Deactivate all profiles of same type
            for p in self._profiles.values():
                if p.profile_type == profile.profile_type:
                    p.is_active = False
            
            # Activate this profile
            profile.is_active = True
            profile.updated_at = time.time()
            
            # Apply profile config
            old_config = self._config.copy()
            self._config.update(profile.config_data)
            
            # Create new version
            self._create_version(f"Activated profile: {profile.name}", user)
            
            self._add_audit(
                user=user,
                action="activate_profile",
                parameter_path=profile.name,
                old_value=old_config,
                new_value=self._config
            )
            
            return True
    
    # ============ Secrets ============
    
    def set_secret(self, name: str, value: str, user: str = "system", description: str = "") -> SecretValue:
        """Store an encrypted secret"""
        with self._lock:
            # Simple XOR encryption (in production, use proper encryption like Fernet)
            key = self._secret_key
            encrypted = base64.b64encode(
                bytes(a ^ b for a, b in zip(value.encode(), key * (len(value) // len(key) + 1)))
            ).decode()
            
            if name in self._secrets:
                secret = self._secrets[name]
                secret.encrypted_value = encrypted
                secret.version += 1
                secret.last_rotated = time.time()
            else:
                secret = SecretValue(
                    secret_id=str(uuid.uuid4()),
                    name=name,
                    encrypted_value=encrypted,
                    created_by=user,
                    description=description
                )
                self._secrets[name] = secret
            
            return secret
    
    def get_secret(self, name: str) -> Optional[str]:
        """Get decrypted secret value"""
        with self._lock:
            secret = self._secrets.get(name)
            if not secret:
                return None
            
            # Check expiration
            if secret.expires_at and time.time() > secret.expires_at:
                return None
            
            # Decrypt
            key = self._secret_key
            encrypted = base64.b64decode(secret.encrypted_value)
            decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1))).decode()
            
            return decrypted
    
    def list_secrets(self) -> List[Dict[str, Any]]:
        """List secrets (without values)"""
        with self._lock:
            return [
                {
                    "name": s.name,
                    "version": s.version,
                    "created_at": s.created_at,
                    "last_rotated": s.last_rotated,
                    "expires_at": s.expires_at,
                    "description": s.description
                }
                for s in self._secrets.values()
            ]
    
    # ============ Feature Flags ============
    
    def create_feature_flag(
        self,
        name: str,
        description: str = "",
        enabled: bool = False,
        user: str = "system"
    ) -> FeatureFlag:
        """Create a feature flag"""
        with self._lock:
            flag = FeatureFlag(
                flag_id=str(uuid.uuid4()),
                name=name,
                description=description,
                enabled=enabled,
                created_by=user
            )
            
            self._feature_flags[name] = flag
            
            self._add_audit(
                user=user,
                action="create_flag",
                parameter_path=name,
                new_value=enabled
            )
            
            return flag
    
    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get feature flag"""
        return self._feature_flags.get(name)
    
    def set_flag(self, name: str, enabled: bool, user: str = "system") -> bool:
        """Enable or disable a feature flag"""
        with self._lock:
            flag = self._feature_flags.get(name)
            if not flag:
                return False
            
            old_enabled = flag.enabled
            flag.enabled = enabled
            flag.updated_at = time.time()
            
            self._add_audit(
                user=user,
                action="update_flag",
                parameter_path=name,
                old_value=old_enabled,
                new_value=enabled
            )
            
            return True
    
    def is_flag_enabled(self, name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if feature flag is enabled"""
        flag = self._feature_flags.get(name)
        if not flag:
            return False
        return flag.is_enabled(context)
    
    def list_flags(self) -> List[FeatureFlag]:
        """List all feature flags"""
        return list(self._feature_flags.values())
    
    # ============ Audit Trail ============
    
    def _add_audit(
        self,
        user: str,
        action: str,
        parameter_path: str,
        old_value: Any = None,
        new_value: Any = None,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """Add audit entry"""
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=time.time(),
            user=user,
            action=action,
            parameter_path=parameter_path,
            old_value=old_value,
            new_value=new_value,
            environment=self._environment,
            reason=reason,
            metadata=metadata or {}
        )
        
        self._audit_trail.append(entry)
        
        # Trim old entries
        while len(self._audit_trail) > self._max_audit_entries:
            self._audit_trail.pop(0)
        
        return entry
    
    def get_audit_trail(
        self,
        since: Optional[float] = None,
        until: Optional[float] = None,
        user: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit trail entries"""
        entries = list(self._audit_trail)
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        if until:
            entries = [e for e in entries if e.timestamp <= until]
        if user:
            entries = [e for e in entries if e.user == user]
        
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # ============ Approval Workflow ============
    
    def submit_for_approval(
        self,
        changes: Dict[str, Any],
        user: str,
        approvers: List[str],
        reason: str = ""
    ) -> ApprovalRequest:
        """Submit changes for approval"""
        with self._lock:
            # Create version in draft status
            self._version_number += 1
            version_id = str(uuid.uuid4())
            
            config_json = json.dumps(self._config, sort_keys=True)
            checksum = hashlib.sha256(config_json.encode()).hexdigest()
            
            version = ConfigVersion(
                version_id=version_id,
                version_number=self._version_number,
                created_at=time.time(),
                created_by=user,
                checksum=checksum,
                environment=self._environment,
                status=ConfigStatus.PENDING_APPROVAL,
                description=f"Pending approval: {reason}"
            )
            
            self._versions.append(version)
            
            request = ApprovalRequest(
                request_id=str(uuid.uuid4()),
                version_id=version_id,
                submitted_by=user,
                submitted_at=time.time(),
                approvers=approvers,
                status="pending",
                changes_summary=changes
            )
            
            self._approval_requests[request.request_id] = request
            
            return request
    
    def approve_request(self, request_id: str, approver: str, comment: str = "") -> bool:
        """Approve a request"""
        with self._lock:
            request = self._approval_requests.get(request_id)
            if not request or request.status != "pending":
                return False
            
            request.status = "approved"
            request.reviewed_by = approver
            request.reviewed_at = time.time()
            request.review_comment = comment
            
            # Update version status
            version = next((v for v in self._versions if v.version_id == request.version_id), None)
            if version:
                version.status = ConfigStatus.ACTIVE
            
            self._current_version_id = request.version_id
            
            return True
    
    def reject_request(self, request_id: str, approver: str, comment: str = "") -> bool:
        """Reject a request"""
        with self._lock:
            request = self._approval_requests.get(request_id)
            if not request or request.status != "pending":
                return False
            
            request.status = "rejected"
            request.reviewed_by = approver
            request.reviewed_at = time.time()
            request.review_comment = comment
            
            return True
    
    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get pending approval requests"""
        return [
            r for r in self._approval_requests.values()
            if r.status == "pending"
        ]
    
    # ============ Import/Export ============
    
    def export_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration"""
        with self._lock:
            export = {
                "version": self._version_number,
                "environment": self._environment.value,
                "exported_at": time.time(),
                "config": self._config.copy(),
                "parameters": {
                    name: {
                        "type": p.param_type.value,
                        "default": p.default_value,
                        "description": p.description,
                        "group": p.group,
                        "required": p.required,
                        "secret": p.secret
                    }
                    for name, p in self._parameters.items()
                },
                "feature_flags": {
                    name: {
                        "enabled": f.enabled,
                        "rollout_percentage": f.rollout_percentage,
                        "description": f.description
                    }
                    for name, f in self._feature_flags.items()
                }
            }
            
            if include_secrets:
                export["secrets"] = self.list_secrets()
            else:
                export["secrets"] = []
            
            return export
    
    def import_config(self, data: Dict[str, Any], user: str = "system", merge: bool = False) -> List[str]:
        """Import configuration"""
        errors = []
        
        with self._lock:
            try:
                if not merge:
                    self._config = {}
                
                # Import config
                if "config" in data:
                    for key, value in data["config"].items():
                        try:
                            self.set(key, value, user, "import", validate=False)
                        except Exception as e:
                            errors.append(f"{key}: {str(e)}")
                
                # Import feature flags
                if "feature_flags" in data:
                    for name, flag_data in data["feature_flags"].items():
                        if name not in self._feature_flags:
                            self.create_feature_flag(
                                name=name,
                                description=flag_data.get("description", ""),
                                enabled=flag_data.get("enabled", False),
                                user=user
                            )
                
                # Create version for import
                self._create_version(f"Imported configuration", user)
                
            except Exception as e:
                errors.append(str(e))
        
        return errors
    
    # ============ Callbacks ============
    
    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Register callback for configuration changes"""
        self._change_callbacks.append(callback)


# Global configuration service instance
config_service = ConfigService()
