"""
Statistical Validation Center
===========================

Automated statistical validation for strategy deployment decisions.

Every strategy must pass all required statistical tests before deployment:
- Walk-forward validation
- Out-of-sample validation
- Rolling validation
- Cross validation
- Bootstrap analysis
- Monte Carlo simulation
- Sensitivity analysis
- Parameter stability analysis
- Confidence calibration
- Expected value analysis
- Profit factor validation
- Maximum drawdown validation
- Capital efficiency validation
- Regime robustness validation
"""

import time
import uuid
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationType(Enum):
    """Types of validation"""
    WALK_FORWARD = "walk_forward"
    OUT_OF_SAMPLE = "out_of_sample"
    ROLLING = "rolling"
    CROSS_VALIDATION = "cross_validation"
    BOOTSTRAP = "bootstrap"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY = "sensitivity"
    PARAMETER_STABILITY = "parameter_stability"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    EXPECTED_VALUE = "expected_value"
    PROFIT_FACTOR = "profit_factor"
    MAX_DRAWDOWN = "max_drawdown"
    CAPITAL_EFFICIENCY = "capital_efficiency"
    REGIME_ROBUSTNESS = "regime_robustness"


@dataclass
class ValidationThresholds:
    """Thresholds for validation metrics"""
    # General
    min_win_rate: float = 0.40
    max_drawdown: float = 0.20
    min_sharpe_ratio: float = 1.0
    min_profit_factor: float = 1.2
    min_trade_count: int = 100
    
    # Walk-forward
    walk_forward_persistence: float = 0.7  # Correlation between windows
    walk_forward_consistency: float = 0.5  # Proportion of profitable windows
    
    # Out-of-sample
    oos_max_sharpe_degradation: float = 0.3  # Max drop from IS to OOS
    
    # Stability
    parameter_stability_score: float = 0.6
    sensitivity_threshold: float = 0.5
    
    # Bootstrap
    bootstrap_confidence: float = 0.95
    
    # Monte Carlo
    monte_carlo_confidence: float = 0.95
    worst_case_confidence: float = 0.05
    
    # Regime
    min_regime_count: int = 3
    regime_performance_variance: float = 0.5
    
    # Confidence calibration
    calibration_error_threshold: float = 0.1


@dataclass
class ValidationResult:
    """Result of a validation test"""
    validation_id: str
    validation_type: ValidationType
    status: ValidationStatus
    
    # Metrics
    metric: str
    value: float
    threshold: float
    
    # Details
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    sample_size: int = 0
    p_value: float = 0
    confidence_interval: Tuple[float, float] = (0, 0)
    
    timestamp: float = field(default_factory=time.time)
    
    def is_passed(self) -> bool:
        return self.status == ValidationStatus.PASSED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "validation_type": self.validation_type.value,
            "status": self.status.value,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "details": self.details,
            "sample_size": self.sample_size,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
            "timestamp": self.timestamp,
        }


def _calculate_basic_metrics(returns: np.ndarray) -> Dict[str, float]:
    """Calculate basic performance metrics"""
    if len(returns) == 0:
        return {}
    
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    
    return {
        "total_return": np.sum(returns),
        "mean_return": np.mean(returns),
        "std_return": np.std(returns),
        "win_rate": len(wins) / len(returns) if len(returns) > 0 else 0,
        "avg_win": np.mean(wins) if len(wins) > 0 else 0,
        "avg_loss": np.mean(losses) if len(losses) > 0 else 0,
        "profit_factor": abs(np.sum(wins) / np.sum(losses)) if len(losses) > 0 and np.sum(losses) != 0 else 0,
        "sharpe_ratio": np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0,
        "max_drawdown": _calculate_max_drawdown(returns),
    }


def _calculate_max_drawdown(returns: np.ndarray) -> float:
    """Calculate maximum drawdown"""
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    return abs(np.min(drawdown))


class StatisticalValidator:
    """Base class for statistical validators"""
    
    def __init__(self, thresholds: Optional[ValidationThresholds] = None):
        self.thresholds = thresholds or ValidationThresholds()
        self.results: List[ValidationResult] = []
    
    def validate(self, returns: np.ndarray, **kwargs) -> ValidationResult:
        """Run validation - to be implemented by subclasses"""
        raise NotImplementedError
    
    def get_results(self) -> List[ValidationResult]:
        return self.results
    
    def get_passed(self) -> List[ValidationResult]:
        return [r for r in self.results if r.is_passed()]
    
    def is_deployment_ready(self) -> bool:
        """Check if all validations passed"""
        return all(r.is_passed() for r in self.results)


class WalkForwardValidator(StatisticalValidator):
    """Walk-forward validation"""
    
    def validate(
        self,
        returns: np.ndarray,
        window_size: int = 252,
        step_size: int = 63
    ) -> ValidationResult:
        """
        Validate using walk-forward analysis.
        
        Splits data into rolling windows and validates consistency.
        """
        n = len(returns)
        if n < window_size * 2:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.WALK_FORWARD,
                status=ValidationStatus.SKIPPED,
                metric="walk_forward",
                value=0,
                threshold=self.thresholds.walk_forward_persistence,
                message="Insufficient data for walk-forward analysis",
            )
        
        # Calculate window returns
        window_returns = []
        i = 0
        while i + window_size <= n:
            window = returns[i:i + window_size]
            window_returns.append(np.sum(window))
            i += step_size
        
        if len(window_returns) < 2:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.WALK_FORWARD,
                status=ValidationStatus.SKIPPED,
                metric="walk_forward",
                value=0,
                threshold=self.thresholds.walk_forward_persistence,
                message="Not enough windows for analysis",
            )
        
        # Calculate persistence (correlation between consecutive windows)
        window_arr = np.array(window_returns)
        persistence = np.corrcoef(window_arr[:-1], window_arr[1:])[0, 1]
        
        # Calculate consistency (proportion of profitable windows)
        profitable = np.sum(window_arr > 0)
        consistency = profitable / len(window_arr)
        
        # Combined score
        score = (persistence + consistency) / 2
        
        status = ValidationStatus.PASSED if (
            persistence >= self.thresholds.walk_forward_persistence and
            consistency >= self.thresholds.walk_forward_consistency
        ) else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.WALK_FORWARD,
            status=status,
            metric="walk_forward_score",
            value=score,
            threshold=self.thresholds.walk_forward_persistence,
            message=f"Walk-forward score: {score:.3f}, Persistence: {persistence:.3f}, Consistency: {consistency:.3f}",
            details={
                "persistence": persistence,
                "consistency": consistency,
                "window_count": len(window_returns),
                "profitable_windows": int(profitable),
            },
            sample_size=len(window_returns),
        )
        
        self.results.append(result)
        return result


class OutOfSampleValidator(StatisticalValidator):
    """Out-of-sample validation"""
    
    def validate(
        self,
        is_returns: np.ndarray,  # In-sample
        oos_returns: np.ndarray  # Out-of-sample
    ) -> ValidationResult:
        """
        Validate out-of-sample performance.
        """
        is_metrics = _calculate_basic_metrics(is_returns)
        oos_metrics = _calculate_basic_metrics(oos_returns)
        
        if not is_metrics or not oos_metrics:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.OUT_OF_SAMPLE,
                status=ValidationStatus.SKIPPED,
                metric="oos_sharpe_degradation",
                value=0,
                threshold=0,
                message="Insufficient data",
            )
        
        # Calculate Sharpe degradation
        is_sharpe = is_metrics.get("sharpe_ratio", 0)
        oos_sharpe = oos_metrics.get("sharpe_ratio", 0)
        
        if is_sharpe > 0:
            degradation = (is_sharpe - oos_sharpe) / is_sharpe
        else:
            degradation = 1.0 if oos_sharpe <= 0 else 0
        
        # Also check if OOS Sharpe is still positive
        oos_positive = oos_sharpe > 0
        
        status = ValidationStatus.PASSED if (
            degradation <= self.thresholds.oos_max_sharpe_degradation and oos_positive
        ) else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.OUT_OF_SAMPLE,
            status=status,
            metric="oos_sharpe_degradation",
            value=degradation,
            threshold=self.thresholds.oos_max_sharpe_degradation,
            message=f"OOS Sharpe: {oos_sharpe:.3f}, Degradation: {degradation:.1%}",
            details={
                "is_sharpe": is_sharpe,
                "oos_sharpe": oos_sharpe,
                "is_win_rate": is_metrics.get("win_rate", 0),
                "oos_win_rate": oos_metrics.get("win_rate", 0),
            },
            sample_size=len(oos_returns),
        )
        
        self.results.append(result)
        return result


class MonteCarloValidator(StatisticalValidator):
    """Monte Carlo simulation validation"""
    
    def validate(
        self,
        returns: np.ndarray,
        n_simulations: int = 10000,
        confidence: float = 0.95
    ) -> ValidationResult:
        """
        Validate using Monte Carlo simulation.
        """
        if len(returns) < 30:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.MONTE_CARLO,
                status=ValidationStatus.SKIPPED,
                metric="monte_carlo_var",
                value=0,
                threshold=0,
                message="Insufficient data for Monte Carlo",
            )
        
        # Calculate parameters
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Run simulations
        simulated_paths = []
        worst_cases = []
        
        for _ in range(n_simulations):
            # Bootstrap sample
            sample = np.random.choice(returns, size=len(returns), replace=True)
            simulated_paths.append(np.sum(sample))
            worst_cases.append(np.min(sample))
        
        simulated_paths = np.array(simulated_paths)
        worst_cases = np.array(worst_cases)
        
        # Calculate percentiles
        var_confidence = (1 - confidence)
        var_threshold = np.percentile(simulated_paths, var_confidence * 100)
        worst_case = np.percentile(worst_cases, self.thresholds.worst_case_confidence * 100)
        
        # Calculate probability of profit
        prob_profit = np.mean(simulated_paths > 0)
        
        # Check if worst case is acceptable
        acceptable = worst_case > -self.thresholds.max_drawdown
        
        status = ValidationStatus.PASSED if acceptable else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.MONTE_CARLO,
            status=status,
            metric="worst_case",
            value=worst_case,
            threshold=-self.thresholds.max_drawdown,
            message=f"Monte Carlo worst case: {worst_case:.2%}, Prob profit: {prob_profit:.1%}",
            details={
                "n_simulations": n_simulations,
                "confidence": confidence,
                "var_threshold": var_threshold,
                "prob_profit": prob_profit,
                "mean_simulated": np.mean(simulated_paths),
                "std_simulated": np.std(simulated_paths),
            },
            sample_size=n_simulations,
        )
        
        self.results.append(result)
        return result


class BootstrapValidator(StatisticalValidator):
    """Bootstrap confidence interval validation"""
    
    def validate(
        self,
        returns: np.ndarray,
        n_bootstrap: int = 10000,
        confidence: float = 0.95
    ) -> ValidationResult:
        """
        Validate using bootstrap analysis.
        """
        if len(returns) < 10:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.BOOTSTRAP,
                status=ValidationStatus.SKIPPED,
                metric="bootstrap_sharpe",
                value=0,
                threshold=0,
                message="Insufficient data for bootstrap",
            )
        
        # Calculate bootstrap distribution of Sharpe ratio
        sharpe_ratios = []
        
        for _ in range(n_bootstrap):
            sample = np.random.choice(returns, size=len(returns), replace=True)
            sharpe = np.mean(sample) / np.std(sample) * np.sqrt(252) if np.std(sample) > 0 else 0
            sharpe_ratios.append(sharpe)
        
        sharpe_ratios = np.array(sharpe_ratios)
        
        # Calculate confidence interval
        alpha = 1 - confidence
        ci_lower = np.percentile(sharpe_ratios, alpha / 2 * 100)
        ci_upper = np.percentile(sharpe_ratios, (1 - alpha / 2) * 100)
        
        # Check if confidence interval is entirely positive
        acceptable = ci_lower > 0
        
        status = ValidationStatus.PASSED if acceptable else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.BOOTSTRAP,
            status=status,
            metric="sharpe_ci_lower",
            value=ci_lower,
            threshold=0,
            message=f"Sharpe ratio 95% CI: [{ci_lower:.3f}, {ci_upper:.3f}]",
            details={
                "n_bootstrap": n_bootstrap,
                "confidence": confidence,
                "ci_upper": ci_upper,
                "mean_sharpe": np.mean(sharpe_ratios),
            },
            sample_size=n_bootstrap,
            confidence_interval=(ci_lower, ci_upper),
        )
        
        self.results.append(result)
        return result


class ParameterStabilityValidator(StatisticalValidator):
    """Parameter stability validation"""
    
    def validate(
        self,
        param_values: List[float],  # Strategy parameter values across time
        stability_threshold: float = 0.6
    ) -> ValidationResult:
        """
        Validate parameter stability.
        """
        if len(param_values) < 3:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.PARAMETER_STABILITY,
                status=ValidationStatus.SKIPPED,
                metric="parameter_stability",
                value=0,
                threshold=stability_threshold,
                message="Insufficient data for parameter stability",
            )
        
        values = np.array(param_values)
        
        # Calculate coefficient of variation
        cv = np.std(values) / np.abs(np.mean(values)) if np.mean(values) != 0 else 1
        
        # Stability score (inverse of CV, capped at 1)
        stability = 1 / (1 + cv)
        
        status = ValidationStatus.PASSED if stability >= stability_threshold else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.PARAMETER_STABILITY,
            status=status,
            metric="parameter_stability",
            value=stability,
            threshold=stability_threshold,
            message=f"Parameter stability: {stability:.3f}",
            details={
                "cv": cv,
                "mean": np.mean(values),
                "std": np.std(values),
            },
            sample_size=len(values),
        )
        
        self.results.append(result)
        return result


class ConfidenceCalibrationValidator(StatisticalValidator):
    """Confidence calibration validation"""
    
    def validate(
        self,
        predictions: List[float],  # Model confidences
        outcomes: List[bool],  # Actual outcomes (True = correct)
        n_bins: int = 10
    ) -> ValidationResult:
        """
        Validate confidence calibration using calibration curve.
        """
        if len(predictions) != len(outcomes) or len(predictions) < 30:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.CONFIDENCE_CALIBRATION,
                status=ValidationStatus.SKIPPED,
                metric="calibration_error",
                value=0,
                threshold=0,
                message="Insufficient data for calibration",
            )
        
        # Bin predictions
        preds = np.array(predictions)
        acts = np.array(outcomes)
        
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(preds, bins) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)
        
        # Calculate calibration curve
        calibration_errors = []
        
        for i in range(n_bins):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                avg_predicted = np.mean(preds[mask])
                avg_actual = np.mean(acts[mask])
                calibration_errors.append(abs(avg_predicted - avg_actual))
        
        # Expected Calibration Error (ECE)
        ece = np.mean(calibration_errors) if calibration_errors else 0
        
        status = ValidationStatus.PASSED if ece <= self.thresholds.calibration_error_threshold else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.CONFIDENCE_CALIBRATION,
            status=status,
            metric="calibration_error",
            value=ece,
            threshold=self.thresholds.calibration_error_threshold,
            message=f"Expected Calibration Error: {ece:.3f}",
            details={
                "n_bins": n_bins,
                "calibration_errors": calibration_errors,
            },
            sample_size=len(predictions),
        )
        
        self.results.append(result)
        return result


class RegimeRobustnessValidator(StatisticalValidator):
    """Regime robustness validation"""
    
    def validate(
        self,
        regime_returns: Dict[str, np.ndarray],  # Returns by regime
        min_regimes: int = 3
    ) -> ValidationResult:
        """
        Validate robustness across market regimes.
        """
        if len(regime_returns) < min_regimes:
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                validation_type=ValidationType.REGIME_ROBUSTNESS,
                status=ValidationStatus.SKIPPED,
                metric="regime_robustness",
                value=0,
                threshold=0,
                message=f"Need at least {min_regimes} regimes",
            )
        
        # Calculate Sharpe for each regime
        regime_sharpes = {}
        for regime, returns in regime_returns.items():
            if len(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
                regime_sharpes[regime] = sharpe
        
        # Check if all regimes are positive
        all_positive = all(s > 0 for s in regime_sharpes.values())
        
        # Calculate performance variance
        sharpe_values = list(regime_sharpes.values())
        mean_sharpe = np.mean(sharpe_values)
        variance = np.var(sharpe_values) / (mean_sharpe ** 2) if mean_sharpe > 0 else 1
        
        # Score based on variance (lower is better)
        robustness = 1 / (1 + variance)
        
        status = ValidationStatus.PASSED if (
            robustness >= (1 - self.thresholds.regime_performance_variance)
        ) else ValidationStatus.FAILED
        
        result = ValidationResult(
            validation_id=str(uuid.uuid4()),
            validation_type=ValidationType.REGIME_ROBUSTNESS,
            status=status,
            metric="regime_robustness",
            value=robustness,
            threshold=1 - self.thresholds.regime_performance_variance,
            message=f"Regime robustness: {robustness:.3f}",
            details={
                "regime_sharpes": regime_sharpes,
                "performance_variance": variance,
                "n_regimes": len(regime_returns),
            },
            sample_size=sum(len(r) for r in regime_returns.values()),
        )
        
        self.results.append(result)
        return result
