"""
Strategy Orchestrator

Combines signals from multiple strategy plugins using configurable consensus mechanisms:
- Voting (majority wins)
- Weighted consensus (weighted by confidence, performance, etc.)
- Priority-based selection
- Custom consensus rules
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from collections import Counter

from plugins.base import Signal, TickData, RiskValidation, PluginMetadata

logger = logging.getLogger(__name__)


class ConsensusMode(Enum):
    """Consensus mechanism modes"""
    VOTING = "voting"  # Simple majority vote
    WEIGHTED_CONFIDENCE = "weighted_confidence"  # Weighted by confidence
    WEIGHTED_PERFORMANCE = "weighted_performance"  # Weighted by historical performance
    WEIGHTED_HYBRID = "weighted_hybrid"  # Combination of confidence and performance
    PRIORITY = "priority"  # First plugin with high enough confidence wins
    ALL_REQUIRED = "all_required"  # All plugins must agree
    ANY = "any"  # Any plugin can trigger
    THRESHOLD = "threshold"  # Configurable threshold for agreement


@dataclass
class ConsensusResult:
    """Result of signal consensus aggregation"""
    direction: str  # "CALL", "PUT", or "HOLD"
    confidence: float
    participating_signals: List[Signal]
    votes: Dict[str, int]
    weighted_scores: Dict[str, float]
    agreement_ratio: float  # 0-1, how many agree
    is_consensus: bool
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    consensus_mode: ConsensusMode = ConsensusMode.VOTING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "participating_signals": [s.to_dict() for s in self.participating_signals],
            "votes": self.votes,
            "weighted_scores": self.weighted_scores,
            "agreement_ratio": self.agreement_ratio,
            "is_consensus": self.is_consensus,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "consensus_mode": self.consensus_mode.value,
        }


@dataclass
class OrchestratorConfig:
    """Configuration for the strategy orchestrator"""
    mode: ConsensusMode = ConsensusMode.WEIGHTED_HYBRID
    min_signals: int = 1  # Minimum signals required
    min_agreement: float = 0.5  # Minimum agreement ratio (0-1)
    min_confidence: float = 60.0  # Minimum confidence threshold
    confidence_weight: float = 0.5  # Weight for confidence in hybrid mode
    performance_weight: float = 0.5  # Weight for performance in hybrid mode
    weights: Dict[str, float] = field(default_factory=dict)  # Per-plugin weights
    priorities: Dict[str, int] = field(default_factory=dict)  # Per-plugin priorities
    cooldown_period: float = 5.0  # Seconds between trades
    max_signals_per_tick: int = 5  # Maximum signals to consider
    allow_hold: bool = True  # Allow HOLD as a valid consensus direction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "min_signals": self.min_signals,
            "min_agreement": self.min_agreement,
            "min_confidence": self.min_confidence,
            "confidence_weight": self.confidence_weight,
            "performance_weight": self.performance_weight,
            "weights": self.weights,
            "priorities": self.priorities,
            "cooldown_period": self.cooldown_period,
            "max_signals_per_tick": self.max_signals_per_tick,
            "allow_hold": self.allow_hold,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorConfig":
        if "mode" in data and isinstance(data["mode"], str):
            data["mode"] = ConsensusMode(data["mode"])
        return cls(**data)


@dataclass
class SignalWithWeight:
    """Signal with calculated weight for consensus"""
    signal: Signal
    weight: float
    performance_score: float = 0.0
    confidence_score: float = 0.0


class StrategyOrchestrator:
    """
    Orchestrates multiple strategy plugins to reach consensus on trading decisions.
    
    Features:
    - Multiple consensus modes (voting, weighted, priority-based)
    - Configurable thresholds and weights
    - Per-plugin customization
    - Trade cooldown to prevent over-trading
    - Comprehensive logging and analytics
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self._config = config or OrchestratorConfig()
        self._plugin_metrics: Dict[str, Dict[str, Any]] = {}
        self._last_trade_time: Optional[datetime] = None
        self._signal_history: List[ConsensusResult] = []
        self._consensus_callbacks: List[Callable[[ConsensusResult], None]] = []
    
    @property
    def config(self) -> OrchestratorConfig:
        return self._config
    
    @config.setter
    def config(self, value: OrchestratorConfig) -> None:
        self._config = value
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with partial updates"""
        current = self._config.to_dict()
        current.update(updates)
        self._config = OrchestratorConfig.from_dict(current)
    
    def register_consensus_callback(
        self,
        callback: Callable[[ConsensusResult], None],
    ) -> None:
        """Register a callback to be called on consensus results"""
        self._consensus_callbacks.append(callback)
    
    def update_plugin_metrics(
        self,
        plugin_id: str,
        metrics: Dict[str, Any],
    ) -> None:
        """Update performance metrics for a plugin"""
        self._plugin_metrics[plugin_id] = metrics
    
    def _calculate_signal_weights(
        self,
        signals: List[Signal],
    ) -> List[SignalWithWeight]:
        """Calculate weights for each signal based on mode and configuration"""
        weighted_signals = []
        
        for signal in signals:
            weight = 1.0
            performance_score = 0.0
            confidence_score = signal.confidence
            
            # Apply custom plugin weight if configured
            if signal.plugin_id in self._config.weights:
                weight *= self._config.weights[signal.plugin_id]
            
            # Calculate performance score from metrics
            if signal.plugin_id in self._plugin_metrics:
                metrics = self._plugin_metrics[signal.plugin_id]
                total_trades = metrics.get("total_trades", 0)
                
                if total_trades > 0:
                    win_rate = metrics.get("winning_trades", 0) / total_trades
                    profit_factor = metrics.get("profit_factor", 1.0)
                    
                    # Performance score: combination of win rate and profit factor
                    performance_score = (win_rate * 0.6 + min(profit_factor / 2, 1) * 0.4)
                    
                    # Adjust weight based on performance in weighted modes
                    if self._config.mode in (
                        ConsensusMode.WEIGHTED_PERFORMANCE,
                        ConsensusMode.WEIGHTED_HYBRID,
                    ):
                        weight *= performance_score
            
            # In confidence-weighted modes, adjust by confidence
            if self._config.mode in (
                ConsensusMode.WEIGHTED_CONFIDENCE,
                ConsensusMode.WEIGHTED_HYBRID,
            ):
                confidence_normalized = signal.confidence / 100.0
                if self._config.mode == ConsensusMode.WEIGHTED_HYBRID:
                    weight *= (
                        confidence_normalized * self._config.confidence_weight +
                        performance_score * self._config.performance_weight
                    )
                else:
                    weight *= confidence_normalized
            
            weighted_signals.append(SignalWithWeight(
                signal=signal,
                weight=weight,
                performance_score=performance_score,
                confidence_score=confidence_score,
            ))
        
        return weighted_signals
    
    def _get_priority_order(
        self,
        signals: List[Signal],
    ) -> List[Signal]:
        """Order signals by priority if configured"""
        if not self._config.priorities:
            return signals
        
        return sorted(
            signals,
            key=lambda s: self._config.priorities.get(s.plugin_id, 0),
            reverse=True,
        )
    
    def _can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed (cooldown check)"""
        if self._last_trade_time and self._config.cooldown_period > 0:
            elapsed = (datetime.utcnow() - self._last_trade_time).total_seconds()
            if elapsed < self._config.cooldown_period:
                return False, f"Cooldown active: {self._config.cooldown_period - elapsed:.1f}s remaining"
        
        return True, "OK"
    
    def aggregate_signals(
        self,
        signals: List[Signal],
    ) -> ConsensusResult:
        """
        Aggregate multiple signals into a consensus decision.
        
        Args:
            signals: List of signals from different plugins
            
        Returns:
            ConsensusResult with the aggregated decision
        """
        # Filter by minimum confidence
        filtered_signals = [
            s for s in signals
            if s.confidence >= self._config.min_confidence
        ]
        
        if len(filtered_signals) < self._config.min_signals:
            return ConsensusResult(
                direction="HOLD",
                confidence=0,
                participating_signals=filtered_signals,
                votes={},
                weighted_scores={},
                agreement_ratio=0,
                is_consensus=False,
                reasoning=f"Only {len(filtered_signals)} signals meet minimum requirements (need {self._config.min_signals})",
            )
        
        # Limit signals if configured
        if len(filtered_signals) > self._config.max_signals_per_tick:
            weighted = self._calculate_signal_weights(filtered_signals)
            weighted.sort(key=lambda x: x.weight, reverse=True)
            filtered_signals = [w.signal for w in weighted[:self._config.max_signals_per_tick]]
        
        # Apply consensus mode
        if self._config.mode == ConsensusMode.VOTING:
            result = self._voting_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.WEIGHTED_CONFIDENCE:
            result = self._weighted_confidence_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.WEIGHTED_PERFORMANCE:
            result = self._weighted_performance_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.WEIGHTED_HYBRID:
            result = self._weighted_hybrid_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.PRIORITY:
            result = self._priority_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.ALL_REQUIRED:
            result = self._all_required_consensus(filtered_signals)
        elif self._config.mode == ConsensusMode.ANY:
            result = self._any_consensus(filtered_signals)
        else:
            result = self._threshold_consensus(filtered_signals)
        
        # Store result
        self._signal_history.append(result)
        if len(self._signal_history) > 1000:
            self._signal_history = self._signal_history[-500:]
        
        # Fire callbacks
        for callback in self._consensus_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in consensus callback: {e}")
        
        return result
    
    def _voting_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Simple majority voting"""
        votes = Counter(s.direction for s in signals)
        total = len(signals)
        
        if not votes:
            return ConsensusResult(
                direction="HOLD",
                confidence=0,
                participating_signals=signals,
                votes=dict(votes),
                weighted_scores={},
                agreement_ratio=0,
                is_consensus=False,
                reasoning="No signals to vote on",
            )
        
        # Get winner
        winner, count = votes.most_common(1)[0]
        agreement = count / total
        
        reasoning = f"Voting: {winner} wins with {count}/{total} votes ({agreement:.0%})"
        
        # Calculate confidence from agreement
        confidence = (agreement * 100 * sum(s.confidence for s in signals) / total) / 100
        
        return ConsensusResult(
            direction=winner if agreement >= self._config.min_agreement or self._config.allow_hold else "HOLD",
            confidence=confidence,
            participating_signals=signals,
            votes=dict(votes),
            weighted_scores={},
            agreement_ratio=agreement,
            is_consensus=agreement >= self._config.min_agreement,
            reasoning=reasoning,
            consensus_mode=ConsensusMode.VOTING,
        )
    
    def _weighted_confidence_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Consensus weighted by signal confidence"""
        weighted = self._calculate_signal_weights(signals)
        
        scores = {"CALL": 0.0, "PUT": 0.0}
        for ws in weighted:
            if ws.signal.direction in scores:
                scores[ws.signal.direction] += ws.weight * ws.signal.confidence
        
        winner = max(scores, key=scores.get)
        total_score = sum(scores.values())
        agreement = scores[winner] / total_score if total_score > 0 else 0
        
        reasoning = (
            f"Weighted confidence: {winner} scored {scores[winner]:.1f} "
            f"({agreement:.0%} of total weight)"
        )
        
        return ConsensusResult(
            direction=winner if agreement >= self._config.min_agreement or self._config.allow_hold else "HOLD",
            confidence=min(agreement * 100, 100),
            participating_signals=signals,
            votes={},
            weighted_scores=scores,
            agreement_ratio=agreement,
            is_consensus=agreement >= self._config.min_agreement,
            reasoning=reasoning,
            consensus_mode=ConsensusMode.WEIGHTED_CONFIDENCE,
        )
    
    def _weighted_performance_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Consensus weighted by plugin historical performance"""
        weighted = self._calculate_signal_weights(signals)
        
        scores = {"CALL": 0.0, "PUT": 0.0}
        for ws in weighted:
            if ws.signal.direction in scores:
                scores[ws.signal.direction] += ws.weight
        
        winner = max(scores, key=scores.get)
        total_score = sum(scores.values())
        agreement = scores[winner] / total_score if total_score > 0 else 0
        
        reasoning = (
            f"Weighted performance: {winner} scored {scores[winner]:.2f} "
            f"({agreement:.0%} of total)"
        )
        
        return ConsensusResult(
            direction=winner if agreement >= self._config.min_agreement or self._config.allow_hold else "HOLD",
            confidence=min(agreement * 100, 100),
            participating_signals=signals,
            votes={},
            weighted_scores=scores,
            agreement_ratio=agreement,
            is_consensus=agreement >= self._config.min_agreement,
            reasoning=reasoning,
            consensus_mode=ConsensusMode.WEIGHTED_PERFORMANCE,
        )
    
    def _weighted_hybrid_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Hybrid consensus combining confidence and performance"""
        weighted = self._calculate_signal_weights(signals)
        
        scores = {"CALL": 0.0, "PUT": 0.0}
        for ws in weighted:
            if ws.signal.direction in scores:
                # Weight by both confidence and performance
                combined_weight = ws.weight * (
                    ws.signal.confidence / 100 * self._config.confidence_weight +
                    ws.performance_score * self._config.performance_weight
                )
                scores[ws.signal.direction] += combined_weight
        
        winner = max(scores, key=scores.get)
        total_score = sum(scores.values())
        agreement = scores[winner] / total_score if total_score > 0 else 0
        
        reasoning = (
            f"Hybrid consensus: {winner} scored {scores[winner]:.3f} "
            f"({agreement:.0%} agreement)"
        )
        
        return ConsensusResult(
            direction=winner if agreement >= self._config.min_agreement or self._config.allow_hold else "HOLD",
            confidence=min(agreement * 100, 100),
            participating_signals=signals,
            votes={},
            weighted_scores=scores,
            agreement_ratio=agreement,
            is_consensus=agreement >= self._config.min_agreement,
            reasoning=reasoning,
            consensus_mode=ConsensusMode.WEIGHTED_HYBRID,
        )
    
    def _priority_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Priority-based consensus - first high-confidence signal wins"""
        ordered = self._get_priority_order(signals)
        
        for signal in ordered:
            if signal.confidence >= self._config.min_confidence:
                reasoning = (
                    f"Priority: {signal.plugin_name} wins with "
                    f"confidence {signal.confidence:.0f}%"
                )
                
                return ConsensusResult(
                    direction=signal.direction,
                    confidence=signal.confidence,
                    participating_signals=[signal],
                    votes={signal.direction: 1},
                    weighted_scores={signal.direction: 1.0},
                    agreement_ratio=1.0,
                    is_consensus=True,
                    reasoning=reasoning,
                    consensus_mode=ConsensusMode.PRIORITY,
                )
        
        return ConsensusResult(
            direction="HOLD",
            confidence=0,
            participating_signals=signals,
            votes={},
            weighted_scores={},
            agreement_ratio=0,
            is_consensus=False,
            reasoning="No signal met priority threshold",
            consensus_mode=ConsensusMode.PRIORITY,
        )
    
    def _all_required_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """All plugins must agree"""
        directions = set(s.direction for s in signals)
        
        if len(directions) == 1:
            direction = list(directions)[0]
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            
            return ConsensusResult(
                direction=direction,
                confidence=avg_confidence,
                participating_signals=signals,
                votes=dict(Counter(s.direction for s in signals)),
                weighted_scores={},
                agreement_ratio=1.0,
                is_consensus=True,
                reasoning=f"All {len(signals)} plugins agree on {direction}",
                consensus_mode=ConsensusMode.ALL_REQUIRED,
            )
        
        return ConsensusResult(
            direction="HOLD",
            confidence=0,
            participating_signals=signals,
            votes=dict(Counter(s.direction for s in signals)),
            weighted_scores={},
            agreement_ratio=0,
            is_consensus=False,
            reasoning=f"Disagreement: {directions}",
            consensus_mode=ConsensusMode.ALL_REQUIRED,
        )
    
    def _any_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Any single signal can trigger a trade"""
        if not signals:
            return ConsensusResult(
                direction="HOLD",
                confidence=0,
                participating_signals=[],
                votes={},
                weighted_scores={},
                agreement_ratio=0,
                is_consensus=False,
                reasoning="No signals available",
                consensus_mode=ConsensusMode.ANY,
            )
        
        # Use highest confidence signal
        best = max(signals, key=lambda s: s.confidence)
        
        return ConsensusResult(
            direction=best.direction,
            confidence=best.confidence,
            participating_signals=[best],
            votes={best.direction: 1},
            weighted_scores={best.direction: 1.0},
            agreement_ratio=1.0,
            is_consensus=True,
            reasoning=f"Any mode: {best.plugin_name} signal selected",
            consensus_mode=ConsensusMode.ANY,
        )
    
    def _threshold_consensus(self, signals: List[Signal]) -> ConsensusResult:
        """Threshold-based consensus"""
        weighted = self._calculate_signal_weights(signals)
        
        total_weight = sum(ws.weight for ws in weighted)
        
        scores = {"CALL": 0.0, "PUT": 0.0}
        for ws in weighted:
            if ws.signal.direction in scores:
                scores[ws.signal.direction] += ws.weight
        
        winner = max(scores, key=scores.get)
        agreement = scores[winner] / total_weight if total_weight > 0 else 0
        
        is_consensus = agreement >= self._config.min_agreement
        
        return ConsensusResult(
            direction=winner if is_consensus or self._config.allow_hold else "HOLD",
            confidence=min(agreement * 100, 100),
            participating_signals=signals,
            votes={},
            weighted_scores=scores,
            agreement_ratio=agreement,
            is_consensus=is_consensus,
            reasoning=f"Threshold: {winner} has {agreement:.0%} ({'passes' if is_consensus else 'fails'} {self._config.min_agreement:.0%} threshold)",
            consensus_mode=ConsensusMode.THRESHOLD,
        )
    
    def on_trade_executed(self, result: ConsensusResult) -> None:
        """Called when a trade is executed from consensus"""
        self._last_trade_time = datetime.utcnow()
    
    def get_signal_history(
        self,
        limit: int = 100,
        direction: Optional[str] = None,
    ) -> List[ConsensusResult]:
        """Get historical consensus results"""
        history = self._signal_history[-limit:]
        
        if direction:
            history = [h for h in history if h.direction == direction]
        
        return history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        if not self._signal_history:
            return {
                "total_decisions": 0,
                "direction_breakdown": {},
                "average_agreement": 0,
                "consensus_rate": 0,
            }
        
        directions = Counter(h.direction for h in self._signal_history)
        total = len(self._signal_history)
        
        return {
            "total_decisions": total,
            "direction_breakdown": dict(directions),
            "average_agreement": sum(h.agreement_ratio for h in self._signal_history) / total,
            "consensus_rate": sum(1 for h in self._signal_history if h.is_consensus) / total,
            "current_mode": self._config.mode.value,
            "last_decision": self._signal_history[-1].to_dict() if self._signal_history else None,
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics"""
        self._signal_history.clear()
        self._last_trade_time = None
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            "config": self._config.to_dict(),
            "plugin_metrics": self._plugin_metrics,
            "statistics": self.get_statistics(),
        }
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore state from persistence"""
        if "config" in state:
            self._config = OrchestratorConfig.from_dict(state["config"])
        if "plugin_metrics" in state:
            self._plugin_metrics = state["plugin_metrics"]


def create_orchestrator(
    mode: ConsensusMode = ConsensusMode.WEIGHTED_HYBRID,
    **kwargs,
) -> StrategyOrchestrator:
    """Factory function to create a strategy orchestrator"""
    config = OrchestratorConfig(mode=mode, **kwargs)
    return StrategyOrchestrator(config=config)
