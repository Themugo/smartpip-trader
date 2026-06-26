"""
Performance Metrics — quantitative analysis of trade journal data.
Computes: Sharpe ratio, profit factor, max drawdown, Calmar ratio,
expected value, win-rate by condition/regime/hour, Kelly criterion.
"""
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Compute institutional-grade trading performance metrics."""

    RISK_FREE_RATE = 0.05  # 5% annual

    # ── Core P&L metrics ──────────────────────────────────────────────────

    @staticmethod
    def profit_factor(trades: List[Dict]) -> float:
        """Gross profit / Gross loss. >1.5 is good, >2.0 is excellent."""
        gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
        return round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf")

    @staticmethod
    def win_rate(trades: List[Dict]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        return round(wins / len(trades) * 100, 2)

    @staticmethod
    def expected_value(trades: List[Dict]) -> float:
        """Average P&L per trade (Kelly-relevant)."""
        if not trades:
            return 0.0
        return round(sum(t.get("pnl", 0) for t in trades) / len(trades), 4)

    @staticmethod
    def avg_win_loss_ratio(trades: List[Dict]) -> float:
        wins  = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
        losses = [abs(t["pnl"]) for t in trades if t.get("pnl", 0) < 0]
        avg_w = sum(wins) / len(wins) if wins else 0
        avg_l = sum(losses) / len(losses) if losses else 1
        return round(avg_w / avg_l, 4) if avg_l > 0 else 0.0

    # ── Risk metrics ──────────────────────────────────────────────────────

    @staticmethod
    def max_drawdown(trades: List[Dict]) -> Dict[str, float]:
        """Max drawdown as % of peak equity."""
        if not trades:
            return {"max_dd_pct": 0.0, "max_dd_abs": 0.0, "peak": 0.0, "trough": 0.0}
        balances = [t.get("running_balance", 1000.0) for t in trades]
        peak = balances[0]
        max_dd = 0.0
        peak_val = peak
        trough_val = peak
        for b in balances:
            if b > peak:
                peak = b
            dd = (peak - b) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                peak_val = peak
                trough_val = b
        return {
            "max_dd_pct": round(max_dd, 2),
            "max_dd_abs": round(peak_val - trough_val, 4),
            "peak": round(peak_val, 4),
            "trough": round(trough_val, 4),
        }

    @staticmethod
    def current_drawdown(trades: List[Dict]) -> float:
        if not trades:
            return 0.0
        balances = [t.get("running_balance", 1000.0) for t in trades]
        peak = max(balances)
        current = balances[-1]
        return round((peak - current) / peak * 100, 2) if peak > 0 else 0.0

    @staticmethod
    def consecutive_losses(trades: List[Dict]) -> Dict[str, int]:
        max_cl = cur_cl = 0
        for t in trades:
            if t.get("pnl", 0) < 0:
                cur_cl += 1
                max_cl = max(max_cl, cur_cl)
            else:
                cur_cl = 0
        return {"max_consecutive_losses": max_cl, "current_streak": cur_cl}

    # ── Risk-adjusted returns ─────────────────────────────────────────────

    @classmethod
    def sharpe_ratio(cls, trades: List[Dict], periods_per_year: int = 252) -> float:
        """Annualised Sharpe ratio."""
        if len(trades) < 2:
            return 0.0
        returns = [t.get("pnl", 0) / t.get("amount", 1) for t in trades if t.get("amount", 0) > 0]
        if len(returns) < 2:
            return 0.0
        n = len(returns)
        mean_r = sum(returns) / n
        variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
        std_r = math.sqrt(variance)
        if std_r == 0:
            return 0.0
        daily_rf = cls.RISK_FREE_RATE / periods_per_year
        sharpe = (mean_r - daily_rf) / std_r * math.sqrt(periods_per_year)
        return round(sharpe, 4)

    @classmethod
    def calmar_ratio(cls, trades: List[Dict]) -> float:
        """Annualised return / Max drawdown. >3 is excellent."""
        dd = cls.max_drawdown(trades)
        max_dd_pct = dd["max_dd_pct"]
        if max_dd_pct == 0 or not trades:
            return 0.0
        total_return_pct = sum(t.get("pnl", 0) for t in trades)
        if trades[0].get("running_balance"):
            total_return_pct = total_return_pct / trades[0]["running_balance"] * 100
        return round(total_return_pct / max_dd_pct, 4)

    # ── Kelly criterion ────────────────────────────────────────────────────

    @classmethod
    def kelly_fraction(cls, trades: List[Dict]) -> float:
        """Optimal bet size as fraction of bankroll (full Kelly — use 25%)."""
        wins = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
        losses = [abs(t["pnl"]) for t in trades if t.get("pnl", 0) < 0]
        if not wins or not losses:
            return 0.0
        p = len(wins) / len(trades)
        q = 1 - p
        avg_win = sum(wins) / len(wins)
        avg_loss = sum(losses) / len(losses)
        b = avg_win / avg_loss if avg_loss > 0 else 1
        kelly = (b * p - q) / b
        return round(max(0.0, min(kelly, 0.5)), 4)  # cap at 50%

    # ── Condition-level analytics ─────────────────────────────────────────

    @staticmethod
    def condition_win_rates(trades: List[Dict]) -> Dict[str, Dict]:
        """Win rate and P&L for each entry condition."""
        condition_stats: Dict[str, Dict] = defaultdict(lambda: {
            "trades": 0, "wins": 0, "total_pnl": 0.0
        })
        for t in trades:
            conditions = t.get("entry_conditions", [])
            won = t.get("pnl", 0) > 0
            pnl = t.get("pnl", 0)
            for cond in conditions:
                if isinstance(cond, str):
                    key = cond.split(":")[0].strip() if ":" in cond else cond[:40]
                    condition_stats[key]["trades"] += 1
                    condition_stats[key]["total_pnl"] += pnl
                    if won:
                        condition_stats[key]["wins"] += 1
        result = {}
        for cond, stats in condition_stats.items():
            n = stats["trades"]
            if n > 0:
                wr = stats["wins"] / n * 100
                ev = stats["total_pnl"] / n
                result[cond] = {
                    "trades": n,
                    "win_rate": round(wr, 1),
                    "expected_value": round(ev, 4),
                    "total_pnl": round(stats["total_pnl"], 4),
                }
        return dict(sorted(result.items(), key=lambda x: x[1]["win_rate"], reverse=True))

    # ── Regime analytics ─────────────────────────────────────────────────

    @staticmethod
    def regime_performance(trades: List[Dict]) -> Dict[str, Dict]:
        """Performance breakdown by market regime."""
        regime_stats: Dict[str, Dict] = defaultdict(lambda: {
            "trades": 0, "wins": 0, "total_pnl": 0.0
        })
        for t in trades:
            regime = t.get("regime", "unknown")
            regime_stats[regime]["trades"] += 1
            regime_stats[regime]["total_pnl"] += t.get("pnl", 0)
            if t.get("pnl", 0) > 0:
                regime_stats[regime]["wins"] += 1
        result = {}
        for regime, stats in regime_stats.items():
            n = stats["trades"]
            result[regime] = {
                "trades": n,
                "win_rate": round(stats["wins"] / n * 100, 1) if n > 0 else 0,
                "total_pnl": round(stats["total_pnl"], 4),
                "avg_pnl": round(stats["total_pnl"] / n, 4) if n > 0 else 0,
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["win_rate"], reverse=True))

    # ── Time-of-day analytics ─────────────────────────────────────────────

    @staticmethod
    def time_of_day_performance(trades: List[Dict]) -> Dict[str, Dict]:
        """Win rate and P&L by hour (UTC) — identifies optimal trading windows."""
        hour_stats: Dict[int, Dict] = defaultdict(lambda: {
            "trades": 0, "wins": 0, "total_pnl": 0.0
        })
        for t in trades:
            ts = t.get("timestamp") or t.get("created_at")
            if not ts:
                continue
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = ts
                hour = dt.hour
            except Exception:
                continue
            hour_stats[hour]["trades"] += 1
            hour_stats[hour]["total_pnl"] += t.get("pnl", 0)
            if t.get("pnl", 0) > 0:
                hour_stats[hour]["wins"] += 1

        result = {}
        for hour in range(24):
            stats = hour_stats[hour]
            n = stats["trades"]
            result[f"{hour:02d}:00"] = {
                "hour": hour,
                "trades": n,
                "win_rate": round(stats["wins"] / n * 100, 1) if n > 0 else 0,
                "total_pnl": round(stats["total_pnl"], 4),
                "avg_pnl": round(stats["total_pnl"] / n, 4) if n > 0 else 0,
            }
        return result

    # ── Confidence-band analytics ─────────────────────────────────────────

    @staticmethod
    def confidence_band_performance(trades: List[Dict]) -> Dict[str, Dict]:
        """Win rate by confidence band (50-60%, 60-70%, 70-80%, 80-90%, 90%+)."""
        bands = {
            "50-60": {"min": 50, "max": 60, "trades": 0, "wins": 0, "pnl": 0.0},
            "60-70": {"min": 60, "max": 70, "trades": 0, "wins": 0, "pnl": 0.0},
            "70-80": {"min": 70, "max": 80, "trades": 0, "wins": 0, "pnl": 0.0},
            "80-90": {"min": 80, "max": 90, "trades": 0, "wins": 0, "pnl": 0.0},
            "90+":   {"min": 90, "max": 101, "trades": 0, "wins": 0, "pnl": 0.0},
        }
        for t in trades:
            conf = t.get("confidence", 0)
            for label, band in bands.items():
                if band["min"] <= conf < band["max"]:
                    band["trades"] += 1
                    band["pnl"] += t.get("pnl", 0)
                    if t.get("pnl", 0) > 0:
                        band["wins"] += 1
                    break
        result = {}
        for label, band in bands.items():
            n = band["trades"]
            result[label + "%"] = {
                "trades": n,
                "win_rate": round(band["wins"] / n * 100, 1) if n > 0 else 0,
                "total_pnl": round(band["pnl"], 4),
                "avg_pnl": round(band["pnl"] / n, 4) if n > 0 else 0,
            }
        return result

    # ── Full report ───────────────────────────────────────────────────────

    @classmethod
    def full_report(cls, trades: List[Dict]) -> Dict[str, Any]:
        closed = [t for t in trades if t.get("pnl") is not None]
        if not closed:
            return {"error": "No closed trades", "total_trades": 0}
        return {
            "total_trades": len(closed),
            "win_rate": cls.win_rate(closed),
            "profit_factor": cls.profit_factor(closed),
            "expected_value": cls.expected_value(closed),
            "avg_win_loss_ratio": cls.avg_win_loss_ratio(closed),
            "sharpe_ratio": cls.sharpe_ratio(closed),
            "calmar_ratio": cls.calmar_ratio(closed),
            "kelly_fraction": cls.kelly_fraction(closed),
            "max_drawdown": cls.max_drawdown(closed),
            "current_drawdown": cls.current_drawdown(closed),
            "consecutive_losses": cls.consecutive_losses(closed),
            "condition_win_rates": cls.condition_win_rates(closed),
            "regime_performance": cls.regime_performance(closed),
            "time_of_day": cls.time_of_day_performance(closed),
            "confidence_bands": cls.confidence_band_performance(closed),
            "total_pnl": round(sum(t.get("pnl", 0) for t in closed), 4),
        }
