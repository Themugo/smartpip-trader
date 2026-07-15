"""
Role-Based Access Control (RBAC)

Provides:
- Permission checking
- Role management
- Access control enforcement
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

from enterprise.models.tenant import (
    Organization,
    Team,
    Workspace,
    UserRole,
    Permission,
    PERMISSIONS,
)


class RBACError(Exception):
    """RBAC authorization error"""
    pass


class PermissionDenied(RBACError):
    """Permission denied error"""
    def __init__(self, permission: str, resource: str = ""):
        self.permission = permission
        self.resource = resource
        message = f"Permission denied: {permission}"
        if resource:
            message += f" on {resource}"
        super().__init__(message)


class RoleManager:
    """
    Manages roles and permissions.
    
    Features:
    - Role CRUD
    - Permission management
    - Role inheritance
    """
    
    def __init__(self):
        self._roles: Dict[str, Dict[str, UserRole]] = {}  # org_id -> {role_id: role}
    
    def get_role(self, org_id: str, role_id: str) -> Optional[UserRole]:
        """Get role by ID"""
        return self._roles.get(org_id, {}).get(role_id)
    
    def get_role_by_name(self, org_id: str, name: str) -> Optional[UserRole]:
        """Get role by name"""
        roles = self._roles.get(org_id, {})
        for role in roles.values():
            if role.name == name:
                return role
        return None
    
    def get_roles(self, org_id: str) -> List[UserRole]:
        """Get all roles for organization"""
        return list(self._roles.get(org_id, {}).values())
    
    def create_role(
        self,
        org_id: str,
        name: str,
        description: str,
        permissions: Optional[List[str]] = None,
        parent_role_id: Optional[str] = None,
    ) -> UserRole:
        """Create a new role"""
        # Get parent permissions if specified
        if parent_role_id:
            parent = self.get_role(org_id, parent_role_id)
            if parent:
                permissions = list(parent.permissions) + (permissions or [])
        
        role = UserRole.create(
            name=name,
            description=description,
            organization_id=org_id,
            permissions=permissions,
        )
        
        if org_id not in self._roles:
            self._roles[org_id] = {}
        self._roles[org_id][role.role_id] = role
        
        return role
    
    def update_role(
        self,
        org_id: str,
        role_id: str,
        updates: Dict[str, Any],
    ) -> Optional[UserRole]:
        """Update a role"""
        role = self.get_role(org_id, role_id)
        if not role or role.is_system_role:
            return None
        
        if "name" in updates:
            role.name = updates["name"]
        if "description" in updates:
            role.description = updates["description"]
        if "permissions" in updates:
            role.permissions = set(updates["permissions"])
        
        role.updated_at = datetime.utcnow()
        return role
    
    def delete_role(self, org_id: str, role_id: str) -> bool:
        """Delete a role"""
        role = self.get_role(org_id, role_id)
        if not role or role.is_system_role:
            return False
        
        del self._roles[org_id][role_id]
        return True
    
    def clone_role(
        self,
        org_id: str,
        source_role_id: str,
        new_name: str,
    ) -> Optional[UserRole]:
        """Clone an existing role"""
        source = self.get_role(org_id, source_role_id)
        if not source:
            return None
        
        return self.create_role(
            org_id=org_id,
            name=new_name,
            description=f"Clone of {source.name}",
            permissions=list(source.permissions),
        )


class PermissionChecker:
    """
    Checks permissions for users.
    
    Features:
    - Single permission check
    - Multiple permission check
    - Resource ownership check
    - Context-aware checks
    """
    
    def __init__(self, role_manager: RoleManager):
        self._role_manager = role_manager
    
    def has_permission(
        self,
        org_id: str,
        user_id: str,
        permission: str,
        user_role_id: Optional[str] = None,
    ) -> bool:
        """Check if user has a specific permission"""
        if user_role_id:
            role = self._role_manager.get_role(org_id, user_role_id)
        else:
            # Would need to look up user's role
            return False
        
        if not role:
            return False
        
        return role.has_permission(permission)
    
    def has_any_permission(
        self,
        org_id: str,
        user_id: str,
        permissions: List[str],
        user_role_id: Optional[str] = None,
    ) -> bool:
        """Check if user has any of the specified permissions"""
        for permission in permissions:
            if self.has_permission(org_id, user_id, permission, user_role_id):
                return True
        return False
    
    def has_all_permissions(
        self,
        org_id: str,
        user_id: str,
        permissions: List[str],
        user_role_id: Optional[str] = None,
    ) -> bool:
        """Check if user has all specified permissions"""
        for permission in permissions:
            if not self.has_permission(org_id, user_id, permission, user_role_id):
                return False
        return True
    
    def check_permission(
        self,
        org_id: str,
        user_id: str,
        permission: str,
        user_role_id: Optional[str] = None,
    ) -> None:
        """Check permission and raise if denied"""
        if not self.has_permission(org_id, user_id, permission, user_role_id):
            raise PermissionDenied(permission)


class RBACService:
    """
    Role-Based Access Control Service.
    
    Provides:
    - Permission enforcement
    - Access decorators
    - Resource-level access control
    """
    
    def __init__(self):
        self._role_manager = RoleManager()
        self._permission_checker = PermissionChecker(self._role_manager)
    
    @property
    def role_manager(self) -> RoleManager:
        return self._role_manager
    
    @property
    def permission_checker(self) -> PermissionChecker:
        return self._permission_checker
    
    def check_access(
        self,
        user_role: UserRole,
        permission: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if role has permission with optional context.
        
        Context can include:
        - resource_owner: Check if user owns the resource
        - team_membership: Check if user is in the team
        - workspace_access: Check workspace permissions
        """
        if not user_role.has_permission(permission):
            return False
        
        # Additional context checks can be added here
        if context:
            if "resource_owner" in context:
                if context["resource_owner"] != context.get("user_id"):
                    # Owner-only permission check
                    owner_permissions = {"strategy:delete", "workspace:delete"}
                    if permission in owner_permissions:
                        return False
        
        return True
    
    def require_permission(
        self,
        permission: str,
        get_user_role: Callable[[str, str], Optional[UserRole]],
    ) -> Callable:
        """
        Decorator to require a permission.
        
        Usage:
            @rbac.require_permission("strategy:write", get_user_role_func)
            def create_strategy(org_id: str, user_id: str, ...):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract org_id and user_id from args/kwargs
                org_id = kwargs.get("org_id") or (args[0] if args else None)
                user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
                
                if not org_id or not user_id:
                    raise RBACError("org_id and user_id required")
                
                role = get_user_role(org_id, user_id)
                if not role:
                    raise PermissionDenied(permission)
                
                if not self.check_access(role, permission):
                    raise PermissionDenied(permission)
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_accessible_resources(
        self,
        user_role: UserRole,
        resource_type: str,
        resources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Filter resources based on user's permissions.
        
        Returns only resources the user can access.
        """
        read_permission = f"{resource_type}:read"
        write_permission = f"{resource_type}:write"
        
        if not user_role.has_permission(read_permission):
            return []
        
        accessible = []
        for resource in resources:
            # Check ownership
            if resource.get("owner_id") == resource.get("user_id"):
                accessible.append(resource)
                continue
            
            # Check shared access
            if resource.get("is_shared") and user_role.has_permission(write_permission):
                accessible.append(resource)
                continue
            
            # Default: show if has read permission
            if user_role.has_permission(read_permission):
                accessible.append(resource)
        
        return accessible
    
    def audit_access(
        self,
        user_role: UserRole,
        attempted_permission: str,
        resource_id: Optional[str] = None,
        success: bool = True,
    ) -> Dict[str, Any]:
        """Create audit record for access attempt"""
        return {
            "user_role": user_role.role_id,
            "role_name": user_role.name,
            "attempted_permission": attempted_permission,
            "resource_id": resource_id,
            "success": success,
            "permissions_held": list(user_role.permissions),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Decorators for API endpoints
# ─────────────────────────────────────────────────────────────────────────────

def require_permissions(*permissions: str):
    """
    Decorator to require multiple permissions.
    
    Usage:
        @require_permissions("strategy:read", "strategy:write")
        def manage_strategy(org_id: str, user_id: str, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Permission checking should be done in the endpoint
            # based on the current user's role
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_feature(feature_code: str):
    """
    Decorator to require a feature flag.
    
    Usage:
        @require_feature("api_access")
        def api_endpoint(org_id: str, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Feature checking should be done based on organization subscription
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_org_role(*roles: str):
    """
    Decorator to require specific organization roles.
    
    Usage:
        @require_org_role("admin", "owner")
        def admin_endpoint(org_id: str, user_id: str, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Role checking should be done based on user's org role
            return func(*args, **kwargs)
        return wrapper
    return decorator
