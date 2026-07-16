"""
Decision Science Core
===================

Core classes for separating prediction from decision-making.
"""

import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import math
import logging

logger = logging.getLogger(__name__)


class DecisionAction(Enum):
    """Possible decision actions"""
    EXECUTE = "execute"  # Take the trade
    REJECT = "reject"    # Skip the trade
    WAIT = "wait"       # Wait for better opportunity


@dataclass
class Prediction:
    """
    Prediction from the AI model.
    
    Separated from decision to enable post-hoc analysis.
    """
    prediction_id: str
    opportunity_id: str
    predicted_direction: str  # "up", "down", "sideways"
    predicted_magnitude: float  # Expected % move
    predicted_confidence: float  # 0.0 - 1.0
    predicted_probability: float  # Probability of success
    features_used: List[str] = field(default_factory=list)
    model_version: str = ""
    inference_time_ms: float = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "opportunity_id": self.opportunity_id,
            "predicted_direction": self.predicted_direction,
            "predicted_magnitude": self.predicted_magnitude,
            "predicted_confidence": self.predicted_confidence,
            "predicted_probability": self.predicted_probability,
            "features_used": self.features_used,
            "model_version": self.model_version,
            "inference_time_ms": self.inference_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class Decision:
    """
    Decision based on prediction and other factors.
    
    Separate from prediction to enable independent evaluation.
    """
    decision_id: str
    opportunity_id: str
    action: DecisionAction
    reason: str
    confidence: float  # 0.0 - 1.0
    expected_value: float
    risk_adjusted_score: float
    opportunity_cost: float
    capital_required: float
    timestamp: float = field(default_factory=time.time)
    rejected_alternatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "opportunity_id": self.opportunity_id,
            "action": self.action.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "risk_adjusted_score": self.risk_adjusted_score,
            "opportunity_cost": self.opportunity_cost,
            "capital_required": self.capital_required,
            "timestamp": self.timestamp,
        }


@dataclass
class Opportunity:
    """
    Trading opportunity with full context.
    """
    opportunity_id: str
    symbol: str
    market_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    window_open: float = field(default_factory=time.time)
    window_close: Optional[float] = None
    
    # Raw signals
    signals: Dict[str, float] = field(default_factory=dict)
    
    # Prediction (populated by analyzer)
    prediction: Optional[Prediction] = None
    
    # Decision (populated by analyzer)
    decision: Optional[Decision] = None
    
    # Outcome (populated after resolution)
    actual_direction: Optional[str] = None
    actual_magnitude: Optional[float] = None
    actual_pnl: Optional[float] = None
    resolved_at: Optional[float] = None
    
    # Analysis metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_resolved(self) -> bool:
        return self.resolved_at is not None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "prediction": self.prediction.to_dict() if self.prediction else None,
            "decision": self.decision.to_dict() if self.decision else None,
            "actual_direction": self.actual_direction,
            "actual_magnitude": self.actual_magnitude,
            "actual_pnl": self.actual_pnl,
            "resolved_at": self.resolved_at,
            "metrics": self.metrics,
        }


@dataclass
class DecisionQualityScore:
    """
    Aggregated decision quality score.
    """
    score_id: str
    timestamp: float
    overall_score: float  # 0.0 - 1.0
    
    # Component scores
    prediction_quality: float
    decision_quality: float
    expected_value_score: float
    capital_efficiency_score: float
    opportunity_cost_score: float
    abstention_quality_score: float
    confidence_calibration_score: float
    regret_score: float  # Lower is better
    
    # Aggregate metrics
    total_opportunities: int
    executed_trades: int
    rejected_trades: int
    waited_trades: int
    
    # Performance
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id": self.score_id,
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "prediction_quality": self.prediction_quality,
            "decision_quality": self.decision_quality,
            "expected_value_score": self.expected_value_score,
            "capital_efficiency_score": self.capital_efficiency_score,
            "opportunity_cost_score": self.opportunity_cost_score,
            "abstention_quality_score": self.abstention_quality_score,
            "confidence_calibration_score": self.confidence_calibration_score,
            "regret_score": self.regret_score,
            "total_opportunities": self.total_opportunities,
            "executed_trades": self.executed_trades,
            "rejected_trades": self.rejected_trades,
            "waited_trades": self.waited_trades,
            "total_pnl": self.total_pnl,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
        }


class OpportunityAnalyzer:
    """
    Analyzes opportunities and makes decisions.
    
    Separates prediction (AI model output) from decision (trade execution choice).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self._prediction_history: List[Prediction] = []
        self._decision_history: List[Decision] = []
        self._opportunity_history: List[Opportunity] = []
        
        # Thresholds
        self.min_confidence = self.config.get("min_confidence", 0.6)
        self.min_expected_value = self.config.get("min_expected_value", 0.01)
        self.min_probability = self.config.get("min_probability", 0.55)
        self.abstention_threshold = self.config.get("abstention_threshold", 0.4)
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "min_confidence": 0.6,
            "min_expected_value": 0.01,
            "min_probability": 0.55,
            "abstention_threshold": 0.4,
            "risk_free_rate": 0.02,  # Annual
            "position_size_pct": 0.1,  # % of capital per trade
            "max_position_size": 100000,
        }
    
    def predict(self, opportunity: Opportunity, model_fn: Callable) -> Prediction:
        """
        Generate prediction using the model.
        
        This is separate from decision to enable:
        - Post-hoc analysis of prediction quality
        - Comparison of predictions to actual outcomes
        - Calibration improvement
        """
        start_time = time.time()
        
        # Call the model
        raw_output = model_fn(opportunity)
        
        inference_time = (time.time() - start_time) * 1000
        
        prediction = Prediction(
            prediction_id=self._generate_id(),
            opportunity_id=opportunity.opportunity_id,
            predicted_direction=raw_output.get("direction", "unknown"),
            predicted_magnitude=raw_output.get("magnitude", 0.0),
            predicted_confidence=raw_output.get("confidence", 0.5),
            predicted_probability=raw_output.get("probability", 0.5),
            features_used=raw_output.get("features", []),
            model_version=raw_output.get("model_version", "unknown"),
            inference_time_ms=inference_time,
        )
        
        opportunity.prediction = prediction
        self._prediction_history.append(prediction)
        
        return prediction
    
    def decide(self, opportunity: Opportunity) -> Decision:
        """
        Make a decision based on prediction and context.
        
        Separated from prediction to enable:
        - Rule-based overrides
        - Risk management checks
        - Opportunity cost consideration
        - Post-hoc decision quality analysis
        """
        prediction = opportunity.prediction
        if not prediction:
            raise ValueError("Must call predict() before decide()")
        
        # Calculate metrics
        ev = self._calculate_expected_value(opportunity)
        risk_score = self._calculate_risk_adjusted_score(opportunity)
        opp_cost = self._calculate_opportunity_cost(opportunity)
        capital_req = self._calculate_capital_requirement(opportunity)
        
        # Decision logic
        action, reason = self._make_decision(prediction, ev, risk_score, opp_cost)
        
        decision = Decision(
            decision_id=self._generate_id(),
            opportunity_id=opportunity.opportunity_id,
            action=action,
            reason=reason,
            confidence=prediction.predicted_confidence,
            expected_value=ev,
            risk_adjusted_score=risk_score,
            opportunity_cost=opp_cost,
            capital_required=capital_req,
        )
        
        opportunity.decision = decision
        self._decision_history.append(decision)
        
        return decision
    
    def analyze(self, opportunity: Opportunity, model_fn: Optional[Callable] = None) -> Opportunity:
        """
        Full analysis: predict + decide + analyze metrics.
        """
        if model_fn and not opportunity.prediction:
            self.predict(opportunity, model_fn)
        
        if opportunity.prediction and not opportunity.decision:
            self.decide(opportunity)
        
        # Calculate all metrics
        opportunity.metrics = self._calculate_all_metrics(opportunity)
        
        self._opportunity_history.append(opportunity)
        
        return opportunity
    
    def resolve(self, opportunity: Opportunity, outcome: Dict[str, Any]) -> None:
        """Resolve an opportunity with actual outcome"""
        opportunity.actual_direction = outcome.get("direction")
        opportunity.actual_magnitude = outcome.get("magnitude")
        opportunity.actual_pnl = outcome.get("pnl", 0)
        opportunity.resolved_at = time.time()
        
        # Update metrics with actual results
        opportunity.metrics["actual_pnl"] = opportunity.actual_pnl
        opportunity.metrics["was_correct"] = (
            opportunity.prediction and 
            opportunity.actual_direction == opportunity.prediction.predicted_direction
        ) if opportunity.prediction else False
    
    def _calculate_expected_value(self, opp: Opportunity) -> float:
        """Calculate expected value of the opportunity"""
        if not opp.prediction:
            return 0.0
        
        p = opp.prediction.predicted_probability
        magnitude = opp.prediction.predicted_magnitude
        
        # EV = P(success) * gain - P(failure) * loss
        # Assuming symmetric risk (can be configured)
        win_rate = p
        loss_rate = 1 - p
        avg_gain = magnitude
        avg_loss = self.config.get("avg_loss_pct", 0.005)  # Default 0.5%
        
        ev = (win_rate * avg_gain) - (loss_rate * avg_loss)
        return ev
    
    def _calculate_risk_adjusted_score(self, opp: Opportunity) -> float:
        """Calculate risk-adjusted score"""
        ev = self._calculate_expected_value(opp)
        volatility = opp.market_data.get("volatility", 0.02)
        
        # Sharpe-like ratio
        risk_free = self.config.get("risk_free_rate", 0.02) / 252  # Daily
        sharpe = (ev - risk_free) / (volatility + 0.001)
        
        # Normalize to 0-1
        return max(0, min(1, (sharpe + 1) / 3))
    
    def _calculate_opportunity_cost(self, opp: Opportunity) -> float:
        """Calculate opportunity cost of not taking alternative actions"""
        if not opp.prediction:
            return 0.0
        
        # Cost of rejecting vs executing
        rejected_ev = 0.0  # Not taking the trade
        taken_ev = self._calculate_expected_value(opp)
        
        # Opportunity cost is the difference
        return taken_ev - rejected_ev
    
    def _calculate_capital_requirement(self, opp: Opportunity) -> float:
        """Calculate capital required for this trade"""
        position_size = self.config.get("position_size_pct", 0.1)
        price = opp.market_data.get("price", 100)
        
        # Simplified calculation
        return price * position_size * 100  # Assuming 100 units
    
    def _make_decision(
        self, 
        prediction: Prediction, 
        ev: float, 
        risk_score: float,
        opp_cost: float
    ) -> tuple[DecisionAction, str]:
        """Make decision based on prediction and metrics"""
        
        # Low confidence - abstain
        if prediction.predicted_confidence < self.abstention_threshold:
            return DecisionAction.REJECT, "Confidence below threshold"
        
        # Low expected value - reject
        if ev < self.min_expected_value:
            return DecisionAction.REJECT, f"Expected value {ev:.4f} below minimum"
        
        # Low probability - wait for better opportunity
        if prediction.predicted_probability < self.min_probability:
            return DecisionAction.WAIT, f"Probability {prediction.predicted_probability:.2f} below threshold"
        
        # High risk - reject
        if risk_score < 0.3:
            return DecisionAction.REJECT, f"Risk-adjusted score {risk_score:.2f} too low"
        
        # Good opportunity - execute
        return DecisionAction.EXECUTE, f"EV={ev:.4f}, RiskScore={risk_score:.2f}"
    
    def _calculate_all_metrics(self, opp: Opportunity) -> Dict[str, float]:
        """Calculate all analysis metrics for an opportunity"""
        metrics = {}
        
        if opp.prediction:
            metrics["prediction_confidence"] = opp.prediction.predicted_confidence
            metrics["prediction_probability"] = opp.prediction.predicted_probability
            metrics["prediction_magnitude"] = opp.prediction.predicted_magnitude
        
        if opp.decision:
            metrics["expected_value"] = opp.decision.expected_value
            metrics["risk_adjusted_score"] = opp.decision.risk_adjusted_score
            metrics["opportunity_cost"] = opp.decision.opportunity_cost
            metrics["capital_required"] = opp.decision.capital_required
        
        # Additional metrics
        metrics["volatility"] = opp.market_data.get("volatility", 0.02)
        metrics["volume"] = opp.market_data.get("volume", 0)
        metrics["spread"] = opp.market_data.get("spread", 0)
        
        return metrics
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
    
    def get_opportunities(self, limit: int = 100) -> List[Opportunity]:
        """Get recent opportunities"""
        return sorted(self._opportunity_history, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_unresolved(self) -> List[Opportunity]:
        """Get unresolved opportunities"""
        return [o for o in self._opportunity_history if not o.is_resolved()]
    
    def calculate_decision_quality_score(self) -> DecisionQualityScore:
        """Calculate aggregated decision quality score"""
        resolved = [o for o in self._opportunity_history if o.is_resolved()]
        
        if not resolved:
            return self._empty_quality_score()
        
        # Calculate component scores
        pred_quality = self._calculate_prediction_quality(resolved)
        dec_quality = self._calculate_decision_quality(resolved)
        ev_score = self._calculate_ev_score(resolved)
        cap_eff = self._calculate_capital_efficiency(resolved)
        opp_cost_score = self._calculate_opp_cost_score(resolved)
        abstain_score = self._calculate_abstention_quality(resolved)
        calib_score = self._calculate_confidence_calibration(resolved)
        regret = self._calculate_regret_score(resolved)
        
        # Performance metrics
        pnls = [o.actual_pnl for o in resolved if o.actual_pnl is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_pnl = sum(pnls)
        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 0
        
        # Calculate Sharpe ratio
        sharpe = self._calculate_sharpe(pnls)
        max_dd = self._calculate_max_drawdown(pnls)
        
        # Overall score (weighted average)
        overall = (
            pred_quality * 0.15 +
            dec_quality * 0.20 +
            ev_score * 0.20 +
            cap_eff * 0.10 +
            opp_cost_score * 0.10 +
            abstain_score * 0.10 +
            calib_score * 0.10 -
            regret * 0.05
        )
        
        return DecisionQualityScore(
            score_id=self._generate_id(),
            timestamp=time.time(),
            overall_score=max(0, min(1, overall)),
            prediction_quality=pred_quality,
            decision_quality=dec_quality,
            expected_value_score=ev_score,
            capital_efficiency_score=cap_eff,
            opportunity_cost_score=opp_cost_score,
            abstention_quality_score=abstain_score,
            confidence_calibration_score=calib_score,
            regret_score=regret,
            total_opportunities=len(resolved),
            executed_trades=len([o for o in resolved if o.decision and o.decision.action == DecisionAction.EXECUTE]),
            rejected_trades=len([o for o in resolved if o.decision and o.decision.action == DecisionAction.REJECT]),
            waited_trades=len([o for o in resolved if o.decision and o.decision.action == DecisionAction.WAIT]),
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
        )
    
    def _empty_quality_score(self) -> DecisionQualityScore:
        """Return empty quality score"""
        return DecisionQualityScore(
            score_id=self._generate_id(),
            timestamp=time.time(),
            overall_score=0.0,
            prediction_quality=0.0,
            decision_quality=0.0,
            expected_value_score=0.0,
            capital_efficiency_score=0.0,
            opportunity_cost_score=0.0,
            abstention_quality_score=0.0,
            confidence_calibration_score=0.0,
            regret_score=0.0,
            total_opportunities=0,
            executed_trades=0,
            rejected_trades=0,
            waited_trades=0,
            total_pnl=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
        )
    
    def _calculate_prediction_quality(self, resolved: List[Opportunity]) -> float:
        """Calculate prediction quality score"""
        correct = sum(1 for o in resolved if o.metrics.get("was_correct", False))
        return correct / len(resolved) if resolved else 0.0
    
    def _calculate_decision_quality(self, resolved: List[Opportunity]) -> float:
        """Calculate decision quality score"""
        # Good decision: execute when correct, reject when incorrect
        executed = [o for o in resolved if o.decision and o.decision.action == DecisionAction.EXECUTE]
        
        if not executed:
            return 0.5  # Neutral if no executions
        
        correct_executions = sum(1 for o in executed if o.metrics.get("was_correct", False))
        return correct_executions / len(executed)
    
    def _calculate_ev_score(self, resolved: List[Opportunity]) -> float:
        """Calculate expected value score"""
        executed = [o for o in resolved if o.decision and o.decision.action == DecisionAction.EXECUTE]
        if not executed:
            return 0.5
        
        positive_ev = sum(1 for o in executed if (o.actual_pnl or 0) > 0)
        return positive_ev / len(executed)
    
    def _calculate_capital_efficiency(self, resolved: List[Opportunity]) -> float:
        """Calculate capital efficiency score"""
        executed = [o for o in resolved if o.decision and o.decision.action == DecisionAction.EXECUTE]
        if not executed:
            return 0.5
        
        # Higher PnL per capital is better
        total_pnl = sum(o.actual_pnl or 0 for o in executed)
        total_capital = sum(o.decision.capital_required for o in executed)
        
        if total_capital == 0:
            return 0.5
        
        efficiency = total_pnl / total_capital
        return max(0, min(1, (efficiency + 0.1) / 0.2))  # Normalize
    
    def _calculate_opp_cost_score(self, resolved: List[Opportunity]) -> float:
        """Calculate opportunity cost score"""
        rejected = [o for o in resolved if o.decision and o.decision.action == DecisionAction.REJECT]
        if not rejected:
            return 0.5
        
        # Good rejection: when opportunity was actually bad
        bad_opps_rejected = sum(1 for o in rejected if (o.actual_pnl or 0) <= 0)
        return bad_opps_rejected / len(rejected)
    
    def _calculate_abstention_quality(self, resolved: List[Opportunity]) -> float:
        """Calculate abstention quality score"""
        waited = [o for o in resolved if o.decision and o.decision.action == DecisionAction.WAIT]
        if not waited:
            return 0.5
        
        # Waited opportunities should have better outcomes later
        # Simplified: at least some waited should have turned positive
        return 0.5  # Placeholder - requires historical comparison
    
    def _calculate_confidence_calibration(self, resolved: List[Opportunity]) -> float:
        """Calculate confidence calibration score"""
        executed = [o for o in resolved if o.prediction and o.decision]
        if not executed:
            return 0.5
        
        # Compare predicted confidence to actual accuracy
        errors = []
        for o in executed:
            if o.prediction and o.metrics.get("was_correct") is not None:
                predicted_correct = o.prediction.predicted_confidence
                actual_correct = 1.0 if o.metrics["was_correct"] else 0.0
                errors.append(abs(predicted_correct - actual_correct))
        
        if not errors:
            return 0.5
        
        # Mean absolute error (lower is better)
        mae = sum(errors) / len(errors)
        return max(0, 1 - mae * 2)  # Convert to score
    
    def _calculate_regret_score(self, resolved: List[Opportunity]) -> float:
        """Calculate regret score (lower is better)"""
        # Regret = missed gains + realized losses from bad decisions
        total_regret = 0.0
        
        for o in resolved:
            if not o.decision:
                continue
            
            if o.decision.action == DecisionAction.REJECT:
                # Regret of missed opportunity
                if (o.actual_pnl or 0) > 0:
                    total_regret += o.actual_pnl
            elif o.decision.action == DecisionAction.EXECUTE:
                # Regret of bad execution
                if (o.actual_pnl or 0) < 0:
                    total_regret += abs(o.actual_pnl)
        
        # Normalize to 0-1 (lower regret = higher score)
        max_possible_regret = sum(abs(o.actual_pnl or 0) for o in resolved)
        if max_possible_regret == 0:
            return 0.0
        
        return max(0, 1 - (total_regret / max_possible_regret))
    
    def _calculate_sharpe(self, pnls: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not pnls or len(pnls) < 2:
            return 0.0
        
        mean = sum(pnls) / len(pnls)
        variance = sum((p - mean) ** 2 for p in pnls) / len(pnls)
        std = math.sqrt(variance)
        
        if std == 0:
            return 0.0
        
        return mean / std
    
    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not pnls:
            return 0.0
        
        cumulative = []
        total = 0.0
        for pnl in pnls:
            total += pnl
            cumulative.append(total)
        
        peak = cumulative[0]
        max_dd = 0.0
        
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / (peak + 1)
            if dd > max_dd:
                max_dd = dd
        
        return max_dd


class ThresholdOptimizer:
    """
    Optimizes decision thresholds using statistical evidence.
    
    Key principle: Never optimize solely for win rate.
    Optimizes for long-term expected value and risk-adjusted performance.
    """
    
    def __init__(self, analyzer: OpportunityAnalyzer):
        self.analyzer = analyzer
        self._optimization_history: List[Dict[str, Any]] = []
    
    def optimize(
        self,
        metric: str = "risk_adjusted_score",
        iterations: int = 100
    ) -> Dict[str, Any]:
        """
        Optimize thresholds to maximize the given metric.
        
        Args:
            metric: Metric to optimize ("expected_value", "sharpe_ratio", "profit_factor")
            iterations: Number of optimization iterations
        """
        current = self.analyzer.get_opportunities(1000)
        if len(current) < 30:
            return {"status": "insufficient_data", "samples": len(current)}
        
        best_score = self._evaluate_metric(current, metric)
        best_thresholds = self._get_current_thresholds()
        
        for i in range(iterations):
            # Generate candidate thresholds
            candidate = self._mutate_thresholds(best_thresholds)
            
            # Apply and evaluate
            self._apply_thresholds(candidate)
            score = self._evaluate_metric(current, metric)
            
            if score > best_score:
                best_score = score
                best_thresholds = candidate
        
        # Restore original thresholds
        self._apply_thresholds(best_thresholds)
        
        result = {
            "status": "optimized",
            "metric": metric,
            "best_score": best_score,
            "thresholds": best_thresholds,
            "iterations": iterations,
        }
        
        self._optimization_history.append(result)
        return result
    
    def _evaluate_metric(
        self, 
        opportunities: List[Opportunity], 
        metric: str
    ) -> float:
        """Evaluate a metric on given opportunities"""
        resolved = [o for o in opportunities if o.is_resolved()]
        if not resolved:
            return 0.0
        
        if metric == "win_rate":
            wins = sum(1 for o in resolved if (o.actual_pnl or 0) > 0)
            return wins / len(resolved)
        
        elif metric == "expected_value":
            avg_pnl = sum(o.actual_pnl or 0 for o in resolved) / len(resolved)
            return avg_pnl
        
        elif metric == "sharpe_ratio":
            pnls = [o.actual_pnl for o in resolved if o.actual_pnl is not None]
            return self.analyzer._calculate_sharpe(pnls)
        
        elif metric == "profit_factor":
            wins = sum(o.actual_pnl for o in resolved if (o.actual_pnl or 0) > 0)
            losses = abs(sum(o.actual_pnl for o in resolved if (o.actual_pnl or 0) < 0))
            return wins / losses if losses > 0 else 0
        
        elif metric == "risk_adjusted_score":
            qs = self.analyzer.calculate_decision_quality_score()
            return qs.risk_adjusted_score
        
        return 0.0
    
    def _get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values"""
        return {
            "min_confidence": self.analyzer.min_confidence,
            "min_expected_value": self.analyzer.min_expected_value,
            "min_probability": self.analyzer.min_probability,
            "abstention_threshold": self.analyzer.abstention_threshold,
        }
    
    def _apply_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Apply threshold values"""
        self.analyzer.min_confidence = thresholds.get("min_confidence", 0.6)
        self.analyzer.min_expected_value = thresholds.get("min_expected_value", 0.01)
        self.analyzer.min_probability = thresholds.get("min_probability", 0.55)
        self.analyzer.abstention_threshold = thresholds.get("abstention_threshold", 0.4)
    
    def _mutate_thresholds(self, current: Dict[str, float]) -> Dict[str, float]:
        """Mutate thresholds for optimization"""
        import random
        mutated = current.copy()
        
        # Random mutation
        for key in mutated:
            mutation_range = mutated[key] * 0.2  # 20% change
            mutated[key] = mutated[key] + random.uniform(-mutation_range, mutation_range)
            
            # Clamp to valid ranges
            if key in ["min_confidence", "min_probability", "abstention_threshold"]:
                mutated[key] = max(0, min(1, mutated[key]))
            else:
                mutated[key] = max(0, mutated[key])
        
        return mutated


class TradeExplainer:
    """
    Generates explanations for trading decisions.
    
    Explains both executed and rejected trades.
    """
    
    def explain_executed_trade(self, opportunity: Opportunity) -> Dict[str, Any]:
        """Generate explanation for an executed trade"""
        if not opportunity.decision or opportunity.decision.action != DecisionAction.EXECUTE:
            raise ValueError("Can only explain executed trades")
        
        parts = []
        
        # Prediction explanation
        if opportunity.prediction:
            parts.append(self._explain_prediction(opportunity.prediction))
        
        # Decision explanation
        parts.append({
            "type": "decision",
            "summary": f"Executed trade: {opportunity.decision.reason}",
            "confidence": opportunity.decision.confidence,
            "expected_value": opportunity.decision.expected_value,
            "risk_score": opportunity.decision.risk_adjusted_score,
        })
        
        # Alternative analysis
        parts.append(self._explain_alternatives(opportunity))
        
        return {
            "trade_id": opportunity.opportunity_id,
            "symbol": opportunity.symbol,
            "explanation": parts,
            "timestamp": opportunity.timestamp,
        }
    
    def explain_rejected_trade(self, opportunity: Opportunity) -> Dict[str, Any]:
        """Generate explanation for a rejected trade"""
        if not opportunity.decision or opportunity.decision.action == DecisionAction.EXECUTE:
            raise ValueError("Can only explain rejected trades")
        
        parts = []
        
        # Why rejected
        if opportunity.prediction:
            parts.append({
                "type": "rejection_reason",
                "summary": opportunity.decision.reason,
                "confidence": opportunity.prediction.predicted_confidence,
                "probability": opportunity.prediction.predicted_probability,
            })
        
        # What was missed (if it would have been profitable)
        if opportunity.actual_pnl and opportunity.actual_pnl > 0:
            parts.append({
                "type": "missed_opportunity",
                "summary": f"Trade would have been profitable: ${opportunity.actual_pnl:.2f}",
                "actual_pnl": opportunity.actual_pnl,
                "was_correct_rejection": opportunity.actual_pnl < 0,
            })
        
        # Regret analysis
        if opportunity.decision:
            parts.append({
                "type": "regret_analysis",
                "regret_score": 1.0 - opportunity.decision.expected_value,
                "alternative_actions": self._suggest_alternatives(opportunity),
            })
        
        return {
            "trade_id": opportunity.opportunity_id,
            "symbol": opportunity.symbol,
            "rejection_explanation": parts,
            "timestamp": opportunity.timestamp,
        }
    
    def _explain_prediction(self, prediction: Prediction) -> Dict[str, Any]:
        """Explain a prediction"""
        return {
            "type": "prediction",
            "direction": prediction.predicted_direction,
            "confidence": prediction.predicted_confidence,
            "probability": prediction.predicted_probability,
            "magnitude": prediction.predicted_magnitude,
            "features": prediction.features_used[:5],  # Top 5 features
            "model_version": prediction.model_version,
        }
    
    def _explain_alternatives(self, opportunity: Opportunity) -> Dict[str, Any]:
        """Explain alternative actions"""
        alternatives = []
        
        # What if we had waited?
        if opportunity.actual_magnitude:
            alternatives.append({
                "action": "wait",
                "description": "Wait for better opportunity",
                "potential_improvement": opportunity.actual_magnitude * 0.1,  # Estimate
            })
        
        # What if we had rejected?
        alternatives.append({
            "action": "reject",
            "description": "Skip this trade",
            "potential_outcome": 0,  # No gain, no loss
        })
        
        return {
            "type": "alternatives",
            "alternatives": alternatives,
        }
    
    def _suggest_alternatives(self, opportunity: Opportunity) -> List[Dict[str, Any]]:
        """Suggest alternative actions"""
        suggestions = []
        
        if opportunity.prediction:
            # Lower threshold suggestion
            suggestions.append({
                "suggestion": "lower_confidence_threshold",
                "current": opportunity.prediction.predicted_confidence,
                "suggested": opportunity.prediction.predicted_confidence - 0.05,
                "reason": "Would have captured profitable trade",
            })
        
        return suggestions


# Type hint
from typing import Optional
