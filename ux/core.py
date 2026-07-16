"""
UX Core
========

Core classes for user interface management.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class WindowState(Enum):
    """Window state"""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    DOCKED = "docked"
    FLOATING = "floating"


class DockPosition(Enum):
    """Dock position"""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    FLOATING = "floating"


class LayoutType(Enum):
    """Layout type"""
    SINGLE = "single"
    SPLIT_HORIZONTAL = "split_horizontal"
    SPLIT_VERTICAL = "split_vertical"
    TABBED = "tabbed"
    GRID = "grid"


@dataclass
class Window:
    """UI Window"""
    window_id: str
    title: str
    component: str  # Component identifier
    
    # Position and size
    x: int = 0
    y: int = 0
    width: int = 800
    height: int = 600
    min_width: int = 200
    min_height: int = 150
    
    # State
    state: WindowState = WindowState.NORMAL
    dock_position: DockPosition = DockPosition.FLOATING
    is_visible: bool = True
    is_focused: bool = False
    
    # Properties
    is_closable: bool = True
    is_minimizable: bool = True
    is_maximizable: bool = True
    is_resizable: bool = True
    is_dockable: bool = True
    
    # Parent/children
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)  # Child window IDs
    
    # Tab group
    tab_group: Optional[str] = None
    tab_index: int = 0
    
    # Metadata
    icon: Optional[str] = None
    badge: Optional[str] = None
    tooltip: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "title": self.title,
            "component": self.component,
            "position": {"x": self.x, "y": self.y},
            "size": {"width": self.width, "height": self.height},
            "state": self.state.value,
            "dock_position": self.dock_position.value,
            "is_visible": self.is_visible,
            "is_focused": self.is_focused,
        }


@dataclass
class Layout:
    """Layout configuration"""
    layout_id: str
    name: str
    layout_type: LayoutType
    children: List[Dict[str, Any]] = field(default_factory=list)
    
    # For split layouts
    split_ratio: float = 0.5
    
    # For grid layouts
    rows: int = 1
    columns: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "layout_type": self.layout_type.value,
            "children": self.children,
            "split_ratio": self.split_ratio,
            "rows": self.rows,
            "columns": self.columns,
        }


@dataclass
class Monitor:
    """Display monitor"""
    monitor_id: str
    name: str
    
    # Geometry
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    is_primary: bool = False
    scale_factor: float = 1.0
    
    # Work area (excluding taskbar, etc.)
    work_x: int = 0
    work_y: int = 0
    work_width: int = 1920
    work_height: int = 1040
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "monitor_id": self.monitor_id,
            "name": self.name,
            "geometry": {
                "x": self.x, "y": self.y,
                "width": self.width, "height": self.height
            },
            "is_primary": self.is_primary,
            "scale_factor": self.scale_factor,
            "work_area": {
                "x": self.work_x, "y": self.work_y,
                "width": self.work_width, "height": self.work_height
            }
        }


@dataclass
class Workspace:
    """
    Complete workspace configuration.
    
    A workspace contains all windows, layouts, and their positions
    for a complete user environment.
    """
    workspace_id: str
    name: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Windows in workspace
    windows: Dict[str, Window] = field(default_factory=dict)
    
    # Layout configuration
    layouts: Dict[str, Layout] = field(default_factory=dict)
    active_layout_id: Optional[str] = None
    
    # Monitors
    monitors: List[Monitor] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    is_default: bool = False
    is_template: bool = False
    
    # User preferences
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def add_window(self, window: Window) -> None:
        """Add a window to the workspace"""
        self.windows[window.window_id] = window
        self.updated_at = time.time()
    
    def remove_window(self, window_id: str) -> Optional[Window]:
        """Remove a window from the workspace"""
        window = self.windows.pop(window_id, None)
        if window:
            self.updated_at = time.time()
        return window
    
    def get_window(self, window_id: str) -> Optional[Window]:
        """Get a window by ID"""
        return self.windows.get(window_id)
    
    def get_visible_windows(self) -> List[Window]:
        """Get all visible windows"""
        return [w for w in self.windows.values() if w.is_visible]
    
    def get_docked_windows(self, position: DockPosition) -> List[Window]:
        """Get windows docked to a position"""
        return [w for w in self.windows.values() if w.dock_position == position]
    
    def get_active_window(self) -> Optional[Window]:
        """Get the currently focused window"""
        for w in self.windows.values():
            if w.is_focused:
                return w
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "windows": {k: v.to_dict() for k, v in self.windows.items()},
            "layouts": {k: v.to_dict() for k, v in self.layouts.items()},
            "active_layout_id": self.active_layout_id,
            "monitors": [m.to_dict() for m in self.monitors],
            "is_default": self.is_default,
            "is_template": self.is_template,
        }


@dataclass
class WorkspaceTemplate:
    """Template for creating workspaces"""
    template_id: str
    name: str
    description: str
    
    # Windows to create
    window_configs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Layout
    layout_type: LayoutType = LayoutType.SINGLE
    layout_config: Dict[str, Any] = field(default_factory=dict)
    
    # Target monitor
    target_monitor: Optional[str] = None
    
    # Tags
    category: str = "general"  # trading, analysis, monitoring, etc.
    tags: List[str] = field(default_factory=list)
    
    def create_workspace(self, name: str) -> Workspace:
        """Create a workspace from this template"""
        workspace = Workspace(
            workspace_id=str(uuid.uuid4()),
            name=name,
        )
        
        # Create windows
        for config in self.window_configs:
            window = Window(
                window_id=str(uuid.uuid4()),
                title=config.get("title", "New Window"),
                component=config.get("component", ""),
                width=config.get("width", 800),
                height=config.get("height", 600),
            )
            workspace.add_window(window)
        
        return workspace
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "window_configs": self.window_configs,
            "layout_type": self.layout_type.value,
            "layout_config": self.layout_config,
            "category": self.category,
            "tags": self.tags,
        }


class DefaultTemplates:
    """Default workspace templates"""
    
    @staticmethod
    def trading_workspace() -> WorkspaceTemplate:
        """Standard trading workspace"""
        return WorkspaceTemplate(
            template_id="template_trading",
            name="Trading Workspace",
            description="Standard trading interface with charts and order entry",
            window_configs=[
                {"title": "Chart", "component": "chart", "width": 800, "height": 600},
                {"title": "Order Entry", "component": "order_entry", "width": 300, "height": 400},
                {"title": "Positions", "component": "positions", "width": 400, "height": 300},
                {"title": "Market Overview", "component": "market_overview", "width": 300, "height": 200},
            ],
            layout_type=LayoutType.SPLIT_HORIZONTAL,
            category="trading",
            tags=["default", "trading", "orders"],
        )
    
    @staticmethod
    def analysis_workspace() -> WorkspaceTemplate:
        """Analysis workspace"""
        return WorkspaceTemplate(
            template_id="template_analysis",
            name="Analysis Workspace",
            description="Workspace for market analysis and research",
            window_configs=[
                {"title": "Chart", "component": "chart", "width": 1000, "height": 700},
                {"title": "Indicators", "component": "indicators", "width": 400, "height": 400},
                {"title": "News", "component": "news", "width": 400, "height": 300},
            ],
            layout_type=LayoutType.SPLIT_VERTICAL,
            category="analysis",
            tags=["analysis", "research"],
        )
    
    @staticmethod
    def monitoring_workspace() -> WorkspaceTemplate:
        """Monitoring workspace"""
        return WorkspaceTemplate(
            template_id="template_monitoring",
            name="Monitoring Workspace",
            description="Multi-window monitoring dashboard",
            window_configs=[
                {"title": "Portfolio", "component": "portfolio", "width": 500, "height": 400},
                {"title": "Performance", "component": "performance", "width": 500, "height": 400},
                {"title": "Alerts", "component": "alerts", "width": 400, "height": 300},
                {"title": "Activity", "component": "activity", "width": 400, "height": 300},
            ],
            layout_type=LayoutType.GRID,
            layout_config={"rows": 2, "columns": 2},
            category="monitoring",
            tags=["monitoring", "dashboard"],
        )
