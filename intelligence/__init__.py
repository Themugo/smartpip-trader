"""
SmartPip Intelligence Layer — AI-first autonomous trading intelligence.

10-component hierarchical architecture:
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
"""

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

__all__ = [
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
]
