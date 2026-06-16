from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class VolatilityAnalyzer(BaseAnalyzer):
    """Analyze volatility markets and find best opportunity"""
    
    def __init__(self):
        super().__init__()
        self.best_market = None
        self.market_scores = {}
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze volatility markets"""
        markets = data.get("markets", {})
        
        market_scores = {}
        
        for market, market_data in markets.items():
            score = 50
            
            # Higher score for higher volatility (more movement)
            vol_scores = {"low": 40, "medium": 60, "high": 70, "very_high": 80, "extreme": 85, "synthetic": 50}
            score += vol_scores.get(market_data.get("volatility", "medium"), 50)
            
            # Adjust based on spread
            score -= market_data.get("spread", 0) * 1000
            
            market_scores[market] = min(max(score, 0), 100)
        
        self.market_scores = market_scores
        self.best_market = max(market_scores, key=market_scores.get) if market_scores else None
        
        return AnalysisResult(
            model_name="volatility_analysis",
            prediction=self.best_market,
            confidence=market_scores.get(self.best_market, 0) if self.best_market else 0,
            data={
                "market_scores": market_scores,
                "best_market": self.best_market
            }
        )
