"""
AI SDK
======

SDK for integrating AI/ML models.
"""

import time
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """AI model configuration"""
    model_id: str
    model_type: str  # "classification", "regression", "ensemble"
    version: str
    input_features: List[str]
    output_type: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """Model prediction result"""
    prediction: Any
    confidence: float  # 0.0 - 1.0
    model_version: str
    inference_time_ms: float
    probabilities: Optional[Dict[str, float]] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "model_version": self.model_version,
            "inference_time_ms": self.inference_time_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class TrainingData:
    """Training data for model"""
    features: List[Dict[str, Any]]
    labels: List[Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingResult:
    """Model training result"""
    model_id: str
    model_version: str
    accuracy: float
    training_time_seconds: float
    metrics: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)


class AIModel:
    """
    Base AI Model class.
    
    All AI models must inherit from this class.
    """
    
    model_id: str = ""
    model_type: str = "base"
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config
        self._is_trained = False
        self._logger = logging.getLogger(f"ai.{self.model_id}")
    
    def train(self, data: TrainingData) -> TrainingResult:
        """
        Train the model.
        
        Override this method to implement training logic.
        """
        raise NotImplementedError
    
    def predict(self, features: Dict[str, Any]) -> PredictionResult:
        """
        Make a prediction.
        
        Override this method to implement prediction logic.
        """
        raise NotImplementedError
    
    def predict_batch(self, features_list: List[Dict[str, Any]]) -> List[PredictionResult]:
        """Make batch predictions"""
        return [self.predict(f) for f in features_list]
    
    def evaluate(self, data: TrainingData) -> Dict[str, float]:
        """
        Evaluate the model.
        
        Override to implement evaluation logic.
        """
        raise NotImplementedError
    
    def save(self, path: str) -> None:
        """Save model to file"""
        raise NotImplementedError
    
    @classmethod
    def load(cls, path: str) -> "AIModel":
        """Load model from file"""
        raise NotImplementedError
    
    @property
    def is_trained(self) -> bool:
        """Check if model is trained"""
        return self._is_trained


class AIModelRegistry(SmartPipSDK):
    """
    AI Model registry for managing and serving models.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._models: Dict[str, AIModel] = {}
        self._active_model: Optional[str] = None
    
    def _on_initialize(self) -> None:
        """Initialize model registry"""
        pass
    
    def register_model(self, model: AIModel) -> None:
        """Register a model"""
        if not model.model_id:
            raise SDKError("Model must have an ID")
        
        self._models[model.model_id] = model
        self._logger.info(f"Registered model: {model.model_id}")
    
    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model"""
        if model_id in self._models:
            del self._models[model_id]
            if self._active_model == model_id:
                self._active_model = None
            return True
        return False
    
    def get_model(self, model_id: str) -> Optional[AIModel]:
        """Get a model by ID"""
        return self._models.get(model_id)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        return [
            {
                "model_id": m.model_id,
                "model_type": m.model_type,
                "is_trained": m.is_trained,
                "config": m.config.__dict__ if m.config else None,
            }
            for m in self._models.values()
        ]
    
    def set_active_model(self, model_id: str) -> bool:
        """Set the active model"""
        if model_id not in self._models:
            return False
        
        model = self._models[model_id]
        if not model.is_trained:
            raise SDKError(f"Model {model_id} is not trained")
        
        self._active_model = model_id
        return True
    
    def get_active_model(self) -> Optional[AIModel]:
        """Get the active model"""
        if not self._active_model:
            return None
        return self._models.get(self._active_model)
    
    def predict(self, features: Dict[str, Any]) -> PredictionResult:
        """Predict using the active model"""
        model = self.get_active_model()
        if not model:
            raise SDKError("No active model set")
        
        return model.predict(features)
    
    def predict_with_fallback(
        self,
        features: Dict[str, Any],
        fallback_model_id: Optional[str] = None
    ) -> PredictionResult:
        """Predict with fallback model"""
        try:
            return self.predict(features)
        except Exception as e:
            self._logger.warning(f"Prediction failed: {e}")
            
            if fallback_model_id:
                fallback = self._models.get(fallback_model_id)
                if fallback and fallback.is_trained:
                    return fallback.predict(features)
            
            raise SDKError("All prediction attempts failed")


class FeatureEngineering:
    """Feature engineering utilities"""
    
    @staticmethod
    def normalize(values: List[float], min_val: float = None, max_val: float = None) -> List[float]:
        """Min-max normalize values"""
        if not values:
            return []
        
        min_v = min_val if min_val is not None else min(values)
        max_v = max_val if max_val is not None else max(values)
        
        if max_v == min_v:
            return [0.5] * len(values)
        
        return [(v - min_v) / (max_v - min_v) for v in values]
    
    @staticmethod
    def standardize(values: List[float]) -> List[float]:
        """Z-score standardize values"""
        if not values:
            return []
        
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        
        if std == 0:
            return [0.0] * len(values)
        
        return [(v - mean) / std for v in values]
    
    @staticmethod
    def create_lag_features(data: List[float], lags: int = 5) -> List[Dict[str, float]]:
        """Create lag features"""
        result = []
        for i in range(len(data)):
            features = {}
            for lag in range(1, min(lags + 1, i + 1)):
                features[f"lag_{lag}"] = data[i - lag]
            result.append(features)
        return result
    
    @staticmethod
    def create_rolling_features(
        data: List[float],
        windows: List[int] = [5, 10, 20]
    ) -> List[Dict[str, float]]:
        """Create rolling window features"""
        result = []
        for i in range(len(data)):
            features = {}
            for window in windows:
                if i >= window:
                    window_data = data[i - window:i]
                    features[f"mean_{window}"] = sum(window_data) / len(window_data)
                    features[f"std_{window}"] = (sum((x - sum(window_data)/len(window_data))**2 for x in window_data) / len(window_data)) ** 0.5
                else:
                    features[f"mean_{window}"] = sum(data[:i+1]) / (i + 1)
                    features[f"std_{window}"] = 0
            result.append(features)
        return result


class ModelMonitor:
    """Monitor model performance and detect drift"""
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self._predictions: List[PredictionResult] = []
        self._actuals: List[Any] = []
        self._thresholds = thresholds or {
            "accuracy_min": 0.6,
            "drift_max": 0.1,
        }
    
    def record_prediction(self, result: PredictionResult, actual: Any = None) -> None:
        """Record a prediction"""
        self._predictions.append(result)
        if actual is not None:
            self._actuals.append(actual)
    
    def calculate_accuracy(self) -> float:
        """Calculate prediction accuracy"""
        if not self._actuals:
            return 0.0
        
        correct = 0
        for pred, actual in zip(self._predictions[-len(self._actuals):], self._actuals):
            if pred.prediction == actual:
                correct += 1
        
        return correct / len(self._actuals)
    
    def detect_drift(self, window_size: int = 100) -> Dict[str, Any]:
        """Detect model drift"""
        if len(self._predictions) < window_size * 2:
            return {"drifted": False, "confidence": 0.0}
        
        recent = self._predictions[-window_size:]
        previous = self._predictions[-window_size * 2:-window_size]
        
        recent_confidence = sum(p.confidence for p in recent) / len(recent)
        previous_confidence = sum(p.confidence for p in previous) / len(previous)
        
        drift = abs(recent_confidence - previous_confidence)
        
        return {
            "drifted": drift > self._thresholds["drift_max"],
            "drift_amount": drift,
            "recent_confidence": recent_confidence,
            "previous_confidence": previous_confidence,
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get monitoring metrics"""
        return {
            "total_predictions": len(self._predictions),
            "total_actuals": len(self._actuals),
            "accuracy": self.calculate_accuracy(),
            "avg_confidence": sum(p.confidence for p in self._predictions) / len(self._predictions) if self._predictions else 0,
            "avg_inference_time_ms": sum(p.inference_time_ms for p in self._predictions) / len(self._predictions) if self._predictions else 0,
        }
