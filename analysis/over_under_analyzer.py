from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class OverUnderAnalyzer(BaseAnalyzer):
    """Analyze Over 3 / Under 7 patterns with early termination"""
    
    def __init__(self):
        super().__init__(min_data_points=15)
        self.over_3_count = 0
        self.under_7_count = 0
        self.between_3_7 = 0
        self.prediction = None
        self.edge = 0
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze over/under patterns with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="over_under",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        last_20_digits = data.get("last_20_digits", [])
        
        over_3 = sum(1 for d in last_20_digits if d > 3)
        under_7 = sum(1 for d in last_20_digits if d < 7)
        between = sum(1 for d in last_20_digits if 3 <= d <= 7)
        
        prediction = None
        confidence = 50
        
        if over_3 > under_7 + 5:
            prediction = "UNDER_7"
            confidence = 65 + (over_3 - under_7)
        elif under_7 > over_3 + 5:
            prediction = "OVER_3"
            confidence = 65 + (under_7 - over_3)
        else:
            # Check for streaks
            streak = self._calculate_streak(last_20_digits, lambda x: x > 3)
            if streak >= 4:
                prediction = "UNDER_7"
                confidence = 70
            else:
                streak = self._calculate_streak(last_20_digits, lambda x: x < 7)
                if streak >= 4:
                    prediction = "OVER_3"
                    confidence = 70
        
        self.over_3_count = over_3
        self.under_7_count = under_7
        self.between_3_7 = between
        self.prediction = prediction
        self.confidence = min(confidence, 95)
        self.edge = abs(over_3 - under_7)
        
        return AnalysisResult(
            model_name="over_under",
            prediction=prediction,
            confidence=self.confidence,
            data={
                "over_3_count": over_3,
                "under_7_count": under_7,
                "between_3_7": between,
                "edge": self.edge
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
