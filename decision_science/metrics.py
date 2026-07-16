"""
Decision Science Metrics
=======================

Individual metric classes for opportunity analysis.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class PredictionQuality:
    """
    Measures the quality of predictions.
    """
    prediction_id: str
    predicted_value: float
    actual_value: Optional[float]
    
    # Component metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Calibration
    calibration_error: float = 0.0
    
    def calculate(self) -> "PredictionQuality":
        """Calculate all quality metrics"""
        if self.actual_value is not None:
            # Accuracy (within tolerance)
            tolerance = 0.05  # 5%
            self.accuracy = 1.0 if abs(self.predicted_value - self.actual_value) / (self.actual_value + 0.001) < tolerance else 0.0
            
            # Direction accuracy
            pred_direction = 1 if self.predicted_value > 0 else -1 if self.predicted_value < 0 else 0
            actual_direction = 1 if self.actual_value > 0 else -1 if self.actual_value < 0 else 0
            self.precision = 1.0 if pred_direction == actual_direction else 0.0
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "calibration_error": self.calibration_error,
        }


@dataclass
class DecisionQuality:
    """
    Measures the quality of decisions.
    """
    decision_id: str
    action_taken: str
    expected_outcome: float
    actual_outcome: Optional[float]
    
    # Quality components
    appropriateness: float = 0.0  # Was the action appropriate?
    timing: float = 0.0  # Was the timing good?
    justification: float = 0.0  # Was there good reasoning?
    
    def calculate(self) -> "DecisionQuality":
        """Calculate decision quality"""
        if self.actual_outcome is not None:
            # Appropriateness: positive outcome with execute, or negative avoided
            if self.action_taken == "execute":
                self.appropriateness = 1.0 if self.actual_outcome > 0 else 0.5
            else:
                self.appropriateness = 1.0 if self.actual_outcome <= 0 else 0.0
            
            # Timing (simplified)
            self.timing = min(1.0, max(0.0, self.actual_outcome / (self.expected_outcome + 0.001)))
            
            # Justification based on alignment
            self.justification = 1.0 - abs(self.expected_outcome - self.actual_outcome) / (abs(self.expected_outcome) + 0.001)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "appropriateness": self.appropriateness,
            "timing": self.timing,
            "justification": self.justification,
        }


@dataclass
class ExpectedValue:
    """
    Expected value calculation and tracking.
    """
    opportunity_id: str
    
    # Input parameters
    probability: float  # P(success)
    win_amount: float  # Amount gained on success
    loss_amount: float  # Amount lost on failure
    
    # Calculated
    expected_value: float = 0.0
    risk_adjusted_ev: float = 0.0
    
    # Breakdown
    expected_gain: float = 0.0
    expected_loss: float = 0.0
    
    def calculate(self) -> "ExpectedValue":
        """Calculate expected value"""
        self.expected_gain = self.probability * self.win_amount
        self.expected_loss = (1 - self.probability) * self.loss_amount
        self.expected_value = self.expected_gain - self.expected_loss
        
        # Risk-adjusted: incorporate volatility
        volatility = 0.02  # Default
        risk_penalty = volatility * self.loss_amount * (1 - self.probability)
        self.risk_adjusted_ev = self.expected_value - risk_penalty
        
        return self
    
    @classmethod
    def from_prediction(
        cls,
        opportunity_id: str,
        predicted_probability: float,
        predicted_magnitude: float,
        loss_rate: float = 0.005
    ) -> "ExpectedValue":
        """Create from prediction data"""
        return cls(
            opportunity_id=opportunity_id,
            probability=predicted_probability,
            win_amount=predicted_magnitude,
            loss_amount=loss_rate,
        ).calculate()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "expected_value": self.expected_value,
            "risk_adjusted_ev": self.risk_adjusted_ev,
            "expected_gain": self.expected_gain,
            "expected_loss": self.expected_loss,
        }


@dataclass
class CapitalEfficiency:
    """
    Measures capital efficiency of a decision.
    """
    opportunity_id: str
    
    capital_required: float
    expected_return: float
    actual_return: Optional[float]
    holding_period_seconds: float
    
    # Metrics
    return_on_capital: float = 0.0
    annualized_return: float = 0.0
    capital_utilization: float = 0.0
    
    def calculate(self) -> "CapitalEfficiency":
        """Calculate efficiency metrics"""
        if self.capital_required > 0:
            self.return_on_capital = self.expected_return / self.capital_required
            
            # Annualize return
            if self.holding_period_seconds > 0:
                periods_per_year = 365 * 24 * 3600 / self.holding_period_seconds
                self.annualized_return = self.return_on_capital * periods_per_year
            
            # Capital utilization (100% if capital is deployed)
            self.capital_utilization = 1.0 if self.expected_return > 0 else 0.0
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "return_on_capital": self.return_on_capital,
            "annualized_return": self.annualized_return,
            "capital_utilization": self.capital_utilization,
        }


@dataclass
class OpportunityCost:
    """
    Calculates opportunity cost of decisions.
    """
    opportunity_id: str
    
    # What was chosen
    chosen_action: str
    chosen_return: float
    
    # What was not chosen
    alternative_actions: Dict[str, float] = field(default_factory=dict)
    
    # Cost metrics
    cost_of_rejection: float = 0.0  # Cost of not taking opportunity
    cost_of_regret: float = 0.0  # Regret from wrong choice
    best_alternative_return: float = 0.0
    
    def calculate(self) -> "OpportunityCost":
        """Calculate opportunity costs"""
        # Find best alternative
        if self.alternative_actions:
            self.best_alternative_return = max(self.alternative_actions.values())
        
        # Cost of rejection
        if self.chosen_action == "reject":
            self.cost_of_rejection = self.best_alternative_return - self.chosen_return
        
        # Regret
        self.cost_of_regret = max(0, self.best_alternative_return - self.chosen_return)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "cost_of_rejection": self.cost_of_rejection,
            "cost_of_regret": self.cost_of_regret,
            "best_alternative_return": self.best_alternative_return,
        }


@dataclass
class AbstentionQuality:
    """
    Measures quality of abstaining from trades.
    """
    opportunity_id: str
    
    # Why abstained
    reason: str
    confidence: float
    expected_loss_if_taken: float
    
    # Actual outcome (for comparison)
    actual_outcome: Optional[float]
    
    # Quality metrics
    was_correct: bool = False
    avoided_loss: float = 0.0
    
    def calculate(self) -> "AbstentionQuality":
        """Calculate abstention quality"""
        if self.actual_outcome is not None:
            # Correct if we avoided a loss
            self.was_correct = self.actual_outcome <= 0
            self.avoided_loss = abs(self.actual_outcome) if self.actual_outcome < 0 else 0
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "was_correct": self.was_correct,
            "avoided_loss": self.avoided_loss,
            "confidence": self.confidence,
        }


@dataclass
class ConfidenceCalibration:
    """
    Calibration of confidence scores against actual accuracy.
    """
    opportunity_id: str
    
    # Predicted confidence
    confidence: float
    
    # Actual accuracy
    was_correct: Optional[bool]
    
    # Calibration metrics
    calibration_error: float = 0.0
    calibration_bins: Dict[str, float] = field(default_factory=dict)
    
    def calculate(self) -> "ConfidenceCalibration":
        """Calculate calibration"""
        if self.was_correct is not None:
            # Calibration error: |confidence - accuracy|
            accuracy = 1.0 if self.was_correct else 0.0
            self.calibration_error = abs(self.confidence - accuracy)
        
        # Bin into confidence buckets
        if 0 <= self.confidence < 0.2:
            self.calibration_bins["0-20%"] = self.confidence
        elif 0.2 <= self.confidence < 0.4:
            self.calibration_bins["20-40%"] = self.confidence
        elif 0.4 <= self.confidence < 0.6:
            self.calibration_bins["40-60%"] = self.confidence
        elif 0.6 <= self.confidence < 0.8:
            self.calibration_bins["60-80%"] = self.confidence
        else:
            self.calibration_bins["80-100%"] = self.confidence
        
        return self
    
    @classmethod
    def aggregate_calibration(
        cls,
        calibrations: List["ConfidenceCalibration"]
    ) -> Dict[str, Any]:
        """Aggregate calibration across multiple opportunities"""
        if not calibrations:
            return {"error": "No calibrations to aggregate"}
        
        # Group by bins
        bins = {"0-20%": [], "20-40%": [], "40-60%": [], "60-80%": [], "80-100%": []}
        
        for cal in calibrations:
            for bin_name, conf in cal.calibration_bins.items():
                bins[bin_name].append(cal)
        
        # Calculate accuracy per bin
        result = {}
        for bin_name, items in bins.items():
            if items:
                correct = sum(1 for c in items if c.was_correct)
                avg_confidence = sum(c.confidence for c in items) / len(items)
                accuracy = correct / len(items)
                result[bin_name] = {
                    "count": len(items),
                    "avg_confidence": avg_confidence,
                    "actual_accuracy": accuracy,
                    "calibration_error": abs(avg_confidence - accuracy),
                }
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "calibration_error": self.calibration_error,
            "calibration_bins": self.calibration_bins,
        }


@dataclass
class RegretScore:
    """
    Measures regret from trading decisions.
    """
    opportunity_id: str
    
    # Decision made
    action: str
    actual_return: Optional[float]
    
    # What could have been
    best_possible_return: float
    best_achieved_return: float
    
    # Regret components
    opportunity_regret: float = 0.0  # Regret from not taking better action
    execution_regret: float = 0.0  # Regret from poor execution
    total_regret: float = 0.0
    
    def calculate(self) -> "RegretScore":
        """Calculate regret scores"""
        if self.actual_return is not None:
            # Opportunity regret
            self.opportunity_regret = max(0, self.best_possible_return - self.actual_return)
            
            # Execution regret (if we made the trade)
            if self.action == "execute":
                self.execution_regret = max(0, self.best_achieved_return - self.actual_return)
            
            # Total regret
            self.total_regret = self.opportunity_regret + self.execution_regret
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_regret": self.opportunity_regret,
            "execution_regret": self.execution_regret,
            "total_regret": self.total_regret,
        }


@dataclass
class AlternativeOutcome:
    """
    Analysis of alternative outcomes.
    """
    opportunity_id: str
    
    # What happened
    actual_outcome: Optional[float]
    
    # What would have happened under alternatives
    alternatives: Dict[str, float] = field(default_factory=dict)
    
    # Analysis
    best_alternative: str = ""
    worst_alternative: str = ""
    value_of_waiting: float = 0.0
    
    def calculate(self) -> "AlternativeOutcome":
        """Calculate alternative outcomes"""
        if self.alternatives:
            self.best_alternative = max(self.alternatives, key=self.alternatives.get)
            self.worst_alternative = min(self.alternatives, key=self.alternatives.get)
            
            # Value of waiting (if wait was an option)
            if "wait" in self.alternatives:
                self.value_of_waiting = self.alternatives["wait"] - (self.actual_outcome or 0)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "best_alternative": self.best_alternative,
            "worst_alternative": self.worst_alternative,
            "value_of_waiting": self.value_of_waiting,
            "alternatives": self.alternatives,
        }


@dataclass
class WaitAnalysis:
    """
    Analyzes whether waiting would have produced better results.
    """
    opportunity_id: str
    
    # Original opportunity
    original_prediction: float
    original_timestamp: float
    
    # Subsequent opportunities
    subsequent_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Analysis results
    waiting_would_have_been_better: bool = False
    improvement_from_waiting: float = 0.0
    optimal_wait_duration: float = 0.0
    
    def calculate(self) -> "WaitAnalysis":
        """Analyze if waiting would have been better"""
        if not self.subsequent_opportunities:
            return self
        
        # Find best subsequent opportunity
        best_subsequent = max(
            self.subsequent_opportunities,
            key=lambda x: x.get("return", 0),
            default={"return": 0}
        )
        
        best_return = best_subsequent.get("return", 0)
        
        # Compare to original
        if best_return > self.original_prediction:
            self.waiting_would_have_been_better = True
            self.improvement_from_waiting = best_return - self.original_prediction
            
            # Estimate optimal wait duration
            if best_subsequent.get("timestamp"):
                self.optimal_wait_duration = (
                    best_subsequent["timestamp"] - self.original_timestamp
                )
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "waiting_would_have_been_better": self.waiting_would_have_been_better,
            "improvement_from_waiting": self.improvement_from_waiting,
            "optimal_wait_duration": self.optimal_wait_duration,
        }
