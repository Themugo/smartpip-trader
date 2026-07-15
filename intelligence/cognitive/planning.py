"""
Layer 4 — Planning
==================

Generates multiple candidate actions with expected value and uncertainty estimates.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .perception import PerceptionResult, DataQuality
from .situation import SituationResult, MarketRegime
from .memory import MemoryResult, HistoricalSituation

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of trading actions"""
    TRADE_CALL = "trade_call"
    TRADE_PUT = "trade_put"
    WAIT = "wait"
    REDUCE_EXPOSURE = "reduce_exposure"
    PAPER_TRADE = "paper_trade"
    NO_ACTION = "no_action"


class ActionConfidence(Enum):
    """Confidence levels for actions"""
    HIGH = "high"  # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # < 0.5
    ABSTAIN = "abstain"  # < 0.2


@dataclass
class CandidateAction:
    """A candidate trading action with estimates"""
    action_type: ActionType
    direction: str  # CALL, PUT, or None
    contract_type: Optional[str]  # e.g., DIGITEVEN, DIGITODD, etc.
    duration_seconds: int  # Contract duration
    stake_amount: float  # Suggested stake
    expected_value: float  # Expected PnL
    expected_value_std: float  # Uncertainty in EV
    win_probability: float  # Probability of success
    risk_reward_ratio: float
    confidence: float  # Overall confidence 0-1
    confidence_level: ActionConfidence
    reasoning: List[str]  # Why this action
    supporting_situations: List[str]  # IDs of similar historical situations
    risk_factors: List[str]  # Identified risks
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "direction": self.direction,
            "contract_type": self.contract_type,
            "duration_seconds": self.duration_seconds,
            "stake_amount": self.stake_amount,
            "expected_value": self.expected_value,
            "expected_value_std": self.expected_value_std,
            "win_probability": self.win_probability,
            "risk_reward_ratio": self.risk_reward_ratio,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "reasoning": self.reasoning,
            "supporting_situations": self.supporting_situations,
            "risk_factors": self.risk_factors
        }
    
    @property
    def sharpe_like_ratio(self) -> float:
        """Calculate a Sharpe-like ratio for the action"""
        if self.expected_value_std == 0:
            return 0.0
        return self.expected_value / self.expected_value_std


@dataclass
class PlanningResult:
    """Result from planning layer"""
    session_id: str
    timestamp: datetime
    candidate_actions: List[CandidateAction]
    best_action: Optional[CandidateAction]
    alternative_actions: List[CandidateAction]
    situation_summary: str  # Natural language summary
    recommended_duration: int  # Recommended contract duration
    risk_tolerance: str  # conservative, moderate, aggressive
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "candidate_count": len(self.candidate_actions),
            "best_action": self.best_action.to_dict() if self.best_action else None,
            "alternatives_count": len(self.alternative_actions),
            "situation_summary": self.situation_summary,
            "recommended_duration": self.recommended_duration,
            "risk_tolerance": self.risk_tolerance,
            "confidence": self.confidence
        }


class PlanningLayer:
    """
    Layer 4: Planning
    
    Responsible for:
    - Generating multiple candidate actions
    - Estimating expected value and uncertainty
    - Ranking actions by favorability
    """
    
    def __init__(
        self,
        base_stake: float = 1.0,
        max_stake: float = 100.0,
        durations: Optional[List[int]] = None,
        default_risk_tolerance: str = "moderate"
    ):
        self.base_stake = base_stake
        self.max_stake = max_stake
        self.durations = durations or [5, 10, 15, 30, 60, 120, 300]  # seconds
        self.default_risk_tolerance = default_risk_tolerance
        
        # Base probabilities for different regimes (these would be learned)
        self.base_probabilities = {
            MarketRegime.TRENDING_UP: {"CALL": 0.65, "PUT": 0.45},
            MarketRegime.TRENDING_DOWN: {"CALL": 0.45, "PUT": 0.65},
            MarketRegime.RANGING: {"CALL": 0.52, "PUT": 0.52},
            MarketRegime.VOLATILE: {"CALL": 0.48, "PUT": 0.48},
            MarketRegime.QUIESCENT: {"CALL": 0.55, "PUT": 0.55},
            MarketRegime.BREAKOUT_IMMINENT: {"CALL": 0.55, "PUT": 0.55},
            MarketRegime.UNKNOWN: {"CALL": 0.50, "PUT": 0.50}
        }
        
    def process(
        self,
        situation_result: SituationResult,
        memory_result: MemoryResult,
        perception_result: PerceptionResult,
        risk_tolerance: Optional[str] = None
    ) -> PlanningResult:
        """
        Generate candidate actions based on situation and memory.
        
        Args:
            situation_result: Result from situation assessment
            memory_result: Result from memory retrieval
            perception_result: Result from perception layer
            risk_tolerance: Risk tolerance (conservative, moderate, aggressive)
            
        Returns:
            PlanningResult with candidate actions
        """
        risk_tolerance = risk_tolerance or self.default_risk_tolerance
        
        # Generate candidates
        candidates = self._generate_candidates(
            situation_result, memory_result, perception_result, risk_tolerance
        )
        
        # Rank and select best
        ranked = self._rank_actions(candidates)
        
        best_action = ranked[0] if ranked else None
        alternatives = ranked[1:4] if len(ranked) > 1 else []
        
        # Determine recommended duration
        duration = self._determine_duration(situation_result, memory_result)
        
        # Generate summary
        summary = self._generate_summary(ranked, situation_result)
        
        # Calculate confidence
        confidence = self._calculate_planning_confidence(
            best_action, situation_result, memory_result
        ) if best_action else 0.0
        
        result = PlanningResult(
            session_id=situation_result.session_id,
            timestamp=datetime.now(),
            candidate_actions=candidates,
            best_action=best_action,
            alternative_actions=alternatives,
            situation_summary=summary,
            recommended_duration=duration,
            risk_tolerance=risk_tolerance,
            confidence=confidence,
            metadata={
                "generation_method": "rule_based_with_memory",
                "situation_regime": situation_result.regime.value
            }
        )
        
        logger.debug(f"Planning: generated {len(candidates)} candidates, best={best_action.action_type.value if best_action else 'none'}")
        return result
    
    def _generate_candidates(
        self,
        situation: SituationResult,
        memory: MemoryResult,
        perception: PerceptionResult,
        risk_tolerance: str
    ) -> List[CandidateAction]:
        """Generate candidate actions"""
        candidates = []
        
        # Get base probabilities adjusted by memory
        base_probs = self._get_adjusted_probabilities(situation, memory)
        
        # Generate trade CALL candidates
        if situation.trend in ["up", "neutral"] or situation.regime == MarketRegime.TRENDING_UP:
            candidates.extend(
                self._create_trade_candidates(
                    "CALL", base_probs["CALL"], situation, memory, risk_tolerance
                )
            )
        
        # Generate trade PUT candidates
        if situation.trend in ["down", "neutral"] or situation.regime == MarketRegime.TRENDING_DOWN:
            candidates.extend(
                self._create_trade_candidates(
                    "PUT", base_probs["PUT"], situation, memory, risk_tolerance
                )
            )
        
        # Add wait action
        candidates.append(self._create_wait_action(situation, memory))
        
        # Add reduce exposure action
        if situation.volatility > 0.6 or situation.uncertainty > 0.5:
            candidates.append(self._create_reduce_action(situation, memory))
        
        # Add paper trade action
        candidates.append(self._create_paper_action(situation, memory, base_probs))
        
        # Add no action
        candidates.append(self._create_no_action(situation))
        
        return candidates
    
    def _create_trade_candidates(
        self,
        direction: str,
        base_prob: float,
        situation: SituationResult,
        memory: MemoryResult,
        risk_tolerance: str
    ) -> List[CandidateAction]:
        """Create trade candidates for a direction"""
        candidates = []
        
        # Select appropriate durations based on regime
        if situation.regime == MarketRegime.TRENDING_UP or situation.regime == MarketRegime.TRENDING_DOWN:
            durations = [5, 10, 15]  # Shorter for trending
        elif situation.regime == MarketRegime.RANGING:
            durations = [15, 30, 60]  # Longer for ranging
        else:
            durations = [10, 15, 30]  # Default
        
        for duration in durations:
            prob = base_prob
            
            # Adjust for memory
            if memory.retrieved_situations:
                historical_probs = [
                    s.win_probability if hasattr(s, 'win_probability') else 0.5
                    for s in memory.retrieved_situations
                ]
                if historical_probs:
                    prob = (prob + np.mean(historical_probs)) / 2
            
            # Adjust for uncertainty
            prob *= (1 - situation.uncertainty * 0.3)
            
            # Calculate expected value
            payout = 0.95  # Binary option payout
            ev = prob * payout - (1 - prob)
            
            # Calculate EV std based on uncertainty
            ev_std = abs(ev) * situation.uncertainty
            
            # Adjust stake based on risk tolerance
            stake_multiplier = {
                "conservative": 0.5,
                "moderate": 1.0,
                "aggressive": 1.5
            }.get(risk_tolerance, 1.0)
            
            stake = min(self.max_stake, self.base_stake * stake_multiplier)
            
            # Calculate confidence
            confidence = self._calculate_action_confidence(
                prob, situation, memory, ev
            )
            
            # Determine confidence level
            if confidence > 0.8:
                level = ActionConfidence.HIGH
            elif confidence > 0.5:
                level = ActionConfidence.MEDIUM
            elif confidence > 0.2:
                level = ActionConfidence.LOW
            else:
                level = ActionConfidence.ABSTAIN
            
            # Build reasoning
            reasoning = self._build_trade_reasoning(direction, duration, prob, situation, memory)
            
            # Identify risk factors
            risk_factors = self._identify_risk_factors(situation, memory)
            
            # Get supporting situations
            supporting = [s.id for s, _ in memory.ranked_situations[:3]]
            
            candidates.append(CandidateAction(
                action_type=ActionType.TRADE_CALL if direction == "CALL" else ActionType.TRADE_PUT,
                direction=direction,
                contract_type=self._get_contract_type(direction, situation),
                duration_seconds=duration,
                stake_amount=stake,
                expected_value=ev,
                expected_value_std=ev_std,
                win_probability=prob,
                risk_reward_ratio=payout / (1 - payout) if prob < 1 else float('inf'),
                confidence=confidence,
                confidence_level=level,
                reasoning=reasoning,
                supporting_situations=supporting,
                risk_factors=risk_factors,
                metadata={
                    "regime_at_generation": situation.regime.value,
                    "adjusted_probability": prob
                }
            ))
        
        return candidates
    
    def _create_wait_action(
        self,
        situation: SituationResult,
        memory: MemoryResult
    ) -> CandidateAction:
        """Create a wait action"""
        reasoning = [
            f"Market regime is {situation.regime.value}",
            f"Uncertainty level is {situation.uncertainty:.2f}"
        ]
        
        if situation.regime_transition_detected:
            reasoning.append("Regime transition detected - waiting for confirmation")
        
        if not memory.is_sufficient_context:
            reasoning.append("Insufficient historical context for confident action")
        
        return CandidateAction(
            action_type=ActionType.WAIT,
            direction=None,
            contract_type=None,
            duration_seconds=0,
            stake_amount=0,
            expected_value=0,
            expected_value_std=0,
            win_probability=0,
            risk_reward_ratio=0,
            confidence=0.5,
            confidence_level=ActionConfidence.MEDIUM,
            reasoning=reasoning,
            supporting_situations=[],
            risk_factors=["Time opportunity cost"]
        )
    
    def _create_reduce_action(
        self,
        situation: SituationResult,
        memory: MemoryResult
    ) -> CandidateAction:
        """Create a reduce exposure action"""
        reasoning = [
            f"High volatility detected ({situation.volatility:.2f})",
            f"Elevated uncertainty ({situation.uncertainty:.2f})",
            "Reducing exposure to manage risk"
        ]
        
        return CandidateAction(
            action_type=ActionType.REDUCE_EXPOSURE,
            direction=None,
            contract_type=None,
            duration_seconds=0,
            stake_amount=self.base_stake * 0.25,  # 25% of normal
            expected_value=0,
            expected_value_std=0,
            win_probability=0.5,
            risk_reward_ratio=1,
            confidence=0.6,
            confidence_level=ActionConfidence.MEDIUM,
            reasoning=reasoning,
            supporting_situations=[],
            risk_factors=["Reduced profit potential"]
        )
    
    def _create_paper_action(
        self,
        situation: SituationResult,
        memory: MemoryResult,
        base_probs: Dict[str, float]
    ) -> CandidateAction:
        """Create a paper trade action"""
        direction = "CALL" if situation.trend.value == "up" else "PUT"
        
        reasoning = [
            "Paper trading mode - no real capital at risk",
            "Building historical record for this regime",
            f"Direction: {direction} based on {situation.trend.value} trend"
        ]
        
        return CandidateAction(
            action_type=ActionType.PAPER_TRADE,
            direction=direction,
            contract_type=self._get_contract_type(direction, situation),
            duration_seconds=15,
            stake_amount=0,  # Paper trade
            expected_value=base_probs[direction] * 0.95 - 0.05,
            expected_value_std=0.3,
            win_probability=base_probs[direction],
            risk_reward_ratio=0.95 / 0.05,
            confidence=0.4,
            confidence_level=ActionConfidence.LOW,
            reasoning=reasoning,
            supporting_situations=[],
            risk_factors=["No real trading experience gained"]
        )
    
    def _create_no_action(
        self,
        situation: SituationResult
    ) -> CandidateAction:
        """Create a no action (abstain) action"""
        reasoning = [
            f"Regime: {situation.regime.value}",
            f"Uncertainty: {situation.uncertainty:.2f}",
            f"Confidence: {situation.confidence:.2f}"
        ]
        
        if situation.regime == MarketRegime.UNKNOWN:
            reasoning.append("Cannot assess market conditions")
        
        if situation.uncertainty > 0.8:
            reasoning.append("Extremely uncertain conditions")
        
        return CandidateAction(
            action_type=ActionType.NO_ACTION,
            direction=None,
            contract_type=None,
            duration_seconds=0,
            stake_amount=0,
            expected_value=0,
            expected_value_std=0,
            win_probability=0,
            risk_reward_ratio=0,
            confidence=situation.uncertainty,
            confidence_level=ActionConfidence.ABSTAIN,
            reasoning=reasoning,
            supporting_situations=[],
            risk_factors=["Zero progress toward goals"]
        )
    
    def _get_adjusted_probabilities(
        self,
        situation: SituationResult,
        memory: MemoryResult
    ) -> Dict[str, float]:
        """Get probabilities adjusted by situation and memory"""
        base = self.base_probabilities.get(
            situation.regime,
            self.base_probabilities[MarketRegime.UNKNOWN]
        )
        
        adjusted = base.copy()
        
        # Adjust based on memory
        if memory.retrieved_situations and memory.outcome_confidence > 0.5:
            for situation_obj, similarity in memory.ranked_situations[:5]:
                if hasattr(situation_obj, 'win_probability'):
                    weight = similarity * situation_obj.confidence
                    adjusted["CALL"] = adjusted["CALL"] * 0.7 + situation_obj.win_probability * 0.3
                    adjusted["PUT"] = adjusted["PUT"] * 0.7 + situation_obj.win_probability * 0.3
        
        # Adjust for regime confidence
        if situation.regime_confidence < 0.5:
            # Pull toward 50%
            for key in adjusted:
                adjusted[key] = 0.5 + (adjusted[key] - 0.5) * situation.regime_confidence
        
        return adjusted
    
    def _calculate_action_confidence(
        self,
        probability: float,
        situation: SituationResult,
        memory: MemoryResult,
        expected_value: float
    ) -> float:
        """Calculate confidence in an action"""
        # Base confidence from probability
        confidence = probability
        
        # Reduce for low situation confidence
        confidence *= situation.confidence
        
        # Reduce for uncertain regime detection
        if situation.regime_confidence < 0.5:
            confidence *= situation.regime_confidence * 2
        
        # Boost for good historical context
        if memory.is_sufficient_context and memory.outcome_confidence > 0.6:
            confidence *= 1.2
        
        # Reduce for high uncertainty
        confidence *= (1 - situation.uncertainty * 0.4)
        
        # Reduce for regime transition
        if situation.regime_transition_detected:
            confidence *= 0.7
        
        return max(0.0, min(1.0, confidence))
    
    def _rank_actions(self, candidates: List[CandidateAction]) -> List[CandidateAction]:
        """Rank actions by favorability"""
        # Filter out abstain actions for trading decisions
        tradeable = [c for c in candidates if c.confidence_level != ActionConfidence.ABSTAIN]
        
        # Sort by a composite score
        def score(action: CandidateAction) -> float:
            # Weight expected value, confidence, and probability
            ev_weight = 0.4
            conf_weight = 0.3
            prob_weight = 0.3
            
            return (
                ev_weight * max(0, action.expected_value) +
                conf_weight * action.confidence +
                prob_weight * action.win_probability
            )
        
        return sorted(tradeable, key=score, reverse=True)
    
    def _determine_duration(
        self,
        situation: SituationResult,
        memory: MemoryResult
    ) -> int:
        """Determine recommended contract duration"""
        if situation.regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            return 5  # Quick trades in trends
        
        if situation.regime == MarketRegime.RANGING:
            return 15  # Medium duration for ranging
        
        if situation.regime == MarketRegime.VOLATILE:
            return 5  # Short in volatile markets
        
        if situation.volatility > 0.6:
            return 5  # Short when volatile
        
        # Default to moderate duration
        return 15
    
    def _get_contract_type(self, direction: str, situation: SituationResult) -> str:
        """Get appropriate contract type"""
        # For simplicity, use MATCH/DIFF contracts
        # In production, would select based on regime and conditions
        if situation.regime == MarketRegime.RANGING:
            return "DIGITMATCH" if random.random() > 0.5 else "DIGITDIFF"
        return "DIGITOVER" if direction == "CALL" else "DIGITUNDER"
    
    def _build_trade_reasoning(
        self,
        direction: str,
        duration: int,
        probability: float,
        situation: SituationResult,
        memory: MemoryResult
    ) -> List[str]:
        """Build natural language reasoning for trade"""
        reasoning = [
            f"Direction: {direction}",
            f"Duration: {duration}s",
            f"Probability: {probability:.1%}"
        ]
        
        if situation.trend.value != "neutral":
            reasoning.append(f"Trend: {situation.trend.value}")
        
        if situation.regime != MarketRegime.UNKNOWN:
            reasoning.append(f"Regime: {situation.regime.value}")
        
        if memory.retrieved_situations:
            reasoning.append(f"Based on {len(memory.retrieved_situations)} similar historical situations")
        
        return reasoning
    
    def _identify_risk_factors(
        self,
        situation: SituationResult,
        memory: MemoryResult
    ) -> List[str]:
        """Identify risk factors for the current situation"""
        risks = []
        
        if situation.volatility > 0.7:
            risks.append("High volatility may cause unexpected outcomes")
        
        if situation.uncertainty > 0.5:
            risks.append("Elevated uncertainty reduces prediction accuracy")
        
        if situation.regime_transition_detected:
            risks.append("Regime transition may invalidate current analysis")
        
        if not memory.is_sufficient_context:
            risks.append("Limited historical data for this regime")
        
        if memory.outcome_confidence < 0.5:
            risks.append("Historical outcomes show mixed results")
        
        return risks
    
    def _generate_summary(
        self,
        ranked: List[CandidateAction],
        situation: SituationResult
    ) -> str:
        """Generate natural language summary"""
        if not ranked:
            return "No favorable trading opportunities identified."
        
        best = ranked[0]
        
        summary_parts = [
            f"Best action: {best.action_type.value.replace('_', ' ').title()}"
        ]
        
        if best.direction:
            summary_parts.append(f"Direction: {best.direction}")
        
        summary_parts.append(f"Confidence: {best.confidence:.0%}")
        summary_parts.append(f"Expected Value: {best.expected_value:.4f}")
        
        if situation.regime != MarketRegime.UNKNOWN:
            summary_parts.append(f"Market in {situation.regime.value.replace('_', ' ')} regime")
        
        return ". ".join(summary_parts)
    
    def _calculate_planning_confidence(
        self,
        best_action: CandidateAction,
        situation: SituationResult,
        memory: MemoryResult
    ) -> float:
        """Calculate overall planning confidence"""
        # Combine action confidence with situation awareness
        confidence = best_action.confidence * 0.6 + situation.confidence * 0.4
        
        # Boost for good memory context
        if memory.is_sufficient_context:
            confidence *= 1.1
        
        return max(0.0, min(1.0, confidence))
    
    def reset(self) -> None:
        """Reset planning layer state"""
        logger.info("Planning layer reset")
