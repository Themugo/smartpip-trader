"""
Quantitative strategy testing framework.
Implements walk-forward testing, OOS validation, and Monte Carlo simulations.
"""
import numpy as np
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque


class ContractType(Enum):
    """Deriv contract types for digit trading"""
    DIGIT_EVEN = "DIGITEVEN"
    DIGIT_ODD = "DIGITODD"
    DIGIT_OVER = "DIGITOVER"
    DIGIT_UNDER = "DIGITUNDER"
    DIGIT_MATCH = "DIGITMATCH"
    DIGIT_DIFF = "DIGITDIFF"


@dataclass
class Trade:
    """Individual trade record"""
    tick_index: int
    contract_type: ContractType
    symbol: str
    amount: float
    entry_price: float
    entry_digit: int
    exit_price: float
    exit_digit: int
    profit: float
    duration: int  # ticks
    fees: float
    slippage: float
    latency: int
    won: bool
    regime: str
    timestamp: int


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Core counts
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    
    # Ratios
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    recovery_factor: float = 0.0
    
    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    
    # Risk
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Returns
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    
    # Fees
    total_fees: float = 0.0
    fee_impact_pct: float = 0.0
    
    # Regime breakdown
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Walk-forward
    in_sample_metrics: Optional[Dict[str, Any]] = None
    out_of_sample_metrics: Optional[Dict[str, Any]] = None
    
    # Monte Carlo
    mc_confidence_95: Optional[Tuple[float, float]] = None
    mc_prob_profit: Optional[float] = None
    mc_max_dd_95: Optional[float] = None
    
    # Parameter sensitivity
    param_sensitivity: Optional[Dict[str, List[float]]] = None
    
    # Validity
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)


class DigitStrategy:
    """Base class for digit-based trading strategies"""
    
    def __init__(self, name: str, min_confidence: float = 55.0):
        self.name = name
        self.min_confidence = min_confidence
        self.digit_history: deque = deque(maxlen=100)
    
    def analyze(self, ticks: List[Dict[str, Any]], current_index: int) -> Optional[ContractType]:
        """Analyze ticks and return contract type or None"""
        raise NotImplementedError
    
    def get_confidence(self, ticks: List[Dict[str, Any]], current_index: int) -> float:
        """Return confidence score 0-100"""
        raise NotImplementedError


class EvenOddStrategy(DigitStrategy):
    """Even/Odd strategy with mean reversion"""
    
    def __init__(self, min_confidence: float = 55.0):
        super().__init__("even_odd", min_confidence)
    
    def analyze(self, ticks: List[Dict[str, Any]], current_index: int) -> Optional[ContractType]:
        if current_index < 20:
            return None
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        evens = sum(1 for d in last_20 if d % 2 == 0)
        odds = 20 - evens
        
        confidence = self.get_confidence(ticks, current_index)
        if confidence < self.min_confidence:
            return None
        
        # Mean reversion: bet against the majority
        if evens > odds + 4:
            return ContractType.DIGIT_ODD
        elif odds > evens + 4:
            return ContractType.DIGIT_EVEN
        
        # Streak reversal
        streak = 1
        for i in range(len(last_20) - 1, 0, -1):
            if (last_20[i] % 2) == (last_20[i-1] % 2):
                streak += 1
            else:
                break
        
        if streak >= 4:
            return ContractType.DIGIT_ODD if last_20[-1] % 2 == 0 else ContractType.DIGIT_EVEN
        
        return None
    
    def get_confidence(self, ticks: List[Dict[str, Any]], current_index: int) -> float:
        if current_index < 20:
            return 0
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        evens = sum(1 for d in last_20 if d % 2 == 0)
        odds = 20 - evens
        
        if evens > odds + 4:
            return min(60 + (evens - odds) * 2, 95)
        elif odds > evens + 4:
            return min(60 + (odds - evens) * 2, 95)
        
        streak = 1
        for i in range(len(last_20) - 1, 0, -1):
            if (last_20[i] % 2) == (last_20[i-1] % 2):
                streak += 1
            else:
                break
        
        if streak >= 4:
            return min(65 + streak * 2, 95)
        
        return 50


class OverUnderStrategy(DigitStrategy):
    """Over/Under strategy"""
    
    def __init__(self, barrier: int = 5, min_confidence: float = 55.0):
        super().__init__("over_under", min_confidence)
        self.barrier = barrier
    
    def analyze(self, ticks: List[Dict[str, Any]], current_index: int) -> Optional[ContractType]:
        if current_index < 20:
            return None
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        over = sum(1 for d in last_20 if d >= self.barrier)
        under = 20 - over
        
        confidence = self.get_confidence(ticks, current_index)
        if confidence < self.min_confidence:
            return None
        
        if over > under + 4:
            return ContractType.DIGIT_UNDER
        elif under > over + 4:
            return ContractType.DIGIT_OVER
        
        return None
    
    def get_confidence(self, ticks: List[Dict[str, Any]], current_index: int) -> float:
        if current_index < 20:
            return 0
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        over = sum(1 for d in last_20 if d >= self.barrier)
        under = 20 - over
        
        if over > under + 4:
            return min(60 + (over - under) * 2, 95)
        elif under > over + 4:
            return min(60 + (under - over) * 2, 95)
        
        return 50


class MatchDiffStrategy(DigitStrategy):
    """Match/Differ strategy"""
    
    def __init__(self, min_confidence: float = 55.0):
        super().__init__("match_diff", min_confidence)
    
    def analyze(self, ticks: List[Dict[str, Any]], current_index: int) -> Optional[ContractType]:
        if current_index < 20:
            return None
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        matches = sum(1 for i in range(1, len(last_20)) if last_20[i] == last_20[i-1])
        diffs = len(last_20) - 1 - matches
        
        confidence = self.get_confidence(ticks, current_index)
        if confidence < self.min_confidence:
            return None
        
        if matches > diffs + 3:
            return ContractType.DIGIT_DIFF
        elif diffs > matches + 3:
            return ContractType.DIGIT_MATCH
        
        # Streak detection
        streak = 1
        for i in range(len(last_20) - 1, 0, -1):
            if last_20[i] == last_20[i-1]:
                streak += 1
            else:
                break
        
        if streak >= 3:
            return ContractType.DIGIT_DIFF
        
        return None
    
    def get_confidence(self, ticks: List[Dict[str, Any]], current_index: int) -> float:
        if current_index < 20:
            return 0
        
        last_20 = [ticks[i]["digit"] for i in range(current_index - 20, current_index)]
        matches = sum(1 for i in range(1, len(last_20)) if last_20[i] == last_20[i-1])
        diffs = len(last_20) - 1 - matches
        
        if matches > diffs + 3:
            return min(65 + (matches - diffs), 95)
        elif diffs > matches + 3:
            return min(65 + (diffs - matches), 95)
        
        streak = 1
        for i in range(len(last_20) - 1, 0, -1):
            if last_20[i] == last_20[i-1]:
                streak += 1
            else:
                break
        
        if streak >= 3:
            return min(70 + streak * 2, 95)
        
        return 50


class CompositeStrategy(DigitStrategy):
    """Combines multiple strategies with voting"""
    
    def __init__(self, strategies: List[DigitStrategy], min_agreement: int = 2):
        super().__init__("composite", 55.0)
        self.strategies = strategies
        self.min_agreement = min_agreement
    
    def analyze(self, ticks: List[Dict[str, Any]], current_index: int) -> Optional[ContractType]:
        votes: Dict[ContractType, int] = {}
        
        for strategy in self.strategies:
            result = strategy.analyze(ticks, current_index)
            if result:
                votes[result] = votes.get(result, 0) + 1
        
        if not votes:
            return None
        
        best = max(votes.items(), key=lambda x: x[1])
        if best[1] >= self.min_agreement:
            return best[0]
        
        return None
    
    def get_confidence(self, ticks: List[Dict[str, Any]], current_index: int) -> float:
        confidences = []
        for strategy in self.strategies:
            confidences.append(strategy.get_confidence(ticks, current_index))
        
        return np.mean(confidences) if confidences else 0


class StrategyTester:
    """
    Comprehensive strategy testing engine.
    Implements walk-forward testing, OOS validation, and Monte Carlo.
    """
    
    def __init__(
        self,
        strategy: DigitStrategy,
        amount: float = 1.0,
        payout_rate: float = 0.94,  # 94% payout for digit contracts
        fee_per_trade: float = 0.0,
        slippage_std: float = 0.0005,
        latency_ticks: int = 1,
    ):
        self.strategy = strategy
        self.amount = amount
        self.payout_rate = payout_rate
        self.fee_per_trade = fee_per_trade
        self.slippage_std = slippage_std
        self.latency_ticks = latency_ticks
        self.rng = np.random.RandomState(seed=42)
    
    def _resolve_trade(
        self,
        contract_type: ContractType,
        entry_tick: Dict[str, Any],
        exit_tick: Dict[str, Any],
    ) -> Trade:
        """Resolve a single trade outcome"""
        entry_digit = entry_tick["digit"]
        exit_digit = exit_tick["digit"]
        
        # Determine win/loss based on contract type
        won = False
        if contract_type == ContractType.DIGIT_EVEN:
            won = exit_digit % 2 == 0
        elif contract_type == ContractType.DIGIT_ODD:
            won = exit_digit % 2 == 1
        elif contract_type == ContractType.DIGIT_OVER:
            won = exit_digit > int(contract_type.value[-1]) if contract_type.value[-1].isdigit() else exit_digit >= 5
        elif contract_type == ContractType.DIGIT_UNDER:
            won = exit_digit < 5
        elif contract_type == ContractType.DIGIT_MATCH:
            won = exit_digit == entry_digit
        elif contract_type == ContractType.DIGIT_DIFF:
            won = exit_digit != entry_digit
        
        # For over/under with barrier
        if contract_type == ContractType.DIGIT_OVER:
            won = exit_digit >= 5
        elif contract_type == ContractType.DIGIT_UNDER:
            won = exit_digit < 5
        
        # Calculate P&L
        if won:
            gross_profit = self.amount * self.payout_rate
        else:
            gross_profit = -self.amount
        
        fees = self.fee_per_trade
        slippage = self.rng.normal(0, self.slippage_std) * self.amount
        
        net_profit = gross_profit - fees - abs(slippage)
        
        return Trade(
            tick_index=entry_tick["tick"],
            contract_type=contract_type,
            symbol=entry_tick["symbol"],
            amount=self.amount,
            entry_price=entry_tick["price"],
            entry_digit=entry_digit,
            exit_price=exit_tick["price"],
            exit_digit=exit_digit,
            profit=net_profit,
            duration=1 + self.latency_ticks,
            fees=fees,
            slippage=slippage,
            latency=self.latency_ticks,
            won=won,
            regime=entry_tick.get("regime", "unknown"),
            timestamp=entry_tick["timestamp"],
        )
    
    def run_backtest(
        self,
        ticks: List[Dict[str, Any]],
        start_index: int = 0,
        end_index: Optional[int] = None,
    ) -> List[Trade]:
        """Run strategy on tick data"""
        end = end_index or len(ticks)
        trades = []
        
        for i in range(start_index + 20, end - self.latency_ticks - 1):
            contract_type = self.strategy.analyze(ticks, i)
            
            if contract_type:
                # Execute at next tick (with latency)
                entry_tick = ticks[i]
                exit_tick = ticks[i + 1 + self.latency_ticks]
                
                trade = self._resolve_trade(contract_type, entry_tick, exit_tick)
                trades.append(trade)
        
        return trades
    
    def walk_forward_test(
        self,
        ticks: List[Dict[str, Any]],
        train_window: int = 2000,
        test_window: int = 500,
        step_size: int = 500,
    ) -> Tuple[List[Trade], List[Trade]]:
        """
        Walk-forward analysis: train on window, test on next window, step forward.
        Returns (in_sample_trades, out_of_sample_trades).
        """
        in_sample_trades = []
        out_of_sample_trades = []
        
        current = train_window
        
        while current + test_window < len(ticks):
            # In-sample: train window
            train_end = current
            train_trades = self.run_backtest(ticks, start_index=current - train_window, end_index=train_end)
            in_sample_trades.extend(train_trades)
            
            # Out-of-sample: test window
            test_end = current + test_window
            test_trades = self.run_backtest(ticks, start_index=train_end, end_index=test_end)
            out_of_sample_trades.extend(test_trades)
            
            # Step forward
            current += step_size
        
        return in_sample_trades, out_of_sample_trades
    
    def monte_carlo_simulation(
        self,
        ticks: List[Dict[str, Any]],
        num_simulations: int = 1000,
        shuffle_trades: bool = True,
    ) -> Dict[str, Any]:
        """
        Monte Carlo simulation: reshuffle trade sequences to estimate robustness.
        """
        base_trades = self.run_backtest(ticks)
        if not base_trades:
            return {"error": "No trades generated"}
        
        profits = [t.profit for t in base_trades]
        
        simulation_results = []
        max_drawdowns = []
        final_balances = []
        
        for sim in range(num_simulations):
            if shuffle_trades:
                shuffled = self.rng.permutation(profits).tolist()
            else:
                # Random sampling with replacement
                shuffled = self.rng.choice(profits, size=len(profits), replace=True).tolist()
            
            balance = 0
            peak = 0
            max_dd = 0
            
            for profit in shuffled:
                balance += profit
                if balance > peak:
                    peak = balance
                dd = peak - balance
                if dd > max_dd:
                    max_dd = dd
            
            simulation_results.append(balance)
            max_drawdowns.append(max_dd)
            final_balances.append(balance)
        
        # Calculate statistics
        sim_array = np.array(simulation_results)
        dd_array = np.array(max_drawdowns)
        
        return {
            "num_simulations": num_simulations,
            "mean_final_pnl": float(np.mean(final_balances)),
            "std_final_pnl": float(np.std(final_balances)),
            "median_final_pnl": float(np.median(final_balances)),
            "prob_profit": float(np.mean(np.array(final_balances) > 0)),
            "confidence_95": (
                float(np.percentile(final_balances, 2.5)),
                float(np.percentile(final_balances, 97.5)),
            ),
            "confidence_99": (
                float(np.percentile(final_balances, 0.5)),
                float(np.percentile(final_balances, 99.5)),
            ),
            "max_dd_95": float(np.percentile(dd_array, 95)),
            "max_dd_mean": float(np.mean(dd_array)),
            "worst_case_pnl": float(np.min(final_balances)),
            "best_case_pnl": float(np.max(final_balances)),
        }
    
    def parameter_sensitivity(
        self,
        ticks: List[Dict[str, Any]],
        param_name: str,
        param_values: List[float],
    ) -> Dict[str, List[float]]:
        """Test strategy sensitivity to parameter changes"""
        results = {
            "values": param_values,
            "expectancy": [],
            "win_rate": [],
            "profit_factor": [],
            "sharpe": [],
            "max_drawdown": [],
        }
        
        original_value = getattr(self.strategy, param_name, None)
        
        for value in param_values:
            try:
                setattr(self.strategy, param_name, value)
                trades = self.run_backtest(ticks)
                metrics = self.calculate_metrics(trades)
                
                results["expectancy"].append(metrics.expectancy)
                results["win_rate"].append(metrics.win_rate)
                results["profit_factor"].append(metrics.profit_factor)
                results["sharpe"].append(metrics.sharpe_ratio)
                results["max_drawdown"].append(metrics.max_drawdown)
            except Exception:
                for key in results:
                    if key != "values":
                        results[key].append(0.0)
        
        # Restore original
        if original_value is not None:
            setattr(self.strategy, param_name, original_value)
        
        return results
    
    def calculate_metrics(self, trades: List[Trade]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return PerformanceMetrics(validation_errors=["No trades to analyze"])
        
        metrics = PerformanceMetrics()
        metrics.total_trades = len(trades)
        
        wins = [t for t in trades if t.won]
        losses = [t for t in trades if not t.won]
        
        metrics.wins = len(wins)
        metrics.losses = len(losses)
        metrics.win_rate = (metrics.wins / metrics.total_trades * 100) if metrics.total_trades > 0 else 0
        
        # P&L
        profits = [t.profit for t in trades]
        metrics.gross_profit = sum(t.profit for t in wins) if wins else 0
        metrics.gross_loss = sum(t.profit for t in losses) if losses else 0
        metrics.net_profit = sum(profits)
        
        metrics.avg_win = np.mean([t.profit for t in wins]) if wins else 0
        metrics.avg_loss = np.mean([t.profit for t in losses]) if losses else 0
        metrics.avg_trade = np.mean(profits)
        
        # Profit factor
        gross_loss_abs = abs(metrics.gross_loss) if metrics.gross_loss != 0 else 1e-10
        metrics.profit_factor = metrics.gross_profit / gross_loss_abs if gross_loss_abs > 0 else float('inf')
        
        # Expectancy
        metrics.expectancy = metrics.avg_trade
        
        # Sharpe ratio (assuming risk-free rate = 0)
        returns = np.array(profits)
        if len(returns) > 1 and np.std(returns) > 0:
            metrics.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(len(returns))
        else:
            metrics.sharpe_ratio = 0
        
        # Sortino ratio (downside deviation)
        downside = returns[returns < 0]
        if len(downside) > 0 and np.std(downside) > 0:
            metrics.sortino_ratio = np.mean(returns) / np.std(downside) * np.sqrt(len(returns))
        else:
            metrics.sortino_ratio = metrics.sharpe_ratio
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        metrics.max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0
        
        # Drawdown duration
        dd_duration = 0
        max_dd_duration = 0
        for i in range(len(cumulative)):
            if cumulative[i] < peak[i]:
                dd_duration += 1
            else:
                max_dd_duration = max(max_dd_duration, dd_duration)
                dd_duration = 0
        metrics.max_drawdown_duration = max_dd_duration
        
        # Consecutive wins/losses
        streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        for t in trades:
            if t.won:
                streak = streak + 1 if streak > 0 else 1
                max_win_streak = max(max_win_streak, streak)
            else:
                streak = streak - 1 if streak < 0 else -1
                max_loss_streak = max(max_loss_streak, abs(streak))
        metrics.max_consecutive_wins = max_win_streak
        metrics.max_consecutive_losses = max_loss_streak
        
        # Recovery factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.net_profit / metrics.max_drawdown
        else:
            metrics.recovery_factor = float('inf') if metrics.net_profit > 0 else 0
        
        # Total return
        initial_capital = self.amount * 100  # Assume 100 trade bankroll
        metrics.total_return_pct = (metrics.net_profit / initial_capital) * 100
        
        # Volatility
        metrics.volatility = float(np.std(returns)) if len(returns) > 1 else 0
        
        # Fees
        metrics.total_fees = sum(t.fees for t in trades)
        metrics.fee_impact_pct = (metrics.total_fees / abs(metrics.net_profit) * 100) if metrics.net_profit != 0 else 0
        
        # Regime breakdown
        regime_trades: Dict[str, List[Trade]] = {}
        for t in trades:
            regime = t.regime
            if regime not in regime_trades:
                regime_trades[regime] = []
            regime_trades[regime].append(t)
        
        for regime, rt in regime_trades.items():
            r_wins = sum(1 for t in rt if t.won)
            r_profits = [t.profit for t in rt]
            metrics.regime_performance[regime] = {
                "trades": len(rt),
                "win_rate": (r_wins / len(rt) * 100) if rt else 0,
                "avg_profit": np.mean(r_profits) if r_profits else 0,
                "total_pnl": sum(r_profits),
            }
        
        # Validation
        metrics.is_valid = metrics.expectancy > 0 and metrics.total_trades >= 100
        if metrics.expectancy <= 0:
            metrics.validation_errors.append(f"Expectancy {metrics.expectancy:.4f} <= 0. Strategy not deployable.")
        if metrics.total_trades < 100:
            metrics.validation_errors.append(f"Only {metrics.total_trades} trades. Minimum 100 required.")
        
        return metrics
    
    def full_validation(
        self,
        ticks: List[Dict[str, Any]],
        num_mc_sims: int = 1000,
    ) -> Dict[str, Any]:
        """
        Run complete validation suite:
        1. Walk-forward test
        2. Out-of-sample metrics
        3. Monte Carlo simulation
        4. Parameter sensitivity
        5. Regime analysis
        """
        results = {
            "strategy_name": self.strategy.name,
            "symbol": ticks[0].get("symbol", "unknown") if ticks else "unknown",
            "total_ticks": len(ticks),
            "timestamp": datetime.now().isoformat(),
        }
        
        # 1. Walk-forward test
        is_trades, oos_trades = self.walk_forward_test(ticks)
        results["in_sample_trades"] = len(is_trades)
        results["out_of_sample_trades"] = len(oos_trades)
        
        is_metrics = self.calculate_metrics(is_trades)
        oos_metrics = self.calculate_metrics(oos_trades)
        
        results["in_sample"] = self._metrics_to_dict(is_metrics)
        results["out_of_sample"] = self._metrics_to_dict(oos_metrics)
        
        # 2. Monte Carlo
        mc_results = self.monte_carlo_simulation(ticks, num_simulations=num_mc_sims)
        results["monte_carlo"] = mc_results
        
        # 3. Parameter sensitivity (min_confidence)
        if hasattr(self.strategy, 'min_confidence'):
            sensitivity = self.parameter_sensitivity(
                ticks, "min_confidence", [50, 55, 60, 65, 70, 75, 80]
            )
            results["param_sensitivity"] = sensitivity
        
        # 4. Full backtest for reference
        all_trades = self.run_backtest(ticks)
        all_metrics = self.calculate_metrics(all_trades)
        results["full_backtest"] = self._metrics_to_dict(all_metrics)
        
        # 5. Deployment gate
        results["deployable"] = (
            oos_metrics.is_valid and
            oos_metrics.expectancy > 0 and
            mc_results.get("prob_profit", 0) > 0.5
        )
        
        return results
    
    def _metrics_to_dict(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_trades": metrics.total_trades,
            "wins": metrics.wins,
            "losses": metrics.losses,
            "win_rate": round(metrics.win_rate, 2),
            "profit_factor": round(metrics.profit_factor, 3),
            "expectancy": round(metrics.expectancy, 4),
            "sharpe_ratio": round(metrics.sharpe_ratio, 3),
            "sortino_ratio": round(metrics.sortino_ratio, 3),
            "recovery_factor": round(metrics.recovery_factor, 3),
            "max_drawdown": round(metrics.max_drawdown, 2),
            "max_drawdown_duration": metrics.max_drawdown_duration,
            "net_profit": round(metrics.net_profit, 2),
            "avg_trade": round(metrics.avg_trade, 4),
            "avg_win": round(metrics.avg_win, 2),
            "avg_loss": round(metrics.avg_loss, 2),
            "max_consecutive_wins": metrics.max_consecutive_wins,
            "max_consecutive_losses": metrics.max_consecutive_losses,
            "total_fees": round(metrics.total_fees, 2),
            "fee_impact_pct": round(metrics.fee_impact_pct, 2),
            "total_return_pct": round(metrics.total_return_pct, 2),
            "volatility": round(metrics.volatility, 4),
            "regime_performance": metrics.regime_performance,
            "is_valid": metrics.is_valid,
            "validation_errors": metrics.validation_errors,
        }
