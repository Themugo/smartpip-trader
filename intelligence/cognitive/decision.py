"""
Layer 6 — Decision
===================

Chooses the action that best satisfies configurable objectives such as
expected value, acceptable risk, and confidence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .planning import PlanningResult, CandidateAction, ActionType
from .critic import CriticResult, CritiqueLevel

logger = logging.getLogger(__name__)


class DecisionStatus(Enum):
    """Decision status"""
    DECIDED = "decided"
    ABSTAINED = "abstained"
    INCONCLUSIVE = "inconclusive"
    ERROR = "error"


class Objective(Enum):
    """Decision objectives"""
    MAXIMIZE_EXPECTED_VALUE = "maximize_expected_value"
    MINIMIZE_RISK = "minimize_risk"
    BALANCED = "balanced"
    HIGH_CONFIDENCE_ONLY = "high_confidence_only"


@dataclass
class DecisionWeights:
    """Weights for different decision factors"""
    expected_value: float = 0.4
    risk: float = 0.3
    confidence: float = 0.3
    
    def __post_init__(self):
        # Normalize weights
        total = self.expected_value + self.risk + self.confidence
        if total > 0:
            self.expected_value /= total
            self.risk /= total
            self.confidence /= total
    
    @classmethod
    def from_objective(cls, objective: Objective) -> "DecisionWeights":
        """Get default weights for an objective"""
        weights = {
            Objective.MAXIMIZE_EXPECTED_VALUE: cls(0.6, 0.2, 0.2),
            Objective.MINIMIZE_RISK: cls(0.2, 0.6, 0.2),
            Objective.BALANCED: cls(0.4, 0.3, 0.3),
            Objective.HIGH_CONFIDENCE_ONLY: cls(0.2, 0.2, 0.6)
        }
        return weights.get(objective, cls())


@dataclass
class DecisionResult:
    """Result from decision layer"""
    session_id: str
    timestamp: datetime
    status: DecisionStatus
    selected_action: Optional[CandidateAction]
    alternative_actions: List[CandidateAction]
    objective: Objective
    objective_weights: DecisionWeights
    decision_score: float
    decision_rationale: str
    confidence: float
    risk_assessment: str
    proceed: bool
    abstention_reason: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "selected_action": self.selected_action.to_dict() if self.selected_action else None,
            "alternatives_count": len(self.alternative_actions),
            "objective": self.objective.value,
            "decision_score": self.decision_score,
            "decision_rationale": self.decision_rationale,
            "confidence": self.confidence,
            "risk_assessment": self.risk_assessment,
            "proceed": self.proceed,
            "abstention_reason": self.abstention_reason
        }


class DecisionLayer:
    """
    Layer 6: Decision
    
    Responsible for:
    - Choosing the action that best satisfies objectives
    - Integrating all previous layers' outputs
    - Making final go/no-go decision
    """
    
    def __init__(
        self,
        min_confidence_threshold: float = 0.3,
        min_expected_value_threshold: float = -0.2,
        default_objective: Objective = Objective.BALANCED
    ):
        self.min_confidence_threshold = min_confidence_threshold
        self.min_expected_value_threshold = min_expected_value_threshold
        self.default_objective = default_objective
        
    def process(
        self,
        critic_result: CriticResult,
        planning_result: PlanningResult,
        objective: Optional[Objective] = None
    ) -> DecisionResult:
        """
        Make final decision on action.
        
        Args:
            critic_result: Result from critic layer
            planning_result: Result from planning layer
            objective: Decision objective (uses default if not specified)
            
        Returns:
            DecisionResult with final decision
        """
        objective = objective or self.default_objective
        weights = DecisionWeights.from_objective(objective)
        
        # Handle no action case
        if not critic_result.original_action:
            return self._create_abstention_result(
                session_id=critic_result.session_id,
                reason="No candidate action available",
                planning_result=planning_result,
                objective=objective,
                weights=weights
            )
        
        # Check if abstention was recommended
        if critic_result.abstention_recommended:
            return self._create_abstention_result(
                session_id=critic_result.session_id,
                reason=critic_result.abstention_reason,
                planning_result=planning_result,
                objective=objective,
                weights=weights
            )
        
        # Get action to evaluate (adjusted if available)
        action = critic_result.adjusted_action or critic_result.original_action
        
        # Calculate decision score
        score = self._calculate_decision_score(action, critic_result, weights)
        
        # Check if meets thresholds
        if not self._meets_thresholds(action, score):
            return self._create_abstention_result(
                session_id=critic_result.session_id,
                reason=f"Action does not meet thresholds (score={score:.3f})",
                planning_result=planning_result,
                objective=objective,
                weights=weights
            )
        
        # Select alternatives
        alternatives = self._select_alternatives(
            action, planning_result, weights, max_alternatives=3
        )
        
        # Generate rationale
        rationale = self._generate_rationale(action, score, objective, critic_result)
        
        # Assess risk
        risk_assessment = self._assess_risk(action, critic_result)
        
        # Calculate final confidence
        confidence = self._calculate_final_confidence(action, score, critic_result)
        
        result = DecisionResult(
            session_id=critic_result.session_id,
            timestamp=datetime.now(),
            status=DecisionStatus.DECIDED,
            selected_action=action,
            alternative_actions=alternatives,
            objective=objective,
            objective_weights=weights,
            decision_score=score,
            decision_rationale=rationale,
            confidence=confidence,
            risk_assessment=risk_assessment,
            proceed=True,
            abstention_reason=None,
            metadata={
                "objective": objective.value,
                "raw_score": score,
                "confidence_before_critique": critic_result.original_action.confidence if critic_result.original_action else 0,
                "confidence_after_critique": action.confidence
            }
        )
        
        logger.info(f"Decision: {action.action_type.value} with score={score:.3f}, proceed=True")
        return result
    
    def _calculate_decision_score(
        self,
        action: CandidateAction,
        critic_result: CriticResult,
        weights: DecisionWeights
    ) -> float:
        """Calculate composite decision score"""
        # Expected value component (normalized to 0-1)
        # Map EV from [-1, 1] to [0, 1]
        ev_score = (action.expected_value + 1) / 2
        ev_score = max(0, min(1, ev_score))
        
        # Risk component (lower risk = higher score)
        # Using expected_value_std as risk proxy
        risk_score = 1 - min(1, action.expected_value_std)
        
        # Confidence component
        confidence_score = action.confidence
        
        # Apply weights
        score = (
            weights.expected_value * ev_score +
            weights.risk * risk_score +
            weights.confidence * confidence_score
        )
        
        # Penalize for critique severity
        severity_penalties = {
            CritiqueLevel.BLOCK: 0.0,
            CritiqueLevel.SEVERE: 0.3,
            CritiqueLevel.MODERATE: 0.15,
            CritiqueLevel.MINOR: 0.05,
            CritiqueLevel.NONE: 0.0
        }
        
        penalty = severity_penalties.get(critic_result.overall_severity, 0)
        score *= (1 - penalty)
        
        return max(0, min(1, score))
    
    def _meets_thresholds(
        self,
        action: CandidateAction,
        score: float
    ) -> bool:
        """Check if action meets minimum thresholds"""
        # Confidence threshold
        if action.confidence < self.min_confidence_threshold:
            return False
        
        # Expected value threshold
        if action.expected_value < self.min_expected_value_threshold:
            return False
        
        # Score threshold
        if score < 0.3:
            return False
        
        return True
    
    def _select_alternatives(
        self,
        selected: CandidateAction,
        planning_result: PlanningResult,
        weights: DecisionWeights,
        max_alternatives: int = 3
    ) -> List[CandidateAction]:
        """Select alternative actions"""
        all_actions = planning_result.candidate_actions
        
        # Filter out the selected action and NO_ACTION/WAIT
        candidates = [
            a for a in all_actions
            if a.action_type != selected.action_type and
            a.action_type not in [ActionType.NO_ACTION, ActionType.WAIT]
        ]
        
        # Score and rank alternatives
        scored = []
        for action in candidates:
            score = (
                weights.expected_value * max(0, action.expected_value) +
                weights.risk * (1 - action.expected_value_std) +
                weights.confidence * action.confidence
            )
            scored.append((action, score))
        
        # Sort by score and take top alternatives
        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, _ in scored[:max_alternatives]]
    
    def _generate_rationale(
        self,
        action: CandidateAction,
        score: float,
        objective: Objective,
        critic_result: CriticResult
    ) -> str:
        """Generate natural language rationale for decision"""
        parts = []
        
        # Decision type
        if action.action_type == ActionType.TRADE_CALL or action.action_type == ActionType.TRADE_PUT:
            parts.append(f"Selected {action.direction} trade")
        else:
            parts.append(f"Selected {action.action_type.value.replace('_', ' ')}")
        
        # Objective alignment
        if objective == Objective.MAXIMIZE_EXPECTED_VALUE:
            parts.append(f"optimizing for expected value ({action.expected_value:.3f})")
        elif objective == Objective.MINIMIZE_RISK:
            parts.append(f"minimizing risk (std={action.expected_value_std:.3f})")
        elif objective == Objective.HIGH_CONFIDENCE_ONLY:
            parts.append(f"requiring high confidence ({action.confidence:.0%})")
        else:
            parts.append("balancing expected value, risk, and confidence")
        
        # Confidence
        parts.append(f"with {action.confidence:.0%} confidence")
        
        # Duration
        if action.duration_seconds > 0:
            parts.append(f"duration {action.duration_seconds}s")
        
        # Critique summary
        if critic_result.critiques:
            severe = sum(1 for c in critic_result.critiques if c.severity == CritiqueLevel.SEVERE)
            moderate = sum(1 for c in critic_result.critiques if c.severity == CritiqueLevel.MODERATE)
            
            if severe > 0:
                parts.append(f"({severe} severe, {moderate} moderate concerns addressed)")
            elif moderate > 0:
                parts.append(f"({moderate} moderate concerns addressed)")
        
        # Overall score
        parts.append(f"[score={score:.3f}]")
        
        return " ".join(parts)
    
    def _assess_risk(
        self,
        action: CandidateAction,
        critic_result: CriticResult
    ) -> str:
        """Assess and describe risk level"""
        risk_level = "LOW"
        risk_factors = []
        
        # Base risk from EV std
        if action.expected_value_std > 0.5:
            risk_level = "MEDIUM"
            risk_factors.append("high variance in outcomes")
        elif action.expected_value_std > 0.8:
            risk_level = "HIGH"
            risk_factors.append("very high variance in outcomes")
        
        # Risk from critiques
        severe_count = sum(
            1 for c in critic_result.critiques
            if c.severity in [CritiqueLevel.SEVERE, CritiqueLevel.BLOCK]
        )
        
        if severe_count >= 2:
            risk_level = "HIGH"
            risk_factors.append(f"{severe_count} severe concerns")
        elif severe_count == 1:
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            risk_factors.append("1 severe concern")
        
        # Risk from confidence
        if action.confidence < 0.4:
            risk_factors.append("low decision confidence")
        
        # Build risk string
        if risk_factors:
            return f"{risk_level}: {', '.join(risk_factors)}"
        return f"{risk_level}: No significant risk factors"
    
    def _calculate_final_confidence(
        self,
        action: CandidateAction,
        score: float,
        critic_result: CriticResult
    ) -> float:
        """Calculate final decision confidence"""
        # Combine action confidence with critique confidence
        confidence = (action.confidence * 0.7 + critic_result.confidence * 0.3)
        
        # Reduce for severe critiques
        severe_count = sum(
            1 for c in critic_result.critiques
            if c.severity in [CritiqueLevel.SEVERE, CritiqueLevel.BLOCK]
        )
        confidence *= (1 - severe_count * 0.1)
        
        return max(0, min(1, confidence))
    
    def _create_abstention_result(
        self,
        session_id: str,
        reason: str,
        planning_result: PlanningResult,
        objective: Objective,
        weights: DecisionWeights
    ) -> DecisionResult:
        """Create result for abstention decision"""
        return DecisionResult(
            session_id=session_id,
            timestamp=datetime.now(),
            status=DecisionStatus.ABSTAINED,
            selected_action=None,
            alternative_actions=[],
            objective=objective,
            objective_weights=weights,
            decision_score=0.0,
            decision_rationale=f"Abstained: {reason}",
            confidence=0.0,
            risk_assessment="N/A - no action taken",
            proceed=False,
            abstention_reason=reason,
            metadata={
                "objective": objective.value,
                "abstention": True
            }
        )
    
    def evaluate_multiple_objectives(
        self,
        critic_result: CriticResult,
        planning_result: PlanningResult
    ) -> Dict[Objective, DecisionResult]:
        """Evaluate decision under multiple objectives"""
        results = {}
        
        for objective in Objective:
            result = self.process(critic_result, planning_result, objective)
            results[objective] = result
        
        return results
    
    def get_best_objective_for_situation(
        self,
        critic_result: CriticResult,
        planning_result: PlanningResult,
        situation_uncertainty: float,
        situation_volatility: float
    ) -> Objective:
        """Recommend best objective given situation parameters"""
        # High uncertainty -> prioritize risk minimization
        if situation_uncertainty > 0.6:
            return Objective.MINIMIZE_RISK
        
        # High volatility -> prioritize risk minimization
        if situation_volatility > 0.7:
            return Objective.MINIMIZE_RISK
        
        # Low uncertainty, good conditions -> maximize expected value
        if situation_uncertainty < 0.3 and situation_volatility < 0.4:
            return Objective.MAXIMIZE_EXPECTED_VALUE
        
        # Default to balanced
        return Objective.BALANCED
    
    def reset(self) -> None:
        """Reset decision layer state"""
        logger.info("Decision layer reset")
