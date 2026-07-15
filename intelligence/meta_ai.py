"""
Meta-AI — Analyzer Performance Evaluator & Ensemble Weight Tuner.

Continuously evaluates each analyzer's predictive accuracy, calibration,
and consistency, then adjusts ensemble weights automatically so the
highest-performing analyzers contribute more to the consensus vote.
"""

import logging
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BUFFER_MAX = 1000          # circular-buffer size per analyzer
_MIN_WEIGHT = 0.02          # floor so no analyzer is completely silenced
_MAX_WEIGHT = 0.25          # cap so no single analyzer dominates
_DEFAULT_WEIGHT = 0.10      # starting weight for unknown analyzers
_DEGRADATION_WINDOW = 50    # default window for degradation detection

# Weight-composition coefficients (must sum to 1.0)
_COEF_WIN_RATE = 0.40
_COEF_PROFIT = 0.30
_COEF_CALIBRATION = 0.20
_COEF_CONSISTENCY = 0.10


class MetaAI:
    """Evaluates analyzer performance and tunes ensemble weights automatically.

    Parameters
    ----------
    analysis_manager : AnalysisManager
        Reference to the central analysis manager so weights can be pushed
        back when ``adjust_weights()`` is called.
    trade_memory : TradeMemory
        Persistent trade memory used for historical look-ups when needed.
    """

    def __init__(self, analysis_manager: Any, trade_memory: Any):
        self.analysis_manager = analysis_manager
        self.trade_memory = trade_memory

        # Per-analyzer tracking state
        self._predictions: Dict[str, deque] = {}
        self._confidences: Dict[str, deque] = {}
        self._correct_flags: Dict[str, deque] = {}
        self._profits: Dict[str, deque] = {}
        self._weight_history: List[Dict[str, float]] = []

        self._current_weights: Dict[str, float] = {}
        self._total_evaluations: int = 0
        self._total_correct: int = 0
        self._creation_time: float = time.time()

        logger.info("MetaAI initialized")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_analyzer(self, analyzer_name: str) -> None:
        """Lazily create circular buffers for a new analyzer."""
        if analyzer_name not in self._predictions:
            self._predictions[analyzer_name] = deque(maxlen=_BUFFER_MAX)
            self._confidences[analyzer_name] = deque(maxlen=_BUFFER_MAX)
            self._correct_flags[analyzer_name] = deque(maxlen=_BUFFER_MAX)
            self._profits[analyzer_name] = deque(maxlen=_BUFFER_MAX)
            logger.debug("Created tracking buffers for analyzer: %s", analyzer_name)

    @staticmethod
    def _normalize(values: np.ndarray) -> np.ndarray:
        """Min-max normalize an array to [0, 1]. Handles constant arrays."""
        if len(values) == 0:
            return values
        mn, mx = values.min(), values.max()
        if mx - mn < 1e-12:
            return np.full_like(values, 0.5)
        return (values - mn) / (mx - mn)

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    def evaluate_analyzer(
        self,
        analyzer_name: str,
        prediction: dict,
        actual_outcome: str,
        confidence: float,
    ) -> None:
        """Record a single evaluation for an analyzer.

        Parameters
        ----------
        analyzer_name : str
            Identifier of the analyzer (e.g. ``"even_odd"``).
        prediction : dict
            The analyzer's prediction dict (must contain at least a
            ``"direction"`` key whose value is compared against
            *actual_outcome*).
        actual_outcome : str
            Ground-truth outcome string (e.g. ``"CALL"``, ``"PUT"``).
        confidence : float
            Confidence value (0–100 scale) the analyzer reported.
        """
        self._ensure_analyzer(analyzer_name)

        pred_direction = str(prediction.get("direction", "")).upper()
        actual_upper = str(actual_outcome).upper()

        # Determine correctness — check whether actual outcome appears in the
        # prediction direction (handles variations like "RISE" vs "CALL").
        is_correct = self._outcomes_match(pred_direction, actual_upper)

        self._predictions[analyzer_name].append(pred_direction)
        self._confidences[analyzer_name].append(float(confidence))
        self._correct_flags[analyzer_name].append(1.0 if is_correct else 0.0)

        self._total_evaluations += 1
        if is_correct:
            self._total_correct += 1

        logger.info(
            "Evaluated %s | pred=%s actual=%s correct=%s conf=%.1f",
            analyzer_name, pred_direction, actual_upper, is_correct, confidence,
        )

    def evaluate_analyzer_with_profit(
        self,
        analyzer_name: str,
        prediction: dict,
        actual_outcome: str,
        confidence: float,
        profit: float,
    ) -> None:
        """Like ``evaluate_analyzer`` but also records the trade profit/loss."""
        self.evaluate_analyzer(analyzer_name, prediction, actual_outcome, confidence)
        self._ensure_analyzer(analyzer_name)
        self._profits[analyzer_name].append(float(profit))

    @staticmethod
    def _outcomes_match(predicted: str, actual: str) -> bool:
        """Check if a predicted direction matches the actual outcome."""
        bullish = {"CALL", "RISE", "EVEN", "OVER"}
        bearish = {"PUT", "FALL", "ODD", "UNDER"}
        pred_cat = "BULL" if any(k in predicted for k in bullish) else "BEAR"
        act_cat = "BULL" if any(k in actual for k in bullish) else "BEAR"
        return pred_cat == act_cat

    # ------------------------------------------------------------------
    # Weight calculation
    # ------------------------------------------------------------------

    def get_analyzer_weights(self) -> Dict[str, float]:
        """Return the current optimal weights for each tracked analyzer.

        Returns
        -------
        dict[str, float]
            Mapping of analyzer name → weight. Weights are normalized so
            they sum to 1.0.
        """
        self.adjust_weights()
        if not self._current_weights:
            return {}
        total = sum(self._current_weights.values())
        if total < 1e-12:
            return {k: 1.0 / len(self._current_weights) for k in self._current_weights}
        return {k: v / total for k, v in self._current_weights.items()}

    def adjust_weights(self) -> Dict[str, float]:
        """Recalculate weights based on accumulated performance metrics.

        The composite weight for each analyzer is::

            W = 0.40 × win_rate + 0.30 × profit_contribution
              + 0.20 × calibration + 0.10 × consistency

        All sub-scores are first normalized across analyzers to [0, 1].
        A floor of ``_MIN_WEIGHT`` and cap of ``_MAX_WEIGHT`` are applied.

        Returns
        -------
        dict[str, float]
            The updated weight mapping.
        """
        analyzers = list(self._predictions.keys())
        if not analyzers:
            logger.debug("No analyzers tracked yet — skipping weight adjustment")
            return self._current_weights

        win_rates = []
        profit_contribs = []
        calibrations = []
        consistencies = []

        for name in analyzers:
            correct = np.array(self._correct_flags[name])
            confs = np.array(self._confidences[name])

            # --- Win rate ---
            wr = float(correct.mean()) if len(correct) > 0 else 0.0
            win_rates.append(wr)

            # --- Profit contribution ---
            profs = np.array(self._profits[name]) if self._profits[name] else np.array([0.0])
            pc = float(profs.sum()) if len(profs) > 0 else 0.0
            profit_contribs.append(pc)

            # --- Calibration (Brier-like: how close confidence is to correctness) ---
            if len(confs) > 0 and len(correct) > 0:
                conf_01 = np.clip(confs / 100.0, 0.0, 1.0)
                # Lower is better for Brier score → invert for weight
                brier = float(np.mean((conf_01 - correct) ** 2))
                calibration = 1.0 - brier  # higher is better
            else:
                calibration = 0.5
            calibrations.append(calibration)

            # --- Consistency (lower variance of recent predictions → higher) ---
            if len(correct) >= 5:
                recent = correct[-min(50, len(correct)):]
                # Use proportion of agreement with majority direction as proxy
                majority_frac = max(recent.mean(), 1.0 - recent.mean())
                consistency = float(majority_frac)
            else:
                consistency = 0.5
            consistencies.append(consistency)

        # Normalize all vectors
        wr_arr = self._normalize(np.array(win_rates))
        pc_arr = self._normalize(np.array(profit_contribs))
        cal_arr = self._normalize(np.array(calibrations))
        con_arr = self._normalize(np.array(consistencies))

        weights = {}
        for i, name in enumerate(analyzers):
            raw = (
                _COEF_WIN_RATE * wr_arr[i]
                + _COEF_PROFIT * pc_arr[i]
                + _COEF_CALIBRATION * cal_arr[i]
                + _COEF_CONSISTENCY * con_arr[i]
            )
            weights[name] = self._clamp(raw, _MIN_WEIGHT, _MAX_WEIGHT)

        # Normalize to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        self._current_weights = weights
        self._weight_history.append(dict(weights))

        # Push updated weights into the analysis manager
        if self.analysis_manager is not None:
            try:
                self.analysis_manager.update_weights(weights)
            except Exception as exc:
                logger.warning("Failed to push weights to analysis_manager: %s", exc)

        logger.info("Adjusted weights: %s", {k: round(v, 4) for k, v in weights.items()})
        return weights

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_analyzer_report(self) -> Dict[str, Dict[str, Any]]:
        """Return detailed per-analyzer performance metrics.

        Returns
        -------
        dict
            ``{analyzer_name: {win_rate, total_predictions, correct,
            avg_confidence_when_correct, avg_confidence_when_wrong,
            profit_contribution, current_weight, ...}}``
        """
        report: Dict[str, Dict[str, Any]] = {}
        for name in self._predictions:
            correct = np.array(self._correct_flags[name])
            confs = np.array(self._confidences[name])
            profs = (
                np.array(self._profits[name])
                if self._profits[name]
                else np.array([0.0])
            )

            n = len(correct)
            n_correct = int(correct.sum()) if n > 0 else 0
            win_rate = n_correct / n if n > 0 else 0.0

            if n > 0:
                mask_correct = correct == 1.0
                mask_wrong = correct == 0.0
                avg_conf_correct = (
                    float(confs[mask_correct].mean()) if mask_correct.any() else 0.0
                )
                avg_conf_wrong = (
                    float(confs[mask_wrong].mean()) if mask_wrong.any() else 0.0
                )
            else:
                avg_conf_correct = 0.0
                avg_conf_wrong = 0.0

            # Prediction agreement with overall outcome (last known)
            agreement = 0.0
            if n >= 2:
                recent = correct[-min(50, n):]
                agreement = float(recent.mean())

            report[name] = {
                "win_rate": round(win_rate, 4),
                "total_predictions": n,
                "correct": n_correct,
                "wrong": n - n_correct,
                "avg_confidence_when_correct": round(avg_conf_correct, 2),
                "avg_confidence_when_wrong": round(avg_conf_wrong, 2),
                "profit_contribution": round(float(profs.sum()), 4),
                "avg_profit": round(float(profs.mean()), 4) if len(profs) > 0 else 0.0,
                "current_weight": round(self._current_weights.get(name, 0.0), 4),
                "prediction_agreement_with_outcome": round(agreement, 4),
            }

        return report

    def get_meta_stats(self) -> Dict[str, Any]:
        """Return overall Meta-AI system performance statistics.

        Returns
        -------
        dict
            Includes ``total_evaluations``, ``overall_win_rate``,
            ``active_analyzers``, ``weight_stability``, ``uptime_hours``,
            and ``recommendation_quality``.
        """
        uptime_h = (time.time() - self._creation_time) / 3600.0
        overall_wr = (
            self._total_correct / self._total_evaluations
            if self._total_evaluations > 0
            else 0.0
        )

        # Weight stability — standard deviation of weights in recent history
        weight_stability = 0.0
        if len(self._weight_history) >= 5:
            recent = self._weight_history[-50:]
            all_names = sorted({k for snap in recent for k in snap})
            if all_names:
                matrices = np.array([
                    [snap.get(a, 0.0) for a in all_names] for snap in recent
                ])
                weight_stability = float(1.0 - matrices.std(axis=0).mean())
                weight_stability = max(0.0, min(1.0, weight_stability))

        # Recommendation quality — average win rate across all analyzers
        rec_quality = 0.0
        report = self.get_analyzer_report()
        if report:
            rec_quality = float(np.mean([v["win_rate"] for v in report.values()]))

        return {
            "total_evaluations": self._total_evaluations,
            "overall_win_rate": round(overall_wr, 4),
            "active_analyzers": len(self._predictions),
            "weight_snapshots_taken": len(self._weight_history),
            "weight_stability": round(weight_stability, 4),
            "recommendation_quality": round(rec_quality, 4),
            "uptime_hours": round(uptime_h, 2),
        }

    # ------------------------------------------------------------------
    # Degradation detection
    # ------------------------------------------------------------------

    def detect_analyzer_degradation(
        self,
        window: int = _DEGRADATION_WINDOW,
    ) -> Dict[str, Dict[str, Any]]:
        """Detect analyzers whose recent performance has degraded.

        Parameters
        ----------
        window : int
            Number of recent evaluations to consider for the "recent" metric.

        Returns
        -------
        dict
            ``{analyzer_name: {is_degraded, recent_win_rate,
            historical_win_rate, recommendation}}``
        """
        results: Dict[str, Dict[str, Any]] = {}
        for name, buf in self._correct_flags.items():
            arr = np.array(buf)
            n = len(arr)
            if n < window:
                results[name] = {
                    "is_degraded": False,
                    "recent_win_rate": round(float(arr.mean()), 4) if n > 0 else 0.0,
                    "historical_win_rate": round(float(arr.mean()), 4) if n > 0 else 0.0,
                    "recommendation": "insufficient_data",
                }
                continue

            historical_wr = float(arr.mean())
            recent_wr = float(arr[-window:].mean())

            # Degradation = recent WR at least 15pp below historical
            is_degraded = recent_wr < (historical_wr - 0.15)

            if is_degraded:
                deficit = historical_wr - recent_wr
                if deficit > 0.30:
                    rec = "disable"
                elif deficit > 0.20:
                    rec = "reduce_weight_and_monitor"
                else:
                    rec = "monitor_closely"
            else:
                rec = "performing_normally"

            results[name] = {
                "is_degraded": is_degraded,
                "recent_win_rate": round(recent_wr, 4),
                "historical_win_rate": round(historical_wr, 4),
                "recommendation": rec,
            }

        return results

    def suggest_analyzer_changes(self) -> List[Dict[str, Any]]:
        """Suggest enables/disables based on accumulated performance.

        Returns
        -------
        list[dict]
            Each dict has keys ``analyzer``, ``action`` (``"disable"``,
            ``"reduce_weight"``, ``"enable"``, ``"no_change"``), and
            ``reason``.
        """
        suggestions: List[Dict[str, Any]] = []
        degradation = self.detect_analyzer_degradation()
        report = self.get_analyzer_report()

        for name, info in degradation.items():
            metrics = report.get(name, {})
            wr = info["recent_win_rate"]
            n = metrics.get("total_predictions", 0)

            if n < 30:
                suggestions.append({
                    "analyzer": name,
                    "action": "no_change",
                    "reason": f"Insufficient data ({n} predictions)",
                })
                continue

            if info["is_degraded"]:
                rec = info["recommendation"]
                if rec == "disable":
                    suggestions.append({
                        "analyzer": name,
                        "action": "disable",
                        "reason": (
                            f"Win rate degraded from {info['historical_win_rate']:.1%} "
                            f"to {info['recent_win_rate']:.1%}"
                        ),
                    })
                elif rec == "reduce_weight_and_monitor":
                    suggestions.append({
                        "analyzer": name,
                        "action": "reduce_weight",
                        "reason": (
                            f"Moderate degradation: {info['recent_win_rate']:.1%} recent "
                            f"vs {info['historical_win_rate']:.1%} historical"
                        ),
                    })
                else:
                    suggestions.append({
                        "analyzer": name,
                        "action": "no_change",
                        "reason": "Minor fluctuation — monitoring",
                    })
            elif wr >= 0.60 and metrics.get("current_weight", 0) < 0.08:
                suggestions.append({
                    "analyzer": name,
                    "action": "increase_weight",
                    "reason": f"Strong win rate ({wr:.1%}) with low weight",
                })
            else:
                suggestions.append({
                    "analyzer": name,
                    "action": "no_change",
                    "reason": f"Performing within normal range (WR={wr:.1%})",
                })

        return suggestions

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist the MetaAI state to disk via joblib.

        Parameters
        ----------
        path : str
            File path for the serialized state.
        """
        state = {
            "_predictions": dict(self._predictions),
            "_confidences": dict(self._confidences),
            "_correct_flags": dict(self._correct_flags),
            "_profits": dict(self._profits),
            "_weight_history": self._weight_history,
            "_current_weights": self._current_weights,
            "_total_evaluations": self._total_evaluations,
            "_total_correct": self._total_correct,
            "_creation_time": self._creation_time,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(state, path)
        logger.info("MetaAI state saved to %s", path)

    def load(self, path: str) -> None:
        """Restore MetaAI state from a previously saved file.

        Parameters
        ----------
        path : str
            File path to load from.
        """
        state = joblib.load(path)
        self._predictions = state["_predictions"]
        self._confidences = state["_confidences"]
        self._correct_flags = state["_correct_flags"]
        self._profits = state["_profits"]
        self._weight_history = state["_weight_history"]
        self._current_weights = state["_current_weights"]
        self._total_evaluations = state["_total_evaluations"]
        self._total_correct = state["_total_correct"]
        self._creation_time = state["_creation_time"]
        logger.info("MetaAI state loaded from %s", path)

    def reset(self) -> None:
        """Clear all tracking data and reset to initial state."""
        self._predictions.clear()
        self._confidences.clear()
        self._correct_flags.clear()
        self._profits.clear()
        self._weight_history.clear()
        self._current_weights.clear()
        self._total_evaluations = 0
        self._total_correct = 0
        self._creation_time = time.time()
        logger.info("MetaAI state reset")
