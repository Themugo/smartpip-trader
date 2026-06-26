"""
Strategy Recommender — generates actionable adjustments based on historical journal data.
Uses performance metrics, regime analysis, and condition win rates to produce
prioritised recommendations with evidence-based reasoning.
"""
import logging
from typing import Dict, Any, List, Tuple
from .performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)

PRIORITY_HIGH   = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW    = "LOW"

class StrategyRecommender:
    """Evidence-based strategy recommendations from trade journal history."""

    THRESHOLDS = {
        "min_win_rate":         52.0,   # % — below this, system has no edge
        "min_profit_factor":    1.2,    # gross profit / gross loss
        "max_drawdown_warning": 8.0,    # % — trigger risk reduction
        "max_drawdown_critical": 15.0,  # % — stop trading
        "min_sharpe":           0.5,    # annualised Sharpe
        "min_trades_for_stats": 20,     # minimum sample for reliable stats
        "regime_avoid_wr":      45.0,   # % — avoid regime below this WR
        "optimal_min_conf":     70.0,   # % — min confidence threshold
        "good_hour_wr":         60.0,   # % — prefer hours above this WR
        "bad_hour_wr":          40.0,   # % — avoid hours below this WR
        "kelly_max_stake":      0.25,   # max Kelly fraction to use
    }

    def __init__(self):
        self.metrics = PerformanceMetrics()

    def generate(self, trades: List[Dict], current_settings: Dict = None) -> Dict[str, Any]:
        """Generate full set of prioritised recommendations."""
        closed = [t for t in trades if t.get("pnl") is not None]
        n = len(closed)
        current_settings = current_settings or {}

        if n < 5:
            return {
                "recommendations": [{
                    "priority": PRIORITY_LOW,
                    "category": "data",
                    "title": "Insufficient data",
                    "action": "Complete at least 20 trades before acting on recommendations.",
                    "evidence": f"Only {n} closed trades available.",
                }],
                "confidence": "low",
                "trades_analyzed": n,
            }

        report = self.metrics.full_report(closed)
        recs = []

        # 1. Drawdown alerts
        recs.extend(self._drawdown_recs(report))

        # 2. Win rate / edge assessment
        recs.extend(self._edge_recs(report, n))

        # 3. Confidence threshold adjustment
        recs.extend(self._confidence_recs(report.get("confidence_bands", {}), current_settings))

        # 4. Regime filtering
        recs.extend(self._regime_recs(report.get("regime_performance", {})))

        # 5. Time-of-day filtering
        recs.extend(self._time_recs(report.get("time_of_day", {})))

        # 6. Position sizing (Kelly)
        recs.extend(self._sizing_recs(report, current_settings))

        # 7. Condition-level adjustments
        recs.extend(self._condition_recs(report.get("condition_win_rates", {})))

        # 8. Streak risk management
        recs.extend(self._streak_recs(report.get("consecutive_losses", {})))

        # Sort by priority
        priority_order = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
        recs.sort(key=lambda r: priority_order.get(r["priority"], 9))

        confidence = "high" if n >= 50 else "medium" if n >= 20 else "low"

        return {
            "recommendations": recs,
            "confidence": confidence,
            "trades_analyzed": n,
            "summary": self._executive_summary(report, recs),
            "settings_patch": self._settings_patch(recs, current_settings),
        }

    # ── Recommendation generators ─────────────────────────────────────────

    def _drawdown_recs(self, report: Dict) -> List[Dict]:
        recs = []
        dd = report.get("max_drawdown", {})
        dd_pct = dd.get("max_dd_pct", 0)
        cur_dd = report.get("current_drawdown", 0)

        if cur_dd >= self.THRESHOLDS["max_drawdown_critical"]:
            recs.append({
                "priority": PRIORITY_HIGH,
                "category": "risk",
                "title": "🛑 CRITICAL DRAWDOWN — Stop Trading",
                "action": "Halt live trading immediately. Current drawdown exceeds 15%. "
                          "Return to shadow/demo mode and review all losing trades.",
                "evidence": f"Current drawdown: {cur_dd:.1f}% (critical threshold: 15%)",
                "metric": {"current_dd": cur_dd, "threshold": 15},
            })
        elif cur_dd >= self.THRESHOLDS["max_drawdown_warning"]:
            recs.append({
                "priority": PRIORITY_HIGH,
                "category": "risk",
                "title": "⚠️ HIGH DRAWDOWN — Reduce Position Size",
                "action": "Reduce stake to 50% of current until drawdown recovers below 5%.",
                "evidence": f"Current drawdown: {cur_dd:.1f}% (warning threshold: 8%)",
                "metric": {"current_dd": cur_dd, "threshold": 8},
            })

        if dd_pct >= 10 and cur_dd < 5:
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "risk",
                "title": "Max historical drawdown was high",
                "action": "Tighten your daily stop-loss to prevent recurrence of deep drawdowns.",
                "evidence": f"Max drawdown: {dd_pct:.1f}% reached at some point this period.",
                "metric": {"max_dd": dd_pct},
            })
        return recs

    def _edge_recs(self, report: Dict, n: int) -> List[Dict]:
        recs = []
        wr = report.get("win_rate", 0)
        pf = report.get("profit_factor", 0)
        sharpe = report.get("sharpe_ratio", 0)
        ev = report.get("expected_value", 0)

        if wr < self.THRESHOLDS["min_win_rate"] and n >= 20:
            recs.append({
                "priority": PRIORITY_HIGH,
                "category": "edge",
                "title": "⚠️ Win rate below breakeven — no statistical edge",
                "action": "Tighten entry conditions. Require at least 5/6 conditions to align "
                          "AND confidence ≥75% before firing. Consider pausing live trading.",
                "evidence": f"Win rate: {wr:.1f}% (need >52% for edge). "
                            f"Profit factor: {pf:.2f}. Expected value: ${ev:.4f}/trade.",
                "metric": {"win_rate": wr, "profit_factor": pf},
            })
        elif wr > 60 and pf > 1.5:
            recs.append({
                "priority": PRIORITY_LOW,
                "category": "edge",
                "title": "✅ Strong edge confirmed",
                "action": "System is performing well. Consider scaling up stake by 10-20% "
                          "if drawdown remains controlled.",
                "evidence": f"Win rate: {wr:.1f}%, Profit factor: {pf:.2f}, Sharpe: {sharpe:.2f}",
                "metric": {"win_rate": wr, "profit_factor": pf, "sharpe": sharpe},
            })

        if sharpe < self.THRESHOLDS["min_sharpe"] and n >= 20:
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "edge",
                "title": "Low Sharpe ratio — returns not compensating for risk",
                "action": "Improve signal selectivity: trade only the highest-confidence setups. "
                          "Skip marginal setups where score <75/100.",
                "evidence": f"Sharpe ratio: {sharpe:.2f} (target >0.5 annualised)",
                "metric": {"sharpe": sharpe},
            })
        return recs

    def _confidence_recs(self, bands: Dict, settings: Dict) -> List[Dict]:
        recs = []
        if not bands:
            return recs
        # Find the first band with positive EV
        for label, stats in bands.items():
            if stats["trades"] >= 3 and stats["avg_pnl"] > 0:
                lower = int(label.split("-")[0].replace("%", "").replace("+", ""))
                current_min = settings.get("min_confidence", 70)
                if lower != current_min:
                    priority = PRIORITY_MEDIUM if abs(lower - current_min) > 10 else PRIORITY_LOW
                    recs.append({
                        "priority": priority,
                        "category": "confidence",
                        "title": f"Adjust minimum confidence threshold to {lower}%",
                        "action": f"Set min_confidence={lower} in settings. "
                                  f"Trades in {label} band show positive EV of ${stats['avg_pnl']:.4f}/trade.",
                        "evidence": f"Band {label}: {stats['trades']} trades, "
                                    f"{stats['win_rate']}% WR, avg P&L ${stats['avg_pnl']:.4f}",
                        "metric": {"recommended_threshold": lower, "current": current_min},
                        "settings_key": "min_confidence",
                        "settings_value": lower,
                    })
                break
        return recs

    def _regime_recs(self, regime_perf: Dict) -> List[Dict]:
        recs = []
        for regime, stats in regime_perf.items():
            if stats["trades"] < 3:
                continue
            if stats["win_rate"] < self.THRESHOLDS["regime_avoid_wr"]:
                recs.append({
                    "priority": PRIORITY_MEDIUM,
                    "category": "regime",
                    "title": f"Avoid trading in '{regime}' regime",
                    "action": f"Skip trades when regime detector identifies '{regime}' market. "
                              f"Historical win rate is only {stats['win_rate']}% in this regime.",
                    "evidence": f"'{regime}': {stats['trades']} trades, "
                                f"{stats['win_rate']}% WR, "
                                f"total P&L ${stats['total_pnl']:.2f}",
                    "metric": {"regime": regime, "win_rate": stats["win_rate"]},
                })
            elif stats["win_rate"] > 65:
                recs.append({
                    "priority": PRIORITY_LOW,
                    "category": "regime",
                    "title": f"Prioritise trading in '{regime}' regime",
                    "action": f"Increase shot count or reduce cooldown when '{regime}' regime is detected. "
                              f"Historical win rate: {stats['win_rate']}%.",
                    "evidence": f"'{regime}': {stats['trades']} trades, "
                                f"{stats['win_rate']}% WR, avg P&L ${stats['avg_pnl']:.4f}",
                    "metric": {"regime": regime, "win_rate": stats["win_rate"]},
                })
        return recs

    def _time_recs(self, tod: Dict) -> List[Dict]:
        recs = []
        good_hours, bad_hours = [], []
        for hr, stats in tod.items():
            if stats["trades"] < 3:
                continue
            if stats["win_rate"] >= self.THRESHOLDS["good_hour_wr"]:
                good_hours.append((hr, stats))
            elif stats["win_rate"] <= self.THRESHOLDS["bad_hour_wr"]:
                bad_hours.append((hr, stats))

        if good_hours:
            hours_str = ", ".join(h for h, _ in sorted(good_hours, key=lambda x: x[1]["win_rate"], reverse=True)[:4])
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "timing",
                "title": f"Best trading windows: {hours_str} UTC",
                "action": f"Consider enabling the time filter to restrict trading to these high-performance hours.",
                "evidence": "Hours with ≥60% win rate: " + ", ".join(
                    f"{h}={s['win_rate']}%" for h, s in sorted(good_hours, key=lambda x: x[1]["win_rate"], reverse=True)[:4]
                ),
                "metric": {"best_hours": [h for h, _ in good_hours]},
            })

        if bad_hours:
            hours_str = ", ".join(h for h, _ in sorted(bad_hours, key=lambda x: x[1]["win_rate"])[:4])
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "timing",
                "title": f"Avoid trading at: {hours_str} UTC",
                "action": "Add these hours to the time filter blocklist. Low win rates suggest unfavourable liquidity/volatility.",
                "evidence": "Hours with ≤40% win rate: " + ", ".join(
                    f"{h}={s['win_rate']}%" for h, s in sorted(bad_hours, key=lambda x: x[1]["win_rate"])[:4]
                ),
                "metric": {"bad_hours": [h for h, _ in bad_hours]},
            })
        return recs

    def _sizing_recs(self, report: Dict, settings: Dict) -> List[Dict]:
        recs = []
        kelly = report.get("kelly_fraction", 0)
        current_base = settings.get("base_amount", 1.0)
        # Recommend 25% of Kelly (conservative)
        conservative_kelly = round(kelly * 0.25, 2)
        if kelly > 0 and len([t for t in [] if True]) == 0:  # placeholder check
            pass
        if kelly > 0.05:
            recs.append({
                "priority": PRIORITY_LOW,
                "category": "sizing",
                "title": f"Optimal stake: {conservative_kelly*100:.1f}% of bankroll (¼ Kelly)",
                "action": f"If your bankroll is $1000, optimal stake ≈ ${1000*conservative_kelly:.2f}. "
                          "Using ¼ Kelly reduces volatility vs full Kelly.",
                "evidence": f"Full Kelly: {kelly*100:.1f}% → ¼ Kelly: {conservative_kelly*100:.1f}%",
                "metric": {"full_kelly": kelly, "quarter_kelly": conservative_kelly},
            })
        elif kelly <= 0:
            recs.append({
                "priority": PRIORITY_HIGH,
                "category": "sizing",
                "title": "Kelly criterion suggests no bets",
                "action": "Negative Kelly means the system has no positive edge at current parameters. "
                          "Do not increase stake size. Review entry conditions.",
                "evidence": f"Kelly fraction: {kelly:.4f}",
                "metric": {"kelly": kelly},
            })
        return recs

    def _condition_recs(self, condition_wr: Dict) -> List[Dict]:
        recs = []
        if not condition_wr:
            return recs
        items = list(condition_wr.items())
        # Weakest conditions (≥3 trades, low WR)
        weak = [(c, s) for c, s in items if s["trades"] >= 3 and s["win_rate"] < 45]
        strong = [(c, s) for c, s in items if s["trades"] >= 3 and s["win_rate"] > 65]
        if weak:
            cnames = ", ".join(c for c, _ in weak[:3])
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "conditions",
                "title": f"Weak conditions dragging performance: {cnames}",
                "action": "Consider increasing the threshold for these conditions or removing them from the required set.",
                "evidence": "; ".join(f"{c}: {s['win_rate']}% WR ({s['trades']} trades)" for c, s in weak[:3]),
                "metric": {"weak_conditions": {c: s for c, s in weak[:3]}},
            })
        if strong:
            cnames = ", ".join(c for c, _ in strong[:3])
            recs.append({
                "priority": PRIORITY_LOW,
                "category": "conditions",
                "title": f"High-alpha conditions: {cnames}",
                "action": "These conditions are your strongest predictors. Prioritise setups where all of them align.",
                "evidence": "; ".join(f"{c}: {s['win_rate']}% WR ({s['trades']} trades)" for c, s in strong[:3]),
                "metric": {"strong_conditions": {c: s for c, s in strong[:3]}},
            })
        return recs

    def _streak_recs(self, streak_info: Dict) -> List[Dict]:
        recs = []
        max_cl = streak_info.get("max_consecutive_losses", 0)
        if max_cl >= 4:
            recs.append({
                "priority": PRIORITY_MEDIUM,
                "category": "risk",
                "title": f"Consecutive loss streak of {max_cl} observed",
                "action": f"Implement a {max_cl}-loss kill switch. After {max_cl} consecutive losses, "
                          "pause for 30 minutes and reassess market regime before continuing.",
                "evidence": f"Max consecutive losses this period: {max_cl}",
                "metric": {"max_consecutive_losses": max_cl},
            })
        return recs

    # ── Helpers ────────────────────────────────────────────────────────────

    def _executive_summary(self, report: Dict, recs: List[Dict]) -> str:
        wr = report.get("win_rate", 0)
        pf = report.get("profit_factor", 0)
        pnl = report.get("total_pnl", 0)
        n = report.get("total_trades", 0)
        high_recs = [r for r in recs if r["priority"] == PRIORITY_HIGH]

        if high_recs:
            return (f"⚠️ {len(high_recs)} HIGH-PRIORITY issue(s) require immediate attention. "
                    f"{n} trades analyzed: {wr:.1f}% WR, PF {pf:.2f}, Net P&L ${pnl:.2f}.")
        elif wr >= 55 and pf >= 1.3:
            return (f"✅ System performing well: {wr:.1f}% WR, profit factor {pf:.2f}, "
                    f"net P&L ${pnl:.2f} over {n} trades. {len(recs)} optimisations suggested.")
        else:
            return (f"📊 {n} trades: {wr:.1f}% WR, PF {pf:.2f}, Net ${pnl:.2f}. "
                    f"Review {len(recs)} recommendation(s) to improve performance.")

    def _settings_patch(self, recs: List[Dict], current: Dict) -> Dict:
        """Return a settings dict patch based on recommendations."""
        patch = {}
        for rec in recs:
            if "settings_key" in rec and "settings_value" in rec:
                patch[rec["settings_key"]] = rec["settings_value"]
        return patch
