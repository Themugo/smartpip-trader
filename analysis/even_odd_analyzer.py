from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class EvenOddAnalyzer(BaseAnalyzer):
    """Analyze Even/Odd patterns with advanced statistics and early termination"""
    
    def __init__(self):
        super().__init__(min_data_points=15)
        self.even_count = 0
        self.odd_count = 0
        self.even_streak = 0
        self.odd_streak = 0
        self.prediction = None
        self.edge = 0
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze even/odd patterns with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="even_odd",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        last_20_digits = data.get("last_20_digits", [])
        
        evens = sum(1 for d in last_20_digits if d % 2 == 0)
        odds = 20 - evens
        
        # Calculate streaks
        current_streak = 1
        for i in range(len(last_20_digits)-1, 0, -1):
            if (last_20_digits[i] % 2) == (last_20_digits[i-1] % 2):
                current_streak += 1
            else:
                break
        
        # Prediction logic
        confidence = 50
        prediction = None
        
        if evens > odds + 4:
            confidence = 60 + (evens - odds) * 2
            prediction = "ODD"  # Mean reversion
        elif odds > evens + 4:
            confidence = 60 + (odds - evens) * 2
            prediction = "EVEN"  # Mean reversion
        elif current_streak >= 4:
            # Streak reversal
            current_type = "EVEN" if last_20_digits[-1] % 2 == 0 else "ODD"
            prediction = "ODD" if current_type == "EVEN" else "EVEN"
            confidence = 65 + min(current_streak * 2, 25)
        else:
            # Random walk - slight edge to majority
            if evens > odds:
                prediction = "EVEN"
                confidence = 55
            else:
                prediction = "ODD"
                confidence = 55
        
        self.even_count = evens
        self.odd_count = odds
        self.even_streak = self._calculate_streak(last_20_digits, 0)
        self.odd_streak = self._calculate_streak(last_20_digits, 1)
        self.prediction = prediction
        self.confidence = min(confidence, 95)
        self.edge = abs(evens - odds)
        
        return AnalysisResult(
            model_name="even_odd",
            prediction=prediction,
            confidence=self.confidence,
            data={
                "even_count": evens,
                "odd_count": odds,
                "even_streak": self.even_streak,
                "odd_streak": self.odd_streak,
                "edge": self.edge
            }
        )
    
    def _calculate_streak(self, digits: list, parity: int) -> int:
        """Calculate streak for even (0) or odd (1)"""
        if not digits:
            return 0
        
        streak = 1
        for i in range(len(digits)-1, 0, -1):
            if (digits[i] % 2) == parity and (digits[i-1] % 2) == parity:
                streak += 1
            else:
                break
        return streak
