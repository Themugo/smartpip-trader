from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class MatchDiffAnalyzer(BaseAnalyzer):
    """Analyze Match and Differ patterns with early termination"""
    
    def __init__(self):
        super().__init__(min_data_points=15)
        self.match_count = 0
        self.diff_count = 0
        self.match_streak = 0
        self.diff_streak = 0
        self.prediction = None
        self.last_match = None
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze match/diff patterns with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="match_diff",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        last_20_digits = data.get("last_20_digits", [])
        
        matches = 0
        diffs = 0
        
        for i in range(1, len(last_20_digits)):
            if last_20_digits[i] == last_20_digits[i-1]:
                matches += 1
            else:
                diffs += 1
        
        # Current streak
        current_streak = 1
        for i in range(len(last_20_digits)-1, 0, -1):
            if last_20_digits[i] == last_20_digits[i-1]:
                current_streak += 1
            else:
                break
        
        prediction = None
        confidence = 50
        
        if matches > diffs + 5:
            prediction = "DIFF"
            confidence = 65
        elif diffs > matches + 5:
            prediction = "MATCH"
            confidence = 65
        elif current_streak >= 3:
            prediction = "DIFF"  # Break the streak
            confidence = 70 + min(current_streak * 2, 20)
        
        self.match_count = matches
        self.diff_count = diffs
        self.match_streak = self._calculate_match_streak(last_20_digits)
        self.diff_streak = current_streak
        self.prediction = prediction
        self.confidence = min(confidence, 95)
        self.last_match = last_20_digits[-1] if last_20_digits else None
        
        return AnalysisResult(
            model_name="match_diff",
            prediction=prediction,
            confidence=self.confidence,
            data={
                "match_count": matches,
                "diff_count": diffs,
                "match_streak": self.match_streak,
                "diff_streak": current_streak,
                "last_match": self.last_match
            }
        )
    
    def _calculate_match_streak(self, digits: list) -> int:
        """Calculate match streak"""
        if len(digits) < 2:
            return 0
        
        streak = 1
        for i in range(len(digits)-1, 0, -1):
            if digits[i] == digits[i-1]:
                streak += 1
            else:
                break
        return streak
