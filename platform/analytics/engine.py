"""
Analytics Engine — comprehensive analytics for all trading activity.
Computes performance summaries, risk metrics, equity curves, and breakdowns.
Uses numpy + scipy for statistics, joblib for persistence.
"""
from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _import_joblib():
    import importlib
    import sys
    from pathlib import Path as _P

    saved_platform = sys.modules.pop("platform", None)
    removed_paths = []
    for p in list(sys.path):
        try:
            if (_P(p) / "platform").is_dir():
                removed_paths.append(p)
                sys.path.remove(p)
        except Exception:
            pass

    import importlib as _imp
    real_platform = _imp.import_module("platform")
    sys.modules["platform"] = real_platform

    import joblib as _joblib

    sys.modules["platform"] = saved_platform
    for p in removed_paths:
        sys.path.insert(0, p)

    return _joblib.dump, _joblib.load


@dataclass
class PerformanceSummary:
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskMetrics:
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    value_at_risk: float = 0.0
    conditional_var: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DrawdownAnalysis:
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    drawdown_duration: float = 0.0
    recovery_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StreakAnalysis:
    max_win_streak: int = 0
    max_loss_streak: int = 0
    current_streak: int = 0
    avg_streak_length: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


RISK_FREE_RATE: float = 0.05
ANNUALIZATION_FACTOR: int = 252


class AnalyticsEngine:
    """Comprehensive analytics for all trading activity."""

    def __init__(self, data_dir: str = "analytics_data") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._trades: List[Dict[str, Any]] = []
        self._equity_history: List[Dict[str, Any]] = []

        existing = self._data_dir / "trades.joblib"
        if existing.exists():
            self._load_internal(existing)
        logger.info(
            "AnalyticsEngine ready — %d trades loaded", len(self._trades)
        )

    # ── Record trade ─────────────────────────────────────────────────────

    def record_trade(self, trade: Dict[str, Any]) -> None:
        """Record a completed trade and update equity history."""
        record = {
            "id": trade.get("id", f"t_{len(self._trades)}"),
            "market": trade.get("market", trade.get("symbol", "UNKNOWN")),
            "strategy": trade.get("strategy", "default"),
            "direction": trade.get("direction", "long"),
            "entry_price": trade.get("entry_price", 0.0),
            "exit_price": trade.get("exit_price", 0.0),
            "amount": trade.get("amount", 0.0),
            "pnl": trade.get("pnl", 0.0),
            "pnl_pct": trade.get("pnl_pct", 0.0),
            "confidence": trade.get("confidence", 0.0),
            "duration": trade.get("duration", 0.0),
            "entry_time": trade.get(
                "entry_time", trade.get("timestamp", time.time())
            ),
            "exit_time": trade.get("exit_time", time.time()),
            "regime": trade.get("regime", "unknown"),
            "stop_loss": trade.get("stop_loss", 0.0),
            "take_profit": trade.get("take_profit", 0.0),
            "running_balance": trade.get("running_balance", 0.0),
            "entry_conditions": trade.get("entry_conditions", []),
        }
        self._trades.append(record)
        self._equity_history.append(
            {
                "timestamp": record["exit_time"],
                "balance": record["running_balance"],
                "pnl": record["pnl"],
            }
        )
        self._persist_trades()
        logger.info(
            "Trade recorded: %s %s pnl=%.4f",
            record["market"],
            record["direction"],
            record["pnl"],
        )

    # ── Performance summary ──────────────────────────────────────────────

    def get_performance_summary(self, days: int = 30) -> PerformanceSummary:
        """Aggregate performance metrics for the last N days."""
        trades = self._filter_days(days)
        if not trades:
            return PerformanceSummary()

        pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)
        n = len(pnls)
        wins = int(np.sum(pnls > 0))
        losses_count = int(np.sum(pnls < 0))
        gross_profit = float(np.sum(pnls[pnls > 0]))
        gross_loss = float(np.abs(np.sum(pnls[pnls < 0])))

        durations = np.array(
            [t.get("duration", 0.0) for t in trades], dtype=np.float64
        )
        returns = np.array(
            [
                t["pnl"] / t["amount"]
                for t in trades
                if t.get("amount", 0) > 0
            ],
            dtype=np.float64,
        )
        sharpe = self._compute_sharpe(returns)
        dd = self._compute_drawdowns(pnls)

        return PerformanceSummary(
            total_trades=n,
            win_rate=round((wins / n) * 100, 2) if n > 0 else 0.0,
            profit_factor=round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
            total_pnl=round(float(np.sum(pnls)), 4),
            avg_pnl=round(float(np.mean(pnls)), 4),
            best_trade=round(float(np.max(pnls)), 4),
            worst_trade=round(float(np.min(pnls)), 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(dd["max_drawdown"], 4),
            avg_duration=round(float(np.mean(durations)), 2) if n > 0 else 0.0,
        )

    # ── Equity curve ─────────────────────────────────────────────────────

    def get_equity_curve(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return equity over time for the last N days."""
        cutoff = time.time() - days * 86400
        if not self._equity_history:
            return []
        curve = [e for e in self._equity_history if e["timestamp"] >= cutoff]
        if not curve:
            return []

        arr = np.array([e["balance"] for e in curve], dtype=np.float64)
        peaks = np.maximum.accumulate(arr)
        dd_pct = np.where(peaks > 0, (peaks - arr) / peaks * 100, 0.0)

        result = []
        for i, entry in enumerate(curve):
            result.append(
                {
                    "timestamp": entry["timestamp"],
                    "balance": round(float(arr[i]), 4),
                    "pnl": round(entry["pnl"], 4),
                    "drawdown_pct": round(float(dd_pct[i]), 4),
                }
            )
        return result

    # ── Strategy breakdown ───────────────────────────────────────────────

    def get_strategy_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Per-strategy analytics."""
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for t in self._trades:
            groups[t.get("strategy", "default")].append(t)

        result: Dict[str, Dict[str, Any]] = {}
        for strat, trades in groups.items():
            pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)
            n = len(pnls)
            wins = int(np.sum(pnls > 0))
            gross_profit = float(np.sum(pnls[pnls > 0]))
            gross_loss = float(np.abs(np.sum(pnls[pnls < 0])))
            returns = np.array(
                [t["pnl"] / t["amount"] for t in trades if t.get("amount", 0) > 0],
                dtype=np.float64,
            )
            result[strat] = {
                "total_trades": n,
                "win_rate": round((wins / n) * 100, 2) if n > 0 else 0.0,
                "total_pnl": round(float(np.sum(pnls)), 4),
                "avg_pnl": round(float(np.mean(pnls)), 4) if n > 0 else 0.0,
                "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
                "sharpe_ratio": round(self._compute_sharpe(returns), 4),
                "best_trade": round(float(np.max(pnls)), 4) if n > 0 else 0.0,
                "worst_trade": round(float(np.min(pnls)), 4) if n > 0 else 0.0,
                "avg_confidence": round(
                    float(np.mean([t.get("confidence", 0) for t in trades])), 4
                ),
            }
        return result

    # ── Market breakdown ─────────────────────────────────────────────────

    def get_market_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Per-market (symbol) analytics."""
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for t in self._trades:
            groups[t.get("market", "UNKNOWN")].append(t)

        result: Dict[str, Dict[str, Any]] = {}
        for market, trades in groups.items():
            pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)
            n = len(pnls)
            wins = int(np.sum(pnls > 0))
            gross_profit = float(np.sum(pnls[pnls > 0]))
            gross_loss = float(np.abs(np.sum(pnls[pnls < 0])))
            returns = np.array(
                [t["pnl"] / t["amount"] for t in trades if t.get("amount", 0) > 0],
                dtype=np.float64,
            )
            result[market] = {
                "total_trades": n,
                "win_rate": round((wins / n) * 100, 2) if n > 0 else 0.0,
                "total_pnl": round(float(np.sum(pnls)), 4),
                "avg_pnl": round(float(np.mean(pnls)), 4) if n > 0 else 0.0,
                "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
                "sharpe_ratio": round(self._compute_sharpe(returns), 4),
                "best_trade": round(float(np.max(pnls)), 4) if n > 0 else 0.0,
                "worst_trade": round(float(np.min(pnls)), 4) if n > 0 else 0.0,
            }
        return result

    # ── Time analysis ────────────────────────────────────────────────────

    def get_time_analysis(self) -> Dict[str, Any]:
        """Performance by hour of day and day of week."""
        hour_stats: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0}
        )
        dow_stats: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0}
        )
        for t in self._trades:
            ts = t.get("entry_time", t.get("exit_time", 0))
            try:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            except (OSError, ValueError):
                continue
            hour = dt.hour
            dow = dt.weekday()

            hour_stats[hour]["trades"] += 1
            hour_stats[hour]["total_pnl"] += t["pnl"]
            if t["pnl"] > 0:
                hour_stats[hour]["wins"] += 1

            dow_stats[dow]["trades"] += 1
            dow_stats[dow]["total_pnl"] += t["pnl"]
            if t["pnl"] > 0:
                dow_stats[dow]["wins"] += 1

        by_hour: Dict[str, Dict[str, Any]] = {}
        for h in range(24):
            s = hour_stats[h]
            n = s["trades"]
            by_hour[f"{h:02d}:00"] = {
                "trades": n,
                "win_rate": round(s["wins"] / n * 100, 1) if n > 0 else 0.0,
                "total_pnl": round(s["total_pnl"], 4),
                "avg_pnl": round(s["total_pnl"] / n, 4) if n > 0 else 0.0,
            }

        day_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        by_day: Dict[str, Dict[str, Any]] = {}
        for d in range(7):
            s = dow_stats[d]
            n = s["trades"]
            by_day[day_names[d]] = {
                "trades": n,
                "win_rate": round(s["wins"] / n * 100, 1) if n > 0 else 0.0,
                "total_pnl": round(s["total_pnl"], 4),
                "avg_pnl": round(s["total_pnl"] / n, 4) if n > 0 else 0.0,
            }

        return {"by_hour": by_hour, "by_day_of_week": by_day}

    # ── Risk metrics ─────────────────────────────────────────────────────

    def get_risk_metrics(self) -> RiskMetrics:
        """Comprehensive risk metrics including VaR, CVaR, beta, alpha."""
        if not self._trades:
            return RiskMetrics()

        returns = np.array(
            [
                t["pnl"] / t["amount"]
                for t in self._trades
                if t.get("amount", 0) > 0
            ],
            dtype=np.float64,
        )
        pnls = np.array([t["pnl"] for t in self._trades], dtype=np.float64)

        if len(returns) < 2:
            return RiskMetrics()

        sharpe = self._compute_sharpe(returns)

        downside = returns[returns < 0]
        if len(downside) > 1:
            downside_std = float(np.std(downside, ddof=1))
            sortino = (
                (float(np.mean(returns)) - RISK_FREE_RATE / ANNUALIZATION_FACTOR)
                / downside_std
                * math.sqrt(ANNUALIZATION_FACTOR)
                if downside_std > 0
                else 0.0
            )
        else:
            sortino = 0.0

        dd_analysis = self._compute_drawdown_analysis(pnls)
        max_dd = dd_analysis["max_drawdown"]
        calmar = 0.0
        if max_dd > 0:
            total_return = float(np.sum(pnls))
            if self._trades[0].get("running_balance", 0) > 0:
                total_return_pct = (
                    total_return / self._trades[0]["running_balance"] * 100
                )
                calmar = total_return_pct / max_dd

        var_95 = float(np.percentile(returns, 5))
        cvar_mask = returns[returns <= var_95]
        cvar_95 = float(np.mean(cvar_mask)) if len(cvar_mask) > 0 else var_95

        market_returns = self._synthetic_market_returns(len(returns))
        covariance = np.cov(returns, market_returns)[0][1]
        market_var = np.var(market_returns, ddof=1)
        beta = float(covariance / market_var) if market_var > 0 else 0.0
        alpha = (
            float(np.mean(returns))
            - RISK_FREE_RATE / ANNUALIZATION_FACTOR
            - beta * (float(np.mean(market_returns)) - RISK_FREE_RATE / ANNUALIZATION_FACTOR)
        ) * ANNUALIZATION_FACTOR

        return RiskMetrics(
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            max_drawdown=round(max_dd, 4),
            value_at_risk=round(var_95, 6),
            conditional_var=round(cvar_95, 6),
            beta=round(beta, 4),
            alpha=round(alpha, 4),
        )

    # ── Drawdown analysis ────────────────────────────────────────────────

    def get_drawdown_analysis(self) -> DrawdownAnalysis:
        """Detailed drawdown analysis."""
        pnls = np.array([t["pnl"] for t in self._trades], dtype=np.float64)
        if len(pnls) == 0:
            return DrawdownAnalysis()

        data = self._compute_drawdown_analysis(pnls)
        return DrawdownAnalysis(
            max_drawdown=round(data["max_drawdown"], 4),
            current_drawdown=round(data["current_drawdown"], 4),
            avg_drawdown=round(data["avg_drawdown"], 4),
            drawdown_duration=round(data["drawdown_duration"], 2),
            recovery_time=round(data["recovery_time"], 2),
        )

    # ── Streak analysis ──────────────────────────────────────────────────

    def get_streak_analysis(self) -> StreakAnalysis:
        """Win/loss streak statistics."""
        if not self._trades:
            return StreakAnalysis()

        outcomes = [1 if t["pnl"] > 0 else -1 for t in self._trades]
        arr = np.array(outcomes, dtype=np.int32)

        max_win = max_loss = current_len = 0
        current_val = 0
        streaks: List[int] = []

        for v in arr:
            if v == current_val:
                current_len += 1
            else:
                if current_val == 1:
                    max_win = max(max_win, current_len)
                elif current_val == -1:
                    max_loss = max(max_loss, current_len)
                if current_len > 0:
                    streaks.append(current_len)
                current_val = v
                current_len = 1

        if current_val == 1:
            max_win = max(max_win, current_len)
        elif current_val == -1:
            max_loss = max(max_loss, current_len)
        if current_len > 0:
            streaks.append(current_len)

        current_streak = current_len if current_len > 0 else 0
        if current_val == -1:
            current_streak = -current_streak

        avg_len = float(np.mean(streaks)) if streaks else 0.0

        return StreakAnalysis(
            max_win_streak=max_win,
            max_loss_streak=max_loss,
            current_streak=current_streak,
            avg_streak_length=round(avg_len, 2),
        )

    # ── Export report ────────────────────────────────────────────────────

    def export_report(
        self, path: str, format: str = "json"
    ) -> None:
        """Export a full analytics report."""
        report: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_trades": len(self._trades),
            "performance_summary": self.get_performance_summary(
                days=max(1, len(self._trades))
            ).to_dict(),
            "risk_metrics": self.get_risk_metrics().to_dict(),
            "drawdown_analysis": self.get_drawdown_analysis().to_dict(),
            "streak_analysis": self.get_streak_analysis().to_dict(),
            "strategy_breakdown": self.get_strategy_breakdown(),
            "market_breakdown": self.get_market_breakdown(),
            "time_analysis": self.get_time_analysis(),
            "equity_curve": self.get_equity_curve(
                days=max(1, len(self._trades))
            ),
        }
        if format == "json":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
        else:
            dump_jlib, _ = _import_joblib()
            dump_jlib(report, path)
        logger.info("Report exported to %s (format=%s)", path, format)

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist engine state to disk via joblib."""
        dump_jlib, _ = _import_joblib()
        state = {
            "trades": self._trades[-5000:],
            "equity_history": self._equity_history[-5000:],
        }
        dump_jlib(state, path)
        logger.info("AnalyticsEngine saved to %s", path)

    def load(self, path: str) -> None:
        """Restore engine state from disk via joblib."""
        if not Path(path).exists():
            logger.warning("No saved state at %s", path)
            return
        self._load_internal(path)
        logger.info("AnalyticsEngine loaded from %s", path)

    def _load_internal(self, path: Path) -> None:
        """Internal loader used by __init__ and load."""
        _, joblib_load = _import_joblib()
        state = joblib_load(str(path))
        self._trades = state.get("trades", [])
        self._equity_history = state.get("equity_history", [])

    # ── Internal helpers ─────────────────────────────────────────────────

    def _persist_trades(self) -> None:
        """Auto-save trade data after each record."""
        dump_jlib, _ = _import_joblib()
        path = self._data_dir / "trades.joblib"
        state = {
            "trades": self._trades[-5000:],
            "equity_history": self._equity_history[-5000:],
        }
        dump_jlib(state, str(path))

    def _filter_days(self, days: int) -> List[Dict[str, Any]]:
        """Return trades from the last N days."""
        cutoff = time.time() - days * 86400
        return [t for t in self._trades if t.get("exit_time", 0) >= cutoff]

    @staticmethod
    def _compute_sharpe(returns: np.ndarray) -> float:
        """Annualized Sharpe ratio from per-trade returns."""
        if len(returns) < 2:
            return 0.0
        n = len(returns)
        mean_r = float(np.mean(returns))
        std_r = float(np.std(returns, ddof=1))
        if std_r == 0:
            return 0.0
        daily_rf = RISK_FREE_RATE / ANNUALIZATION_FACTOR
        return round(
            (mean_r - daily_rf) / std_r * math.sqrt(ANNUALIZATION_FACTOR), 4
        )

    @staticmethod
    def _compute_drawdowns(pnls: np.ndarray) -> Dict[str, float]:
        """Compute drawdown metrics from a P&L series."""
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        current_dd = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        return {
            "max_drawdown": max_dd,
            "current_drawdown": current_dd,
            "avg_drawdown": float(np.mean(drawdowns)) if len(drawdowns) > 0 else 0.0,
        }

    @staticmethod
    def _compute_drawdown_analysis(pnls: np.ndarray) -> Dict[str, float]:
        """Full drawdown analysis from a P&L series."""
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative

        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        current_dd = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        avg_dd = float(np.mean(drawdowns)) if len(drawdowns) > 0 else 0.0

        in_dd = False
        dd_start = 0
        max_dd_duration = 0.0
        max_recovery = 0.0
        for i, dd_val in enumerate(drawdowns):
            if dd_val > 0 and not in_dd:
                in_dd = True
                dd_start = i
            elif dd_val == 0 and in_dd:
                in_dd = False
                duration = i - dd_start
                if duration > max_dd_duration:
                    max_dd_duration = float(duration)
                if duration > max_recovery:
                    max_recovery = float(duration)

        if in_dd:
            duration = len(drawdowns) - dd_start
            if duration > max_dd_duration:
                max_dd_duration = float(duration)

        return {
            "max_drawdown": max_dd,
            "current_drawdown": current_dd,
            "avg_drawdown": avg_dd,
            "drawdown_duration": max_dd_duration,
            "recovery_time": max_recovery,
        }

    def _synthetic_market_returns(self, n: int) -> np.ndarray:
        """Generate synthetic market returns for beta/alpha calculation."""
        np.random.seed(42)
        market_daily_vol = 0.01
        market_daily_drift = RISK_FREE_RATE / ANNUALIZATION_FACTOR
        returns = np.random.normal(
            market_daily_drift, market_daily_vol, size=n
        )
        return returns
