"""
Workspaces Module

Professional workspace management for the trading platform with:
- Dashboard
- Live Trading
- Paper Trading
- Backtesting
- Strategy Builder
- Analytics
- Risk Center
- Notifications
- AI Command Center
- Developer Console
- Settings
"""

from workspaces.manager import WorkspaceManager, Workspace, WorkspaceType
from workspaces.state import WorkspaceState, WorkspaceLayout

__all__ = [
    "WorkspaceManager",
    "Workspace",
    "WorkspaceType",
    "WorkspaceState",
    "WorkspaceLayout",
]
