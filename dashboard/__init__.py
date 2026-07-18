"""
Decision Intelligence Dashboard
===========================

Bloomberg-style dashboard with real-time panels and comprehensive monitoring.
"""

__version__ = "1.0.0"

from .core import (
    Dashboard,
    DashboardConfig,
    Panel,
    PanelType,
    Widget,
    WidgetType,
    Theme,
    Layout,
    get_dashboard_html,
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
