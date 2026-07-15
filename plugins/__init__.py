"""
SmartPip Trader Plugin System

A modular, extensible plugin architecture for trading strategies with:
- Standard lifecycle management
- Isolated execution environment
- Hot-reload capability
- Version management and compatibility checks
"""

from plugins.base import (
    StrategyPlugin,
    PluginMetadata,
    PluginState,
    Signal,
    RiskValidation,
    TickData,
    PerformanceMetrics,
)
from plugins.manager import PluginManager, PluginLoadError, PluginDependencyError
from plugins.marketplace import (
    StrategyMarketplace,
    MarketplaceListing,
    MarketplaceStatus,
    CompatibilityLevel,
)
from plugins.orchestrator import (
    StrategyOrchestrator,
    ConsensusMode,
    ConsensusResult,
    OrchestratorConfig,
)

__all__ = [
    # Base classes
    "StrategyPlugin",
    "PluginMetadata",
    "PluginState",
    "Signal",
    "RiskValidation",
    "TickData",
    "PerformanceMetrics",
    # Manager
    "PluginManager",
    "PluginLoadError",
    "PluginDependencyError",
    # Marketplace
    "StrategyMarketplace",
    "MarketplaceListing",
    "MarketplaceStatus",
    "CompatibilityLevel",
    # Orchestrator
    "StrategyOrchestrator",
    "ConsensusMode",
    "ConsensusResult",
    "OrchestratorConfig",
]
