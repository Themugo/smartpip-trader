"""
SmartPip Trader SDK
==================

Complete SDK ecosystem for the trading platform.

Available SDKs:
- Plugin SDK: Extend the platform with custom plugins
- Strategy SDK: Build and test trading strategies
- AI SDK: Integrate AI/ML models
- Feature SDK: Feature flag management
- Visualization SDK: Dashboard components
- Risk SDK: Risk management tools
- Notification SDK: Alerts and notifications
- Replay SDK: Historical data replay
- Testing SDK: Strategy testing utilities

Developer Tools:
- CLI: Command line interface
- Generators: Project and template generators
- Validators: Plugin and dependency validators
- Tools: Profilers, analyzers, and utilities
"""

__version__ = "1.0.0"
__sdk_version__ = "1.0.0"

# SDK modules
from .base import (
    SmartPipSDK,
    SDKConfig,
    SDKError,
    SDKWarning,
    SDKLogger,
)
from .plugin import (
    Plugin,
    PluginMetadata,
    PluginHook,
    PluginManager,
)
from .strategy import (
    Strategy,
    StrategyContext,
    Signal,
    Position,
)
from .ai import (
    AIModel,
    ModelConfig,
    PredictionResult,
)
from .feature import (
    FeatureClient,
    FeatureContext,
)
from .risk import (
    RiskManager,
    RiskLimits,
)
from .notification import (
    NotificationClient,
    NotificationChannel,
)
from .replay import (
    ReplayEngine,
    ReplayConfig,
)
from .testing import (
    BacktestRunner,
    TestCase,
)

__all__ = [
    # Version
    "__version__",
    "__sdk_version__",
    # Base
    "SmartPipSDK",
    "SDKConfig",
    "SDKError",
    "SDKWarning",
    "SDKLogger",
    # Plugin
    "Plugin",
    "PluginMetadata",
    "PluginHook",
    "PluginManager",
    # Strategy
    "Strategy",
    "StrategyContext",
    "Signal",
    "Position",
    # AI
    "AIModel",
    "ModelConfig",
    "PredictionResult",
    # Feature
    "FeatureClient",
    "FeatureContext",
    # Risk
    "RiskManager",
    "RiskLimits",
    # Notification
    "NotificationClient",
    "NotificationChannel",
    # Replay
    "ReplayEngine",
    "ReplayConfig",
    # Testing
    "BacktestRunner",
    "TestCase",
]
