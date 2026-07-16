"""
Decision Science Module
=====================

Separates prediction from decision-making for improved trading outcomes.

Features:
- Prediction Quality assessment
- Decision Quality scoring
- Expected Value calculation
- Capital Efficiency metrics
- Opportunity Cost analysis
- Abstention Quality tracking
- Confidence Calibration
- Regret Score calculation
- Alternative Outcome Analysis
- Wait Analysis (would waiting produce better results?)
- Trade Explanation generation
- Threshold Optimization
"""

__version__ = "1.0.0"

from .core import (
    Prediction,
    Decision,
    Opportunity,
    OpportunityAnalyzer,
    DecisionQualityScore,
    ThresholdOptimizer,
    TradeExplainer,
)
from .metrics import (
    PredictionQuality,
    DecisionQuality,
    ExpectedValue,
    CapitalEfficiency,
    OpportunityCost,
    AbstentionQuality,
    ConfidenceCalibration,
    RegretScore,
    AlternativeOutcome,
    WaitAnalysis,
)

__all__ = [
    "Prediction",
    "Decision",
    "Opportunity",
    "OpportunityAnalyzer",
    "DecisionQualityScore",
    "ThresholdOptimizer",
    "TradeExplainer",
    "PredictionQuality",
    "DecisionQuality",
    "ExpectedValue",
    "CapitalEfficiency",
    "OpportunityCost",
    "AbstentionQuality",
    "ConfidenceCalibration",
    "RegretScore",
    "AlternativeOutcome",
    "WaitAnalysis",
]
