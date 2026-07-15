"""
Backtesting & Walk-Forward Validation Engine — strategy simulation and robustness analysis.

Provides comprehensive backtesting of trading strategies against historical trade records,
rolling walk-forward validation to detect overfitting, Monte Carlo permutation testing for
statistical significance, and parameter stability analysis.

Key features:
  - Full equity-curve simulation with drawdown and risk-adjusted metrics.
  - Rolling walk-forward windows with in-sample / out-of-sample performance tracking.
  - Monte Carlo return-shuffling for robustness vs random trade ordering.
  - Parameter perturbation sensitivity analysis.
  - Formatted report generation and persistence via joblib.
"""
import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import joblib

logger = logging.getLogger(__name__)

_DEFAULT_RISK_FREE_RATE = 0.0
_DEFAULT_ANNUALIZATION_FACTOR = 252
_DEFAULT_WALK_TRAIN_BARS = 500
_DEFAULT_WALK_TEST_BARS = 100
_DEFAULT_MONTE_CARLO_RUNS = 1000
_DEFAULT_PERTURBATION_STEPS = 20
_DEFAULT_PERTURBATION_RANGE = 0.1
_MIN_TRADES_FOR_STATS = 5


@dataclass
class BacktestResult:
    """Complete output of a single backtest run."""
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_trade_duration: float
    expectancy: float
    total_pnl: float
    equity_curve: np.ndarray
    trades_per_day: float
    calmar_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 6),
            "avg_trade_duration": round(self.avg_trade_duration, 2),
            "expectancy": round(self.expectancy, 4),
            "total_pnl": round(self.total_pnl, 4),
            "equity_curve": self.equity_curve.tolist(),
            "trades_per_day": round(self.trades_per_day, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
        }


@dataclass
class WalkForwardWindow:
    """Result of one walk-forward window."""
    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_win_rate: float
    test_win_rate: float
    parameter_stability: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "train_win_rate": round(self.train_win_rate, 4),
            "test_win_rate": round(self.test_win_rate, 4),
            "parameter_stability": round(self.parameter_stability, 4),
        }


# ── Internal helpers ──────────────────────────────────────────────────────

def _extract_returns(trade_records: List[Dict[str, Any]]) -> np.ndarray:
    out: List[float] = []
    for rec in trade_records:
        pnl = rec.get("pnl", rec.get("profit", rec.get("result", 0.0)))
        try:
            out.append(float(pnl))
        except (TypeError, ValueError):
            out.append(0.0)
    return np.asarray(out, dtype=np.float64)


def _extract_durations(trade_records: List[Dict[str, Any]]) -> np.ndarray:
    out: List[float] = []
    for rec in trade_records:
        dur = rec.get("duration", rec.get("bars_held", 1))
        try:
            out.append(float(dur))
        except (TypeError, ValueError):
            out.append(1.0)
    return np.asarray(out, dtype=np.float64)


def _compute_equity_curve(returns: np.ndarray, initial_capital: float = 10_000.0) -> np.ndarray:
    curve = np.empty(len(returns) + 1, dtype=np.float64)
    curve[0] = initial_capital
    for i, r in enumerate(returns):
        curve[i + 1] = curve[i] + r
    return curve


def _max_drawdown(curve: np.ndarray) -> float:
    if len(curve) < 2:
        return 0.0
    peak = curve[0]
    max_dd = 0.0
    for val in curve[1:]:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak != 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def _sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0,
                  annualisation: int = _DEFAULT_ANNUALIZATION_FACTOR) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free_rate
    sigma = float(np.std(excess, ddof=1))
    if sigma < 1e-12:
        return 0.0
    return (float(np.mean(excess)) / sigma) * math.sqrt(float(annualisation))


def _profit_factor(returns: np.ndarray) -> float:
    gains = float(np.sum(returns[returns > 0]))
    losses = float(np.abs(np.sum(returns[returns < 0])))
    if losses < 1e-12:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _win_rate(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    return float(np.sum(returns > 0)) / float(len(returns))


def _expectancy(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    return float(np.mean(returns))


def _calmar_ratio(returns: np.ndarray, annualisation: int = _DEFAULT_ANNUALIZATION_FACTOR,
                  max_dd: Optional[float] = None) -> float:
    if len(returns) < 2:
        return 0.0
    if max_dd is None:
        max_dd = _max_drawdown(_compute_equity_curve(returns))
    if max_dd < 1e-12:
        return float("inf") if np.sum(returns) > 0 else 0.0
    return float(np.mean(returns)) * float(annualisation) / max_dd


# ── BacktestingEngine ─────────────────────────────────────────────────────

class BacktestingEngine:
    """Backtesting and walk-forward validation engine.

    Args:
        risk_free_rate: Annualised risk-free rate for Sharpe calculation.
        annualisation_factor: Trading days per year for annualisation.
        initial_capital: Starting equity for equity-curve simulation.
        monte_carlo_runs: Number of Monte Carlo permutation iterations.
        walk_train_bars: Default training window size in bars.
        walk_test_bars: Default testing window size in bars.
        perturbation_steps: Number of parameter-perturbation iterations.
        perturbation_range: Fractional perturbation range around base parameters.
    """

    def __init__(
        self,
        risk_free_rate: float = _DEFAULT_RISK_FREE_RATE,
        annualisation_factor: int = _DEFAULT_ANNUALIZATION_FACTOR,
        initial_capital: float = 10_000.0,
        monte_carlo_runs: int = _DEFAULT_MONTE_CARLO_RUNS,
        walk_train_bars: int = _DEFAULT_WALK_TRAIN_BARS,
        walk_test_bars: int = _DEFAULT_WALK_TEST_BARS,
        perturbation_steps: int = _DEFAULT_PERTURBATION_STEPS,
        perturbation_range: float = _DEFAULT_PERTURBATION_RANGE,
    ) -> None:
        self.risk_free_rate = risk_free_rate
        self.annualisation_factor = annualisation_factor
        self.initial_capital = initial_capital
        self.monte_carlo_runs = monte_carlo_runs
        self.walk_train_bars = walk_train_bars
        self.walk_test_bars = walk_test_bars
        self.perturbation_steps = perturbation_steps
        self.perturbation_range = perturbation_range
        self._last_backtest: Optional[BacktestResult] = None
        self._walk_forward_results: List[WalkForwardWindow] = []
        self._monte_carlo_distribution: Optional[np.ndarray] = None
        self._parameter_stability_map: Dict[str, List[float]] = {}
        logger.info(
            "BacktestingEngine initialised (rf=%.4f, ann=%d, cap=%.2f)",
            self.risk_free_rate, self.annualisation_factor, self.initial_capital,
        )

    # ── Core backtest ─────────────────────────────────────────────────────

    def run_backtest(
        self,
        trade_records: List[Dict[str, Any]],
        bars_per_day: float = 1.0,
    ) -> BacktestResult:
        """Simulate strategy on historical trades and compute comprehensive metrics.

        Args:
            trade_records: List of dicts with at least ``pnl``/``profit``/``result``
                and optional ``duration``/``bars_held`` keys.
            bars_per_day: Average bars per trading day for rate calculations.

        Returns:
            A ``BacktestResult`` with all computed metrics.
        """
        t0 = time.perf_counter()
        returns = _extract_returns(trade_records)
        durations = _extract_durations(trade_records)
        n_trades = len(returns)
        wr = _win_rate(returns)
        pf = _profit_factor(returns)
        sr = _sharpe_ratio(returns, self.risk_free_rate, self.annualisation_factor)
        curve = _compute_equity_curve(returns, self.initial_capital)
        mdd = _max_drawdown(curve)
        cr = _calmar_ratio(returns, self.annualisation_factor, mdd)
        exp = _expectancy(returns)
        total_pnl = float(np.sum(returns))
        avg_dur = float(np.mean(durations)) if len(durations) > 0 else 0.0
        tpd = float(n_trades) / max(bars_per_day, 1.0) if bars_per_day > 0 else float(n_trades)

        result = BacktestResult(
            total_trades=n_trades, win_rate=wr, profit_factor=pf, sharpe_ratio=sr,
            max_drawdown=mdd, avg_trade_duration=avg_dur, expectancy=exp, total_pnl=total_pnl,
            equity_curve=curve, trades_per_day=tpd, calmar_ratio=cr,
        )
        self._last_backtest = result
        logger.info(
            "Backtest complete: %d trades, WR=%.2f%%, PF=%.2f, SR=%.2f, MDD=%.4f (%.3fs)",
            n_trades, wr * 100, pf, sr, mdd, time.perf_counter() - t0,
        )
        return result

    # ── Walk-forward validation ───────────────────────────────────────────

    def walk_forward_validation(
        self,
        trade_records: List[Dict[str, Any]],
        train_bars: Optional[int] = None,
        test_bars: Optional[int] = None,
        step_bars: Optional[int] = None,
    ) -> List[WalkForwardWindow]:
        """Rolling walk-forward validation with in-sample / out-of-sample splits.

        Splits the trade sequence into rolling (train, test) windows, computes
        in-sample and out-of-sample win rates, and measures parameter stability
        as the ratio of OOS to IS performance.

        Args:
            trade_records: Ordered list of trade record dicts.
            train_bars: Training window size (default: ``self.walk_train_bars``).
            test_bars: Testing window size (default: ``self.walk_test_bars``).
            step_bars: Step size between windows. Defaults to ``test_bars``.

        Returns:
            List of ``WalkForwardWindow`` results.
        """
        if train_bars is None:
            train_bars = self.walk_train_bars
        if test_bars is None:
            test_bars = self.walk_test_bars
        if step_bars is None:
            step_bars = test_bars

        n = len(trade_records)
        windows: List[WalkForwardWindow] = []
        if n < train_bars + test_bars:
            logger.warning(
                "Not enough trades (%d) for walk-forward (need %d).",
                n, train_bars + test_bars,
            )
            return windows

        returns_all = _extract_returns(trade_records)
        window_id = 0
        start = 0
        while start + train_bars + test_bars <= n:
            train_slice = returns_all[start: start + train_bars]
            test_slice = returns_all[start + train_bars: start + train_bars + test_bars]
            train_wr = _win_rate(train_slice)
            test_wr = _win_rate(test_slice)
            stability = test_wr / train_wr if train_wr > 0 else 0.0
            windows.append(WalkForwardWindow(
                window_id=window_id, train_start=start, train_end=start + train_bars,
                test_start=start + train_bars, test_end=start + train_bars + test_bars,
                train_win_rate=train_wr, test_win_rate=test_wr,
                parameter_stability=stability,
            ))
            window_id += 1
            start += step_bars

        self._walk_forward_results = windows
        logger.info("Walk-forward: %d windows produced from %d trades.", len(windows), n)
        return windows

    # ── Monte Carlo permutation ───────────────────────────────────────────

    def monte_carlo_permutation(
        self,
        trade_records: List[Dict[str, Any]],
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """Shuffle trade returns to build a null distribution of Sharpe ratios.

        By randomly permuting the order of trade outcomes we build a null
        distribution of Sharpe ratios.  If the real Sharpe ratio sits in the
        extreme tail, the strategy performance is unlikely to be due to lucky
        ordering.

        Args:
            trade_records: List of trade record dicts.
            seed: Optional RNG seed for reproducibility.

        Returns:
            Numpy array of length ``self.monte_carlo_runs`` with shuffled Sharpe ratios.
        """
        returns = _extract_returns(trade_records)
        real_sharpe = _sharpe_ratio(returns, self.risk_free_rate, self.annualisation_factor)
        rng = np.random.default_rng(seed)
        n = len(returns)
        if n < _MIN_TRADES_FOR_STATS:
            logger.warning("Monte Carlo permutation requires >= %d trades.", _MIN_TRADES_FOR_STATS)
            return np.array([])

        distribution = np.empty(self.monte_carlo_runs, dtype=np.float64)
        for i in range(self.monte_carlo_runs):
            shuffled = rng.permutation(returns)
            distribution[i] = _sharpe_ratio(shuffled, self.risk_free_rate, self.annualisation_factor)

        p_value = float(np.mean(np.abs(distribution) >= abs(real_sharpe)))
        logger.info(
            "Monte Carlo permutation (%d runs): real SR=%.3f, p=%.4f",
            self.monte_carlo_runs, real_sharpe, p_value,
        )
        self._monte_carlo_distribution = distribution
        return distribution

    # ── Parameter stability ───────────────────────────────────────────────

    def parameter_stability_check(
        self,
        trade_records: List[Dict[str, Any]],
        param_names: List[str],
        base_params: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, List[float]]:
        """Test sensitivity of performance to small parameter perturbations.

        For each named parameter the engine perturbs its value by a random
        fraction within ``[-perturbation_range, +perturbation_range]`` across
        ``perturbation_steps`` iterations.  The resulting win-rate delta
        (perturbed minus base) is recorded per iteration.

        Args:
            trade_records: List of trade record dicts.
            param_names: List of parameter names to test.
            base_params: Base parameter dictionary.  Defaults to ``{}``.
            seed: Optional RNG seed for reproducibility.

        Returns:
            Dict mapping parameter name to list of win-rate deltas.
        """
        if base_params is None:
            base_params = {}
        rng = np.random.default_rng(seed)
        base_returns = _extract_returns(trade_records)
        base_wr = _win_rate(base_returns)
        stability_map: Dict[str, List[float]] = {name: [] for name in param_names}

        for name in param_names:
            for _ in range(self.perturbation_steps):
                perturb_factor = rng.uniform(-self.perturbation_range, self.perturbation_range)
                original_val = base_params.get(name, 1.0)
                perturbed_val = original_val * (1.0 + perturb_factor)
                perturbed_records = self._apply_param_shift(
                    trade_records, name, original_val, perturbed_val,
                )
                perturbed_wr = _win_rate(_extract_returns(perturbed_records))
                stability_map[name].append(perturbed_wr - base_wr)

        self._parameter_stability_map = stability_map
        logger.info(
            "Parameter stability check: %d params x %d steps.",
            len(param_names), self.perturbation_steps,
        )
        return stability_map

    @staticmethod
    def _apply_param_shift(
        trade_records: List[Dict[str, Any]],
        param_name: str,
        original: float,
        perturbed: float,
    ) -> List[Dict[str, Any]]:
        """Scale trade PnL by the parameter ratio (linear proxy)."""
        ratio = perturbed / original if abs(original) >= 1e-12 else 1.0
        shifted: List[Dict[str, Any]] = []
        for rec in trade_records:
            new_rec = dict(rec)
            pnl = new_rec.get("pnl", new_rec.get("profit", new_rec.get("result", 0.0)))
            try:
                new_rec["pnl"] = float(pnl) * ratio
            except (TypeError, ValueError):
                new_rec["pnl"] = 0.0
            shifted.append(new_rec)
        return shifted

    # ── Report generation ─────────────────────────────────────────────────

    def generate_report(self, result: Optional[BacktestResult] = None) -> str:
        """Generate a human-readable text report.

        Args:
            result: A ``BacktestResult`` to report on.  If *None*, uses the most
                recently computed backtest result.

        Returns:
            Multi-line formatted report string.
        """
        if result is None:
            result = self._last_backtest
        if result is None:
            return "No backtest results available."

        lines: List[str] = [
            "=" * 60,
            "  BACKTEST REPORT",
            "=" * 60,
            f"  Total Trades        : {result.total_trades}",
            f"  Win Rate            : {result.win_rate:.2%}",
            f"  Profit Factor       : {result.profit_factor:.4f}",
            f"  Sharpe Ratio        : {result.sharpe_ratio:.4f}",
            f"  Max Drawdown        : {result.max_drawdown:.4%}",
            f"  Calmar Ratio        : {result.calmar_ratio:.4f}",
            f"  Avg Trade Duration  : {result.avg_trade_duration:.2f} bars",
            f"  Expectancy          : {result.expectancy:.4f}",
            f"  Total PnL           : {result.total_pnl:.4f}",
            f"  Trades Per Day      : {result.trades_per_day:.2f}",
            "-" * 60,
        ]

        if self._walk_forward_results:
            lines.append("  WALK-FORWARD RESULTS")
            lines.append("-" * 60)
            for w in self._walk_forward_results:
                lines.append(
                    f"  Window {w.window_id:3d}: Train WR={w.train_win_rate:.2%}  "
                    f"Test WR={w.test_win_rate:.2%}  Stability={w.parameter_stability:.4f}"
                )
            avg_stab = np.mean([w.parameter_stability for w in self._walk_forward_results])
            lines.append(f"  Average Stability   : {avg_stab:.4f}")
            lines.append("-" * 60)

        if self._monte_carlo_distribution is not None and len(self._monte_carlo_distribution) > 0:
            dist = self._monte_carlo_distribution
            p_value = float(np.mean(np.abs(dist) >= abs(result.sharpe_ratio)))
            lines.extend([
                "  MONTE CARLO PERMUTATION",
                "-" * 60,
                f"  Runs                : {len(dist)}",
                f"  Mean Shuffled SR    : {float(np.mean(dist)):.4f}",
                f"  Std Shuffled SR     : {float(np.std(dist)):.4f}",
                f"  Real Sharpe SR      : {result.sharpe_ratio:.4f}",
                f"  p-value (2-tailed)  : {p_value:.4f}",
                "-" * 60,
            ])

        if self._parameter_stability_map:
            lines.append("  PARAMETER STABILITY")
            lines.append("-" * 60)
            for param_name, deltas in self._parameter_stability_map.items():
                mean_d = float(np.mean(deltas))
                std_d = float(np.std(deltas))
                lines.append(
                    f"  {param_name:20s}: mean_delta={mean_d:+.4f}  std_delta={std_d:.4f}"
                )
            lines.append("-" * 60)

        lines.append("=" * 60)
        report = "\n".join(lines)
        logger.info("Generated backtest report (%d lines).", len(lines))
        return report

    # ── Validation statistics ─────────────────────────────────────────────

    def get_validation_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across walk-forward windows.

        Returns:
            Dict with keys ``num_windows``, ``mean_train_win_rate``,
            ``mean_test_win_rate``, ``mean_stability``, ``std_stability``,
            ``overfitting_ratio`` (mean test / mean train), and
            ``percent_stable`` (fraction of windows with stability >= 0.8).
        """
        windows = self._walk_forward_results
        if not windows:
            return {
                "num_windows": 0, "mean_train_win_rate": 0.0, "mean_test_win_rate": 0.0,
                "mean_stability": 0.0, "std_stability": 0.0,
                "overfitting_ratio": 0.0, "percent_stable": 0.0,
            }

        train_wrs = np.array([w.train_win_rate for w in windows])
        test_wrs = np.array([w.test_win_rate for w in windows])
        stabilities = np.array([w.parameter_stability for w in windows])

        mean_tr = float(np.mean(train_wrs))
        mean_te = float(np.mean(test_wrs))
        mean_stab = float(np.mean(stabilities))
        std_stab = float(np.std(stabilities, ddof=1)) if len(stabilities) > 1 else 0.0
        overfit = mean_te / mean_tr if mean_tr > 1e-12 else 0.0
        pct_stable = float(np.mean(stabilities >= 0.8))

        stats: Dict[str, Any] = {
            "num_windows": len(windows),
            "mean_train_win_rate": round(mean_tr, 4),
            "mean_test_win_rate": round(mean_te, 4),
            "mean_stability": round(mean_stab, 4),
            "std_stability": round(std_stab, 4),
            "overfitting_ratio": round(overfit, 4),
            "percent_stable": round(pct_stable, 4),
        }
        logger.info("Validation stats: %s", stats)
        return stats

    # ── Persistence ───────────────────────────────────────────────────────

    def save(self, filepath: str) -> None:
        """Persist the engine state to disk via joblib."""
        state = {
            "risk_free_rate": self.risk_free_rate,
            "annualisation_factor": self.annualisation_factor,
            "initial_capital": self.initial_capital,
            "monte_carlo_runs": self.monte_carlo_runs,
            "walk_train_bars": self.walk_train_bars,
            "walk_test_bars": self.walk_test_bars,
            "perturbation_steps": self.perturbation_steps,
            "perturbation_range": self.perturbation_range,
            "last_backtest": self._last_backtest,
            "walk_forward_results": self._walk_forward_results,
            "monte_carlo_distribution": self._monte_carlo_distribution,
            "parameter_stability_map": self._parameter_stability_map,
        }
        joblib.dump(state, filepath)
        logger.info("BacktestingEngine saved to %s", filepath)

    @classmethod
    def load(cls, filepath: str) -> "BacktestingEngine":
        """Load a previously persisted engine from disk."""
        state: Dict[str, Any] = joblib.load(filepath)
        engine = cls(
            risk_free_rate=state.get("risk_free_rate", _DEFAULT_RISK_FREE_RATE),
            annualisation_factor=state.get("annualisation_factor", _DEFAULT_ANNUALIZATION_FACTOR),
            initial_capital=state.get("initial_capital", 10_000.0),
            monte_carlo_runs=state.get("monte_carlo_runs", _DEFAULT_MONTE_CARLO_RUNS),
            walk_train_bars=state.get("walk_train_bars", _DEFAULT_WALK_TRAIN_BARS),
            walk_test_bars=state.get("walk_test_bars", _DEFAULT_WALK_TEST_BARS),
            perturbation_steps=state.get("perturbation_steps", _DEFAULT_PERTURBATION_STEPS),
            perturbation_range=state.get("perturbation_range", _DEFAULT_PERTURBATION_RANGE),
        )
        engine._last_backtest = state.get("last_backtest")
        engine._walk_forward_results = state.get("walk_forward_results", [])
        engine._monte_carlo_distribution = state.get("monte_carlo_distribution")
        engine._parameter_stability_map = state.get("parameter_stability_map", {})
        logger.info("BacktestingEngine loaded from %s", filepath)
        return engine
