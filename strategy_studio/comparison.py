"""
Strategy Comparison Center - Multi-Strategy Evaluation

Run multiple strategies over identical historical datasets and compare results.
"""

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from strategy_studio.lifecycle import LifecycleManager, LifecycleMetrics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for comparison"""
    # Basic metrics
    total_return: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Calculated metrics
    win_rate: float = 0
    expectancy: float = 0
    profit_factor: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    
    # Risk metrics
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    max_drawdown: float = 0
    max_drawdown_duration: int = 0  # in periods
    calmar_ratio: float = 0
    
    # Timing metrics
    avg_trade_duration: float = 0
    total_trading_time: float = 0
    trade_frequency: float = 0  # trades per day
    
    # Quality metrics
    calibration_score: float = 0
    recovery_factor: float = 0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "calmar_ratio": self.calmar_ratio,
            "avg_trade_duration": self.avg_trade_duration,
            "trade_frequency": self.trade_frequency,
            "calibration_score": self.calibration_score,
        }


@dataclass
class StrategyComparison:
    """Comparison result for multiple strategies"""
    id: str
    name: str
    created_at: datetime
    
    # Dataset info
    dataset_name: str
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    
    # Individual results
    results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Rankings
    rankings: Dict[str, int] = field(default_factory=dict)
    
    # Best strategy
    best_strategy_id: str = ""
    best_metric: str = "sharpe_ratio"
    
    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "dataset_name": self.dataset_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "symbols": self.symbols,
            "results": self.results,
            "rankings": self.rankings,
            "best_strategy_id": self.best_strategy_id,
            "summary": self.summary,
        }


@dataclass
class EquityPoint:
    """Single equity curve point"""
    timestamp: datetime
    equity: float
    drawdown: float = 0
    trade_id: Optional[str] = None


@dataclass
class ComparisonResult:
    """Result for a single strategy in comparison"""
    strategy_id: str
    strategy_name: str
    
    # Metrics
    metrics: PerformanceMetrics
    
    # Time series
    equity_curve: List[EquityPoint] = field(default_factory=list)
    drawdown_curve: List[EquityPoint] = field(default_factory=list)
    
    # Trades
    trades: List[Dict[str, Any]] = field(default_factory=list)
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "metrics": self.metrics.to_dict(),
            "trades_count": len(self.trades),
            "errors": self.errors,
        }


class StrategyComparisonCenter:
    """
    Strategy Comparison Center for multi-strategy evaluation.
    
    Features:
    - Run multiple strategies over identical data
    - Equity curve comparison
    - Drawdown comparison
    - Statistical comparison
    - Ranking by multiple metrics
    - Comparison reports
    """
    
    def __init__(self, lifecycle_manager: LifecycleManager):
        self._lifecycle = lifecycle_manager
        self._comparisons: Dict[str, StrategyComparison] = {}
        self._results_cache: Dict[str, ComparisonResult] = {}
    
    def compare_strategies(
        self,
        strategy_ids: List[str],
        dataset_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        name: Optional[str] = None,
        backtest_func: Optional[Callable] = None,
    ) -> StrategyComparison:
        """
        Compare multiple strategies over the same dataset.
        
        Args:
            strategy_ids: List of strategy IDs to compare
            dataset_name: Name of the dataset
            start_date: Start of backtest period
            end_date: End of backtest period
            symbols: Symbols to test
            name: Optional comparison name
            backtest_func: Function to run backtest (if None, uses metrics from lifecycle)
            
        Returns:
            StrategyComparison with results
        """
        comparison_id = str(uuid.uuid4())
        
        comparison = StrategyComparison(
            id=comparison_id,
            name=name or f"Comparison {len(self._comparisons) + 1}",
            created_at=datetime.utcnow(),
            dataset_name=dataset_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
        )
        
        results = {}
        
        for strategy_id in strategy_ids:
            strategy = self._lifecycle.get_strategy(strategy_id)
            if not strategy:
                logger.warning(f"Strategy not found: {strategy_id}")
                continue
            
            # Run or fetch results
            if backtest_func:
                result = backtest_func(strategy_id, start_date, end_date, symbols)
            else:
                # Use existing metrics
                result = self._create_result_from_metrics(strategy)
            
            results[strategy_id] = result
        
        comparison.results = {sid: r.to_dict() for sid, r in results.items()}
        
        # Calculate rankings
        comparison.rankings = self._calculate_rankings(results)
        
        # Find best strategy
        if results:
            best_id = min(
                comparison.rankings.keys(),
                key=lambda sid: comparison.rankings[sid]
            )
            comparison.best_strategy_id = best_id
        
        # Generate summary
        comparison.summary = self._generate_summary(results)
        
        self._comparisons[comparison_id] = comparison
        return comparison
    
    def _create_result_from_metrics(
        self,
        strategy: Dict[str, Any],
    ) -> ComparisonResult:
        """Create comparison result from lifecycle metrics"""
        metrics = strategy["metrics"]
        
        perf_metrics = PerformanceMetrics(
            total_return=metrics.total_return,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown=metrics.max_drawdown,
            win_rate=metrics.win_rate,
            expectancy=metrics.expectancy,
            profit_factor=metrics.profit_factor,
        )
        
        return ComparisonResult(
            strategy_id=strategy["id"],
            strategy_name=strategy["name"],
            metrics=perf_metrics,
        )
    
    def _calculate_rankings(self, results: Dict[str, ComparisonResult]) -> Dict[str, int]:
        """Calculate rankings for all metrics"""
        if not results:
            return {}
        
        # Metrics to rank by (higher is better)
        higher_better = [
            "sharpe_ratio", "sortino_ratio", "total_return", "win_rate",
            "expectancy", "profit_factor", "calibration_score",
        ]
        
        # Metrics to rank by (lower is better)
        lower_better = ["max_drawdown", "avg_trade_duration"]
        
        rankings = defaultdict(list)
        
        for metric in higher_better + lower_better:
            # Get values for this metric
            values = []
            for sid, result in results.items():
                value = getattr(result.metrics, metric, 0)
                values.append((sid, value))
            
            # Sort by value
            if metric in higher_better:
                values.sort(key=lambda x: x[1], reverse=True)
            else:
                values.sort(key=lambda x: x[1])
            
            # Assign ranks
            for rank, (sid, _) in enumerate(values, 1):
                rankings[sid].append((metric, rank))
        
        # Calculate average rank
        avg_ranks = {}
        for sid in results:
            ranks = [r for m, r in rankings[sid]]
            avg_ranks[sid] = sum(ranks) / len(ranks) if ranks else 0
        
        # Final ranking by average
        final_ranks = {}
        for rank, (sid, _) in enumerate(
            sorted(avg_ranks.items(), key=lambda x: x[1]),
            1
        ):
            final_ranks[sid] = rank
        
        return final_ranks
    
    def _generate_summary(
        self,
        results: Dict[str, ComparisonResult],
    ) -> Dict[str, Any]:
        """Generate comparison summary"""
        if not results:
            return {}
        
        # Aggregate metrics
        all_metrics = [r.metrics for r in results.values()]
        
        summary = {
            "strategies_compared": len(results),
            "best_by_sharpe": max(
                results.keys(),
                key=lambda sid: results[sid].metrics.sharpe_ratio,
                default=""
            ),
            "best_by_return": max(
                results.keys(),
                key=lambda sid: results[sid].metrics.total_return,
                default=""
            ),
            "best_by_drawdown": min(
                results.keys(),
                key=lambda sid: results[sid].metrics.max_drawdown,
                default=""
            ),
            "best_by_winrate": max(
                results.keys(),
                key=lambda sid: results[sid].metrics.win_rate,
                default=""
            ),
            "averages": {
                "sharpe_ratio": sum(m.sharpe_ratio for m in all_metrics) / len(all_metrics),
                "total_return": sum(m.total_return for m in all_metrics) / len(all_metrics),
                "max_drawdown": sum(m.max_drawdown for m in all_metrics) / len(all_metrics),
                "win_rate": sum(m.win_rate for m in all_metrics) / len(all_metrics),
            },
        }
        
        return summary
    
    def get_comparison(self, comparison_id: str) -> Optional[StrategyComparison]:
        """Get a comparison by ID"""
        return self._comparisons.get(comparison_id)
    
    def get_all_comparisons(self) -> List[StrategyComparison]:
        """Get all comparisons"""
        return list(self._comparisons.values())
    
    def get_leaderboard(
        self,
        metric: str = "sharpe_ratio",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get strategy leaderboard by metric"""
        leaderboard = []
        
        for strategy in self._lifecycle.get_all_strategies():
            metrics = strategy["metrics"]
            value = getattr(metrics, metric, 0)
            
            leaderboard.append({
                "strategy_id": strategy["id"],
                "strategy_name": strategy["name"],
                "state": strategy["state"].value,
                "metric": metric,
                "value": value,
            })
        
        # Sort by metric value (higher is better for most metrics)
        higher_better = [
            "sharpe_ratio", "sortino_ratio", "total_return", "win_rate",
            "expectancy", "profit_factor",
        ]
        
        reverse = metric in higher_better
        
        leaderboard.sort(key=lambda x: x["value"], reverse=reverse)
        
        # Add ranks
        for rank, entry in enumerate(leaderboard[:limit], 1):
            entry["rank"] = rank
        
        return leaderboard[:limit]
    
    def generate_report(self, comparison_id: str) -> Dict[str, Any]:
        """Generate a detailed comparison report"""
        comparison = self._comparisons.get(comparison_id)
        if not comparison:
            return {}
        
        report = {
            "comparison": comparison.to_dict(),
            "rankings_detailed": [],
            "charts_data": {},
        }
        
        # Detailed rankings
        for sid, result in comparison.results.items():
            entry = {
                "strategy_id": sid,
                "strategy_name": result["strategy_name"],
                "rank": comparison.rankings.get(sid, 0),
                "metrics": result["metrics"],
            }
            report["rankings_detailed"].append(entry)
        
        # Sort by rank
        report["rankings_detailed"].sort(key=lambda x: x["rank"])
        
        return report
