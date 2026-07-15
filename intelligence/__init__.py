"""
SmartPip Intelligence Layer — AI-first autonomous trading intelligence.

22-component hierarchical architecture:

Original 10 (core intelligence):
 1. RegimeDetector        — statistical market regime classification
 2. OpportunityScorer     — multi-signal composite execution score
 3. TradeMemory           — feature-store for continual learning
 4. CaseBasedReasoner     — historical similarity retrieval
 5. RLAgent               — reinforcement learning for timing/abstention
 6. RetrainingPipeline    — automated nightly retrain with rollback
 7. ExplainableAI         — per-trade decision explanations
 8. DynamicSizer          — confidence + edge-based position sizing
 9. MetaAI                — analyzer performance evaluator & weight tuner
10. DigitalTwin           — pre-execution scenario simulation

Advanced 12 (research-grade intelligence):
11. MarketDNA             — deep market fingerprinting via clustering & anomaly detection
12. SimilaritySearch      — high-performance historical pattern matching (LSH index)
13. BayesianEngine        — principled uncertainty quantification (Beta-Binomial)
14. EnsembleIntelligence  — advanced multi-model aggregation with dynamic weighting
15. OnlineLearner         — continuous learning with concept drift detection
16. AbstentionModel       — intelligent decision to NOT trade
17. MetaSupervisor        — meta-learning calibration & weight tuning
18. ExplainableEngine     — structured explanations with confidence decomposition
19. BacktestingEngine     — walk-forward validation & Monte Carlo permutation
20. CapitalPreservation   — institutional-grade risk management layer
21. SelfImprovementPipeline — archive, retrain, compare, promote, rollback
22. ResearchOrchestrator  — ties all 12 advanced modules into unified pipeline
"""

# Original 10 components
from .regime_detector import RegimeDetector, MarketRegime
from .opportunity_scorer import OpportunityScorer, OpportunityScore
from .trade_memory import TradeMemory, TradeRecord
from .case_based_reasoner import CaseBasedReasoner, SimilarCase
from .rl_agent import RLAgent, RLAction
from .retraining_pipeline import RetrainingPipeline
from .explainable_ai import ExplainableAI, TradeExplanation
from .dynamic_sizer import DynamicSizer
from .meta_ai import MetaAI
from .digital_twin import DigitalTwin, TwinResult
from .intelligence_orchestrator import IntelligenceOrchestrator

# Advanced 12 components
from .market_dna import MarketDNA, DNAFingerprint, TransitionPrediction, AnomalyReport
from .similarity_search import SimilaritySearch, SearchResult, PatternCluster
from .bayesian_engine import BayesianEngine, PosteriorStats, BayesianVerdict
from .ensemble_intelligence import EnsembleIntelligence, ModelVote, EnsembleVerdict, ModelPerformance
from .online_learner import OnlineLearner, DriftReport, LearningState
from .abstention_model import AbstentionModel, AbstentionSignal, AbstentionVerdict
from .meta_supervisor import MetaSupervisor, CalibrationReport, MetaReport
from .explainable_engine import ExplainableEngine, StructuredExplanation, DecisionStep
from .backtesting_engine import BacktestingEngine, BacktestResult, WalkForwardWindow
from .capital_preservation import CapitalPreservation, RiskState
from .self_improvement import SelfImprovementPipeline, ImprovementAttempt
from .research_orchestrator import ResearchOrchestrator

__all__ = [
    # Original 10
    "RegimeDetector", "MarketRegime",
    "OpportunityScorer", "OpportunityScore",
    "TradeMemory", "TradeRecord",
    "CaseBasedReasoner", "SimilarCase",
    "RLAgent", "RLAction",
    "RetrainingPipeline",
    "ExplainableAI", "TradeExplanation",
    "DynamicSizer",
    "MetaAI",
    "DigitalTwin", "TwinResult",
    "IntelligenceOrchestrator",
    # Advanced 12
    "MarketDNA", "DNAFingerprint", "TransitionPrediction", "AnomalyReport",
    "SimilaritySearch", "SearchResult", "PatternCluster",
    "BayesianEngine", "PosteriorStats", "BayesianVerdict",
    "EnsembleIntelligence", "ModelVote", "EnsembleVerdict", "ModelPerformance",
    "OnlineLearner", "DriftReport", "LearningState",
    "AbstentionModel", "AbstentionSignal", "AbstentionVerdict",
    "MetaSupervisor", "CalibrationReport", "MetaReport",
    "ExplainableEngine", "StructuredExplanation", "DecisionStep",
    "BacktestingEngine", "BacktestResult", "WalkForwardWindow",
    "CapitalPreservation", "RiskState",
    "SelfImprovementPipeline", "ImprovementAttempt",
    "ResearchOrchestrator",
]
