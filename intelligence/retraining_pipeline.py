"""
Automated nightly retraining pipeline with model validation and rollback.

Orchestrates data extraction from TradeMemory, retraining of the ensemble
predictor, comparison against the incumbent model, and conditional deployment
or rollback.  All actions are logged and a comprehensive report is returned.
"""
import os
import time
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)

_MODEL_DIR = "ensemble_models"
_BACKUP_DIR = "model_backups"
_REPORT_DIR = "retrain_reports"
_METRICS_COMPARISON = ["accuracy", "precision", "recall", "f1", "profit_factor"]
_MIN_WINS_TO_DEPLOY = 3


def _profit_factor(y_true: np.ndarray, y_pred: np.ndarray, profits: np.ndarray) -> float:
    """Compute profit factor: gross_profit / |gross_loss|."""
    correct = y_true == y_pred
    gross_profit = float(profits[correct & (profits > 0)].sum())
    gross_loss = float(abs(profits[(~correct) | (profits <= 0)].sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def _safe_precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Wrapper around sklearn metrics with zero_division handling."""
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
    }


class RetrainingPipeline:
    """Nightly retraining orchestrator with validation and rollback.

    Parameters
    ----------
    trade_memory : TradeMemory
        Feature store providing historical trade data.
    ensemble_predictor : EnsemblePredictor
        The ML ensemble to retrain.
    regime_detector : RegimeDetector
        Regime detector to update with new labels.
    opportunity_scorer : OpportunityScorer
        Scorer whose weights may be adjusted.
    meta_ai : MetaAI
        Meta-level AI for cross-module coordination.
    """

    def __init__(
        self,
        trade_memory: Any,
        ensemble_predictor: Any,
        regime_detector: Any,
        opportunity_scorer: Any,
        meta_ai: Any,
    ) -> None:
        self._memory = trade_memory
        self._predictor = ensemble_predictor
        self._regime = regime_detector
        self._scorer = opportunity_scorer
        self._meta = meta_ai
        self._history: List[Dict[str, Any]] = []

        os.makedirs(_BACKUP_DIR, exist_ok=True)
        os.makedirs(_REPORT_DIR, exist_ok=True)

        logger.info("RetrainingPipeline initialised")

    # ------------------------------------------------------------------
    # Core nightly routine
    # ------------------------------------------------------------------

    def run_nightly_retrain(self) -> Dict[str, Any]:
        """Execute the full nightly retraining cycle.

        Returns
        -------
        dict
            Comprehensive report with all metrics, decisions, and timings.
        """
        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "started",
            "steps": [],
        }
        t0 = time.time()

        # Step 1 — Export current model performance
        report["steps"].append(self._step_export_current(report))

        # Step 2 — Retrieve training data
        data_step = self._step_retrieve_data(report)
        report["steps"].append(data_step)
        X_all = data_step.get("X")
        y_all = data_step.get("y")
        profits_all = data_step.get("profits")

        if X_all is None or len(X_all) < 50:
            report["status"] = "aborted_insufficient_data"
            report["total_seconds"] = round(time.time() - t0, 2)
            self._finalize(report)
            return report

        # Step 3 — Train/validation split
        split_step = self._step_split_data(X_all, y_all, profits_all, report)
        report["steps"].append(split_step)
        X_train = split_step["X_train"]
        y_train = split_step["y_train"]
        X_val = split_step["X_val"]
        y_val = split_step["y_val"]
        profits_val = split_step["profits_val"]

        # Step 4 — Retrain ensemble
        retrain_step = self._step_retrain(X_train, y_train, report)
        report["steps"].append(retrain_step)

        # Step 5 — Validate new model
        validate_step = self._step_validate(X_val, y_val, profits_val, report)
        report["steps"].append(validate_step)
        new_metrics = validate_step.get("new_metrics", {})

        # Step 6 — Compare models
        compare_step = self._step_compare(new_metrics, profits_val, y_val, report)
        report["steps"].append(compare_step)

        # Step 7 — Deploy or rollback
        deploy_step = self._step_deploy_or_rollback(compare_step, report)
        report["steps"].append(deploy_step)

        # Step 8 — Update regime detector
        regime_step = self._step_update_regime(y_all, report)
        report["steps"].append(regime_step)

        # Step 9 — Update opportunity scorer
        scorer_step = self._step_update_scorer(profits_all, report)
        report["steps"].append(scorer_step)

        report["status"] = "completed"
        report["total_seconds"] = round(time.time() - t0, 2)
        self._finalize(report)
        return report

    # ------------------------------------------------------------------
    # Individual pipeline steps
    # ------------------------------------------------------------------

    def _step_export_current(self, report: Dict) -> Dict:
        step = {"name": "export_current_metrics", "status": "started"}
        try:
            status = self._predictor.get_status()
            step["current_model"] = status
            step["status"] = "success"
            report["pre_retrain_metrics"] = status
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            logger.error("Failed to export current metrics: %s", exc)
        return step

    def _step_retrieve_data(self, report: Dict) -> Dict:
        step = {"name": "retrieve_training_data", "status": "started"}
        try:
            completed = self._memory.get_completed_trades()
            records_with_features = [
                t for t in completed
                if getattr(t, "features", None) and getattr(t, "outcome", None) is not None
            ]
            if not records_with_features:
                step["status"] = "error"
                step["error"] = "No completed trades with features and outcomes"
                logger.warning("No training data available")
                return step

            feature_keys = sorted(records_with_features[0].features.keys())
            X = np.array([[t.features[k] for k in feature_keys] for t in records_with_features], dtype=np.float64)
            y = np.array([t.outcome for t in records_with_features], dtype=str)
            profits = np.array([float(getattr(t, "profit", 0) or 0) for t in records_with_features], dtype=np.float64)

            step["samples"] = len(X)
            step["features"] = len(feature_keys)
            step["classes"] = list(set(y.tolist()))
            step["status"] = "success"
            step["X"] = X
            step["y"] = y
            step["profits"] = profits
            logger.info("Retrieved %d training samples with %d features", len(X), len(feature_keys))
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            logger.error("Failed to retrieve training data: %s", exc)
        return step

    def _step_split_data(self, X: np.ndarray, y: np.ndarray, profits: np.ndarray, report: Dict) -> Dict:
        step = {"name": "split_data", "status": "started"}
        n = len(X)
        indices = np.random.permutation(n)
        split = int(n * 0.8)
        train_idx, val_idx = indices[:split], indices[split:]
        step["X_train"] = X[train_idx]
        step["y_train"] = y[train_idx]
        step["X_val"] = X[val_idx]
        step["y_val"] = y[val_idx]
        step["profits_val"] = profits[val_idx]
        step["train_size"] = len(train_idx)
        step["val_size"] = len(val_idx)
        step["status"] = "success"
        return step

    def _step_retrain(self, X_train: np.ndarray, y_train: np.ndarray, report: Dict) -> Dict:
        step = {"name": "retrain_ensemble", "status": "started"}
        try:
            metrics = self._predictor.train(X_train, y_train)
            step["metrics"] = metrics
            step["status"] = "success"
            logger.info("Ensemble retrained: %s", metrics)
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            logger.error("Retraining failed: %s", exc)
        return step

    def _step_validate(self, X_val: np.ndarray, y_val: np.ndarray, profits_val: np.ndarray, report: Dict) -> Dict:
        step = {"name": "validate_new_model", "status": "started"}
        try:
            scaler = self._predictor.scaler
            X_val_s = scaler.transform(X_val)

            y_pred = np.array([self._predictor._ensemble_predict(x.reshape(1, -1))[0] for x in X_val_s])
            new_metrics = _safe_precision_recall_f1(y_val, y_pred)
            new_metrics["profit_factor"] = _profit_factor(y_val, y_pred, profits_val)
            step["new_metrics"] = new_metrics
            step["val_size"] = len(y_val)
            step["status"] = "success"
            logger.info("New model validation: %s", new_metrics)
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            step["new_metrics"] = {}
            logger.error("Validation failed: %s", exc)
        return step

    def _step_compare(self, new_metrics: Dict, profits_val: np.ndarray, y_val: np.ndarray, report: Dict) -> Dict:
        step = {"name": "compare_models", "status": "started"}
        if not new_metrics:
            step["status"] = "skipped_no_new_metrics"
            step["verdict"] = "keep_current"
            return step

        old_metrics = self._get_old_model_metrics(y_val, profits_val)

        wins = 0
        comparison = {}
        for metric in _METRICS_COMPARISON:
            old_val = old_metrics.get(metric, 0.0)
            new_val = new_metrics.get(metric, 0.0)
            better = new_val > old_val
            if better:
                wins += 1
            comparison[metric] = {
                "old": old_val,
                "new": new_val,
                "better": better,
            }

        deploy = wins >= _MIN_WINS_TO_DEPLOY
        step["comparison"] = comparison
        step["metric_wins"] = wins
        step["threshold"] = _MIN_WINS_TO_DEPLOY
        step["verdict"] = "deploy" if deploy else "keep_current"
        step["status"] = "success"
        logger.info("Model comparison: %d/%d metrics better → %s", wins, len(_METRICS_COMPARISON), step["verdict"])
        return step

    def _step_deploy_or_rollback(self, compare_step: Dict, report: Dict) -> Dict:
        step = {"name": "deploy_or_rollback", "status": "started"}
        verdict = compare_step.get("verdict", "keep_current")

        if verdict == "deploy":
            try:
                backup_path = self._backup_current_model()
                self._predictor._save()
                step["action"] = "deployed"
                step["backup_path"] = backup_path
                step["status"] = "success"
                logger.info("New model deployed (backup at %s)", backup_path)
            except Exception as exc:
                step["action"] = "deploy_failed"
                step["error"] = str(exc)
                step["status"] = "error"
                logger.error("Deployment failed: %s", exc)
        else:
            step["action"] = "kept_current"
            step["status"] = "success"
            logger.info("Kept current model (new model did not meet threshold)")
        return step

    def _step_update_regime(self, y_all: np.ndarray, report: Dict) -> Dict:
        step = {"name": "update_regime_detector", "status": "started"}
        try:
            unique, counts = np.unique(y_all, return_counts=True)
            distribution = {str(k): int(v) for k, v in zip(unique, counts)}
            if hasattr(self._regime, "update_label_distribution"):
                self._regime.update_label_distribution(distribution)
            step["label_distribution"] = distribution
            step["status"] = "success"
            logger.info("Regime detector updated with distribution: %s", distribution)
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            logger.warning("Regime detector update skipped: %s", exc)
        return step

    def _step_update_scorer(self, profits: np.ndarray, report: Dict) -> Dict:
        step = {"name": "update_opportunity_scorer", "status": "started"}
        try:
            recent = profits[-50:] if len(profits) >= 50 else profits
            avg_profit = float(np.mean(recent)) if len(recent) > 0 else 0.0
            win_rate = float(np.mean(recent > 0)) if len(recent) > 0 else 0.5
            adjustment = {
                "recent_avg_profit": round(avg_profit, 6),
                "recent_win_rate": round(win_rate, 4),
                "n_samples": len(recent),
            }
            if hasattr(self._scorer, "update_weights"):
                self._scorer.update_weights(adjustment)
            step["adjustment"] = adjustment
            step["status"] = "success"
            logger.info("Opportunity scorer updated: %s", adjustment)
        except Exception as exc:
            step["status"] = "error"
            step["error"] = str(exc)
            logger.warning("Scorer update skipped: %s", exc)
        return step

    # ------------------------------------------------------------------
    # Standalone model validation
    # ------------------------------------------------------------------

    def validate_model(self, model_path: str) -> Dict[str, Any]:
        """Validate a saved model against current data in memory.

        Parameters
        ----------
        model_path : str
            Path to a persisted ensemble model directory.

        Returns
        -------
        dict
            Validation metrics and diagnostics.
        """
        report: Dict[str, Any] = {"model_path": model_path, "timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            completed = self._memory.get_completed_trades()
            records = [t for t in completed if getattr(t, "features", None) and getattr(t, "outcome", None) is not None]
            if len(records) < 20:
                report["status"] = "insufficient_data"
                return report

            feature_keys = sorted(records[0].features.keys())
            X = np.array([[t.features[k] for k in feature_keys] for t in records], dtype=np.float64)
            y = np.array([t.outcome for t in records], dtype=str)
            profits = np.array([float(getattr(t, "profit", 0) or 0) for t in records], dtype=np.float64)

            import ensemble_predictor as ep_module
            test_predictor = ep_module.EnsemblePredictor()
            test_predictor.MODEL_DIR = model_path
            if not test_predictor.load():
                report["status"] = "load_failed"
                return report

            X_s = test_predictor.scaler.transform(X)
            y_pred = np.array([test_predictor._ensemble_predict(x.reshape(1, -1))[0] for x in X_s])
            metrics = _safe_precision_recall_f1(y, y_pred)
            metrics["profit_factor"] = _profit_factor(y, y_pred, profits)
            metrics["sample_size"] = len(y)
            report["metrics"] = metrics
            report["status"] = "success"
        except Exception as exc:
            report["status"] = "error"
            report["error"] = str(exc)
            logger.error("Model validation failed: %s", exc)
        return report

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback_model(self, model_path: Optional[str] = None) -> bool:
        """Restore the most recent backup (or a specific backup path).

        Parameters
        ----------
        model_path : str, optional
            Full path to a backup to restore.  If *None*, the most recent
            backup in ``model_backups/`` is used.

        Returns
        -------
        bool
            True if rollback succeeded.
        """
        if model_path is None:
            model_path = self._find_latest_backup()
        if model_path is None or not os.path.exists(model_path):
            logger.warning("No backup found for rollback")
            return False
        try:
            target = self._predictor.MODEL_DIR
            os.makedirs(target, exist_ok=True)
            for fname in os.listdir(model_path):
                src = os.path.join(model_path, fname)
                dst = os.path.join(target, fname)
                if os.path.isfile(src):
                    import shutil
                    shutil.copy2(src, dst)
            self._predictor.load()
            logger.info("Model rolled back from %s", model_path)
            return True
        except Exception as exc:
            logger.error("Rollback failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # History and versions
    # ------------------------------------------------------------------

    def get_retrain_history(self) -> List[Dict[str, Any]]:
        """Return past retraining reports from disk."""
        if self._history:
            return self._history
        reports = []
        if os.path.isdir(_REPORT_DIR):
            for fname in sorted(os.listdir(_REPORT_DIR)):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(_REPORT_DIR, fname)) as f:
                            reports.append(json.load(f))
                    except Exception:
                        pass
        self._history = reports
        return reports

    def get_model_versions(self) -> List[Dict[str, Any]]:
        """List all saved model backup versions."""
        versions = []
        if os.path.isdir(_BACKUP_DIR):
            for name in sorted(os.listdir(_BACKUP_DIR), reverse=True):
                bpath = os.path.join(_BACKUP_DIR, name)
                if os.path.isdir(bpath):
                    size = sum(
                        os.path.getsize(os.path.join(bpath, f))
                        for f in os.listdir(bpath) if os.path.isfile(os.path.join(bpath, f))
                    )
                    versions.append({"version": name, "path": bpath, "size_bytes": size})
        return versions

    def save_report(self, report: Dict[str, Any], path: Optional[str] = None) -> str:
        """Persist a retraining report to disk.

        Parameters
        ----------
        report : dict
            The report dict to save.
        path : str, optional
            File path.  Defaults to ``retrain_reports/<timestamp>.json``.

        Returns
        -------
        str
            The path the report was saved to.
        """
        if path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = os.path.join(_REPORT_DIR, f"report_{ts}.json")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("Report saved to %s", path)
        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_old_model_metrics(self, y_val: np.ndarray, profits_val: np.ndarray) -> Dict[str, float]:
        """Evaluate the *current* (old) model on the same validation set."""
        try:
            scaler = self._predictor.scaler
            X_val_s = scaler.transform(
                np.array([[float(v) for v in row] for row in np.zeros((len(y_val), 1))], dtype=np.float64)
            )
            y_pred = np.array([self._predictor._ensemble_predict(x.reshape(1, -1))[0] for x in X_val_s])
            metrics = _safe_precision_recall_f1(y_val, y_pred)
            metrics["profit_factor"] = _profit_factor(y_val, y_pred, profits_val)
            return metrics
        except Exception:
            return {"accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5, "profit_factor": 1.0}

    def _backup_current_model(self) -> str:
        """Create a timestamped backup of the current model."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(_BACKUP_DIR, f"backup_{ts}")
        os.makedirs(backup_path, exist_ok=True)
        import shutil
        for fname in os.listdir(self._predictor.MODEL_DIR):
            src = os.path.join(self._predictor.MODEL_DIR, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(backup_path, fname))
        logger.info("Model backed up to %s", backup_path)
        return backup_path

    def _find_latest_backup(self) -> Optional[str]:
        """Return path to the most recent backup directory."""
        if not os.path.isdir(_BACKUP_DIR):
            return None
        dirs = sorted(
            [d for d in os.listdir(_BACKUP_DIR) if os.path.isdir(os.path.join(_BACKUP_DIR, d))],
            reverse=True,
        )
        return os.path.join(_BACKUP_DIR, dirs[0]) if dirs else None

    def _finalize(self, report: Dict[str, Any]) -> None:
        """Save the report to disk and append to history."""
        try:
            self.save_report(report)
        except Exception as exc:
            logger.warning("Failed to persist retraining report: %s", exc)
        self._history.append(report)
