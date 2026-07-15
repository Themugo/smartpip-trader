"""
Workspace System - Modular Workspaces

Customizable workspace layouts with persistent state:
- Multiple workspace templates
- Panel configurations
- Chart layouts
- Strategy selections
- User preferences
"""

from workspace.manager import WorkspaceManager, WorkspaceLayout, PanelState
from workspace.templates import WorkspaceTemplate, TEMPLATES

__all__ = [
    "WorkspaceManager",
    "WorkspaceLayout",
    "PanelState",
    "WorkspaceTemplate",
    "TEMPLATES",
]
