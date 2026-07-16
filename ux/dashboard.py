"""
Dashboard System
===============

Customizable dashboards with widgets.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DashboardWidget:
    """A widget on a dashboard"""
    widget_id: str
    widget_type: str  # chart, table, metric, graph, etc.
    title: str
    
    # Position
    x: int = 0
    y: int = 0
    width: int = 1
    height: int = 1
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Data source
    data_source: Optional[str] = None  # API endpoint or data function
    refresh_interval: int = 0  # Seconds (0 = manual)
    
    # State
    is_visible: bool = True
    is_loading: bool = False
    error: Optional[str] = None
    
    # Permissions
    requires_role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "position": {"x": self.x, "y": self.y, "w": self.width, "h": self.height},
            "config": self.config,
            "is_visible": self.is_visible,
        }


@dataclass
class DashboardLayout:
    """Dashboard layout configuration"""
    layout_id: str
    name: str
    type: str = "grid"  # grid, freeform, tabs
    
    # Grid settings
    columns: int = 12
    row_height: int = 80
    margin: List[int] = field(default_factory=lambda: [10, 10])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "type": self.type,
            "columns": self.columns,
        }


@dataclass
class Dashboard:
    """A customizable dashboard"""
    dashboard_id: str
    name: str
    
    # Widgets
    widgets: List[DashboardWidget] = field(default_factory=list)
    layout: DashboardLayout = field(default_factory=lambda: DashboardLayout(layout_id="default", name="Default"))
    
    # Settings
    is_default: bool = False
    is_shared: bool = False
    shared_with: List[str] = field(default_factory=list)  # User IDs
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = ""
    
    # Refresh
    auto_refresh: bool = True
    refresh_interval: int = 30  # Seconds
    
    def add_widget(self, widget: DashboardWidget) -> None:
        """Add a widget"""
        self.widgets.append(widget)
        self.updated_at = time.time()
    
    def remove_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """Remove a widget"""
        for i, w in enumerate(self.widgets):
            if w.widget_id == widget_id:
                self.widgets.pop(i)
                self.updated_at = time.time()
                return w
        return None
    
    def get_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """Get a widget by ID"""
        for w in self.widgets:
            if w.widget_id == widget_id:
                return w
        return None
    
    def update_widget(
        self,
        widget_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a widget"""
        widget = self.get_widget(widget_id)
        if not widget:
            return False
        
        for key, value in updates.items():
            if hasattr(widget, key):
                setattr(widget, key, value)
        
        self.updated_at = time.time()
        return True
    
    def reorder_widgets(self, widget_order: List[str]) -> bool:
        """Reorder widgets"""
        if len(widget_order) != len(self.widgets):
            return False
        
        widget_map = {w.widget_id: w for w in self.widgets}
        self.widgets = [widget_map[wid] for wid in widget_order if wid in widget_map]
        self.updated_at = time.time()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "widgets": [w.to_dict() for w in self.widgets],
            "layout": self.layout.to_dict(),
            "is_default": self.is_default,
            "updated_at": self.updated_at,
        }


# Default widget types
DEFAULT_WIDGET_TYPES = {
    "portfolio_summary": {
        "name": "Portfolio Summary",
        "description": "Overview of portfolio value and performance",
        "default_size": {"width": 3, "height": 2},
    },
    "positions": {
        "name": "Positions",
        "description": "Current open positions",
        "default_size": {"width": 4, "height": 3},
    },
    "orders": {
        "name": "Recent Orders",
        "description": "Recent order activity",
        "default_size": {"width": 4, "height": 3},
    },
    "chart": {
        "name": "Price Chart",
        "description": "Interactive price chart",
        "default_size": {"width": 6, "height": 4},
    },
    "performance": {
        "name": "Performance",
        "description": "Performance metrics and charts",
        "default_size": {"width": 4, "height": 3},
    },
    "news": {
        "name": "News Feed",
        "description": "Latest market news",
        "default_size": {"width": 3, "height": 2},
    },
    "alerts": {
        "name": "Alerts",
        "description": "Trading alerts and notifications",
        "default_size": {"width": 3, "height": 2},
    },
    "watchlist": {
        "name": "Watchlist",
        "description": "Watched symbols",
        "default_size": {"width": 2, "height": 3},
    },
}


class DashboardManager:
    """
    Manages user dashboards.
    """
    
    def __init__(self):
        self._dashboards: Dict[str, Dashboard] = {}
        self._current_dashboard_id: Optional[str] = None
        self._listeners: List[Callable] = []
    
    # ========== Dashboard Management ==========
    
    def create_dashboard(
        self,
        name: str,
        layout_type: str = "grid"
    ) -> Dashboard:
        """Create a new dashboard"""
        dashboard = Dashboard(
            dashboard_id=str(uuid.uuid4()),
            name=name,
            layout=DashboardLayout(
                layout_id=str(uuid.uuid4()),
                name=f"{name} Layout",
                type=layout_type,
            ),
        )
        
        self._dashboards[dashboard.dashboard_id] = dashboard
        return dashboard
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard"""
        return self._dashboards.get(dashboard_id)
    
    def get_all_dashboards(self) -> List[Dashboard]:
        """Get all dashboards"""
        return list(self._dashboards.values())
    
    def get_current_dashboard(self) -> Optional[Dashboard]:
        """Get the current dashboard"""
        if self._current_dashboard_id:
            return self._dashboards.get(self._current_dashboard_id)
        return None
    
    def set_current_dashboard(self, dashboard_id: str) -> bool:
        """Set the current dashboard"""
        if dashboard_id in self._dashboards:
            self._current_dashboard_id = dashboard_id
            return True
        return False
    
    def update_dashboard(
        self,
        dashboard_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update dashboard settings"""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return False
        
        for key, value in updates.items():
            if key == "widgets":
                continue  # Handle separately
            elif hasattr(dashboard, key):
                setattr(dashboard, key, value)
        
        dashboard.updated_at = time.time()
        return True
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard"""
        if dashboard_id in self._dashboards:
            dashboard = self._dashboards.pop(dashboard_id)
            if self._current_dashboard_id == dashboard_id:
                self._current_dashboard_id = None
            return True
        return False
    
    def duplicate_dashboard(
        self,
        dashboard_id: str,
        new_name: Optional[str] = None
    ) -> Optional[Dashboard]:
        """Duplicate a dashboard"""
        original = self._dashboards.get(dashboard_id)
        if not original:
            return None
        
        duplicate = Dashboard(
            dashboard_id=str(uuid.uuid4()),
            name=new_name or f"{original.name} (Copy)",
            widgets=[w for w in original.widgets],
            layout=original.layout,
        )
        
        self._dashboards[duplicate.dashboard_id] = duplicate
        return duplicate
    
    # ========== Widget Management ==========
    
    def add_widget(
        self,
        dashboard_id: str,
        widget_type: str,
        title: str,
        position: Optional[Dict[str, int]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[DashboardWidget]:
        """Add a widget to a dashboard"""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        
        widget = DashboardWidget(
            widget_id=str(uuid.uuid4()),
            widget_type=widget_type,
            title=title,
            x=position.get("x", 0) if position else 0,
            y=position.get("y", 0) if position else 0,
            config=config or {},
        )
        
        dashboard.add_widget(widget)
        self._notify_change("widget_added", widget)
        return widget
    
    def remove_widget(
        self,
        dashboard_id: str,
        widget_id: str
    ) -> bool:
        """Remove a widget"""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return False
        
        widget = dashboard.remove_widget(widget_id)
        if widget:
            self._notify_change("widget_removed", widget)
            return True
        return False
    
    def update_widget(
        self,
        dashboard_id: str,
        widget_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a widget"""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return False
        
        if dashboard.update_widget(widget_id, updates):
            self._notify_change("widget_updated", widget_id)
            return True
        return False
    
    # ========== Listeners ==========
    
    def on_change(self, callback: Callable) -> None:
        """Register change listener"""
        self._listeners.append(callback)
    
    def _notify_change(self, event: str, data: Any) -> None:
        """Notify listeners of changes"""
        for callback in self._listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Dashboard listener error: {e}")
    
    # ========== Defaults ==========
    
    def create_default_dashboard(self) -> Dashboard:
        """Create a default trading dashboard"""
        dashboard = self.create_dashboard("Trading Dashboard")
        dashboard.is_default = True
        
        # Add default widgets
        self.add_widget(dashboard.dashboard_id, "portfolio_summary", "Portfolio", {"x": 0, "y": 0, "w": 3, "h": 2})
        self.add_widget(dashboard.dashboard_id, "chart", "BTC/USD Chart", {"x": 3, "y": 0, "w": 6, "h": 4})
        self.add_widget(dashboard.dashboard_id, "positions", "Positions", {"x": 9, "y": 0, "w": 3, "h": 3})
        self.add_widget(dashboard.dashboard_id, "orders", "Recent Orders", {"x": 9, "y": 3, "w": 3, "h": 2})
        
        return dashboard
