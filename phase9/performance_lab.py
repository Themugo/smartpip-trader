"""
AI Performance Lab - Model Performance Dashboard

Comprehensive performance monitoring for AI models and analyzers.
"""

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    CALIBRATION = "calibration"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass
class ModelMetrics:
    """Metrics for a single model"""
    model_id: str
    model_name: str
    
    # Accuracy metrics
    accuracy: float = 0
    precision: float = 0
    recall: float = 0
    f1_score: float = 0
    
    # Calibration metrics
    calibration_error: float = 0
    brier_score: float = 0
    
    # Performance metrics
    avg_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    throughput: float = 0
    
    # Trading metrics
    win_rate: float = 0
    expectancy: float = 0
    sharpe_ratio: float = 0
    
    # Counts
    total_predictions: int = 0
    correct_predictions: int = 0
    
    # Timestamps
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "calibration_error": self.calibration_error,
            "avg_latency_ms": self.avg_latency_ms,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio,
            "total_predictions": self.total_predictions,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class RollingMetrics:
    """Rolling window metrics"""
    window_size: int
    values: deque = field(default_factory=deque)
    
    @property
    def average(self) -> float:
        if not self.values:
            return 0
        return sum(self.values) / len(self.values)
    
    @property
    def min(self) -> float:
        return min(self.values) if self.values else 0
    
    @property
    def max(self) -> float:
        return max(self.values) if self.values else 0
    
    def add(self, value: float) -> None:
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.popleft()


class PerformanceLab:
    """
    AI Performance Lab for model monitoring.
    
    Features:
    - Live accuracy tracking
    - Rolling accuracy
    - Calibration analysis
    - False positive/negative tracking
    - Confidence drift detection
    - Expected vs realized value
    - Strategy rankings
    - Analyzer rankings
    - Latency monitoring
    - Execution quality
    """
    
    def __init__(self):
        self._models: Dict[str, ModelMetrics] = {}
        self._predictions: Dict[str, List[Dict[str, Any]]] = {}
        
        # Rolling metrics
        self._rolling_accuracy: Dict[str, RollingMetrics] = {}
        self._rolling_latency: Dict[str, RollingMetrics] = {}
        
        # Rankings
        self._model_rankings: Dict[str, float] = {}
        
        logger.info("Performance Lab initialized")
    
    def register_model(self, model_id: str, model_name: str) -> None:
        """Register a model for tracking"""
        self._models[model_id] = ModelMetrics(
            model_id=model_id,
            model_name=model_name,
        )
        self._predictions[model_id] = []
        self._rolling_accuracy[model_id] = RollingMetrics(window_size=100)
        self._rolling_latency[model_id] = RollingMetrics(window_size=100)
        
        logger.info(f"Registered model: {model_name}")
    
    def record_prediction(
        self,
        model_id: str,
        prediction: Dict[str, Any],
    ) -> None:
        """Record a model prediction"""
        if model_id not in self._predictions:
            self.register_model(model_id, prediction.get("name", model_id))
        
        self._predictions[model_id].append({
            **prediction,
            "recorded_at": datetime.now(timezone.utc),
        })
        
        # Keep only recent predictions
        if len(self._predictions[model_id]) > 10000:
            self._predictions[model_id] = self._predictions[model_id][-5000:]
    
    def record_outcome(
        self,
        model_id: str,
        prediction_id: str,
        actual_outcome: bool,
        realized_value: float,
    ) -> None:
        """Record the outcome of a prediction"""
        predictions = self._predictions.get(model_id, [])
        
        for pred in reversed(predictions):
            if pred.get("id") == prediction_id:
                pred["actual_outcome"] = actual_outcome
                pred["realized_value"] = realized_value
                pred["outcome_recorded_at"] = datetime.now(timezone.utc)
                
                # Update rolling accuracy
                is_correct = (actual_outcome == pred.get("correct_prediction"))
                self._rolling_accuracy[model_id].add(1 if is_correct else 0)
                
                break
    
    def calculate_metrics(self, model_id: str) -> ModelMetrics:
        """Calculate current metrics for a model"""
        if model_id not in self._models:
            raise ValueError(f"Model not registered: {model_id}")
        
        predictions = self._predictions.get(model_id, [])
        model = self._models[model_id]
        
        # Filter to predictions with outcomes
        completed = [p for p in predictions if "actual_outcome" in p]
        
        if not completed:
            return model
        
        # Calculate accuracy metrics
        correct = sum(1 for p in completed if p["actual_outcome"] == p.get("correct_prediction", False))
        model.accuracy = correct / len(completed) if completed else 0
        model.total_predictions = len(completed)
        model.correct_predictions = correct
        
        # Calculate precision/recall
        true_positives = sum(
            1 for p in completed
            if p["actual_outcome"] and p.get("correct_prediction", False)
        )
        false_positives = sum(
            1 for p in completed
            if not p["actual_outcome"] and p.get("correct_prediction", False)
        )
        false_negatives = sum(
            1 for p in completed
            if p["actual_outcome"] and not p.get("correct_prediction", False)
        )
        
        if (true_positives + false_positives) > 0:
            model.precision = true_positives / (true_positives + false_positives)
        
        if (true_positives + false_negatives) > 0:
            model.recall = true_positives / (true_positives + false_negatives)
        
        if model.precision + model.recall > 0:
            model.f1_score = 2 * (model.precision * model.recall) / (model.precision + model.recall)
        
        # Calculate calibration
        model.calibration_error = self._calculate_calibration_error(completed)
        
        # Calculate trading metrics
        wins = sum(1 for p in completed if p["realized_value"] > 0)
        losses = sum(1 for p in completed if p["realized_value"] < 0)
        
        if completed:
            model.win_rate = wins / len(completed)
            
            values = [p["realized_value"] for p in completed]
            avg_win = sum(v for v in values if v > 0) / max(wins, 1)
            avg_loss = abs(sum(v for v in values if v < 0) / max(losses, 1)) if losses > 0 else 1
            
            if avg_loss > 0:
                model.expectancy = (model.win_rate * avg_win - (1 - model.win_rate) * avg_loss) / avg_loss
        
        # Update rolling metrics
        model.accuracy = self._rolling_accuracy[model_id].average
        
        # Latency from rolling metrics
        model.avg_latency_ms = self._rolling_latency[model_id].average
        
        model.calculated_at = datetime.now(timezone.utc)
        
        return model
    
    def _calculate_calibration_error(self, predictions: List[Dict[str, Any]]) -> float:
        """Calculate calibration error (expected vs actual)"""
        # Group predictions by confidence bucket
        buckets = {0.1: [], 0.3: [], 0.5: [], 0.7: [], 0.9: []}
        
        for pred in predictions:
            confidence = pred.get("confidence", 0.5)
            bucket = max(0.1, min(0.9, round(confidence * 10) / 10))
            
            is_correct = pred["actual_outcome"] == pred.get("correct_prediction", False)
            buckets[bucket].append(1 if is_correct else 0)
        
        # Calculate calibration error
        total_error = 0
        count = 0
        
        for bucket, values in buckets.items():
            if values:
                actual_rate = sum(values) / len(values)
                total_error += abs(bucket - actual_rate)
                count += 1
        
        return total_error / count if count > 0 else 0
    
    def record_latency(self, model_id: str, latency_ms: float) -> None:
        """Record prediction latency"""
        if model_id in self._rolling_latency:
            self._rolling_latency[model_id].add(latency_ms)
    
    def detect_drift(
        self,
        model_id: str,
        window_size: int = 50,
    ) -> Dict[str, Any]:
        """Detect performance drift"""
        predictions = self._predictions.get(model_id, [])
        
        if len(predictions) < window_size * 2:
            return {"drift_detected": False, "reason": "Insufficient data"}
        
        # Split into two windows
        recent = predictions[-window_size:]
        previous = predictions[-window_size*2:-window_size]
        
        # Calculate accuracy for each window
        recent_correct = sum(
            1 for p in recent if "actual_outcome" in p and p["actual_outcome"] == p.get("correct_prediction", False)
        )
        previous_correct = sum(
            1 for p in previous if "actual_outcome" in p and p["actual_outcome"] == p.get("correct_prediction", False)
        )
        
        recent_accuracy = recent_correct / window_size if recent else 0
        previous_accuracy = previous_correct / window_size if previous else 0
        
        # Check for significant drift
        drift = recent_accuracy - previous_accuracy
        
        return {
            "drift_detected": abs(drift) > 0.1,  # 10% threshold
            "recent_accuracy": recent_accuracy,
            "previous_accuracy": previous_accuracy,
            "drift": drift,
            "direction": "improving" if drift > 0 else "degrading",
        }
    
    def get_model_ranking(self, model_id: str) -> float:
        """Calculate composite ranking score for a model"""
        model = self._models.get(model_id)
        if not model:
            return 0
        
        # Composite score
        accuracy_score = model.accuracy * 30
        precision_score = model.precision * 20
        latency_score = max(0, 100 - model.avg_latency_ms) / 100 * 20
        calibration_score = (1 - model.calibration_error) * 15
        trading_score = (model.expectancy + 1) * 10 if model.expectancy > -1 else 0
        
        return accuracy_score + precision_score + latency_score + calibration_score + trading_score
    
    def get_rankings(self) -> List[Dict[str, Any]]:
        """Get ranked list of models"""
        rankings = []
        
        for model_id in self._models:
            model = self.calculate_metrics(model_id)
            score = self.get_model_ranking(model_id)
            
            rankings.append({
                "model_id": model_id,
                "model_name": model.model_name,
                "score": score,
                "accuracy": model.accuracy,
                "precision": model.precision,
                "win_rate": model.win_rate,
                "avg_latency_ms": model.avg_latency_ms,
            })
        
        # Sort by score
        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        # Add ranks
        for i, r in enumerate(rankings, 1):
            r["rank"] = i
        
        return rankings
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for performance monitoring"""
        rankings = self.get_rankings()
        
        # Aggregate metrics
        total_predictions = sum(m.total_predictions for m in self._models.values())
        avg_accuracy = (
            sum(m.accuracy for m in self._models.values()) / len(self._models)
            if self._models else 0
        )
        avg_latency = (
            sum(m.avg_latency_ms for m in self._models.values()) / len(self._models)
            if self._models else 0
        )
        
        return {
            "models": rankings,
            "total_models": len(self._models),
            "total_predictions": total_predictions,
            "avg_accuracy": avg_accuracy,
            "avg_latency_ms": avg_latency,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_all_metrics(self) -> Dict[str, ModelMetrics]:
        """Get metrics for all models"""
        return {
            model_id: self.calculate_metrics(model_id)
            for model_id in self._models
        }
