"""
Meta-Learning Supervisor — monitors, calibrates, and governs the entire
intelligence layer.

Tracks five key metrics — calibration quality, inference latency,
false-positive rate, missed opportunities, and profit factor — then
recommends weight adjustments and recalibration actions to keep the
system operating within healthy bounds.
"""

import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)

_BUFFER_MAX = 500
_MIN_SAMPLES = 10
_MIN_WEIGHT = 0.02
_MAX_WEIGHT = 0.25
_DEFAULT_WEIGHT = 0.10
_CALIBRATION_DRIFT_THRESHOLD = 0.08
_COEF_WIN_RATE = 0.40
_COEF_PROFIT = 0.30
_COEF_CALIBRATION = 0.20
_COEF_CONSISTENCY = 0.10


@dataclass
class CalibrationReport:
    """Result of a single calibration check on one metric."""
    metric_name: str
    expected_value: float
    actual_value: float
    calibration_error: float
    sample_count: int
    recommendation: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "expected_value": round(self.expected_value, 6),
            "actual_value": round(self.actual_value, 6),
            "calibration_error": round(self.calibration_error, 6),
            "sample_count": self.sample_count,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class AnalyzerStats:
    """Per-analyzer performance snapshot."""
    analyzer_name: str
    win_rate: float
    total_predictions: int
    avg_confidence: float
    profit_factor: float
    calibration_error: float
    false_positive_rate: float
    current_weight: float
    consistency: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyzer_name": self.analyzer_name,
            "win_rate": round(self.win_rate, 4),
            "total_predictions": self.total_predictions,
            "avg_confidence": round(self.avg_confidence, 2),
            "profit_factor": round(self.profit_factor, 4),
            "calibration_error": round(self.calibration_error, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "current_weight": round(self.current_weight, 4),
            "consistency": round(self.consistency, 4),
        }


@dataclass
class MetaReport:
    """Aggregate meta-learning statistics for the full pipeline."""
    total_supervisions: int
    active_analyzers: int
    overall_calibration_error: float
    overall_profit_factor: float
    overall_false_positive_rate: float
    pipeline_health: str
    uptime_hours: float
    drift_detected: bool
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_supervisions": self.total_supervisions,
            "active_analyzers": self.active_analyzers,
            "overall_calibration_error": round(self.overall_calibration_error, 4),
            "overall_profit_factor": round(self.overall_profit_factor, 4),
            "overall_false_positive_rate": round(self.overall_false_positive_rate, 4),
            "pipeline_health": self.pipeline_health,
            "uptime_hours": round(self.uptime_hours, 2),
            "drift_detected": self.drift_detected,
            "timestamp": self.timestamp,
        }


class MetaSupervisor:
    """Monitors and calibrates the full intelligence layer.

    Tracks five key metrics: calibration quality, inference latency,
    false-positive rate, missed opportunities, and profit factor.
    Per-analyzer statistics are maintained in circular buffers to detect
    degradation and recommend weight adjustments.
    """

    def __init__(self) -> None:
        self._total_supervisions: int = 0
        self._creation_time: float = time.time()

        # Per-metric circular buffers
        self._calibration_scores: deque = deque(maxlen=_BUFFER_MAX)
        self._latency_samples: deque = deque(maxlen=_BUFFER_MAX)
        self._false_positive_flags: deque = deque(maxlen=_BUFFER_MAX)
        self._missed_opportunity_flags: deque = deque(maxlen=_BUFFER_MAX)
        self._profit_values: deque = deque(maxlen=_BUFFER_MAX)

        # Per-analyzer tracking
        self._analyzer_predictions: Dict[str, deque] = {}
        self._analyzer_confidences: Dict[str, deque] = {}
        self._analyzer_correct: Dict[str, deque] = {}
        self._analyzer_profits: Dict[str, deque] = {}

        # Weight state
        self._current_weights: Dict[str, float] = {}
        self._weight_history: List[Dict[str, float]] = []

        # Drift tracking
        self._drift_events: int = 0
        self._drift_history: deque = deque(maxlen=100)

        logger.info("MetaSupervisor initialised")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_analyzer(self, name: str) -> None:
        if name not in self._analyzer_predictions:
            self._analyzer_predictions[name] = deque(maxlen=_BUFFER_MAX)
            self._analyzer_confidences[name] = deque(maxlen=_BUFFER_MAX)
            self._analyzer_correct[name] = deque(maxlen=_BUFFER_MAX)
            self._analyzer_profits[name] = deque(maxlen=_BUFFER_MAX)

    @staticmethod
    def _normalize(values: np.ndarray) -> np.ndarray:
        if len(values) == 0:
            return values
        mn, mx = values.min(), values.max()
        if mx - mn < 1e-12:
            return np.full_like(values, 0.5)
        return (values - mn) / (mx - mn)

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def _compute_profit_factor(profits: np.ndarray) -> float:
        gains = float(profits[profits > 0].sum()) if (profits > 0).any() else 0.0
        losses = float(abs(profits[profits < 0].sum())) if (profits < 0).any() else 0.0
        return gains / losses if losses > 1e-12 else (gains if gains > 0 else 1.0)

    @staticmethod
    def _compute_consistency(correct_flags: np.ndarray) -> float:
        if len(correct_flags) < 3:
            return 0.5
        flips = int(np.sum(np.abs(np.diff(correct_flags))))
        max_flips = len(correct_flags) - 1
        return 1.0 - (flips / max_flips) if max_flips > 0 else 0.5

    def _assess_calibration(self, meta_ai_data: Dict[str, Any]) -> float:
        total_cal, count = 0.0, 0
        for info in meta_ai_data.values():
            if not isinstance(info, dict):
                continue
            wr = info.get("win_rate", 0.5)
            c_cor = info.get("avg_confidence_when_correct", 50.0) / 100.0
            c_wrg = info.get("avg_confidence_when_wrong", 50.0) / 100.0
            total_cal += abs(c_cor - wr) * wr + abs(c_wrg - (1.0 - wr)) * (1.0 - wr)
            count += 1
        return total_cal / count if count > 0 else 0.0

    def _assess_false_positive_rate(self, meta_ai_data: Dict[str, Any]) -> float:
        tw, t = 0, 0
        for info in meta_ai_data.values():
            if not isinstance(info, dict):
                continue
            t += info.get("total_predictions", 0)
            tw += info.get("wrong", 0)
        return tw / t if t > 0 else 0.0

    def _assess_missed_opportunities(self, state: Dict[str, Any]) -> float:
        p = state.get("pipeline_stats", {})
        total = p.get("trades_recommended", 0) + p.get("abstentions", 0)
        return p.get("abstentions", 0) / total if total > 0 else 0.0

    def _assess_profit_factor(self, meta_ai_data: Dict[str, Any]) -> float:
        tp, tl = 0.0, 0.0
        for info in meta_ai_data.values():
            if not isinstance(info, dict):
                continue
            profit = info.get("profit_contribution", 0.0)
            if profit > 0:
                tp += profit
            else:
                tl += abs(profit)
        return tp / tl if tl > 1e-12 else (tp if tp > 0 else 1.0)

    def _update_analyzer_tracking(self, meta_ai_data: Dict[str, Any]) -> None:
        for name, info in meta_ai_data.items():
            if not isinstance(info, dict):
                continue
            self._ensure_analyzer(name)
            self._analyzer_predictions[name].append(info.get("total_predictions", 0))
            self._analyzer_confidences[name].append(info.get("avg_confidence_when_correct", 50.0))
            self._analyzer_correct[name].append(info.get("win_rate", 0.0))
            self._analyzer_profits[name].append(info.get("profit_contribution", 0.0))

    def _build_metric_report(
        self, metric_name: str, current_value: float, history: deque,
        expected: Optional[float] = None,
    ) -> CalibrationReport:
        arr = np.array(list(history))
        n = len(arr)
        if expected is None:
            expected = float(arr.mean()) if n > 0 else 0.0
        actual = float(arr[-1]) if n > 0 else 0.0
        error = abs(actual - expected)
        if n < _MIN_SAMPLES:
            rec = "insufficient_data"
        elif error < 0.02:
            rec = "within_tolerance"
        elif error < 0.05:
            rec = "monitor_closely"
        elif error < 0.10:
            rec = "recalibrate_soon"
        else:
            rec = "recalibrate_now"
        return CalibrationReport(
            metric_name=metric_name, expected_value=expected,
            actual_value=actual, calibration_error=error,
            sample_count=n, recommendation=rec,
        )

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def supervise(self, intelligence_state: Dict[str, Any]) -> Dict[str, CalibrationReport]:
        """Evaluate the full intelligence state and return calibration reports."""
        self._total_supervisions += 1
        reports: Dict[str, CalibrationReport] = {}
        meta_ai_data = intelligence_state.get("meta_ai", {})
        pipeline = intelligence_state.get("pipeline_stats", {})

        cal_error = self._assess_calibration(meta_ai_data)
        self._calibration_scores.append(cal_error)
        reports["calibration"] = self._build_metric_report(
            "calibration", cal_error, self._calibration_scores)

        latency = float(pipeline.get("avg_latency_ms", 100.0))
        self._latency_samples.append(latency)
        elat = float(np.median(list(self._latency_samples))) if self._latency_samples else 100.0
        reports["latency"] = self._build_metric_report(
            "latency", latency, self._latency_samples, expected=elat)

        fpr = self._assess_false_positive_rate(meta_ai_data)
        self._false_positive_flags.append(fpr)
        reports["false_positive_rate"] = self._build_metric_report(
            "false_positive_rate", fpr, self._false_positive_flags, expected=0.30)

        missed = self._assess_missed_opportunities(intelligence_state)
        self._missed_opportunity_flags.append(missed)
        reports["missed_opportunities"] = self._build_metric_report(
            "missed_opportunities", missed, self._missed_opportunity_flags, expected=0.15)

        pf = self._assess_profit_factor(meta_ai_data)
        self._profit_values.append(pf)
        reports["profit_factor"] = self._build_metric_report(
            "profit_factor", pf, self._profit_values, expected=1.5)

        self._update_analyzer_tracking(meta_ai_data)
        logger.info(
            "Supervision #%d: cal=%.4f fpr=%.4f pf=%.4f",
            self._total_supervisions, cal_error, fpr, pf,
        )
        return reports

    # ------------------------------------------------------------------
    # Weight adjustment
    # ------------------------------------------------------------------

    def update_weights(self) -> Dict[str, float]:
        """Recalculate analyzer weights: 0.4×win_rate + 0.3×profit +
        0.2×calibration + 0.1×consistency, normalised to sum to 1.0."""
        analyzers = list(self._analyzer_predictions.keys())
        if not analyzers:
            return self._current_weights

        wr_list, pf_list, cal_list, con_list = [], [], [], []
        for name in analyzers:
            correct = np.array(self._analyzer_correct[name])
            confs = np.array(self._analyzer_confidences[name])
            profs = (
                np.array(self._analyzer_profits[name])
                if self._analyzer_profits[name] else np.array([0.0])
            )
            wr_list.append(float(correct.mean()) if len(correct) > 0 else 0.0)
            pf_list.append(self._compute_profit_factor(profs))
            if len(confs) > 0 and len(correct) > 0:
                brier = float(np.mean((np.clip(confs / 100.0, 0.0, 1.0) - correct) ** 2))
                cal_list.append(1.0 - brier)
            else:
                cal_list.append(0.5)
            con_list.append(self._compute_consistency(correct))

        wr_arr = self._normalize(np.array(wr_list))
        pf_arr = self._normalize(np.array(pf_list))
        cal_arr = self._normalize(np.array(cal_list))
        con_arr = self._normalize(np.array(con_list))

        weights: Dict[str, float] = {}
        for i, name in enumerate(analyzers):
            raw = (
                _COEF_WIN_RATE * wr_arr[i] + _COEF_PROFIT * pf_arr[i]
                + _COEF_CALIBRATION * cal_arr[i] + _COEF_CONSISTENCY * con_arr[i]
            )
            weights[name] = self._clamp(raw, _MIN_WEIGHT, _MAX_WEIGHT)

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        self._current_weights = weights
        self._weight_history.append(dict(weights))
        logger.info("Adjusted weights: %s", {k: round(v, 4) for k, v in weights.items()})
        return weights

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_analyzer_report(self) -> Dict[str, AnalyzerStats]:
        """Return per-analyzer performance statistics."""
        report: Dict[str, AnalyzerStats] = {}
        for name in self._analyzer_predictions:
            correct = np.array(self._analyzer_correct[name])
            confs = np.array(self._analyzer_confidences[name])
            profs = (
                np.array(self._analyzer_profits[name])
                if self._analyzer_profits[name] else np.array([0.0])
            )
            n = len(correct)
            nc = int(correct.sum()) if n > 0 else 0
            wr = nc / n if n > 0 else 0.0
            cal_err = (
                float(np.mean((np.clip(confs / 100.0, 0.0, 1.0) - correct) ** 2))
                if n >= _MIN_SAMPLES else 0.0
            )
            report[name] = AnalyzerStats(
                analyzer_name=name, win_rate=wr, total_predictions=n,
                avg_confidence=float(confs.mean()) if n > 0 else 0.0,
                profit_factor=self._compute_profit_factor(profs),
                calibration_error=cal_err,
                false_positive_rate=(n - nc) / n if n > 0 else 0.0,
                current_weight=self._current_weights.get(name, _DEFAULT_WEIGHT),
                consistency=self._compute_consistency(correct),
            )
        return report

    def get_meta_report(self) -> MetaReport:
        """Return overall meta-learning statistics for the full pipeline."""
        uptime_h = (time.time() - self._creation_time) / 3600.0
        oc = float(np.mean(self._calibration_scores)) if self._calibration_scores else 0.0
        opf = float(np.mean(list(self._profit_values))) if self._profit_values else 1.0
        ofpr = float(np.mean(self._false_positive_flags)) if self._false_positive_flags else 0.0
        if oc < 0.05 and opf > 1.2 and ofpr < 0.35:
            health = "HEALTHY"
        elif oc < 0.10 and opf > 1.0:
            health = "DEGRADED"
        else:
            health = "UNHEALTHY"
        return MetaReport(
            total_supervisions=self._total_supervisions,
            active_analyzers=len(self._analyzer_predictions),
            overall_calibration_error=oc, overall_profit_factor=opf,
            overall_false_positive_rate=ofpr, pipeline_health=health,
            uptime_hours=uptime_h, drift_detected=self._drift_events > 0,
        )

    # ------------------------------------------------------------------
    # Calibration drift detection
    # ------------------------------------------------------------------

    def detect_calibration_drift(
        self, window: int = 100, threshold: float = _CALIBRATION_DRIFT_THRESHOLD,
    ) -> Dict[str, Any]:
        """Detect whether calibration has drifted via two-sample KS test."""
        scores = np.array(list(self._calibration_scores))
        if len(scores) < window * 2:
            mv = float(scores.mean()) if len(scores) > 0 else 0.0
            return {
                "drift_detected": False, "ks_statistic": 0.0, "p_value": 1.0,
                "recent_mean": mv, "historical_mean": mv,
                "recommendation": "insufficient_data",
            }
        hist, recent = scores[:-window], scores[-window:]
        ks_stat, p_value = sp_stats.ks_2samp(hist, recent)
        rm, hm = float(recent.mean()), float(hist.mean())
        drift_detected = p_value < 0.05 and abs(rm - hm) > threshold
        if drift_detected:
            self._drift_events += 1
            self._drift_history.append({
                "time": time.time(), "ks_statistic": float(ks_stat),
                "p_value": float(p_value), "shift": rm - hm,
            })
            rec = (
                f"RECALIBRATE — calibration drifted from {hm:.4f} to {rm:.4f} "
                f"(KS={ks_stat:.4f}, p={p_value:.4f})"
            )
        else:
            rec = "calibration_stable"
        return {
            "drift_detected": drift_detected,
            "ks_statistic": round(float(ks_stat), 4),
            "p_value": round(float(p_value), 4),
            "recent_mean": round(rm, 4),
            "historical_mean": round(hm, 4),
            "recommendation": rec,
        }

    # ------------------------------------------------------------------
    # Recommended adjustments
    # ------------------------------------------------------------------

    def get_recommended_adjustments(self) -> List[Dict[str, Any]]:
        """Return suggested config changes based on tracked performance."""
        adjustments: List[Dict[str, Any]] = []
        report = self.get_analyzer_report()
        drift = self.detect_calibration_drift()

        for name, s in report.items():
            if s.total_predictions < _MIN_SAMPLES:
                continue
            if s.false_positive_rate > 0.55:
                adjustments.append({
                    "component": f"analyzer.{name}", "action": "reduce_weight",
                    "parameter": "weight",
                    "current_value": round(s.current_weight, 4),
                    "recommended_value": round(max(_MIN_WEIGHT, s.current_weight * 0.5), 4),
                    "reason": f"High false-positive rate ({s.false_positive_rate:.1%})",
                })
            if s.calibration_error > 0.15:
                adjustments.append({
                    "component": f"analyzer.{name}", "action": "recalibrate",
                    "parameter": "confidence_scaling", "current_value": 1.0,
                    "recommended_value": round(1.0 - (s.calibration_error - 0.10), 4),
                    "reason": f"Calibration error {s.calibration_error:.4f} exceeds threshold",
                })
            if s.win_rate >= 0.60 and s.current_weight < 0.08:
                adjustments.append({
                    "component": f"analyzer.{name}", "action": "increase_weight",
                    "parameter": "weight",
                    "current_value": round(s.current_weight, 4),
                    "recommended_value": round(min(_MAX_WEIGHT, s.current_weight * 1.5), 4),
                    "reason": f"Strong win rate ({s.win_rate:.1%}) with low weight",
                })
            if s.total_predictions > 0 and s.win_rate < 0.35:
                adjustments.append({
                    "component": f"analyzer.{name}", "action": "disable",
                    "parameter": "enabled", "current_value": True,
                    "recommended_value": False,
                    "reason": f"Win rate {s.win_rate:.1%} below min ({s.total_predictions} predictions)",
                })

        if drift["drift_detected"]:
            adjustments.append({
                "component": "pipeline.calibration", "action": "recalibrate_all",
                "parameter": "confidence_threshold", "current_value": None,
                "recommended_value": None, "reason": drift["recommendation"],
            })
        meta = self.get_meta_report()
        if meta.overall_profit_factor < 1.0:
            adjustments.append({
                "component": "pipeline.risk", "action": "tighten_gates",
                "parameter": "min_opportunity_score", "current_value": None,
                "recommended_value": None,
                "reason": f"Profit factor {meta.overall_profit_factor:.2f} below 1.0",
            })
        if meta.overall_false_positive_rate > 0.40:
            adjustments.append({
                "component": "pipeline.ensemble", "action": "increase_min_agreement",
                "parameter": "min_agreement", "current_value": 0.5,
                "recommended_value": 0.65,
                "reason": f"False-positive rate {meta.overall_false_positive_rate:.1%} elevated",
            })
        if meta.pipeline_health == "UNHEALTHY":
            adjustments.append({
                "component": "pipeline.general", "action": "reduce_exposure",
                "parameter": "base_amount", "current_value": None,
                "recommended_value": "50% of current",
                "reason": "Pipeline UNHEALTHY — reduce position sizing",
            })
        return adjustments

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist MetaSupervisor state to disk via joblib."""
        state = {
            "_total_supervisions": self._total_supervisions,
            "_creation_time": self._creation_time,
            "_calibration_scores": list(self._calibration_scores),
            "_latency_samples": list(self._latency_samples),
            "_false_positive_flags": list(self._false_positive_flags),
            "_missed_opportunity_flags": list(self._missed_opportunity_flags),
            "_profit_values": list(self._profit_values),
            "_analyzer_predictions": {k: list(v) for k, v in self._analyzer_predictions.items()},
            "_analyzer_confidences": {k: list(v) for k, v in self._analyzer_confidences.items()},
            "_analyzer_correct": {k: list(v) for k, v in self._analyzer_correct.items()},
            "_analyzer_profits": {k: list(v) for k, v in self._analyzer_profits.items()},
            "_current_weights": self._current_weights,
            "_weight_history": self._weight_history,
            "_drift_events": self._drift_events,
            "_drift_history": list(self._drift_history),
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(state, path)
        logger.info("MetaSupervisor state saved to %s", path)

    def load(self, path: str) -> bool:
        """Restore MetaSupervisor state from a previously saved file."""
        try:
            state = joblib.load(path)
            self._total_supervisions = state["_total_supervisions"]
            self._creation_time = state["_creation_time"]
            self._calibration_scores = deque(state["_calibration_scores"], maxlen=_BUFFER_MAX)
            self._latency_samples = deque(state["_latency_samples"], maxlen=_BUFFER_MAX)
            self._false_positive_flags = deque(state["_false_positive_flags"], maxlen=_BUFFER_MAX)
            self._missed_opportunity_flags = deque(state["_missed_opportunity_flags"], maxlen=_BUFFER_MAX)
            self._profit_values = deque(state["_profit_values"], maxlen=_BUFFER_MAX)
            self._analyzer_predictions = {
                k: deque(v, maxlen=_BUFFER_MAX) for k, v in state["_analyzer_predictions"].items()
            }
            self._analyzer_confidences = {
                k: deque(v, maxlen=_BUFFER_MAX) for k, v in state["_analyzer_confidences"].items()
            }
            self._analyzer_correct = {
                k: deque(v, maxlen=_BUFFER_MAX) for k, v in state["_analyzer_correct"].items()
            }
            self._analyzer_profits = {
                k: deque(v, maxlen=_BUFFER_MAX) for k, v in state["_analyzer_profits"].items()
            }
            self._current_weights = state["_current_weights"]
            self._weight_history = state["_weight_history"]
            self._drift_events = state["_drift_events"]
            self._drift_history = deque(state["_drift_history"], maxlen=100)
            logger.info("MetaSupervisor state loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load MetaSupervisor: %s", exc)
            return False

    def reset(self) -> None:
        """Clear all tracking data and reset to initial state."""
        self._total_supervisions = 0
        self._creation_time = time.time()
        self._calibration_scores.clear()
        self._latency_samples.clear()
        self._false_positive_flags.clear()
        self._missed_opportunity_flags.clear()
        self._profit_values.clear()
        self._analyzer_predictions.clear()
        self._analyzer_confidences.clear()
        self._analyzer_correct.clear()
        self._analyzer_profits.clear()
        self._current_weights.clear()
        self._weight_history.clear()
        self._drift_events = 0
        self._drift_history.clear()
        logger.info("MetaSupervisor state reset")
