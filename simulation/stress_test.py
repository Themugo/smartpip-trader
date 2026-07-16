"""
Stress Testing Framework
=====================

Stress test trading strategies under adverse conditions.
"""

import time
import random
import threading
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class StressTestConfig:
    """Configuration for stress test"""
    name: str
    duration_seconds: float = 60
    
    # Load settings
    orders_per_second: float = 10
    concurrent_agents: int = 1
    
    # Failure injection
    inject_failures: bool = True
    failure_rate: float = 0.1  # 10% of orders affected
    
    # Network conditions
    min_latency_ms: float = 10
    max_latency_ms: float = 500
    network_failure_rate: float = 0.05
    
    # Market conditions
    volatility_multiplier: float = 1.0  # 1.0 = normal
    trend_strength: float = 0.5  # 0 = random, 1 = strong trend
    
    # Resource constraints
    simulate_high_load: bool = True
    max_memory_mb: float = 100


@dataclass
class StressTestResult:
    """Results from stress test"""
    test_id: str
    config: Dict[str, Any]
    start_time: float
    end_time: float
    duration_seconds: float
    
    # Order statistics
    total_orders: int
    successful_orders: int
    failed_orders: int
    rejected_orders: int
    
    # Latency statistics
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    
    # Throughput
    orders_per_second_actual: float
    peak_orders_per_second: float
    
    # Failures
    failures_injected: int
    failures_recovered: int
    
    # Strategy performance
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    
    # Resilience assessment
    resilience_grade: str  # A, B, C, D, F
    resilience_score: float
    fragile_strategies: List[str]
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "config": self.config,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "total_orders": self.total_orders,
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_orders,
            "rejected_orders": self.rejected_orders,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "orders_per_second_actual": self.orders_per_second_actual,
            "peak_orders_per_second": self.peak_orders_per_second,
            "failures_injected": self.failures_injected,
            "failures_recovered": self.failures_recovered,
            "total_pnl": self.total_pnl,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "resilience_grade": self.resilience_grade,
            "resilience_score": self.resilience_score,
            "fragile_strategies": self.fragile_strategies,
            "recommendations": self.recommendations,
        }


class StressTestRunner:
    """
    Runs stress tests on trading strategies.
    
    Tests:
    - High load conditions
    - Network failures
    - Market volatility
    - Resource constraints
    - Recovery scenarios
    """
    
    def __init__(
        self,
        strategy,
        simulator,
        failure_injector=None
    ):
        self.strategy = strategy
        self.simulator = simulator
        self.failure_injector = failure_injector
        self._is_running = False
        self._threads: List[threading.Thread] = []
    
    def run_stress_test(
        self,
        config: StressTestConfig,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> StressTestResult:
        """
        Run a stress test.
        
        Args:
            config: Test configuration
            on_progress: Progress callback
            
        Returns:
            Stress test results
        """
        self._is_running = True
        start_time = time.time()
        
        # Initialize state
        latencies: List[float] = []
        order_results: List[Dict[str, Any]] = []
        pnl_values: List[float] = []
        current_pnl = 0.0
        peak_pnl = 0.0
        max_drawdown = 0.0
        
        failures_injected = 0
        failures_recovered = 0
        
        # Start failure injector if enabled
        if self.failure_injector and config.inject_failures:
            self.failure_injector.start()
        
        # Generate market data
        price = 50000.0
        order_interval = 1.0 / config.orders_per_second if config.orders_per_second > 0 else 1.0
        
        try:
            elapsed = 0.0
            orders_this_second = 0
            peak_orders_per_second = 0
            second_start = time.time()
            
            while elapsed < config.duration_seconds and self._is_running:
                # Generate market tick
                volatility = 0.02 * config.volatility_multiplier
                price_change = random.gauss(0, volatility)
                price *= (1 + price_change)
                
                market_tick = {
                    "symbol": "BTC/USD",
                    "price": price,
                    "volatility": volatility,
                    "timestamp": time.time(),
                }
                
                # Inject failures occasionally
                if self.failure_injector and random.random() < config.failure_rate:
                    self._inject_random_failure(config)
                    failures_injected += 1
                
                # Strategy processing
                try:
                    signals = self.strategy.on_tick(market_tick)
                    
                    for signal in signals:
                        order_start = time.time()
                        
                        # Submit order
                        order = self.simulator.submit_order(
                            symbol=signal.get("symbol", "BTC/USD"),
                            side=1 if signal.get("side") == "buy" else -1,
                            order_type=1,
                            quantity=signal.get("quantity", 1.0),
                            market_price=price,
                            volatility=volatility,
                        )
                        
                        order_latency = (time.time() - order_start) * 1000
                        latencies.append(order_latency)
                        
                        # Record result
                        result = {
                            "timestamp": time.time(),
                            "order_id": order.order_id,
                            "status": order.status.value,
                            "latency_ms": order_latency,
                            "slippage_bps": order.slippage_bps,
                        }
                        order_results.append(result)
                        
                        # Track PnL
                        if order.status.value == "filled":
                            current_pnl += random.gauss(10, 5)  # Simulated PnL
                            orders_this_second += 1
                        else:
                            current_pnl -= 5  # Cost of failure
                        
                        # Track drawdown
                        if current_pnl > peak_pnl:
                            peak_pnl = current_pnl
                        drawdown = peak_pnl - current_pnl
                        if drawdown > max_drawdown:
                            max_drawdown = drawdown
                        
                        pnl_values.append(current_pnl)
                
                except Exception as e:
                    logger.error(f"Strategy error during stress test: {e}")
                
                # Track peak throughput
                if time.time() - second_start >= 1.0:
                    if orders_this_second > peak_orders_per_second:
                        peak_orders_per_second = orders_this_second
                    orders_this_second = 0
                    second_start = time.time()
                
                # Progress callback
                if on_progress:
                    on_progress(elapsed / config.duration_seconds)
                
                elapsed = time.time() - start_time
                time.sleep(order_interval)
        
        finally:
            self._is_running = False
            if self.failure_injector:
                self.failure_injector.stop()
        
        end_time = time.time()
        
        # Calculate statistics
        total_orders = len(order_results)
        successful = sum(1 for r in order_results if r["status"] == "filled")
        failed = sum(1 for r in order_results if r["status"] in ["rejected", "partial"])
        
        # Latency percentiles
        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            avg_lat = statistics.mean(latencies)
            p50 = sorted_lat[int(n * 0.5)]
            p95 = sorted_lat[int(n * 0.95)]
            p99 = sorted_lat[int(n * 0.99)]
            max_lat = max(latencies)
        else:
            avg_lat = p50 = p95 = p99 = max_lat = 0
        
        # Throughput
        actual_ops = total_orders / (end_time - start_time) if end_time > start_time else 0
        
        # Performance metrics
        wins = sum(1 for p in pnl_values if p > 0)
        win_rate = wins / len(pnl_values) if pnl_values else 0
        
        # Sharpe ratio
        if len(pnl_values) > 1:
            returns = [pnl_values[i] - pnl_values[i-1] for i in range(1, len(pnl_values))]
            mean_return = statistics.mean(returns) if returns else 0
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0
            sharpe = mean_return / std_return if std_return > 0 else 0
        else:
            sharpe = 0
        
        # Resilience assessment
        resilience_score = self._calculate_resilience_score(
            total_orders, successful, failed,
            avg_lat, failures_injected
        )
        resilience_grade = self._get_resilience_grade(resilience_score)
        fragile = self._identify_fragile_strategies(
            total_orders, successful, failed, avg_lat, max_drawdown
        )
        recommendations = self._generate_recommendations(
            total_orders, successful, failed,
            avg_lat, p95, max_drawdown, resilience_score
        )
        
        return StressTestResult(
            test_id=f"stress_test_{int(start_time)}",
            config=config.__dict__,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=end_time - start_time,
            total_orders=total_orders,
            successful_orders=successful,
            failed_orders=failed,
            rejected_orders=0,
            avg_latency_ms=avg_lat,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            max_latency_ms=max_lat,
            orders_per_second_actual=actual_ops,
            peak_orders_per_second=peak_orders_per_second,
            failures_injected=failures_injected,
            failures_recovered=failures_recovered,
            total_pnl=current_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            resilience_grade=resilience_grade,
            resilience_score=resilience_score,
            fragile_strategies=fragile,
            recommendations=recommendations,
        )
    
    def _inject_random_failure(self, config: StressTestConfig) -> None:
        """Inject a random failure"""
        from .failures import FailureType
        
        failures = [
            FailureType.NETWORK_TIMEOUT,
            FailureType.NETWORK_ERROR,
            FailureType.API_ERROR,
            FailureType.RATE_LIMIT,
            FailureType.PARTIAL_FILL,
            FailureType.ORDER_REJECTED,
        ]
        
        failure = random.choice(failures)
        self.failure_injector.inject_failure(failure, duration_ms=500)
    
    def _calculate_resilience_score(
        self,
        total: int,
        successful: int,
        failed: int,
        avg_latency: float,
        failures: int
    ) -> float:
        """Calculate resilience score (0-100)"""
        score = 100.0
        
        # Success rate contribution (40%)
        if total > 0:
            success_rate = successful / total
            score -= (1 - success_rate) * 40
        
        # Latency contribution (30%)
        if avg_latency > 500:
            score -= 30
        elif avg_latency > 200:
            score -= 20
        elif avg_latency > 100:
            score -= 10
        
        # Failure handling contribution (30%)
        if failures > 0:
            recovery_rate = 0.8  # Assume 80% recovery
            score -= (1 - recovery_rate) * 30
        
        return max(0, min(100, score))
    
    def _get_resilience_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _identify_fragile_strategies(
        self,
        total: int,
        successful: int,
        failed: int,
        avg_latency: float,
        max_drawdown: float
    ) -> List[str]:
        """Identify fragile strategies that shouldn't be deployed"""
        fragile = []
        
        # High failure rate
        if total > 0 and failed / total > 0.1:
            fragile.append("High failure rate under stress")
        
        # High latency
        if avg_latency > 300:
            fragile.append("Excessive latency in adverse conditions")
        
        # High drawdown
        if max_drawdown > 100:
            fragile.append("Unacceptable drawdown under stress")
        
        # Low success rate
        if total > 0 and successful / total < 0.8:
            fragile.append("Low success rate indicates fragile strategy")
        
        return fragile
    
    def _generate_recommendations(
        self,
        total: int,
        successful: int,
        failed: int,
        avg_lat: float,
        p95_lat: float,
        max_drawdown: float,
        resilience_score: float
    ) -> List[str]:
        """Generate recommendations based on results"""
        recs = []
        
        if total > 0:
            fail_rate = failed / total
            if fail_rate > 0.1:
                recs.append(f"High failure rate: {fail_rate:.1%}. Review error handling.")
            elif fail_rate > 0.05:
                recs.append(f"Moderate failure rate: {fail_rate:.1%}. Monitor closely.")
        
        if avg_lat > 200:
            recs.append(f"High average latency: {avg_lat:.0f}ms. Optimize execution path.")
        
        if p95_lat > 500:
            recs.append(f"High P95 latency: {p95_lat:.0f}ms. Review timeout settings.")
        
        if max_drawdown > 50:
            recs.append(f"Significant drawdown: ${max_drawdown:.2f}. Review position sizing.")
        
        if resilience_score < 70:
            recs.append(f"Resilience score ({resilience_score:.0f}) below threshold. Improve error handling.")
        
        if resilience_score >= 90:
            recs.append("Excellent resilience. Strategy is production-ready.")
        elif resilience_score >= 80:
            recs.append("Good resilience. Strategy suitable for deployment.")
        
        if not recs:
            recs.append("No major issues detected. Continue monitoring.")
        
        return recs
    
    def stop(self) -> None:
        """Stop the stress test"""
        self._is_running = False
        for thread in self._threads:
            thread.join(timeout=1)


class MarketConditionSimulator:
    """
    Simulates various market conditions for testing.
    """
    
    @staticmethod
    def generate_trending_market(
        start_price: float,
        duration_seconds: float,
        trend_strength: float = 0.01
    ) -> List[Dict[str, Any]]:
        """Generate trending market data"""
        ticks = []
        price = start_price
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            drift = trend_strength * price
            noise = random.gauss(0, 0.001 * price)
            price += drift + noise
            
            ticks.append({
                "price": price,
                "timestamp": time.time(),
                "trend": "up" if drift > 0 else "down"
            })
            time.sleep(0.1)
        
        return ticks
    
    @staticmethod
    def generate_volatile_market(
        start_price: float,
        duration_seconds: float,
        volatility: float = 0.03
    ) -> List[Dict[str, Any]]:
        """Generate volatile market data"""
        ticks = []
        price = start_price
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            change = random.gauss(0, volatility * price)
            price += change
            
            ticks.append({
                "price": price,
                "volatility": volatility,
                "timestamp": time.time(),
            })
            time.sleep(0.1)
        
        return ticks
    
    @staticmethod
    def generate_ranging_market(
        start_price: float,
        duration_seconds: float,
        range_pct: float = 0.02
    ) -> List[Dict[str, Any]]:
        """Generate ranging market data"""
        ticks = []
        price = start_price
        end_time = time.time() + duration_seconds
        mid_price = start_price
        high = mid_price * (1 + range_pct)
        low = mid_price * (1 - range_pct)
        direction = 1
        
        while time.time() < end_time:
            # Mean reversion
            if price > high:
                direction = -1
            elif price < low:
                direction = 1
            
            change = direction * abs(random.gauss(0, 0.001 * price))
            price += change
            
            ticks.append({
                "price": price,
                "range_high": high,
                "range_low": low,
                "timestamp": time.time(),
            })
            time.sleep(0.1)
        
        return ticks
