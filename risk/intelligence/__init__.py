"""
Institutional Risk Intelligence
===============================

Enterprise-grade risk engine for algorithmic trading systems.

Components:
    - Scenario Analysis & Stress Testing
    - Sensitivity Analysis
    - Rolling Drawdown Analysis
    - Expected Shortfall (CVaR)
    - Capital Allocation Models
    - Adaptive Exposure Limits
    - Confidence-Aware Position Sizing
    - Portfolio Concentration Analysis
    - Recovery Mode
    - Circuit Breakers
    - Automated Kill Switches
    - Risk Score (0-100)
    - Live Dashboard
    - Historical Trend Analysis
"""

__version__ = "1.0.0"

from .core import RiskIntelligenceEngine, RiskLimits, SystemState, RiskMetrics
from .scenarios import ScenarioAnalyzer, StressTestRunner
from .sensitivity import SensitivityAnalyzer
from .drawdown import DrawdownAnalyzer
from .shortfall import ExpectedShortfallCalculator
from .allocation import CapitalAllocator, AllocationMethod
from .exposure import AdaptiveExposureManager
from .position_sizing import ConfidenceAwareSizer
from .concentration import ConcentrationAnalyzer
from .circuit_breaker import CircuitBreaker, KillSwitch
from .recovery import RecoveryManager
from .risk_score import RiskScoreCalculator
from .dashboard import RiskDashboard
from .registry import RiskRegistry

__all__ = [
    "RiskIntelligenceEngine",
    "RiskLimits",
    "SystemState",
    "RiskMetrics",
    "ScenarioAnalyzer",
    "StressTestRunner",
    "SensitivityAnalyzer",
    "DrawdownAnalyzer",
    "ExpectedShortfallCalculator",
    "CapitalAllocator",
    "AllocationMethod",
    "AdaptiveExposureManager",
    "ConfidenceAwareSizer",
    "ConcentrationAnalyzer",
    "CircuitBreaker",
    "KillSwitch",
    "RecoveryManager",
    "RiskScoreCalculator",
    "RiskDashboard",
    "RiskRegistry",
]
