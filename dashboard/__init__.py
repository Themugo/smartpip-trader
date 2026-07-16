"""
Decision Intelligence Dashboard
===========================

Bloomberg-style dashboard with real-time panels and comprehensive monitoring.
"""

__version__ = "1.0.0"

import os

def get_dashboard_html() -> str:
    """Load and return the dashboard HTML from web/index.html."""
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
    index_path = os.path.join(web_dir, 'index.html')
    with open(index_path, 'r', encoding='utf-8') as f:
        return f.read()

from .core import (
    Dashboard,
    DashboardConfig,
    Panel,
    PanelType,
    Widget,
    WidgetType,
    Theme,
    Layout
)
from .panels import (
    # Health
    HealthStatus,
    HealthMetrics,
    HealthPanel,
    StrategyHealthPanel,
    ModelHealthPanel,
    PluginHealthPanel,
    ExecutionHealthPanel,
    PortfolioHealthPanel,
    AccountHealthPanel,
    # Intelligence Panels
    MarketRegimePanel,
    AIConfidencePanel,
    OpportunityScorePanel,
    RiskScorePanel,
    AIThoughtsPanel,
    AnalyzerAgreementPanel,
    HistoricalSimilarityPanel,
    ExpectedValuePanel,
    TradeAccuracyPanel,
    DrawdownPanel,
    CapitalAllocationPanel,
    # Queue Panels
    TradeQueuePanel,
    PendingDecisionsPanel,
    OpportunityTrackerPanel,
    # System Panels
    SystemMonitorPanel,
    ServiceStatusPanel
)
from .analytics import DrillDownAnalytics, DrillDownLevel, DrillDownView
from .layouts import LayoutManager, LayoutPreset, GridPosition

__all__ = [
    # Dashboard HTML
    "get_dashboard_html",
    # Core
    "Dashboard",
    "DashboardConfig",
    "Panel",
    "PanelType",
    "Widget",
    "WidgetType",
    "Theme",
    "Layout",
    # Health
    "HealthStatus",
    "HealthMetrics",
    "HealthPanel",
    "StrategyHealthPanel",
    "ModelHealthPanel",
    "PluginHealthPanel",
    "ExecutionHealthPanel",
    "PortfolioHealthPanel",
    "AccountHealthPanel",
    # Intelligence Panels
    "MarketRegimePanel",
    "AIConfidencePanel",
    "OpportunityScorePanel",
    "RiskScorePanel",
    "AIThoughtsPanel",
    "AnalyzerAgreementPanel",
    "HistoricalSimilarityPanel",
    "ExpectedValuePanel",
    "TradeAccuracyPanel",
    "DrawdownPanel",
    "CapitalAllocationPanel",
    # Queue Panels
    "TradeQueuePanel",
    "PendingDecisionsPanel",
    "OpportunityTrackerPanel",
    # System Panels
    "SystemMonitorPanel",
    "ServiceStatusPanel",
    # Analytics
    "DrillDownAnalytics",
    "DrillDownLevel",
    "DrillDownView",
    # Layouts
    "LayoutManager",
    "LayoutPreset",
    "GridPosition",
]
