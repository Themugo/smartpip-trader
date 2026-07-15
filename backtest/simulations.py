"""
Market Simulations
=================

Execution delay, slippage, and transaction cost simulations.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for simulations"""
    base_latency_ms: float = 50.0
    latency_volatility_ms: float = 20.0
    base_slippage_pct: float = 0.0001  # 1 pip for forex
    slippage_volatility_pct: float = 0.00005
    commission_per_lot: float = 5.0
    spread_cost_pct: float = 0.0001
    funding_rate: float = 0.0001  # Daily


class ExecutionSimulator:
    """
    Simulates execution delays and market impact.
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.execution_log = []
    
    def simulate_execution(
        self,
        signal_price: float,
        direction: str,  # "buy" or "sell"
        timestamp: datetime,
        volatility: float = 0.01
    ) -> Dict[str, Any]:
        """
        Simulate order execution with delay and price impact.
        
        Returns execution price and latency.
        """
        # Calculate latency
        latency_ms = max(
            1,
            random.gauss(
                self.config.base_latency_ms,
                self.config.latency_volatility_ms
            )
        )
        
        # Calculate latency delay (seconds)
        delay_seconds = latency_ms / 1000
        
        # Calculate price impact during delay
        # Higher volatility = more price movement during delay
        price_impact = signal_price * volatility * random.uniform(-1, 1) * (delay_seconds / 1)
        
        # Determine execution price
        if direction == "buy":
            execution_price = signal_price + abs(price_impact)
        else:
            execution_price = signal_price - abs(price_impact)
        
        # Slippage
        slippage = execution_price * random.gauss(
            self.config.base_slippage_pct,
            self.config.slippage_volatility_pct
        )
        
        if direction == "buy":
            execution_price += slippage
        else:
            execution_price -= slippage
        
        result = {
            "signal_price": signal_price,
            "execution_price": execution_price,
            "slippage": slippage,
            "latency_ms": latency_ms,
            "execution_time": timestamp + timedelta(seconds=delay_seconds),
            "price_impact": price_impact,
            "direction": direction
        }
        
        self.execution_log.append(result)
        
        return result
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_log:
            return {}
        
        latencies = [e["latency_ms"] for e in self.execution_log]
        slippage = [e["slippage"] for e in self.execution_log]
        
        return {
            "total_executions": len(self.execution_log),
            "avg_latency_ms": np.mean(latencies),
            "max_latency_ms": np.max(latencies),
            "min_latency_ms": np.min(latencies),
            "avg_slippage": np.mean(slippage),
            "worst_slippage": np.max(slippage) if slippage else 0
        }


class SlippageSimulator:
    """
    Simulates slippage based on order size and market conditions.
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
    
    def calculate_slippage(
        self,
        base_price: float,
        order_size: float,
        market_volatility: float = 0.01,
        liquidity_factor: float = 1.0  # < 1 = thin liquidity, > 1 = deep
    ) -> Dict[str, Any]:
        """
        Calculate expected slippage.
        
        Args:
            base_price: Base price of asset
            order_size: Size of order
            market_volatility: Current market volatility
            liquidity_factor: Market liquidity (default 1.0)
        """
        # Base slippage increases with order size
        size_slippage = base_price * self.config.base_slippage_pct * (order_size / 100000)
        
        # Volatility multiplier
        vol_multiplier = 1 + market_volatility * 10
        
        # Liquidity adjustment (thin liquidity = more slippage)
        liquidity_adjustment = 1 / max(liquidity_factor, 0.1)
        
        # Total slippage
        total_slippage = size_slippage * vol_multiplier * liquidity_adjustment
        
        # Expected price impact
        expected_impact = base_price * total_slippage
        
        return {
            "base_price": base_price,
            "order_size": order_size,
            "expected_slippage": expected_impact,
            "slippage_pct": total_slippage,
            "size_factor": order_size / 100000,
            "vol_multiplier": vol_multiplier,
            "liquidity_adjustment": liquidity_adjustment
        }
    
    def simulate_slippage_distribution(
        self,
        base_price: float,
        order_size: float,
        n_simulations: int = 1000
    ) -> Dict[str, Any]:
        """Simulate distribution of slippage outcomes"""
        slippage = []
        
        for _ in range(n_simulations):
            result = self.calculate_slippage(
                base_price,
                order_size,
                market_volatility=random.uniform(0.005, 0.02),
                liquidity_factor=random.uniform(0.5, 1.5)
            )
            slippage.append(result["expected_slippage"])
        
        slippage = np.array(slippage)
        
        return {
            "mean": np.mean(slippage),
            "median": np.median(slippage),
            "std": np.std(slippage),
            "percentile_5": np.percentile(slippage, 5),
            "percentile_95": np.percentile(slippage, 95),
            "worst_case": np.max(slippage),
            "best_case": np.min(slippage)
        }


class TransactionCostSimulator:
    """
    Simulates all transaction costs including commissions, spreads, and funding.
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.trade_log = []
    
    def calculate_round_trip_cost(
        self,
        entry_price: float,
        exit_price: float,
        position_size: float,
        n_lots: float,
        holding_days: float = 0,
        direction: str = "long"
    ) -> Dict[str, Any]:
        """
        Calculate total round-trip transaction costs.
        
        Returns breakdown of all costs.
        """
        # Entry costs
        entry_commission = self.config.commission_per_lot * n_lots
        entry_spread = entry_price * self.config.spread_cost_pct * position_size
        
        # Exit costs
        exit_commission = self.config.commission_per_lot * n_lots
        exit_spread = exit_price * self.config.spread_cost_pct * position_size
        
        # Funding cost (for long positions)
        if direction == "long" and holding_days > 0:
            funding_cost = position_size * self.config.funding_rate * holding_days
        else:
            funding_cost = 0
        
        # Slippage (estimate)
        avg_price = (entry_price + exit_price) / 2
        slippage = avg_price * self.config.base_slippage_pct * 2 * position_size
        
        # Total costs
        total_cost = (
            entry_commission + entry_spread +
            exit_commission + exit_spread +
            funding_cost + slippage
        )
        
        # Cost as percentage of position
        position_value = avg_price * position_size
        cost_pct = total_cost / position_value if position_value > 0 else 0
        
        return {
            "entry_commission": entry_commission,
            "exit_commission": exit_commission,
            "spread_cost": entry_spread + exit_spread,
            "funding_cost": funding_cost,
            "slippage_cost": slippage,
            "total_cost": total_cost,
            "cost_pct": cost_pct,
            "cost_per_lot": total_cost / n_lots if n_lots > 0 else 0
        }
    
    def analyze_trade(
        self,
        entry_price: float,
        exit_price: float,
        position_size: float,
        n_lots: float,
        direction: str,
        holding_days: float = 0
    ) -> Dict[str, Any]:
        """Analyze a trade with full cost breakdown"""
        gross_pnl = (exit_price - entry_price) * position_size
        if direction == "short":
            gross_pnl = -gross_pnl
        
        costs = self.calculate_round_trip_cost(
            entry_price, exit_price, position_size, n_lots, holding_days, direction
        )
        
        net_pnl = gross_pnl - costs["total_cost"]
        gross_roi = gross_pnl / (entry_price * position_size)
        net_roi = net_pnl / (entry_price * position_size)
        
        return {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "position_size": position_size,
            "n_lots": n_lots,
            "direction": direction,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "gross_roi": gross_roi,
            "net_roi": net_roi,
            "cost_breakdown": costs,
            "breakeven_move": costs["total_cost"] / position_size,
            "breakeven_pct": costs["cost_pct"]
        }
    
    def estimate_annual_costs(
        self,
        avg_trade_size: float,
        trades_per_day: float,
        avg_holding_days: float,
        n_days: int = 252
    ) -> Dict[str, Any]:
        """Estimate annual transaction costs"""
        total_trades = trades_per_day * n_days
        total_volume = avg_trade_size * total_trades
        total_lots = total_volume / 100000
        
        # Cost per trade
        cost_per_trade = (
            2 * self.config.commission_per_lots * 100000 / avg_trade_size +  # Commissions
            2 * self.config.spread_cost_pct  # Spreads
        )
        
        # Annual estimates
        annual_commission = 2 * self.config.commission_per_lot * total_lots
        annual_spread = total_volume * self.config.spread_cost_pct
        annual_funding = total_volume * self.config.funding_rate * avg_holding_days
        
        total_annual = annual_commission + annual_spread + annual_funding
        
        return {
            "total_trades": total_trades,
            "total_volume": total_volume,
            "annual_commission": annual_commission,
            "annual_spread": annual_spread,
            "annual_funding": annual_funding,
            "total_annual_cost": total_annual,
            "cost_per_trade": cost_per_trade,
            "cost_per_dollar": total_annual / total_volume if total_volume > 0 else 0
        }


class MarketImpactSimulator:
    """
    Simulates market impact of large orders.
    """
    
    def __init__(self):
        self.impact_coefficient = 0.1  # Typical for liquid markets
    
    def calculate_impact(
        self,
        order_size: float,
        avg_daily_volume: float,
        urgency: float = 0.5  # 0 = patient, 1 = urgent
    ) -> Dict[str, Any]:
        """
        Calculate expected market impact.
        
        Uses square-root market impact model.
        """
        # Participation rate
        participation = order_size / avg_daily_volume
        
        # Square-root impact model
        base_impact = self.impact_coefficient * np.sqrt(participation)
        
        # Urgency multiplier
        urgency_multiplier = 1 + urgency * 0.5
        
        # Total impact
        total_impact = base_impact * urgency_multiplier
        
        # Execution time estimate (hours)
        if participation < 0.1:
            exec_time = 1.0  # Can execute same day
        elif participation < 0.25:
            exec_time = 4.0  # Multiple hours
        else:
            exec_time = 8.0  # Full day or more
        
        return {
            "order_size": order_size,
            "avg_daily_volume": avg_daily_volume,
            "participation_rate": participation,
            "base_impact_pct": base_impact,
            "urgency_multiplier": urgency_multiplier,
            "total_impact_pct": total_impact,
            "estimated_exec_time_hours": exec_time,
            "impact_cost": order_size * total_impact
        }
