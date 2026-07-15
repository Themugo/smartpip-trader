"""
Workspace State Management

Manages workspace-specific state including:
- Panel layouts
- Widget configurations
- View preferences
- UI state persistence
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkspaceLayout(Enum):
    """Predefined workspace layouts"""
    DEFAULT = "default"
    COMPACT = "compact"
    EXPANDED = "expanded"
    FOCUS = "focus"
    CUSTOM = "custom"


@dataclass
class PanelConfig:
    """Configuration for a workspace panel"""
    id: str
    type: str
    title: str
    position: Dict[str, int]  # x, y, width, height
    is_visible: bool = True
    is_locked: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "position": self.position,
            "is_visible": self.is_visible,
            "is_locked": self.is_locked,
            "settings": self.settings,
            "order": self.order,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PanelConfig":
        return cls(
            id=data["id"],
            type=data["type"],
            title=data["title"],
            position=data["position"],
            is_visible=data.get("is_visible", True),
            is_locked=data.get("is_locked", False),
            settings=data.get("settings", {}),
            order=data.get("order", 0),
        )


@dataclass
class WidgetConfig:
    """Configuration for a workspace widget"""
    id: str
    type: str
    panel_id: str
    settings: Dict[str, Any] = field(default_factory=dict)
    data_source: Optional[str] = None
    refresh_interval: int = 5  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "panel_id": self.panel_id,
            "settings": self.settings,
            "data_source": self.data_source,
            "refresh_interval": self.refresh_interval,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetConfig":
        return cls(
            id=data["id"],
            type=data["type"],
            panel_id=data["panel_id"],
            settings=data.get("settings", {}),
            data_source=data.get("data_source"),
            refresh_interval=data.get("refresh_interval", 5),
        )


@dataclass
class WorkspaceState:
    """Complete state for a workspace"""
    workspace_id: str
    layout: WorkspaceLayout = WorkspaceLayout.DEFAULT
    panels: List[PanelConfig] = field(default_factory=list)
    widgets: List[WidgetConfig] = field(default_factory=list)
    view_settings: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_order: Dict[str, str] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "layout": self.layout.value,
            "panels": [p.to_dict() for p in self.panels],
            "widgets": [w.to_dict() for w in self.widgets],
            "view_settings": self.view_settings,
            "filters": self.filters,
            "sort_order": self.sort_order,
            "last_updated": self.last_updated.isoformat(),
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceState":
        return cls(
            workspace_id=data["workspace_id"],
            layout=WorkspaceLayout(data.get("layout", "default")),
            panels=[PanelConfig.from_dict(p) for p in data.get("panels", [])],
            widgets=[WidgetConfig.from_dict(w) for w in data.get("widgets", [])],
            view_settings=data.get("view_settings", {}),
            filters=data.get("filters", {}),
            sort_order=data.get("sort_order", {}),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.utcnow(),
            version=data.get("version", "1.0"),
        )
    
    def add_panel(self, panel: PanelConfig) -> None:
        """Add a panel to the workspace"""
        self.panels.append(panel)
        self.last_updated = datetime.utcnow()
    
    def remove_panel(self, panel_id: str) -> bool:
        """Remove a panel from the workspace"""
        for i, panel in enumerate(self.panels):
            if panel.id == panel_id:
                self.panels.pop(i)
                # Also remove widgets in this panel
                self.widgets = [w for w in self.widgets if w.panel_id != panel_id]
                self.last_updated = datetime.utcnow()
                return True
        return False
    
    def update_panel(self, panel_id: str, updates: Dict[str, Any]) -> bool:
        """Update panel configuration"""
        for panel in self.panels:
            if panel.id == panel_id:
                for key, value in updates.items():
                    if hasattr(panel, key):
                        setattr(panel, key, value)
                self.last_updated = datetime.utcnow()
                return True
        return False
    
    def add_widget(self, widget: WidgetConfig) -> None:
        """Add a widget to the workspace"""
        self.widgets.append(widget)
        self.last_updated = datetime.utcnow()
    
    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget from the workspace"""
        for i, widget in enumerate(self.widgets):
            if widget.id == widget_id:
                self.widgets.pop(i)
                self.last_updated = datetime.utcnow()
                return True
        return False
    
    def update_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """Update widget configuration"""
        for widget in self.widgets:
            if widget.id == widget_id:
                for key, value in updates.items():
                    if hasattr(widget, key):
                        setattr(widget, key, value)
                self.last_updated = datetime.utcnow()
                return True
        return False
    
    def get_panels_by_type(self, panel_type: str) -> List[PanelConfig]:
        """Get all panels of a specific type"""
        return [p for p in self.panels if p.type == panel_type]
    
    def get_widgets_by_panel(self, panel_id: str) -> List[WidgetConfig]:
        """Get all widgets in a specific panel"""
        return [w for w in self.widgets if w.panel_id == panel_id]


# Default panel configurations for each workspace type
DEFAULT_PANEL_CONFIGS = {
    "dashboard": [
        {"id": "overview", "type": "stats", "title": "Overview", "position": {"x": 0, "y": 0, "w": 12, "h": 3}},
        {"id": "chart", "type": "chart", "title": "Price Chart", "position": {"x": 0, "y": 3, "w": 8, "h": 6}},
        {"id": "signals", "type": "signals", "title": "Active Signals", "position": {"x": 8, "y": 3, "w": 4, "h": 6}},
        {"id": "trades", "type": "trades", "title": "Recent Trades", "position": {"x": 0, "y": 9, "w": 6, "h": 4}},
        {"id": "performance", "type": "performance", "title": "Performance", "position": {"x": 6, "y": 9, "w": 6, "h": 4}},
    ],
    "live_trading": [
        {"id": "chart", "type": "chart", "title": "Trading Chart", "position": {"x": 0, "y": 0, "w": 8, "h": 8}},
        {"id": "controls", "type": "controls", "title": "Trading Controls", "position": {"x": 8, "y": 0, "w": 4, "h": 4}},
        {"id": "positions", "type": "positions", "title": "Open Positions", "position": {"x": 8, "y": 4, "w": 4, "h": 4}},
        {"id": "orders", "type": "orders", "title": "Order Book", "position": {"x": 0, "y": 8, "w": 6, "h": 4}},
        {"id": "risk", "type": "risk", "title": "Risk Metrics", "position": {"x": 6, "y": 8, "w": 6, "h": 4}},
    ],
    "paper_trading": [
        {"id": "chart", "type": "chart", "title": "Trading Chart", "position": {"x": 0, "y": 0, "w": 8, "h": 8}},
        {"id": "simulator", "type": "simulator", "title": "Trade Simulator", "position": {"x": 8, "y": 0, "w": 4, "h": 4}},
        {"id": "sim_trades", "type": "trades", "title": "Simulated Trades", "position": {"x": 8, "y": 4, "w": 4, "h": 4}},
        {"id": "comparison", "type": "comparison", "title": "vs Live Results", "position": {"x": 0, "y": 8, "w": 12, "h": 4}},
    ],
    "backtesting": [
        {"id": "config", "type": "config", "title": "Test Configuration", "position": {"x": 0, "y": 0, "w": 4, "h": 6}},
        {"id": "chart", "type": "chart", "title": "Equity Curve", "position": {"x": 4, "y": 0, "w": 8, "h": 6}},
        {"id": "results", "type": "results", "title": "Results", "position": {"x": 0, "y": 6, "w": 6, "h": 6}},
        {"id": "trades", "type": "trades", "title": "Trade Log", "position": {"x": 6, "y": 6, "w": 6, "h": 6}},
    ],
    "strategy_builder": [
        {"id": "canvas", "type": "canvas", "title": "Strategy Canvas", "position": {"x": 0, "y": 0, "w": 10, "h": 10}},
        {"id": "blocks", "type": "blocks", "title": "Building Blocks", "position": {"x": 10, "y": 0, "w": 2, "h": 5}},
        {"id": "properties", "type": "properties", "title": "Properties", "position": {"x": 10, "y": 5, "w": 2, "h": 5}},
        {"id": "code", "type": "code", "title": "Generated Code", "position": {"x": 0, "y": 10, "w": 12, "h": 2}},
    ],
    "analytics": [
        {"id": "summary", "type": "stats", "title": "Summary", "position": {"x": 0, "y": 0, "w": 12, "h": 2}},
        {"id": "equity", "type": "chart", "title": "Equity Curve", "position": {"x": 0, "y": 2, "w": 6, "h": 5}},
        {"id": "drawdown", "type": "chart", "title": "Drawdown", "position": {"x": 6, "y": 2, "w": 6, "h": 5}},
        {"id": "trades", "type": "trades", "title": "Trade Analysis", "position": {"x": 0, "y": 7, "w": 8, "h": 5}},
        {"id": "export", "type": "export", "title": "Export", "position": {"x": 8, "y": 7, "w": 4, "h": 5}},
    ],
    "risk_center": [
        {"id": "limits", "type": "limits", "title": "Risk Limits", "position": {"x": 0, "y": 0, "w": 4, "h": 4}},
        {"id": "exposure", "type": "exposure", "title": "Exposure", "position": {"x": 4, "y": 0, "w": 4, "h": 4}},
        {"id": "alerts", "type": "alerts", "title": "Risk Alerts", "position": {"x": 8, "y": 0, "w": 4, "h": 4}},
        {"id": "history", "type": "history", "title": "Risk History", "position": {"x": 0, "y": 4, "w": 12, "h": 8}},
    ],
    "notifications": [
        {"id": "filters", "type": "filters", "title": "Filters", "position": {"x": 0, "y": 0, "w": 3, "h": 12}},
        {"id": "list", "type": "list", "title": "Notifications", "position": {"x": 3, "y": 0, "w": 9, "h": 12}},
    ],
    "ai_command_center": [
        {"id": "agents", "type": "agents", "title": "AI Agents", "position": {"x": 0, "y": 0, "w": 4, "h": 6}},
        {"id": "commands", "type": "commands", "title": "Command History", "position": {"x": 4, "y": 0, "w": 8, "h": 6}},
        {"id": "status", "type": "status", "title": "Status", "position": {"x": 0, "y": 6, "w": 12, "h": 6}},
    ],
    "developer_console": [
        {"id": "terminal", "type": "terminal", "title": "Terminal", "position": {"x": 0, "y": 0, "w": 8, "h": 8}},
        {"id": "logs", "type": "logs", "title": "Logs", "position": {"x": 8, "y": 0, "w": 4, "h": 8}},
        {"id": "api", "type": "api", "title": "API Explorer", "position": {"x": 0, "y": 8, "w": 12, "h": 4}},
    ],
    "settings": [
        {"id": "general", "type": "form", "title": "General", "position": {"x": 0, "y": 0, "w": 6, "h": 6}},
        {"id": "trading", "type": "form", "title": "Trading", "position": {"x": 6, "y": 0, "w": 6, "h": 6}},
        {"id": "accounts", "type": "accounts", "title": "Accounts", "position": {"x": 0, "y": 6, "w": 6, "h": 6}},
        {"id": "security", "type": "security", "title": "Security", "position": {"x": 6, "y": 6, "w": 6, "h": 6}},
    ],
}


def create_default_workspace_state(workspace_id: str) -> WorkspaceState:
    """Create a default workspace state with panels"""
    state = WorkspaceState(workspace_id=workspace_id)
    
    panels_config = DEFAULT_PANEL_CONFIGS.get(workspace_id, [])
    for i, panel_data in enumerate(panels_config):
        panel = PanelConfig(
            id=panel_data["id"],
            type=panel_data["type"],
            title=panel_data["title"],
            position=panel_data["position"],
            order=i,
        )
        state.add_panel(panel)
    
    return state
