"""
Ensemble predictor: voting ensemble of RF + GBM with calibrated probabilities,
incremental learning from live trade outcomes, and per-model confidence tracking.
"""
import numpy as np
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from collections import deque
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, brier_score_loss
import joblib

from models import Prediction

logger = logging.getLogger(__name__)


class ModelTracker:
    """Tracks per-model accuracy on live trades for adaptive weighting."""

    def __init__(self, window: int = 50):
        self.window = window
        self.results: Dict[str, deque] = {}
        self.weights: Dict[str, float] = {}

    def record(self, model_name: str, predicted: str, actual: str):
        if model_name not in self.results:
            self.results[model_name] = deque(maxlen=self.window)
        self.results[model_name].append(1 if predicted == actual else 0)
        self._update_weight(model_name)

    def _update_weight(self, model_name: str):
        hist = list(self.results[model_name])
        if len(hist) < 5:
            self.weights[model_name] = 1.0
        else:
            wr = sum(hist) / len(hist)
            # Weight between 0.3 and 2.0 based on win rate around 50%
            self.weights[model_name] = max(0.3, min(2.0, wr / 0.5))

    def get_weight(self, model_name: str) -> float:
        return self.weights.get(model_name, 1.0)

    def get_summary(self) -> Dict[str, Any]:
        summary = {}
        for name, hist in self.results.items():
            if hist:
                summary[name] = {
                    "samples": len(hist),
                    "win_rate": round(sum(hist) / len(hist) * 100, 1),
                    "weight": round(self.get_weight(name), 3),
                }
        return summary


class EnsemblePredictor:
    """
    Soft-voting ensemble: RandomForest + GradientBoosting + LogisticRegression.
    Each model's vote is weighted by its live-trade accuracy via ModelTracker.
    Supports incremental learning by retraining on batched live outcomes.
    """

    CLASSES = ["CALL", "PUT"]
    MODEL_DIR = "ensemble_models"

    def __init__(self):
        self.scaler = StandardScaler()
        self.tracker = ModelTracker(window=60)
        self.is_trained = False

        self.models: Dict[str, Any] = {
            "rf": RandomForestClassifier(
                n_estimators=200, max_depth=12, min_samples_leaf=3,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "gbm": GradientBoostingClassifier(
                n_estimators=150, max_depth=5, learning_rate=0.05,
                subsample=0.8, random_state=42
            ),
            "lr": LogisticRegression(
                C=1.0, max_iter=500, class_weight="balanced", random_state=42
            ),
        }
        self.calibrated: Dict[str, Any] = {}

        # Replay buffer for incremental learning
        self._live_X: List[np.ndarray] = []
        self._live_y: List[str] = []
        self._incremental_threshold = 30

        self._ensure_model_dir()

    def _ensure_model_dir(self):
        os.makedirs(self.MODEL_DIR, exist_ok=True)

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Full training from historical data."""
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None)
        X_tr_s = self.scaler.fit_transform(X_tr)
        X_te_s = self.scaler.transform(X_te)

        metrics = {}
        for name, model in self.models.items():
            model.fit(X_tr_s, y_tr)
            cal = CalibratedClassifierCV(model, cv="prefit", method="isotonic")
            cal.fit(X_tr_s, y_tr)
            self.calibrated[name] = cal
            preds = cal.predict(X_te_s)
            acc = accuracy_score(y_te, preds)
            proba = cal.predict_proba(X_te_s)
            classes = list(cal.classes_)
            call_idx = classes.index("CALL") if "CALL" in classes else 0
            brier = brier_score_loss(y_te == "CALL", proba[:, call_idx])
            metrics[name] = {"accuracy": round(acc, 4), "brier": round(brier, 4)}
            logger.info("Ensemble model %s trained: acc=%.3f brier=%.4f", name, acc, brier)

        self.is_trained = True
        self._save()
        overall_acc = accuracy_score(y_te, self._ensemble_predict(X_te_s))
        return {"models": metrics, "ensemble_accuracy": round(overall_acc, 4), "train_size": len(X_tr), "test_size": len(X_te)}

    def predict(self, features: np.ndarray) -> Optional[Prediction]:
        if not self.is_trained or not self.calibrated:
            return None
        try:
            x_s = self.scaler.transform([features])
            direction, confidence, breakdown = self._soft_vote(x_s)
            reason = self._build_reason(breakdown)
            return Prediction(
                type="ENSEMBLE",
                direction=direction,
                confidence=round(confidence, 1),
                reason=reason,
            )
        except Exception as e:
            logger.warning("Ensemble predict error: %s", e)
            return None

    def _soft_vote(self, x_s: np.ndarray) -> Tuple[str, float, Dict]:
        """Adaptive soft voting weighted by live tracker accuracy."""
        call_score = 0.0
        put_score = 0.0
        total_weight = 0.0
        breakdown = {}

        for name, cal in self.calibrated.items():
            proba = cal.predict_proba(x_s)[0]
            classes = list(cal.classes_)
            call_idx = classes.index("CALL") if "CALL" in classes else 0
            put_idx = 1 - call_idx
            p_call = proba[call_idx]
            p_put = proba[put_idx]
            w = self.tracker.get_weight(name)
            call_score += p_call * w
            put_score += p_put * w
            total_weight += w
            breakdown[name] = {"call": round(p_call, 3), "put": round(p_put, 3), "weight": round(w, 2)}

        if total_weight == 0:
            total_weight = 1.0

        p_call_final = call_score / total_weight
        p_put_final = put_score / total_weight
        direction = "CALL" if p_call_final >= p_put_final else "PUT"
        confidence = max(p_call_final, p_put_final) * 100
        return direction, confidence, breakdown

    def _ensemble_predict(self, X_s: np.ndarray) -> np.ndarray:
        preds = []
        for x in X_s:
            d, _, _ = self._soft_vote(x.reshape(1, -1))
            preds.append(d)
        return np.array(preds)

    def _build_reason(self, breakdown: Dict) -> str:
        parts = []
        for name, info in breakdown.items():
            winner = "CALL" if info["call"] >= info["put"] else "PUT"
            confidence = max(info["call"], info["put"]) * 100
            parts.append(f"{name.upper()}→{winner}({confidence:.0f}%,w={info['weight']})")
        return "Ensemble: " + " | ".join(parts)

    def add_live_outcome(self, features: np.ndarray, actual_direction: str, model_predictions: Dict[str, str]):
        """Record live trade outcome for tracker + incremental buffer."""
        for model_name, predicted in model_predictions.items():
            self.tracker.record(model_name, predicted, actual_direction)

        self._live_X.append(features)
        self._live_y.append(actual_direction)

        if len(self._live_X) >= self._incremental_threshold:
            self._incremental_retrain()

    def _incremental_retrain(self):
        """Retrain on original + live data (if we have enough)."""
        if not self.is_trained or len(self._live_X) < 10:
            return
        try:
            X_live = np.array(self._live_X)
            y_live = np.array(self._live_y)
            X_live_s = self.scaler.transform(X_live)
            for name, model in self.models.items():
                if hasattr(model, "warm_start"):
                    model.set_params(warm_start=True)
                model.fit(X_live_s, y_live)
                cal = CalibratedClassifierCV(model, cv="prefit", method="isotonic")
                cal.fit(X_live_s, y_live)
                self.calibrated[name] = cal
            self._save()
            self._live_X.clear()
            self._live_y.clear()
            logger.info("Ensemble incrementally retrained on %d live samples", len(X_live))
        except Exception as e:
            logger.warning("Incremental retrain failed: %s", e)

    def _save(self):
        try:
            joblib.dump(self.scaler, os.path.join(self.MODEL_DIR, "scaler.pkl"))
            for name, cal in self.calibrated.items():
                joblib.dump(cal, os.path.join(self.MODEL_DIR, f"{name}_cal.pkl"))
            tracker_data = {"weights": self.tracker.weights}
            with open(os.path.join(self.MODEL_DIR, "tracker.json"), "w") as f:
                json.dump(tracker_data, f)
        except Exception as e:
            logger.warning("Ensemble save error: %s", e)

    def load(self) -> bool:
        try:
            scaler_path = os.path.join(self.MODEL_DIR, "scaler.pkl")
            if not os.path.exists(scaler_path):
                return False
            self.scaler = joblib.load(scaler_path)
            for name in self.models:
                cal_path = os.path.join(self.MODEL_DIR, f"{name}_cal.pkl")
                if os.path.exists(cal_path):
                    self.calibrated[name] = joblib.load(cal_path)
            tracker_path = os.path.join(self.MODEL_DIR, "tracker.json")
            if os.path.exists(tracker_path):
                with open(tracker_path) as f:
                    data = json.load(f)
                    self.tracker.weights = data.get("weights", {})
            if self.calibrated:
                self.is_trained = True
                logger.info("Ensemble loaded: %d models", len(self.calibrated))
                return True
        except Exception as e:
            logger.warning("Ensemble load error: %s", e)
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_trained": self.is_trained,
            "models": list(self.calibrated.keys()),
            "live_buffer_size": len(self._live_X),
            "tracker": self.tracker.get_summary(),
        }
