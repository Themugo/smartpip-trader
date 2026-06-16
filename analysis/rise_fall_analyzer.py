from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class RiseFallAnalyzer(BaseAnalyzer):
    """Analyze price direction for Rise/Fall predictions with early termination"""
    
    def __init__(self):
        super().__init__(min_data_points=25)
        self.rise_count = 0
        self.fall_count = 0
        self.rise_streak = 0
        self.fall_streak = 0
        self.prediction = None
        self.momentum = 0
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze rise/fall patterns with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="rise_fall",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        price_history = data.get("price_history", [])
        
        prices = list(price_history)
        rises = 0
        falls = 0
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                rises += 1
            elif prices[i] < prices[i-1]:
                falls += 1
        
        # Calculate momentum
        recent_changes = [prices[i] - prices[i-1] for i in range(-20, 0)]
        momentum = sum(recent_changes) / len(recent_changes) if recent_changes else 0
        
        # Calculate streaks
        rise_streak = 0
        fall_streak = 0
        for i in range(len(prices)-1, 0, -1):
            if prices[i] > prices[i-1]:
                rise_streak += 1
                fall_streak = 0
            elif prices[i] < prices[i-1]:
                fall_streak += 1
                rise_streak = 0
            else:
                break
        
        # Prediction
        confidence = 50
        prediction = None
        
        if momentum > 0.001:
            prediction = "RISE"
            confidence = 60 + min(momentum * 1000, 30)
        elif momentum < -0.001:
            prediction = "FALL"
            confidence = 60 + min(abs(momentum) * 1000, 30)
        elif rise_streak >= 3:
            prediction = "FALL"  # Reversal
            confidence = 65 + min(rise_streak * 3, 25)
        elif fall_streak >= 3:
            prediction = "RISE"  # Reversal
            confidence = 65 + min(fall_streak * 3, 25)
        else:
            # Use majority
            if rises > falls:
                prediction = "RISE"
                confidence = 55
            else:
                prediction = "FALL"
                confidence = 55
        
        self.rise_count = rises
        self.fall_count = falls
        self.rise_streak = rise_streak
        self.fall_streak = fall_streak
        self.prediction = prediction
        self.confidence = min(confidence, 95)
        self.momentum = momentum
        
        return AnalysisResult(
            model_name="rise_fall",
            prediction=prediction,
            confidence=self.confidence,
            data={
                "rise_count": rises,
                "fall_count": falls,
                "rise_streak": rise_streak,
                "fall_streak": fall_streak,
                "momentum": momentum
            }
        )
