from typing import Dict, Any
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer
from indicators import TechnicalIndicatorManager


class TechnicalAnalyzer(BaseAnalyzer):
    """Analyze market using technical indicators (RSI, MACD, Bollinger Bands, SMA/EMA)"""
    
    def __init__(self):
        super().__init__(min_data_points=30)
        self.indicator_manager = TechnicalIndicatorManager()
        self.indicators = {}
        self.signals = {}
    
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze market using technical indicators with early termination"""
        # Early termination check
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="technical",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": reason}
            )
        
        price_history = data.get("price_history", [])
        if len(price_history) < 30:
            return AnalysisResult(
                model_name="technical",
                prediction=None,
                confidence=0,
                data={"skipped": True, "reason": "Insufficient price history"}
            )
        
        # Calculate all indicators
        self.indicators = self.indicator_manager.calculate_all(price_history)
        
        # Get trading signals
        self.signals = self.indicator_manager.get_signal(price_history)
        
        # Generate prediction based on signals
        prediction, confidence = self._generate_prediction()
        
        return AnalysisResult(
            model_name="technical",
            prediction=prediction,
            confidence=confidence,
            data={
                "indicators": self.indicators,
                "signals": self.signals
            }
        )
    
    def _generate_prediction(self) -> tuple:
        """Generate prediction based on technical indicators"""
        trend = self.signals.get("trend", "NEUTRAL")
        momentum = self.signals.get("momentum", "NEUTRAL")
        rsi = self.indicators.get("rsi_14", 50)
        macd = self.indicators.get("macd", {})
        
        prediction = None
        confidence = 50
        
        # Buy signals
        buy_signals = 0
        sell_signals = 0
        
        # Trend analysis
        if trend == "BULLISH":
            buy_signals += 2
        elif trend == "BEARISH":
            sell_signals += 2
        
        # Momentum analysis
        if momentum == "OVERSOLD":
            buy_signals += 2
        elif momentum == "OVERBOUGHT":
            sell_signals += 2
        
        # RSI analysis
        if rsi < 30:
            buy_signals += 1
        elif rsi > 70:
            sell_signals += 1
        
        # MACD analysis
        if macd:
            macd_value = macd.get("macd", 0)
            signal_value = macd.get("signal", 0)
            histogram = macd.get("histogram", 0)
            
            if macd_value > signal_value and histogram > 0:
                buy_signals += 1
            elif macd_value < signal_value and histogram < 0:
                sell_signals += 1
        
        # Generate final prediction
        if buy_signals > sell_signals:
            prediction = "CALL"
            confidence = 50 + (buy_signals - sell_signals) * 5
        elif sell_signals > buy_signals:
            prediction = "PUT"
            confidence = 50 + (sell_signals - buy_signals) * 5
        else:
            prediction = None
            confidence = 30
        
        confidence = min(confidence, 85)
        
        return prediction, confidence
