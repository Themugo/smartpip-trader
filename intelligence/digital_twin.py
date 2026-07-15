"""
Digital Twin — Pre-Execution Scenario Simulator.

Before any live signal is executed, the Digital Twin replays the signal
against thousands of synthetic scenarios derived from historical market
data.  Only signals that survive statistical scrutiny are forwarded to
the executor.
"""

import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_SIMULATIONS = 1000
_DEFAULT_MIN_THRESHOLD = 0.55
_SPREAD_COST = 0.005        # ~0.5 % spread
_SLIPPAGE_RANGE = (0.0, 0.002)  # uniform slippage 0–0.2 %
_BOOTSTRAP_RESAMPLES = 2000
_MIN_HISTORICAL_SAMPLES = 10


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class TwinResult:
    """Outcome of a Digital-Twin simulation run."""

    approved: bool = False
    simulated_win_rate: float = 0.0
    simulated_avg_profit: float = 0.0
    simulated_max_drawdown: float = 0.0
    simulated_sharpe: float = 0.0
    scenarios_tested: int = 0
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    rejection_reason: str = ""
    scenario_breakdown: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# DigitalTwin
# ---------------------------------------------------------------------------
class DigitalTwin:
    """Simulates live signals against historical scenarios before execution.

    Parameters
    ----------
    trade_memory : TradeMemory
        Persistent trade memory that stores historical trade records and
        market data segments.
    min_twin_threshold : float
        Minimum simulated win rate required for a signal to be approved.
        Default is ``0.55`` (55 %).
    """

    def __init__(self, trade_memory: Any, min_twin_threshold: float = _DEFAULT_MIN_THRESHOLD):
        self.trade_memory = trade_memory
        self.min_twin_threshold = min_twin_threshold

        # Running stats
        self._total_simulations: int = 0
        self._total_approved: int = 0
        self._total_rejected: int = 0
        self._simulated_win_rates: List[float] = []
        self._actual_vs_predicted: List[Dict[str, float]] = []

        logger.info(
            "DigitalTwin initialized (min_threshold=%.2f)", min_twin_threshold
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _retrieve_segments(
        self, market: str, regime: str, min_count: int = _MIN_HISTORICAL_SAMPLES
    ) -> List[List[float]]:
        """Fetch historical price-segments from trade memory.

        Each segment is a list of float price movements suitable for
        replay.  Falls back to constructing synthetic segments from
        entry/exit prices when full price_history is unavailable.
        """
        segments: List[List[float]] = []
        try:
            records = self.trade_memory.get_by_market(market)
        except Exception:
            records = []

        for rec in records:
            rec_regime = getattr(rec, "regime", None)
            if rec_regime and str(rec_regime).lower() != regime.lower():
                continue

            # Try full price_history first
            prices = getattr(rec, "price_history", None)
            if prices and len(prices) >= min_count:
                segments.append([float(p) for p in prices])
                continue

            # Build a synthetic segment from entry/exit
            entry = getattr(rec, "entry_price", None)
            exit_ = getattr(rec, "exit_price", None)
            if entry is not None and exit_ is not None:
                segment = [float(entry), float(exit_)]
                if len(segment) >= 2:
                    segments.append(segment)

        return segments

    @staticmethod
    def _compute_returns(prices: List[float]) -> np.ndarray:
        """Convert raw prices to percentage returns."""
        arr = np.array(prices, dtype=np.float64)
        if len(arr) < 2:
            return np.array([], dtype=np.float64)
        return np.diff(arr) / arr[:-1]

    @staticmethod
    def _simulate_trade(
        returns: np.ndarray,
        direction_bull: bool,
        amount: float,
    ) -> Dict[str, float]:
        """Simulate a single trade over a return series.

        Parameters
        ----------
        returns : np.ndarray
            Historical percentage returns.
        direction_bull : bool
            True for CALL/RISE, False for PUT/FALL.
        amount : float
            Notional trade amount.

        Returns
        -------
        dict
            ``{pnl, win, drawdown}``
        """
        if len(returns) == 0:
            return {"pnl": 0.0, "win": 0.0, "drawdown": 0.0}

        # Apply direction
        effective = returns if direction_bull else -returns

        # Random entry offset to simulate realistic entry timing
        n = len(effective)
        offset = np.random.randint(0, max(1, n // 3))
        segment = effective[offset:]

        # Costs
        spread = _SPREAD_COST
        slippage = np.random.uniform(*_SLIPPAGE_RANGE)

        # P&L per step
        step_pnl = segment - spread - slippage
        cum_pnl = np.cumsum(step_pnl)

        # Max drawdown on cumulative P&L
        running_max = np.maximum.accumulate(cum_pnl)
        drawdowns = running_max - cum_pnl
        max_dd = float(drawdowns.max()) if len(drawdowns) > 0 else 0.0

        total_pnl = float(cum_pnl[-1]) if len(cum_pnl) > 0 else 0.0
        pnl_dollars = total_pnl * amount
        win = 1.0 if pnl_dollars > 0 else 0.0

        return {"pnl": pnl_dollars, "win": win, "drawdown": max_dd * amount}

    @staticmethod
    def _bootstrap_ci(
        win_rates: np.ndarray, confidence: float = 0.95, resamples: int = _BOOTSTRAP_RESAMPLES
    ) -> Tuple[float, float]:
        """Compute a bootstrap confidence interval for mean win rate."""
        n = len(win_rates)
        if n < 2:
            return (0.0, 1.0)

        rng = np.random.default_rng()
        boot_means = np.empty(resamples)
        for i in range(resamples):
            sample = rng.choice(win_rates, size=n, replace=True)
            boot_means[i] = sample.mean()

        alpha = (1.0 - confidence) / 2.0
        lo = float(np.percentile(boot_means, alpha * 100))
        hi = float(np.percentile(boot_means, (1.0 - alpha) * 100))
        return (round(lo, 4), round(hi, 4))

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def simulate(
        self,
        signal: dict,
        market: str,
        regime: str,
        amount: float,
        n_simulations: int = _DEFAULT_SIMULATIONS,
    ) -> TwinResult:
        """Run Monte-Carlo simulation of a signal against historical data.

        Parameters
        ----------
        signal : dict
            Must contain ``"direction"`` (e.g. ``"CALL"`` / ``"PUT"``).
        market : str
            Market identifier (e.g. ``"volatility_10"``).
        regime : str
            Current market regime label.
        amount : float
            Trade notional.
        n_simulations : int
            Number of simulated scenarios.

        Returns
        -------
        TwinResult
        """
        segments = self._retrieve_segments(market, regime)

        if not segments:
            logger.warning(
                "No historical data for market=%s regime=%s — auto-rejecting", market, regime
            )
            self._total_rejected += 1
            return TwinResult(
                approved=False,
                rejection_reason=f"No historical data for {market}/{regime}",
                timestamp=time.time(),
            )

        direction_str = str(signal.get("direction", "CALL")).upper()
        direction_bull = any(k in direction_str for k in ("CALL", "RISE", "EVEN", "OVER"))

        wins = 0
        pnls = []
        drawdowns = []

        for _ in range(n_simulations):
            # Sample a random historical segment
            seg = segments[np.random.randint(0, len(segments))]
            returns = self._compute_returns(seg)
            if len(returns) < 5:
                continue

            result = self._simulate_trade(returns, direction_bull, amount)
            wins += result["win"]
            pnls.append(result["pnl"])
            drawdowns.append(result["drawdown"])

        tested = len(pnls)
        if tested == 0:
            self._total_rejected += 1
            return TwinResult(
                approved=False,
                rejection_reason="All sampled segments were too short",
                timestamp=time.time(),
            )

        win_rate = wins / tested
        avg_profit = float(np.mean(pnls))
        max_dd = float(np.max(drawdowns)) if drawdowns else 0.0

        # Sharpe ratio (annualised-ish)
        pnl_arr = np.array(pnls)
        std = float(pnl_arr.std())
        sharpe = (avg_profit / std) if std > 1e-12 else 0.0

        # Bootstrap confidence interval
        wr_arr = np.array([1.0 if p > 0 else 0.0 for p in pnls])
        ci = self._bootstrap_ci(wr_arr)

        # Decision
        approved = win_rate >= self.min_twin_threshold
        rejection_reason = "" if approved else (
            f"Simulated win rate {win_rate:.1%} < threshold {self.min_twin_threshold:.1%}"
        )

        # Breakdown
        regime_counts = {"wins": int(wins), "losses": tested - int(wins)}
        profit_brackets = {
            "profitable": int((pnl_arr > 0).sum()),
            "breakeven": int((np.abs(pnl_arr) < 1e-9).sum()),
            "losing": int((pnl_arr < 0).sum()),
        }

        tw = TwinResult(
            approved=approved,
            simulated_win_rate=round(win_rate, 4),
            simulated_avg_profit=round(avg_profit, 6),
            simulated_max_drawdown=round(max_dd, 6),
            simulated_sharpe=round(sharpe, 4),
            scenarios_tested=tested,
            confidence_interval=ci,
            rejection_reason=rejection_reason,
            scenario_breakdown={"outcome_counts": regime_counts, "profit_brackets": profit_brackets},
            timestamp=time.time(),
        )

        # Update running stats
        self._total_simulations += tested
        self._simulated_win_rates.append(win_rate)
        if approved:
            self._total_approved += 1
        else:
            self._total_rejected += 1

        logger.info(
            "Simulation complete: approved=%s WR=%.2f%% avg_profit=%.6f sharpe=%.2f (%d scenarios)",
            approved, win_rate * 100, avg_profit, sharpe, tested,
        )
        return tw

    def simulate_batch(self, signals: List[dict]) -> List[TwinResult]:
        """Run simulation for a batch of signals.

        Each element in *signals* should be a dict with keys ``signal``,
        ``market``, ``regime``, ``amount``, and optionally ``n_simulations``.

        Parameters
        ----------
        signals : list[dict]

        Returns
        -------
        list[TwinResult]
        """
        results: List[TwinResult] = []
        for entry in signals:
            sig = entry.get("signal", {})
            market = entry.get("market", "unknown")
            regime = entry.get("regime", "unknown")
            amount = entry.get("amount", 1.0)
            n_sims = entry.get("n_simulations", _DEFAULT_SIMULATIONS)
            try:
                r = self.simulate(sig, market, regime, amount, n_sims)
            except Exception as exc:
                logger.error("Batch simulation failed for %s: %s", market, exc)
                r = TwinResult(
                    approved=False,
                    rejection_reason=f"Simulation error: {exc}",
                    timestamp=time.time(),
                )
            results.append(r)
        return results

    def backtest_simulation(
        self, signal: dict, historical_data: List[float]
    ) -> TwinResult:
        """Run a single-segment backtest against provided price data.

        Parameters
        ----------
        signal : dict
            Must contain ``"direction"``.
        historical_data : list[float]
            Raw price series.

        Returns
        -------
        TwinResult
        """
        if len(historical_data) < 5:
            return TwinResult(
                approved=False,
                rejection_reason="Historical data too short (< 5 points)",
                timestamp=time.time(),
            )

        direction_str = str(signal.get("direction", "CALL")).upper()
        direction_bull = any(k in direction_str for k in ("CALL", "RISE", "EVEN", "OVER"))

        # Use the entire segment but sample multiple starting points
        returns = self._compute_returns(historical_data)
        if len(returns) < 5:
            return TwinResult(
                approved=False,
                rejection_reason="Insufficient return data after conversion",
                timestamp=time.time(),
            )

        amount = signal.get("amount", 1.0)
        wins = 0
        pnls: List[float] = []
        drawdowns: List[float] = []
        n_tries = min(len(returns), 500)

        for _ in range(n_tries):
            result = self._simulate_trade(returns, direction_bull, amount)
            wins += result["win"]
            pnls.append(result["pnl"])
            drawdowns.append(result["drawdown"])

        tested = len(pnls)
        win_rate = wins / tested
        pnl_arr = np.array(pnls)
        avg_profit = float(pnl_arr.mean())
        max_dd = float(np.max(drawdowns)) if drawdowns else 0.0
        std = float(pnl_arr.std())
        sharpe = (avg_profit / std) if std > 1e-12 else 0.0

        wr_arr = np.array([1.0 if p > 0 else 0.0 for p in pnls])
        ci = self._bootstrap_ci(wr_arr)

        approved = win_rate >= self.min_twin_threshold
        rejection_reason = "" if approved else (
            f"Backtest win rate {win_rate:.1%} < {self.min_twin_threshold:.1%}"
        )

        self._total_simulations += tested
        self._simulated_win_rates.append(win_rate)
        if approved:
            self._total_approved += 1
        else:
            self._total_rejected += 1

        return TwinResult(
            approved=approved,
            simulated_win_rate=round(win_rate, 4),
            simulated_avg_profit=round(avg_profit, 6),
            simulated_max_drawdown=round(max_dd, 6),
            simulated_sharpe=round(sharpe, 4),
            scenarios_tested=tested,
            confidence_interval=ci,
            rejection_reason=rejection_reason,
            scenario_breakdown={
                "outcome_counts": {"wins": int(wins), "losses": tested - int(wins)},
            },
            timestamp=time.time(),
        )

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, actual_outcomes: List[dict]) -> None:
        """Calibrate simulation accuracy against real trade outcomes.

        Parameters
        ----------
        actual_outcomes : list[dict]
            Each dict should have at least ``"predicted_win_rate"`` and
            ``"actual_win"`` (bool or 0/1) keys.
        """
        for record in actual_outcomes:
            predicted = float(record.get("predicted_win_rate", 0.5))
            actual = 1.0 if record.get("actual_win", False) else 0.0
            self._actual_vs_predicted.append({
                "predicted": predicted,
                "actual": actual,
            })

        logger.info(
            "Calibration updated with %d outcomes (total=%d)",
            len(actual_outcomes), len(self._actual_vs_predicted),
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Aggregate statistics over all simulations run.

        Returns
        -------
        dict
        """
        total = self._total_simulations
        approval_rate = (
            self._total_approved / max(self._total_approved + self._total_rejected, 1)
        )

        avg_accuracy = 0.0
        if self._actual_vs_predicted:
            errors = [
                abs(e["predicted"] - e["actual"]) for e in self._actual_vs_predicted
            ]
            avg_accuracy = 1.0 - float(np.mean(errors))

        return {
            "total_scenarios_simulated": total,
            "total_signals_approved": self._total_approved,
            "total_signals_rejected": self._total_rejected,
            "approval_rate": round(approval_rate, 4),
            "avg_calibration_error": round(1.0 - avg_accuracy, 4) if self._actual_vs_predicted else None,
            "simulation_accuracy_vs_actual": round(avg_accuracy, 4) if self._actual_vs_predicted else None,
            "calibration_samples": len(self._actual_vs_predicted),
        }

    def get_twin_stats(self) -> Dict[str, Any]:
        """High-level Digital Twin stats.

        Returns
        -------
        dict
            ``calibration_accuracy``, ``simulation_count``,
            ``approval_rate``, ``avg_simulated_win_rate``.
        """
        stats = self.get_simulation_stats()
        avg_wr = (
            float(np.mean(self._simulated_win_rates))
            if self._simulated_win_rates
            else 0.0
        )
        return {
            "calibration_accuracy": stats.get("simulation_accuracy_vs_actual"),
            "simulation_count": stats["total_scenarios_simulated"],
            "approval_rate": stats["approval_rate"],
            "avg_simulated_win_rate": round(avg_wr, 4),
            "total_approved": stats["total_signals_approved"],
            "total_rejected": stats["total_signals_rejected"],
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist DigitalTwin state to disk.

        Parameters
        ----------
        path : str
            Destination file path.
        """
        state = {
            "min_twin_threshold": self.min_twin_threshold,
            "_total_simulations": self._total_simulations,
            "_total_approved": self._total_approved,
            "_total_rejected": self._total_rejected,
            "_simulated_win_rates": self._simulated_win_rates,
            "_actual_vs_predicted": self._actual_vs_predicted,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(state, path)
        logger.info("DigitalTwin state saved to %s", path)

    def load(self, path: str) -> None:
        """Restore DigitalTwin state from disk.

        Parameters
        ----------
        path : str
            Source file path.
        """
        state = joblib.load(path)
        self.min_twin_threshold = state["min_twin_threshold"]
        self._total_simulations = state["_total_simulations"]
        self._total_approved = state["_total_approved"]
        self._total_rejected = state["_total_rejected"]
        self._simulated_win_rates = state["_simulated_win_rates"]
        self._actual_vs_predicted = state["_actual_vs_predicted"]
        logger.info("DigitalTwin state loaded from %s", path)
