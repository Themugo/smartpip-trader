"""
Workspace Manager - Customizable Layouts and State Persistence

Provides comprehensive workspace management with:
- Multiple workspace templates
- Panel configurations
- Chart layouts
- Strategy selections
- Full state persistence
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import deque

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """Workspace layout types"""
    GRID = "grid"
    SPLIT_VERTICAL = "split_vertical"
    SPLIT_HORIZONTAL = "split_horizontal"
    TABBED = "tabbed"
    FLOATING = "floating"


class PanelType(Enum):
    """Panel types available in workspaces"""
    # Trading panels
    CHART = "chart"
    ORDER_BOOK = "order_book"
    TRADE_PANEL = "trade_panel"
    POSITIONS = "positions"
    ORDERS = "orders"
    TRADE_HISTORY = "trade_history"
    
    # Analysis panels
    ANALYZER_OUTPUT = "analyzer_output"
    AI_SIGNALS = "ai_signals"
    CONFIDENCE = "confidence"
    PATTERN_DETECTION = "pattern_detection"
    REGIME_INDICATOR = "regime_indicator"
    
    # Risk panels
    RISK_DASHBOARD = "risk_dashboard"
    EXPOSURE = "exposure"
    DRAWDOWN = "drawdown"
    ALERTS = "alerts"
    
    # Research panels
    BACKTEST_RESULTS = "backtest_results"
    STRATEGY_COMPARE = "strategy_compare"
    FEATURE_ANALYSIS = "feature_analysis"
    EXPERIMENT_TRACKER = "experiment_tracker"
    
    # Utility panels
    WATCHLIST = "watchlist"
    NEWS_FEED = "news_feed"
    NOTES = "notes"
    TERMINAL = "terminal"
    SETTINGS = "settings"
    
    # Timeline
    EVENT_TIMELINE = "event_timeline"
    TRADE_LOG = "trade_log"


@dataclass
class PanelPosition:
    """Panel position and size"""
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 100
    z_index: int = 0


@dataclass
class PanelState:
    """State of a panel in the workspace"""
    id: str
    panel_type: PanelType
    title: str
    position: PanelPosition
    layout: LayoutType = LayoutType.GRID
    is_visible: bool = True
    is_locked: bool = False
    is_minimized: bool = False
    is_maximized: bool = False
    configuration: Dict[str, Any] = field(default_factory=dict)
    data_source: Optional[str] = None
    refresh_interval: int = 5  # seconds
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "panel_type": self.panel_type.value,
            "title": self.title,
            "position": self.position.__dict__,
            "layout": self.layout.value,
            "is_visible": self.is_visible,
            "is_locked": self.is_locked,
            "is_minimized": self.is_minimized,
            "is_maximized": self.is_maximized,
            "configuration": self.configuration,
            "data_source": self.data_source,
            "refresh_interval": self.refresh_interval,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PanelState":
        pos_data = data.get("position", {})
        position = PanelPosition(
            x=pos_data.get("x", 0),
            y=pos_data.get("y", 0),
            width=pos_data.get("width", 100),
            height=pos_data.get("height", 100),
            z_index=pos_data.get("z_index", 0),
        )
        return cls(
            id=data["id"],
            panel_type=PanelType(data["panel_type"]),
            title=data["title"],
            position=position,
            layout=LayoutType(data.get("layout", "grid")),
            is_visible=data.get("is_visible", True),
            is_locked=data.get("is_locked", False),
            is_minimized=data.get("is_minimized", False),
            is_maximized=data.get("is_maximized", False),
            configuration=data.get("configuration", {}),
            data_source=data.get("data_source"),
            refresh_interval=data.get("refresh_interval", 5),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.now(timezone.utc),
        )


@dataclass
class ChartLayout:
    """Chart configuration within a workspace"""
    id: str
    symbol: str
    timeframe: str = "1m"
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    drawings: List[Dict[str, Any]] = field(default_factory=list)
    overlays: Dict[str, bool] = field(default_factory=dict)
    chart_type: str = "candlestick"  # candlestick, line, area
    zoom_level: float = 1.0
    scroll_position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "indicators": self.indicators,
            "drawings": self.drawings,
            "overlays": self.overlays,
            "chart_type": self.chart_type,
            "zoom_level": self.zoom_level,
            "scroll_position": self.scroll_position,
        }


@dataclass
class WorkspaceLayout:
    """Complete workspace layout configuration"""
    id: str
    name: str
    description: str
    panels: List[PanelState] = field(default_factory=list)
    charts: List[ChartLayout] = field(default_factory=list)
    enabled_strategies: List[str] = field(default_factory=list)
    watchlists: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    theme: str = "dark"
    notifications_enabled: Dict[str, bool] = field(default_factory=dict)
    grid_config: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    is_template: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "panels": [p.to_dict() for p in self.panels],
            "charts": [c.to_dict() for c in self.charts],
            "enabled_strategies": self.enabled_strategies,
            "watchlists": self.watchlists,
            "filters": self.filters,
            "theme": self.theme,
            "notifications_enabled": self.notifications_enabled,
            "grid_config": self.grid_config,
            "version": self.version,
            "is_template": self.is_template,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceLayout":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            panels=[PanelState.from_dict(p) for p in data.get("panels", [])],
            charts=[ChartLayout(**c) if isinstance(c, dict) else c for c in data.get("charts", [])],
            enabled_strategies=data.get("enabled_strategies", []),
            watchlists=data.get("watchlists", []),
            filters=data.get("filters", {}),
            theme=data.get("theme", "dark"),
            notifications_enabled=data.get("notifications_enabled", {}),
            grid_config=data.get("grid_config", {}),
            version=data.get("version", 1),
            is_template=data.get("is_template", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
            created_by=data.get("created_by"),
        )


class WorkspaceManager:
    """
    Manages multiple workspace layouts with full state persistence.
    
    Features:
    - Multiple named workspaces
    - Template-based creation
    - Panel customization
    - Chart configurations
    - Strategy selections
    - State auto-save
    - Import/export
    """
    
    def __init__(self, storage_path: str = "data/workspaces"):
        self._storage_path = storage_path
        self._workspaces: Dict[str, WorkspaceLayout] = {}
        self._active_workspace_id: Optional[str] = None
        self._change_callbacks: List[Callable[[str, WorkspaceLayout], None]] = []
        self._auto_save = True
        self._save_debounce = 1.0  # seconds
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_workspaces()
    
    def _load_workspaces(self) -> None:
        """Load workspaces from storage"""
        index_file = os.path.join(self._storage_path, "index.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, "r") as f:
                    data = json.load(f)
                
                # Load workspace files
                for ws_id in data.get("workspace_ids", []):
                    ws_file = os.path.join(self._storage_path, f"{ws_id}.json")
                    if os.path.exists(ws_file):
                        with open(ws_file, "r") as f:
                            ws_data = json.load(f)
                            self._workspaces[ws_id] = WorkspaceLayout.from_dict(ws_data)
                
                self._active_workspace_id = data.get("active_workspace_id")
                
                logger.info(f"Loaded {len(self._workspaces)} workspaces")
            except Exception as e:
                logger.error(f"Failed to load workspaces: {e}")
    
    def _save_workspace(self, workspace: WorkspaceLayout) -> None:
        """Save a single workspace to storage"""
        ws_file = os.path.join(self._storage_path, f"{workspace.id}.json")
        
        try:
            with open(ws_file, "w") as f:
                json.dump(workspace.to_dict(), f, indent=2)
            
            # Update index
            self._update_index()
        except Exception as e:
            logger.error(f"Failed to save workspace {workspace.id}: {e}")
    
    def _update_index(self) -> None:
        """Update the workspace index"""
        index_file = os.path.join(self._storage_path, "index.json")
        
        data = {
            "workspace_ids": list(self._workspaces.keys()),
            "active_workspace_id": self._active_workspace_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(index_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def create_workspace(
        self,
        name: str,
        description: str = "",
        template: Optional["WorkspaceTemplate"] = None,
        created_by: Optional[str] = None,
    ) -> WorkspaceLayout:
        """
        Create a new workspace.
        
        Args:
            name: Workspace name
            description: Optional description
            template: Optional template to base workspace on
            created_by: User who created the workspace
            
        Returns:
            Created workspace layout
        """
        workspace_id = str(uuid.uuid4())
        
        if template:
            # Create from template
            workspace = WorkspaceLayout(
                id=workspace_id,
                name=name,
                description=description or template.description,
                panels=[PanelState.from_dict(p.to_dict()) for p in template.panels],
                charts=[ChartLayout(**c.to_dict()) for c in template.charts],
                enabled_strategies=template.enabled_strategies.copy(),
                watchlists=template.watchlists.copy(),
                filters=template.filters.copy(),
                theme=template.theme,
                created_by=created_by,
            )
        else:
            # Create empty workspace
            workspace = WorkspaceLayout(
                id=workspace_id,
                name=name,
                description=description,
                created_by=created_by,
            )
        
        self._workspaces[workspace_id] = workspace
        self._save_workspace(workspace)
        
        logger.info(f"Created workspace: {name} ({workspace_id})")
        return workspace
    
    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceLayout]:
        """Get a workspace by ID"""
        return self._workspaces.get(workspace_id)
    
    def get_all_workspaces(self) -> List[WorkspaceLayout]:
        """Get all workspaces"""
        return list(self._workspaces.values())
    
    def update_workspace(
        self,
        workspace_id: str,
        updates: Dict[str, Any],
    ) -> Optional[WorkspaceLayout]:
        """
        Update a workspace.
        
        Args:
            workspace_id: Workspace to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated workspace or None if not found
        """
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        # Apply updates
        if "name" in updates:
            workspace.name = updates["name"]
        if "description" in updates:
            workspace.description = updates["description"]
        if "panels" in updates:
            workspace.panels = [PanelState.from_dict(p) for p in updates["panels"]]
        if "charts" in updates:
            workspace.charts = [ChartLayout(**c) if isinstance(c, dict) else c for c in updates["charts"]]
        if "enabled_strategies" in updates:
            workspace.enabled_strategies = updates["enabled_strategies"]
        if "watchlists" in updates:
            workspace.watchlists = updates["watchlists"]
        if "filters" in updates:
            workspace.filters = updates["filters"]
        if "theme" in updates:
            workspace.theme = updates["theme"]
        if "notifications_enabled" in updates:
            workspace.notifications_enabled = updates["notifications_enabled"]
        
        workspace.version += 1
        workspace.updated_at = datetime.now(timezone.utc)
        
        self._save_workspace(workspace)
        self._notify_change(workspace_id, workspace)
        
        return workspace
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace"""
        if workspace_id not in self._workspaces:
            return False
        
        # Don't delete the last workspace
        if len(self._workspaces) <= 1:
            logger.warning("Cannot delete the last workspace")
            return False
        
        workspace = self._workspaces.pop(workspace_id)
        
        # Delete file
        ws_file = os.path.join(self._storage_path, f"{workspace_id}.json")
        if os.path.exists(ws_file):
            os.remove(ws_file)
        
        # Switch to another workspace if active was deleted
        if self._active_workspace_id == workspace_id:
            self._active_workspace_id = next(iter(self._workspaces.keys()))
        
        self._update_index()
        
        logger.info(f"Deleted workspace: {workspace_id}")
        return True
    
    def duplicate_workspace(
        self,
        workspace_id: str,
        new_name: Optional[str] = None,
    ) -> Optional[WorkspaceLayout]:
        """Duplicate an existing workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        return self.create_workspace(
            name=new_name or f"{workspace.name} (Copy)",
            description=workspace.description,
            created_by=workspace.created_by,
        )
    
    def set_active_workspace(self, workspace_id: str) -> bool:
        """Set the active workspace"""
        if workspace_id not in self._workspaces:
            return False
        
        self._active_workspace_id = workspace_id
        self._update_index()
        
        workspace = self._workspaces[workspace_id]
        self._notify_change(workspace_id, workspace)
        
        return True
    
    def get_active_workspace(self) -> Optional[WorkspaceLayout]:
        """Get the currently active workspace"""
        if self._active_workspace_id:
            return self._workspaces.get(self._active_workspace_id)
        return next(iter(self._workspaces.values())) if self._workspaces else None
    
    def add_panel(
        self,
        workspace_id: str,
        panel_type: PanelType,
        title: str,
        position: Optional[PanelPosition] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Optional[PanelState]:
        """Add a panel to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        panel = PanelState(
            id=str(uuid.uuid4()),
            panel_type=panel_type,
            title=title,
            position=position or PanelPosition(),
            configuration=configuration or {},
        )
        
        workspace.panels.append(panel)
        workspace.version += 1
        workspace.updated_at = datetime.now(timezone.utc)
        
        self._save_workspace(workspace)
        self._notify_change(workspace_id, workspace)
        
        return panel
    
    def remove_panel(
        self,
        workspace_id: str,
        panel_id: str,
    ) -> bool:
        """Remove a panel from a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        workspace.panels = [p for p in workspace.panels if p.id != panel_id]
        workspace.version += 1
        workspace.updated_at = datetime.now(timezone.utc)
        
        self._save_workspace(workspace)
        self._notify_change(workspace_id, workspace)
        
        return True
    
    def update_panel(
        self,
        workspace_id: str,
        panel_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a panel in a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return False
        
        for panel in workspace.panels:
            if panel.id == panel_id:
                if "title" in updates:
                    panel.title = updates["title"]
                if "position" in updates:
                    pos_data = updates["position"]
                    panel.position = PanelPosition(**pos_data) if isinstance(pos_data, dict) else pos_data
                if "configuration" in updates:
                    panel.configuration = updates["configuration"]
                if "is_visible" in updates:
                    panel.is_visible = updates["is_visible"]
                if "is_locked" in updates:
                    panel.is_locked = updates["is_locked"]
                if "is_minimized" in updates:
                    panel.is_minimized = updates["is_minimized"]
                if "is_maximized" in updates:
                    panel.is_maximized = updates["is_maximized"]
                
                panel.last_updated = datetime.now(timezone.utc)
                workspace.version += 1
                workspace.updated_at = datetime.now(timezone.utc)
                
                self._save_workspace(workspace)
                self._notify_change(workspace_id, workspace)
                return True
        
        return False
    
    def add_chart(
        self,
        workspace_id: str,
        symbol: str,
        timeframe: str = "1m",
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChartLayout]:
        """Add a chart to a workspace"""
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        
        chart = ChartLayout(
            id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            **(configuration or {}),
        )
        
        workspace.charts.append(chart)
        workspace.version += 1
        workspace.updated_at = datetime.now(timezone.utc)
        
        self._save_workspace(workspace)
        self._notify_change(workspace_id, workspace)
        
        return chart
    
    def export_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Export a workspace for sharing"""
        workspace = self._workspaces.get(workspace_id)
        return workspace.to_dict() if workspace else None
    
    def import_workspace(
        self,
        data: Dict[str, Any],
        new_name: Optional[str] = None,
    ) -> Optional[WorkspaceLayout]:
        """Import a workspace from shared data"""
        try:
            data["id"] = str(uuid.uuid4())  # Generate new ID
            if new_name:
                data["name"] = new_name
            
            workspace = WorkspaceLayout.from_dict(data)
            workspace.created_at = datetime.now(timezone.utc)
            workspace.updated_at = datetime.now(timezone.utc)
            
            self._workspaces[workspace.id] = workspace
            self._save_workspace(workspace)
            
            return workspace
        except Exception as e:
            logger.error(f"Failed to import workspace: {e}")
            return None
    
    def on_change(
        self,
        callback: Callable[[str, WorkspaceLayout], None],
    ) -> None:
        """Register a change callback"""
        self._change_callbacks.append(callback)
    
    def _notify_change(self, workspace_id: str, workspace: WorkspaceLayout) -> None:
        """Notify registered callbacks"""
        for callback in self._change_callbacks:
            try:
                callback(workspace_id, workspace)
            except Exception as e:
                logger.error(f"Workspace change callback error: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            "workspaces": [w.to_dict() for w in self._workspaces.values()],
            "active_workspace_id": self._active_workspace_id,
        }
