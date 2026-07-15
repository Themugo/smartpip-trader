"""
Statistical Evaluator
====================

Evaluates statistical significance of experiment results.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StatisticalResult:
    """Result of statistical evaluation"""
    id: str
    experiment_id: str
    p_value: float
    confidence_interval: Tuple[float, float]
    effect_size: float
    power: float
    is_significant: bool
    significance_level: float
    test_type: str
    test_statistic: float
    sample_size: int
    degrees_of_freedom: Optional[int]
    assumptions_valid: bool
    assumptions_check: Dict[str, bool]
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "p_value": self.p_value,
            "confidence_interval": list(self.confidence_interval),
            "effect_size": self.effect_size,
            "power": self.power,
            "is_significant": self.is_significant,
            "significance_level": self.significance_level,
            "test_type": self.test_type,
            "test_statistic": self.test_statistic,
            "sample_size": self.sample_size
        }


class StatisticalEvaluator:
    """
    Evaluates statistical significance of experiment results.
    """
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.significance_level = 1 - confidence_level
    
    def evaluate(self, experiment_result: Any) -> StatisticalResult:
        """
        Evaluate statistical significance of experiment result.
        
        Args:
            experiment_result: ExperimentResult
            
        Returns:
            StatisticalResult
        """
        returns = experiment_result.returns
        trades = experiment_result.trades
        
        # Basic statistics
        sample_size = len(returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # T-test for mean return
        t_stat, p_value = self._t_test(returns)
        
        # Confidence interval
        ci = self._confidence_interval(returns, self.confidence_level)
        
        # Effect size (Cohen's d)
        effect_size = self._cohens_d(returns)
        
        # Statistical power
        power = self._calculate_power(sample_size, effect_size, std_return)
        
        # Check assumptions
        assumptions = self._check_assumptions(returns)
        
        # Determine significance
        is_significant = p_value < self.significance_level
        
        result = StatisticalResult(
            id=str(uuid4()),
            experiment_id=experiment_result.id,
            p_value=p_value,
            confidence_interval=ci,
            effect_size=effect_size,
            power=power,
            is_significant=is_significant,
            significance_level=self.significance_level,
            test_type="one_sample_t_test",
            test_statistic=t_stat,
            sample_size=sample_size,
            degrees_of_freedom=sample_size - 1,
            assumptions_valid=all(assumptions.values()),
            assumptions_check=assumptions
        )
        
        logger.info(f"Statistical evaluation: p={p_value:.4f}, significant={is_significant}")
        
        return result
    
    def _t_test(self, data: List[float]) -> Tuple[float, float]:
        """
        One-sample t-test against zero.
        
        Returns:
            Tuple of (t_statistic, p_value)
        """
        n = len(data)
        if n < 2:
            return 0.0, 1.0
        
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        se = std / math.sqrt(n)
        
        if se == 0:
            return 0.0, 1.0
        
        t_stat = mean / se
        
        # Two-tailed p-value
        # Using approximation for large n
        p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))
        
        return t_stat, min(p_value, 1.0)
    
    def _confidence_interval(
        self,
        data: List[float],
        confidence: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for mean"""
        n = len(data)
        if n < 2:
            return (0.0, 0.0)
        
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        se = std / math.sqrt(n)
        
        # Z-score for confidence level
        z = self._z_score(confidence)
        
        lower = mean - z * se
        upper = mean + z * se
        
        return (lower, upper)
    
    def _cohens_d(self, data: List[float]) -> float:
        """
        Calculate Cohen's d effect size.
        
        d = mean / std
        """
        if len(data) < 2:
            return 0.0
        
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return 0.0
        
        return mean / std
    
    def _calculate_power(
        self,
        sample_size: int,
        effect_size: float,
        std: float
    ) -> float:
        """
        Calculate statistical power.
        
        Simplified power calculation.
        """
        if sample_size < 2 or std == 0:
            return 0.0
        
        # Standard error
        se = std / math.sqrt(sample_size)
        
        # Effect in terms of standard errors
        z_effect = abs(effect_size * std) / se
        
        # Power = P(reject H0 | H1 is true)
        # Simplified: power based on effect size and sample size
        power = self._normal_cdf(z_effect - self._z_score(1 - self.significance_level/2))
        
        return max(0.0, min(1.0, power))
    
    def _check_assumptions(self, data: List[float]) -> Dict[str, bool]:
        """
        Check statistical assumptions.
        
        Returns:
            Dict of assumption -> valid
        """
        n = len(data)
        
        # Normality (simplified - use skewness and kurtosis)
        if n >= 8:
            skewness = self._skewness(data)
            kurtosis = self._kurtosis(data)
            normality = abs(skewness) < 1 and abs(kurtosis) < 3
        else:
            normality = True  # Not enough data
        
        # Independence (simplified - assume true)
        independence = True
        
        # Sample size (minimum for t-test)
        sample_size = n >= 5
        
        # Homogeneity of variance (not applicable for one-sample)
        
        return {
            "normality": normality,
            "independence": independence,
            "sample_size": sample_size
        }
    
    def _skewness(self, data: List[float]) -> float:
        """Calculate skewness"""
        if len(data) < 3:
            return 0.0
        
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return 0.0
        
        skew = sum((x - mean) ** 3 for x in data) / (n * std ** 3)
        return skew
    
    def _kurtosis(self, data: List[float]) -> float:
        """Calculate excess kurtosis"""
        if len(data) < 4:
            return 0.0
        
        n = len(data)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return 0.0
        
        kurt = sum((x - mean) ** 4 for x in data) / (n * std ** 4) - 3
        return kurt
    
    def _z_score(self, confidence: float) -> float:
        """Get z-score for confidence level"""
        # Simplified mapping
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
            0.999: 3.291
        }
        return z_scores.get(confidence, 1.96)
    
    def _normal_cdf(self, x: float) -> float:
        """Approximation of normal CDF"""
        # Abramowitz and Stegun approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911
        
        sign = -1 if x < 0 else 1
        x = abs(x) / math.sqrt(2)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)
    
    def compare_experiments(
        self,
        result1: StatisticalResult,
        result2: StatisticalResult
    ) -> Dict[str, Any]:
        """Compare two statistical results"""
        return {
            "p_values": [result1.p_value, result2.p_value],
            "effect_sizes": [result1.effect_size, result2.effect_size],
            "sample_sizes": [result1.sample_size, result2.sample_size],
            "power_diff": result1.power - result2.power,
            "recommendation": self._compare_recommendation(result1, result2)
        }
    
    def _compare_recommendation(
        self,
        r1: StatisticalResult,
        r2: StatisticalResult
    ) -> str:
        """Get recommendation based on comparison"""
        if r1.is_significant and not r2.is_significant:
            return "Result 1 is preferred (statistically significant)"
        elif r2.is_significant and not r1.is_significant:
            return "Result 2 is preferred (statistically significant)"
        elif r1.is_significant and r2.is_significant:
            if abs(r1.effect_size) > abs(r2.effect_size):
                return "Result 1 has larger effect size"
            else:
                return "Result 2 has larger effect size"
        else:
            return "Neither result is statistically significant"
    
    def get_interpretation(self, result: StatisticalResult) -> str:
        """Get human-readable interpretation"""
        if result.is_significant:
            if result.p_value < 0.01:
                strength = "very strong"
            elif result.p_value < 0.05:
                strength = "strong"
            else:
                strength = "moderate"
            
            return (
                f"{strength.capitalize()} statistical evidence that the observed "
                f"returns are different from zero (p={result.p_value:.4f}). "
                f"Effect size (Cohen's d)={result.effect_size:.3f}."
            )
        else:
            return (
                f"No statistically significant evidence that returns are different "
                f"from zero (p={result.p_value:.4f}). Cannot reject null hypothesis."
            )
