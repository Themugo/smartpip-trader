"""
Explainable Decision Engine — structured, machine-readable decision explanations
with confidence decomposition and audit-trail tracing.

Upgraded successor to ExplainableAI that produces:
  - Step-by-step decision path tracing (like a decision tree audit trail).
  - Confidence decomposition into component contributions with attribution.
  - Factor importance tracking over time.
  - Human-readable trade reports.
  - SQLite persistence and JSON export for all explanations.

All outputs are serialisable dataclasses with ``to_dict()`` methods so they
can be consumed by dashboards, APIs, or further ML pipelines.
"""

import json
import logging
import os
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.getenv("EXPLANATION_ENGINE_DB_PATH", "explanation_engine.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS explanations (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    decision                    TEXT    NOT NULL,
    confidence                  REAL    NOT NULL,
    score                       REAL    NOT NULL,
    factors                     TEXT    NOT NULL DEFAULT '[]',
    regime_description          TEXT    NOT NULL DEFAULT '',
    risk_assessment             TEXT    NOT NULL DEFAULT '',
    similar_historical_cases    INTEGER NOT NULL DEFAULT 0,
    recommendation              TEXT    NOT NULL DEFAULT '',
    timestamp                   REAL    NOT NULL,
    raw_data                    TEXT    NOT NULL DEFAULT '{}',
    confidence_decomposition    TEXT    NOT NULL DEFAULT '{}',
    decision_path               TEXT    NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_ee_ts       ON explanations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ee_decision ON explanations(decision);
"""

MAX_HISTORY = 3000
_MIN_COMPONENT_WEIGHT = 0.01


# ── Dataclasses ──────────────────────────────────────────────────────────

@dataclass
class DecisionStep:
    """Single step in a decision-path audit trail.

    Attributes:
        step_name:  Identifier for the decision gate (e.g. ``"risk_check"``).
        input_value: Value that entered this step.
        threshold: Threshold that was compared against.
        passed: Whether the step passed its gate.
        contribution: Numeric contribution of this step to the final score.
        explanation: Human-readable explanation of what happened at this step.
    """

    step_name: str
    input_value: Any
    threshold: Any
    passed: bool
    contribution: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "input_value": self.input_value,
            "threshold": self.threshold,
            "passed": self.passed,
            "contribution": round(self.contribution, 4),
            "explanation": self.explanation,
        }


@dataclass
class StructuredExplanation:
    """Full machine-readable explanation for a trade decision.

    Attributes:
        decision: ``"TRADE"`` / ``"ABSTAIN"`` / ``"REJECT"``.
        confidence: Overall confidence score in ``[0, 100]``.
        score: Composite opportunity score in ``[0, 100]``.
        factors: Ranked list of contributing factors.
        regime_description: Human-readable summary of the market regime.
        risk_assessment: Human-readable risk status.
        similar_historical_cases: Number of analogous past trades found.
        recommendation: One-line summary recommendation.
        timestamp: Unix epoch time.
        raw_data: Dict of all raw upstream data for full traceability.
        confidence_decomposition: Dict mapping component names to their
            individual contribution toward the final confidence value.
        decision_path: Ordered list of ``DecisionStep`` dicts forming the
            step-by-step audit trail.
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
    confidence_decomposition: Dict[str, float]
    decision_path: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
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
            "confidence_decomposition": self.confidence_decomposition,
            "decision_path": self.decision_path,
        }


# ── Helpers ──────────────────────────────────────────────────────────────

def _tier(value: float, thresholds: tuple = (70.0, 40.0)) -> str:
    if value >= thresholds[0]:
        return "high"
    elif value >= thresholds[1]:
        return "medium"
    return "low"


def _clamp(value: float, lo: float = -100.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _describe_regime(regime: Any) -> str:
    if regime is None:
        return "Market regime is unknown — insufficient data."
    name = _safe_attr(regime, "regime", "UNKNOWN")
    confidence = _safe_attr(regime, "confidence", 0.0)
    descriptions = {
        "TRENDING_UP": "Market is trending upward — momentum favours long positions",
        "TRENDING_DOWN": "Market is trending downward — momentum favours short positions",
        "MEAN_REVERTING": "Market is mean-reverting — price tends to bounce around a central level",
        "RANDOM": "Market appears random — no exploitable structure detected",
        "HIGH_VOLATILITY": "High volatility regime — prices swinging widely, risk is elevated",
        "LOW_VOLATILITY": "Low volatility regime — calm market, smaller moves expected",
    }
    base = descriptions.get(str(name).upper(), f"Market regime: {name}")
    return f"{base} (confidence: {confidence:.2f})"


def _assess_risk(risk_check: Optional[Dict[str, Any]]) -> str:
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
    "bayesian_confidence": {
        "high": "Bayesian posterior shows high confidence ({value:.2f}) — strong evidence",
        "medium": "Bayesian confidence is moderate ({value:.2f}) — some uncertainty remains",
        "low": "Bayesian confidence is low ({value:.2f}) — high uncertainty",
    },
    "abstention_signal": {
        "high": "Abstention module strongly recommends staying out",
        "medium": "Abstention module suggests caution",
        "low": "Abstention module does not flag concerns",
    },
    "ensemble_direction": {
        "high": "Ensemble consensus direction is strong ({value:.0f}% agreement)",
        "medium": "Ensemble direction is moderate ({value:.0f}% agreement)",
        "low": "Ensemble direction is weak ({value:.0f}% agreement)",
    },
}


def _format_factor_description(name: str, contribution: float, raw_value: float = 0.0) -> str:
    templates = _FACTOR_TEMPLATES.get(name)
    if templates:
        tier = _tier(abs(raw_value) * 100 if abs(raw_value) <= 1.0 else abs(raw_value))
        template = templates.get(tier, templates["medium"])
        try:
            return template.format(value=raw_value)
        except (KeyError, IndexError):
            pass
    return f"{name}: contribution {contribution:+.2f}"


# ── SQLite persistence ──────────────────────────────────────────────────

class _ExplanationStore:
    """SQLite-backed storage for structured explanations."""

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

    def save(self, explanation: StructuredExplanation) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO explanations
                       (decision, confidence, score, factors, regime_description,
                        risk_assessment, similar_historical_cases, recommendation,
                        timestamp, raw_data, confidence_decomposition, decision_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        json.dumps(explanation.confidence_decomposition, default=str),
                        json.dumps(explanation.decision_path, default=str),
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
                for key in ("factors", "raw_data", "confidence_decomposition", "decision_path"):
                    d[key] = json.loads(d.get(key) or ("[]" if key in ("factors", "decision_path") else "{}"))
                results.append(d)
            return results
        except Exception as exc:
            logger.error("Failed to fetch explanations: %s", exc, exc_info=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                total = conn.execute("SELECT COUNT(*) FROM explanations").fetchone()[0]
                rows = conn.execute(
                    "SELECT decision, confidence, score FROM explanations"
                ).fetchall()
            if total == 0:
                return {"total_explanations": 0}
            decisions: Counter = Counter()
            confs: List[float] = []
            scores: List[float] = []
            for r in rows:
                decisions[r["decision"]] += 1
                confs.append(r["confidence"])
                scores.append(r["score"])
            conf_arr = np.array(confs)
            score_arr = np.array(scores)
            return {
                "total_explanations": total,
                "decision_distribution": dict(decisions),
                "acceptance_rate": round(decisions.get("TRADE", 0) / total * 100, 1),
                "avg_confidence": round(float(conf_arr.mean()), 2),
                "avg_score": round(float(score_arr.mean()), 2),
                "score_std": round(float(score_arr.std()), 2),
            }
        except Exception as exc:
            logger.error("Failed to compute stats: %s", exc, exc_info=True)
            return {}

    def get_factor_importance(self, n: int = 500) -> Dict[str, float]:
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT factors FROM explanations ORDER BY timestamp DESC LIMIT ?", (n,)
                ).fetchall()
            accum: Dict[str, List[float]] = defaultdict(list)
            for row in rows:
                factors = json.loads(row["factors"] or "[]")
                for f in factors:
                    accum[f["name"]].append(abs(f.get("contribution", 0.0)))
            return {
                name: round(float(np.mean(vals)), 4)
                for name, vals in sorted(accum.items(), key=lambda kv: -np.mean(kv[1]))
            }
        except Exception as exc:
            logger.error("Failed to compute factor importance: %s", exc, exc_info=True)
            return {}

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
                for key in ("factors", "raw_data", "confidence_decomposition", "decision_path"):
                    d[key] = json.loads(d.get(key) or ("[]" if key in ("factors", "decision_path") else "{}"))
                data.append(d)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info("Exported %d explanations to %s (last %d days)", len(data), path, days)
            return len(data)
        except Exception as exc:
            logger.error("Export failed: %s", exc, exc_info=True)
            return 0


# ── ExplainableEngine ────────────────────────────────────────────────────

class ExplainableEngine:
    """Structured, machine-readable decision explanations with confidence
    decomposition and audit-trail tracing.

    Usage::

        engine = ExplainableEngine(db_path="intelligence_data/explanation_engine.db")
        explanation = engine.explain(
            analyzer_output={...},
            opportunity_score=score_obj,
            regime=regime_obj,
            trade_memory_stats={...},
            case_reasoner_output={...},
            rl_action=action_obj,
            digital_twin_result=twin_obj,
            risk_check={...},
            bayesian_verdict=bayesian_obj,
            abstention_verdict=abstain_obj,
            ensemble_verdict=ensemble_obj,
        )
        print(engine.generate_trade_report(explanation))
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._store = _ExplanationStore(db_path)
        self._history: List[StructuredExplanation] = []
        self._decision_counts: Dict[str, int] = {"TRADE": 0, "ABSTAIN": 0, "REJECT": 0}
        self._total_scores: List[float] = []
        self._total_confidences: List[float] = []
        self._rejection_reasons_counter: Counter = Counter()
        self._factor_accumulator: Dict[str, List[float]] = defaultdict(list)
        logger.info("ExplainableEngine initialised (db=%s)", db_path)

    # ── Main explanation pipeline ────────────────────────────────────────

    def explain(
        self,
        analyzer_output: Dict[str, Any],
        opportunity_score: Any,
        regime: Any,
        trade_memory_stats: Dict[str, Any],
        case_reasoner_output: Dict[str, Any],
        rl_action: Any,
        digital_twin_result: Any,
        risk_check: Dict[str, Any],
        bayesian_verdict: Any = None,
        abstention_verdict: Any = None,
        ensemble_verdict: Any = None,
    ) -> StructuredExplanation:
        """Build a complete structured explanation from all intelligence-layer outputs.

        Parameters
        ----------
        analyzer_output : dict
            Raw analyzer predictions keyed by analyzer name.
        opportunity_score : OpportunityScore | dict
            Composite opportunity scoring result.
        regime : MarketRegime | dict
            Current regime classification.
        trade_memory_stats : dict
            Summary statistics from ``TradeMemory.get_stats()``.
        case_reasoner_output : dict
            Output from ``CaseBasedReasoner.evaluate()``.
        rl_action : RLAction | dict
            Action chosen by the reinforcement-learning agent.
        digital_twin_result : TwinResult | dict
            Outcome of the Digital-Twin simulation.
        risk_check : dict
            Dict with ``"can_trade"`` (bool) and ``"reason"`` (str).
        bayesian_verdict : BayesianVerdict | dict | None
            Output from the Bayesian confidence engine.
        abstention_verdict : dict | None
            Output from the abstention module.
        ensemble_verdict : EnsembleVerdict | dict | None
            Output from the ensemble intelligence layer.

        Returns
        -------
        StructuredExplanation
        """
        try:
            raw_data: Dict[str, Any] = {
                "analyzer_output": analyzer_output,
                "trade_memory_stats": trade_memory_stats,
                "case_reasoner_output": case_reasoner_output,
                "risk_check": risk_check,
            }

            factors: List[Dict[str, Any]] = []

            # ── 1. Analyzer consensus ─────────────────────────────────────
            consensus_value = self._extract_analyzer_consensus(analyzer_output)
            factors.append(self._build_factor("analyzer_consensus", consensus_value, weight=0.18))

            # ── 2. Opportunity-score components ────────────────────────────
            opp_components = _safe_attr(opportunity_score, "components", {})
            if not isinstance(opp_components, dict):
                opp_components = {}
            opp_weights = _safe_attr(opportunity_score, "_weights", {})
            if not isinstance(opp_weights, dict):
                opp_weights = {}

            for comp_name, comp_value in opp_components.items():
                if comp_name in ("analyzer_consensus",):
                    continue
                w = opp_weights.get(comp_name, 0.08)
                factors.append(self._build_factor(comp_name, comp_value, weight=w))

            # ── 3. Regime alignment ───────────────────────────────────────
            regime_confidence = float(_safe_attr(regime, "confidence", 0.0))
            regime_name = str(_safe_attr(regime, "regime", "UNKNOWN"))
            regime_score = regime_confidence * 100.0
            factors.append(self._build_factor("regime_alignment", regime_score, weight=0.10))
            raw_data["regime_name"] = regime_name
            raw_data["regime_confidence"] = regime_confidence

            # ── 4. Case-based reasoner ────────────────────────────────────
            cbr_win_rate = float(case_reasoner_output.get("win_rate_in_similar", 0.0)) * 100.0
            cbr_recommendation = case_reasoner_output.get("recommendation", "NEUTRAL")
            factors.append(self._build_factor("case_based_reasoner", cbr_win_rate, weight=0.12))
            raw_data["cbr_win_rate"] = cbr_win_rate
            raw_data["cbr_recommendation"] = cbr_recommendation

            # ── 5. RL agent ───────────────────────────────────────────────
            rl_confidence = float(_safe_attr(rl_action, "confidence", 0.0)) * 100.0
            rl_action_name = str(_safe_attr(rl_action, "action", "ABSTAIN"))
            q_vals = _safe_attr(rl_action, "q_values", {})
            if not isinstance(q_vals, dict):
                q_vals = {}
            rl_q_trade = q_vals.get("TRADE", 0.0)
            rl_score = rl_confidence if rl_action_name == "TRADE" else -rl_confidence
            factors.append(self._build_factor("rl_agent", rl_score, weight=0.10))
            raw_data["rl_action"] = rl_action_name
            raw_data["rl_confidence"] = rl_confidence
            raw_data["rl_q_trade"] = rl_q_trade

            # ── 6. Digital twin ───────────────────────────────────────────
            twin_approved = bool(_safe_attr(digital_twin_result, "approved", False))
            twin_win_rate = float(_safe_attr(digital_twin_result, "simulated_win_rate", 0.0)) * 100.0
            twin_score = twin_win_rate if twin_approved else -twin_win_rate
            factors.append(self._build_factor("digital_twin", twin_score, weight=0.12))
            raw_data["twin_approved"] = twin_approved
            raw_data["twin_win_rate"] = twin_win_rate

            # ── 7. Bayesian confidence ────────────────────────────────────
            bayes_conf = 50.0
            bayes_recommendation = "NO_DATA"
            if bayesian_verdict is not None:
                bayes_conf = float(_safe_attr(bayesian_verdict, "overall_confidence", 0.5)) * 100.0
                bayes_recommendation = str(_safe_attr(bayesian_verdict, "recommendation", "NO_DATA"))
                raw_data["bayesian_confidence"] = bayes_conf
                raw_data["bayesian_recommendation"] = bayes_recommendation
            factors.append(self._build_factor("bayesian_confidence", bayes_conf, weight=0.10))

            # ── 8. Abstention signal ─────────────────────────────────────
            abstain_score = 0.0
            if abstention_verdict is not None:
                should_abstain = bool(_safe_attr(abstention_verdict, "should_abstain", False))
                abstain_conf = float(_safe_attr(abstention_verdict, "confidence", 0.0)) * 100.0
                abstain_score = -abstain_conf if should_abstain else abstain_conf
                raw_data["abstention_should_abstain"] = should_abstain
                raw_data["abstention_confidence"] = abstain_conf
            factors.append(self._build_factor("abstention_signal", abstain_score, weight=0.08))

            # ── 9. Ensemble direction ─────────────────────────────────────
            ensemble_score = 0.0
            if ensemble_verdict is not None:
                ensemble_dir = str(_safe_attr(ensemble_verdict, "direction", "NEUTRAL"))
                ensemble_conf = float(_safe_attr(ensemble_verdict, "confidence", 0.0))
                ensemble_agreement = float(_safe_attr(ensemble_verdict, "agreement_ratio", 0.0)) * 100.0
                ensemble_score = ensemble_conf if ensemble_dir in ("CALL", "PUT") else -ensemble_conf * 0.5
                raw_data["ensemble_direction"] = ensemble_dir
                raw_data["ensemble_confidence"] = ensemble_conf
                raw_data["ensemble_agreement"] = ensemble_agreement
            factors.append(self._build_factor("ensemble_direction", ensemble_score, weight=0.08))

            # ── 10. Risk check ────────────────────────────────────────────
            risk_passed = risk_check.get("can_trade", True)
            risk_reason = risk_check.get("reason", "")
            risk_score = 80.0 if risk_passed else -50.0
            factors.append(self._build_factor("risk_check", risk_score, weight=0.14))
            raw_data["risk_passed"] = risk_passed
            raw_data["risk_reason"] = risk_reason

            # ── Rank factors ──────────────────────────────────────────────
            factors.sort(key=lambda f: abs(f["contribution"]), reverse=True)

            # ── Compute overall score and confidence ──────────────────────
            contributions = np.array([f["contribution"] for f in factors], dtype=np.float64)
            weights = np.array([f["weight"] for f in factors], dtype=np.float64)
            total_weight = float(weights.sum()) if weights.sum() > 0 else 1.0

            raw_sum = float(contributions.sum())
            overall_score = (raw_sum / total_weight + 100.0) / 2.0
            overall_score = float(np.clip(overall_score, 0.0, 100.0))
            confidence = overall_score

            # ── Confidence decomposition ──────────────────────────────────
            decomp = self.decompose_confidence(factors, overall_score)

            # ── Decision path ─────────────────────────────────────────────
            path = self.trace_decision_path(
                overall_score=overall_score,
                consensus_value=consensus_value,
                regime_name=regime_name,
                regime_confidence=regime_confidence,
                twin_approved=twin_approved,
                twin_win_rate=twin_win_rate,
                risk_passed=risk_passed,
                risk_reason=risk_reason,
                cbr_win_rate=cbr_win_rate,
                rl_action_name=rl_action_name,
                bayes_conf=bayes_conf,
                abstain_score=abstain_score,
            )

            # ── Final decision ────────────────────────────────────────────
            decision, recommendation = self._determine_decision(
                overall_score, consensus_value, regime_name, regime_confidence,
                twin_approved, twin_win_rate, risk_passed, risk_reason,
                cbr_win_rate, rl_action_name, bayes_conf,
            )

            # ── Similar historical cases ──────────────────────────────────
            similar_cases = trade_memory_stats.get("total_trades", 0)
            similar_cases = case_reasoner_output.get("similar_cases_count", similar_cases)

            # ── Build explanation ─────────────────────────────────────────
            explanation = StructuredExplanation(
                decision=decision,
                confidence=round(confidence, 2),
                score=round(overall_score, 2),
                factors=factors,
                regime_description=_describe_regime(regime),
                risk_assessment=_assess_risk(risk_check),
                similar_historical_cases=int(similar_cases),
                recommendation=recommendation,
                timestamp=time.time(),
                raw_data=raw_data,
                confidence_decomposition=decomp,
                decision_path=[step.to_dict() for step in path],
            )

            # ── Persist and track ─────────────────────────────────────────
            self._history.append(explanation)
            if len(self._history) > MAX_HISTORY:
                self._history = self._history[-MAX_HISTORY:]
            self._decision_counts[decision] = self._decision_counts.get(decision, 0) + 1
            self._total_scores.append(overall_score)
            self._total_confidences.append(confidence)
            if decision in ("ABSTAIN", "REJECT"):
                self._rejection_reasons_counter[recommendation] += 1
            for f in factors:
                self._factor_accumulator[f["name"]].append(abs(f["contribution"]))
            self._store.save(explanation)

            logger.info(
                "Explanation: %s (score=%.1f, conf=%.1f) — %s",
                decision, overall_score, confidence, recommendation[:80],
            )
            return explanation

        except Exception as exc:
            logger.error("Explanation generation failed: %s", exc, exc_info=True)
            return StructuredExplanation(
                decision="ABSTAIN", confidence=0.0, score=0.0, factors=[],
                regime_description="Error generating explanation",
                risk_assessment=str(exc), similar_historical_cases=0,
                recommendation=f"Explanation error: {exc}", timestamp=time.time(),
                raw_data={"error": str(exc)}, confidence_decomposition={},
                decision_path=[],
            )

    # ── Confidence decomposition ──────────────────────────────────────────

    def decompose_confidence(
        self,
        factors: List[Dict[str, Any]],
        overall_score: float,
    ) -> Dict[str, float]:
        """Break overall confidence into per-component contributions.

        Each component's contribution is expressed as a percentage of the
        total absolute contribution, so values sum to 100.

        Parameters
        ----------
        factors : list[dict]
            Ranked factor dicts with ``"name"`` and ``"contribution"`` keys.
        overall_score : float
            The computed overall score in [0, 100].

        Returns
        -------
        dict
            Mapping of factor name → percentage contribution to confidence.
        """
        abs_contributions = {f["name"]: abs(f["contribution"]) for f in factors}
        total_abs = sum(abs_contributions.values())
        if total_abs < 1e-12:
            return {f["name"]: round(100.0 / max(len(factors), 1), 2) for f in factors}

        decomposition: Dict[str, float] = {}
        for name, val in abs_contributions.items():
            raw_pct = (val / total_abs) * 100.0
            decomposition[name] = round(raw_pct, 2)

        # Positive vs negative attribution
        pos_total = sum(f["contribution"] for f in factors if f["contribution"] > 0)
        neg_total = sum(abs(f["contribution"]) for f in factors if f["contribution"] < 0)
        grand_total = pos_total + neg_total if (pos_total + neg_total) > 0 else 1.0

        decomposition["_positive_sum"] = round(pos_total, 4)
        decomposition["_negative_sum"] = round(-neg_total, 4)
        decomposition["_net_contribution"] = round(pos_total - neg_total, 4)
        decomposition["_positive_ratio"] = round(pos_total / grand_total * 100, 2)
        decomposition["_overall_score"] = round(overall_score, 2)

        return decomposition

    # ── Decision path tracing ─────────────────────────────────────────────

    def trace_decision_path(
        self,
        overall_score: float,
        consensus_value: float,
        regime_name: str,
        regime_confidence: float,
        twin_approved: bool,
        twin_win_rate: float,
        risk_passed: bool,
        risk_reason: str,
        cbr_win_rate: float,
        rl_action_name: str,
        bayes_conf: float = 50.0,
        abstain_score: float = 0.0,
    ) -> List[DecisionStep]:
        """Produce a step-by-step audit trail of how the decision was made.

        Each step records the input, the threshold tested against, whether
        it passed, its contribution, and a human-readable explanation.

        Parameters
        ----------
        See ``explain()`` parameter descriptions.

        Returns
        -------
        list[DecisionStep]
            Ordered decision steps forming the audit trail.
        """
        steps: List[DecisionStep] = []

        # Step 1: Risk gate (hard reject)
        risk_step = DecisionStep(
            step_name="risk_gate",
            input_value={"can_trade": risk_passed, "reason": risk_reason},
            threshold={"can_trade": True},
            passed=risk_passed,
            contribution=80.0 if risk_passed else -50.0,
            explanation=(
                "All risk limits are within bounds — trade is permitted."
                if risk_passed
                else f"Risk gate BLOCKED: {risk_reason or 'limits exceeded'}"
            ),
        )
        steps.append(risk_step)

        if not risk_passed:
            return steps

        # Step 2: Analyzer consensus
        consensus_passed = consensus_value >= 40.0
        steps.append(DecisionStep(
            step_name="analyzer_consensus",
            input_value=round(consensus_value, 2),
            threshold=40.0,
            passed=consensus_passed,
            contribution=consensus_value * 0.18,
            explanation=(
                f"Analyzer consensus at {consensus_value:.0f}% exceeds minimum threshold."
                if consensus_passed
                else f"Analyzer consensus at {consensus_value:.0f}% is below 40% — weak signal."
            ),
        ))

        # Step 3: Regime evaluation
        regime_favourable = regime_name.upper() not in ("RANDOM",) or regime_confidence < 0.5
        steps.append(DecisionStep(
            step_name="regime_evaluation",
            input_value={"regime": regime_name, "confidence": round(regime_confidence, 4)},
            threshold={"regime": "NOT_RANDOM", "confidence": "< 0.5 if RANDOM"},
            passed=regime_favourable,
            contribution=regime_confidence * 100.0 * 0.10 if regime_favourable else -regime_confidence * 50.0,
            explanation=(
                f"Market regime '{regime_name}' (conf: {regime_confidence:.2f}) is suitable for trading."
                if regime_favourable
                else f"Market regime RANDOM with high confidence ({regime_confidence:.2f}) — no exploitable pattern."
            ),
        ))

        # Step 4: RL agent recommendation
        rl_approves = rl_action_name == "TRADE"
        steps.append(DecisionStep(
            step_name="rl_agent_gate",
            input_value=rl_action_name,
            threshold="TRADE",
            passed=rl_approves,
            contribution=10.0 if rl_approves else -10.0,
            explanation=(
                f"RL agent recommends TRADE."
                if rl_approves
                else f"RL agent recommends {rl_action_name} — no trade from RL perspective."
            ),
        ))

        # Step 5: Digital Twin simulation
        twin_passes = twin_approved and twin_win_rate >= 55.0
        steps.append(DecisionStep(
            step_name="digital_twin_simulation",
            input_value={"approved": twin_approved, "win_rate": round(twin_win_rate, 2)},
            threshold={"approved": True, "min_win_rate": 55.0},
            passed=twin_passes,
            contribution=twin_win_rate * 0.12 if twin_passes else -twin_win_rate * 0.12,
            explanation=(
                f"Digital Twin simulation approved with {twin_win_rate:.0f}% win rate."
                if twin_passes
                else f"Digital Twin simulation rejected (win rate: {twin_win_rate:.0f}%)."
            ),
        ))

        # Step 6: Bayesian confidence check
        bayes_passes = bayes_conf >= 45.0
        steps.append(DecisionStep(
            step_name="bayesian_confidence",
            input_value=round(bayes_conf, 2),
            threshold=45.0,
            passed=bayes_passes,
            contribution=bayes_conf * 0.10 if bayes_passes else -bayes_conf * 0.05,
            explanation=(
                f"Bayesian posterior confidence at {bayes_conf:.1f}% — sufficient evidence."
                if bayes_passes
                else f"Bayesian confidence at {bayes_conf:.1f}% — insufficient evidence."
            ),
        ))

        # Step 7: Historical precedent
        precedent_strong = cbr_win_rate >= 55.0
        steps.append(DecisionStep(
            step_name="historical_precedent",
            input_value=round(cbr_win_rate, 2),
            threshold=55.0,
            passed=precedent_strong,
            contribution=cbr_win_rate * 0.12 if precedent_strong else 0.0,
            explanation=(
                f"Historical cases show {cbr_win_rate:.0f}% win rate — strong precedent."
                if precedent_strong
                else f"Historical win rate {cbr_win_rate:.0f}% — no strong precedent."
            ),
        ))

        # Step 8: Abstention override check
        abstention_active = abstain_score < -30.0
        steps.append(DecisionStep(
            step_name="abstention_override",
            input_value=round(abstain_score, 2),
            threshold=-30.0,
            passed=not abstention_active,
            contribution=abstain_score * 0.08,
            explanation=(
                "No abstention override triggered."
                if not abstention_active
                else f"Abstention module active (score: {abstain_score:.1f}) — suppressing trade."
            ),
        ))

        # Step 9: Composite score evaluation
        score_above_trade = overall_score >= 60.0
        score_above_abstain = overall_score >= 40.0
        steps.append(DecisionStep(
            step_name="composite_score_evaluation",
            input_value=round(overall_score, 2),
            threshold={"trade": 60.0, "abstain": 40.0},
            passed=score_above_trade,
            contribution=0.0,
            explanation=(
                f"Composite score {overall_score:.1f}/100 exceeds trade threshold (60)."
                if score_above_trade
                else (
                    f"Composite score {overall_score:.1f}/100 is between 40-60 — marginal zone."
                    if score_above_abstain
                    else f"Composite score {overall_score:.1f}/100 is below 40 — clear abstain zone."
                ),
            ),
        ))

        return steps

    # ── Factor explanation builder ────────────────────────────────────────

    def _build_factor(
        self,
        name: str,
        value: float,
        weight: float = 0.10,
    ) -> Dict[str, Any]:
        contribution = _clamp(value * weight, -100.0, 100.0)
        description = _format_factor_description(name, contribution, value)
        return {
            "name": name,
            "contribution": round(contribution, 4),
            "description": description,
            "weight": round(weight, 4),
        }

    # ── Formatted report ──────────────────────────────────────────────────

    def generate_trade_report(self, explanation: StructuredExplanation) -> str:
        """Generate a formatted human-readable text report.

        Parameters
        ----------
        explanation : StructuredExplanation

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

        decision_symbol = {
            "TRADE": "[TRADE]",
            "ABSTAIN": "[ABSTAIN]",
            "REJECT": "[REJECT]",
        }.get(explanation.decision, "[???]")
        lines.append(f"  Decision:   {decision_symbol}")
        lines.append(f"  Score:      {explanation.score:.1f} / 100")
        lines.append(f"  Confidence: {explanation.confidence:.1f}%")
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

        # Confidence decomposition summary
        decomp = explanation.confidence_decomposition
        if decomp:
            lines.append("  CONFIDENCE DECOMPOSITION:")
            lines.append("  " + "-" * 50)
            pos_sum = decomp.get("_positive_sum", 0)
            neg_sum = decomp.get("_negative_sum", 0)
            pos_ratio = decomp.get("_positive_ratio", 50.0)
            lines.append(f"  Positive factors: +{pos_sum:.2f}  ({pos_ratio:.0f}% of total)")
            lines.append(f"  Negative factors: {neg_sum:.2f}  ({100.0 - pos_ratio:.0f}% of total)")
            lines.append(f"  Net contribution:  {decomp.get('_net_contribution', 0):+.2f}")
            lines.append("")

        # Decision path
        if explanation.decision_path:
            lines.append("  DECISION PATH (audit trail):")
            lines.append("  " + "-" * 50)
            for i, step in enumerate(explanation.decision_path, 1):
                status = "PASS" if step["passed"] else "FAIL"
                lines.append(
                    f"  {i:2d}. [{status}] {step['step_name']}"
                )
                lines.append(f"      {step['explanation']}")
            lines.append("")

        # Regime and risk
        lines.append(f"  REGIME: {explanation.regime_description}")
        lines.append("")
        lines.append(f"  RISK:   {explanation.risk_assessment}")
        lines.append("")

        # Historical context
        lines.append(
            f"  HISTORICAL CONTEXT: {explanation.similar_historical_cases} similar past cases"
        )
        lines.append("")
        lines.append(f"  RECOMMENDATION: {explanation.recommendation}")
        lines.append("")
        lines.append("=" * 72)

        return "\n".join(lines)

    # ── Decision stats ────────────────────────────────────────────────────

    def get_decision_stats(self) -> Dict[str, Any]:
        """Aggregate statistics over all explanations generated in this session.

        Returns
        -------
        dict
            Keys include ``total_explanations``, ``acceptance_rate``,
            ``rejection_rate``, ``avg_score``, ``avg_confidence``,
            ``common_rejection_reasons``, ``decision_distribution``.
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
            stats["median_score"] = 0.0
            stats["score_std"] = 0.0

        if self._total_confidences:
            conf_arr = np.array(self._total_confidences)
            stats["avg_confidence"] = round(float(conf_arr.mean()), 2)
            stats["confidence_std"] = round(float(conf_arr.std()), 2)
        else:
            stats["avg_confidence"] = 0.0
            stats["confidence_std"] = 0.0

        common = self._rejection_reasons_counter.most_common(5)
        stats["common_rejection_reasons"] = [
            {"reason": reason, "count": count} for reason, count in common
        ]

        return stats

    def get_persistent_stats(self) -> Dict[str, Any]:
        """Load stats from the SQLite store (cross-session)."""
        return self._store.get_stats()

    # ── Factor importance ─────────────────────────────────────────────────

    def get_factor_importance(self, n: int = 500) -> Dict[str, float]:
        """Which factors matter most over time.

        Computes the mean absolute contribution of each factor across the
        most recent *n* explanations (in-memory first, then falls back to
        the database).

        Parameters
        ----------
        n : int
            Number of recent explanations to consider.

        Returns
        -------
        dict
            Mapping of factor name → mean absolute contribution, sorted
            descending.
        """
        # Prefer in-memory data if available
        if self._factor_accumulator:
            result = {
                name: round(float(np.mean(vals[-n:])), 4)
                for name, vals in self._factor_accumulator.items()
                if vals
            }
            return dict(sorted(result.items(), key=lambda kv: -kv[1]))

        # Fall back to database
        return self._store.get_factor_importance(n)

    # ── Export ────────────────────────────────────────────────────────────

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

    # ── History access ────────────────────────────────────────────────────

    def get_explanation_history(self, n: int = 50) -> List[StructuredExplanation]:
        """Return the most recent *n* explanations (in-memory, newest first)."""
        return list(reversed(self._history[-n:]))

    # ── Persistence (joblib) ─────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist engine state to disk via joblib."""
        state = {
            "decision_counts": dict(self._decision_counts),
            "total_scores": self._total_scores[-MAX_HISTORY:],
            "total_confidences": self._total_confidences[-MAX_HISTORY:],
            "rejection_reasons_counter": dict(self._rejection_reasons_counter),
            "factor_accumulator": {
                k: v[-MAX_HISTORY:] for k, v in self._factor_accumulator.items()
            },
        }
        try:
            import joblib
            joblib.dump(state, path)
            logger.info("ExplainableEngine state saved to %s", path)
        except Exception as exc:
            logger.error("Failed to save engine state: %s", exc, exc_info=True)

    def load(self, path: str) -> bool:
        """Load engine state from disk via joblib."""
        try:
            import joblib
            state = joblib.load(path)
            self._decision_counts = state.get("decision_counts", {"TRADE": 0, "ABSTAIN": 0, "REJECT": 0})
            self._total_scores = state.get("total_scores", [])
            self._total_confidences = state.get("total_confidences", [])
            self._rejection_reasons_counter = Counter(state.get("rejection_reasons_counter", {}))
            raw_accum = state.get("factor_accumulator", {})
            self._factor_accumulator = defaultdict(list, {
                k: list(v) for k, v in raw_accum.items()
            })
            logger.info("ExplainableEngine state loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load engine state: %s", exc, exc_info=True)
            return False

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_analyzer_consensus(analyzer_output: Dict[str, Any]) -> float:
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
        bayes_conf: float = 50.0,
    ) -> Tuple[str, str]:
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
                    f"ABSTAIN: Market is RANDOM (confidence: {regime_confidence:.2f}). "
                    f"Digital Twin win rate only {twin_win_rate:.0f}% in simulation"
                )

        # Abstain on low consensus
        if consensus < 40.0 and overall_score < 60.0:
            return "ABSTAIN", (
                f"ABSTAIN: Low consensus ({consensus:.0f}%), "
                f"market is {regime_name} (confidence: {regime_confidence:.2f})"
            )

        # Abstain if Bayesian confidence is very low
        if bayes_conf < 35.0 and overall_score < 70.0:
            return "ABSTAIN", (
                f"ABSTAIN: Bayesian confidence critically low ({bayes_conf:.1f}%), "
                f"insufficient evidence to trade"
            )

        # Trade: sufficient score and favourable conditions
        if overall_score >= 60.0:
            parts = [
                f"TRADE recommended: Score {overall_score:.1f}/100",
                f"Consensus {consensus:.0f}%",
                f"Regime: {regime_name} (confidence: {regime_confidence:.2f})",
            ]
            if twin_approved:
                parts.append(f"Digital Twin approves ({twin_win_rate:.0f}% win rate)")
            else:
                parts.append(f"Digital Twin inconclusive ({twin_win_rate:.0f}% win rate)")
            if rl_action_name == "TRADE":
                parts.append("RL agent recommends TRADE")
            if cbr_win_rate > 50.0:
                parts.append(f"Historical precedent: {cbr_win_rate:.0f}% win rate")
            if bayes_conf > 55.0:
                parts.append(f"Bayesian confidence: {bayes_conf:.0f}%")
            return "TRADE", ", ".join(parts)

        # Default: abstain
        return "ABSTAIN", (
            f"ABSTAIN: Score {overall_score:.1f} below trade threshold. "
            f"Consensus={consensus:.0f}%, regime={regime_name}"
        )
