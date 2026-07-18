"""
Dashboard Core
============

Core dashboard infrastructure with panels, widgets, and themes.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class Theme(Enum):
    """Dashboard themes"""
    DARK = "dark"
    LIGHT = "light"
    Bloomberg = "bloomberg"  # Classic Bloomberg orange
    System = "system"


class PanelType(Enum):
    """Types of panels"""
    # Health
    STRATEGY_HEALTH = "strategy_health"
    MODEL_HEALTH = "model_health"
    PLUGIN_HEALTH = "plugin_health"
    EXECUTION_HEALTH = "execution_health"
    PORTFOLIO_HEALTH = "portfolio_health"
    ACCOUNT_HEALTH = "account_health"
    
    # Intelligence
    MARKET_REGIME = "market_regime"
    AI_CONFIDENCE = "ai_confidence"
    OPPORTUNITY_SCORE = "opportunity_score"
    RISK_SCORE = "risk_score"
    AI_THOUGHTS = "ai_thoughts"
    ANALYZER_AGREEMENT = "analyzer_agreement"
    HISTORICAL_SIMILARITY = "historical_similarity"
    EXPECTED_VALUE = "expected_value"
    TRADE_ACCURACY = "trade_accuracy"
    DRAWDOWN = "drawdown"
    CAPITAL_ALLOCATION = "capital_allocation"
    
    # Queue
    TRADE_QUEUE = "trade_queue"
    PENDING_DECISIONS = "pending_decisions"
    OPPORTUNITY_TRACKER = "opportunity_tracker"
    
    # System
    SYSTEM_MONITOR = "system_monitor"
    SERVICE_STATUS = "service_status"


class WidgetType(Enum):
    """Types of widgets"""
    GAUGE = "gauge"
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"
    GRAPH = "graph"
    HISTOGRAM = "histogram"
    SCATTER = "scatter"
    TIMESERIES = "timeseries"


@dataclass
class Widget:
    """A single widget within a panel"""
    widget_id: str
    widget_type: WidgetType
    title: str
    data_source: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1})
    filters: List[str] = field(default_factory=list)
    drill_down_enabled: bool = True
    refresh_interval: float = 1.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "title": self.title,
            "data_source": self.data_source,
            "config": self.config,
            "position": self.position,
            "filters": self.filters,
            "drill_down_enabled": self.drill_down_enabled,
            "refresh_interval": self.refresh_interval
        }


@dataclass
class Panel:
    """A dashboard panel containing widgets"""
    panel_id: str
    panel_type: PanelType
    title: str
    widgets: List[Widget] = field(default_factory=list)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    visible: bool = True
    collapsible: bool = True
    header_color: str = "#1a1a2e"
    refresh_interval: float = 1.0
    
    def add_widget(self, widget: Widget) -> None:
        self.widgets.append(widget)
    
    def remove_widget(self, widget_id: str) -> bool:
        for i, w in enumerate(self.widgets):
            if w.widget_id == widget_id:
                self.widgets.pop(i)
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "panel_type": self.panel_type.value,
            "title": self.title,
            "widgets": [w.to_dict() for w in self.widgets],
            "position": self.position,
            "visible": self.visible,
            "collapsible": self.collapsible,
            "header_color": self.header_color,
            "refresh_interval": self.refresh_interval
        }


@dataclass
class Layout:
    """Dashboard layout configuration"""
    layout_id: str
    name: str
    panels: List[Panel]
    grid_columns: int = 12
    grid_row_height: int = 100
    monitor_index: int = 0  # For multi-monitor
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "name": self.name,
            "panels": [p.to_dict() for p in self.panels],
            "grid_columns": self.grid_columns,
            "grid_row_height": self.grid_row_height,
            "monitor_index": self.monitor_index,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    theme: Theme = Theme.DARK
    refresh_rate: float = 1.0  # seconds
    max_history: int = 1000
    enable_animations: bool = True
    compact_mode: bool = False
    show_tooltips: bool = True
    enable_keyboard_shortcuts: bool = True
    auto_save: bool = True
    save_interval: float = 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme.value,
            "refresh_rate": self.refresh_rate,
            "max_history": self.max_history,
            "enable_animations": self.enable_animations,
            "compact_mode": self.compact_mode,
            "show_tooltips": self.show_tooltips,
            "enable_keyboard_shortcuts": self.enable_keyboard_shortcuts,
            "auto_save": self.auto_save,
            "save_interval": self.save_interval
        }


class Dashboard:
    """
    Bloomberg-style Decision Intelligence Dashboard.
    
    Features:
    - Customizable panels and widgets
    - Real-time data streaming
    - Drill-down analytics
    - Dark/Light themes
    - Multi-monitor layouts
    - Persistent configuration
    """
    
    def __init__(
        self,
        config: DashboardConfig = None,
        db_path: str = "data/dashboard/config.json"
    ):
        self.config = config or DashboardConfig()
        self.db_path = db_path
        self.panels: Dict[str, Panel] = {}
        self.layouts: Dict[str, Layout] = {}
        self.current_layout: Optional[Layout] = None
        self._data_cache: Dict[str, Any] = {}
        self._update_callbacks: List[Callable] = []
        self._history: Dict[str, List[Any]] = {}
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    # Restore state if needed
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            data = {
                "config": self.config.to_dict(),
                "layouts": [l.to_dict() for l in self.layouts.values()],
                "current_layout_id": self.current_layout.layout_id if self.current_layout else None
            }
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def add_panel(self, panel: Panel) -> None:
        """Add a panel to the dashboard"""
        self.panels[panel.panel_id] = panel
        logger.info(f"Added panel: {panel.title}")
    
    def remove_panel(self, panel_id: str) -> bool:
        """Remove a panel"""
        if panel_id in self.panels:
            del self.panels[panel_id]
            return True
        return False
    
    def get_panel(self, panel_id: str) -> Optional[Panel]:
        """Get a panel by ID"""
        return self.panels.get(panel_id)
    
    def add_widget(
        self,
        panel_id: str,
        widget: Widget
    ) -> bool:
        """Add a widget to a panel"""
        panel = self.panels.get(panel_id)
        if panel:
            panel.add_widget(widget)
            return True
        return False
    
    def register_update_callback(
        self,
        callback: Callable[[str, Any], None]
    ) -> None:
        """Register a callback for data updates"""
        self._update_callbacks.append(callback)
    
    def update_data(
        self,
        source: str,
        data: Any,
        timestamp: datetime = None
    ) -> None:
        """Update data for a source"""
        timestamp = timestamp or datetime.now()
        
        # Cache data
        self._data_cache[source] = {
            "data": data,
            "timestamp": timestamp
        }
        
        # Add to history
        if source not in self._history:
            self._history[source] = []
        
        self._history[source].append({
            "data": data,
            "timestamp": timestamp
        })
        
        # Trim history
        if len(self._history[source]) > self.config.max_history:
            self._history[source] = self._history[source][-self.config.max_history:]
        
        # Notify callbacks
        for callback in self._update_callbacks:
            try:
                callback(source, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_data(
        self,
        source: str,
        history: bool = False
    ) -> Any:
        """Get data for a source"""
        if history:
            return self._history.get(source, [])
        return self._data_cache.get(source, {}).get("data")
    
    def create_layout(
        self,
        name: str,
        panel_ids: List[str],
        monitor_index: int = 0
    ) -> Layout:
        """Create a new layout"""
        layout_id = str(uuid4())
        
        panels = [self.panels[pid] for pid in panel_ids if pid in self.panels]
        
        layout = Layout(
            layout_id=layout_id,
            name=name,
            panels=panels,
            monitor_index=monitor_index
        )
        
        self.layouts[layout_id] = layout
        self._save_config()
        
        return layout
    
    def apply_layout(self, layout_id: str) -> bool:
        """Apply a layout"""
        layout = self.layouts.get(layout_id)
        if layout:
            self.current_layout = layout
            return True
        return False
    
    def set_theme(self, theme: Theme) -> None:
        """Set dashboard theme"""
        self.config.theme = theme
        self._save_config()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current dashboard state"""
        return {
            "config": self.config.to_dict(),
            "panels": {pid: p.to_dict() for pid, p in self.panels.items()},
            "current_layout": self.current_layout.to_dict() if self.current_layout else None,
            "layouts": {lid: l.to_dict() for lid, l in self.layouts.items()},
            "data_sources": list(self._data_cache.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    def export_layout(self, layout_id: str) -> str:
        """Export layout as JSON"""
        layout = self.layouts.get(layout_id)
        if not layout:
            return "{}"
        return json.dumps(layout.to_dict(), indent=2)
    
    def import_layout(self, layout_json: str) -> Layout:
        """Import layout from JSON"""
        data = json.loads(layout_json)
        
        layout = Layout(
            layout_id=data["layout_id"],
            name=data["name"],
            panels=[],  # Panels should be added separately
            grid_columns=data.get("grid_columns", 12),
            grid_row_height=data.get("grid_row_height", 100),
            monitor_index=data.get("monitor_index", 0),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        
        self.layouts[layout.layout_id] = layout
        self._save_config()
        
        return layout


def get_dashboard_html() -> str:
    """Get the main dashboard HTML page"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip Trader Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .title { font-size: 24px; font-weight: bold; color: #00d4ff; }
        .status { padding: 5px 10px; border-radius: 4px; background: #00d4ff; color: #000; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .panel { background: #16213e; border-radius: 8px; padding: 15px; }
        .panel-header { font-size: 14px; color: #00d4ff; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }
        .metric { font-size: 28px; font-weight: bold; margin: 10px 0; }
        .positive { color: #00ff88; }
        .negative { color: #ff4757; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">SmartPip Trader</div>
        <div class="status">Connected</div>
    </div>
    <div class="grid">
        <div class="panel">
            <div class="panel-header">Portfolio Value</div>
            <div class="metric" id="portfolio-value">$10,000.00</div>
        </div>
        <div class="panel">
            <div class="panel-header">Today's P&L</div>
            <div class="metric positive" id="daily-pnl">+$125.50</div>
        </div>
        <div class="panel">
            <div class="panel-header">Win Rate</div>
            <div class="metric" id="win-rate">62.5%</div>
        </div>
        <div class="panel">
            <div class="panel-header">Active Positions</div>
            <div class="metric" id="active-positions">3</div>
        </div>
    </div>
</body>
</html>"""
