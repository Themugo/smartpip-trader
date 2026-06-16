from typing import Dict, Any, List, Optional
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer
from indicators import SMA, EMA, RSI, MACD


class MultiTimeframeAnalyzer(BaseAnalyzer):
    """Analyze market across multiple timeframes for better timing"""
    
    def __init__(self):
        super().__init__(min_data_points=100)
        self.timeframes = {
            "short": 5,
            "medium": 15,
            "long": 30
        }
        self.timeframe_signals = {}
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze across multiple timeframes"""
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="multitimeframe",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        price_history = data.get("price_history", [])
        if len(price_history) < 100:
            return AnalysisResult(
                model_name="multitimeframe",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": "Insufficient data for multi-timeframe"}
            )
        
        # Analyze each timeframe
        self.timeframe_signals = {}
        
        for tf_name, tf_period in self.timeframes.items():
            signal = self._analyze_timeframe(price_history, tf_period)
            self.timeframe_signals[tf_name] = signal
        
        # Combine signals
        combined_signal = self._combine_timeframe_signals()
        
        if not combined_signal:
            return AnalysisResult(
                model_name="multitimeframe",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": "No clear multi-timeframe signal"}
            )
        
        return AnalysisResult(
            model_name="multitimeframe",
            prediction=combined_signal["direction"],
            confidence=combined_signal["confidence"],
            data={
                "timeframe_signals": self.timeframe_signals,
                "combined_signal": combined_signal
            }
        )
    
    def _analyze_timeframe(self, price_history: List[float], period: int) -> Dict[str, Any]:
        """Analyze a specific timeframe"""
        if len(price_history) < period * 2:
            return {"direction": None, "confidence": 0}
        
        tf_prices = price_history[-period * 2:]
        
        # Calculate indicators
        sma_short = SMA.calculate(tf_prices, period // 2)
        sma_long = SMA.calculate(tf_prices, period)
        rsi = RSI.calculate(tf_prices, 14)
        
        bullish_score = 0
        bearish_score = 0
        
        # SMA crossover
        if sma_short and sma_long:
            if sma_short > sma_long:
                bullish_score += 1
            else:
                bearish_score += 1
        
        # RSI
        if rsi:
            if rsi < 30:
                bullish_score += 2
            elif rsi > 70:
                bearish_score += 2
            elif 40 < rsi < 60:
                pass  # Neutral
        
        # Momentum
        if len(tf_prices) >= 5:
            momentum = (tf_prices[-1] - tf_prices[-5]) / tf_prices[-5]
            if momentum > 0.01:
                bullish_score += 1
            elif momentum < -0.01:
                bearish_score += 1
        
        # Determine direction
        if bullish_score > bearish_score:
            direction = "CALL"
            confidence = 50 + (bullish_score - bearish_score) * 10
        elif bearish_score > bullish_score:
            direction = "PUT"
            confidence = 50 + (bearish_score - bullish_score) * 10
        else:
            direction = None
            confidence = 0
        
        return {
            "direction": direction,
            "confidence": min(confidence, 90),
            "bullish_score": bullish_score,
            "bearish_score": bearish_score
        }
    
    def _combine_timeframe_signals(self) -> Optional[Dict[str, Any]]:
        """Combine signals from multiple timeframes"""
        bullish_count = 0
        bearish_count = 0
        total_confidence = 0
        
        for tf_name, signal in self.timeframe_signals.items():
            if signal["direction"] == "CALL":
                bullish_count += 1
                total_confidence += signal["confidence"]
            elif signal["direction"] == "PUT":
                bearish_count += 1
                total_confidence += signal["confidence"]
        
        # Only trade if at least 2 timeframes agree
        if bullish_count >= 2:
            return {
                "direction": "CALL",
                "confidence": total_confidence / (bullish_count + bearish_count),
                "agreement": bullish_count / len(self.timeframes)
            }
        elif bearish_count >= 2:
            return {
                "direction": "PUT",
                "confidence": total_confidence / (bullish_count + bearish_count),
                "agreement": bearish_count / len(self.timeframes)
            }
        
        return None
