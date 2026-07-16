"""
Execution Simulator
================

Realistic execution simulation with configurable failure modes.
"""

import time
import random
import threading
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class SimulatedOrder:
    """Simulated order with execution parameters"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0
    average_price: float = 0
    submitted_at: float = 0
    filled_at: Optional[float] = None
    rejection_reason: Optional[str] = None
    slippage_bps: float = 0


@dataclass
class SimulatedFill:
    """Simulated fill"""
    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: float
    latency_ms: float
    slippage_bps: float


@dataclass
class SimulationConfig:
    """Configuration for execution simulation"""
    # Latency settings (in milliseconds)
    min_latency_ms: float = 10
    max_latency_ms: float = 500
    latency_p99_ms: float = 200
    
    # Failure rates (0.0 - 1.0)
    order_rejection_rate: float = 0.01
    partial_fill_rate: float = 0.05
    network_failure_rate: float = 0.02
    websocket_drop_rate: float = 0.01
    
    # Clock drift (seconds per minute)
    clock_drift_rate: float = 0.0  # 0 = no drift
    
    # Resource constraints
    max_orders_per_second: float = 100
    max_concurrent_orders: int = 10
    
    # Market data delays (milliseconds)
    market_data_delay_ms: float = 50
    
    # Slippage model
    base_slippage_bps: float = 1.0
    volatility_slippage_factor: float = 0.5
    
    # Partial fill settings
    min_partial_fill_pct: float = 0.1
    max_partial_fill_pct: float = 0.9
    
    # Recovery simulation
    recovery_time_ms: float = 1000
    recovery_success_rate: float = 0.95


@dataclass
class SimulationResult:
    """Results from a simulation run"""
    result_id: str
    duration_seconds: float
    total_orders: int
    filled_orders: int
    rejected_orders: int
    partial_fills: int
    cancelled_orders: int
    
    # Latency metrics
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    
    # Slippage metrics
    avg_slippage_bps: float
    max_slippage_bps: float
    
    # Failure metrics
    network_failures: int
    websocket_drops: int
    api_failures: int
    clock_drift_seconds: float
    
    # Resilience score (0-100)
    resilience_score: float
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "duration_seconds": self.duration_seconds,
            "total_orders": self.total_orders,
            "filled_orders": self.filled_orders,
            "rejected_orders": self.rejected_orders,
            "partial_fills": self.partial_fills,
            "cancelled_orders": self.cancelled_orders,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "avg_slippage_bps": self.avg_slippage_bps,
            "max_slippage_bps": self.max_slippage_bps,
            "network_failures": self.network_failures,
            "websocket_drops": self.websocket_drops,
            "api_failures": self.api_failures,
            "clock_drift_seconds": self.clock_drift_seconds,
            "resilience_score": self.resilience_score,
            "recommendations": self.recommendations,
        }


class ExecutionSimulator:
    """
    Realistic execution simulator for trading strategies.
    
    Simulates:
    - Network latency
    - Order rejections
    - Partial fills
    - Network failures
    - Clock drift
    - Market data delays
    """
    
    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self._orders: Dict[str, SimulatedOrder] = {}
        self._fills: List[SimulatedFill] = []
        self._order_counter = 0
        self._fill_counter = 0
        self._start_time = 0
        self._simulated_time = 0
        self._lock = threading.Lock()
        
        # Statistics
        self._latencies: List[float] = []
        self._slippages: List[float] = []
        self._network_failures = 0
        self._websocket_drops = 0
        self._api_failures = 0
        
        # Clock drift state
        self._drift_offset = 0.0
    
    def start(self) -> None:
        """Start the simulator"""
        self._start_time = time.time()
        self._simulated_time = self._start_time
        logger.info("Execution simulator started")
    
    def stop(self) -> None:
        """Stop the simulator"""
        logger.info("Execution simulator stopped")
    
    def _get_simulated_time(self) -> float:
        """Get current simulated time with clock drift"""
        if self.config.clock_drift_rate != 0:
            elapsed = time.time() - self._start_time
            self._drift_offset = elapsed * self.config.clock_drift_rate / 60
        return self._simulated_time + self._drift_offset
    
    def _simulate_latency(self) -> float:
        """Simulate network latency using realistic distribution"""
        # Use a combination of uniform and exponential for realistic latency
        base_latency = random.uniform(
            self.config.min_latency_ms,
            self.config.max_latency_ms
        )
        
        # Occasionally add high latency spikes
        if random.random() < 0.01:  # 1% chance of spike
            base_latency *= random.uniform(2, 5)
        
        return base_latency
    
    def _simulate_slippage(self, price: float, volatility: float = 0.02) -> float:
        """Simulate slippage based on price and volatility"""
        # Base slippage + volatility factor
        slippage = self.config.base_slippage_bps
        
        # Add volatility component
        slippage += volatility * self.config.volatility_slippage_factor * 100
        
        # Add randomness
        slippage *= random.uniform(0.5, 1.5)
        
        return slippage
    
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        market_price: float = 100.0,
        volatility: float = 0.02
    ) -> SimulatedOrder:
        """
        Submit a simulated order.
        
        Returns order with simulated execution.
        """
        with self._lock:
            self._order_counter += 1
            order_id = f"sim_{self._order_counter}"
            
            order = SimulatedOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=OrderStatus.PENDING,
                submitted_at=self._get_simulated_time(),
            )
            
            self._orders[order_id] = order
        
        # Simulate latency
        latency = self._simulate_latency()
        time.sleep(latency / 1000)  # Convert to seconds
        
        # Check for order rejection
        if random.random() < self.config.order_rejection_rate:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = random.choice([
                "INSUFFICIENT_MARGIN",
                "MARKET_CLOSED",
                "RATE_LIMIT_EXCEEDED",
                "POSITION_LIMIT_EXCEEDED",
                "RISK_CHECK_FAILED",
            ])
            self._api_failures += 1
            return order
        
        # Check for network failure
        if random.random() < self.config.network_failure_rate:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = "NETWORK_ERROR"
            self._network_failures += 1
            return order
        
        # Check for partial fill
        if random.random() < self.config.partial_fill_rate:
            fill_qty = quantity * random.uniform(
                self.config.min_partial_fill_pct,
                self.config.max_partial_fill_pct
            )
            
            slippage = self._simulate_slippage(market_price, volatility)
            
            fill = SimulatedFill(
                fill_id=f"fill_{self._fill_counter}",
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=fill_qty,
                price=market_price * (1 + slippage / 10000),
                timestamp=self._get_simulated_time(),
                latency_ms=latency,
                slippage_bps=slippage,
            )
            
            order.status = OrderStatus.PARTIAL
            order.filled_quantity = fill_qty
            order.average_price = fill.price
            order.slippage_bps = slippage
            
            self._fills.append(fill)
            self._fill_counter += 1
            self._latencies.append(latency)
            self._slippages.append(slippage)
            
            return order
        
        # Full fill (simulate with execution delay)
        time.sleep(random.uniform(5, 50) / 1000)  # Small additional delay
        
        slippage = self._simulate_slippage(market_price, volatility)
        fill_price = market_price * (1 + slippage / 10000)
        
        fill = SimulatedFill(
            fill_id=f"fill_{self._fill_counter}",
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=fill_price,
            timestamp=self._get_simulated_time(),
            latency_ms=latency,
            slippage_bps=slippage,
        )
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = quantity
        order.average_price = fill_price
        order.slippage_bps = slippage
        order.filled_at = self._get_simulated_time()
        
        self._fills.append(fill)
        self._fill_counter += 1
        self._latencies.append(latency)
        self._slippages.append(slippage)
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return False
            
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
            
            return False
    
    def get_market_data_delay(self) -> float:
        """Get simulated market data delay"""
        base_delay = self.config.market_data_delay_ms
        # Add jitter
        return base_delay * random.uniform(0.8, 1.2)
    
    def simulate_websocket_drop(self) -> bool:
        """Simulate WebSocket disconnection"""
        if random.random() < self.config.websocket_drop_rate:
            self._websocket_drops += 1
            return True
        return False
    
    def simulate_network_interruption(self, duration_ms: float = 1000) -> None:
        """Simulate network interruption"""
        self._network_failures += 1
        time.sleep(duration_ms / 1000)
    
    def get_order(self, order_id: str) -> Optional[SimulatedOrder]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_all_orders(self) -> List[SimulatedOrder]:
        """Get all orders"""
        return list(self._orders.values())
    
    def get_all_fills(self) -> List[SimulatedFill]:
        """Get all fills"""
        return self._fills.copy()
    
    def calculate_result(self) -> SimulationResult:
        """Calculate simulation results"""
        duration = time.time() - self._start_time
        
        # Count orders by status
        total = len(self._orders)
        filled = sum(1 for o in self._orders.values() if o.status == OrderStatus.FILLED)
        rejected = sum(1 for o in self._orders.values() if o.status == OrderStatus.REJECTED)
        partial = sum(1 for o in self._orders.values() if o.status == OrderStatus.PARTIAL)
        cancelled = sum(1 for o in self._orders.values() if o.status == OrderStatus.CANCELLED)
        
        # Latency percentiles
        if self._latencies:
            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)
            avg_lat = statistics.mean(self._latencies)
            p50 = sorted_latencies[int(n * 0.5)]
            p95 = sorted_latencies[int(n * 0.95)]
            p99 = sorted_latencies[int(n * 0.99)]
            max_lat = max(self._latencies)
        else:
            avg_lat = p50 = p95 = p99 = max_lat = 0
        
        # Slippage
        avg_slip = statistics.mean(self._slippages) if self._slippages else 0
        max_slip = max(self._slippages) if self._slippages else 0
        
        # Calculate resilience score (0-100)
        resilience = self._calculate_resilience_score(
            total, filled, rejected, partial,
            avg_lat, self._network_failures, self._websocket_drops
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            total, filled, rejected, partial,
            avg_lat, p95, avg_slip, self._network_failures
        )
        
        return SimulationResult(
            result_id=f"sim_{int(time.time())}",
            duration_seconds=duration,
            total_orders=total,
            filled_orders=filled,
            rejected_orders=rejected,
            partial_fills=partial,
            cancelled_orders=cancelled,
            avg_latency_ms=avg_lat,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            max_latency_ms=max_lat,
            avg_slippage_bps=avg_slip,
            max_slippage_bps=max_slip,
            network_failures=self._network_failures,
            websocket_drops=self._websocket_drops,
            api_failures=self._api_failures,
            clock_drift_seconds=self._drift_offset,
            resilience_score=resilience,
            recommendations=recommendations,
        )
    
    def _calculate_resilience_score(
        self,
        total: int,
        filled: int,
        rejected: int,
        partial: int,
        avg_latency: float,
        network_failures: int,
        websocket_drops: int
    ) -> float:
        """Calculate resilience score (0-100)"""
        score = 100.0
        
        # Deduction for rejections
        if total > 0:
            rejection_rate = rejected / total
            score -= rejection_rate * 30
        
        # Deduction for partial fills
        if total > 0:
            partial_rate = partial / total
            score -= partial_rate * 10
        
        # Deduction for high latency
        if avg_latency > 200:
            score -= 10
        elif avg_latency > 100:
            score -= 5
        
        # Deduction for network failures
        score -= min(20, network_failures * 2)
        score -= min(10, websocket_drops * 3)
        
        return max(0, min(100, score))
    
    def _generate_recommendations(
        self,
        total: int,
        filled: int,
        rejected: int,
        partial: int,
        avg_latency: float,
        p95_latency: float,
        avg_slippage: float,
        network_failures: int
    ) -> List[str]:
        """Generate recommendations based on results"""
        recs = []
        
        if total > 0:
            rejection_rate = rejected / total
            if rejection_rate > 0.1:
                recs.append(f"High order rejection rate: {rejection_rate:.1%}. Consider checking margin and position limits.")
            elif rejection_rate > 0.05:
                recs.append(f"Moderate rejection rate: {rejection_rate:.1%}. Monitor for system issues.")
        
        if avg_latency > 200:
            recs.append(f"High average latency: {avg_latency:.0f}ms. Consider optimizing order routing.")
        
        if p95_latency > 500:
            recs.append(f"High P95 latency: {p95_latency:.0f}ms. Review network conditions.")
        
        if avg_slippage > 5:
            recs.append(f"High slippage: {avg_slippage:.1f} bps. Review execution strategy.")
        
        if network_failures > 5:
            recs.append(f"Multiple network failures: {network_failures}. Implement circuit breakers.")
        
        if partial > 0:
            partial_rate = partial / total
            if partial_rate > 0.1:
                recs.append(f"Frequent partial fills: {partial_rate:.1%}. Review order sizing.")
        
        if not recs:
            recs.append("Simulation completed with good resilience. Strategy appears robust.")
        
        return recs
    
    def reset(self) -> None:
        """Reset simulator state"""
        with self._lock:
            self._orders.clear()
            self._fills.clear()
            self._latencies.clear()
            self._slippages.clear()
            self._network_failures = 0
            self._websocket_drops = 0
            self._api_failures = 0
            self._order_counter = 0
            self._fill_counter = 0
            self._drift_offset = 0
            self._start_time = 0
            self._simulated_time = 0


class StrategySimulator:
    """
    Simulates a trading strategy under adverse conditions.
    
    Wraps a strategy and executes it with the simulator.
    """
    
    def __init__(
        self,
        strategy,
        simulator: ExecutionSimulator
    ):
        self.strategy = strategy
        self.simulator = simulator
        self._results: List[Dict[str, Any]] = []
    
    def run_simulation(
        self,
        market_data: List[Dict[str, Any]],
        duration_seconds: float = 60
    ) -> SimulationResult:
        """Run a simulation with the strategy"""
        self.simulator.start()
        start = time.time()
        
        for tick in market_data:
            if time.time() - start > duration_seconds:
                break
            
            # Strategy processing
            signals = self.strategy.on_tick(tick)
            
            # Execute signals
            for signal in signals:
                order = self.simulator.submit_order(
                    symbol=signal.get("symbol", "BTC/USD"),
                    side=OrderSide.BUY if signal.get("side") == "buy" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=signal.get("quantity", 1.0),
                    market_price=tick.get("price", 50000),
                    volatility=tick.get("volatility", 0.02),
                )
                
                self._results.append({
                    "signal": signal,
                    "order": order.__dict__,
                    "timestamp": time.time(),
                })
            
            # Simulate market data delay
            time.sleep(self.simulator.get_market_data_delay_ms() / 1000)
        
        self.simulator.stop()
        return self.simulator.calculate_result()
