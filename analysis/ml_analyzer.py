from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer
from ml import MLPredictor


class MLAnalyzer(BaseAnalyzer):
    """Machine Learning analyzer using trained models"""
    
    def __init__(self, model_type: str = "random_forest"):
        super().__init__(min_data_points=30)
        self.model_type = model_type
        self.predictor = MLPredictor(model_type=model_type)
        self.is_trained = False
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze using ML model with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="ml",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        # Try to load model if not trained
        if not self.is_trained:
            if self.predictor.load_model():
                self.is_trained = True
            else:
                return AnalysisResult(
                    model_name="ml",
                    prediction=None,
                    confidence=0,
                    data={"skipped": True, "reason": "Model not trained"}
                )
        
        # Make prediction
        prediction = self.predictor.predict(data)
        
        if prediction is None:
            return AnalysisResult(
                model_name="ml",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": "Prediction failed"}
            )
        
        return AnalysisResult(
            model_name="ml",
            prediction=prediction.direction,
            confidence=prediction.confidence,
            data={
                "model_type": self.model_type,
                "reason": prediction.reason,
                "is_trained": self.is_trained
            }
        )
    
    def train_model(self, historical_data: list, labels: list) -> Dict[str, Any]:
        """Train the ML model"""
        metrics = self.predictor.train(historical_data, labels)
        self.is_trained = True
        return metrics
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model"""
        return self.predictor.get_feature_importance() or {}
