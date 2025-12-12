"""
Role-Based Access Control (RBAC) Module
Implements permission and role management for OPTIX platform
"""
from enum import Enum
from typing import List, Set, Dict, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Permission(str, Enum):
    """System permissions"""
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Watchlist operations
    WATCHLIST_READ = "watchlist:read"
    WATCHLIST_WRITE = "watchlist:write"
    WATCHLIST_DELETE = "watchlist:delete"
    
    # Alert operations
    ALERT_READ = "alert:read"
    ALERT_WRITE = "alert:write"
    ALERT_DELETE = "alert:delete"
    
    # Brokerage operations
    BROKERAGE_CONNECT = "brokerage:connect"
    BROKERAGE_READ = "brokerage:read"
    BROKERAGE_TRADE = "brokerage:trade"
    BROKERAGE_DISCONNECT = "brokerage:disconnect"
    
    # Market data access
    MARKET_DATA_REALTIME = "market_data:realtime"
    MARKET_DATA_HISTORICAL = "market_data:historical"
    MARKET_DATA_OPTIONS = "market_data:options"
    MARKET_DATA_FLOW = "market_data:flow"
    
    # AI features
    AI_INSIGHTS = "ai:insights"
    AI_PREDICTIONS = "ai:predictions"
    
    # Premium features
    PREMIUM_ADVANCED_CHARTS = "premium:advanced_charts"
    PREMIUM_UNLIMITED_ALERTS = "premium:unlimited_alerts"
    PREMIUM_PRIORITY_SUPPORT = "premium:priority_support"
    
    # Admin operations
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_ANALYTICS = "admin:analytics"


class Role(str, Enum):
    """User roles"""
    GUEST = "guest"
    FREE_USER = "free_user"
    PREMIUM_USER = "premium_user"
    TRADER = "trader"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class RolePermissions(BaseModel):
    """Role with associated permissions"""
    role: Role
    permissions: Set[Permission]
    description: str
    priority: int  # Higher priority roles override lower ones


# Define role permission mappings
ROLE_PERMISSIONS_MAP: Dict[Role, RolePermissions] = {
    Role.GUEST: RolePermissions(
        role=Role.GUEST,
        permissions={
            Permission.USER_READ,
            Permission.MARKET_DATA_REALTIME,
        },
        description="Limited read-only access",
        priority=0
    ),
    
    Role.FREE_USER: RolePermissions(
        role=Role.FREE_USER,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.WATCHLIST_READ,
            Permission.WATCHLIST_WRITE,
            Permission.WATCHLIST_DELETE,
            Permission.ALERT_READ,
            Permission.ALERT_WRITE,
            Permission.ALERT_DELETE,
            Permission.MARKET_DATA_REALTIME,
            Permission.MARKET_DATA_HISTORICAL,
        },
        description="Basic platform features",
        priority=10
    ),
    
    Role.PREMIUM_USER: RolePermissions(
        role=Role.PREMIUM_USER,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.WATCHLIST_READ,
            Permission.WATCHLIST_WRITE,
            Permission.WATCHLIST_DELETE,
            Permission.ALERT_READ,
            Permission.ALERT_WRITE,
            Permission.ALERT_DELETE,
            Permission.MARKET_DATA_REALTIME,
            Permission.MARKET_DATA_HISTORICAL,
            Permission.MARKET_DATA_OPTIONS,
            Permission.MARKET_DATA_FLOW,
            Permission.AI_INSIGHTS,
            Permission.AI_PREDICTIONS,
            Permission.PREMIUM_ADVANCED_CHARTS,
            Permission.PREMIUM_UNLIMITED_ALERTS,
            Permission.PREMIUM_PRIORITY_SUPPORT,
        },
        description="Premium features including AI insights and options flow",
        priority=20
    ),
    
    Role.TRADER: RolePermissions(
        role=Role.TRADER,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.WATCHLIST_READ,
            Permission.WATCHLIST_WRITE,
            Permission.WATCHLIST_DELETE,
            Permission.ALERT_READ,
            Permission.ALERT_WRITE,
            Permission.ALERT_DELETE,
            Permission.BROKERAGE_CONNECT,
            Permission.BROKERAGE_READ,
            Permission.BROKERAGE_TRADE,
            Permission.BROKERAGE_DISCONNECT,
            Permission.MARKET_DATA_REALTIME,
            Permission.MARKET_DATA_HISTORICAL,
            Permission.MARKET_DATA_OPTIONS,
            Permission.MARKET_DATA_FLOW,
            Permission.AI_INSIGHTS,
            Permission.AI_PREDICTIONS,
            Permission.PREMIUM_ADVANCED_CHARTS,
            Permission.PREMIUM_UNLIMITED_ALERTS,
        },
        description="Full trading capabilities with brokerage integration",
        priority=30
    ),
    
    Role.ADMIN: RolePermissions(
        role=Role.ADMIN,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.USER_DELETE,
            Permission.WATCHLIST_READ,
            Permission.WATCHLIST_WRITE,
            Permission.WATCHLIST_DELETE,
            Permission.ALERT_READ,
            Permission.ALERT_WRITE,
            Permission.ALERT_DELETE,
            Permission.BROKERAGE_CONNECT,
            Permission.BROKERAGE_READ,
            Permission.BROKERAGE_TRADE,
            Permission.BROKERAGE_DISCONNECT,
            Permission.MARKET_DATA_REALTIME,
            Permission.MARKET_DATA_HISTORICAL,
            Permission.MARKET_DATA_OPTIONS,
            Permission.MARKET_DATA_FLOW,
            Permission.AI_INSIGHTS,
            Permission.AI_PREDICTIONS,
            Permission.PREMIUM_ADVANCED_CHARTS,
            Permission.PREMIUM_UNLIMITED_ALERTS,
            Permission.PREMIUM_PRIORITY_SUPPORT,
            Permission.ADMIN_USERS,
            Permission.ADMIN_ANALYTICS,
        },
        description="Administrative access to user management",
        priority=90
    ),
    
    Role.SUPER_ADMIN: RolePermissions(
        role=Role.SUPER_ADMIN,
        permissions=set(Permission),  # All permissions
        description="Full system access",
        priority=100
    ),
}


class UserRole(BaseModel):
    """User role assignment"""
    user_id: uuid.UUID
    role: Role
    granted_by: Optional[uuid.UUID] = None
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class RBACService:
    """Role-Based Access Control service"""
    
    def __init__(self):
        self._user_roles: Dict[uuid.UUID, List[Role]] = {}
        self._custom_permissions: Dict[uuid.UUID, Set[Permission]] = {}
    
    def assign_role(self, user_id: uuid.UUID, role: Role, granted_by: Optional[uuid.UUID] = None) -> UserRole:
        """Assign role to user"""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        
        if role not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role)
        
        return UserRole(
            user_id=user_id,
            role=role,
            granted_by=granted_by
        )
    
    def revoke_role(self, user_id: uuid.UUID, role: Role) -> bool:
        """Revoke role from user"""
        if user_id in self._user_roles and role in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role)
            return True
        return False
    
    def get_user_roles(self, user_id: uuid.UUID) -> List[Role]:
        """Get all roles assigned to user"""
        return self._user_roles.get(user_id, [])
    
    def get_user_permissions(self, user_id: uuid.UUID) -> Set[Permission]:
        """Get all permissions for user based on roles"""
        roles = self.get_user_roles(user_id)
        permissions = set()
        
        for role in roles:
            if role in ROLE_PERMISSIONS_MAP:
                permissions.update(ROLE_PERMISSIONS_MAP[role].permissions)
        
        # Add custom permissions
        if user_id in self._custom_permissions:
            permissions.update(self._custom_permissions[user_id])
        
        return permissions
    
    def has_permission(self, user_id: uuid.UUID, permission: Permission) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions
    
    def has_any_permission(self, user_id: uuid.UUID, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user_id)
        return any(perm in user_permissions for perm in permissions)
    
    def has_all_permissions(self, user_id: uuid.UUID, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions"""
        user_permissions = self.get_user_permissions(user_id)
        return all(perm in user_permissions for perm in permissions)
    
    def grant_custom_permission(self, user_id: uuid.UUID, permission: Permission) -> None:
        """Grant custom permission to user (beyond their role)"""
        if user_id not in self._custom_permissions:
            self._custom_permissions[user_id] = set()
        self._custom_permissions[user_id].add(permission)
    
    def revoke_custom_permission(self, user_id: uuid.UUID, permission: Permission) -> bool:
        """Revoke custom permission from user"""
        if user_id in self._custom_permissions and permission in self._custom_permissions[user_id]:
            self._custom_permissions[user_id].remove(permission)
            return True
        return False
    
    def get_highest_role(self, user_id: uuid.UUID) -> Optional[Role]:
        """Get user's highest priority role"""
        roles = self.get_user_roles(user_id)
        if not roles:
            return None
        
        highest_role = max(
            roles,
            key=lambda r: ROLE_PERMISSIONS_MAP.get(r, RolePermissions(
                role=r, permissions=set(), description="", priority=0
            )).priority
        )
        return highest_role
    
    def can_access_resource(
        self,
        user_id: uuid.UUID,
        resource_type: str,
        action: str
    ) -> bool:
        """Check if user can perform action on resource type"""
        # Map resource type and action to permission
        permission_map = {
            ("watchlist", "read"): Permission.WATCHLIST_READ,
            ("watchlist", "write"): Permission.WATCHLIST_WRITE,
            ("watchlist", "delete"): Permission.WATCHLIST_DELETE,
            ("alert", "read"): Permission.ALERT_READ,
            ("alert", "write"): Permission.ALERT_WRITE,
            ("alert", "delete"): Permission.ALERT_DELETE,
            ("brokerage", "connect"): Permission.BROKERAGE_CONNECT,
            ("brokerage", "trade"): Permission.BROKERAGE_TRADE,
            ("market_data", "options"): Permission.MARKET_DATA_OPTIONS,
            ("market_data", "flow"): Permission.MARKET_DATA_FLOW,
        }
        
        permission = permission_map.get((resource_type, action))
        if permission:
            return self.has_permission(user_id, permission)
        
        return False
    
    def is_premium_user(self, user_id: uuid.UUID) -> bool:
        """Check if user has premium access"""
        roles = self.get_user_roles(user_id)
        premium_roles = {Role.PREMIUM_USER, Role.TRADER, Role.ADMIN, Role.SUPER_ADMIN}
        return any(role in premium_roles for role in roles)
    
    def is_admin(self, user_id: uuid.UUID) -> bool:
        """Check if user has admin privileges"""
        roles = self.get_user_roles(user_id)
        return Role.ADMIN in roles or Role.SUPER_ADMIN in roles


# Singleton instance
_rbac_service = None


def get_rbac_service() -> RBACService:
    """Get RBAC service singleton"""
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service


from pydantic import Field
