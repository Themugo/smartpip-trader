"""
Workspace Templates - Pre-configured Workspace Layouts

Provides factory templates for common workspace configurations:
- AI Trading Workspace
- Research Workspace
- Backtesting Workspace
- Live Execution Workspace
- Risk Management Workspace
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from workspace.manager import (
    LayoutType,
    PanelState,
    PanelType,
    PanelPosition,
    ChartLayout,
    WorkspaceLayout,
)


@dataclass
class WorkspaceTemplate:
    """Workspace template definition"""
    name: str
    description: str
    panels: List[PanelState] = field(default_factory=list)
    charts: List[ChartLayout] = field(default_factory=list)
    enabled_strategies: List[str] = field(default_factory=list)
    watchlists: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    theme: str = "dark"
    
    def create_workspace(self, workspace_id: str) -> WorkspaceLayout:
        """Create a workspace from this template"""
        return WorkspaceLayout(
            id=workspace_id,
            name=self.name,
            description=self.description,
            panels=[PanelState.from_dict(p.to_dict()) for p in self.panels],
            charts=[ChartLayout(**c.to_dict()) for c in self.charts],
            enabled_strategies=self.enabled_strategies.copy(),
            watchlists=self.watchlists.copy(),
            filters=self.filters.copy(),
            theme=self.theme,
            is_template=True,
        )


# AI Trading Workspace Template
AI_TRADING_WORKSPACE = WorkspaceTemplate(
    name="AI Trading Workspace",
    description="Comprehensive AI-powered trading interface",
    panels=[
        PanelState(
            id="ai-chart",
            panel_type=PanelType.CHART,
            title="Trading Chart",
            position=PanelPosition(x=0, y=0, width=60, height=60),
            layout=LayoutType.GRID,
        ),
        PanelState(
            id="ai-signals",
            panel_type=PanelType.AI_SIGNALS,
            title="AI Signals",
            position=PanelPosition(x=60, y=0, width=40, height=30),
        ),
        PanelState(
            id="confidence",
            panel_type=PanelType.CONFIDENCE,
            title="Confidence Meter",
            position=PanelPosition(x=60, y=30, width=40, height=30),
        ),
        PanelState(
            id="analyzer-output",
            panel_type=PanelType.ANALYZER_OUTPUT,
            title="Analyzer Output",
            position=PanelPosition(x=0, y=60, width=50, height=40),
        ),
        PanelState(
            id="positions",
            panel_type=PanelType.POSITIONS,
            title="Open Positions",
            position=PanelPosition(x=50, y=60, width=25, height=40),
        ),
        PanelState(
            id="alerts",
            panel_type=PanelType.ALERTS,
            title="Active Alerts",
            position=PanelPosition(x=75, y=60, width=25, height=40),
        ),
    ],
    charts=[
        ChartLayout(id="main-chart", symbol="R_100", timeframe="1m"),
    ],
    enabled_strategies=["unified"],
    filters={"min_confidence": 75},
    theme="dark",
)

# Research Workspace Template
RESEARCH_WORKSPACE = WorkspaceTemplate(
    name="Research Workspace",
    description="Strategy research and experimentation",
    panels=[
        PanelState(
            id="research-chart",
            panel_type=PanelType.CHART,
            title="Analysis Chart",
            position=PanelPosition(x=0, y=0, width=50, height=50),
        ),
        PanelState(
            id="experiments",
            panel_type=PanelType.EXPERIMENT_TRACKER,
            title="Experiments",
            position=PanelPosition(x=50, y=0, width=50, height=50),
        ),
        PanelState(
            id="feature-analysis",
            panel_type=PanelType.FEATURE_ANALYSIS,
            title="Feature Analysis",
            position=PanelPosition(x=0, y=50, width=50, height=50),
        ),
        PanelState(
            id="backtest-results",
            panel_type=PanelType.BACKTEST_RESULTS,
            title="Backtest Results",
            position=PanelPosition(x=50, y=50, width=50, height=50),
        ),
    ],
    charts=[
        ChartLayout(id="research-chart", symbol="R_100", timeframe="5m"),
    ],
    theme="dark",
)

# Backtesting Workspace Template
BACKTESTING_WORKSPACE = WorkspaceTemplate(
    name="Backtesting Workspace",
    description="Strategy backtesting and optimization",
    panels=[
        PanelState(
            id="bt-chart",
            panel_type=PanelType.CHART,
            title="Backtest Chart",
            position=PanelPosition(x=0, y=0, width=60, height=50),
        ),
        PanelState(
            id="bt-results",
            panel_type=PanelType.BACKTEST_RESULTS,
            title="Results",
            position=PanelPosition(x=60, y=0, width=40, height=50),
        ),
        PanelState(
            id="compare",
            panel_type=PanelType.STRATEGY_COMPARE,
            title="Strategy Comparison",
            position=PanelPosition(x=0, y=50, width=100, height=50),
        ),
    ],
    charts=[
        ChartLayout(id="bt-chart", symbol="R_100", timeframe="1m"),
    ],
    theme="dark",
)

# Live Execution Workspace Template
LIVE_EXECUTION_WORKSPACE = WorkspaceTemplate(
    name="Live Execution Workspace",
    description="Active trading with minimal distractions",
    panels=[
        PanelState(
            id="live-chart",
            panel_type=PanelType.CHART,
            title="Live Chart",
            position=PanelPosition(x=0, y=0, width=100, height=50),
        ),
        PanelState(
            id="trade-panel",
            panel_type=PanelType.TRADE_PANEL,
            title="Quick Trade",
            position=PanelPosition(x=0, y=50, width=33, height=50),
        ),
        PanelState(
            id="live-positions",
            panel_type=PanelType.POSITIONS,
            title="Positions",
            position=PanelPosition(x=33, y=50, width=34, height=50),
        ),
        PanelState(
            id="live-orders",
            panel_type=PanelType.ORDERS,
            title="Orders",
            position=PanelPosition(x=67, y=50, width=33, height=50),
        ),
    ],
    charts=[
        ChartLayout(id="live-chart", symbol="R_100", timeframe="1m"),
    ],
    enabled_strategies=["unified"],
    theme="dark",
)

# Risk Management Workspace Template
RISK_MANAGEMENT_WORKSPACE = WorkspaceTemplate(
    name="Risk Management Workspace",
    description="Comprehensive risk monitoring and control",
    panels=[
        PanelState(
            id="risk-dashboard",
            panel_type=PanelType.RISK_DASHBOARD,
            title="Risk Dashboard",
            position=PanelPosition(x=0, y=0, width=50, height=33),
        ),
        PanelState(
            id="exposure",
            panel_type=PanelType.EXPOSURE,
            title="Exposure",
            position=PanelPosition(x=50, y=0, width=50, height=33),
        ),
        PanelState(
            id="drawdown",
            panel_type=PanelType.DRAWDOWN,
            title="Drawdown Monitor",
            position=PanelPosition(x=0, y=33, width=33, height=34),
        ),
        PanelState(
            id="trade-history",
            panel_type=PanelType.TRADE_HISTORY,
            title="Trade History",
            position=PanelPosition(x=33, y=33, width=34, height=34),
        ),
        PanelState(
            id="risk-alerts",
            panel_type=PanelType.ALERTS,
            title="Risk Alerts",
            position=PanelPosition(x=67, y=33, width=33, height=34),
        ),
        PanelState(
            id="event-timeline",
            panel_type=PanelType.EVENT_TIMELINE,
            title="Event Timeline",
            position=PanelPosition(x=0, y=67, width=100, height=33),
        ),
    ],
    charts=[
        ChartLayout(id="risk-chart", symbol="R_100", timeframe="5m"),
    ],
    theme="dark",
)

# All Templates
TEMPLATES = {
    "ai_trading": AI_TRADING_WORKSPACE,
    "research": RESEARCH_WORKSPACE,
    "backtesting": BACKTESTING_WORKSPACE,
    "live_execution": LIVE_EXECUTION_WORKSPACE,
    "risk_management": RISK_MANAGEMENT_WORKSPACE,
}

# Import LayoutType
from workspace.manager import LayoutType
