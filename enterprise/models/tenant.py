"""
Tenant Models - Multi-Tenant Architecture

Implements secure multi-tenant data isolation with:
- Organization hierarchy
- Team management
- Workspace isolation
- Role-based access control
- Billing accounts
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class OrganizationStatus(Enum):
    """Organization lifecycle states"""
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class SubscriptionTier(Enum):
    """Subscription tiers"""
    FREE = "free"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class TeamStatus(Enum):
    """Team membership status"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LEFT = "left"


class WorkspaceType(Enum):
    """Workspace types"""
    PRIVATE = "private"
    SHARED = "shared"
    ORGANIZATION = "organization"


@dataclass
class Permission:
    """Permission definition"""
    code: str
    name: str
    description: str
    resource: str
    action: str
    
    def __hash__(self):
        return hash(self.code)
    
    def __eq__(self, other):
        if isinstance(other, Permission):
            return self.code == other.code
        return False


# Predefined permissions
PERMISSIONS = {
    # Organization permissions
    "org:read": Permission("org:read", "View Organization", "View organization details", "organization", "read"),
    "org:write": Permission("org:write", "Manage Organization", "Update organization settings", "organization", "write"),
    "org:delete": Permission("org:delete", "Delete Organization", "Delete organization", "organization", "delete"),
    "org:billing": Permission("org:billing", "Manage Billing", "Manage billing and subscriptions", "organization", "billing"),
    "org:members": Permission("org:members", "Manage Members", "Invite and remove members", "organization", "members"),
    
    # Team permissions
    "team:read": Permission("team:read", "View Team", "View team details", "team", "read"),
    "team:write": Permission("team:write", "Manage Team", "Update team settings", "team", "write"),
    "team:delete": Permission("team:delete", "Delete Team", "Delete team", "team", "delete"),
    "team:members": Permission("team:members", "Manage Team Members", "Add and remove team members", "team", "members"),
    
    # Workspace permissions
    "workspace:read": Permission("workspace:read", "View Workspace", "View workspace content", "workspace", "read"),
    "workspace:write": Permission("workspace:write", "Edit Workspace", "Create and modify workspace content", "workspace", "write"),
    "workspace:delete": Permission("workspace:delete", "Delete Workspace", "Delete workspace", "workspace", "delete"),
    "workspace:share": Permission("workspace:share", "Share Workspace", "Share workspace with others", "workspace", "share"),
    
    # Strategy permissions
    "strategy:read": Permission("strategy:read", "View Strategies", "View trading strategies", "strategy", "read"),
    "strategy:write": Permission("strategy:write", "Create Strategies", "Create and modify strategies", "strategy", "write"),
    "strategy:delete": Permission("strategy:delete", "Delete Strategies", "Delete strategies", "strategy", "delete"),
    "strategy:execute": Permission("strategy:execute", "Execute Strategies", "Run trading strategies", "strategy", "execute"),
    "strategy:share": Permission("strategy:share", "Share Strategies", "Share strategies with team", "strategy", "share"),
    
    # Backtest permissions
    "backtest:read": Permission("backtest:read", "View Backtests", "View backtest results", "backtest", "read"),
    "backtest:write": Permission("backtest:write", "Run Backtests", "Run backtest simulations", "backtest", "write"),
    
    # Report permissions
    "report:read": Permission("report:read", "View Reports", "View reports and analytics", "report", "read"),
    "report:write": Permission("report:write", "Create Reports", "Create and share reports", "report", "write"),
    
    # Experiment permissions
    "experiment:read": Permission("experiment:read", "View Experiments", "View experiments", "experiment", "read"),
    "experiment:write": Permission("experiment:write", "Manage Experiments", "Create and modify experiments", "experiment", "write"),
    
    # Plugin permissions
    "plugin:read": Permission("plugin:read", "View Plugins", "View installed plugins", "plugin", "read"),
    "plugin:write": Permission("plugin:write", "Install Plugins", "Install and configure plugins", "plugin", "write"),
    
    # Admin permissions
    "admin:users": Permission("admin:users", "User Administration", "Manage all users", "admin", "users"),
    "admin:audit": Permission("admin:audit", "Audit Logs", "View audit logs", "admin", "audit"),
    "admin:settings": Permission("admin:settings", "System Settings", "Configure system settings", "admin", "settings"),
}


@dataclass
class UserRole:
    """Role with associated permissions"""
    role_id: str
    name: str
    description: str
    organization_id: str
    permissions: Set[str] = field(default_factory=set)
    is_system_role: bool = False
    is_default: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        organization_id: str,
        permissions: Optional[List[str]] = None,
    ) -> "UserRole":
        """Create a new role"""
        return cls(
            role_id=str(uuid.uuid4()),
            name=name,
            description=description,
            organization_id=organization_id,
            permissions=set(permissions) if permissions else set(),
        )
    
    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission"""
        return permission_code in self.permissions
    
    def grant_permission(self, permission_code: str) -> None:
        """Grant a permission to this role"""
        if permission_code in PERMISSIONS:
            self.permissions.add(permission_code)
    
    def revoke_permission(self, permission_code: str) -> None:
        """Revoke a permission from this role"""
        self.permissions.discard(permission_code)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "organization_id": self.organization_id,
            "permissions": list(self.permissions),
            "is_system_role": self.is_system_role,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# Predefined roles
DEFAULT_ROLES = {
    "owner": ["org:read", "org:write", "org:delete", "org:billing", "org:members",
              "team:read", "team:write", "team:delete", "team:members",
              "workspace:read", "workspace:write", "workspace:delete", "workspace:share",
              "strategy:read", "strategy:write", "strategy:delete", "strategy:execute", "strategy:share",
              "backtest:read", "backtest:write",
              "report:read", "report:write",
              "experiment:read", "experiment:write",
              "plugin:read", "plugin:write",
              "admin:users", "admin:audit", "admin:settings"],
    "admin": ["org:read", "org:members",
              "team:read", "team:write", "team:members",
              "workspace:read", "workspace:write", "workspace:delete", "workspace:share",
              "strategy:read", "strategy:write", "strategy:delete", "strategy:execute", "strategy:share",
              "backtest:read", "backtest:write",
              "report:read", "report:write",
              "experiment:read", "experiment:write",
              "plugin:read", "plugin:write",
              "admin:audit"],
    "trader": ["org:read",
               "team:read",
               "workspace:read", "workspace:write",
               "strategy:read", "strategy:write", "strategy:execute",
               "backtest:read", "backtest:write",
               "report:read",
               "experiment:read", "experiment:write"],
    "analyst": ["org:read",
                "team:read",
                "workspace:read",
                "strategy:read",
                "backtest:read",
                "report:read", "report:write",
                "experiment:read"],
    "viewer": ["org:read",
               "team:read",
               "workspace:read",
               "strategy:read",
               "backtest:read",
               "report:read"],
}


@dataclass
class Organization:
    """Organization entity"""
    org_id: str
    name: str
    slug: str
    status: OrganizationStatus
    subscription_tier: SubscriptionTier
    
    # Billing
    billing_account_id: Optional[str] = None
    billing_email: Optional[str] = None
    
    # Limits based on subscription
    max_users: int = 5
    max_teams: int = 2
    max_workspaces: int = 3
    max_storage_gb: int = 10
    max_api_calls_per_month: int = 10000
    
    # Features based on subscription
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trial_ends_at: Optional[datetime] = None
    
    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        name: str,
        owner_id: str,
        billing_email: Optional[str] = None,
    ) -> "Organization":
        """Create a new organization"""
        slug = cls._generate_slug(name)
        return cls(
            org_id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            status=OrganizationStatus.TRIAL,
            subscription_tier=SubscriptionTier.FREE,
            billing_email=billing_email,
            features=cls._get_tier_features(SubscriptionTier.FREE),
        )
    
    @staticmethod
    def _generate_slug(name: str) -> str:
        """Generate URL-safe slug from name"""
        slug = name.lower().replace(" ", "-")
        slug = "".join(c if c.isalnum() or c in "-_" else "" for c in slug)
        suffix = hashlib.md5(str(datetime.now(timezone.utc)).encode()).hexdigest()[:6]
        return f"{slug}-{suffix}"
    
    @staticmethod
    def _get_tier_features(tier: SubscriptionTier) -> Dict[str, bool]:
        """Get features enabled for a subscription tier"""
        features = {
            SubscriptionTier.FREE: {
                "basic_strategies": True,
                "1_strategy": True,
                "basic_backtesting": True,
                "community_support": True,
                "1_workspace": True,
                "100_api_calls_day": True,
            },
            SubscriptionTier.PROFESSIONAL: {
                "basic_strategies": True,
                "5_strategies": True,
                "advanced_backtesting": True,
                "email_support": True,
                "3_workspaces": True,
                "1000_api_calls_day": True,
                "export_csv": True,
                "basic_analytics": True,
            },
            SubscriptionTier.BUSINESS: {
                "basic_strategies": True,
                "unlimited_strategies": True,
                "advanced_backtesting": True,
                "walk_forward": True,
                "priority_support": True,
                "10_workspaces": True,
                "10000_api_calls_day": True,
                "export_excel": True,
                "advanced_analytics": True,
                "team_collaboration": True,
                "custom_indicators": True,
            },
            SubscriptionTier.ENTERPRISE: {
                "basic_strategies": True,
                "unlimited_strategies": True,
                "advanced_backtesting": True,
                "walk_forward": True,
                "hft_mode": True,
                "dedicated_support": True,
                "unlimited_workspaces": True,
                "unlimited_api_calls": True,
                "export_pdf": True,
                "custom_analytics": True,
                "full_team_management": True,
                "custom_indicators": True,
                "api_access": True,
                "sso": True,
                "audit_logs": True,
                "sla_guarantee": True,
                "custom_integrations": True,
            },
        }
        return features.get(tier, {})
    
    def has_feature(self, feature: str) -> bool:
        """Check if feature is enabled"""
        return self.features.get(feature, False)
    
    def update_tier(self, tier: SubscriptionTier) -> None:
        """Update subscription tier"""
        self.subscription_tier = tier
        self.features = self._get_tier_features(tier)
        
        # Update limits based on tier
        tier_limits = {
            SubscriptionTier.FREE: (5, 2, 3, 10, 10000),
            SubscriptionTier.PROFESSIONAL: (10, 5, 10, 50, 30000),
            SubscriptionTier.BUSINESS: (50, 20, 50, 200, 300000),
            SubscriptionTier.ENTERPRISE: (999999, 999999, 999999, 999999, 999999999),
        }
        limits = tier_limits.get(tier, tier_limits[SubscriptionTier.FREE])
        self.max_users = limits[0]
        self.max_teams = limits[1]
        self.max_workspaces = limits[2]
        self.max_storage_gb = limits[3]
        self.max_api_calls_per_month = limits[4]
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        result = {
            "org_id": self.org_id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status.value,
            "subscription_tier": self.subscription_tier.value,
            "features": self.features,
            "limits": {
                "max_users": self.max_users,
                "max_teams": self.max_teams,
                "max_workspaces": self.max_workspaces,
                "max_storage_gb": self.max_storage_gb,
                "max_api_calls_per_month": self.max_api_calls_per_month,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "settings": self.settings,
        }
        
        if include_sensitive:
            result["billing_account_id"] = self.billing_account_id
            result["billing_email"] = self.billing_email
            
        return result


@dataclass
class Team:
    """Team within an organization"""
    team_id: str
    organization_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        organization_id: str,
        name: str,
        created_by: str,
        description: str = "",
    ) -> "Team":
        """Create a new team"""
        return cls(
            team_id=str(uuid.uuid4()),
            organization_id=organization_id,
            name=name,
            description=description,
            created_by=created_by,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "settings": self.settings,
        }


@dataclass
class TeamMembership:
    """Team membership record"""
    membership_id: str
    team_id: str
    user_id: str
    role_id: str
    status: TeamStatus
    invited_by: str
    joined_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        team_id: str,
        user_id: str,
        role_id: str,
        invited_by: str,
    ) -> "TeamMembership":
        """Create a new membership"""
        return cls(
            membership_id=str(uuid.uuid4()),
            team_id=team_id,
            user_id=user_id,
            role_id=role_id,
            status=TeamStatus.PENDING,
            invited_by=invited_by,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "membership_id": self.membership_id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "status": self.status.value,
            "invited_by": self.invited_by,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Workspace:
    """Workspace for organizing work"""
    workspace_id: str
    organization_id: str
    name: str
    workspace_type: WorkspaceType
    owner_id: str
    
    # Optional fields with defaults
    team_id: Optional[str] = None
    
    # Sharing settings
    is_shared: bool = False
    shared_with_teams: List[str] = field(default_factory=list)
    
    # Namespace for data isolation
    namespace: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Limits
    max_strategies: int = 10
    max_storage_mb: int = 100
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        organization_id: str,
        name: str,
        owner_id: str,
        workspace_type: WorkspaceType = WorkspaceType.PRIVATE,
        team_id: Optional[str] = None,
    ) -> "Workspace":
        """Create a new workspace"""
        return cls(
            workspace_id=str(uuid.uuid4()),
            organization_id=organization_id,
            team_id=team_id,
            name=name,
            workspace_type=workspace_type,
            owner_id=owner_id,
        )
    
    def share_with_team(self, team_id: str) -> None:
        """Share workspace with a team"""
        if team_id not in self.shared_with_teams:
            self.shared_with_teams.append(team_id)
            self.is_shared = True
    
    def unshare_with_team(self, team_id: str) -> None:
        """Remove team from shared access"""
        if team_id in self.shared_with_teams:
            self.shared_with_teams.remove(team_id)
            self.is_shared = len(self.shared_with_teams) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "organization_id": self.organization_id,
            "team_id": self.team_id,
            "name": self.name,
            "workspace_type": self.workspace_type.value,
            "owner_id": self.owner_id,
            "is_shared": self.is_shared,
            "shared_with_teams": self.shared_with_teams,
            "namespace": self.namespace,
            "max_strategies": self.max_strategies,
            "max_storage_mb": self.max_storage_mb,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "settings": self.settings,
        }


@dataclass
class BillingAccount:
    """Billing account for an organization"""
    billing_id: str
    organization_id: str
    payment_method: str  # "card", "bank_transfer", "invoice"
    
    # Subscription details
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    subscription_status: str = "active"  # "active", "past_due", "canceled"
    
    # Billing info
    billing_name: Optional[str] = None
    billing_email: Optional[str] = None
    billing_address: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Usage tracking
    current_period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    api_calls_this_period: int = 0
    storage_used_gb: float = 0
    
    # Payment info
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    
    # History
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(cls, organization_id: str, billing_email: str) -> "BillingAccount":
        """Create a new billing account"""
        return cls(
            billing_id=str(uuid.uuid4()),
            organization_id=organization_id,
            payment_method="card",
            billing_email=billing_email,
            current_period_end=datetime.now(timezone.utc),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "billing_id": self.billing_id,
            "organization_id": self.organization_id,
            "payment_method": self.payment_method,
            "subscription_tier": self.subscription_tier.value,
            "subscription_status": self.subscription_status,
            "billing_name": self.billing_name,
            "billing_email": self.billing_email,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "api_calls_this_period": self.api_calls_this_period,
            "storage_used_gb": self.storage_used_gb,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TenantNamespace:
    """Data isolation namespace for a tenant"""
    namespace: str
    organization_id: str
    workspace_id: Optional[str] = None
    
    # Database connections (virtual)
    db_schema: str = ""
    
    # Isolation markers
    row_level_security_enabled: bool = True
    encryption_key_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def create(
        cls,
        organization_id: str,
        workspace_id: Optional[str] = None,
    ) -> "TenantNamespace":
        """Create a new tenant namespace"""
        namespace = f"org_{organization_id[:8]}"
        if workspace_id:
            namespace = f"{namespace}_ws_{workspace_id[:8]}"
        
        return cls(
            namespace=namespace,
            organization_id=organization_id,
            workspace_id=workspace_id,
            db_schema=namespace.replace("-", "_"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "db_schema": self.db_schema,
            "row_level_security_enabled": self.row_level_security_enabled,
            "created_at": self.created_at.isoformat(),
        }
