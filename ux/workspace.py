"""
Workspace Management
=================

Manages user workspaces and layouts.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

from .core import (
    Workspace,
    WorkspaceTemplate,
    Window,
    Monitor,
    Layout,
    DefaultTemplates,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceSettings:
    """User workspace settings"""
    # Display
    auto_save: bool = True
    save_interval_seconds: int = 30
    
    # Layout
    remember_window_positions: bool = True
    snap_to_grid: bool = True
    grid_size: int = 10
    
    # Multi-monitor
    use_all_monitors: bool = True
    primary_monitor_index: int = 0
    
    # Animation
    enable_animations: bool = True
    animation_speed: float = 1.0
    
    # Docking
    enable_docking: bool = True
    dock_preview: bool = True
    dock_snap_threshold: int = 20
    
    # Recent
    max_recent_workspaces: int = 10
    show_recent_on_startup: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_save": self.auto_save,
            "save_interval_seconds": self.save_interval_seconds,
            "remember_window_positions": self.remember_window_positions,
            "snap_to_grid": self.snap_to_grid,
            "grid_size": self.grid_size,
            "use_all_monitors": self.use_all_monitors,
            "primary_monitor_index": self.primary_monitor_index,
            "enable_animations": self.enable_animations,
            "animation_speed": self.animation_speed,
            "enable_docking": self.enable_docking,
            "dock_preview": self.dock_preview,
            "dock_snap_threshold": self.dock_snap_threshold,
            "max_recent_workspaces": self.max_recent_workspaces,
            "show_recent_on_startup": self.show_recent_on_startup,
        }


class WorkspaceManager:
    """
    Manages user workspaces and layouts.
    
    Handles:
    - Workspace CRUD operations
    - Template management
    - Multi-monitor support
    - Auto-save
    - Recent workspaces
    """
    
    def __init__(self, storage_path: str = "./data/ux"):
        self.storage_path = storage_path
        self._workspaces: Dict[str, Workspace] = {}
        self._templates: Dict[str, WorkspaceTemplate] = {}
        self._recent: List[str] = []  # Workspace IDs
        self._settings = WorkspaceSettings()
        
        # Callbacks
        self._workspace_changed_callbacks: List[Callable] = []
        self._window_changed_callbacks: List[Callable] = []
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self) -> None:
        """Initialize default workspace templates"""
        templates = [
            DefaultTemplates.trading_workspace(),
            DefaultTemplates.analysis_workspace(),
            DefaultTemplates.monitoring_workspace(),
        ]
        
        for template in templates:
            self._templates[template.template_id] = template
    
    # ========== Workspace Management ==========
    
    def create_workspace(
        self,
        name: str,
        template: Optional[WorkspaceTemplate] = None
    ) -> Workspace:
        """Create a new workspace"""
        workspace = Workspace(
            workspace_id=str(uuid.uuid4()),
            name=name,
        )
        
        if template:
            # Create from template
            workspace = template.create_workspace(name)
        
        self._workspaces[workspace.workspace_id] = workspace
        self._add_to_recent(workspace.workspace_id)
        
        logger.info(f"Created workspace: {workspace.name}")
        return workspace
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID"""
        return self._workspaces.get(workspace_id)
    
    def get_all_workspaces(self) -> List[Workspace]:
        """Get all workspaces"""
        return list(self._workspaces.values())
    
    def get_recent_workspaces(self, limit: int = 10) -> List[Workspace]:
        """Get recent workspaces"""
        recent = []
        for wid in self._recent[:limit]:
            workspace = self._workspaces.get(wid)
            if workspace:
                recent.append(workspace)
        return recent
    
    def update_workspace(self, workspace: Workspace) -> None:
        """Update a workspace"""
        workspace.updated_at = time.time()
        self._workspaces[workspace.workspace_id] = workspace
        self._notify_workspace_changed(workspace)
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        if workspace_id in self._workspaces:
            workspace = self._workspaces.pop(workspace_id)
            self._recent = [wid for wid in self._recent if wid != workspace_id]
            logger.info(f"Deleted workspace: {workspace.name}")
            return True
        return False
    
    def duplicate_workspace(
        self,
        workspace_id: str,
        new_name: Optional[str] = None
    ) -> Optional[Workspace]:
        """Duplicate an existing workspace"""
        original = self._workspaces.get(workspace_id)
        if not original:
            return None
        
        duplicate = Workspace(
            workspace_id=str(uuid.uuid4()),
            name=new_name or f"{original.name} (Copy)",
            windows={k: v for k, v in original.windows.items()},
            layouts={k: v for k, v in original.layouts.items()},
            monitors=original.monitors.copy(),
        )
        
        self._workspaces[duplicate.workspace_id] = duplicate
        self._add_to_recent(duplicate.workspace_id)
        
        return duplicate
    
    def _add_to_recent(self, workspace_id: str) -> None:
        """Add workspace to recent list"""
        self._recent = [wid for wid in self._recent if wid != workspace_id]
        self._recent.insert(0, workspace_id)
        self._recent = self._recent[:self._settings.max_recent_workspaces]
    
    # ========== Window Management ==========
    
    def add_window(
        self,
        workspace_id: str,
        window: Window
    ) -> bool:
        """Add a window to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        workspace.add_window(window)
        self._notify_window_changed(workspace, window)
        return True
    
    def remove_window(
        self,
        workspace_id: str,
        window_id: str
    ) -> bool:
        """Remove a window from a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        window = workspace.remove_window(window_id)
        if window:
            self._notify_window_changed(workspace, window, removed=True)
        return window is not None
    
    def update_window(
        self,
        workspace_id: str,
        window_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a window's properties"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        window = workspace.get_window(window_id)
        if not window:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(window, key):
                setattr(window, key, value)
        
        workspace.updated_at = time.time()
        self._notify_window_changed(workspace, window)
        return True
    
    def move_window(
        self,
        workspace_id: str,
        window_id: str,
        x: int,
        y: int
    ) -> bool:
        """Move a window to a position"""
        return self.update_window(workspace_id, window_id, {"x": x, "y": y})
    
    def resize_window(
        self,
        workspace_id: str,
        window_id: str,
        width: int,
        height: int
    ) -> bool:
        """Resize a window"""
        return self.update_window(workspace_id, window_id, {"width": width, "height": height})
    
    def focus_window(
        self,
        workspace_id: str,
        window_id: str
    ) -> bool:
        """Focus a window"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        # Unfocus all windows
        for w in workspace.windows.values():
            w.is_focused = False
        
        # Focus the target window
        window = workspace.get_window(window_id)
        if window:
            window.is_focused = True
            self._notify_window_changed(workspace, window)
            return True
        
        return False
    
    def dock_window(
        self,
        workspace_id: str,
        window_id: str,
        position: str,
        target_window_id: Optional[str] = None
    ) -> bool:
        """Dock a window to a position"""
        from .core import DockPosition
        
        position_enum = DockPosition(position)
        updates = {"dock_position": position_enum, "state": "docked"}
        
        return self.update_window(workspace_id, window_id, updates)
    
    def float_window(
        self,
        workspace_id: str,
        window_id: str
    ) -> bool:
        """Float a docked window"""
        return self.update_window(
            workspace_id,
            window_id,
            {"dock_position": "floating", "state": "normal"}
        )
    
    # ========== Layout Management ==========
    
    def create_layout(
        self,
        workspace_id: str,
        name: str,
        layout_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[Layout]:
        """Create a new layout"""
        from .core import Layout, LayoutType
        
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        layout = Layout(
            layout_id=str(uuid.uuid4()),
            name=name,
            layout_type=LayoutType(layout_type),
        )
        
        if config:
            layout.split_ratio = config.get("split_ratio", 0.5)
            layout.rows = config.get("rows", 1)
            layout.columns = config.get("columns", 1)
        
        workspace.layouts[layout.layout_id] = layout
        return layout
    
    def apply_layout(
        self,
        workspace_id: str,
        layout_id: str
    ) -> bool:
        """Apply a layout to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace or layout_id not in workspace.layouts:
            return False
        
        workspace.active_layout_id = layout_id
        return True
    
    # ========== Template Management ==========
    
    def create_from_template(
        self,
        template_id: str,
        workspace_name: str
    ) -> Optional[Workspace]:
        """Create a workspace from a template"""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        return self.create_workspace(workspace_name, template)
    
    def save_as_template(
        self,
        workspace_id: str,
        template_name: str,
        description: str = ""
    ) -> Optional[WorkspaceTemplate]:
        """Save a workspace as a template"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        # Extract window configs
        window_configs = []
        for window in workspace.windows.values():
            window_configs.append({
                "title": window.title,
                "component": window.component,
                "width": window.width,
                "height": window.height,
            })
        
        template = WorkspaceTemplate(
            template_id=str(uuid.uuid4()),
            name=template_name,
            description=description,
            window_configs=window_configs,
        )
        
        self._templates[template.template_id] = template
        return template
    
    def get_templates(self) -> List[WorkspaceTemplate]:
        """Get all templates"""
        return list(self._templates.values())
    
    def get_templates_by_category(self, category: str) -> List[WorkspaceTemplate]:
        """Get templates by category"""
        return [t for t in self._templates.values() if t.category == category]
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        return self._templates.pop(template_id, None) is not None
    
    # ========== Settings ==========
    
    def get_settings(self) -> WorkspaceSettings:
        """Get workspace settings"""
        return self._settings
    
    def update_settings(self, settings: WorkspaceSettings) -> None:
        """Update workspace settings"""
        self._settings = settings
    
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a single setting"""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            return True
        return False
    
    # ========== Persistence ==========
    
    def save_workspace(self, workspace_id: str) -> bool:
        """Save a workspace to disk"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        filepath = os.path.join(self.storage_path, f"{workspace_id}.json")
        with open(filepath, "w") as f:
            json.dump(workspace.to_dict(), f, indent=2)
        
        return True
    
    def load_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Load a workspace from disk"""
        import os
        filepath = os.path.join(self.storage_path, f"{workspace_id}.json")
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return self._workspace_from_dict(data)
    
    def _workspace_from_dict(self, data: Dict) -> Workspace:
        """Create workspace from dict"""
        workspace = Workspace(
            workspace_id=data["workspace_id"],
            name=data["name"],
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
        
        # Load windows
        for wid, wdata in data.get("windows", {}).items():
            workspace.windows[wid] = self._window_from_dict(wdata)
        
        return workspace
    
    def _window_from_dict(self, data: Dict) -> Window:
        """Create window from dict"""
        from .core import WindowState, DockPosition
        
        return Window(
            window_id=data["window_id"],
            title=data["title"],
            component=data["component"],
            x=data.get("position", {}).get("x", 0),
            y=data.get("position", {}).get("y", 0),
            width=data.get("size", {}).get("width", 800),
            height=data.get("size", {}).get("height", 600),
            state=WindowState(data.get("state", "normal")),
            dock_position=DockPosition(data.get("dock_position", "floating")),
            is_visible=data.get("is_visible", True),
        )
    
    # ========== Callbacks ==========
    
    def on_workspace_changed(
        self,
        callback: Callable[[Workspace], None]
    ) -> None:
        """Register workspace change callback"""
        self._workspace_changed_callbacks.append(callback)
    
    def on_window_changed(
        self,
        callback: Callable[[Workspace, Window], None]
    ) -> None:
        """Register window change callback"""
        self._window_changed_callbacks.append(callback)
    
    def _notify_workspace_changed(self, workspace: Workspace) -> None:
        """Notify workspace changed"""
        for callback in self._workspace_changed_callbacks:
            try:
                callback(workspace)
            except Exception as e:
                logger.error(f"Workspace change callback error: {e}")
    
    def _notify_window_changed(
        self,
        workspace: Workspace,
        window: Window,
        removed: bool = False
    ) -> None:
        """Notify window changed"""
        for callback in self._window_changed_callbacks:
            try:
                callback(workspace, window)
            except Exception as e:
                logger.error(f"Window change callback error: {e}")
