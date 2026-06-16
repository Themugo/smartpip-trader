import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from models import Prediction, AnalysisResult
from .even_odd_analyzer import EvenOddAnalyzer
from .rise_fall_analyzer import RiseFallAnalyzer
from .over_under_analyzer import OverUnderAnalyzer
from .match_diff_analyzer import MatchDiffAnalyzer
from .digit_analyzer import DigitAnalyzer
from .volatility_analyzer import VolatilityAnalyzer
from .technical_analyzer import TechnicalAnalyzer
from .ml_analyzer import MLAnalyzer
from .multitimeframe_analyzer import MultiTimeframeAnalyzer
from .adaptive_confidence import AdaptiveConfidence


class AnalysisManager:
    """Manages all analysis models and coordinates predictions"""
    
    def __init__(self):
        self.analyzers = {
            "even_odd": EvenOddAnalyzer(),
            "rise_fall": RiseFallAnalyzer(),
            "over_under": OverUnderAnalyzer(),
            "match_diff": MatchDiffAnalyzer(),
            "digit_analysis": DigitAnalyzer(),
            "volatility_analysis": VolatilityAnalyzer(),
            "technical": TechnicalAnalyzer(),
            "ml": MLAnalyzer(),
            "multitimeframe": MultiTimeframeAnalyzer()
        }
        self.adaptive_confidence = AdaptiveConfidence(base_threshold=70)
        self.analysis_result = {}
        self.trade_signals = []
        self.best_prediction = None
        self.recent_trades = []
    
    def set_analyzer_enabled(self, analyzer_name: str, enabled: bool):
        """Enable or disable specific analyzer"""
        if analyzer_name in self.analyzers:
            self.analyzers[analyzer_name].set_enabled(enabled)
    
    async def get_comprehensive_analysis_async(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all analysis models in parallel and combine results"""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "last_20_digits": data.get("last_20_digits", []),
            "current_price": data.get("current_price", 0),
            "market": data.get("market", "")
        }
        
        # Run all enabled analyzers in parallel
        tasks = []
        for name, analyzer in self.analyzers.items():
            if analyzer.is_enabled():
                tasks.append(self._run_analyzer_async(name, analyzer, data))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    continue
                name, analyzer_result = result
                analysis[name] = {
                    "prediction": analyzer_result.prediction,
                    "confidence": analyzer_result.confidence,
                    "data": analyzer_result.data
                }
        
        self.analysis_result = analysis
        self.generate_best_prediction()
        
        return analysis
    
    async def _run_analyzer_async(self, name: str, analyzer, data: Dict[str, Any]):
        """Run a single analyzer asynchronously"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyzer.analyze, data)
        return name, result
    
    def get_comprehensive_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for comprehensive analysis"""
        # For backward compatibility, run synchronously
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "last_20_digits": data.get("last_20_digits", []),
            "current_price": data.get("current_price", 0),
            "market": data.get("market", "")
        }
        
        # Run all enabled analyzers
        for name, analyzer in self.analyzers.items():
            if analyzer.is_enabled():
                result = analyzer.analyze(data)
                analysis[name] = {
                    "prediction": result.prediction,
                    "confidence": result.confidence,
                    "data": result.data
                }
        
        self.analysis_result = analysis
        self.generate_best_prediction()
        
        return analysis
    
    def generate_best_prediction(self) -> Optional[Prediction]:
        """Combine all model predictions to find best trade"""
        predictions = []
        
        # Even/Odd prediction
        even_odd_result = self.analysis_result.get("even_odd", {})
        if even_odd_result.get("prediction") and even_odd_result.get("confidence", 0) > 60:
            predictions.append({
                "type": "EVEN_ODD",
                "direction": even_odd_result["prediction"],
                "confidence": even_odd_result["confidence"],
                "reason": f"Even/Odd edge: {even_odd_result['data'].get('edge', 0)}"
            })
        
        # Rise/Fall prediction
        rise_fall_result = self.analysis_result.get("rise_fall", {})
        if rise_fall_result.get("prediction") and rise_fall_result.get("confidence", 0) > 60:
            predictions.append({
                "type": "RISE_FALL",
                "direction": rise_fall_result["prediction"],
                "confidence": rise_fall_result["confidence"],
                "reason": f"Momentum: {rise_fall_result['data'].get('momentum', 0):.4f}"
            })
        
        # Over/Under prediction
        over_under_result = self.analysis_result.get("over_under", {})
        if over_under_result.get("prediction") and over_under_result.get("confidence", 0) > 60:
            predictions.append({
                "type": "OVER_UNDER",
                "direction": over_under_result["prediction"],
                "confidence": over_under_result["confidence"],
                "reason": f"Edge: {over_under_result['data'].get('edge', 0)}"
            })
        
        # Match/Diff prediction
        match_diff_result = self.analysis_result.get("match_diff", {})
        if match_diff_result.get("prediction") and match_diff_result.get("confidence", 0) > 60:
            predictions.append({
                "type": "MATCH_DIFF",
                "direction": match_diff_result["prediction"],
                "confidence": match_diff_result["confidence"],
                "reason": f"Streak: {match_diff_result['data'].get('match_streak', 0)}"
            })
        
        # Digit predictions
        digit_result = self.analysis_result.get("digit_analysis", {})
        digit_predictions = digit_result.get("data", {}).get("digit_predictions", [])
        for pred in digit_predictions[:2]:
            if pred.get("confidence", 0) > 65:
                predictions.append({
                    "type": "DIGIT",
                    "direction": f"DIGIT_{pred.get('digit', pred.get('range', '?'))}",
                    "confidence": pred["confidence"],
                    "reason": pred["reason"]
                })
        
        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        self.trade_signals = predictions
        self.best_prediction = predictions[0] if predictions else None
        
        return self.best_prediction
    
    def get_best_prediction(self) -> Optional[Prediction]:
        """Get best prediction"""
        return self.best_prediction
    
    def get_trade_signals(self) -> List[Dict]:
        """Get all trade signals"""
        return self.trade_signals
