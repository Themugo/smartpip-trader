"""
Professional Quantitative Testing Framework
=====================================

Institutional-grade backtesting and validation framework.
"""

__version__ = "1.0.0"

from .data_manager import (
    HistoricalDataManager, 
    TickDatasetManager, 
    DatasetVersion,
    DatasetType,
    Tick,
    OHLCV
)
from .validator import (
    WalkForwardValidator,
    RollingWindowValidator,
    OutOfSampleValidator,
    MonteCarloSimulator,
    BootstrapAnalyzer,
    ValidationType,
    ValidationResult,
    WalkForwardResult
)
from .simulations import (
    ExecutionSimulator,
    SlippageSimulator,
    TransactionCostSimulator,
    MarketImpactSimulator,
    SimulationConfig
)
from .analysis import (
    ParameterStabilityAnalyzer,
    SensitivityAnalyzer,
    ConfidenceCalibrator,
    ExpectedValueAnalyzer,
    ProbabilityCalibrator,
    StabilityStatus,
    StabilityResult
)
from .reporter import (
    BacktestReport,
    ReportGenerator,
    ReportFormat,
    EquityCurve,
    DrawdownAnalysis,
    TradeDistribution,
    CalibrationAnalysis
)
from .benchmark import (
    BenchmarkComparator,
    DeploymentGate,
    ComparisonResult,
    ComparisonReport,
    BenchmarkMetrics
)

__all__ = [
    # Data Management
    "HistoricalDataManager",
    "TickDatasetManager",
    "DatasetVersion",
    "DatasetType",
    "Tick",
    "OHLCV",
    # Validation
    "WalkForwardValidator",
    "RollingWindowValidator",
    "OutOfSampleValidator",
    "MonteCarloSimulator",
    "BootstrapAnalyzer",
    "ValidationType",
    "ValidationResult",
    "WalkForwardResult",
    # Simulations
    "ExecutionSimulator",
    "SlippageSimulator",
    "TransactionCostSimulator",
    "MarketImpactSimulator",
    "SimulationConfig",
    # Analysis
    "ParameterStabilityAnalyzer",
    "SensitivityAnalyzer",
    "ConfidenceCalibrator",
    "ExpectedValueAnalyzer",
    "ProbabilityCalibrator",
    "StabilityStatus",
    "StabilityResult",
    # Reporting
    "BacktestReport",
    "ReportGenerator",
    "ReportFormat",
    "EquityCurve",
    "DrawdownAnalysis",
    "TradeDistribution",
    "CalibrationAnalysis",
    # Benchmark
    "BenchmarkComparator",
    "DeploymentGate",
    "ComparisonResult",
    "ComparisonReport",
    "BenchmarkMetrics",
]
