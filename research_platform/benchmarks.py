"""
Benchmark Library - Historical Performance Baselines

Complete benchmark system for comparing strategies against historical baselines.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks"""
    BUY_AND_HOLD = "buy_and_hold"
    RANDOM = "random"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SEASONAL = "seasonal"
    STATISTICAL = "statistical"
    CUSTOM = "custom"


class BenchmarkStatus(Enum):
    """Benchmark status"""
    DRAFT = "draft"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class BenchmarkMetrics:
    """Benchmark performance metrics"""
    # Core metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    
    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Trading metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    total_trades: int = 0
    avg_trade_duration: float = 0.0
    
    # Time metrics
    time_in_market: float = 0.0  # Percentage
    avg_holding_period: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "total_trades": self.total_trades,
            "avg_trade_duration": self.avg_trade_duration,
            "time_in_market": self.time_in_market,
            "avg_holding_period": self.avg_holding_period,
        }


@dataclass
class BenchmarkPeriod:
    """A period within the benchmark"""
    period_id: str
    name: str
    start_date: datetime
    end_date: datetime
    
    # Metrics for this period
    metrics: BenchmarkMetrics = field(default_factory=BenchmarkMetrics)
    
    # Market conditions
    market_regime: str = ""
    avg_volatility: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_id": self.period_id,
            "name": self.name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "metrics": self.metrics.to_dict(),
            "market_regime": self.market_regime,
            "avg_volatility": self.avg_volatility,
        }


@dataclass
class Benchmark:
    """A performance benchmark"""
    id: str
    name: str
    description: str
    benchmark_type: BenchmarkType
    
    # Time coverage (required, before optional config)
    start_date: datetime
    end_date: datetime
    
    # Configuration (with default)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Overall metrics
    metrics: BenchmarkMetrics = field(default_factory=BenchmarkMetrics)
    
    # Period breakdowns
    periods: List[BenchmarkPeriod] = field(default_factory=list)
    
    # Status
    status: BenchmarkStatus = BenchmarkStatus.DRAFT
    
    # Metadata
    author: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Usage
    comparison_count: int = 0
    last_compared_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "benchmark_type": self.benchmark_type.value,
            "config": self.config,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "metrics": self.metrics.to_dict(),
            "periods": [p.to_dict() for p in self.periods],
            "status": self.status.value,
            "author": self.author,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "comparison_count": self.comparison_count,
            "last_compared_at": self.last_compared_at.isoformat() if self.last_compared_at else None,
        }


@dataclass
class BenchmarkResult:
    """Result of comparing a strategy against a benchmark"""
    result_id: str
    benchmark_id: str
    benchmark_name: str
    
    # Strategy info
    strategy_id: str
    strategy_name: str
    strategy_version: str
    
    # Comparison period
    start_date: datetime
    end_date: datetime
    
    # Performance comparison
    strategy_metrics: BenchmarkMetrics
    benchmark_metrics: BenchmarkMetrics
    
    # Relative performance
    return_diff: float = 0.0  # Strategy return - Benchmark return
    sharpe_diff: float = 0.0
    drawdown_diff: float = 0.0
    
    # Outperformance statistics
    win_rate_vs_benchmark: float = 0.0  # % of periods strategy beat benchmark
    
    # Period-by-period
    period_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary
    outperforms_benchmark: bool = False
    confidence_level: float = 0.0  # Statistical confidence
    
    # Metadata
    compared_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "strategy_metrics": self.strategy_metrics.to_dict(),
            "benchmark_metrics": self.benchmark_metrics.to_dict(),
            "return_diff": self.return_diff,
            "sharpe_diff": self.sharpe_diff,
            "drawdown_diff": self.drawdown_diff,
            "win_rate_vs_benchmark": self.win_rate_vs_benchmark,
            "period_results": self.period_results,
            "outperforms_benchmark": self.outperforms_benchmark,
            "confidence_level": self.confidence_level,
            "compared_at": self.compared_at.isoformat(),
        }


class BenchmarkLibrary:
    """
    Benchmark Library for comparing strategies against historical baselines.
    
    Features:
    - Pre-built benchmarks (Buy & Hold, Random, etc.)
    - Custom benchmark creation
    - Period-based analysis
    - Statistical comparison
    - Performance tracking
    """
    
    def __init__(self, storage_path: str = "data/benchmarks"):
        self._storage_path = storage_path
        self._benchmarks: Dict[str, Benchmark] = {}
        self._results: List[BenchmarkResult] = []
        
        import os
        os.makedirs(storage_path, exist_ok=True)
        self._load_library()
        self._initialize_defaults()
    
    def _load_library(self) -> None:
        """Load benchmark library"""
        library_file = f"{self._storage_path}/library.json"
        
        try:
            if os.path.exists(library_file):
                with open(library_file, "r") as f:
                    data = json.load(f)
                
                # Load benchmarks
                for bm_data in data.get("benchmarks", []):
                    bm_data["created_at"] = datetime.fromisoformat(bm_data["created_at"])
                    bm_data["updated_at"] = datetime.fromisoformat(bm_data["updated_at"])
                    bm_data["start_date"] = datetime.fromisoformat(bm_data["start_date"])
                    bm_data["end_date"] = datetime.fromisoformat(bm_data["end_date"])
                    if bm_data.get("last_compared_at"):
                        bm_data["last_compared_at"] = datetime.fromisoformat(bm_data["last_compared_at"])
                    
                    # Parse metrics
                    bm_data["metrics"] = BenchmarkMetrics(**bm_data["metrics"])
                    
                    # Parse periods
                    for p in bm_data.get("periods", []):
                        p["start_date"] = datetime.fromisoformat(p["start_date"])
                        p["end_date"] = datetime.fromisoformat(p["end_date"])
                        p["metrics"] = BenchmarkMetrics(**p["metrics"])
                    bm_data["periods"] = [BenchmarkPeriod(**p) for p in bm_data.get("periods", [])]
                    
                    benchmark = Benchmark(**bm_data)
                    self._benchmarks[benchmark.id] = benchmark
                
                # Load results
                for result_data in data.get("results", []):
                    result_data["compared_at"] = datetime.fromisoformat(result_data["compared_at"])
                    result_data["start_date"] = datetime.fromisoformat(result_data["start_date"])
                    result_data["end_date"] = datetime.fromisoformat(result_data["end_date"])
                    result_data["strategy_metrics"] = BenchmarkMetrics(**result_data["strategy_metrics"])
                    result_data["benchmark_metrics"] = BenchmarkMetrics(**result_data["benchmark_metrics"])
                    result = BenchmarkResult(**result_data)
                    self._results.append(result)
                
                logger.info(f"Loaded {len(self._benchmarks)} benchmarks and {len(self._results)} results")
        except Exception as e:
            logger.warning(f"Could not load library: {e}")
    
    def _save_library(self) -> None:
        """Save benchmark library"""
        library_file = f"{self._storage_path}/library.json"
        
        data = {
            "benchmarks": [b.to_dict() for b in self._benchmarks.values()],
            "results": [r.to_dict() for r in self._results[-100:]],  # Keep last 100 results
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        with open(library_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _initialize_defaults(self) -> None:
        """Initialize default benchmarks"""
        if self._benchmarks:
            return
        
        # Buy and Hold benchmark
        buy_hold = Benchmark(
            id="bm_buy_hold",
            name="Buy and Hold",
            description="Traditional buy and hold strategy",
            benchmark_type=BenchmarkType.BUY_AND_HOLD,
            start_date=datetime.utcnow() - timedelta(days=365),
            end_date=datetime.utcnow(),
            status=BenchmarkStatus.ACTIVE,
            author="System",
            metrics=BenchmarkMetrics(
                total_return=0.15,
                annualized_return=0.15,
                volatility=0.20,
                sharpe_ratio=0.75,
                sortino_ratio=1.0,
                max_drawdown=-0.25,
                win_rate=0.55,
                profit_factor=1.3,
            ),
        )
        self._benchmarks[buy_hold.id] = buy_hold
        
        # Random benchmark
        random_bm = Benchmark(
            id="bm_random",
            name="Random Trading",
            description="Random entry/exit benchmark",
            benchmark_type=BenchmarkType.RANDOM,
            start_date=datetime.utcnow() - timedelta(days=365),
            end_date=datetime.utcnow(),
            status=BenchmarkStatus.ACTIVE,
            author="System",
            metrics=BenchmarkMetrics(
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.30,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=-0.40,
                win_rate=0.50,
                profit_factor=1.0,
                expectancy=0.0,
            ),
        )
        self._benchmarks[random_bm.id] = random_bm
        
        # Momentum benchmark
        momentum_bm = Benchmark(
            id="bm_momentum",
            name="Momentum Strategy",
            description="Simple momentum following benchmark",
            benchmark_type=BenchmarkType.MOMENTUM,
            start_date=datetime.utcnow() - timedelta(days=365),
            end_date=datetime.utcnow(),
            status=BenchmarkStatus.ACTIVE,
            author="System",
            metrics=BenchmarkMetrics(
                total_return=0.12,
                annualized_return=0.12,
                volatility=0.25,
                sharpe_ratio=0.60,
                sortino_ratio=0.80,
                max_drawdown=-0.30,
                win_rate=0.52,
                profit_factor=1.2,
            ),
        )
        self._benchmarks[momentum_bm.id] = momentum_bm
        
        self._save_library()
        logger.info("Initialized default benchmarks")
    
    # Benchmark Management
    def create_benchmark(
        self,
        name: str,
        description: str,
        benchmark_type: BenchmarkType,
        config: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        metrics: BenchmarkMetrics,
        author: str = "",
        tags: Optional[List[str]] = None,
    ) -> Benchmark:
        """Create a new benchmark"""
        benchmark = Benchmark(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            benchmark_type=benchmark_type,
            config=config,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            author=author,
            tags=tags or [],
        )
        
        self._benchmarks[benchmark.id] = benchmark
        self._save_library()
        
        logger.info(f"Created benchmark: {name}")
        return benchmark
    
    def update_benchmark(
        self,
        benchmark_id: str,
        metrics: Optional[BenchmarkMetrics] = None,
        status: Optional[BenchmarkStatus] = None,
    ) -> bool:
        """Update a benchmark"""
        benchmark = self._benchmarks.get(benchmark_id)
        if not benchmark:
            return False
        
        if metrics is not None:
            benchmark.metrics = metrics
        if status is not None:
            benchmark.status = status
        
        benchmark.updated_at = datetime.utcnow()
        self._save_library()
        return True
    
    def add_period(
        self,
        benchmark_id: str,
        name: str,
        start_date: datetime,
        end_date: datetime,
        metrics: BenchmarkMetrics,
        market_regime: str = "",
        avg_volatility: float = 0.0,
    ) -> bool:
        """Add a period to a benchmark"""
        benchmark = self._benchmarks.get(benchmark_id)
        if not benchmark:
            return False
        
        period = BenchmarkPeriod(
            period_id=str(uuid.uuid4()),
            name=name,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            market_regime=market_regime,
            avg_volatility=avg_volatility,
        )
        
        benchmark.periods.append(period)
        benchmark.updated_at = datetime.utcnow()
        self._save_library()
        return True
    
    def get_benchmark(self, benchmark_id: str) -> Optional[Benchmark]:
        """Get a benchmark by ID"""
        return self._benchmarks.get(benchmark_id)
    
    # Comparison
    def compare(
        self,
        benchmark_id: str,
        strategy_id: str,
        strategy_name: str,
        strategy_version: str,
        start_date: datetime,
        end_date: datetime,
        strategy_metrics: BenchmarkMetrics,
    ) -> BenchmarkResult:
        """Compare a strategy against a benchmark"""
        benchmark = self._benchmarks.get(benchmark_id)
        if not benchmark:
            raise ValueError(f"Benchmark {benchmark_id} not found")
        
        # Create result
        result = BenchmarkResult(
            result_id=str(uuid.uuid4()),
            benchmark_id=benchmark_id,
            benchmark_name=benchmark.name,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            start_date=start_date,
            end_date=end_date,
            strategy_metrics=strategy_metrics,
            benchmark_metrics=benchmark.metrics,
        )
        
        # Calculate differences
        result.return_diff = strategy_metrics.total_return - benchmark.metrics.total_return
        result.sharpe_diff = strategy_metrics.sharpe_ratio - benchmark.metrics.sharpe_ratio
        result.drawdown_diff = strategy_metrics.max_drawdown - benchmark.metrics.max_drawdown
        
        # Determine if outperforms
        result.outperforms_benchmark = (
            result.return_diff > 0 and
            result.sharpe_diff > 0 and
            result.drawdown_diff > 0  # Less negative = better
        )
        
        # Calculate win rate vs benchmark (simplified)
        result.win_rate_vs_benchmark = 0.5  # Would need period data for accurate calculation
        
        # Calculate confidence (simplified statistical measure)
        if strategy_metrics.total_trades > 30:
            result.confidence_level = min(0.95, 0.5 + strategy_metrics.total_trades / 100)
        else:
            result.confidence_level = 0.5
        
        # Update benchmark usage
        benchmark.comparison_count += 1
        benchmark.last_compared_at = datetime.utcnow()
        
        self._results.append(result)
        self._save_library()
        
        return result
    
    def get_comparison_history(
        self,
        benchmark_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[BenchmarkResult]:
        """Get comparison history"""
        results = self._results
        
        if benchmark_id:
            results = [r for r in results if r.benchmark_id == benchmark_id]
        if strategy_id:
            results = [r for r in results if r.strategy_id == strategy_id]
        
        return sorted(results, key=lambda r: r.compared_at, reverse=True)[:limit]
    
    # Search
    def search_benchmarks(
        self,
        query: Optional[str] = None,
        benchmark_types: Optional[List[BenchmarkType]] = None,
        statuses: Optional[List[BenchmarkStatus]] = None,
        tags: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 50,
    ) -> List[Benchmark]:
        """Search benchmarks"""
        results = list(self._benchmarks.values())
        
        if query:
            query_lower = query.lower()
            results = [
                b for b in results
                if query_lower in b.name.lower()
                or query_lower in b.description.lower()
            ]
        
        if benchmark_types:
            results = [b for b in results if b.benchmark_type in benchmark_types]
        
        if statuses:
            results = [b for b in results if b.status in statuses]
        
        if tags:
            results = [b for b in results if any(t in b.tags for t in tags)]
        
        if date_range:
            start, end = date_range
            results = [b for b in results
                      if b.start_date >= start and b.end_date <= end]
        
        # Sort by comparison count
        results.sort(key=lambda b: b.comparison_count, reverse=True)
        return results[:limit]
    
    def get_active_benchmarks(self) -> List[Benchmark]:
        """Get all active benchmarks"""
        return [b for b in self._benchmarks.values() if b.status == BenchmarkStatus.ACTIVE]
    
    def get_benchmark_summary(self, benchmark_id: str) -> Dict[str, Any]:
        """Get comprehensive benchmark summary"""
        benchmark = self._benchmarks.get(benchmark_id)
        if not benchmark:
            return {}
        
        # Get recent comparisons
        comparisons = self.get_comparison_history(benchmark_id=benchmark_id, limit=10)
        
        # Calculate average performance vs benchmark
        avg_return_diff = 0.0
        avg_sharpe_diff = 0.0
        outperform_count = 0
        
        if comparisons:
            avg_return_diff = sum(c.return_diff for c in comparisons) / len(comparisons)
            avg_sharpe_diff = sum(c.sharpe_diff for c in comparisons) / len(comparisons)
            outperform_count = sum(1 for c in comparisons if c.outperforms_benchmark)
        
        return {
            "benchmark": benchmark.to_dict(),
            "total_comparisons": benchmark.comparison_count,
            "recent_comparisons": len(comparisons),
            "avg_return_diff": avg_return_diff,
            "avg_sharpe_diff": avg_sharpe_diff,
            "outperform_rate": outperform_count / len(comparisons) if comparisons else 0,
            "period_count": len(benchmark.periods),
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        benchmarks = list(self._benchmarks.values())
        
        return {
            "total_benchmarks": len(benchmarks),
            "by_type": {
                btype.value: sum(1 for b in benchmarks if b.benchmark_type == btype)
                for btype in BenchmarkType
            },
            "by_status": {
                status.value: sum(1 for b in benchmarks if b.status == status)
                for status in BenchmarkStatus
            },
            "active_benchmarks": sum(1 for b in benchmarks if b.status == BenchmarkStatus.ACTIVE),
            "total_comparisons": sum(b.comparison_count for b in benchmarks),
            "total_results": len(self._results),
        }


import os
