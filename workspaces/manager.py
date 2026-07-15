"""
Workspace Manager and Models

Manages the professional workspace system with:
- Workspace definitions and configurations
- Layout persistence
- User preferences
- Quick access shortcuts
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkspaceType(Enum):
    """Available workspace types"""
    DASHBOARD = "dashboard"
    LIVE_TRADING = "live_trading"
    PAPER_TRADING = "paper_trading"
    BACKTESTING = "backtesting"
    STRATEGY_BUILDER = "strategy_builder"
    ANALYTICS = "analytics"
    RISK_CENTER = "risk_center"
    NOTIFICATIONS = "notifications"
    AI_COMMAND_CENTER = "ai_command_center"
    DEVELOPER_CONSOLE = "developer_console"
    SETTINGS = "settings"


@dataclass
class Workspace:
    """Workspace definition"""
    id: str
    type: WorkspaceType
    name: str
    description: str
    icon: str
    route: str
    order: int
    is_default: bool = False
    requires_auth: bool = True
    permissions: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "route": self.route,
            "order": self.order,
            "is_default": self.is_default,
            "requires_auth": self.requires_auth,
            "permissions": self.permissions,
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        return cls(
            id=data["id"],
            type=WorkspaceType(data["type"]),
            name=data["name"],
            description=data["description"],
            icon=data["icon"],
            route=data["route"],
            order=data["order"],
            is_default=data.get("is_default", False),
            requires_auth=data.get("requires_auth", True),
            permissions=data.get("permissions", []),
            settings=data.get("settings", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
        )


# Default workspace definitions
DEFAULT_WORKSPACES = [
    Workspace(
        id="dashboard",
        type=WorkspaceType.DASHBOARD,
        name="Dashboard",
        description="Overview of all trading activities and performance metrics",
        icon="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
        route="/dashboard",
        order=1,
        is_default=True,
    ),
    Workspace(
        id="live_trading",
        type=WorkspaceType.LIVE_TRADING,
        name="Live Trading",
        description="Real-time trading with live market execution",
        icon="M13 10V3L4 14h7v7l9-11h-7z",
        route="/live-trading",
        order=2,
        requires_auth=True,
        permissions=["trade"],
    ),
    Workspace(
        id="paper_trading",
        type=WorkspaceType.PAPER_TRADING,
        name="Paper Trading",
        description="Practice trading with simulated funds",
        icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
        route="/paper-trading",
        order=3,
        permissions=["paper_trade"],
    ),
    Workspace(
        id="backtesting",
        type=WorkspaceType.BACKTESTING,
        name="Backtesting",
        description="Test strategies against historical data",
        icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
        route="/backtesting",
        order=4,
        permissions=["backtest"],
    ),
    Workspace(
        id="strategy_builder",
        type=WorkspaceType.STRATEGY_BUILDER,
        name="Strategy Builder",
        description="Create and customize trading strategies",
        icon="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
        route="/strategy-builder",
        order=5,
        permissions=["strategy_manage"],
    ),
    Workspace(
        id="analytics",
        type=WorkspaceType.ANALYTICS,
        name="Analytics",
        description="Comprehensive trading analytics and performance reports",
        icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
        route="/analytics",
        order=6,
    ),
    Workspace(
        id="risk_center",
        type=WorkspaceType.RISK_CENTER,
        name="Risk Center",
        description="Monitor and control trading risk parameters",
        icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
        route="/risk-center",
        order=7,
        permissions=["risk_manage"],
    ),
    Workspace(
        id="notifications",
        type=WorkspaceType.NOTIFICATIONS,
        name="Notifications",
        description="Trade alerts, system messages, and activity history",
        icon="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9",
        route="/notifications",
        order=8,
    ),
    Workspace(
        id="ai_command_center",
        type=WorkspaceType.AI_COMMAND_CENTER,
        name="AI Command Center",
        description="Control AI trading agents and strategies",
        icon="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
        route="/ai-command-center",
        order=9,
        permissions=["ai_control"],
    ),
    Workspace(
        id="developer_console",
        type=WorkspaceType.DEVELOPER_CONSOLE,
        name="Developer Console",
        description="API testing, logs, and developer tools",
        icon="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
        route="/developer-console",
        order=10,
        permissions=["developer"],
    ),
    Workspace(
        id="settings",
        type=WorkspaceType.SETTINGS,
        name="Settings",
        description="Application configuration and preferences",
        icon="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
        route="/settings",
        order=11,
    ),
]


class WorkspaceManager:
    """
    Manages workspace configuration and user preferences.
    
    Features:
    - Workspace enumeration and metadata
    - User preferences per workspace
    - Layout persistence
    - Quick navigation shortcuts
    - Favorites management
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path or "data/workspaces"
        self._workspaces: Dict[str, Workspace] = {}
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        self._favorites: List[str] = []
        self._current_workspace: Optional[str] = None
        self._on_change_callbacks: List[Callable[[str], None]] = []
        
        os.makedirs(self._storage_path, exist_ok=True)
        self._initialize_default_workspaces()
        self._load_user_preferences()
    
    def _initialize_default_workspaces(self) -> None:
        """Initialize with default workspace definitions"""
        for workspace in DEFAULT_WORKSPACES:
            self._workspaces[workspace.id] = workspace
    
    def _load_user_preferences(self) -> None:
        """Load user preferences from storage"""
        prefs_file = os.path.join(self._storage_path, "preferences.json")
        
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, "r") as f:
                    data = json.load(f)
                    self._user_preferences = data.get("preferences", {})
                    self._favorites = data.get("favorites", [])
                    self._current_workspace = data.get("current_workspace", "dashboard")
            except Exception as e:
                logger.error(f"Failed to load preferences: {e}")
    
    def _save_user_preferences(self) -> None:
        """Save user preferences to storage"""
        prefs_file = os.path.join(self._storage_path, "preferences.json")
        
        try:
            with open(prefs_file, "w") as f:
                json.dump({
                    "preferences": self._user_preferences,
                    "favorites": self._favorites,
                    "current_workspace": self._current_workspace,
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        return self._workspaces.get(workspace_id)
    
    def get_workspace_by_type(self, workspace_type: WorkspaceType) -> Optional[Workspace]:
        """Get workspace by type"""
        for workspace in self._workspaces.values():
            if workspace.type == workspace_type:
                return workspace
        return None
    
    def get_all_workspaces(self) -> List[Workspace]:
        """Get all workspaces sorted by order"""
        return sorted(
            self._workspaces.values(),
            key=lambda w: w.order
        )
    
    def get_favorites(self) -> List[Workspace]:
        """Get favorite workspaces"""
        return [
            self._workspaces[wid]
            for wid in self._favorites
            if wid in self._workspaces
        ]
    
    def add_to_favorites(self, workspace_id: str) -> bool:
        """Add workspace to favorites"""
        if workspace_id not in self._favorites:
            self._favorites.append(workspace_id)
            self._save_user_preferences()
            return True
        return False
    
    def remove_from_favorites(self, workspace_id: str) -> bool:
        """Remove workspace from favorites"""
        if workspace_id in self._favorites:
            self._favorites.remove(workspace_id)
            self._save_user_preferences()
            return True
        return False
    
    def set_current_workspace(self, workspace_id: str) -> bool:
        """Set the current active workspace"""
        if workspace_id in self._workspaces:
            self._current_workspace = workspace_id
            self._save_user_preferences()
            
            # Notify callbacks
            for callback in self._on_change_callbacks:
                try:
                    callback(workspace_id)
                except Exception as e:
                    logger.error(f"Workspace change callback error: {e}")
            
            return True
        return False
    
    def get_current_workspace(self) -> Optional[Workspace]:
        """Get the current active workspace"""
        if self._current_workspace:
            return self._workspaces.get(self._current_workspace)
        return self.get_workspace_by_type(WorkspaceType.DASHBOARD)
    
    def get_workspace_preferences(self, workspace_id: str) -> Dict[str, Any]:
        """Get user preferences for a workspace"""
        return self._user_preferences.get(workspace_id, {})
    
    def update_workspace_preferences(
        self,
        workspace_id: str,
        preferences: Dict[str, Any],
    ) -> bool:
        """Update preferences for a workspace"""
        if workspace_id not in self._workspaces:
            return False
        
        current = self._user_preferences.get(workspace_id, {})
        current.update(preferences)
        self._user_preferences[workspace_id] = current
        self._save_user_preferences()
        return True
    
    def register_workspace(
        self,
        workspace: Workspace,
        set_default: bool = False,
    ) -> bool:
        """Register a custom workspace"""
        if workspace.id in self._workspaces:
            return False
        
        self._workspaces[workspace.id] = workspace
        if set_default:
            workspace.is_default = True
        
        self._save_user_preferences()
        return True
    
    def unregister_workspace(self, workspace_id: str) -> bool:
        """Unregister a workspace"""
        if workspace_id not in self._workspaces:
            return False
        
        if self._workspaces[workspace_id].is_default:
            logger.warning(f"Cannot unregister default workspace: {workspace_id}")
            return False
        
        del self._workspaces[workspace_id]
        self._user_preferences.pop(workspace_id, None)
        self._favorites = [f for f in self._favorites if f != workspace_id]
        self._save_user_preferences()
        return True
    
    def on_workspace_change(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """Register a workspace change callback"""
        self._on_change_callbacks.append(callback)
    
    def get_navigation_tree(self) -> Dict[str, Any]:
        """Get navigation tree structure for UI"""
        workspaces = self.get_all_workspaces()
        
        return {
            "workspaces": [w.to_dict() for w in workspaces],
            "favorites": self._favorites,
            "current_workspace": self._current_workspace,
        }
    
    def export_config(self) -> Dict[str, Any]:
        """Export workspace configuration"""
        return {
            "workspaces": [
                w.to_dict() for w in self._workspaces.values()
            ],
            "favorites": self._favorites,
            "current_workspace": self._current_workspace,
            "preferences": self._user_preferences,
        }
    
    def import_config(self, config: Dict[str, Any]) -> None:
        """Import workspace configuration"""
        for workspace_data in config.get("workspaces", []):
            workspace = Workspace.from_dict(workspace_data)
            self._workspaces[workspace.id] = workspace
        
        self._favorites = config.get("favorites", [])
        self._current_workspace = config.get("current_workspace", "dashboard")
        self._user_preferences = config.get("preferences", {})
        self._save_user_preferences()


def create_workspace_manager(
    storage_path: Optional[str] = None,
) -> WorkspaceManager:
    """Factory function to create a workspace manager"""
    return WorkspaceManager(storage_path=storage_path)
