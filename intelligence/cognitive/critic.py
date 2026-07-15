"""
Layer 5 — Critic
=================

Independently challenges proposed actions, identifies weak evidence,
flags overconfidence, and recommends abstention when appropriate.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .perception import PerceptionResult, DataQuality
from .situation import SituationResult, MarketRegime
from .memory import MemoryResult
from .planning import PlanningResult, CandidateAction, ActionType, ActionConfidence

logger = logging.getLogger(__name__)


class CritiqueLevel(Enum):
    """Level of critique severity"""
    NONE = "none"
    MINOR = "minor"  # Suggestions for improvement
    MODERATE = "moderate"  # Significant concerns
    SEVERE = "severe"  # Action should not proceed
    BLOCK = "block"  # Action is blocked


@dataclass
class CritiqueItem:
    """A single critique of an action"""
    category: str
    severity: CritiqueLevel
    description: str
    evidence: List[str]  # Supporting evidence
    recommendation: str  # How to address
    confidence_in_critique: float  # How confident we are in this critique
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "confidence": self.confidence_in_critique
        }


@dataclass
class CriticResult:
    """Result from critic layer"""
    session_id: str
    timestamp: datetime
    original_action: CandidateAction
    critiques: List[CritiqueItem]
    overall_severity: CritiqueLevel
    should_proceed: bool
    confidence_adjustment: float  # How much to adjust confidence
    adjusted_action: Optional[CandidateAction]  # Action with adjustments
    abstention_recommended: bool
    abstention_reason: Optional[str]
    overconfidence_flags: List[str]
    weak_evidence_flags: List[str]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "original_action": self.original_action.to_dict(),
            "critique_count": len(self.critiques),
            "overall_severity": self.overall_severity.value,
            "should_proceed": self.should_proceed,
            "confidence_adjustment": self.confidence_adjustment,
            "abstention_recommended": self.abstention_recommended,
            "abstention_reason": self.abstention_reason,
            "overconfidence_flags": self.overconfidence_flags,
            "weak_evidence_flags": self.weak_evidence_flags,
            "confidence": self.confidence
        }


class CriticLayer:
    """
    Layer 5: Critic
    
    Responsible for:
    - Independently challenging proposed actions
    - Identifying weak evidence
    - Flagging overconfidence
    - Recommending abstention when appropriate
    """
    
    def __init__(
        self,
        overconfidence_threshold: float = 0.15,
        weak_evidence_threshold: float = 0.3,
        severe_critique_threshold: int = 2
    ):
        self.overconfidence_threshold = overconfidence_threshold
        self.weak_evidence_threshold = weak_evidence_threshold
        self.severe_critique_threshold = severe_critique_threshold
        
        # Calibration history for overconfidence detection
        self._calibration_history: List[Tuple[float, float]] = []  # (predicted, actual)
        
    def process(
        self,
        planning_result: PlanningResult,
        situation_result: SituationResult,
        perception_result: PerceptionResult,
        memory_result: MemoryResult
    ) -> CriticResult:
        """
        Critique the planned action.
        
        Args:
            planning_result: Result from planning layer
            situation_result: Result from situation assessment
            perception_result: Result from perception layer
            memory_result: Result from memory retrieval
            
        Returns:
            CriticResult with critiques and recommendations
        """
        if not planning_result.best_action:
            return self._create_no_action_result(planning_result.session_id)
        
        original_action = planning_result.best_action
        critiques: List[CritiqueItem] = []
        overconfidence_flags: List[str] = []
        weak_evidence_flags: List[str] = []
        
        # Perform various critiques
        critiques.extend(self._critique_data_quality(perception_result))
        critiques.extend(self._critique_situation_confidence(situation_result))
        critiques.extend(self._critique_historical_context(memory_result))
        critiques.extend(self._critique_action_parameters(original_action))
        critiques.extend(self._critique_overconfidence(original_action, situation_result))
        
        # Extract flags
        overconfidence_flags = [c.description for c in critiques 
                               if "overconfident" in c.description.lower()]
        weak_evidence_flags = [c.description for c in critiques
                              if c.category == "weak_evidence"]
        
        # Determine overall severity
        overall_severity = self._determine_overall_severity(critiques)
        
        # Calculate confidence adjustment
        confidence_adj = self._calculate_confidence_adjustment(critiques, situation_result)
        
        # Determine if should proceed
        should_proceed = (
            overall_severity not in [CritiqueLevel.SEVERE, CritiqueLevel.BLOCK] and
            not self._should_abstain(critiques, situation_result, original_action)
        )
        
        # Check for abstention
        abstention_recommended, abstention_reason = self._check_abstention(
            critiques, situation_result, original_action
        )
        
        # Create adjusted action if proceeding
        adjusted_action = None
        if should_proceed and confidence_adj != 0:
            adjusted_action = self._adjust_action(original_action, confidence_adj)
        
        # Calculate overall confidence
        confidence = self._calculate_critique_confidence(critiques)
        
        result = CriticResult(
            session_id=planning_result.session_id,
            timestamp=datetime.now(),
            original_action=original_action,
            critiques=critiques,
            overall_severity=overall_severity,
            should_proceed=should_proceed,
            confidence_adjustment=confidence_adj,
            adjusted_action=adjusted_action,
            abstention_recommended=abstention_recommended,
            abstention_reason=abstention_reason,
            overconfidence_flags=overconfidence_flags,
            weak_evidence_flags=weak_evidence_flags,
            confidence=confidence,
            metadata={
                "critique_method": "multi_perspective",
                "severe_count": sum(1 for c in critiques if c.severity == CritiqueLevel.SEVERE)
            }
        )
        
        logger.debug(f"Critic: {len(critiques)} critiques, severity={overall_severity.value}, proceed={should_proceed}")
        return result
    
    def _critique_data_quality(self, perception: PerceptionResult) -> List[CritiqueItem]:
        """Critique the quality of input data"""
        critiques = []
        
        if perception.quality == DataQuality.POOR:
            critiques.append(CritiqueItem(
                category="data_quality",
                severity=CritiqueLevel.MODERATE,
                description="Data quality is poor",
                evidence=[f"Quality score: {perception.quality_score:.2f}"],
                recommendation="Consider waiting for better data quality",
                confidence_in_critique=0.8
            ))
        elif perception.quality == DataQuality.UNUSABLE:
            critiques.append(CritiqueItem(
                category="data_quality",
                severity=CritiqueLevel.BLOCK,
                description="Data is unusable",
                evidence=["Data quality assessment: UNUSABLE"],
                recommendation="Do not trade - data integrity compromised",
                confidence_in_critique=0.95
            ))
        
        if DataAnomaly.SPIKE_DETECTED in perception.anomalies:
            critiques.append(CritiqueItem(
                category="data_quality",
                severity=CritiqueLevel.SEVERE,
                description="Price spike detected in data",
                evidence=["Anomaly: SPIKE_DETECTED"],
                recommendation="Verify data source and wait for stabilization",
                confidence_in_critique=0.85
            ))
        
        if perception.missing_ticks_count > 5:
            critiques.append(CritiqueItem(
                category="weak_evidence",
                severity=CritiqueLevel.MODERATE,
                description=f"Missing {perception.missing_ticks_count} ticks in recent data",
                evidence=[f"Missing ticks: {perception.missing_ticks_count}"],
                recommendation="Analysis may be based on incomplete data",
                confidence_in_critique=0.7
            ))
        
        if perception.latency_ms > 200:
            critiques.append(CritiqueItem(
                category="data_quality",
                severity=CritiqueLevel.MINOR,
                description=f"High latency ({perception.latency_ms:.0f}ms)",
                evidence=[f"Latency: {perception.latency_ms:.0f}ms"],
                recommendation="Data may not reflect current market",
                confidence_in_critique=0.6
            ))
        
        return critiques
    
    def _critique_situation_confidence(self, situation: SituationResult) -> List[CritiqueItem]:
        """Critique the confidence in situation assessment"""
        critiques = []
        
        if situation.regime == MarketRegime.UNKNOWN:
            critiques.append(CritiqueItem(
                category="situation_assessment",
                severity=CritiqueLevel.BLOCK,
                description="Cannot determine market regime",
                evidence=["Regime: UNKNOWN"],
                recommendation="Abstain from trading until regime is identifiable",
                confidence_in_critique=0.95
            ))
        
        if situation.regime_confidence < 0.5:
            critiques.append(CritiqueItem(
                category="weak_evidence",
                severity=CritiqueLevel.MODERATE,
                description=f"Low confidence in regime detection ({situation.regime_confidence:.0%})",
                evidence=[f"Regime confidence: {situation.regime_confidence:.0%}"],
                recommendation="Reduce position size or wait for confirmation",
                confidence_in_critique=0.75
            ))
        
        if situation.regime_transition_detected:
            critiques.append(CritiqueItem(
                category="situation_assessment",
                severity=CritiqueLevel.MODERATE,
                description="Regime transition in progress",
                evidence=[f"Transition probability: {situation.transition_probability:.0%}"],
                recommendation="Current analysis may not hold after transition",
                confidence_in_critique=0.7
            ))
        
        if situation.uncertainty > 0.7:
            critiques.append(CritiqueItem(
                category="weak_evidence",
                severity=CritiqueLevel.SEVERE,
                description=f"High uncertainty ({situation.uncertainty:.0%})",
                evidence=[f"Uncertainty: {situation.uncertainty:.0%}"],
                recommendation="Significant uncertainty in predictions",
                confidence_in_critique=0.85
            ))
        
        return critiques
    
    def _critique_historical_context(self, memory: MemoryResult) -> List[CritiqueItem]:
        """Critique the strength of historical context"""
        critiques = []
        
        if not memory.is_sufficient_context:
            critiques.append(CritiqueItem(
                category="weak_evidence",
                severity=CritiqueLevel.MODERATE,
                description="Insufficient historical context for this situation",
                evidence=[f"Retrieved: {len(memory.retrieved_situations)} situations"],
                recommendation="Proceed with caution, may be operating outside historical patterns",
                confidence_in_critique=0.8
            ))
        
        if memory.outcome_confidence < 0.5:
            critiques.append(CritiqueItem(
                category="weak_evidence",
                severity=CritiqueLevel.MODERATE,
                description="Low confidence in historical outcomes",
                evidence=[f"Outcome confidence: {memory.outcome_confidence:.0%}"],
                recommendation="Historical data shows inconsistent results",
                confidence_in_critique=0.7
            ))
        
        if memory.retrieved_situations:
            dist = memory.outcome_distribution
            total = sum(dist.values())
            if total > 0:
                failure_rate = dist.get("FAILURE", 0) / total
                if failure_rate > 0.4:
                    critiques.append(CritiqueItem(
                        category="risk_assessment",
                        severity=CritiqueLevel.SEVERE,
                        description=f"High historical failure rate ({failure_rate:.0%})",
                        evidence=[f"Failures: {dist.get('FAILURE', 0)}/{total}"],
                        recommendation="Consider alternative action or abstention",
                        confidence_in_critique=0.85
                    ))
        
        return critiques
    
    def _critique_action_parameters(self, action: CandidateAction) -> List[CritiqueItem]:
        """Critique the action parameters"""
        critiques = []
        
        if action.win_probability < 0.5 and action.expected_value > 0:
            critiques.append(CritiqueItem(
                category="risk_assessment",
                severity=CritiqueLevel.MINOR,
                description=f"Unusual parameters: low prob ({action.win_probability:.0%}) but positive EV",
                evidence=[
                    f"Probability: {action.win_probability:.0%}",
                    f"Expected value: {action.expected_value:.4f}"
                ],
                recommendation="Verify payout assumptions",
                confidence_in_critique=0.6
            ))
        
        if action.expected_value_std > abs(action.expected_value):
            critiques.append(CritiqueItem(
                category="risk_assessment",
                severity=CritiqueLevel.MODERATE,
                description="High uncertainty in expected value",
                evidence=[f"EV std: {action.expected_value_std:.4f}, EV: {action.expected_value:.4f}"],
                recommendation="Variance in outcomes is significant",
                confidence_in_critique=0.75
            ))
        
        if action.risk_factors:
            # Check for severe risk factors
            severe_risks = [r for r in action.risk_factors if "extreme" in r.lower() or "high volatility" in r.lower()]
            if severe_risks:
                critiques.append(CritiqueItem(
                    category="risk_assessment",
                    severity=CritiqueLevel.SEVERE,
                    description=f"Severe risk factors identified: {', '.join(severe_risks)}",
                    evidence=severe_risks,
                    recommendation="Significant risks present, consider abstention",
                    confidence_in_critique=0.8
                ))
        
        return critiques
    
    def _critique_overconfidence(
        self,
        action: CandidateAction,
        situation: SituationResult
    ) -> List[CritiqueItem]:
        """Detect potential overconfidence"""
        critiques = []
        
        # Check if predicted probability is higher than historical suggests
        if self._calibration_history:
            recent_calibration = self._calibration_history[-20:]
            if recent_calibration:
                avg_predicted = np.mean([p for p, _ in recent_calibration])
                avg_actual = np.mean([a for _, a in recent_calibration])
                
                overconfidence = avg_predicted - avg_actual
                
                if overconfidence > self.overconfidence_threshold:
                    critiques.append(CritiqueItem(
                        category="overconfidence",
                        severity=CritiqueLevel.MODERATE,
                        description=f"Historical overconfidence detected ({overconfidence:.0%})",
                        evidence=[
                            f"Avg predicted: {avg_predicted:.0%}",
                            f"Avg actual: {avg_actual:.0%}"
                        ],
                        recommendation="Reduce confidence estimates by historical calibration error",
                        confidence_in_critique=0.75
                    ))
        
        # Check for suspiciously high confidence with low evidence
        if action.confidence > 0.9 and situation.regime_confidence < 0.6:
            critiques.append(CritiqueItem(
                category="overconfidence",
                severity=CritiqueLevel.SEVERE,
                description="Action confidence exceeds situation confidence",
                evidence=[
                    f"Action confidence: {action.confidence:.0%}",
                    f"Situation confidence: {situation.regime_confidence:.0%}"
                ],
                recommendation="Reduce action confidence to match situation awareness",
                confidence_in_critique=0.85
            ))
        
        # Check for high EV without sufficient context
        if action.expected_value > 0.3 and len(action.supporting_situations) < 3:
            critiques.append(CritiqueItem(
                category="overconfidence",
                severity=CritiqueLevel.MINOR,
                description="High expected value based on limited historical support",
                evidence=[
                    f"Expected value: {action.expected_value:.4f}",
                    f"Supporting situations: {len(action.supporting_situations)}"
                ],
                recommendation="Verify EV estimate with additional data",
                confidence_in_critique=0.65
            ))
        
        return critiques
    
    def _determine_overall_severity(self, critiques: List[CritiqueItem]) -> CritiqueLevel:
        """Determine overall severity of critiques"""
        if not critiques:
            return CritiqueLevel.NONE
        
        severities = [c.severity for c in critiques]
        
        if CritiqueLevel.BLOCK in severities:
            return CritiqueLevel.BLOCK
        
        severe_count = sum(1 for s in severities if s == CritiqueLevel.SEVERE)
        if severe_count >= self.severe_critique_threshold:
            return CritiqueLevel.SEVERE
        
        if CritiqueLevel.SEVERE in severities:
            return CritiqueLevel.MODERATE
        
        moderate_count = sum(1 for s in severities if s == CritiqueLevel.MODERATE)
        if moderate_count >= 2:
            return CritiqueLevel.MODERATE
        
        if CritiqueLevel.MODERATE in severities or CritiqueLevel.MINOR in severities:
            return CritiqueLevel.MINOR
        
        return CritiqueLevel.NONE
    
    def _should_abstain(
        self,
        critiques: List[CritiqueItem],
        situation: SituationResult,
        action: CandidateAction
    ) -> bool:
        """Determine if should abstain from trading"""
        # Block-level critiques always lead to abstention
        if self._determine_overall_severity(critiques) == CritiqueLevel.BLOCK:
            return True
        
        # Very high uncertainty
        if situation.uncertainty > 0.85:
            return True
        
        # Multiple severe critiques
        severe_count = sum(1 for c in critiques if c.severity == CritiqueLevel.SEVERE)
        if severe_count >= 3:
            return True
        
        # High uncertainty with low action confidence
        if situation.uncertainty > 0.7 and action.confidence < 0.4:
            return True
        
        return False
    
    def _check_abstention(
        self,
        critiques: List[CritiqueItem],
        situation: SituationResult,
        action: CandidateAction
    ) -> Tuple[bool, Optional[str]]:
        """Check if abstention is recommended"""
        if self._should_abstain(critiques, situation, action):
            reasons = []
            
            for c in critiques:
                if c.severity in [CritiqueLevel.SEVERE, CritiqueLevel.BLOCK]:
                    reasons.append(c.description)
            
            if not reasons:
                reasons.append("Multiple moderate concerns detected")
            
            return True, "; ".join(reasons[:3])
        
        return False, None
    
    def _calculate_confidence_adjustment(
        self,
        critiques: List[CritiqueItem],
        situation: SituationResult
    ) -> float:
        """Calculate how much to adjust confidence"""
        adjustment = 0.0
        
        for critique in critiques:
            if critique.severity == CritiqueLevel.BLOCK:
                adjustment -= 1.0
            elif critique.severity == CritiqueLevel.SEVERE:
                adjustment -= 0.3 * critique.confidence_in_critique
            elif critique.severity == CritiqueLevel.MODERATE:
                adjustment -= 0.15 * critique.confidence_in_critique
            elif critique.severity == CritiqueLevel.MINOR:
                adjustment -= 0.05 * critique.confidence_in_critique
        
        # Additional adjustment for high uncertainty
        if situation.uncertainty > 0.5:
            adjustment -= situation.uncertainty * 0.2
        
        return max(-1.0, min(0.0, adjustment))
    
    def _adjust_action(
        self,
        action: CandidateAction,
        confidence_adj: float
    ) -> CandidateAction:
        """Create adjusted action based on critique"""
        import copy
        adjusted = copy.deepcopy(action)
        
        # Adjust confidence
        adjusted.confidence = max(0.0, min(1.0, action.confidence + confidence_adj))
        
        # Update confidence level
        if adjusted.confidence > 0.8:
            adjusted.confidence_level = ActionConfidence.HIGH
        elif adjusted.confidence > 0.5:
            adjusted.confidence_level = ActionConfidence.MEDIUM
        elif adjusted.confidence > 0.2:
            adjusted.confidence_level = ActionConfidence.LOW
        else:
            adjusted.confidence_level = ActionConfidence.ABSTAIN
        
        # Reduce stake proportionally
        if confidence_adj < 0:
            stake_reduction = 1.0 + confidence_adj
            adjusted.stake_amount *= stake_reduction
        
        # Add critique note to reasoning
        adjusted.reasoning.append(
            f"Confidence adjusted by {confidence_adj:.2f} due to critique"
        )
        
        return adjusted
    
    def _calculate_critique_confidence(self, critiques: List[CritiqueItem]) -> float:
        """Calculate confidence in the critique itself"""
        if not critiques:
            return 0.5  # Neutral confidence when no critiques
        
        # Weight by severity
        severity_weights = {
            CritiqueLevel.BLOCK: 1.0,
            CritiqueLevel.SEVERE: 0.8,
            CritiqueLevel.MODERATE: 0.6,
            CritiqueLevel.MINOR: 0.4,
            CritiqueLevel.NONE: 0.2
        }
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for c in critiques:
            weight = severity_weights.get(c.severity, 0.5)
            weighted_confidence += c.confidence_in_critique * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.5
    
    def _create_no_action_result(self, session_id: str) -> CriticResult:
        """Create result when no action to critique"""
        return CriticResult(
            session_id=session_id,
            timestamp=datetime.now(),
            original_action=None,
            critiques=[],
            overall_severity=CritiqueLevel.NONE,
            should_proceed=False,
            confidence_adjustment=0.0,
            adjusted_action=None,
            abstention_recommended=True,
            abstention_reason="No action available to critique",
            overconfidence_flags=[],
            weak_evidence_flags=[],
            confidence=1.0,
            metadata={"reason": "no_action"}
        )
    
    def record_outcome(self, predicted_probability: float, actual_outcome: float) -> None:
        """
        Record prediction outcome for calibration tracking.
        
        Args:
            predicted_probability: The probability we predicted
            actual_outcome: 1.0 for win, 0.0 for loss
        """
        self._calibration_history.append((predicted_probability, actual_outcome))
        
        # Keep only last 100 records
        if len(self._calibration_history) > 100:
            self._calibration_history = self._calibration_history[-100:]
    
    def get_calibration_error(self) -> float:
        """Get current calibration error"""
        if len(self._calibration_history) < 10:
            return 0.0
        
        recent = self._calibration_history[-20:]
        predicted = np.mean([p for p, _ in recent])
        actual = np.mean([a for _, a in recent])
        
        return predicted - actual
    
    def reset(self) -> None:
        """Reset critic layer state"""
        self._calibration_history.clear()
        logger.info("Critic layer reset")


from .perception import DataAnomaly
