"""
Explainable AI — human-readable trade decision explanations.

Every trade decision produced by the intelligence layer is passed through
this module to generate a structured ``TradeExplanation`` that captures *why*
the system chose to trade, abstain, or reject.  The explanation aggregates
signals from all upstream components (analyzers, regime detector, entropy,
case-based reasoner, RL agent, digital twin, risk check) and ranks them by
absolute contribution so that the most influential factors appear first.

Explanations are persisted in a local SQLite database for audit, analysis,
and continuous improvement of the system's transparency.
"""

import json
import logging
import os
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.getenv("EXPLANATION_DB_PATH", "explanations.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS explanations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    decision        TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    score           REAL    NOT NULL,
    factors         TEXT    NOT NULL DEFAULT '[]',
    regime_description TEXT NOT NULL DEFAULT '',
    risk_assessment TEXT    NOT NULL DEFAULT '',
    similar_historical_cases INTEGER NOT NULL DEFAULT 0,
    recommendation  TEXT    NOT NULL DEFAULT '',
    timestamp       REAL    NOT NULL,
    raw_data        TEXT    NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_exp_ts       ON explanations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_exp_decision ON explanations(decision);
"""

MAX_HISTORY = 2000


# ── Natural-language templates ───────────────────────────────────────────

_FACTOR_TEMPLATES: Dict[str, Dict[str, str]] = {
    "analyzer_consensus": {
        "high": "Strong consensus among analyzers ({value:.0f}%) — most agree on direction",
        "medium": "Moderate analyzer agreement ({value:.0f}%) — signals are mixed but leaning",
        "low": "Weak analyzer consensus ({value:.0f}%) — analyzers disagree significantly",
    },
    "entropy_score": {
        "high": "Low entropy ({value:.2f}/3.32 bits) indicates a clear non-random pattern",
        "medium": "Moderate entropy ({value:.2f}/3.32 bits) — some structure detected",
        "low": "High entropy ({value:.2f}/3.32 bits) — market appears near-random",
    },
    "volatility_score": {
        "high": "Volatility is in the optimal trading band ({value:.4f} annualised)",
        "medium": "Volatility slightly outside ideal range ({value:.4f} annualised)",
        "low": "Volatility extreme ({value:.4f} annualised) — elevated risk",
    },
    "historical_similarity": {
        "high": "Current conditions closely match profitable historical trades (similarity: {value:.2f})",
        "medium": "Moderate similarity to past trades ({value:.2f}) — some familiar patterns",
        "low": "Low similarity to historical trades ({value:.2f}) — uncharted territory",
    },
    "model_accuracy": {
        "high": "ML ensemble showing strong accuracy ({value:.0f}%)",
        "medium": "ML accuracy is acceptable ({value:.0f}%) but not compelling",
        "low": "ML accuracy is weak ({value:.0f}%) — model confidence low",
    },
    "regime_alignment": {
        "high": "Market regime ({value}) is highly favourable for this trade type",
        "medium": "Market regime ({value}) is neutral for this trade type",
        "low": "Market regime ({value}) is unfavourable for this trade type",
    },
    "time_quality": {
        "high": "Current hour is within peak liquidity window — spreads are tight",
        "medium": "Off-peak trading hour — slightly wider spreads expected",
        "low": "Low-liquidity hour — expect wider spreads and more noise",
    },
    "streak_momentum": {
        "high": "Extended streak detected ({value:.0f}) — reversal opportunity strong",
        "medium": "Moderate streak in progress ({value:.0f}) — potential reversal",
        "low": "No significant streak — no momentum edge",
    },
    "rl_agent": {
        "high": "RL agent strongly recommends TRADE (Q-value: {value:.4f})",
        "medium": "RL agent suggests WAIT (Q-value: {value:.4f})",
        "low": "RL agent recommends ABSTAIN (Q-value: {value:.4f})",
    },
    "digital_twin": {
        "high": "Digital Twin simulation approves — {value:.0f}% simulated win rate",
        "medium": "Digital Twin simulation is inconclusive ({value:.0f}% win rate)",
        "low": "Digital Twin simulation rejects — only {value:.0f}% simulated win rate",
    },
    "case_based_reasoner": {
        "high": "Similar historical cases show {value:.0f}% win rate — strong precedent",
        "medium": "Historical cases show mixed results ({value:.0f}% win rate)",
        "low": "Similar cases show poor outcomes ({value:.0f}% win rate)",
    },
    "risk_check": {
        "high": "All risk checks pass — within all drawdown and loss limits",
        "medium": "Minor risk concerns raised — trade may be reduced",
        "low": "Risk check failed — {value}",
    },
}


# ── Dataclass ────────────────────────────────────────────────────────────

@dataclass
class TradeExplanation:
    """Structured explanation for a single trade decision.

    Attributes:
        decision: ``"TRADE"`` / ``"ABSTAIN"`` / ``"REJECT"``.
        confidence: Overall confidence score in ``[0, 100]``.
        score: Composite opportunity score in ``[0, 100]``.
        factors: Ranked list of contributing factors.  Each factor dict has
            keys ``name`` (str), ``contribution`` (float, -100 to +100),
            ``description`` (str), and ``weight`` (float).
        regime_description: Human-readable summary of the market regime.
        risk_assessment: Human-readable risk status.
        similar_historical_cases: Number of analogous past trades found.
        recommendation: One-line summary recommendation.
        timestamp: Unix epoch time.
        raw_data: Dict of all raw upstream data for full traceability.
    """

    decision: str
    confidence: float
    score: float
    factors: List[Dict[str, Any]]
    regime_description: str
    risk_assessment: str
    similar_historical_cases: int
    recommendation: str
    timestamp: float
    raw_data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "decision": self.decision,
            "confidence": round(self.confidence, 2),
            "score": round(self.score, 2),
            "factors": self.factors,
            "regime_description": self.regime_description,
            "risk_assessment": self.risk_assessment,
            "similar_historical_cases": self.similar_historical_cases,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "raw_data": self.raw_data,
        }


# ── Helper functions ─────────────────────────────────────────────────────

def _tier(value: float, thresholds: tuple = (70.0, 40.0)) -> str:
    """Map a 0-100 value to 'high'/'medium'/'low'."""
    if value >= thresholds[0]:
        return "high"
    elif value >= thresholds[1]:
        return "medium"
    return "low"


def _clamp(value: float, lo: float = -100.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _safe_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Nested dict access with a default."""
    current = d
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


def _describe_regime(regime: Any) -> str:
    """Generate a natural-language regime description."""
    if regime is None:
        return "Market regime is unknown — insufficient data."

    name = getattr(regime, "regime", None) or (regime.get("regime", "UNKNOWN") if isinstance(regime, dict) else "UNKNOWN")
    confidence = getattr(regime, "confidence", None) or (regime.get("confidence", 0.0) if isinstance(regime, dict) else 0.0)

    descriptions = {
        "TRENDING_UP": "Market is trending upward — momentum favours long positions",
        "TRENDING_DOWN": "Market is trending downward — momentum favours short positions",
        "MEAN_REVERTING": "Market is mean-reverting — price tends to bounce around a central level",
        "RANDOM": "Market appears random — no exploitable structure detected",
        "HIGH_VOLATILITY": "High volatility regime — prices swinging widely, risk is elevated",
        "LOW_VOLATILITY": "Low volatility regime — calm market, smaller moves expected",
    }

    base = descriptions.get(name.upper(), f"Market regime: {name}")
    return f"{base} (confidence: {confidence:.2f})"


def _assess_risk(risk_check: Optional[Dict[str, Any]]) -> str:
    """Generate a human-readable risk assessment."""
    if risk_check is None:
        return "No risk data available."

    can_trade = risk_check.get("can_trade", True)
    reason = risk_check.get("reason", "")
    consecutive_losses = risk_check.get("consecutive_losses", 0)
    daily_pnl = risk_check.get("daily_pnl", 0.0)

    if not can_trade:
        return f"Risk check FAILED — {reason}" if reason else "Risk check FAILED — limits exceeded"

    parts = ["Risk check PASSED"]
    if consecutive_losses > 0:
        parts.append(f"{consecutive_losses} consecutive loss(es)")
    if daily_pnl < 0:
        parts.append(f"Daily P&L: {daily_pnl:+.2f}")
    return " — ".join(parts)


def _format_factor_description(name: str, value: float, raw_value: float = 0.0) -> str:
    """Look up a natural-language template for a factor."""
    templates = _FACTOR_TEMPLATES.get(name)
    if templates:
        tier = _tier(abs(raw_value) * 100 if abs(raw_value) <= 1.0 else abs(raw_value))
        template = templates.get(tier, templates["medium"])
        try:
            return template.format(value=raw_value)
        except (KeyError, IndexError):
            pass
    return f"{name}: contribution {value:+.2f}"


# ── SQLite persistence ──────────────────────────────────────────────────

class _ExplanationStore:
    """SQLite-backed storage for trade explanations."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save(self, explanation: TradeExplanation) -> None:
        try:
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS explanations (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        decision        TEXT    NOT NULL,
                        confidence      REAL    NOT NULL,
                        score           REAL    NOT NULL,
                        factors         TEXT    NOT NULL DEFAULT '[]',
                        regime_description TEXT NOT NULL DEFAULT '',
                        risk_assessment TEXT    NOT NULL DEFAULT '',
                        similar_historical_cases INTEGER NOT NULL DEFAULT 0,
                        recommendation  TEXT    NOT NULL DEFAULT '',
                        timestamp       REAL    NOT NULL,
                        raw_data        TEXT    NOT NULL DEFAULT '{}'
                    )
                """)
                conn.execute(
                    """INSERT INTO explanations
                       (decision, confidence, score, factors, regime_description,
                        risk_assessment, similar_historical_cases, recommendation,
                        timestamp, raw_data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        explanation.decision,
                        explanation.confidence,
                        explanation.score,
                        json.dumps(explanation.factors, default=str),
                        explanation.regime_description,
                        explanation.risk_assessment,
                        explanation.similar_historical_cases,
                        explanation.recommendation,
                        explanation.timestamp,
                        json.dumps(explanation.raw_data, default=str),
                    ),
                )
        except Exception as exc:
            logger.error("Failed to save explanation: %s", exc, exc_info=True)

    def get_recent(self, n: int = 50) -> List[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM explanations ORDER BY timestamp DESC LIMIT ?", (n,)
                ).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                d["factors"] = json.loads(d.get("factors") or "[]")
                d["raw_data"] = json.loads(d.get("raw_data") or "{}")
                results.append(d)
            return results
        except Exception as exc:
            logger.error("Failed to fetch explanations: %s", exc, exc_info=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM explanations").fetchone()[0]
                decisions = conn.execute(
                    "SELECT decision, COUNT(*) as cnt FROM explanations GROUP BY decision"
                ).fetchall()
                scores = conn.execute(
                    "SELECT score FROM explanations"
                ).fetchall()

            decision_dist = {row["decision"]: row["cnt"] for row in decisions}
            all_scores = [row["score"] for row in scores]

            stats: Dict[str, Any] = {
                "total_explanations": total,
                "decision_distribution": decision_dist,
                "acceptance_rate": round(
                    decision_dist.get("TRADE", 0) / total * 100, 1
                ) if total > 0 else 0.0,
                "rejection_rate": round(
                    (decision_dist.get("ABSTAIN", 0) + decision_dist.get("REJECT", 0)) / total * 100, 1
                ) if total > 0 else 0.0,
            }

            if all_scores:
                arr = np.array(all_scores)
                stats["avg_score"] = round(float(arr.mean()), 2)
                stats["median_score"] = round(float(np.median(arr)), 2)
                stats["score_std"] = round(float(arr.std()), 2)

            return stats
        except Exception as exc:
            logger.error("Failed to compute explanation stats: %s", exc, exc_info=True)
            return {}

    def get_rejection_reasons(self, n: int = 100) -> List[str]:
        """Return the most recent rejection reasons."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT recommendation FROM explanations
                       WHERE decision IN ('ABSTAIN', 'REJECT')
                       ORDER BY timestamp DESC LIMIT ?""",
                    (n,),
                ).fetchall()
            return [row["recommendation"] for row in rows if row["recommendation"]]
        except Exception as exc:
            logger.error("Failed to fetch rejection reasons: %s", exc, exc_info=True)
            return []

    def export(self, path: str, days: int = 30) -> int:
        try:
            cutoff = time.time() - (days * 86400)
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM explanations WHERE timestamp > ? ORDER BY timestamp DESC",
                    (cutoff,),
                ).fetchall()
            data = []
            for row in rows:
                d = dict(row)
                d["factors"] = json.loads(d.get("factors") or "[]")
                d["raw_data"] = json.loads(d.get("raw_data") or "{}")
                data.append(d)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("Exported %d explanations to %s (last %d days)", len(data), path, days)
            return len(data)
        except Exception as exc:
            logger.error("Export failed: %s", exc, exc_info=True)
            return 0


# ── ExplainableAI ────────────────────────────────────────────────────────

class ExplainableAI:
    """Generates human-readable explanations for every trade decision.

    Collects outputs from all intelligence-layer components, ranks factors
    by absolute contribution, and produces a ``TradeExplanation`` that
    tells the operator *why* the system decided what it decided.

    Usage::

        xai = ExplainableAI()
        explanation = xai.explain_trade_decision(
            analyzer_output={...},
            opportunity_score=score_obj,
            regime=regime_obj,
            trade_memory_stats={...},
            case_reasoner_output={...},
            rl_action=action_obj,
            digital_twin_result=twin_obj,
            risk_check={...},
        )
        print(xai.generate_trade_report(explanation))
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._store = _ExplanationStore(db_path)
        self._history: List[TradeExplanation] = []
        self._decision_counts: Dict[str, int] = {"TRADE": 0, "ABSTAIN": 0, "REJECT": 0}
        self._total_scores: List[float] = []
        self._rejection_reasons_counter: Counter = Counter()
        logger.info("ExplainableAI initialised (db=%s)", db_path)

    # ── Main explanation pipeline ────────────────────────────────────────

    def explain_trade_decision(
        self,
        analyzer_output: Dict[str, Any],
        opportunity_score: Any,
        regime: Any,
        trade_memory_stats: Dict[str, Any],
        case_reasoner_output: Dict[str, Any],
        rl_action: Any,
        digital_twin_result: Any,
        risk_check: Dict[str, Any],
    ) -> TradeExplanation:
        """Build a complete explanation from all intelligence-layer outputs.

        Parameters
        ----------
        analyzer_output : dict
            Raw analyzer predictions keyed by analyzer name.  Each value
            should have ``"direction"`` and ``"confidence"`` keys.
        opportunity_score : OpportunityScore
            Composite opportunity scoring result.
        regime : MarketRegime
            Current regime classification.
        trade_memory_stats : dict
            Summary statistics from ``TradeMemory.get_stats()``.
        case_reasoner_output : dict
            Output from ``CaseBasedReasoner.evaluate()``.
        rl_action : RLAction
            Action chosen by the reinforcement-learning agent.
        digital_twin_result : TwinResult
            Outcome of the Digital-Twin simulation.
        risk_check : dict
            Dict with ``"can_trade"`` (bool), ``"reason"`` (str), and
            any additional risk-limit fields.

        Returns
        -------
        TradeExplanation
            A fully populated explanation with ranked factors and summary.
        """
        try:
            factors: List[Dict[str, Any]] = []
            raw_data: Dict[str, Any] = {
                "analyzer_output": analyzer_output,
                "trade_memory_stats": trade_memory_stats,
                "case_reasoner_output": case_reasoner_output,
                "risk_check": risk_check,
            }

            # ── 1. Analyzer consensus factor ─────────────────────────────
            consensus_value = self._extract_analyzer_consensus(analyzer_output)
            factors.append(self.explain_factor(
                "analyzer_consensus",
                consensus_value,
                {"weight": 0.20},
            ))

            # ── 2. Opportunity score components ───────────────────────────
            opp_components = {}
            if opportunity_score is not None:
                opp_components = getattr(opportunity_score, "components", {})
                if isinstance(opportunity_score, dict):
                    opp_components = opportunity_score.get("components", {})

            for comp_name, comp_value in opp_components.items():
                if comp_name not in ("analyzer_consensus",):
                    weight = 0.10
                    if opportunity_score is not None:
                        weights = getattr(opportunity_score, "_weights", {})
                        if isinstance(opportunity_score, dict):
                            weights = opportunity_score.get("_weights", {})
                        weight = weights.get(comp_name, 0.10)
                    factors.append(self.explain_factor(comp_name, comp_value, {"weight": weight}))

            # ── 3. Regime factor ──────────────────────────────────────────
            regime_confidence = 0.0
            regime_name = "UNKNOWN"
            if regime is not None:
                regime_confidence = getattr(regime, "confidence", 0.0)
                regime_name = getattr(regime, "regime", "UNKNOWN")
                if isinstance(regime, dict):
                    regime_confidence = regime.get("confidence", 0.0)
                    regime_name = regime.get("regime", "UNKNOWN")
            regime_score = regime_confidence * 100.0
            factors.append(self.explain_factor("regime_alignment", regime_score, {"weight": 0.10}))
            raw_data["regime_name"] = regime_name
            raw_data["regime_confidence"] = regime_confidence

            # ── 4. Case-based reasoner factor ─────────────────────────────
            cbr_win_rate = 0.0
            cbr_recommendation = case_reasoner_output.get("recommendation", "NEUTRAL")
            cbr_modifier = case_reasoner_output.get("confidence_modifier", 0.0)
            cbr_win_rate = case_reasoner_output.get("win_rate_in_similar", 0.0) * 100.0
            factors.append(self.explain_factor("case_based_reasoner", cbr_win_rate, {"weight": 0.15}))
            raw_data["cbr_win_rate"] = cbr_win_rate
            raw_data["cbr_recommendation"] = cbr_recommendation

            # ── 5. RL agent factor ────────────────────────────────────────
            rl_confidence = 0.0
            rl_action_name = "ABSTAIN"
            rl_q_trade = 0.0
            if rl_action is not None:
                rl_confidence = getattr(rl_action, "confidence", 0.0) * 100.0
                rl_action_name = getattr(rl_action, "action", "ABSTAIN")
                q_vals = getattr(rl_action, "q_values", {})
                if isinstance(rl_action, dict):
                    rl_confidence = rl_action.get("confidence", 0.0) * 100.0
                    rl_action_name = rl_action.get("action", "ABSTAIN")
                    q_vals = rl_action.get("q_values", {})
                rl_q_trade = q_vals.get("TRADE", 0.0) if isinstance(q_vals, dict) else 0.0
            rl_score = rl_confidence if rl_action_name == "TRADE" else -rl_confidence
            factors.append(self.explain_factor("rl_agent", rl_score, {"weight": 0.10}))
            raw_data["rl_action"] = rl_action_name
            raw_data["rl_confidence"] = rl_confidence
            raw_data["rl_q_trade"] = rl_q_trade

            # ── 6. Digital twin factor ────────────────────────────────────
            twin_approved = False
            twin_win_rate = 0.0
            if digital_twin_result is not None:
                twin_approved = getattr(digital_twin_result, "approved", False)
                twin_win_rate = getattr(digital_twin_result, "simulated_win_rate", 0.0) * 100.0
                if isinstance(digital_twin_result, dict):
                    twin_approved = digital_twin_result.get("approved", False)
                    twin_win_rate = digital_twin_result.get("simulated_win_rate", 0.0) * 100.0
            twin_score = twin_win_rate if twin_approved else -twin_win_rate
            factors.append(self.explain_factor("digital_twin", twin_score, {"weight": 0.15}))
            raw_data["twin_approved"] = twin_approved
            raw_data["twin_win_rate"] = twin_win_rate

            # ── 7. Risk check factor ──────────────────────────────────────
            risk_passed = risk_check.get("can_trade", True)
            risk_reason = risk_check.get("reason", "")
            risk_score = 80.0 if risk_passed else -50.0
            factors.append(self.explain_factor("risk_check", risk_score, {"weight": 0.15}))
            raw_data["risk_passed"] = risk_passed
            raw_data["risk_reason"] = risk_reason

            # ── Rank factors by absolute contribution ─────────────────────
            factors.sort(key=lambda f: abs(f["contribution"]), reverse=True)

            # ── Compute aggregate confidence and score ────────────────────
            # Contributions are already weighted (contribution = value * weight).
            # We sum them and normalise by the total weight to get a 0-100 score.
            contributions = [f["contribution"] for f in factors]
            weights = [f["weight"] for f in factors]
            total_weight = sum(weights) if weights else 1.0

            # weighted_sum is in range [-total_weight * 100, +total_weight * 100]
            # but contributions are clamped to [-100, +100] so typical range is
            # [-total_weight * 100, +total_weight * 100].
            raw_sum = sum(contributions)
            overall_score = (raw_sum / total_weight + 100.0) / 2.0
            overall_score = float(np.clip(overall_score, 0.0, 100.0))

            # Confidence is the weighted average of component confidences
            confidence = overall_score  # direct mapping for now

            # ── Count similar historical cases ────────────────────────────
            similar_cases = trade_memory_stats.get("total_trades", 0)
            if isinstance(case_reasoner_output, dict):
                # Try to get case count from the reasoner
                similar_cases = case_reasoner_output.get("similar_cases_count", similar_cases)

            # ── Determine final decision ──────────────────────────────────
            decision, recommendation = self._determine_decision(
                overall_score,
                consensus_value,
                regime_name,
                regime_confidence,
                twin_approved,
                twin_win_rate,
                risk_passed,
                risk_reason,
                cbr_win_rate,
                rl_action_name,
            )

            # ── Build descriptions ────────────────────────────────────────
            regime_description = _describe_regime(regime)
            risk_assessment = _assess_risk(risk_check)

            # ── Build the explanation ─────────────────────────────────────
            explanation = TradeExplanation(
                decision=decision,
                confidence=round(confidence, 2),
                score=round(overall_score, 2),
                factors=factors,
                regime_description=regime_description,
                risk_assessment=risk_assessment,
                similar_historical_cases=similar_cases,
                recommendation=recommendation,
                timestamp=time.time(),
                raw_data=raw_data,
            )

            # ── Persist and track ─────────────────────────────────────────
            self._history.append(explanation)
            if len(self._history) > MAX_HISTORY:
                self._history = self._history[-MAX_HISTORY:]
            self._decision_counts[decision] = self._decision_counts.get(decision, 0) + 1
            self._total_scores.append(overall_score)
            if decision in ("ABSTAIN", "REJECT"):
                self._rejection_reasons_counter[recommendation] += 1
            self._store.save(explanation)

            logger.info(
                "Explanation: %s (score=%.1f, conf=%.1f) — %s",
                decision, overall_score, confidence, recommendation[:80],
            )
            return explanation

        except Exception as exc:
            logger.error("Explanation generation failed: %s", exc, exc_info=True)
            return TradeExplanation(
                decision="ABSTAIN",
                confidence=0.0,
                score=0.0,
                factors=[],
                regime_description="Error generating explanation",
                risk_assessment=str(exc),
                similar_historical_cases=0,
                recommendation=f"Explanation error: {exc}",
                timestamp=time.time(),
                raw_data={"error": str(exc)},
            )

    # ── Factor explanation ────────────────────────────────────────────────

    def explain_factor(
        self,
        name: str,
        value: float,
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate a structured explanation for a single factor.

        Parameters
        ----------
        name : str
            Factor identifier (e.g. ``"analyzer_consensus"``).
        value : float
            Raw factor value (typically 0-100 scale).
        weights : dict
            Must contain ``"weight"`` key with the factor's weight in the
            overall score.

        Returns
        -------
        dict
            Keys: ``name``, ``contribution``, ``description``, ``weight``.
        """
        weight = weights.get("weight", 0.10)

        # Contribution is the weighted impact on the final score
        contribution = _clamp(value * weight, -100.0, 100.0)

        # Description via natural-language templates
        description = _format_factor_description(name, contribution, value)

        return {
            "name": name,
            "contribution": round(contribution, 4),
            "description": description,
            "weight": round(weight, 4),
        }

    # ── Formatted report ──────────────────────────────────────────────────

    def generate_trade_report(self, explanation: TradeExplanation) -> str:
        """Generate a formatted human-readable text report.

        Parameters
        ----------
        explanation : TradeExplanation
            The explanation to format.

        Returns
        -------
        str
            Multi-line text report.
        """
        lines: List[str] = []
        ts = datetime.fromtimestamp(explanation.timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        lines.append("=" * 72)
        lines.append(f"  TRADE DECISION REPORT — {ts}")
        lines.append("=" * 72)
        lines.append("")

        # Decision header
        decision_symbol = {
            "TRADE": "[TRADE]",
            "ABSTAIN": "[ABSTAIN]",
            "REJECT": "[REJECT]",
        }.get(explanation.decision, "[???]")
        lines.append(f"  Decision:  {decision_symbol}")
        lines.append(f"  Score:     {explanation.score:.1f} / 100")
        lines.append(f"  Confidence:{explanation.confidence:.1f}%")
        lines.append("")

        # Top factors
        lines.append("  TOP CONTRIBUTING FACTORS:")
        lines.append("  " + "-" * 50)
        for i, factor in enumerate(explanation.factors[:8], 1):
            sign = "+" if factor["contribution"] >= 0 else ""
            lines.append(
                f"  {i:2d}. {factor['name']:<25s} {sign}{factor['contribution']:+.2f}  "
                f"(w={factor['weight']:.2f})"
            )
            lines.append(f"      {factor['description']}")
        lines.append("")

        # Regime
        lines.append(f"  REGIME: {explanation.regime_description}")
        lines.append("")

        # Risk
        lines.append(f"  RISK:   {explanation.risk_assessment}")
        lines.append("")

        # Historical context
        lines.append(
            f"  HISTORICAL CONTEXT: {explanation.similar_historical_cases} similar past cases"
        )
        lines.append("")

        # Recommendation
        lines.append(f"  RECOMMENDATION: {explanation.recommendation}")
        lines.append("")
        lines.append("=" * 72)

        return "\n".join(lines)

    # ── History and stats ─────────────────────────────────────────────────

    def get_explanation_history(self, n: int = 50) -> List[TradeExplanation]:
        """Return the most recent *n* explanations (in-memory, newest first)."""
        return list(reversed(self._history[-n:]))

    def get_decision_stats(self) -> Dict[str, Any]:
        """Aggregate statistics over all explanations generated in this session.

        Returns
        -------
        dict
            Keys: ``total_explanations``, ``acceptance_rate``, ``rejection_rate``,
            ``avg_score``, ``common_rejection_reasons``, ``decision_distribution``.
        """
        total = sum(self._decision_counts.values())
        trade_count = self._decision_counts.get("TRADE", 0)
        abstain_count = self._decision_counts.get("ABSTAIN", 0)
        reject_count = self._decision_counts.get("REJECT", 0)

        stats: Dict[str, Any] = {
            "total_explanations": total,
            "decision_distribution": dict(self._decision_counts),
            "acceptance_rate": round(trade_count / total * 100, 1) if total > 0 else 0.0,
            "rejection_rate": round(
                (abstain_count + reject_count) / total * 100, 1
            ) if total > 0 else 0.0,
        }

        if self._total_scores:
            arr = np.array(self._total_scores)
            stats["avg_score"] = round(float(arr.mean()), 2)
            stats["median_score"] = round(float(np.median(arr)), 2)
            stats["score_std"] = round(float(arr.std()), 2)
        else:
            stats["avg_score"] = 0.0

        # Common rejection reasons
        common = self._rejection_reasons_counter.most_common(5)
        stats["common_rejection_reasons"] = [
            {"reason": reason, "count": count} for reason, count in common
        ]

        return stats

    def get_persistent_stats(self) -> Dict[str, Any]:
        """Load stats from the SQLite store (cross-session)."""
        return self._store.get_stats()

    def export_explanations(self, path: str, days: int = 30) -> int:
        """Export recent explanations to a JSON file.

        Parameters
        ----------
        path : str
            Output file path.
        days : int
            Number of days of history to export.

        Returns
        -------
        int
            Number of explanations exported.
        """
        return self._store.export(path, days)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_analyzer_consensus(analyzer_output: Dict[str, Any]) -> float:
        """Compute a 0-100 consensus score from raw analyzer outputs."""
        if not analyzer_output:
            return 30.0

        directions: List[str] = []
        confidences: List[float] = []

        for name, info in analyzer_output.items():
            if isinstance(info, dict):
                d = info.get("direction", info.get("prediction", ""))
                c = float(info.get("confidence", 50.0))
                if d:
                    directions.append(d.upper())
                    confidences.append(c)

        if not directions:
            return 30.0

        counts = Counter(directions)
        most_common_count = counts.most_common(1)[0][1]
        consensus_ratio = most_common_count / len(directions)
        avg_conf = np.mean(confidences) / 100.0

        score = (consensus_ratio ** 1.5) * 60.0 + avg_conf * 40.0
        return float(np.clip(score, 0.0, 100.0))

    @staticmethod
    def _determine_decision(
        overall_score: float,
        consensus: float,
        regime_name: str,
        regime_confidence: float,
        twin_approved: bool,
        twin_win_rate: float,
        risk_passed: bool,
        risk_reason: str,
        cbr_win_rate: float,
        rl_action_name: str,
    ) -> tuple:
        """Determine the final decision and build the recommendation string.

        Returns (decision, recommendation) tuple.
        """
        # Hard reject: risk check failed
        if not risk_passed:
            reason = risk_reason if risk_reason else "risk limits exceeded"
            return "REJECT", f"REJECT: Risk check failed — {reason}"

        # Soft abstain: score too low
        if overall_score < 40.0:
            return "ABSTAIN", (
                f"ABSTAIN: Score too low ({overall_score:.1f}/100). "
                f"Consensus={consensus:.0f}%, regime={regime_name}"
            )

        # Abstain on random markets unless twin strongly approves
        if regime_name.upper() == "RANDOM" and regime_confidence > 0.5:
            if not twin_approved or twin_win_rate < 55.0:
                return "ABSTAIN", (
                    f"ABSTAIN: Market is RANDOM (entropy/confidence: {regime_confidence:.2f}). "
                    f"Digital Twin win rate only {twin_win_rate:.0f}% in simulation"
                )

        # Abstain on low consensus
        if consensus < 40.0 and overall_score < 60.0:
            return "ABSTAIN", (
                f"ABSTAIN: Low consensus ({consensus:.0f}%), "
                f"market is {regime_name} (entropy: {regime_confidence:.2f})"
            )

        # Trade: sufficient score and favourable conditions
        if overall_score >= 60.0:
            consensus_n = int(round(consensus / 10.0))  # approximate number of analyzers
            total_analyzers = max(consensus_n, 1)
            parts = [
                f"TRADE recommended: Score {overall_score:.1f}/100",
            ]
            if consensus_n > 0:
                parts.append(
                    f"Consensus {consensus:.0f}% across ~{consensus_n} analyzers"
                )
            parts.append(f"Regime: {regime_name} (confidence: {regime_confidence:.2f})")
            if twin_approved:
                parts.append(f"Digital Twin approves ({twin_win_rate:.0f}% win rate)")
            else:
                parts.append(f"Digital Twin inconclusive ({twin_win_rate:.0f}% win rate)")
            if rl_action_name == "TRADE":
                parts.append("RL agent recommends TRADE")
            if cbr_win_rate > 50.0:
                parts.append(f"Historical precedent: {cbr_win_rate:.0f}% win rate")
            return "TRADE", ", ".join(parts)

        # Default: abstain
        return "ABSTAIN", (
            f"ABSTAIN: Score {overall_score:.1f} below trade threshold. "
            f"Consensus={consensus:.0f}%, regime={regime_name}"
        )
