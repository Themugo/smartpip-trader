"""
Validation Framework
=================

Walk-forward, rolling window, out-of-sample, Monte Carlo, and Bootstrap validation.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ValidationType(Enum):
    """Types of validation"""
    WALK_FORWARD = "walk_forward"
    ROLLING_WINDOW = "rolling_window"
    OUT_OF_SAMPLE = "out_of_sample"
    MONTE_CARLO = "monte_carlo"
    BOOTSTRAP = "bootstrap"


@dataclass
class ValidationResult:
    """Result of a validation run"""
    validation_id: str
    validation_type: ValidationType
    timestamp: datetime
    metrics: Dict[str, float]
    statistics: Dict[str, float]
    is_significant: bool
    confidence_level: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "validation_type": self.validation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "statistics": self.statistics,
            "is_significant": self.is_significant,
            "confidence_level": self.confidence_level,
            "details": self.details
        }


@dataclass
class WalkForwardResult:
    """Result of walk-forward analysis"""
    window_results: List[Dict[str, Any]]
    consistency_ratio: float
    avg_sharpe: float
    avg_return: float
    worst_sharpe: float
    best_sharpe: float
    std_sharpe: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_count": len(self.window_results),
            "consistency_ratio": self.consistency_ratio,
            "avg_sharpe": self.avg_sharpe,
            "avg_return": self.avg_return,
            "worst_sharpe": self.worst_sharpe,
            "best_sharpe": self.best_sharpe,
            "std_sharpe": self.std_sharpe,
            "windows": self.window_results
        }


class WalkForwardValidator:
    """
    Walk-forward validation for strategy robustness.
    
    Splits data into rolling in-sample and out-of-sample windows.
    """
    
    def __init__(
        self,
        in_sample_days: int = 90,
        out_sample_days: int = 30,
        step_days: int = 7
    ):
        self.in_sample_days = in_sample_days
        self.out_sample_days = out_sample_days
        self.step_days = step_days
    
    def validate(
        self,
        strategy_func: Callable,
        data: List[Any],
        get_metrics: Callable[[List], Dict[str, float]]
    ) -> WalkForwardResult:
        """
        Run walk-forward validation.
        
        Args:
            strategy_func: Strategy to validate
            data: Historical data
            get_metrics: Function to compute metrics from trades
            
        Returns:
            WalkForwardResult
        """
        window_results = []
        sharpes = []
        returns = []
        
        # Calculate windows
        total_days = len(data)
        start = 0
        
        while start + self.in_sample_days + self.out_sample_days <= total_days:
            # In-sample window
            is_start = start
            is_end = start + self.in_sample_days
            
            # Out-of-sample window
            oos_start = is_end
            oos_end = min(oos_start + self.out_sample_days, total_days)
            
            # Get data
            is_data = data[is_start:is_end]
            oos_data = data[oos_start:oos_end]
            
            # Run strategy on in-sample
            is_metrics = get_metrics(is_data)
            
            # Run strategy on out-of-sample
            oos_metrics = get_metrics(oos_data)
            
            # Store results
            window_results.append({
                "in_sample": is_metrics,
                "out_sample": oos_metrics,
                "is_sharpe": is_metrics.get("sharpe_ratio", 0),
                "oos_sharpe": oos_metrics.get("sharpe_ratio", 0),
                "is_return": is_metrics.get("total_return", 0),
                "oos_return": oos_metrics.get("total_return", 0)
            })
            
            sharpes.append(oos_metrics.get("sharpe_ratio", 0))
            returns.append(oos_metrics.get("total_return", 0))
            
            # Step forward
            start += self.step_days
        
        # Calculate statistics
        sharpes = np.array(sharpes)
        returns = np.array(returns)
        
        positive_count = sum(1 for s in sharpes if s > 0)
        consistency = positive_count / len(sharpes) if sharpes.size > 0 else 0
        
        result = WalkForwardResult(
            window_results=window_results,
            consistency_ratio=consistency,
            avg_sharpe=float(np.mean(sharpes)) if sharpes.size > 0 else 0,
            avg_return=float(np.mean(returns)) if returns.size > 0 else 0,
            worst_sharpe=float(np.min(sharpes)) if sharpes.size > 0 else 0,
            best_sharpe=float(np.max(sharpes)) if sharpes.size > 0 else 0,
            std_sharpe=float(np.std(sharpes)) if sharpes.size > 0 else 0
        )
        
        logger.info(f"Walk-forward: {len(window_results)} windows, consistency={consistency:.2%}")
        
        return result


class RollingWindowValidator:
    """
    Rolling window validation with expanding or rolling windows.
    """
    
    def __init__(
        self,
        window_size: int = 100,
        step_size: int = 20,
        expanding: bool = True
    ):
        self.window_size = window_size
        self.step_size = step_size
        self.expanding = expanding
    
    def validate(
        self,
        strategy_func: Callable,
        data: List[Any],
        get_metrics: Callable[[List], Dict[str, float]]
    ) -> Dict[str, Any]:
        """Run rolling window validation"""
        results = []
        start = 0 if self.expanding else 0
        iteration = 0
        
        while start + self.window_size <= len(data):
            end = start + self.window_size
            window_data = data[start:end]
            
            metrics = get_metrics(window_data)
            
            results.append({
                "iteration": iteration,
                "start": start,
                "end": end,
                "metrics": metrics,
                "sharpe": metrics.get("sharpe_ratio", 0),
                "return": metrics.get("total_return", 0),
                "drawdown": metrics.get("max_drawdown", 0)
            })
            
            start += self.step_size
            iteration += 1
        
        # Calculate stability metrics
        sharpes = [r["sharpe"] for r in results]
        
        return {
            "iterations": len(results),
            "avg_sharpe": np.mean(sharpes) if sharpes else 0,
            "std_sharpe": np.std(sharpes) if sharpes else 0,
            "min_sharpe": np.min(sharpes) if sharpes else 0,
            "max_sharpe": np.max(sharpes) if sharpes else 0,
            "stability_score": 1.0 - (np.std(sharpes) / abs(np.mean(sharpes)) if sharpes and np.mean(sharpes) != 0 else 1.0),
            "windows": results
        }


class OutOfSampleValidator:
    """
    Out-of-sample validation with train/test splits.
    """
    
    def __init__(
        self,
        train_ratio: float = 0.7,
        n_splits: int = 5
    ):
        self.train_ratio = train_ratio
        self.n_splits = n_splits
    
    def validate(
        self,
        strategy_func: Callable,
        data: List[Any],
        get_metrics: Callable[[List], Dict[str, float]]
    ) -> Dict[str, Any]:
        """Run out-of-sample validation with multiple splits"""
        results = []
        gap = max(1, int(len(data) * 0.05))  # 5% gap
        
        for i in range(self.n_splits):
            # Calculate split point
            split_ratio = 0.5 + (i * 0.1)  # Vary split point
            split_point = int(len(data) * split_ratio * self.train_ratio)
            
            train_end = min(split_point, len(data) - gap)
            test_start = train_end + gap
            test_end = min(test_start + (len(data) - test_start) * self.train_ratio, len(data))
            
            if test_start >= test_end or train_end <= 0:
                continue
            
            train_data = data[:train_end]
            test_data = data[test_start:test_end]
            
            train_metrics = get_metrics(train_data)
            test_metrics = get_metrics(test_data)
            
            results.append({
                "split": i,
                "train_sharpe": train_metrics.get("sharpe_ratio", 0),
                "test_sharpe": test_metrics.get("sharpe_ratio", 0),
                "train_return": train_metrics.get("total_return", 0),
                "test_return": test_metrics.get("total_return", 0),
                "decay": train_metrics.get("sharpe_ratio", 0) - test_metrics.get("sharpe_ratio", 0)
            })
        
        # Calculate statistics
        train_sharpes = [r["train_sharpe"] for r in results]
        test_sharpes = [r["test_sharpe"] for r in results]
        
        # Statistical test
        if len(train_sharpes) >= 2 and len(test_sharpes) >= 2:
            _, p_value = stats.ttest_ind(train_sharpes, test_sharpes)
        else:
            p_value = 1.0
        
        return {
            "splits": len(results),
            "avg_train_sharpe": np.mean(train_sharpes) if train_sharpes else 0,
            "avg_test_sharpe": np.mean(test_sharpes) if test_sharpes else 0,
            "avg_decay": np.mean([r["decay"] for r in results]) if results else 0,
            "statistical_decay_p_value": p_value,
            "is_robust": p_value > 0.05,
            "results": results
        }


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy analysis.
    
    Simulates various market conditions and randomness.
    """
    
    def __init__(
        self,
        n_simulations: int = 1000,
        random_seed: int = 42
    ):
        self.n_simulations = n_simulations
        self.random_seed = random_seed
    
    def simulate_returns(
        self,
        historical_returns: List[float],
        n_periods: int = 252
    ) -> Dict[str, Any]:
        """Simulate future returns using historical distribution"""
        np.random.seed(self.random_seed)
        
        sim_returns = []
        sharpes = []
        max_dds = []
        
        mu = np.mean(historical_returns)
        sigma = np.std(historical_returns)
        
        for _ in range(self.n_simulations):
            # Generate simulated returns
            sim = np.random.normal(mu, sigma, n_periods)
            
            # Calculate metrics
            cumulative = np.cumprod(1 + sim)
            max_dd = self._calculate_max_drawdown(cumulative)
            
            sharpe = (np.mean(sim) / np.std(sim) * np.sqrt(252)) if np.std(sim) > 0 else 0
            
            sim_returns.append(cumulative[-1])
            sharpes.append(sharpe)
            max_dds.append(max_dd)
        
        sim_returns = np.array(sim_returns)
        sharpes = np.array(sharpes)
        max_dds = np.array(max_dds)
        
        return {
            "n_simulations": self.n_simulations,
            "final_returns": {
                "mean": np.mean(sim_returns),
                "median": np.median(sim_returns),
                "std": np.std(sim_returns),
                "percentile_5": np.percentile(sim_returns, 5),
                "percentile_95": np.percentile(sim_returns, 95)
            },
            "sharpe": {
                "mean": np.mean(sharpes),
                "median": np.median(sharpes),
                "std": np.std(sharpes),
                "percentile_5": np.percentile(sharpes, 5),
                "percentile_95": np.percentile(sharpes, 95)
            },
            "max_drawdown": {
                "mean": np.mean(max_dds),
                "median": np.median(max_dds),
                "std": np.std(max_dds),
                "worst": np.max(max_dds)
            },
            "probability_of_profit": np.mean(sim_returns > 1.0)
        }
    
    def simulate_slippage(
        self,
        base_slippage: float,
        volatility: float,
        n_trades: int = 100
    ) -> Dict[str, Any]:
        """Simulate slippage impact"""
        np.random.seed(self.random_seed)
        
        slippage_factor = 1 + np.random.normal(0, volatility, n_trades)
        actual_slippage = base_slippage * slippage_factor
        
        return {
            "base_slippage": base_slippage,
            "avg_slippage": np.mean(actual_slippage),
            "worst_slippage": np.max(actual_slippage),
            "slippage_std": np.std(actual_slippage),
            "impact_on_return": np.mean(actual_slippage) - base_slippage
        }
    
    def _calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        return abs(np.min(drawdown))


class BootstrapAnalyzer:
    """
    Bootstrap analysis for statistical inference.
    """
    
    def __init__(
        self,
        n_iterations: int = 10000,
        confidence_level: float = 0.95,
        random_seed: int = 42
    ):
        self.n_iterations = n_iterations
        self.confidence_level = confidence_level
        self.random_seed = random_seed
    
    def analyze(
        self,
        returns: List[float],
        metric_func: Callable[[List[float]], float] = None
    ) -> Dict[str, Any]:
        """
        Bootstrap analysis of returns.
        
        Args:
            returns: Historical returns
            metric_func: Function to calculate metric (default: Sharpe ratio)
        """
        np.random.seed(self.random_seed)
        
        if metric_func is None:
            def metric_func(r):
                if len(r) == 0 or np.std(r) == 0:
                    return 0
                return np.mean(r) / np.std(r) * np.sqrt(252)
        
        # Calculate observed metric
        observed = metric_func(returns)
        
        # Bootstrap
        bootstrap_metrics = []
        for _ in range(self.n_iterations):
            sample = np.random.choice(returns, size=len(returns), replace=True)
            bootstrap_metrics.append(metric_func(list(sample)))
        
        bootstrap_metrics = np.array(bootstrap_metrics)
        
        # Confidence interval
        alpha = 1 - self.confidence_level
        ci_lower = np.percentile(bootstrap_metrics, alpha / 2 * 100)
        ci_upper = np.percentile(bootstrap_metrics, (1 - alpha / 2) * 100)
        
        # P-value
        p_value = np.mean(bootstrap_metrics <= 0)
        
        # Bias
        bias = np.mean(bootstrap_metrics) - observed
        
        return {
            "observed": observed,
            "mean": np.mean(bootstrap_metrics),
            "std": np.std(bootstrap_metrics),
            "bias": bias,
            "confidence_interval": [ci_lower, ci_upper],
            "p_value": p_value,
            "is_significant": p_value < (1 - self.confidence_level),
            "confidence_level": self.confidence_level,
            "n_iterations": self.n_iterations
        }
    
    def compare_strategies(
        self,
        returns_a: List[float],
        returns_b: List[float]
    ) -> Dict[str, Any]:
        """Compare two strategies using bootstrap"""
        np.random.seed(self.random_seed)
        
        # Calculate difference
        observed_diff = np.mean(returns_a) - np.mean(returns_b)
        
        # Bootstrap difference
        diffs = []
        for _ in range(self.n_iterations):
            sample_a = np.random.choice(returns_a, size=len(returns_a), replace=True)
            sample_b = np.random.choice(returns_b, size=len(returns_b), replace=True)
            diffs.append(np.mean(sample_a) - np.mean(sample_b))
        
        diffs = np.array(diffs)
        
        # P-value for superiority
        p_value = np.mean(diffs <= 0)
        
        return {
            "observed_difference": observed_diff,
            "mean_difference": np.mean(diffs),
            "std_difference": np.std(diffs),
            "p_value": p_value,
            "is_better": p_value < 0.05,
            "confidence_a_over_b": 1 - p_value
        }
