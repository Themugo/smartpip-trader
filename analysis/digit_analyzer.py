from typing import Dict, Any, List
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class DigitAnalyzer(BaseAnalyzer):
    """Comprehensive digit analysis for exact predictions with early termination"""
    
    def __init__(self):
        super().__init__(min_data_points=15)
        self.digit_frequencies = {i: 0 for i in range(10)}
        self.digit_predictions = []
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze digit patterns with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="digit_analysis",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        last_20_digits = data.get("last_20_digits", [])
        
        # Frequency analysis
        for d in last_20_digits:
            self.digit_frequencies[d] = self.digit_frequencies.get(d, 0) + 1
        
        # Most frequent digits
        most_frequent = max(self.digit_frequencies, key=self.digit_frequencies.get)
        least_frequent = min(self.digit_frequencies, key=self.digit_frequencies.get)
        
        # Calculate probabilities
        total = sum(self.digit_frequencies.values())
        probabilities = {d: count/total for d, count in self.digit_frequencies.items()}
        
        # Look for specific patterns
        predictions = []
        
        # Single digit prediction
        if probabilities.get(most_frequent, 0) > 0.2:
            predictions.append({
                "digit": most_frequent,
                "confidence": probabilities[most_frequent] * 100,
                "reason": "Most frequent"
            })
        
        # Range predictions
        low_digits = sum(probabilities.get(d, 0) for d in [0,1,2,3,4])
        high_digits = sum(probabilities.get(d, 0) for d in [5,6,7,8,9])
        
        if low_digits > 0.6:
            predictions.append({
                "range": "0-4",
                "confidence": low_digits * 100,
                "reason": "Low digit bias"
            })
        if high_digits > 0.6:
            predictions.append({
                "range": "5-9",
                "confidence": high_digits * 100,
                "reason": "High digit bias"
            })
        
        # Streak prediction
        streak = self._calculate_streak(last_20_digits, lambda x: True)
        if streak >= 3:
            predictions.append({
                "digit": last_20_digits[-1],
                "confidence": 60 + streak * 2,
                "reason": f"Streak of {streak}"
            })
        
        self.digit_predictions = predictions
        
        # Get best prediction
        best_pred = predictions[0] if predictions else None
        confidence = best_pred["confidence"] if best_pred else 0
        
        return AnalysisResult(
            model_name="digit_analysis",
            prediction=f"DIGIT_{best_pred.get('digit', best_pred.get('range', '?'))}" if best_pred else None,
            confidence=confidence,
            data={
                "digit_predictions": predictions,
                "digit_frequencies": self.digit_frequencies
            }
        )
    
    def _calculate_streak(self, digits: list, condition_func) -> int:
        """Calculate streak based on condition"""
        if not digits:
            return 0
        
        streak = 1
        for i in range(len(digits)-1, 0, -1):
            if condition_func(digits[i]) == condition_func(digits[i-1]):
                streak += 1
            else:
                break
        return streak
