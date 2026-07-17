"""
Research Pipeline
=================

Continuous research and strategy improvement.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HypothesisStatus(Enum):
    """Hypothesis status"""
    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ExperimentStatus(Enum):
    """Experiment status"""
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StrategyStatus(Enum):
    """Strategy status"""
    CANDIDATE = "candidate"
    PAPER_TESTING = "paper_testing"
    PROMOTED = "promoted"
    RETIRED = "retired"
    REJECTED = "rejected"


@dataclass
class Hypothesis:
    """Research hypothesis"""
    id: str
    title: str
    description: str
    status: HypothesisStatus
    created_at: float
    created_by: str
    
    # Evidence
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    
    # Results
    validated: bool = False
    confidence: float = 0
    notes: str = ""


@dataclass
class Experiment:
    """Research experiment"""
    id: str
    hypothesis_id: str
    title: str
    status: ExperimentStatus
    
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    conclusion: str = ""


@dataclass
class StrategyCandidate:
    """Strategy candidate for promotion"""
    id: str
    name: str
    strategy_type: str
    
    status: StrategyStatus
    
    # Metrics
    sharpe_ratio: float = 0
    max_drawdown: float = 0
    win_rate: float = 0
    total_return: float = 0
    trade_count: int = 0
    
    # Validation
    paper_score: float = 0
    validation_count: int = 0
    promoted_at: Optional[float] = None
    retired_at: Optional[float] = None
    
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # History
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "metrics": {
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
                "win_rate": self.win_rate,
                "total_return": self.total_return,
                "trade_count": self.trade_count,
            },
            "paper_score": self.paper_score,
            "validation_count": self.validation_count,
            "created_at": self.created_at,
        }


class ResearchPipeline:
    """
    Continuous research pipeline.
    
    - Generate hypotheses
    - Run experiments
    - Validate candidates
    - Rank strategies
    - Retire weak strategies
    - Promote validated candidates
    """
    
    def __init__(self):
        # Hypotheses
        self._hypotheses: Dict[str, Hypothesis] = {}
        
        # Experiments
        self._experiments: Dict[str, Experiment] = {}
        
        # Strategy candidates
        self._candidates: Dict[str, StrategyCandidate] = {}
        
        # Promotion rules
        self._promotion_thresholds = {
            "min_sharpe_ratio": 1.0,
            "max_drawdown": 0.15,
            "min_win_rate": 0.45,
            "min_paper_score": 0.7,
            "min_validation_count": 3,
        }
        
        # Retire rules
        self._retire_thresholds = {
            "max_drawdown": 0.25,
            "min_trade_count": 50,
        }
    
    # ========== Hypotheses ==========
    
    def create_hypothesis(
        self,
        title: str,
        description: str,
        created_by: str
    ) -> Hypothesis:
        """Create a new hypothesis"""
        hypothesis = Hypothesis(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            status=HypothesisStatus.PROPOSED,
            created_at=time.time(),
            created_by=created_by,
        )
        
        self._hypotheses[hypothesis.id] = hypothesis
        logger.info(f"Hypothesis created: {hypothesis.id}")
        
        return hypothesis
    
    def update_hypothesis(
        self,
        hypothesis_id: str,
        status: Optional[HypothesisStatus] = None,
        validated: Optional[bool] = None,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Update a hypothesis"""
        if hypothesis_id not in self._hypotheses:
            return False
        
        h = self._hypotheses[hypothesis_id]
        
        if status:
            h.status = status
        if validated is not None:
            h.validated = validated
        if confidence is not None:
            h.confidence = confidence
        if notes:
            h.notes = notes
        
        return True
    
    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis"""
        return self._hypotheses.get(hypothesis_id)
    
    def get_hypotheses_by_status(
        self,
        status: HypothesisStatus
    ) -> List[Hypothesis]:
        """Get hypotheses by status"""
        return [h for h in self._hypotheses.values() if h.status == status]
    
    # ========== Experiments ==========
    
    def create_experiment(
        self,
        hypothesis_id: str,
        title: str,
        parameters: Dict[str, Any]
    ) -> Experiment:
        """Create a new experiment"""
        experiment = Experiment(
            id=str(uuid.uuid4())[:8],
            hypothesis_id=hypothesis_id,
            title=title,
            status=ExperimentStatus.PLANNED,
            created_at=time.time(),
            parameters=parameters,
        )
        
        self._experiments[experiment.id] = experiment
        logger.info(f"Experiment created: {experiment.id}")
        
        return experiment
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment"""
        if experiment_id not in self._experiments:
            return False
        
        exp = self._experiments[experiment_id]
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = time.time()
        
        return True
    
    def complete_experiment(
        self,
        experiment_id: str,
        results: Dict[str, Any],
        conclusion: str
    ) -> bool:
        """Complete an experiment"""
        if experiment_id not in self._experiments:
            return False
        
        exp = self._experiments[experiment_id]
        exp.status = ExperimentStatus.COMPLETED
        exp.completed_at = time.time()
        exp.results = results
        exp.conclusion = conclusion
        
        return True
    
    # ========== Strategy Candidates ==========
    
    def register_candidate(
        self,
        name: str,
        strategy_type: str,
        metrics: Dict[str, float]
    ) -> StrategyCandidate:
        """Register a strategy candidate"""
        candidate = StrategyCandidate(
            id=str(uuid.uuid4())[:8],
            name=name,
            strategy_type=strategy_type,
            status=StrategyStatus.CANDIDATE,
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            win_rate=metrics.get("win_rate", 0),
            total_return=metrics.get("total_return", 0),
            trade_count=metrics.get("trade_count", 0),
        )
        
        self._candidates[candidate.id] = candidate
        logger.info(f"Candidate registered: {candidate.id}")
        
        return candidate
    
    def update_candidate_metrics(
        self,
        candidate_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Update candidate metrics"""
        if candidate_id not in self._candidates:
            return False
        
        c = self._candidates[candidate_id]
        
        for key, value in metrics.items():
            if hasattr(c, key):
                setattr(c, key, value)
        
        c.updated_at = time.time()
        
        # Record in history
        c.history.append({
            "timestamp": time.time(),
            "metrics": metrics.copy(),
        })
        
        return True
    
    def validate_candidate(self, candidate_id: str) -> bool:
        """Mark candidate as validated"""
        if candidate_id not in self._candidates:
            return False
        
        c = self._candidates[candidate_id]
        c.validation_count += 1
        c.updated_at = time.time()
        
        return True
    
    def promote_candidate(self, candidate_id: str) -> bool:
        """Promote candidate to paper testing"""
        if candidate_id not in self._candidates:
            return False
        
        c = self._candidates[candidate_id]
        
        # Check promotion rules
        if not self._check_promotion_rules(c):
            logger.warning(f"Candidate {candidate_id} does not meet promotion rules")
            return False
        
        c.status = StrategyStatus.PAPER_TESTING
        c.promoted_at = time.time()
        c.updated_at = time.time()
        
        logger.info(f"Candidate promoted: {candidate_id}")
        return True
    
    def retire_candidate(self, candidate_id: str, reason: str = "") -> bool:
        """Retire a candidate"""
        if candidate_id not in self._candidates:
            return False
        
        c = self._candidates[candidate_id]
        c.status = StrategyStatus.RETIRED
        c.retired_at = time.time()
        c.updated_at = time.time()
        
        c.history.append({
            "timestamp": time.time(),
            "action": "retired",
            "reason": reason,
        })
        
        logger.info(f"Candidate retired: {candidate_id}")
        return True
    
    def _check_promotion_rules(self, candidate: StrategyCandidate) -> bool:
        """Check if candidate meets promotion rules"""
        t = self._promotion_thresholds
        
        return (
            candidate.sharpe_ratio >= t["min_sharpe_ratio"] and
            candidate.max_drawdown <= t["max_drawdown"] and
            candidate.win_rate >= t["min_win_rate"] and
            candidate.paper_score >= t["min_paper_score"] and
            candidate.validation_count >= t["min_validation_count"]
        )
    
    def rank_candidates(self) -> List[StrategyCandidate]:
        """Rank candidates by score"""
        candidates = list(self._candidates.values())
        
        # Calculate composite score
        for c in candidates:
            c.paper_score = (
                c.sharpe_ratio * 0.3 +
                (1 - c.max_drawdown) * 0.2 +
                c.win_rate * 0.2 +
                (c.total_return / 100) * 0.1 +
                (c.validation_count / 10) * 0.2
            )
        
        # Sort by score
        candidates.sort(key=lambda x: x.paper_score, reverse=True)
        
        return candidates
    
    def get_candidate(self, candidate_id: str) -> Optional[StrategyCandidate]:
        """Get a candidate"""
        return self._candidates.get(candidate_id)
    
    def get_candidates_by_status(
        self,
        status: StrategyStatus
    ) -> List[StrategyCandidate]:
        """Get candidates by status"""
        return [c for c in self._candidates.values() if c.status == status]
    
    def check_retirement(self) -> List[StrategyCandidate]:
        """Check for candidates that should be retired"""
        to_retire = []
        t = self._retire_thresholds
        
        for c in self._candidates.values():
            if c.status not in [StrategyStatus.CANDIDATE, StrategyStatus.PAPER_TESTING]:
                continue
            
            if c.max_drawdown > t["max_drawdown"] and c.trade_count >= t["min_trade_count"]:
                to_retire.append(c)
        
        return to_retire
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get pipeline summary"""
        candidates = list(self._candidates.values())
        
        return {
            "total_hypotheses": len(self._hypotheses),
            "active_hypotheses": len(self.get_hypotheses_by_status(HypothesisStatus.IN_PROGRESS)),
            "total_experiments": len(self._experiments),
            "running_experiments": len([e for e in self._experiments.values() if e.status == ExperimentStatus.RUNNING]),
            "total_candidates": len(candidates),
            "candidates_by_status": {
                status.value: len([c for c in candidates if c.status == status])
                for status in StrategyStatus
            },
            "top_candidates": [c.to_dict() for c in self.rank_candidates()[:5]],
            "pending_retirement": len(self.check_retirement()),
        }
