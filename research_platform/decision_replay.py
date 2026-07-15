"""
Decision Replay - Historical Trade Replay System

Complete decision replay system for analyzing historical trading decisions:
- Available information at decision time
- AI reasoning
- Model outputs
- Confidence levels
- Risk evaluation
- Execution decisions
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of trading decisions"""
    ENTRY = "entry"
    EXIT = "exit"
    SIZE_ADJUSTMENT = "size_adjustment"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    HOLD = "hold"
    SKIP = "skip"


class DecisionOutcome(Enum):
    """Outcome of a trading decision"""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"
    CANCELLED = "cancelled"


class ReplayStatus(Enum):
    """Replay session status"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class AvailableInformation:
    """Information available at decision time"""
    # Market data
    timestamp: datetime
    symbol: str
    price: float
    spread: float = 0.0
    volume: float = 0.0
    
    # Technical indicators
    indicators: Dict[str, float] = field(default_factory=dict)
    
    # Market regime
    regime: str = "unknown"
    regime_confidence: float = 0.0
    
    # Historical context
    recent_prices: List[float] = field(default_factory=list)
    recent_volatility: float = 0.0
    
    # Account state
    account_balance: float = 0.0
    current_positions: int = 0
    available_margin: float = 0.0
    
    # Time context
    time_of_day: str = ""
    day_of_week: str = ""
    is_market_open: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "price": self.price,
            "spread": self.spread,
            "volume": self.volume,
            "indicators": self.indicators,
            "regime": self.regime,
            "regime_confidence": self.regime_confidence,
            "recent_prices": self.recent_prices,
            "recent_volatility": self.recent_volatility,
            "account_balance": self.account_balance,
            "current_positions": self.current_positions,
            "available_margin": self.available_margin,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "is_market_open": self.is_market_open,
        }


@dataclass
class ModelOutput:
    """Output from AI/ML models"""
    model_name: str
    model_version: str
    
    # Predictions
    prediction: str  # "buy", "sell", "hold"
    confidence: float  # 0-100
    
    # Probabilities
    buy_probability: float = 0.0
    sell_probability: float = 0.0
    hold_probability: float = 0.0
    
    # Feature contributions
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Uncertainty
    uncertainty: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    
    # Metadata
    inference_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "buy_probability": self.buy_probability,
            "sell_probability": self.sell_probability,
            "hold_probability": self.hold_probability,
            "feature_contributions": self.feature_contributions,
            "uncertainty": self.uncertainty,
            "confidence_interval": self.confidence_interval,
            "inference_time_ms": self.inference_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RiskEvaluation:
    """Risk evaluation at decision time"""
    # Risk metrics
    risk_score: float = 0.0  # 0-100
    risk_level: str = "low"  # "low", "medium", "high"
    
    # Position sizing
    recommended_size: float = 0.0
    max_size: float = 0.0
    min_size: float = 0.0
    
    # Risk limits
    stop_loss_distance: float = 0.0
    take_profit_distance: float = 0.0
    risk_reward_ratio: float = 0.0
    
    # Exposure
    current_exposure: float = 0.0
    projected_exposure: float = 0.0
    margin_utilization: float = 0.0
    
    # Checks
    risk_checks_passed: bool = True
    risk_check_results: Dict[str, bool] = field(default_factory=dict)
    failed_check_reasons: List[str] = field(default_factory=list)
    
    # VaR
    value_at_risk: float = 0.0
    conditional_var: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "recommended_size": self.recommended_size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "stop_loss_distance": self.stop_loss_distance,
            "take_profit_distance": self.take_profit_distance,
            "risk_reward_ratio": self.risk_reward_ratio,
            "current_exposure": self.current_exposure,
            "projected_exposure": self.projected_exposure,
            "margin_utilization": self.margin_utilization,
            "risk_checks_passed": self.risk_checks_passed,
            "risk_check_results": self.risk_check_results,
            "failed_check_reasons": self.failed_check_reasons,
            "value_at_risk": self.value_at_risk,
            "conditional_var": self.conditional_var,
        }


@dataclass
class AIReasoning:
    """AI reasoning for the decision"""
    # Decision
    decision: DecisionType
    final_decision: str  # "trade", "abstain", "reject"
    
    # Reasoning process
    reasoning_chain: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)
    
    # Consensus
    analyzer_consensus: float = 0.0  # 0-100
    confidence_score: float = 0.0  # 0-100
    opportunity_score: float = 0.0  # 0-100
    
    # Alternative considerations
    alternative_decisions: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    
    # Historical comparison
    similar_past_decisions: int = 0
    similar_decisions_win_rate: float = 0.0
    
    # Recommendation
    recommendation: str = ""
    recommendation_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "final_decision": self.final_decision,
            "reasoning_chain": self.reasoning_chain,
            "key_factors": self.key_factors,
            "analyzer_consensus": self.analyzer_consensus,
            "confidence_score": self.confidence_score,
            "opportunity_score": self.opportunity_score,
            "alternative_decisions": self.alternative_decisions,
            "rejection_reasons": self.rejection_reasons,
            "similar_past_decisions": self.similar_past_decisions,
            "similar_decisions_win_rate": self.similar_decisions_win_rate,
            "recommendation": self.recommendation,
            "recommendation_confidence": self.recommendation_confidence,
        }


@dataclass
class ExecutionDecision:
    """Final execution decision"""
    # Action
    action: str  # "buy", "sell", "hold", "skip"
    direction: str  # "long", "short"
    
    # Execution details
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_size: float = 0.0
    
    # Timing
    execution_delay_ms: float = 0.0
    slippage_estimate: float = 0.0
    
    # Override info
    was_overridden: bool = False
    override_reason: str = ""
    
    # Post-decision
    order_id: str = ""
    filled: bool = False
    fill_price: float = 0.0
    fill_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "execution_delay_ms": self.execution_delay_ms,
            "slippage_estimate": self.slippage_estimate,
            "was_overridden": self.was_overridden,
            "override_reason": self.override_reason,
            "order_id": self.order_id,
            "filled": self.filled,
            "fill_price": self.fill_price,
            "fill_time": self.fill_time.isoformat() if self.fill_time else None,
        }


@dataclass
class DecisionSnapshot:
    """Complete snapshot of a trading decision"""
    snapshot_id: str
    trade_id: str
    
    # Timing (required first)
    decision_time: datetime
    
    # Components (required, no defaults)
    available_information: AvailableInformation
    risk_evaluation: RiskEvaluation
    ai_reasoning: AIReasoning
    execution_decision: ExecutionDecision
    
    # Optional timing
    market_close_time: Optional[datetime] = None
    
    # Optional components
    model_outputs: List[ModelOutput] = field(default_factory=list)
    
    # Outcome (filled after trade closes)
    outcome: DecisionOutcome = DecisionOutcome.PENDING
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration_seconds: float = 0.0
    
    # Analysis
    was_correct: bool = False
    missed_opportunity: bool = False
    unexpected_loss: bool = False
    
    # Metadata
    session_id: str = ""
    strategy_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "trade_id": self.trade_id,
            "decision_time": self.decision_time.isoformat(),
            "market_close_time": self.market_close_time.isoformat() if self.market_close_time else None,
            "available_information": self.available_information.to_dict(),
            "model_outputs": [m.to_dict() for m in self.model_outputs],
            "risk_evaluation": self.risk_evaluation.to_dict(),
            "ai_reasoning": self.ai_reasoning.to_dict(),
            "execution_decision": self.execution_decision.to_dict(),
            "outcome": self.outcome.value,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "duration_seconds": self.duration_seconds,
            "was_correct": self.was_correct,
            "missed_opportunity": self.missed_opportunity,
            "unexpected_loss": self.unexpected_loss,
            "session_id": self.session_id,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TradeReplay:
    """Complete replay of a trade with all decisions"""
    replay_id: str
    trade_id: str
    
    # Timeline (required first)
    entry_time: datetime
    
    # Entry snapshot (required)
    entry_snapshot: DecisionSnapshot
    
    # Optional timeline
    exit_time: Optional[datetime] = None
    
    # Intermediate snapshots (for held positions)
    intermediate_snapshots: List[DecisionSnapshot] = field(default_factory=list)
    
    # Exit snapshot
    exit_snapshot: Optional[DecisionSnapshot] = None
    
    # Trade result
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    net_pnl: float = 0.0
    
    # Analysis
    decision_quality: str = "unknown"  # "excellent", "good", "poor", "random"
    lessons_learned: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "trade_id": self.trade_id,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "entry_snapshot": self.entry_snapshot.to_dict(),
            "intermediate_snapshots": [s.to_dict() for s in self.intermediate_snapshots],
            "exit_snapshot": self.exit_snapshot.to_dict() if self.exit_snapshot else None,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "commission": self.commission,
            "net_pnl": self.net_pnl,
            "decision_quality": self.decision_quality,
            "lessons_learned": self.lessons_learned,
        }


class DecisionReplayEngine:
    """
    Decision Replay Engine for analyzing historical trading decisions.
    
    Features:
    - Complete decision capture
    - Replay with adjustable speed
    - Analysis tools
    - Learning extraction
    - Decision quality scoring
    """
    
    def __init__(self, storage_path: str = "data/decision_replay"):
        self._storage_path = storage_path
        self._snapshots: Dict[str, DecisionSnapshot] = {}
        self._replays: Dict[str, TradeReplay] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_data()
    
    def _load_data(self) -> None:
        """Load replay data"""
        data_file = f"{self._storage_path}/replays.json"
        
        try:
            if os.path.exists(data_file):
                with open(data_file, "r") as f:
                    data = json.load(f)
                
                # Load snapshots
                for snap_data in data.get("snapshots", []):
                    snap_data["available_information"]["timestamp"] = datetime.fromisoformat(
                        snap_data["available_information"]["timestamp"]
                    )
                    
                    for m in snap_data.get("model_outputs", []):
                        m["timestamp"] = datetime.fromisoformat(m["timestamp"])
                    
                    snap = DecisionSnapshot(**snap_data)
                    self._snapshots[snap.snapshot_id] = snap
                
                logger.info(f"Loaded {len(self._snapshots)} decision snapshots")
        except Exception as e:
            logger.warning(f"Could not load replay data: {e}")
    
    def _save_data(self) -> None:
        """Save replay data"""
        data_file = f"{self._storage_path}/replays.json"
        
        data = {
            "snapshots": [s.to_dict() for s in self._snapshots.values()],
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(data_file, "w") as f:
            json.dump(data, f, indent=2)
    
    # Snapshot Management
    def create_snapshot(
        self,
        trade_id: str,
        available_information: AvailableInformation,
        model_outputs: List[ModelOutput],
        risk_evaluation: RiskEvaluation,
        ai_reasoning: AIReasoning,
        execution_decision: ExecutionDecision,
        session_id: str = "",
        strategy_id: str = "",
    ) -> DecisionSnapshot:
        """Create a complete decision snapshot"""
        snapshot = DecisionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            trade_id=trade_id,
            decision_time=available_information.timestamp,
            available_information=available_information,
            model_outputs=model_outputs,
            risk_evaluation=risk_evaluation,
            ai_reasoning=ai_reasoning,
            execution_decision=execution_decision,
            session_id=session_id,
            strategy_id=strategy_id,
        )
        
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._save_data()
        
        return snapshot
    
    def update_snapshot_outcome(
        self,
        snapshot_id: str,
        outcome: DecisionOutcome,
        pnl: float = 0.0,
        pnl_pct: float = 0.0,
        duration_seconds: float = 0.0,
    ) -> bool:
        """Update snapshot with trade outcome"""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        
        snapshot.outcome = outcome
        snapshot.pnl = pnl
        snapshot.pnl_pct = pnl_pct
        snapshot.duration_seconds = duration_seconds
        
        # Analyze correctness
        snapshot.was_correct = (
            (outcome == DecisionOutcome.WIN and snapshot.execution_decision.action in ["buy", "sell"]) or
            (outcome == DecisionOutcome.LOSS and snapshot.execution_decision.action == "skip")
        )
        
        snapshot.unexpected_loss = (
            outcome == DecisionOutcome.LOSS and
            snapshot.ai_reasoning.confidence_score > 70
        )
        
        self._save_data()
        return True
    
    def get_snapshot(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Get a snapshot by ID"""
        return self._snapshots.get(snapshot_id)
    
    # Replay Management
    def create_replay(
        self,
        trade_id: str,
        entry_snapshot: DecisionSnapshot,
        exit_snapshot: Optional[DecisionSnapshot] = None,
        intermediate_snapshots: Optional[List[DecisionSnapshot]] = None,
    ) -> TradeReplay:
        """Create a trade replay"""
        replay = TradeReplay(
            replay_id=str(uuid.uuid4()),
            trade_id=trade_id,
            entry_time=entry_snapshot.decision_time,
            entry_snapshot=entry_snapshot,
            exit_snapshot=exit_snapshot,
            intermediate_snapshots=intermediate_snapshots or [],
        )
        
        if exit_snapshot:
            replay.exit_time = exit_snapshot.decision_time
            replay.pnl = exit_snapshot.pnl
            replay.pnl_pct = exit_snapshot.pnl_pct
        
        self._replays[replay.replay_id] = replay
        return replay
    
    def get_replay(self, replay_id: str) -> Optional[TradeReplay]:
        """Get a replay by ID"""
        return self._replays.get(replay_id)
    
    # Analysis
    def analyze_decision_quality(
        self,
        snapshot_id: str,
    ) -> Dict[str, Any]:
        """Analyze the quality of a decision"""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return {}
        
        analysis = {
            "snapshot_id": snapshot_id,
            "decision_time": snapshot.decision_time.isoformat(),
            "components": {},
            "overall_score": 0.0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }
        
        # Analyze confidence calibration
        if snapshot.outcome != DecisionOutcome.PENDING:
            confidence = snapshot.ai_reasoning.confidence_score
            actual_win = snapshot.outcome == DecisionOutcome.WIN
            
            # Well-calibrated if high confidence + win or low confidence + loss
            well_calibrated = (confidence > 70 and actual_win) or (confidence < 50 and not actual_win)
            analysis["components"]["confidence_calibration"] = {
                "score": 100 if well_calibrated else 0,
                "confidence": confidence,
                "actual_win": actual_win,
            }
        
        # Analyze risk evaluation accuracy
        risk_evaluated = snapshot.risk_evaluation.risk_score > 0
        analysis["components"]["risk_evaluation"] = {
            "score": 80 if risk_evaluated else 20,
            "risk_score": snapshot.risk_evaluation.risk_score,
            "passed": snapshot.risk_evaluation.risk_checks_passed,
        }
        
        # Analyze model consensus
        if snapshot.model_outputs:
            predictions = [m.prediction for m in snapshot.model_outputs]
            consensus = max(set(predictions), key=predictions.count) if predictions else "unknown"
            consensus_ratio = predictions.count(consensus) / len(predictions)
            
            analysis["components"]["model_consensus"] = {
                "score": int(consensus_ratio * 100),
                "consensus": consensus,
                "agreement_ratio": consensus_ratio,
            }
        
        # Analyze reasoning quality
        reasoning_length = len(snapshot.ai_reasoning.reasoning_chain)
        analysis["components"]["reasoning_quality"] = {
            "score": min(100, reasoning_length * 10),
            "reasoning_steps": reasoning_length,
        }
        
        # Overall score
        scores = [c["score"] for c in analysis["components"].values()]
        analysis["overall_score"] = sum(scores) / len(scores) if scores else 0
        
        # Strengths and weaknesses
        for component, data in analysis["components"].items():
            if data["score"] >= 80:
                analysis["strengths"].append(f"Strong {component}")
            elif data["score"] < 50:
                analysis["weaknesses"].append(f"Weak {component}")
        
        # Recommendations
        if analysis["confidence_calibration"]["score"] < 50:
            analysis["recommendations"].append("Improve confidence calibration")
        if analysis["reasoning_quality"]["score"] < 50:
            analysis["recommendations"].append("Enhance decision reasoning")
        
        return analysis
    
    def compare_decisions(
        self,
        snapshot_ids: List[str],
    ) -> Dict[str, Any]:
        """Compare multiple decisions"""
        snapshots = [self._snapshots.get(sid) for sid in snapshot_ids]
        snapshots = [s for s in snapshots if s]
        
        if not snapshots:
            return {}
        
        comparison = {
            "num_decisions": len(snapshots),
            "decision_types": {},
            "confidence_stats": {},
            "outcome_stats": {},
            "risk_stats": {},
        }
        
        # Decision types
        for snap in snapshots:
            dtype = snap.ai_reasoning.final_decision
            comparison["decision_types"][dtype] = comparison["decision_types"].get(dtype, 0) + 1
        
        # Confidence statistics
        confidences = [s.ai_reasoning.confidence_score for s in snapshots]
        comparison["confidence_stats"] = {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
        }
        
        # Outcome statistics
        outcomes = [s.outcome for s in snapshots if s.outcome != DecisionOutcome.PENDING]
        if outcomes:
            wins = sum(1 for o in outcomes if o == DecisionOutcome.WIN)
            comparison["outcome_stats"] = {
                "total_evaluated": len(outcomes),
                "wins": wins,
                "losses": len(outcomes) - wins,
                "win_rate": wins / len(outcomes) * 100 if outcomes else 0,
            }
        
        # Risk statistics
        risk_scores = [s.risk_evaluation.risk_score for s in snapshots]
        comparison["risk_stats"] = {
            "mean": sum(risk_scores) / len(risk_scores),
            "passed_rate": sum(1 for r in risk_scores if r < 50) / len(risk_scores) * 100,
        }
        
        return comparison
    
    def extract_lessons(
        self,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> Dict[str, Any]:
        """Extract lessons from recent decisions"""
        snapshots = list(self._snapshots.values())
        
        # Filter by date range
        if date_range:
            start, end = date_range
            snapshots = [
                s for s in snapshots
                if start <= s.decision_time <= end
            ]
        
        # Only consider decided trades
        decided = [s for s in snapshots if s.outcome != DecisionOutcome.PENDING]
        
        lessons = {
            "total_decisions": len(decided),
            "lessons": [],
            "patterns": [],
            "improvements": [],
        }
        
        # Analyze unexpected losses
        unexpected_losses = [s for s in decided if s.unexpected_loss]
        if unexpected_losses:
            avg_confidence = sum(s.ai_reasoning.confidence_score for s in unexpected_losses) / len(unexpected_losses)
            lessons["lessons"].append({
                "type": "unexpected_loss",
                "count": len(unexpected_losses),
                "avg_confidence": avg_confidence,
                "lesson": "High confidence does not guarantee success",
            })
        
        # Analyze missed opportunities
        skipped_good = [
            s for s in decided
            if s.execution_decision.action == "skip"
            and s.outcome == DecisionOutcome.WIN
        ]
        if skipped_good:
            lessons["lessons"].append({
                "type": "missed_opportunity",
                "count": len(skipped_good),
                "lesson": "Some winning opportunities were skipped",
            })
        
        # Analyze pattern in wins vs losses
        wins = [s for s in decided if s.outcome == DecisionOutcome.WIN]
        losses = [s for s in decided if s.outcome == DecisionOutcome.LOSS]
        
        if wins and losses:
            # Confidence difference
            win_conf = sum(s.ai_reasoning.confidence_score for s in wins) / len(wins)
            loss_conf = sum(s.ai_reasoning.confidence_score for s in losses) / len(losses)
            
            if win_conf > loss_conf + 10:
                lessons["patterns"].append({
                    "pattern": "confidence_correlates_with_success",
                    "description": f"Wins had avg confidence {win_conf:.1f} vs losses {loss_conf:.1f}",
                })
        
        # Improvement suggestions
        if len(unexpected_losses) > len(decided) * 0.2:
            lessons["improvements"].append("Review high-confidence loss decisions for patterns")
        
        if len(skipped_good) > len(decided) * 0.1:
            lessons["improvements"].append("Analyze skipped trades that would have won")
        
        return lessons
    
    # Export
    def export_snapshot(
        self,
        snapshot_id: str,
        format: str = "json",
    ) -> Optional[str]:
        """Export a snapshot"""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return None
        
        if format == "json":
            return json.dumps(snapshot.to_dict(), indent=2)
        
        return None
    
    def export_replay_narrative(
        self,
        replay_id: str,
    ) -> str:
        """Export a replay as a human-readable narrative"""
        replay = self._replays.get(replay_id)
        if not replay:
            return ""
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"TRADE REPLAY: {replay.trade_id}")
        lines.append("=" * 80)
        lines.append("")
        
        # Entry
        entry = replay.entry_snapshot
        lines.append("ENTRY DECISION")
        lines.append("-" * 40)
        lines.append(f"Time: {entry.decision_time}")
        lines.append(f"Symbol: {entry.available_information.symbol}")
        lines.append(f"Price: {entry.available_information.price}")
        lines.append(f"Regime: {entry.available_information.regime}")
        lines.append("")
        
        # Model outputs
        lines.append("MODEL OUTPUTS:")
        for model in entry.model_outputs:
            lines.append(f"  - {model.model_name}: {model.prediction} ({model.confidence}%)")
        lines.append("")
        
        # AI Reasoning
        lines.append("AI REASONING:")
        for step in entry.ai_reasoning.reasoning_chain:
            lines.append(f"  - {step}")
        lines.append(f"Final Decision: {entry.ai_reasoning.final_decision}")
        lines.append(f"Confidence: {entry.ai_reasoning.confidence_score}%")
        lines.append("")
        
        # Risk
        lines.append("RISK EVALUATION:")
        lines.append(f"  Risk Score: {entry.risk_evaluation.risk_score}")
        lines.append(f"  Risk Level: {entry.risk_evaluation.risk_level}")
        lines.append(f"  Size: {entry.execution_decision.position_size}")
        lines.append(f"  Stop Loss: {entry.execution_decision.stop_loss}")
        lines.append("")
        
        # Execution
        lines.append("EXECUTION:")
        lines.append(f"  Action: {entry.execution_decision.action}")
        lines.append(f"  Direction: {entry.execution_decision.direction}")
        lines.append(f"  Entry Price: {entry.execution_decision.entry_price}")
        lines.append("")
        
        # Outcome
        if replay.exit_snapshot:
            lines.append("EXIT & OUTCOME")
            lines.append("-" * 40)
            lines.append(f"Exit Time: {replay.exit_snapshot.decision_time}")
            lines.append(f"P&L: ${replay.pnl:.2f} ({replay.pnl_pct:.2f}%)")
            lines.append(f"Outcome: {replay.exit_snapshot.outcome.value}")
            lines.append("")
        
        # Analysis
        lines.append("DECISION QUALITY")
        lines.append("-" * 40)
        lines.append(f"Quality Rating: {replay.decision_quality}")
        if replay.lessons_learned:
            lines.append("Lessons Learned:")
            for lesson in replay.lessons_learned:
                lines.append(f"  - {lesson}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


import os
