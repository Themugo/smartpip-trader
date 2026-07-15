"""
Experiment Runner
================

Executes experiments and collects results.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """A single trade record"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str  # LONG or SHORT
    pnl: float
    return_pct: float
    holding_period: int  # seconds
    confidence: float


@dataclass
class ExperimentResult:
    """Result of an experiment"""
    id: str
    plan_id: str
    trades: List[TradeRecord]
    returns: List[float]
    equity_curve: List[float]
    metrics: Dict[str, float]
    start_date: datetime
    end_date: datetime
    status: str  # success, failed, incomplete
    error_message: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "trade_count": len(self.trades),
            "total_return": self.metrics.get("total_return", 0),
            "sharpe_ratio": self.metrics.get("sharpe_ratio", 0),
            "max_drawdown": self.metrics.get("max_drawdown", 0),
            "win_rate": self.metrics.get("win_rate", 0),
            "status": self.status,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }


class ExperimentRunner:
    """
    Runs experiments based on experiment plans.
    """
    
    def __init__(
        self,
        use_market_data: bool = True,
        seed: Optional[int] = None
    ):
        self.use_market_data = use_market_data
        self.seed = seed
        self.results: Dict[str, ExperimentResult] = {}
        
        if seed:
            np.random.seed(seed)
            random.seed(seed)
    
    def run(self, plan: Any) -> ExperimentResult:
        """
        Run an experiment based on plan.
        
        Args:
            plan: ExperimentPlan
            
        Returns:
            ExperimentResult
        """
        logger.info(f"Running experiment: {plan.name}")
        
        try:
            # Generate synthetic market data
            price_data = self._generate_price_data(plan)
            
            # Run strategy simulation
            trades, returns, equity = self._simulate_strategy(plan, price_data)
            
            # Calculate metrics
            metrics = self._calculate_metrics(trades, returns, equity)
            
            # Create result
            result = ExperimentResult(
                id=str(uuid4()),
                plan_id=plan.id,
                trades=trades,
                returns=returns,
                equity_curve=equity,
                metrics=metrics,
                start_date=datetime.now(),
                end_date=datetime.now(),
                status="success"
            )
            
            self.results[result.id] = result
            logger.info(f"Experiment completed: {plan.name}, Sharpe={metrics.get('sharpe_ratio', 0):.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Experiment failed: {plan.name}, error={e}")
            return ExperimentResult(
                id=str(uuid4()),
                plan_id=plan.id,
                trades=[],
                returns=[],
                equity_curve=[100000],
                metrics={},
                start_date=datetime.now(),
                end_date=datetime.now(),
                status="failed",
                error_message=str(e)
            )
    
    def _generate_price_data(self, plan: Any) -> Dict[str, Any]:
        """Generate synthetic price data for backtesting"""
        lookback = plan.parameters.get("lookback_days", 90)
        periods_per_day = 24 * 4  # 15-minute periods
        
        n_periods = lookback * periods_per_day
        
        # Generate price series with trends and mean reversion
        initial_price = 150.0
        prices = [initial_price]
        
        # Parameters
        drift = 0.0001  # Slight upward drift
        volatility = 0.005  # 0.5% per period
        mean_reversion_strength = 0.02
        
        # Mean level
        mean_price = initial_price
        
        for i in range(n_periods - 1):
            # Random return
            random_return = np.random.normal(drift, volatility)
            
            # Mean reversion component
            reversion = mean_reversion_strength * (mean_price - prices[-1])
            
            # New price
            new_price = prices[-1] * (1 + random_return + reversion)
            prices.append(max(new_price, 0.01))
        
        return {
            "prices": np.array(prices),
            "volumes": np.random.uniform(1000, 10000, n_periods),
            "timestamps": [datetime.now() for _ in range(n_periods)]
        }
    
    def _simulate_strategy(
        self,
        plan: Any,
        price_data: Dict[str, Any]
    ) -> tuple[List[TradeRecord], List[float], List[float]]:
        """Simulate trading strategy"""
        prices = price_data["prices"]
        n = len(prices)
        
        htype = plan.hypothesis.type.value if hasattr(plan.hypothesis.type, 'value') else "generic"
        
        trades = []
        returns = []
        equity = [100000]
        position = None
        
        # Entry threshold
        entry_threshold = plan.parameters.get("entry_threshold", 2.0)
        stop_loss = plan.parameters.get("stop_loss_pct", 0.02)
        holding_period = plan.parameters.get("holding_period", 5) * 4  # Convert to periods
        
        for i in range(10, n - holding_period):
            current_price = prices[i]
            
            if position is None:
                # Check entry condition based on type
                should_enter = self._check_entry(htype, prices[i-10:i], entry_threshold)
                
                if should_enter:
                    # Determine direction
                    direction = "LONG" if random.random() > 0.5 else "SHORT"
                    entry_price = current_price
                    position = {
                        "entry_time": i,
                        "entry_price": entry_price,
                        "direction": direction,
                        "entry_index": i
                    }
            else:
                # Check exit conditions
                pnl = self._calculate_pnl(
                    position["entry_price"],
                    current_price,
                    position["direction"]
                )
                
                # Exit on profit target, stop loss, or time
                should_exit = False
                if pnl >= 0.01:  # 1% profit target
                    should_exit = True
                elif pnl <= -stop_loss:
                    should_exit = True
                elif i - position["entry_index"] >= holding_period:
                    should_exit = True
                
                if should_exit:
                    # Record trade
                    trade = TradeRecord(
                        entry_time=position["entry_time"],
                        exit_time=i,
                        entry_price=position["entry_price"],
                        exit_price=current_price,
                        direction=position["direction"],
                        pnl=pnl * 100000 / position["entry_price"],  # Convert to $
                        return_pct=pnl * 100,
                        holding_period=i - position["entry_index"],
                        confidence=0.7
                    )
                    trades.append(trade)
                    
                    # Update returns and equity
                    returns.append(pnl)
                    equity.append(equity[-1] * (1 + pnl))
                    position = None
        
        # Close any open position
        if position is not None:
            pnl = self._calculate_pnl(
                position["entry_price"],
                prices[-1],
                position["direction"]
            )
            returns.append(pnl)
            equity.append(equity[-1] * (1 + pnl))
        
        return trades, returns, equity
    
    def _check_entry(
        self,
        htype: str,
        recent_prices: np.ndarray,
        threshold: float
    ) -> bool:
        """Check if entry conditions are met"""
        if len(recent_prices) < 10:
            return False
        
        # Simplified entry logic based on type
        if "momentum" in htype:
            # Entry on upward momentum
            recent_return = (recent_prices[-1] - recent_prices[-10]) / recent_prices[-10]
            return recent_return > threshold * 0.01
        elif "mean_reversion" in htype:
            # Entry on deviation from mean
            mean = np.mean(recent_prices)
            current = recent_prices[-1]
            deviation = abs(current - mean) / mean
            return deviation > threshold * 0.01
        elif "volatility" in htype:
            # Entry on volatility spike
            vol = np.std(np.diff(recent_prices) / recent_prices[:-1])
            return vol > threshold * 0.005
        else:
            # Random entry with low probability
            return random.random() < 0.1
    
    def _calculate_pnl(
        self,
        entry_price: float,
        exit_price: float,
        direction: str
    ) -> float:
        """Calculate PnL percentage"""
        if direction == "LONG":
            return (exit_price - entry_price) / entry_price
        else:
            return (entry_price - exit_price) / entry_price
    
    def _calculate_metrics(
        self,
        trades: List[TradeRecord],
        returns: List[float],
        equity: List[float]
    ) -> Dict[str, float]:
        """Calculate strategy metrics"""
        if not returns:
            return {
                "total_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_trade_pnl": 0,
                "trade_count": 0,
                "calmar_ratio": 0
            }
        
        # Total return
        total_return = (equity[-1] - equity[0]) / equity[0] if len(equity) > 1 else 0
        
        # Sharpe ratio
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown
        peak = equity[0]
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        
        # Win rate
        wins = sum(1 for t in returns if t > 0)
        win_rate = wins / len(returns) if returns else 0
        
        # Profit factor
        gross_profit = sum(t for t in returns if t > 0)
        gross_loss = abs(sum(t for t in returns if t < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Average trade PnL
        avg_trade = np.mean(returns) if returns else 0
        
        # Calmar ratio
        calmar = total_return / max_dd if max_dd > 0 else 0
        
        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_trade_pnl": avg_trade,
            "trade_count": len(trades),
            "calmar_ratio": calmar
        }
    
    def get_result(self, result_id: str) -> Optional[ExperimentResult]:
        """Get experiment result by ID"""
        return self.results.get(result_id)
    
    def get_all_results(self) -> List[ExperimentResult]:
        """Get all experiment results"""
        return list(self.results.values())
