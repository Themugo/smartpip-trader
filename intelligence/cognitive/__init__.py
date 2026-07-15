"""
Cognitive Architecture - AI Decision Platform
============================================

Transforms SmartPip from a signal engine into a cognitive decision platform
with 7 reasoning layers for transparent, traceable trading decisions.

Layers:
    Layer 1 - Perception: Data ingestion and validation
    Layer 2 - Situation Assessment: Regime detection and anomaly identification
    Layer 3 - Memory: Historical situation retrieval
    Layer 4 - Planning: Candidate action generation
    Layer 5 - Critic: Challenge and validation
    Layer 6 - Decision: Action selection
    Layer 7 - Reflection: Post-trade analysis and learning
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

__version__ = "1.0.0"

from .perception import PerceptionLayer, PerceptionResult, DataQuality, DataAnomaly
from .situation import SituationAssessmentLayer, SituationResult, MarketRegime, TrendDirection
from .memory import MemoryLayer, MemoryResult
from .planning import PlanningLayer, PlanningResult, CandidateAction, ActionType, ActionConfidence
from .critic import CriticLayer, CriticResult, CritiqueLevel
from .decision import DecisionLayer, DecisionResult, DecisionStatus, Objective
from .reflection import ReflectionLayer, ReflectionResult, OutcomeType
from .cognitive_orchestrator import CognitiveOrchestrator

__all__ = [
    "CognitiveOrchestrator",
    # Layer 1
    "PerceptionLayer",
    "PerceptionResult",
    "DataQuality",
    "DataAnomaly",
    # Layer 2
    "SituationAssessmentLayer",
    "SituationResult",
    "MarketRegime",
    "TrendDirection",
    # Layer 3
    "MemoryLayer",
    "MemoryResult",
    # Layer 4
    "PlanningLayer",
    "PlanningResult",
    "CandidateAction",
    "ActionType",
    "ActionConfidence",
    # Layer 5
    "CriticLayer",
    "CriticResult",
    "CritiqueLevel",
    # Layer 6
    "DecisionLayer",
    "DecisionResult",
    "DecisionStatus",
    "Objective",
    # Layer 7
    "ReflectionLayer",
    "ReflectionResult",
    "OutcomeType",
]
