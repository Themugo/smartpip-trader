"""
Organization Manager

Handles organization lifecycle:
- Creation
- Updates
- Settings
- Member management
- Deletion
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from enterprise.models.tenant import (
    Organization,
    OrganizationStatus,
    SubscriptionTier,
    BillingAccount,
    UserRole,
    DEFAULT_ROLES,
)
from enterprise.models.audit import AuditLogger, AuditEventType, AuditSeverity
from enterprise.subscription.billing import SubscriptionManager, SubscriptionInfo


@dataclass
class OrganizationSettings:
    """Organization configuration settings"""
    organization_id: str
    
    # Branding
    logo_url: Optional[str] = None
    primary_color: str = "#3B82F6"
    
    # Trading settings
    default_market: str = "R_100"
    default_stake: float = 10.0
    auto_trading_enabled: bool = False
    max_concurrent_strategies: int = 5
    
    # Notification settings
    email_notifications: bool = True
    slack_webhook_url: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Security settings
    require_mfa: bool = False
    session_timeout_hours: int = 24
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    
    # Compliance settings
    require_approval_for_live: bool = False
    approval_threshold: float = 500.0  # Amount requiring approval
    approval_notifications: List[str] = field(default_factory=list)  # Emails
    
    # Regional settings
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    currency_display: str = "USD"
    
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "branding": {
                "logo_url": self.logo_url,
                "primary_color": self.primary_color,
            },
            "trading": {
                "default_market": self.default_market,
                "default_stake": self.default_stake,
                "auto_trading_enabled": self.auto_trading_enabled,
                "max_concurrent_strategies": self.max_concurrent_strategies,
            },
            "notifications": {
                "email_notifications": self.email_notifications,
                "slack_webhook_url": self.slack_webhook_url,
                "telegram_chat_id": self.telegram_chat_id,
            },
            "security": {
                "require_mfa": self.require_mfa,
                "session_timeout_hours": self.session_timeout_hours,
                "ip_whitelist_enabled": self.ip_whitelist_enabled,
                "ip_whitelist": self.ip_whitelist,
            },
            "compliance": {
                "require_approval_for_live": self.require_approval_for_live,
                "approval_threshold": self.approval_threshold,
                "approval_notifications": self.approval_notifications,
            },
            "regional": {
                "timezone": self.timezone,
                "date_format": self.date_format,
                "currency_display": self.currency_display,
            },
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class OrganizationMember:
    """Organization member information"""
    user_id: str
    organization_id: str
    role_id: str
    role_name: str
    email: str
    full_name: str
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[str] = None
    last_active: Optional[datetime] = None
    is_owner: bool = False
    is_admin: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "email": self.email,
            "full_name": self.full_name,
            "joined_at": self.joined_at.isoformat(),
            "invited_by": self.invited_by,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "is_owner": self.is_owner,
            "is_admin": self.is_admin,
        }


class OrganizationManager:
    """
    Manages organization lifecycle.
    
    Features:
    - Organization CRUD
    - Member management
    - Role assignment
    - Settings management
    - Trial management
    """
    
    def __init__(self):
        self._organizations: Dict[str, Organization] = {}
        self._org_by_slug: Dict[str, str] = {}  # slug -> org_id
        self._org_settings: Dict[str, OrganizationSettings] = {}
        self._org_members: Dict[str, List[str]] = {}  # org_id -> [user_ids]
        self._user_orgs: Dict[str, List[str]] = {}  # user_id -> [org_ids]
        self._org_roles: Dict[str, Dict[str, UserRole]] = {}  # org_id -> {role_id: UserRole}
        self._user_roles: Dict[str, Dict[str, str]] = {}  # user_id -> {org_id: role_id}
        self._billing_accounts: Dict[str, BillingAccount] = {}
        self._subscription_manager = SubscriptionManager()
        self._audit = AuditLogger()
    
    def create_organization(
        self,
        name: str,
        owner_id: str,
        owner_email: str,
        billing_email: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> Organization:
        """Create a new organization"""
        # Generate slug
        if not slug:
            slug = self._generate_slug(name)
        
        # Check slug uniqueness
        if slug in self._org_by_slug:
            raise ValueError(f"Organization slug '{slug}' already exists")
        
        # Create organization
        org = Organization.create(
            name=name,
            owner_id=owner_id,
            billing_email=billing_email or owner_email,
        )
        org.slug = slug
        
        self._organizations[org.org_id] = org
        self._org_by_slug[slug] = org.org_id
        
        # Create settings
        self._org_settings[org.org_id] = OrganizationSettings(
            organization_id=org.org_id,
        )
        
        # Initialize roles
        self._initialize_roles(org.org_id)
        
        # Add owner as member with owner role
        self._add_member(org.org_id, owner_id, owner_email, "owner")
        
        # Create billing account
        billing = BillingAccount.create(org.org_id, billing_email or owner_email)
        self._billing_accounts[org.org_id] = billing
        
        # Create trial subscription
        self._subscription_manager.create_subscription(
            org, SubscriptionTier.FREE, is_trial=True, trial_days=14
        )
        
        # Log creation
        self._audit.log_organization(
            org_id=org.org_id,
            action="created",
            user_id=owner_id,
            description=f"Organization created: {name}",
        )
        
        return org
    
    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        return self._organizations.get(org_id)
    
    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        org_id = self._org_by_slug.get(slug)
        return self._organizations.get(org_id) if org_id else None
    
    def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get all organizations for a user"""
        org_ids = self._user_orgs.get(user_id, [])
        return [self._organizations[oid] for oid in org_ids if oid in self._organizations]
    
    def update_organization(
        self,
        org_id: str,
        updates: Dict[str, Any],
        updated_by: str,
    ) -> Optional[Organization]:
        """Update organization details"""
        org = self._organizations.get(org_id)
        if not org:
            return None
        
        # Allowed updates
        allowed = ["name", "billing_email", "settings"]
        for key in allowed:
            if key in updates:
                if key == "name":
                    org.name = updates[key]
                elif key == "billing_email":
                    org.billing_email = updates[key]
        
        org.updated_at = datetime.utcnow()
        
        self._audit.log_organization(
            org_id=org_id,
            action="updated",
            user_id=updated_by,
            description=f"Organization updated: {', '.join(updates.keys())}",
        )
        
        return org
    
    def update_settings(
        self,
        org_id: str,
        settings: Dict[str, Any],
    ) -> Optional[OrganizationSettings]:
        """Update organization settings"""
        org_settings = self._org_settings.get(org_id)
        if not org_settings:
            return None
        
        # Update allowed settings
        for section, values in settings.items():
            if hasattr(org_settings, section):
                section_obj = getattr(org_settings, section)
                if isinstance(section_obj, dict):
                    section_obj.update(values)
        
        org_settings.updated_at = datetime.utcnow()
        return org_settings
    
    def get_settings(self, org_id: str) -> Optional[OrganizationSettings]:
        """Get organization settings"""
        return self._org_settings.get(org_id)
    
    def suspend_organization(
        self,
        org_id: str,
        reason: str,
        suspended_by: str,
    ) -> bool:
        """Suspend an organization"""
        org = self._organizations.get(org_id)
        if not org:
            return False
        
        org.status = OrganizationStatus.SUSPENDED
        org.updated_at = datetime.utcnow()
        
        self._audit.log_organization(
            org_id=org_id,
            action="suspended",
            user_id=suspended_by,
            description=f"Organization suspended: {reason}",
        )
        
        return True
    
    def delete_organization(self, org_id: str, deleted_by: str) -> bool:
        """Delete an organization (soft delete)"""
        org = self._organizations.get(org_id)
        if not org:
            return False
        
        org.status = OrganizationStatus.CLOSED
        org.updated_at = datetime.utcnow()
        
        self._audit.log_organization(
            org_id=org_id,
            action="deleted",
            user_id=deleted_by,
            description="Organization deleted",
        )
        
        return True
    
    # ─────────────────────────────────────────────────────────────
    # Member Management
    # ─────────────────────────────────────────────────────────────
    
    def _initialize_roles(self, org_id: str) -> None:
        """Initialize default roles for organization"""
        self._org_roles[org_id] = {}
        
        for role_name, permissions in DEFAULT_ROLES.items():
            role = UserRole.create(
                name=role_name,
                description=f"{role_name.capitalize()} role",
                organization_id=org_id,
                permissions=permissions,
                is_system_role=True,
                is_default=(role_name == "viewer"),
            )
            self._org_roles[org_id][role.role_id] = role
    
    def _add_member(
        self,
        org_id: str,
        user_id: str,
        email: str,
        role_name: str,
        invited_by: Optional[str] = None,
    ) -> bool:
        """Add member to organization"""
        # Get role
        role = self._get_role_by_name(org_id, role_name)
        if not role:
            return False
        
        # Add to index
        if user_id not in self._user_orgs:
            self._user_orgs[user_id] = []
        if org_id not in self._user_orgs[user_id]:
            self._user_orgs[user_id].append(org_id)
        
        if org_id not in self._org_members:
            self._org_members[org_id] = []
        if user_id not in self._org_members[org_id]:
            self._org_members[org_id].append(user_id)
        
        # Set role
        if user_id not in self._user_roles:
            self._user_roles[user_id] = {}
        self._user_roles[user_id][org_id] = role.role_id
        
        return True
    
    def add_member(
        self,
        org_id: str,
        user_id: str,
        email: str,
        role_name: str,
        added_by: str,
        invited_by: Optional[str] = None,
    ) -> bool:
        """Add member to organization with audit logging"""
        result = self._add_member(org_id, user_id, email, role_name, invited_by)
        
        if result:
            self._audit.log_organization(
                org_id=org_id,
                action="member_added",
                user_id=added_by,
                description=f"Member added: {email} as {role_name}",
                metadata={"new_member_id": user_id},
            )
        
        return result
    
    def remove_member(self, org_id: str, user_id: str, removed_by: str) -> bool:
        """Remove member from organization"""
        if org_id in self._org_members and user_id in self._org_members[org_id]:
            self._org_members[org_id].remove(user_id)
        
        if user_id in self._user_orgs and org_id in self._user_orgs[user_id]:
            self._user_orgs[user_id].remove(org_id)
        
        if user_id in self._user_roles and org_id in self._user_roles[user_id]:
            del self._user_roles[user_id][org_id]
        
        self._audit.log_organization(
            org_id=org_id,
            action="member_removed",
            user_id=removed_by,
            description=f"Member removed: {user_id}",
        )
        
        return True
    
    def update_member_role(
        self,
        org_id: str,
        user_id: str,
        new_role_name: str,
        updated_by: str,
    ) -> bool:
        """Update member's role"""
        role = self._get_role_by_name(org_id, new_role_name)
        if not role:
            return False
        
        if user_id in self._user_roles and org_id in self._user_roles[user_id]:
            old_role_id = self._user_roles[user_id][org_id]
            self._user_roles[user_id][org_id] = role.role_id
            
            self._audit.log_organization(
                org_id=org_id,
                action="role_changed",
                user_id=updated_by,
                description=f"Role changed for {user_id}: {new_role_name}",
            )
            
            return True
        
        return False
    
    def get_members(self, org_id: str) -> List[OrganizationMember]:
        """Get all members of organization"""
        user_ids = self._org_members.get(org_id, [])
        members = []
        
        for user_id in user_ids:
            role_id = self._user_roles.get(user_id, {}).get(org_id)
            role = self._org_roles.get(org_id, {}).get(role_id)
            
            member = OrganizationMember(
                user_id=user_id,
                organization_id=org_id,
                role_id=role_id or "",
                role_name=role.name if role else "Unknown",
                email=f"{user_id}@example.com",  # Would fetch from user service
                full_name=f"User {user_id[:8]}",
                is_owner=(role.name == "owner" if role else False),
                is_admin=(role.name == "admin" if role else False),
            )
            members.append(member)
        
        return members
    
    def get_member_role(self, org_id: str, user_id: str) -> Optional[UserRole]:
        """Get member's role"""
        role_id = self._user_roles.get(user_id, {}).get(org_id)
        if role_id:
            return self._org_roles.get(org_id, {}).get(role_id)
        return None
    
    def get_user_permissions(self, org_id: str, user_id: str) -> List[str]:
        """Get all permissions for a user in an organization"""
        role = self.get_member_role(org_id, user_id)
        if role:
            return list(role.permissions)
        return []
    
    def _get_role_by_name(self, org_id: str, name: str) -> Optional[UserRole]:
        """Get role by name within organization"""
        roles = self._org_roles.get(org_id, {})
        for role in roles.values():
            if role.name == name:
                return role
        return None
    
    # ─────────────────────────────────────────────────────────────
    # Role Management
    # ─────────────────────────────────────────────────────────────
    
    def create_role(
        self,
        org_id: str,
        name: str,
        description: str,
        permissions: List[str],
        created_by: str,
    ) -> Optional[UserRole]:
        """Create a custom role"""
        role = UserRole.create(
            name=name,
            description=description,
            organization_id=org_id,
            permissions=permissions,
        )
        
        if org_id not in self._org_roles:
            self._org_roles[org_id] = {}
        self._org_roles[org_id][role.role_id] = role
        
        return role
    
    def update_role(
        self,
        org_id: str,
        role_id: str,
        updates: Dict[str, Any],
    ) -> Optional[UserRole]:
        """Update a role"""
        role = self._org_roles.get(org_id, {}).get(role_id)
        if not role:
            return None
        
        if "name" in updates:
            role.name = updates["name"]
        if "description" in updates:
            role.description = updates["description"]
        if "permissions" in updates:
            role.permissions = set(updates["permissions"])
        
        role.updated_at = datetime.utcnow()
        return role
    
    def get_roles(self, org_id: str) -> List[UserRole]:
        """Get all roles for organization"""
        return list(self._org_roles.get(org_id, {}).values())
    
    # ─────────────────────────────────────────────────────────────
    # Subscription & Billing
    # ─────────────────────────────────────────────────────────────
    
    def get_billing_account(self, org_id: str) -> Optional[BillingAccount]:
        """Get billing account for organization"""
        return self._billing_accounts.get(org_id)
    
    def get_subscription(self, org_id: str) -> Optional[SubscriptionInfo]:
        """Get subscription info for organization"""
        return self._subscription_manager.get_subscription(org_id)
    
    # ─────────────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────────────
    
    @staticmethod
    def _generate_slug(name: str) -> str:
        """Generate URL-safe slug from name"""
        import hashlib
        slug = name.lower().replace(" ", "-")
        slug = "".join(c if c.isalnum() or c in "-_" else "" for c in slug)
        suffix = hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:6]
        return f"{slug}-{suffix}"
    
    def get_stats(self, org_id: str) -> Dict[str, Any]:
        """Get organization statistics"""
        org = self._organizations.get(org_id)
        if not org:
            return {}
        
        members = self.get_members(org_id)
        subscription = self.get_subscription(org_id)
        
        return {
            "org_id": org_id,
            "name": org.name,
            "status": org.status.value,
            "member_count": len(members),
            "subscription": subscription.to_dict() if subscription else None,
            "created_at": org.created_at.isoformat(),
        }
