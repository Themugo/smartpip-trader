"""
Weekly Insights Engine — quantitative analysis of a week's trades.
Identifies best/worst setups, time-of-day windows, regime performance,
and flags statistically significant edges using chi-squared significance.
"""
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from .performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class WeeklyInsightsEngine:
    """Generate weekly quantitative insights from trade journal data."""

    MIN_SAMPLE = 3  # minimum trades for statistical relevance

    def __init__(self):
        self.metrics = PerformanceMetrics()

    def generate(self, trades: List[Dict], week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Full weekly report generation."""
        if not trades:
            return {"error": "No trades found for this period", "trades": 0}

        closed = [t for t in trades if t.get("pnl") is not None]
        if not closed:
            return {"error": "No closed trades to analyze", "trades": len(trades)}

        week_start = week_start or self._infer_week_start(closed)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59)

        # Core metrics
        report = self.metrics.full_report(closed)

        # Setups: best/worst
        best_setups, worst_setups = self._rank_setups(closed)

        # Time-of-day best/worst windows
        tod = self.metrics.time_of_day_performance(closed)
        best_hours, worst_hours = self._rank_hours(tod)

        # Regime analysis
        regime_perf = self.metrics.regime_performance(closed)
        best_regime, worst_regime = self._rank_regimes(regime_perf)

        # Confidence threshold analysis
        conf_bands = self.metrics.confidence_band_performance(closed)
        optimal_conf = self._find_optimal_confidence(conf_bands)

        # Streak & consistency
        win_streak, loss_streak = self._streak_analysis(closed)

        # Statistical significance flags
        significance = self._significance_flags(closed)

        # Daily breakdown
        daily = self._daily_breakdown(closed)

        return {
            "week_start": week_start.date().isoformat(),
            "week_end": week_end.date().isoformat(),
            "summary": {
                "total_trades": report["total_trades"],
                "win_rate": report["win_rate"],
                "profit_factor": report["profit_factor"],
                "total_pnl": report["total_pnl"],
                "sharpe_ratio": report["sharpe_ratio"],
                "calmar_ratio": report["calmar_ratio"],
                "max_drawdown_pct": report["max_drawdown"]["max_dd_pct"],
                "expected_value_per_trade": report["expected_value"],
                "kelly_fraction": report["kelly_fraction"],
            },
            "best_setups": best_setups,
            "worst_setups": worst_setups,
            "time_of_day": tod,
            "best_hours": best_hours,
            "worst_hours": worst_hours,
            "regime_performance": regime_perf,
            "best_regime": best_regime,
            "worst_regime": worst_regime,
            "confidence_bands": conf_bands,
            "optimal_confidence_threshold": optimal_conf,
            "streaks": {"best_win_streak": win_streak, "worst_loss_streak": loss_streak},
            "significance": significance,
            "daily_breakdown": daily,
            "condition_win_rates": report["condition_win_rates"],
        }

    # ── Setup ranking ─────────────────────────────────────────────────────

    def _rank_setups(self, trades: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Find which entry-condition combinations produce best/worst results."""
        # Group by "setup signature" = frozenset of conditions
        setup_groups: Dict[str, List] = defaultdict(list)
        for t in trades:
            conds = t.get("entry_conditions", [])
            if not conds:
                conds = ["no_conditions"]
            # Use sorted condition names as signature
            sig = " + ".join(sorted(
                c.split(":")[0].strip()[:20] if ":" in c else c[:20]
                for c in conds
            )[:4])  # max 4 conditions in signature
            setup_groups[sig].append(t)

        setups = []
        for sig, group in setup_groups.items():
            if len(group) < self.MIN_SAMPLE:
                continue
            wins = [t for t in group if t.get("pnl", 0) > 0]
            total_pnl = sum(t.get("pnl", 0) for t in group)
            avg_conf = sum(t.get("confidence", 70) for t in group) / len(group)
            wr = len(wins) / len(group) * 100
            ev = total_pnl / len(group)
            regime_dist = defaultdict(int)
            for t in group:
                regime_dist[t.get("regime", "unknown")] += 1
            most_common_regime = max(regime_dist, key=regime_dist.get)
            setups.append({
                "setup": sig,
                "trades": len(group),
                "win_rate": round(wr, 1),
                "total_pnl": round(total_pnl, 4),
                "expected_value": round(ev, 4),
                "avg_confidence": round(avg_conf, 1),
                "most_common_regime": most_common_regime,
                "score": round(wr * 0.5 + (ev / 0.01) * 0.5, 2),  # composite score
            })

        setups.sort(key=lambda x: x["score"], reverse=True)
        best = setups[:5]
        worst = sorted(setups, key=lambda x: x["score"])[:5]
        return best, worst

    # ── Hour ranking ─────────────────────────────────────────────────────

    def _rank_hours(self, tod: Dict) -> Tuple[List[Dict], List[Dict]]:
        filtered = [
            {"hour": k, **v} for k, v in tod.items() if v["trades"] >= self.MIN_SAMPLE
        ]
        filtered.sort(key=lambda x: x["win_rate"], reverse=True)
        return filtered[:3], list(reversed(filtered))[:3]

    # ── Regime ranking ────────────────────────────────────────────────────

    def _rank_regimes(self, regime_perf: Dict) -> Tuple[Optional[str], Optional[str]]:
        qualified = {k: v for k, v in regime_perf.items() if v["trades"] >= self.MIN_SAMPLE}
        if not qualified:
            return None, None
        best = max(qualified, key=lambda k: qualified[k]["win_rate"])
        worst = min(qualified, key=lambda k: qualified[k]["win_rate"])
        return best, worst

    # ── Optimal confidence ─────────────────────────────────────────────────

    def _find_optimal_confidence(self, conf_bands: Dict) -> Dict[str, Any]:
        """Find the confidence threshold with best expected value."""
        best_band = None
        best_ev = -999
        for band, stats in conf_bands.items():
            if stats["trades"] >= self.MIN_SAMPLE and stats["avg_pnl"] > best_ev:
                best_ev = stats["avg_pnl"]
                best_band = band
        if not best_band:
            return {"band": "70-80%", "note": "insufficient data"}
        lower = int(best_band.split("-")[0].replace("%", "").replace("+", ""))
        return {
            "band": best_band,
            "threshold": lower,
            "avg_pnl": best_ev,
            "note": f"Trades with confidence in the {best_band} band yield the best expected value",
        }

    # ── Streak analysis ────────────────────────────────────────────────────

    def _streak_analysis(self, trades: List[Dict]) -> Tuple[int, int]:
        max_win = cur_win = 0
        max_loss = cur_loss = 0
        for t in trades:
            if t.get("pnl", 0) > 0:
                cur_win += 1; max_win = max(max_win, cur_win); cur_loss = 0
            else:
                cur_loss += 1; max_loss = max(max_loss, cur_loss); cur_win = 0
        return max_win, max_loss

    # ── Statistical significance ───────────────────────────────────────────

    def _significance_flags(self, trades: List[Dict]) -> List[Dict]:
        """Flag patterns that are statistically significant (p < 0.05)."""
        flags = []
        n = len(trades)
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        wr = wins / n if n > 0 else 0.5

        # Test if win rate is significantly different from 50%
        if n >= 10:
            # Binomial z-test vs 50%
            p0 = 0.5
            se = math.sqrt(p0 * (1 - p0) / n)
            z = (wr - p0) / se
            p_val = 2 * (1 - self._norm_cdf(abs(z)))
            if p_val < 0.05:
                flags.append({
                    "finding": f"Win rate {wr*100:.1f}% is statistically significant (p={p_val:.3f})",
                    "z_score": round(z, 3),
                    "p_value": round(p_val, 4),
                    "direction": "positive" if wr > 0.5 else "negative",
                })

        # Regime significance
        regime_stats = self.metrics.regime_performance(trades)
        for regime, stats in regime_stats.items():
            rn = stats["trades"]
            rwr = stats["win_rate"] / 100
            if rn >= 8:
                se = math.sqrt(0.5 * 0.5 / rn)
                z = (rwr - 0.5) / se
                p_val = 2 * (1 - self._norm_cdf(abs(z)))
                if p_val < 0.1:
                    flags.append({
                        "finding": f"Regime '{regime}': {stats['win_rate']}% WR over {rn} trades (p={p_val:.3f})",
                        "regime": regime,
                        "z_score": round(z, 3),
                        "p_value": round(p_val, 4),
                        "direction": "positive" if rwr > 0.5 else "negative",
                    })

        return flags

    # ── Daily breakdown ────────────────────────────────────────────────────

    def _daily_breakdown(self, trades: List[Dict]) -> Dict[str, Dict]:
        day_stats: Dict[str, Dict] = defaultdict(lambda: {
            "trades": 0, "wins": 0, "pnl": 0.0
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
                day = dt.strftime("%A")  # Monday, Tuesday...
            except Exception:
                continue
            day_stats[day]["trades"] += 1
            day_stats[day]["pnl"] += t.get("pnl", 0)
            if t.get("pnl", 0) > 0:
                day_stats[day]["wins"] += 1

        result = {}
        for day, stats in day_stats.items():
            n = stats["trades"]
            result[day] = {
                "trades": n,
                "win_rate": round(stats["wins"] / n * 100, 1) if n > 0 else 0,
                "total_pnl": round(stats["pnl"], 4),
                "avg_pnl": round(stats["pnl"] / n, 4) if n > 0 else 0,
            }
        return result

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _norm_cdf(z: float) -> float:
        """Approximation of normal CDF."""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    @staticmethod
    def _infer_week_start(trades: List[Dict]) -> datetime:
        ts = trades[0].get("timestamp") or trades[0].get("created_at")
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = ts or datetime.now(timezone.utc)
        # Roll back to Monday
        days_back = dt.weekday()
        return (dt - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
