"""
Tests for Decision Intelligence Dashboard
======================================
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from dashboard import (
    # Core
    Dashboard,
    DashboardConfig,
    Panel,
    PanelType,
    Widget,
    WidgetType,
    Theme,
    Layout,
    # Panels
    StrategyHealthPanel,
    ModelHealthPanel,
    PluginHealthPanel,
    ExecutionHealthPanel,
    PortfolioHealthPanel,
    AccountHealthPanel,
    MarketRegimePanel,
    AIConfidencePanel,
    OpportunityScorePanel,
    RiskScorePanel,
    HealthStatus,
    # Analytics
    DrillDownAnalytics,
    DrillDownLevel,
    # Layouts
    LayoutManager,
    LayoutPreset
)


class TestDashboardCore:
    """Tests for dashboard core functionality"""
    
    def test_initialization(self):
        """Test dashboard initialization"""
        config = DashboardConfig(theme=Theme.DARK)
        dashboard = Dashboard(config=config)
        
        assert dashboard.config.theme == Theme.DARK
        assert len(dashboard.panels) == 0
    
    def test_add_panel(self):
        """Test adding panels"""
        dashboard = Dashboard()
        
        panel = Panel(
            panel_id="test_panel",
            panel_type=PanelType.STRATEGY_HEALTH,
            title="Test Panel"
        )
        
        dashboard.add_panel(panel)
        
        assert "test_panel" in dashboard.panels
        assert dashboard.get_panel("test_panel") == panel
    
    def test_add_widget(self):
        """Test adding widgets to panels"""
        dashboard = Dashboard()
        
        panel = Panel(
            panel_id="test_panel",
            panel_type=PanelType.STRATEGY_HEALTH,
            title="Test Panel"
        )
        
        widget = Widget(
            widget_id="test_widget",
            widget_type=WidgetType.GAUGE,
            title="Test Widget",
            data_source="test_source"
        )
        
        dashboard.add_panel(panel)
        result = dashboard.add_widget("test_panel", widget)
        
        assert result is True
        assert len(panel.widgets) == 1
    
    def test_update_data(self):
        """Test data updates"""
        dashboard = Dashboard()
        
        dashboard.update_data("test_source", {"value": 100})
        
        data = dashboard.get_data("test_source")
        assert data == {"value": 100}
    
    def test_theme_setting(self):
        """Test theme changes"""
        dashboard = Dashboard()
        
        dashboard.set_theme(Theme.LIGHT)
        assert dashboard.config.theme == Theme.LIGHT
    
    def test_layout_creation(self):
        """Test layout creation"""
        dashboard = Dashboard()
        
        panel = Panel(
            panel_id="test_panel",
            panel_type=PanelType.STRATEGY_HEALTH,
            title="Test Panel"
        )
        dashboard.add_panel(panel)
        
        layout = dashboard.create_layout(
            name="Test Layout",
            panel_ids=["test_panel"]
        )
        
        assert layout.name == "Test Layout"
        assert "test_panel" in [p.panel_id for p in layout.panels]


class TestHealthPanels:
    """Tests for health panels"""
    
    def test_strategy_health(self):
        """Test strategy health panel"""
        panel = StrategyHealthPanel("test")
        health = panel.get_health()
        
        assert health.status in HealthStatus
        assert 0 <= health.score <= 100
        assert "active_strategies" in health.details
    
    def test_model_health(self):
        """Test model health panel"""
        panel = ModelHealthPanel("test")
        health = panel.get_health()
        
        assert health.status in HealthStatus
        assert "model_accuracy" in health.details
    
    def test_execution_health(self):
        """Test execution health panel"""
        panel = ExecutionHealthPanel("test")
        health = panel.get_health()
        
        assert health.status in HealthStatus
        assert "avg_latency_ms" in health.details
        assert "fill_rate" in health.details
    
    def test_portfolio_health(self):
        """Test portfolio health panel"""
        panel = PortfolioHealthPanel("test")
        health = panel.get_health()
        
        assert health.status in HealthStatus
        assert "daily_return" in health.details
    
    def test_account_health(self):
        """Test account health panel"""
        panel = AccountHealthPanel("test")
        health = panel.get_health()
        
        assert health.status in HealthStatus
        assert "margin_available_pct" in health.details


class TestIntelligencePanels:
    """Tests for intelligence panels"""
    
    def test_market_regime(self):
        """Test market regime panel"""
        panel = MarketRegimePanel("test")
        value = panel.get_value()
        
        assert "current_regime" in value
        assert "confidence" in value
        assert value["confidence"] <= 1.0
    
    def test_ai_confidence(self):
        """Test AI confidence panel"""
        panel = AIConfidencePanel("test")
        value = panel.get_value()
        
        assert "confidence" in value
        assert "calibrated_confidence" in value
    
    def test_opportunity_score(self):
        """Test opportunity score panel"""
        panel = OpportunityScorePanel("test")
        value = panel.get_value()
        
        assert "score" in value
        assert "level" in value
    
    def test_risk_score(self):
        """Test risk score panel"""
        panel = RiskScorePanel("test")
        value = panel.get_value()
        
        assert "risk_score" in value
        assert "var_95" in value


class TestAnalytics:
    """Tests for drill-down analytics"""
    
    def test_strategy_analytics_summary(self):
        """Test strategy analytics at summary level"""
        analytics = DrillDownAnalytics()
        
        view = analytics.get_strategy_analytics(
            "test_strategy",
            DrillDownLevel.SUMMARY
        )
        
        assert view.level == DrillDownLevel.SUMMARY
        assert "sharpe_ratio" in view.data
        assert "trade_count" in view.data
    
    def test_strategy_analytics_detailed(self):
        """Test strategy analytics at detailed level"""
        analytics = DrillDownAnalytics()
        
        view = analytics.get_strategy_analytics(
            "test_strategy",
            DrillDownLevel.DETAILED
        )
        
        assert view.level == DrillDownLevel.DETAILED
        assert "metrics" in view.data
        assert "distributions" in view.data
    
    def test_model_analytics(self):
        """Test model analytics"""
        analytics = DrillDownAnalytics()
        
        view = analytics.get_model_analytics(
            "test_model",
            DrillDownLevel.ANALYTICS
        )
        
        assert view.level == DrillDownLevel.ANALYTICS
        assert "drift_metrics" in view.data
    
    def test_execution_analytics(self):
        """Test execution analytics"""
        analytics = DrillDownAnalytics()
        
        view = analytics.get_execution_analytics(DrillDownLevel.DETAILED)
        
        assert "execution_summary" in view.data
    
    def test_risk_analytics(self):
        """Test risk analytics"""
        analytics = DrillDownAnalytics()
        
        view = analytics.get_risk_analytics(DrillDownLevel.ANALYTICS)
        
        assert "tail_risk" in view.data


class TestLayoutManager:
    """Tests for layout manager"""
    
    def test_initialization(self):
        """Test layout manager initialization"""
        manager = LayoutManager()
        
        assert len(manager.presets) > 0
        assert len(manager.layouts) >= 0
    
    def test_get_preset(self):
        """Test getting preset layouts"""
        manager = LayoutManager()
        
        preset = manager.get_preset(LayoutPreset.TRADING_DESK)
        
        assert preset is not None
        assert preset["name"] == "Trading Desk"
    
    def test_create_layout(self):
        """Test creating custom layout"""
        manager = LayoutManager()
        
        panels = [
            {"id": "panel1", "position": {"x": 0, "y": 0, "w": 4, "h": 3}}
        ]
        
        layout = manager.create_layout("Test Layout", panels)
        
        assert layout["name"] == "Test Layout"
        assert layout["id"] is not None
    
    def test_validate_layout(self):
        """Test layout validation"""
        manager = LayoutManager()
        
        # Valid layout
        valid_layout = {
            "panels": [
                {"id": "panel1", "position": {"x": 0, "y": 0, "w": 4, "h": 3}},
                {"id": "panel2", "position": {"x": 4, "y": 0, "w": 4, "h": 3}}
            ],
            "grid_columns": 12
        }
        
        result = manager.validate_layout(valid_layout)
        assert result["valid"] is True
        
        # Invalid layout with overlap
        invalid_layout = {
            "panels": [
                {"id": "panel1", "position": {"x": 0, "y": 0, "w": 8, "h": 3}},
                {"id": "panel2", "position": {"x": 5, "y": 0, "w": 4, "h": 3}}  # Overlap
            ],
            "grid_columns": 12
        }
        
        result = manager.validate_layout(invalid_layout)
        assert result["valid"] is False
        assert len(result["issues"]) > 0
    
    def test_duplicate_layout(self):
        """Test layout duplication"""
        manager = LayoutManager()
        
        # Create original
        layout = manager.create_layout("Original", [{"id": "p1"}])
        original_id = layout["id"]
        
        # Duplicate
        duplicate = manager.duplicate_layout(original_id, "Duplicate")
        
        assert duplicate["name"] == "Duplicate"
        assert duplicate["id"] != original_id
    
    def test_export_import_layout(self):
        """Test layout export and import"""
        manager = LayoutManager()
        
        # Create layout
        layout = manager.create_layout("Export Test", [{"id": "p1"}])
        layout_id = layout["id"]
        
        # Export
        exported = manager.export_layout(layout_id)
        assert "Export Test" in exported
        
        # Import
        imported = manager.import_layout(exported)
        assert imported["name"] == "Export Test"
        assert imported["id"] != layout_id


class TestWidgets:
    """Tests for widget functionality"""
    
    def test_widget_creation(self):
        """Test widget creation"""
        widget = Widget(
            widget_id="test_widget",
            widget_type=WidgetType.GAUGE,
            title="Test",
            data_source="test"
        )
        
        assert widget.widget_id == "test_widget"
        assert widget.drill_down_enabled is True
    
    def test_widget_serialization(self):
        """Test widget serialization"""
        widget = Widget(
            widget_id="test_widget",
            widget_type=WidgetType.CHART,
            title="Test Chart",
            data_source="test_data"
        )
        
        data = widget.to_dict()
        
        assert data["widget_id"] == "test_widget"
        assert data["widget_type"] == "chart"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
