"""
Benchmark & Deployment Gate
=========================

Automatic benchmark comparison and deployment gating.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ComparisonResult(Enum):
    """Result of benchmark comparison"""
    SIGNIFICANTLY_BETTER = "significantly_better"
    MARGINALLY_BETTER = "marginally_better"
    EQUIVALENT = "equivalent"
    MARGINALLY_WORSE = "marginally_worse"
    SIGNIFICANTLY_WORSE = "significantly_worse"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class BenchmarkMetrics:
    """Metrics from a benchmark or strategy"""
    strategy_name: str
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    expectancy: float
    trade_count: int
    n_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "trade_count": self.trade_count,
            "n_days": self.n_days
        }


@dataclass
class ComparisonReport:
    """Report of benchmark comparison"""
    comparison_id: str
    timestamp: datetime
    new_strategy: BenchmarkMetrics
    baseline_strategy: BenchmarkMetrics
    comparison_result: ComparisonResult
    
    # Statistical tests
    t_statistic: float
    p_value: float
    effect_size: float
    
    # Metric comparisons
    metric_differences: Dict[str, float]
    metric_improvements: Dict[str, bool]
    
    # Recommendation
    can_deploy: bool
    deployment_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "timestamp": self.timestamp.isoformat(),
            "new_strategy": self.new_strategy.to_dict(),
            "baseline_strategy": self.baseline_strategy.to_dict(),
            "comparison_result": self.comparison_result.value,
            "t_statistic": self.t_statistic,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "metric_differences": self.metric_differences,
            "metric_improvements": self.metric_improvements,
            "can_deploy": self.can_deploy,
            "deployment_reason": self.deployment_reason
        }


class BenchmarkComparator:
    """
    Compares strategies against benchmarks and production baselines.
    """
    
    def __init__(
        self,
        confidence_level: float = 0.95,
        minimum_improvement: float = 0.05
    ):
        self.confidence_level = confidence_level
        self.minimum_improvement = minimum_improvement
    
    def compare(
        self,
        new_strategy_name: str,
        new_metrics: Dict[str, float],
        baseline_name: str,
        baseline_metrics: Dict[str, float],
        new_trades: List[Dict] = None,
        baseline_trades: List[Dict] = None
    ) -> ComparisonReport:
        """
        Compare new strategy against baseline.
        
        Args:
            new_strategy_name: Name of new strategy
            new_metrics: Performance metrics for new strategy
            baseline_name: Name of baseline
            baseline_metrics: Performance metrics for baseline
            new_trades: Optional trade data for statistical tests
            baseline_trades: Optional baseline trade data
            
        Returns:
            ComparisonReport
        """
        # Build metrics objects
        new = BenchmarkMetrics(
            strategy_name=new_strategy_name,
            total_return=new_metrics.get("total_return", 0),
            annualized_return=new_metrics.get("annualized_return", 0),
            sharpe_ratio=new_metrics.get("sharpe_ratio", 0),
            sortino_ratio=new_metrics.get("sortino_ratio", 0),
            max_drawdown=new_metrics.get("max_drawdown", 0),
            win_rate=new_metrics.get("win_rate", 0),
            profit_factor=new_metrics.get("profit_factor", 0),
            expectancy=new_metrics.get("expectancy", 0),
            trade_count=int(new_metrics.get("trade_count", 0)),
            n_days=int(new_metrics.get("n_days", 0))
        )
        
        baseline = BenchmarkMetrics(
            strategy_name=baseline_name,
            total_return=baseline_metrics.get("total_return", 0),
            annualized_return=baseline_metrics.get("annualized_return", 0),
            sharpe_ratio=baseline_metrics.get("sharpe_ratio", 0),
            sortino_ratio=baseline_metrics.get("sortino_ratio", 0),
            max_drawdown=baseline_metrics.get("max_drawdown", 0),
            win_rate=baseline_metrics.get("win_rate", 0),
            profit_factor=baseline_metrics.get("profit_factor", 0),
            expectancy=baseline_metrics.get("expectancy", 0),
            trade_count=int(baseline_metrics.get("trade_count", 0)),
            n_days=int(baseline_metrics.get("n_days", 0))
        )
        
        # Calculate metric differences
        metric_differences = {
            "return_diff": new.total_return - baseline.total_return,
            "sharpe_diff": new.sharpe_ratio - baseline.sharpe_ratio,
            "drawdown_diff": baseline.max_drawdown - new.max_drawdown,  # Lower is better
            "win_rate_diff": new.win_rate - baseline.win_rate,
            "profit_factor_diff": new.profit_factor - baseline.profit_factor,
            "expectancy_diff": new.expectancy - baseline.expectancy
        }
        
        # Determine improvements
        metric_improvements = {
            "return": new.total_return > baseline.total_return * (1 + self.minimum_improvement),
            "sharpe": new.sharpe_ratio > baseline.sharpe_ratio * (1 + self.minimum_improvement),
            "drawdown": new.max_drawdown < baseline.max_drawdown * (1 - self.minimum_improvement),
            "win_rate": new.win_rate > baseline.win_rate + self.minimum_improvement,
            "profit_factor": new.profit_factor > baseline.profit_factor * (1 + self.minimum_improvement)
        }
        
        # Statistical comparison
        if new_trades and baseline_trades:
            new_returns = np.array([t.get("pnl", 0) for t in new_trades])
            baseline_returns = np.array([t.get("pnl", 0) for t in baseline_trades])
            
            t_stat, p_value = stats.ttest_ind(new_returns, baseline_returns)
            effect_size = (np.mean(new_returns) - np.mean(baseline_returns)) / np.sqrt(
                (np.std(new_returns)**2 + np.std(baseline_returns)**2) / 2
            )
        else:
            t_stat, p_value, effect_size = 0.0, 1.0, 0.0
        
        # Determine comparison result
        comparison_result = self._determine_result(
            new, baseline, t_stat, p_value, effect_size, metric_improvements
        )
        
        # Determine deployment recommendation
        can_deploy, reason = self._determine_deployment(
            comparison_result, new, baseline, metric_improvements
        )
        
        return ComparisonReport(
            comparison_id=str(uuid4()),
            timestamp=datetime.now(),
            new_strategy=new,
            baseline_strategy=baseline,
            comparison_result=comparison_result,
            t_statistic=t_stat,
            p_value=p_value,
            effect_size=effect_size,
            metric_differences=metric_differences,
            metric_improvements=metric_improvements,
            can_deploy=can_deploy,
            deployment_reason=reason
        )
    
    def _determine_result(
        self,
        new: BenchmarkMetrics,
        baseline: BenchmarkMetrics,
        t_stat: float,
        p_value: float,
        effect_size: float,
        improvements: Dict[str, bool]
    ) -> ComparisonResult:
        """Determine comparison result"""
        # Check for significant improvement
        n_improvements = sum(improvements.values())
        
        if p_value < 0.05 and t_stat > 0 and effect_size > 0.5:
            if n_improvements >= 4:
                return ComparisonResult.SIGNIFICANTLY_BETTER
            elif n_improvements >= 2:
                return ComparisonResult.MARGINALLY_BETTER
        
        # Check for equivalence
        if abs(t_stat) < 1.96 and n_improvements >= 2:
            return ComparisonResult.EQUIVALENT
        
        # Check for worse performance
        if p_value < 0.05 and t_stat < 0:
            if n_improvements <= 1:
                return ComparisonResult.SIGNIFICANTLY_WORSE
            else:
                return ComparisonResult.MARGINALLY_WORSE
        
        return ComparisonResult.INSUFFICIENT_DATA
    
    def _determine_deployment(
        self,
        result: ComparisonResult,
        new: BenchmarkMetrics,
        baseline: BenchmarkMetrics,
        improvements: Dict[str, bool]
    ) -> tuple[bool, str]:
        """Determine if new strategy should be deployed"""
        n_improvements = sum(improvements.values())
        
        if result == ComparisonResult.SIGNIFICANTLY_BETTER:
            return True, "Statistically significant improvement in multiple metrics"
        
        elif result == ComparisonResult.MARGINALLY_BETTER:
            if n_improvements >= 3:
                return True, "Improvement in multiple metrics"
            else:
                return False, "Only marginal improvement, requires further validation"
        
        elif result == ComparisonResult.EQUIVALENT:
            # Check if risk-adjusted returns are better
            if new.sharpe_ratio > baseline.sharpe_ratio:
                return True, "Equivalent returns with better risk-adjusted performance"
            else:
                return False, "No clear advantage over baseline"
        
        elif result == ComparisonResult.MARGINALLY_WORSE:
            return False, "Marginal degradation in performance"
        
        elif result == ComparisonResult.SIGNIFICANTLY_WORSE:
            return False, "Significant degradation - baseline is superior"
        
        else:
            return False, "Insufficient data for comparison"


class DeploymentGate:
    """
    Deployment gate that prevents deployment of inferior strategies.
    """
    
    def __init__(
        self,
        minimum_sharpe: float = 0.5,
        maximum_drawdown: float = 0.20,
        minimum_win_rate: float = 0.45,
        minimum_trades: int = 30,
        comparison_confidence: float = 0.95
    ):
        self.minimum_sharpe = minimum_sharpe
        self.maximum_drawdown = maximum_drawdown
        self.minimum_win_rate = minimum_win_rate
        self.minimum_trades = minimum_trades
        self.comparison_confidence = comparison_confidence
        
        self.benchmark_comparator = BenchmarkComparator(
            confidence_level=comparison_confidence
        )
        
        self.deployment_history: List[Dict] = []
    
    def can_deploy(
        self,
        strategy_name: str,
        metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Check if strategy can be deployed.
        
        Args:
            strategy_name: Name of strategy
            metrics: Strategy metrics
            baseline_metrics: Optional baseline metrics for comparison
            
        Returns:
            Dict with deployment decision and details
        """
        reasons = []
        blockers = []
        
        # Check minimum requirements
        if metrics.get("sharpe_ratio", 0) < self.minimum_sharpe:
            blockers.append(f"Sharpe ratio {metrics.get('sharpe_ratio', 0):.2f} below minimum {self.minimum_sharpe}")
        
        if metrics.get("max_drawdown", 1) > self.maximum_drawdown:
            blockers.append(f"Max drawdown {metrics.get('max_drawdown', 0):.1%} exceeds maximum {self.maximum_drawdown:.1%}")
        
        if metrics.get("win_rate", 0) < self.minimum_win_rate:
            blockers.append(f"Win rate {metrics.get('win_rate', 0):.1%} below minimum {self.minimum_win_rate:.1%}")
        
        if metrics.get("trade_count", 0) < self.minimum_trades:
            blockers.append(f"Trade count {metrics.get('trade_count', 0)} below minimum {self.minimum_trades}")
        
        # Check against baseline
        comparison_report = None
        if baseline_metrics and blockers == []:
            comparison_report = self.benchmark_comparator.compare(
                new_strategy_name=strategy_name,
                new_metrics=metrics,
                baseline_name="production",
                baseline_metrics=baseline_metrics
            )
            
            if not comparison_report.can_deploy:
                blockers.append(comparison_report.deployment_reason)
        
        # Determine decision
        can_deploy = len(blockers) == 0
        
        if can_deploy:
            if comparison_report:
                reasons.append(comparison_report.deployment_reason)
            else:
                reasons.append("All gate criteria met")
        
        result = {
            "can_deploy": can_deploy,
            "strategy_name": strategy_name,
            "blockers": blockers,
            "reasons": reasons,
            "comparison_report": comparison_report.to_dict() if comparison_report else None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log deployment attempt
        self.deployment_history.append(result)
        
        return result
    
    def get_deployment_history(self) -> List[Dict]:
        """Get deployment history"""
        return self.deployment_history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get deployment gate statistics"""
        total = len(self.deployment_history)
        approved = sum(1 for r in self.deployment_history if r["can_deploy"])
        rejected = total - approved
        
        return {
            "total_attempts": total,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": approved / total if total > 0 else 0
        }
