"""
Benchmark Comparator
===================

Compares experiment results against benchmarks.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks"""
    BUY_AND_HOLD = "buy_and_hold"
    RANDOM = "random"
    SIMPLE_MA = "simple_ma"
    PREVIOUS_STRATEGY = "previous_strategy"
    MARKET_INDEX = "market_index"


@dataclass
class BenchmarkResult:
    """Result of benchmark comparison"""
    id: str
    experiment_id: str
    benchmark_type: BenchmarkType
    strategy_return: float
    benchmark_return: float
    excess_return: float
    information_ratio: float
    win_rate_vs_benchmark: float
    max_drawdown_vs_benchmark: float
    is_outperforming: bool
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "benchmark_type": self.benchmark_type.value,
            "strategy_return": self.strategy_return,
            "benchmark_return": self.benchmark_return,
            "excess_return": self.excess_return,
            "information_ratio": self.information_ratio,
            "is_outperforming": self.is_outperforming
        }


class BenchmarkComparator:
    """
    Compares strategy results against benchmarks.
    """
    
    def __init__(self, default_benchmark: str = "buy_and_hold"):
        self.default_benchmark = BenchmarkType(default_benchmark)
        self.benchmark_history: Dict[str, List[float]] = {}
    
    def compare(
        self,
        experiment_result: Any,
        benchmark_type: Optional[BenchmarkType] = None
    ) -> BenchmarkResult:
        """
        Compare experiment result against benchmark.
        
        Args:
            experiment_result: ExperimentResult
            benchmark_type: Type of benchmark to use
            
        Returns:
            BenchmarkResult
        """
        benchmark_type = benchmark_type or self.default_benchmark
        
        # Generate benchmark returns
        benchmark_returns = self._generate_benchmark_returns(
            benchmark_type,
            experiment_result.returns
        )
        
        # Calculate metrics
        strategy_return = experiment_result.metrics.get("total_return", 0)
        benchmark_return = np.sum(benchmark_returns)
        
        # Excess return
        excess_return = strategy_return - benchmark_return
        
        # Information ratio
        tracking_error = np.std(np.array(experiment_result.returns) - np.array(benchmark_returns))
        ir = excess_return / tracking_error if tracking_error > 0 else 0
        
        # Win rate vs benchmark
        wins_vs_benchmark = sum(
            1 for s, b in zip(experiment_result.returns, benchmark_returns)
            if s > b
        )
        win_rate_vs_benchmark = wins_vs_benchmark / len(experiment_result.returns) if experiment_result.returns else 0
        
        # Max drawdown comparison
        strategy_dd = experiment_result.metrics.get("max_drawdown", 0)
        benchmark_dd = self._calculate_max_drawdown(benchmark_returns)
        dd_vs_benchmark = strategy_dd - benchmark_dd
        
        # Is outperforming
        is_outperforming = excess_return > 0 and ir > 0
        
        # Confidence (based on sample size)
        confidence = min(1.0, len(experiment_result.returns) / 100)
        
        result = BenchmarkResult(
            id=str(uuid4()),
            experiment_id=experiment_result.id,
            benchmark_type=benchmark_type,
            strategy_return=strategy_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            information_ratio=ir,
            win_rate_vs_benchmark=win_rate_vs_benchmark,
            max_drawdown_vs_benchmark=dd_vs_benchmark,
            is_outperforming=is_outperforming,
            confidence=confidence
        )
        
        logger.info(
            f"Benchmark comparison: Strategy={strategy_return:.2%}, "
            f"Benchmark={benchmark_return:.2%}, IR={ir:.3f}"
        )
        
        return result
    
    def _generate_benchmark_returns(
        self,
        benchmark_type: BenchmarkType,
        strategy_returns: List[float]
    ) -> List[float]:
        """Generate benchmark returns for comparison"""
        n = len(strategy_returns)
        
        if benchmark_type == BenchmarkType.BUY_AND_HOLD:
            return self._buy_and_hold_returns(n)
        elif benchmark_type == BenchmarkType.RANDOM:
            return self._random_returns(n)
        elif benchmark_type == BenchmarkType.SIMPLE_MA:
            return self._simple_ma_returns(n)
        elif benchmark_type == BenchmarkType.PREVIOUS_STRATEGY:
            return self._previous_strategy_returns(n)
        else:
            return self._buy_and_hold_returns(n)
    
    def _buy_and_hold_returns(self, n: int) -> List[float]:
        """Generate buy and hold benchmark returns"""
        # Assume small positive drift
        daily_return = 0.0002  # ~5% annual
        volatility = 0.01
        
        returns = []
        cumulative_return = 0
        for _ in range(n):
            r = np.random.normal(daily_return, volatility)
            cumulative_return *= (1 + r)
            returns.append(r)
        
        return returns
    
    def _random_returns(self, n: int) -> List[float]:
        """Generate random returns (null hypothesis)"""
        return list(np.random.normal(0, 0.01, n))
    
    def _simple_ma_returns(self, n: int) -> List[float]:
        """Generate simple moving average strategy returns"""
        # MA crossover returns
        returns = []
        for _ in range(n):
            # Simplified: assume MA strategy returns slightly positive
            r = np.random.normal(0.0001, 0.008)
            returns.append(r)
        
        return returns
    
    def _previous_strategy_returns(self, n: int) -> List[float]:
        """Generate previous (baseline) strategy returns"""
        # Use historical benchmark if available
        if "previous" in self.benchmark_history:
            hist = self.benchmark_history["previous"]
            if len(hist) >= n:
                return hist[-n:]
        
        # Otherwise use simple MA
        return self._simple_ma_returns(n)
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate max drawdown from returns"""
        equity = [1.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        
        peak = equity[0]
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def compare_multiple_benchmarks(
        self,
        experiment_result: Any
    ) -> Dict[str, BenchmarkResult]:
        """Compare against all benchmark types"""
        results = {}
        
        for benchmark_type in BenchmarkType:
            result = self.compare(experiment_result, benchmark_type)
            results[benchmark_type.value] = result
        
        return results
    
    def get_best_benchmark(
        self,
        experiment_result: Any
    ) -> BenchmarkResult:
        """Get comparison against best performing benchmark"""
        comparisons = self.compare_multiple_benchmarks(experiment_result)
        
        best = max(comparisons.values(), key=lambda x: x.excess_return)
        return best
    
    def rank_strategies(
        self,
        results: List[Any]
    ) -> List[Dict[str, Any]]:
        """Rank multiple strategy results by performance"""
        rankings = []
        
        for result in results:
            benchmark = self.compare(result)
            
            rankings.append({
                "strategy_id": result.id,
                "total_return": benchmark.strategy_return,
                "excess_return": benchmark.excess_return,
                "information_ratio": benchmark.information_ratio,
                "is_outperforming": benchmark.is_outperforming,
                "rank": 0  # Will be set after sorting
            })
        
        # Sort by excess return
        rankings.sort(key=lambda x: x["excess_return"], reverse=True)
        
        # Assign ranks
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        
        return rankings
    
    def get_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Get summary statistics for benchmark comparisons"""
        if not results:
            return {}
        
        outperforming = sum(1 for r in results if r.is_outperforming)
        
        return {
            "total_comparisons": len(results),
            "outperforming_count": outperforming,
            "outperforming_pct": outperforming / len(results) if results else 0,
            "avg_excess_return": np.mean([r.excess_return for r in results]),
            "avg_information_ratio": np.mean([r.information_ratio for r in results]),
            "best_performing": max(results, key=lambda x: x.excess_return).experiment_id if results else None
        }
