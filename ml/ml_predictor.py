"""
ML Predictor — upgraded to use EnsemblePredictor as primary, with single-model fallback.
Provides rich reason strings, feature-importance reporting, and live-outcome ingestion.
"""
import numpy as np
import os
import logging
from typing import Dict, Any, Optional, List

from .feature_engineer import FeatureEngineer
from .ensemble_predictor import EnsemblePredictor
from models import Prediction

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

logger = logging.getLogger(__name__)


class MLPredictor:
    """
    Primary predictor: delegates to EnsemblePredictor.
    Falls back to a single RandomForest if the ensemble is not yet trained.
    Supports incremental learning via add_live_outcome().
    """

    def __init__(self, model_type: str = "ensemble"):
        self.model_type = model_type
        self.feature_engineer = FeatureEngineer()
        self.ensemble = EnsemblePredictor()

        # Fallback single model
        self._fallback_scaler = StandardScaler()
        self._fallback_model = RandomForestClassifier(
            n_estimators=150, max_depth=10, min_samples_leaf=3,
            class_weight="balanced", random_state=42, n_jobs=-1
        )
        self._fallback_trained = False
        self._fallback_model_path = "ml_model.pkl"
        self._fallback_scaler_path = "ml_scaler.pkl"

        self.is_trained = False
        self._try_load()

    def _try_load(self):
        """Try loading ensemble first, then fallback."""
        if self.ensemble.load():
            self.is_trained = True
            logger.info("Ensemble predictor loaded.")
            return
        # Try fallback
        if os.path.exists(self._fallback_model_path) and os.path.exists(self._fallback_scaler_path):
            self._fallback_model = joblib.load(self._fallback_model_path)
            self._fallback_scaler = joblib.load(self._fallback_scaler_path)
            self._fallback_trained = True
            self.is_trained = True
            logger.info("Fallback RF model loaded.")

    # ── Public API ────────────────────────────────────────────────────────

    def train(self, historical_data: List[Dict[str, Any]], labels: List[str]) -> Dict[str, Any]:
        """Train ensemble (and fallback) from historical data + labels."""
        features, valid_labels = [], []
        for data, label in zip(historical_data, labels):
            try:
                fv = self.feature_engineer.extract_features(data)
                features.append(fv)
                valid_labels.append(label)
            except Exception:
                continue

        if len(features) < 20:
            raise ValueError(f"Too few valid samples: {len(features)}")

        X = np.array(features)
        y = np.array(valid_labels)

        # Train ensemble
        metrics = self.ensemble.train(X, y)

        # Train fallback too
        self._train_fallback(X, y)

        self.is_trained = True
        return metrics

    def predict(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Make prediction; ensemble preferred, fallback if needed."""
        if not self.is_trained:
            return None
        try:
            features = self.feature_engineer.extract_features(data)
        except Exception as e:
            logger.debug("Feature extraction failed: %s", e)
            return None

        # Try ensemble first
        if self.ensemble.is_trained:
            pred = self.ensemble.predict(features)
            if pred:
                return pred

        # Fallback RF
        if self._fallback_trained:
            return self._fallback_predict(features)

        return None

    def add_live_outcome(self, data: Dict[str, Any], actual_direction: str, model_preds: Dict[str, str] = None):
        """Feed live trade outcome back to ensemble for incremental learning."""
        try:
            features = self.feature_engineer.extract_features(data)
            self.ensemble.add_live_outcome(features, actual_direction, model_preds or {})
        except Exception as e:
            logger.debug("add_live_outcome error: %s", e)

    def predict_proba(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        if not self.is_trained:
            return None
        try:
            features = self.feature_engineer.extract_features(data)
            if self.ensemble.is_trained and self.ensemble.calibrated:
                x_s = self.ensemble.scaler.transform([features])
                # Average calibrated probabilities
                call_p, put_p, n = 0.0, 0.0, 0
                for name, cal in self.ensemble.calibrated.items():
                    proba = cal.predict_proba(x_s)[0]
                    classes = list(cal.classes_)
                    ci = classes.index("CALL") if "CALL" in classes else 0
                    call_p += proba[ci]
                    put_p += proba[1 - ci]
                    n += 1
                if n:
                    return {"CALL": round(call_p / n, 4), "PUT": round(put_p / n, 4)}
        except Exception:
            pass
        return None

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Feature importance from ensemble RF component."""
        try:
            rf_cal = self.ensemble.calibrated.get("rf")
            if rf_cal and hasattr(rf_cal.estimator if hasattr(rf_cal, "estimator") else rf_cal, "feature_importances_"):
                base = rf_cal.estimator if hasattr(rf_cal, "estimator") else rf_cal
                if hasattr(base, "feature_importances_"):
                    names = self.feature_engineer.get_feature_names()
                    imps = base.feature_importances_
                    pairs = sorted(zip(names, imps), key=lambda x: x[1], reverse=True)
                    return {k: round(float(v), 5) for k, v in pairs}
        except Exception:
            pass
        # Fallback RF
        if self._fallback_trained and hasattr(self._fallback_model, "feature_importances_"):
            names = self.feature_engineer.get_feature_names()
            return {k: round(float(v), 5) for k, v in zip(names, self._fallback_model.feature_importances_)}
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_trained": self.is_trained,
            "mode": "ensemble" if self.ensemble.is_trained else ("fallback_rf" if self._fallback_trained else "untrained"),
            "feature_count": self.feature_engineer.feature_count(),
            "ensemble": self.ensemble.get_status(),
        }

    # ── Private helpers ───────────────────────────────────────────────────

    def _train_fallback(self, X: np.ndarray, y: np.ndarray):
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        X_tr_s = self._fallback_scaler.fit_transform(X_tr)
        X_te_s = self._fallback_scaler.transform(X_te)
        self._fallback_model.fit(X_tr_s, y_tr)
        self._fallback_trained = True
        acc = accuracy_score(y_te, self._fallback_model.predict(X_te_s))
        logger.info("Fallback RF accuracy: %.3f", acc)
        joblib.dump(self._fallback_model, self._fallback_model_path)
        joblib.dump(self._fallback_scaler, self._fallback_scaler_path)

    def _fallback_predict(self, features: np.ndarray) -> Optional[Prediction]:
        try:
            x_s = self._fallback_scaler.transform([features])
            pred = self._fallback_model.predict(x_s)[0]
            proba = self._fallback_model.predict_proba(x_s)[0]
            conf = float(max(proba)) * 100
            fi = self.get_feature_importance()
            top_feat = list(fi.keys())[:3] if fi else []
            reason = f"RF fallback → {pred} ({conf:.0f}%) | top features: {', '.join(top_feat)}"
            return Prediction(type="ML_RF", direction=pred, confidence=conf, reason=reason)
        except Exception as e:
            logger.debug("Fallback predict error: %s", e)
            return None

    # Keep backward-compat method
    def load_model(self) -> bool:
        self._try_load()
        return self.is_trained
