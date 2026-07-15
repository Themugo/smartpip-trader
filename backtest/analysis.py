"""
Analysis Framework
=================

Parameter stability, sensitivity, confidence calibration, and expected value analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class StabilityStatus(Enum):
    """Stability assessment"""
    STABLE = "stable"
    MARGINALLY_STABLE = "marginally_stable"
    UNSTABLE = "unstable"
    ROBUST = "robust"


@dataclass
class StabilityResult:
    """Result of stability analysis"""
    parameter_name: str
    status: StabilityStatus
    stability_score: float
    sensitivity: float
    critical_value: float
    is_robust: bool
    details: Dict[str, Any] = field(default_factory=dict)


class ParameterStabilityAnalyzer:
    """
    Analyzes parameter stability across different market conditions.
    """
    
    def __init__(
        self,
        stability_threshold: float = 0.5,
        robustness_threshold: float = 0.7
    ):
        self.stability_threshold = stability_threshold
        self.robustness_threshold = robustness_threshold
    
    def analyze_parameter(
        self,
        parameter_name: str,
        parameter_values: List[float],
        performance_values: List[float]
    ) -> StabilityResult:
        """
        Analyze how strategy performance changes with parameter values.
        
        Args:
            parameter_name: Name of parameter
            parameter_values: List of parameter values tested
            performance_values: Corresponding performance metrics
            
        Returns:
            StabilityResult
        """
        if len(parameter_values) != len(performance_values):
            raise ValueError("Parameter and performance lists must be same length")
        
        # Calculate correlation
        correlation, p_value = stats.pearsonr(parameter_values, performance_values)
        
        # Calculate sensitivity (derivative of performance wrt parameter)
        sensitivity = self._calculate_sensitivity(parameter_values, performance_values)
        
        # Calculate stability score (lower = more stable)
        # Use coefficient of variation of performance
        cv = np.std(performance_values) / abs(np.mean(performance_values)) if np.mean(performance_values) != 0 else 1
        stability_score = 1.0 - min(cv, 1.0)
        
        # Find critical value (optimal parameter)
        best_idx = np.argmax(performance_values)
        critical_value = parameter_values[best_idx]
        
        # Determine status
        if stability_score >= self.robustness_threshold and abs(correlation) < 0.5:
            status = StabilityStatus.ROBUST
        elif stability_score >= self.stability_threshold:
            status = StabilityStatus.STABLE
        elif stability_score >= self.stability_threshold * 0.5:
            status = StabilityStatus.MARGINALLY_STABLE
        else:
            status = StabilityStatus.UNSTABLE
        
        return StabilityResult(
            parameter_name=parameter_name,
            status=status,
            stability_score=stability_score,
            sensitivity=sensitivity,
            critical_value=critical_value,
            is_robust=status in [StabilityStatus.ROBUST, StabilityStatus.STABLE],
            details={
                "correlation": correlation,
                "p_value": p_value,
                "cv": cv,
                "best_performance": np.max(performance_values),
                "worst_performance": np.min(performance_values),
                "performance_range": np.max(performance_values) - np.min(performance_values)
            }
        )
    
    def _calculate_sensitivity(
        self,
        parameter_values: List[float],
        performance_values: List[float]
    ) -> float:
        """Calculate parameter sensitivity"""
        if len(parameter_values) < 2:
            return 0.0
        
        # Use gradient magnitude
        param_range = max(parameter_values) - min(parameter_values)
        perf_range = max(performance_values) - min(performance_values)
        
        if param_range == 0:
            return 0.0
        
        return perf_range / param_range


class SensitivityAnalyzer:
    """
    Sensitivity analysis using one-at-a-time (OAT) and factorial methods.
    """
    
    def analyze(
        self,
        strategy_func: Callable,
        base_params: Dict[str, float],
        param_ranges: Dict[str, Tuple[float, float]],
        n_steps: int = 10
    ) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on strategy parameters.
        
        Args:
            strategy_func: Function that takes params and returns performance
            base_params: Base parameter values
            param_ranges: Dict of (min, max) for each parameter
            n_steps: Number of steps for each parameter
            
        Returns:
            Sensitivity analysis results
        """
        results = {}
        
        # Base performance
        base_performance = strategy_func(base_params)
        
        for param_name, (min_val, max_val) in param_ranges.items():
            # Generate test values
            test_values = np.linspace(min_val, max_val, n_steps)
            performances = []
            
            for value in test_values:
                test_params = base_params.copy()
                test_params[param_name] = value
                perf = strategy_func(test_params)
                performances.append(perf)
            
            # Calculate sensitivity metrics
            sensitivity = self._calculate_sensitivity(test_values, performances)
            range_impact = max(performances) - min(performances)
            
            # Find optimal value
            best_idx = np.argmax(performances)
            
            results[param_name] = {
                "base_value": base_params.get(param_name),
                "optimal_value": test_values[best_idx],
                "sensitivity": sensitivity,
                "range_impact": range_impact,
                "performance_at_min": performances[0],
                "performance_at_max": performances[-1],
                "performance_at_optimal": performances[best_idx],
                "degradation_at_edges": min(
                    base_performance - performances[0],
                    base_performance - performances[-1]
                ),
                "test_values": list(test_values),
                "performances": performances
            }
        
        # Rank by sensitivity
        sensitivity_ranking = sorted(
            results.items(),
            key=lambda x: x[1]["sensitivity"],
            reverse=True
        )
        
        return {
            "base_performance": base_performance,
            "parameter_analysis": results,
            "most_sensitive": sensitivity_ranking[0][0] if sensitivity_ranking else None,
            "least_sensitive": sensitivity_ranking[-1][0] if sensitivity_ranking else None,
            "sensitivity_ranking": [x[0] for x in sensitivity_ranking]
        }
    
    def _calculate_sensitivity(
        self,
        values: np.ndarray,
        performances: np.ndarray
    ) -> float:
        """Calculate normalized sensitivity"""
        if len(values) < 2:
            return 0.0
        
        # Use correlation as sensitivity measure
        corr, _ = stats.pearsonr(values, performances)
        return abs(corr)


class ConfidenceCalibrator:
    """
    Calibrates model confidence estimates.
    """
    
    def __init__(self):
        self.calibration_data = []
    
    def add_observation(
        self,
        predicted_confidence: float,
        actual_outcome: float  # 1.0 = correct, 0.0 = incorrect
    ) -> None:
        """Add a confidence observation"""
        self.calibration_data.append({
            "predicted": predicted_confidence,
            "actual": actual_outcome
        })
    
    def calibrate(
        self,
        n_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Perform isotonic regression calibration.
        
        Returns calibrated predictions and calibration curve.
        """
        if len(self.calibration_data) < 30:
            return {"error": "Insufficient data for calibration"}
        
        predictions = np.array([d["predicted"] for d in self.calibration_data])
        outcomes = np.array([d["actual"] for d in self.calibration_data])
        
        # Calculate calibration curve (binned)
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_accuracy = []
        bin_counts = []
        
        for i in range(n_bins):
            mask = (predictions >= bin_edges[i]) & (predictions < bin_edges[i + 1])
            if np.sum(mask) > 0:
                bin_accuracy.append(np.mean(outcomes[mask]))
                bin_counts.append(np.sum(mask))
            else:
                bin_accuracy.append(bin_centers[i])
                bin_counts.append(0)
        
        bin_accuracy = np.array(bin_accuracy)
        bin_counts = np.array(bin_counts)
        
        # Calculate calibration error (ECE)
        ece = np.sum(bin_counts / len(predictions) * abs(bin_accuracy - bin_centers))
        
        # Calculate reliability (correlation between confidence and accuracy)
        reliability, _ = stats.pearsonr(predictions, outcomes)
        
        return {
            "calibration_curve": {
                "bin_centers": list(bin_centers),
                "bin_accuracy": list(bin_accuracy),
                "bin_counts": list(bin_counts)
            },
            "expected_calibration_error": ece,
            "reliability": reliability,
            "n_observations": len(self.calibration_data),
            "is_calibrated": ece < 0.1
        }
    
    def get_calibrated_confidence(
        self,
        raw_confidence: float
    ) -> float:
        """Get calibrated confidence using Platt scaling"""
        if len(self.calibration_data) < 30:
            return raw_confidence
        
        predictions = np.array([d["predicted"] for d in self.calibration_data])
        outcomes = np.array([d["actual"] for d in self.calibration_data])
        
        # Fit logistic regression
        try:
            slope, intercept, _ = stats.mlogit(predictions, outcomes)
            
            # Apply Platt scaling
            calibrated = 1 / (1 + np.exp(-(slope * raw_confidence + intercept)))
            return float(np.clip(calibrated, 0, 1))
        except:
            return raw_confidence


class ExpectedValueAnalyzer:
    """
    Analyzes expected value of trading decisions.
    """
    
    def __init__(self):
        self.trades = []
    
    def add_trade(
        self,
        confidence: float,
        actual_pnl: float,
        predicted_direction: str,
        actual_direction: str
    ) -> None:
        """Add a trade for analysis"""
        correct = predicted_direction == actual_direction
        self.trades.append({
            "confidence": confidence,
            "pnl": actual_pnl,
            "correct": correct,
            "correct_sign": 1 if correct else -1
        })
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze expected value patterns"""
        if len(self.trades) < 10:
            return {"error": "Insufficient trades"}
        
        # Sort by confidence
        sorted_trades = sorted(self.trades, key=lambda x: x["confidence"], reverse=True)
        
        # Calculate EV by confidence quintile
        n = len(sorted_trades)
        quintile_size = n // 5
        
        quintile_ev = []
        for i in range(5):
            start = i * quintile_size
            end = start + quintile_size if i < 4 else n
            quintile_trades = sorted_trades[start:end]
            
            if quintile_trades:
                avg_confidence = np.mean([t["confidence"] for t in quintile_trades])
                avg_pnl = np.mean([t["pnl"] for t in quintile_trades])
                win_rate = np.mean([t["correct"] for t in quintile_trades])
                
                quintile_ev.append({
                    "quintile": i + 1,
                    "avg_confidence": avg_confidence,
                    "avg_pnl": avg_pnl,
                    "win_rate": win_rate,
                    "n_trades": len(quintile_trades)
                })
        
        # Overall statistics
        all_confidence = [t["confidence"] for t in self.trades]
        all_pnl = [t["pnl"] for t in self.trades]
        
        # Correlation between confidence and PnL
        corr, p_value = stats.pearsonr(all_confidence, all_pnl)
        
        return {
            "n_trades": len(self.trades),
            "overall_ev": np.mean(all_pnl),
            "confidence_pnl_correlation": corr,
            "correlation_p_value": p_value,
            "is_confidence_useful": p_value < 0.05,
            "quintile_analysis": quintile_ev,
            "high_confidence_ev": quintile_ev[-1]["avg_pnl"] if quintile_ev else 0,
            "low_confidence_ev": quintile_ev[0]["avg_pnl"] if quintile_ev else 0
        }


class ProbabilityCalibrator:
    """
    Calibrates probability estimates using various methods.
    """
    
    def __init__(self):
        self.predictions = []
    
    def add_prediction(
        self,
        predicted_prob: float,
        outcome: bool
    ) -> None:
        """Add a prediction and outcome"""
        self.predictions.append({
            "probability": predicted_prob,
            "outcome": 1.0 if outcome else 0.0
        })
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate calibration metrics"""
        if len(self.predictions) < 10:
            return {"error": "Insufficient predictions"}
        
        probs = np.array([p["probability"] for p in self.predictions])
        outcomes = np.array([p["outcome"] for p in self.predictions])
        
        # Brier Score
        brier_score = np.mean((probs - outcomes) ** 2)
        
        # Log Loss
        eps = 1e-15
        log_loss = -np.mean(
            outcomes * np.log(np.clip(probs, eps, 1 - eps)) +
            (1 - outcomes) * np.log(np.clip(1 - probs, eps, 1 - eps))
        )
        
        # Accuracy
        binary_preds = (probs >= 0.5).astype(float)
        accuracy = np.mean(binary_preds == outcomes)
        
        # Precision, Recall
        tp = np.sum((binary_preds == 1) & (outcomes == 1))
        fp = np.sum((binary_preds == 1) & (outcomes == 0))
        fn = np.sum((binary_preds == 0) & (outcomes == 1))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # Calibration curve
        n_bins = 10
        bins = np.linspace(0, 1, n_bins + 1)
        calibration_curve = []
        
        for i in range(n_bins):
            mask = (probs >= bins[i]) & (probs < bins[i + 1])
            if np.sum(mask) > 0:
                calibration_curve.append({
                    "bin_center": (bins[i] + bins[i + 1]) / 2,
                    "predicted": np.mean(probs[mask]),
                    "actual": np.mean(outcomes[mask]),
                    "count": np.sum(mask)
                })
        
        # ECE (Expected Calibration Error)
        ece = 0
        for point in calibration_curve:
            weight = point["count"] / len(probs)
            ece += weight * abs(point["predicted"] - point["actual"])
        
        return {
            "brier_score": brier_score,
            "log_loss": log_loss,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "expected_calibration_error": ece,
            "calibration_curve": calibration_curve,
            "n_predictions": len(self.predictions),
            "is_well_calibrated": ece < 0.1
        }
