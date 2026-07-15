"""
Audit Models

Comprehensive audit logging for:
- User actions
- System events
- Security events
- Compliance tracking
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditEventType(Enum):
    """Audit event types"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_VERIFIED = "mfa_verified"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    DEVICE_TRUSTED = "device_trusted"
    DEVICE_DISTRUSTED = "device_distrusted"
    
    # Organization events
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    ORG_SUSPENDED = "org_suspended"
    ORG_DELETED = "org_deleted"
    ORG_BILLING_UPDATED = "org_billing_updated"
    ORG_TIER_CHANGED = "org_tier_changed"
    
    # Team events
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    TEAM_DELETED = "team_deleted"
    TEAM_MEMBER_INVITED = "team_member_invited"
    TEAM_MEMBER_JOINED = "team_member_joined"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_ROLE_CHANGED = "team_role_changed"
    
    # Workspace events
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_UPDATED = "workspace_updated"
    WORKSPACE_DELETED = "workspace_deleted"
    WORKSPACE_SHARED = "workspace_shared"
    WORKSPACE_UNSHARED = "workspace_unshared"
    
    # Strategy events
    STRATEGY_CREATED = "strategy_created"
    STRATEGY_UPDATED = "strategy_updated"
    STRATEGY_DELETED = "strategy_deleted"
    STRATEGY_SHARED = "strategy_shared"
    STRATEGY_EXECUTED = "strategy_executed"
    STRATEGY_STOPPED = "strategy_stopped"
    
    # Trading events
    TRADE_EXECUTED = "trade_executed"
    TRADE_CLOSED = "trade_closed"
    TRADE_CANCELLED = "trade_cancelled"
    RISK_LIMIT_HIT = "risk_limit_hit"
    
    # Backtest events
    BACKTEST_STARTED = "backtest_started"
    BACKTEST_COMPLETED = "backtest_completed"
    BACKTEST_FAILED = "backtest_failed"
    
    # Report events
    REPORT_GENERATED = "report_generated"
    REPORT_EXPORTED = "report_exported"
    
    # Plugin events
    PLUGIN_INSTALLED = "plugin_installed"
    PLUGIN_UNINSTALLED = "plugin_uninstalled"
    PLUGIN_UPDATED = "plugin_updated"
    
    # API events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_RATE_LIMIT_EXCEEDED = "api_rate_limit_exceeded"
    
    # Security events
    SECURITY_ALERT = "security_alert"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # System events
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    FEATURE_FLAG_CHANGED = "feature_flag_changed"


class AuditSeverity(Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Single audit event"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    
    # Actor (who performed the action)
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Target (what was affected)
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    workspace_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # Action details
    action: str = ""
    description: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    
    # Result
    success: bool = True
    error_message: Optional[str] = None
    
    # Context
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    service: str = "smartpip-trader"
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        action: str = "",
        description: str = "",
        **kwargs
    ) -> "AuditEvent":
        """Create a new audit event"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            description=description,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "organization_id": self.organization_id,
            "team_id": self.team_id,
            "workspace_id": self.workspace_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "success": self.success,
            "error_message": self.error_message,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "service": self.service,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class AuditLog:
    """Audit log collection"""
    organization_id: str
    
    # Retention settings
    retention_days: int = 90
    compression_enabled: bool = True
    
    # Filters
    event_types: List[AuditEventType] = field(default_factory=list)
    user_ids: List[str] = field(default_factory=list)
    resource_types: List[str] = field(default_factory=list)
    
    # Pagination
    page: int = 1
    page_size: int = 50
    
    # Results
    events: List[AuditEvent] = field(default_factory=list)
    total_count: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_filter(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        user_ids: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> None:
        """Add filters to the audit log"""
        if event_types:
            self.event_types.extend(event_types)
        if user_ids:
            self.user_ids.extend(user_ids)
        if resource_types:
            self.resource_types.extend(resource_types)
    
    def get_filters(self) -> Dict[str, Any]:
        """Get current filters"""
        return {
            "event_types": [e.value for e in self.event_types],
            "user_ids": self.user_ids,
            "resource_types": self.resource_types,
            "page": self.page,
            "page_size": self.page_size,
        }
    
    def next_page(self) -> None:
        """Move to next page"""
        self.page += 1
    
    def prev_page(self) -> None:
        """Move to previous page"""
        if self.page > 1:
            self.page -= 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "filters": self.get_filters(),
            "events": [e.to_dict() for e in self.events],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": (self.total_count + self.page_size - 1) // self.page_size,
        }


class AuditLogger:
    """Centralized audit logging service"""
    
    def __init__(self):
        self._handlers: List[callable] = []
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 100
        self._flush_interval = 5  # seconds
    
    def add_handler(self, handler: callable) -> None:
        """Add an audit event handler"""
        self._handlers.append(handler)
    
    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        **kwargs
    ) -> AuditEvent:
        """Log an audit event"""
        event = AuditEvent.create(
            event_type=event_type,
            severity=severity,
            **kwargs
        )
        
        # Buffer the event
        self._buffer.append(event)
        
        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            self.flush()
        
        # Process immediately for critical events
        if severity == AuditSeverity.CRITICAL:
            self._process_event(event)
        
        return event
    
    def _process_event(self, event: AuditEvent) -> None:
        """Process an audit event through all handlers"""
        for handler in self._handlers:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors break audit logging
    
    def flush(self) -> None:
        """Flush buffered events"""
        while self._buffer:
            event = self._buffer.pop(0)
            self._process_event(event)
    
    # Convenience methods
    def log_login(self, user_id: str, success: bool, ip_address: str, **kwargs) -> AuditEvent:
        """Log login attempt"""
        return self.log(
            event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            **kwargs
        )
    
    def log_mfa(self, user_id: str, action: str, ip_address: str, **kwargs) -> AuditEvent:
        """Log MFA event"""
        event_type = {
            "enabled": AuditEventType.MFA_ENABLED,
            "disabled": AuditEventType.MFA_DISABLED,
            "verified": AuditEventType.MFA_VERIFIED,
        }.get(action, AuditEventType.MFA_ENABLED)
        
        return self.log(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs
        )
    
    def log_organization(self, org_id: str, action: str, user_id: str, **kwargs) -> AuditEvent:
        """Log organization event"""
        event_type = {
            "created": AuditEventType.ORG_CREATED,
            "updated": AuditEventType.ORG_UPDATED,
            "suspended": AuditEventType.ORG_SUSPENDED,
            "deleted": AuditEventType.ORG_DELETED,
            "billing_updated": AuditEventType.ORG_BILLING_UPDATED,
            "tier_changed": AuditEventType.ORG_TIER_CHANGED,
        }.get(action, AuditEventType.ORG_UPDATED)
        
        return self.log(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            organization_id=org_id,
            **kwargs
        )
    
    def log_team(self, team_id: str, org_id: str, action: str, user_id: str, **kwargs) -> AuditEvent:
        """Log team event"""
        event_type = {
            "created": AuditEventType.TEAM_CREATED,
            "updated": AuditEventType.TEAM_UPDATED,
            "deleted": AuditEventType.TEAM_DELETED,
            "member_invited": AuditEventType.TEAM_MEMBER_INVITED,
            "member_joined": AuditEventType.TEAM_MEMBER_JOINED,
            "member_removed": AuditEventType.TEAM_MEMBER_REMOVED,
            "role_changed": AuditEventType.TEAM_ROLE_CHANGED,
        }.get(action, AuditEventType.TEAM_UPDATED)
        
        return self.log(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            organization_id=org_id,
            team_id=team_id,
            **kwargs
        )
    
    def log_strategy(self, strategy_id: str, action: str, user_id: str, org_id: str, **kwargs) -> AuditEvent:
        """Log strategy event"""
        event_type = {
            "created": AuditEventType.STRATEGY_CREATED,
            "updated": AuditEventType.STRATEGY_UPDATED,
            "deleted": AuditEventType.STRATEGY_DELETED,
            "shared": AuditEventType.STRATEGY_SHARED,
            "executed": AuditEventType.STRATEGY_EXECUTED,
            "stopped": AuditEventType.STRATEGY_STOPPED,
        }.get(action, AuditEventType.STRATEGY_UPDATED)
        
        return self.log(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            organization_id=org_id,
            resource_type="strategy",
            resource_id=strategy_id,
            **kwargs
        )
    
    def log_security(self, event_type: str, user_id: str, description: str, severity: AuditSeverity = AuditSeverity.WARNING, **kwargs) -> AuditEvent:
        """Log security event"""
        audit_type = {
            "alert": AuditEventType.SECURITY_ALERT,
            "permission_denied": AuditEventType.PERMISSION_DENIED,
            "suspicious": AuditEventType.SUSPICIOUS_ACTIVITY,
        }.get(event_type, AuditEventType.SECURITY_ALERT)
        
        return self.log(
            event_type=audit_type,
            severity=severity,
            user_id=user_id,
            description=description,
            **kwargs
        )
    
    def log_trade(self, trade_id: str, action: str, user_id: str, org_id: str, **kwargs) -> AuditEvent:
        """Log trading event"""
        event_type = {
            "executed": AuditEventType.TRADE_EXECUTED,
            "closed": AuditEventType.TRADE_CLOSED,
            "cancelled": AuditEventType.TRADE_CANCELLED,
        }.get(action, AuditEventType.TRADE_EXECUTED)
        
        return self.log(
            event_type=event_type,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            organization_id=org_id,
            resource_type="trade",
            resource_id=trade_id,
            **kwargs
        )


# Global audit logger instance
audit_logger = AuditLogger()
