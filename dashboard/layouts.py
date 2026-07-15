"""
Layout Manager
============

Manages dashboard layouts for multi-monitor configurations.
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


class LayoutPreset(Enum):
    """Predefined layout presets"""
    TRADING_DESK = "trading_desk"  # Full monitoring
    TRADING_PANEL = "trading_panel"  # Primary trading
    ANALYSIS = "analysis"  # Research focused
    EXECUTION = "execution"  # Execution monitoring
    MOBILE = "mobile"  # Compact mobile view
    CUSTOM = "custom"


@dataclass
class GridPosition:
    """Position in grid layout"""
    x: int
    y: int
    width: int
    height: int
    
    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.width, "h": self.height}


class LayoutManager:
    """
    Manages dashboard layouts including presets and multi-monitor support.
    """
    
    def __init__(
        self,
        db_path: str = "data/dashboard/layouts.json",
        grid_columns: int = 12,
        grid_row_height: int = 100
    ):
        self.db_path = db_path
        self.grid_columns = grid_columns
        self.grid_row_height = grid_row_height
        
        self.layouts: Dict[str, Dict[str, Any]] = {}
        self.presets: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_presets()
        self._load_layouts()
    
    def _initialize_presets(self) -> None:
        """Initialize predefined layout presets"""
        self.presets = {
            LayoutPreset.TRADING_DESK.value: {
                "name": "Trading Desk",
                "description": "Full monitoring with all panels",
                "grid_columns": 12,
                "grid_row_height": 100,
                "monitor_count": 2,
                "panels": [
                    # Monitor 1 - Health & Intelligence
                    {"id": "strategy_health", "position": GridPosition(0, 0, 4, 3).to_dict()},
                    {"id": "model_health", "position": GridPosition(4, 0, 4, 3).to_dict()},
                    {"id": "execution_health", "position": GridPosition(8, 0, 4, 3).to_dict()},
                    {"id": "market_regime", "position": GridPosition(0, 3, 3, 2).to_dict()},
                    {"id": "ai_confidence", "position": GridPosition(3, 3, 3, 2).to_dict()},
                    {"id": "opportunity_score", "position": GridPosition(6, 3, 3, 2).to_dict()},
                    {"id": "risk_score", "position": GridPosition(9, 3, 3, 2).to_dict()},
                    # Monitor 2 - Operations
                    {"id": "trade_queue", "position": GridPosition(0, 0, 6, 4).to_dict()},
                    {"id": "pending_decisions", "position": GridPosition(6, 0, 6, 4).to_dict()},
                    {"id": "ai_thoughts", "position": GridPosition(0, 4, 6, 3).to_dict()},
                    {"id": "system_monitor", "position": GridPosition(6, 4, 6, 3).to_dict()},
                ]
            },
            LayoutPreset.TRADING_PANEL.value: {
                "name": "Trading Panel",
                "description": "Primary trading focus",
                "grid_columns": 12,
                "grid_row_height": 80,
                "monitor_count": 1,
                "panels": [
                    {"id": "strategy_health", "position": GridPosition(0, 0, 4, 2).to_dict()},
                    {"id": "ai_confidence", "position": GridPosition(4, 0, 4, 2).to_dict()},
                    {"id": "risk_score", "position": GridPosition(8, 0, 4, 2).to_dict()},
                    {"id": "opportunity_score", "position": GridPosition(0, 2, 4, 2).to_dict()},
                    {"id": "execution_health", "position": GridPosition(4, 2, 4, 2).to_dict()},
                    {"id": "market_regime", "position": GridPosition(8, 2, 4, 2).to_dict()},
                    {"id": "trade_queue", "position": GridPosition(0, 4, 8, 3).to_dict()},
                    {"id": "ai_thoughts", "position": GridPosition(0, 7, 8, 2).to_dict()},
                    {"id": "system_monitor", "position": GridPosition(8, 4, 4, 5).to_dict()},
                ]
            },
            LayoutPreset.ANALYSIS.value: {
                "name": "Analysis",
                "description": "Research and analysis focus",
                "grid_columns": 12,
                "grid_row_height": 80,
                "monitor_count": 2,
                "panels": [
                    # Monitor 1 - Research
                    {"id": "market_regime", "position": GridPosition(0, 0, 6, 3).to_dict()},
                    {"id": "historical_similarity", "position": GridPosition(6, 0, 6, 3).to_dict()},
                    {"id": "expected_value", "position": GridPosition(0, 3, 4, 2).to_dict()},
                    {"id": "trade_accuracy", "position": GridPosition(4, 3, 4, 2).to_dict()},
                    {"id": "drawdown", "position": GridPosition(8, 3, 4, 2).to_dict()},
                    {"id": "capital_allocation", "position": GridPosition(0, 5, 12, 2).to_dict()},
                    # Monitor 2 - Models
                    {"id": "model_health", "position": GridPosition(0, 0, 6, 3).to_dict()},
                    {"id": "analyzer_agreement", "position": GridPosition(6, 0, 6, 3).to_dict()},
                    {"id": "ai_thoughts", "position": GridPosition(0, 3, 12, 4).to_dict()},
                ]
            },
            LayoutPreset.EXECUTION.value: {
                "name": "Execution",
                "description": "Execution monitoring focus",
                "grid_columns": 12,
                "grid_row_height": 80,
                "monitor_count": 1,
                "panels": [
                    {"id": "execution_health", "position": GridPosition(0, 0, 6, 3).to_dict()},
                    {"id": "portfolio_health", "position": GridPosition(6, 0, 6, 3).to_dict()},
                    {"id": "account_health", "position": GridPosition(0, 3, 4, 2).to_dict()},
                    {"id": "plugin_health", "position": GridPosition(4, 3, 4, 2).to_dict()},
                    {"id": "strategy_health", "position": GridPosition(8, 3, 4, 2).to_dict()},
                    {"id": "trade_queue", "position": GridPosition(0, 5, 8, 4).to_dict()},
                    {"id": "pending_decisions", "position": GridPosition(8, 5, 4, 4).to_dict()},
                ]
            },
            LayoutPreset.MOBILE.value: {
                "name": "Mobile",
                "description": "Compact mobile view",
                "grid_columns": 4,
                "grid_row_height": 60,
                "monitor_count": 1,
                "panels": [
                    {"id": "strategy_health", "position": GridPosition(0, 0, 2, 1).to_dict()},
                    {"id": "ai_confidence", "position": GridPosition(2, 0, 2, 1).to_dict()},
                    {"id": "opportunity_score", "position": GridPosition(0, 1, 2, 1).to_dict()},
                    {"id": "risk_score", "position": GridPosition(2, 1, 2, 1).to_dict()},
                    {"id": "trade_queue", "position": GridPosition(0, 2, 4, 3).to_dict()},
                    {"id": "system_monitor", "position": GridPosition(0, 5, 4, 1).to_dict()},
                ]
            }
        }
    
    def _load_layouts(self) -> None:
        """Load saved layouts from file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    self.layouts = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load layouts: {e}")
    
    def _save_layouts(self) -> None:
        """Save layouts to file"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump(self.layouts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save layouts: {e}")
    
    def get_preset(self, preset: LayoutPreset) -> Optional[Dict[str, Any]]:
        """Get a preset layout"""
        return self.presets.get(preset.value)
    
    def get_all_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get all available presets"""
        return self.presets.copy()
    
    def create_layout(
        self,
        name: str,
        panels: List[Dict[str, Any]],
        monitor_count: int = 1,
        grid_columns: int = 12
    ) -> Dict[str, Any]:
        """Create a new custom layout"""
        layout_id = str(uuid4())
        
        layout = {
            "id": layout_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "grid_columns": grid_columns,
            "grid_row_height": self.grid_row_height,
            "monitor_count": monitor_count,
            "panels": panels
        }
        
        self.layouts[layout_id] = layout
        self._save_layouts()
        
        return layout
    
    def update_layout(
        self,
        layout_id: str,
        panels: List[Dict[str, Any]]
    ) -> bool:
        """Update an existing layout"""
        if layout_id not in self.layouts:
            return False
        
        self.layouts[layout_id]["panels"] = panels
        self.layouts[layout_id]["updated_at"] = datetime.now().isoformat()
        self._save_layouts()
        
        return True
    
    def delete_layout(self, layout_id: str) -> bool:
        """Delete a layout"""
        if layout_id in self.layouts:
            del self.layouts[layout_id]
            self._save_layouts()
            return True
        return False
    
    def get_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific layout"""
        return self.layouts.get(layout_id)
    
    def get_all_layouts(self) -> Dict[str, Dict[str, Any]]:
        """Get all saved layouts"""
        return self.layouts.copy()
    
    def get_layouts_by_monitor(self, monitor_index: int) -> List[Dict[str, Any]]:
        """Get layouts for a specific monitor"""
        results = []
        
        for layout in self.layouts.values():
            monitor_panels = [
                p for p in layout.get("panels", [])
                if p.get("monitor", 0) == monitor_index
            ]
            if monitor_panels:
                results.append({
                    "id": layout["id"],
                    "name": layout["name"],
                    "panels": monitor_panels
                })
        
        return results
    
    def validate_layout(self, layout: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a layout for conflicts and overlaps"""
        issues = []
        warnings = []
        
        panels = layout.get("panels", [])
        grid_columns = layout.get("grid_columns", 12)
        
        # Check for overlaps
        positions = []
        for panel in panels:
            pos = panel.get("position", {})
            positions.append({
                "id": panel.get("id"),
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "width": pos.get("w", 4),
                "height": pos.get("h", 3)
            })
        
        for i, p1 in enumerate(positions):
            for p2 in positions[i+1:]:
                # Check overlap
                if (p1["x"] < p2["x"] + p2["width"] and
                    p1["x"] + p1["width"] > p2["x"] and
                    p1["y"] < p2["y"] + p2["height"] and
                    p1["y"] + p1["height"] > p2["y"]):
                    issues.append(f"Panel overlap: {p1['id']} and {p2['id']}")
        
        # Check bounds
        for panel in positions:
            if panel["x"] + panel["width"] > grid_columns:
                warnings.append(f"Panel {panel['id']} exceeds grid width")
            if panel["x"] < 0 or panel["y"] < 0:
                issues.append(f"Panel {panel['id']} has negative position")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    def duplicate_layout(
        self,
        layout_id: str,
        new_name: str
    ) -> Optional[Dict[str, Any]]:
        """Duplicate an existing layout"""
        original = self.layouts.get(layout_id)
        if not original:
            return None
        
        new_layout = original.copy()
        new_layout["id"] = str(uuid4())
        new_layout["name"] = new_name
        new_layout["created_at"] = datetime.now().isoformat()
        new_layout["duplicated_from"] = layout_id
        
        self.layouts[new_layout["id"]] = new_layout
        self._save_layouts()
        
        return new_layout
    
    def export_layout(self, layout_id: str) -> str:
        """Export layout as JSON string"""
        layout = self.layouts.get(layout_id)
        if not layout:
            return "{}"
        return json.dumps(layout, indent=2)
    
    def import_layout(self, layout_json: str) -> Dict[str, Any]:
        """Import layout from JSON string"""
        try:
            layout = json.loads(layout_json)
            layout["id"] = str(uuid4())  # Generate new ID
            layout["imported_at"] = datetime.now().isoformat()
            
            self.layouts[layout["id"]] = layout
            self._save_layouts()
            
            return layout
        except Exception as e:
            logger.error(f"Failed to import layout: {e}")
            raise
