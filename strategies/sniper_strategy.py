from typing import Dict, Any, Optional, List
from models import Prediction
from backtesting.strategy import BacktestStrategy
from indicators import RSI, SMA, EMA, BollingerBands
import numpy as np


class SniperStrategy(BacktestStrategy):
    """Sniper trading strategy - high precision, selective entries"""
    
    def __init__(self, min_confidence: float = 85, max_risk: float = 0.02):
        super().__init__("sniper")
        self.min_confidence = min_confidence
        self.max_risk = max_risk
        self.confluence_score = 0
        self.market_regime = "NEUTRAL"
        self.last_signals = []
    
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate signal only when multiple factors align (sniper approach)"""
        price_history = data.get("price_history", [])
        if len(price_history) < 50:
            return None
        
        current_price = price_history[-1]
        
        # Fast market regime detection (optimized for speed)
        self.market_regime = self._detect_market_regime_fast(price_history)
        
        # Calculate confluence score (multiple indicators must agree)
        confluence = self._calculate_confluence_fast(price_history, current_price)
        self.confluence_score = confluence["score"]
        
        # Only trade if confluence is high
        if confluence["score"] < 3:
            return None
        
        # Calculate confidence based on confluence strength
        confidence = min(50 + (confluence["score"] * 10), 95)
        
        # Determine direction
        direction = confluence["direction"]
        
        # Adjust position size based on confidence and risk
        self._adjust_position_size(confidence, current_price)
        
        return Prediction(
            type="SNIPER",
            direction=direction,
            confidence=confidence,
            reason=f"Sniper entry - Confluence: {confluence['score']}/5, Regime: {self.market_regime}"
        )
    
    def _detect_market_regime_fast(self, price_history: List[float]) -> str:
        """Detect market regime (trending, ranging, volatile) - optimized for speed"""
        if len(price_history) < 20:
            return "NEUTRAL"
        
        recent = price_history[-20:]
        sma_10 = sum(recent[-10:]) / 10
        sma_20 = sum(recent) / 20
        
        # Fast trend detection
        if sma_10 > sma_20 * 1.003:
            return "BULLISH_TREND"
        elif sma_10 < sma_20 * 0.997:
            return "BEARISH_TREND"
        
        # Fast volatility detection
        price_range = max(recent) - min(recent)
        avg_price = sum(recent) / len(recent)
        cv = price_range / avg_price if avg_price > 0 else 0
        
        if cv > 0.025:
            return "HIGH_VOLATILITY"
        elif cv < 0.008:
            return "LOW_VOLATILITY"
        
        return "RANGING"
    
    def _detect_market_regime(self, price_history: List[float]) -> str:
        """Detect market regime (trending, ranging, volatile)"""
        if len(price_history) < 30:
            return "NEUTRAL"
        
        recent = price_history[-30:]
        sma_20 = sum(recent[-20:]) / 20
        sma_10 = sum(recent[-10:]) / 10
        
        # Trend detection
        if sma_10 > sma_20 * 1.002:
            return "BULLISH_TREND"
        elif sma_10 < sma_20 * 0.998:
            return "BEARISH_TREND"
        
        # Volatility detection
        std = np.std(recent)
        avg = np.mean(recent)
        cv = std / avg if avg > 0 else 0
        
        if cv > 0.02:
            return "HIGH_VOLATILITY"
        elif cv < 0.005:
            return "LOW_VOLATILITY"
        
        return "RANGING"
    
    def _calculate_confluence_fast(self, price_history: List[float], current_price: float) -> Dict[str, Any]:
        """Calculate confluence score from multiple indicators - optimized for speed"""
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        
        # 1. Fast RSI confluence (shorter period)
        rsi = RSI.calculate(price_history, 10)  # Faster RSI
        if rsi:
            if rsi < 35:
                bullish_signals += 1
                score += 1
            elif rsi > 65:
                bearish_signals += 1
                score += 1
            elif 45 < rsi < 55:
                score += 0.5  # Neutral zone
        
        # 2. Fast EMA confluence (shorter periods)
        ema_8 = EMA.calculate(price_history, 8)
        ema_16 = EMA.calculate(price_history, 16)
        if ema_8 and ema_16:
            if ema_8 > ema_16:
                bullish_signals += 1
                score += 1
            else:
                bearish_signals += 1
                score += 1
        
        # 3. Fast Bollinger Bands confluence
        bb = BollingerBands.calculate(price_history, 15, 2)  # Shorter period
        if bb:
            percent_b = bb.get("percent_b", 0.5)
            if percent_b < 0.25:
                bullish_signals += 1
                score += 1
            elif percent_b > 0.75:
                bearish_signals += 1
                score += 1
        
        # 4. Fast price momentum confluence
        if len(price_history) >= 3:
            momentum = (price_history[-1] - price_history[-3]) / price_history[-3]
            if momentum > 0.008:
                bullish_signals += 1
                score += 1
            elif momentum < -0.008:
                bearish_signals += 1
                score += 1
        
        # 5. Fast support/resistance confluence
        if len(price_history) >= 15:
            recent_high = max(price_history[-15:])
            recent_low = min(price_history[-15:])
            range_size = recent_high - recent_low
            
            # Near resistance
            if current_price > recent_high - (range_size * 0.15):
                bearish_signals += 1
                score += 1
            # Near support
            elif current_price < recent_low + (range_size * 0.15):
                bullish_signals += 1
                score += 1
        
        # Determine direction based on signal count
        if bullish_signals > bearish_signals:
            direction = "CALL"
        elif bearish_signals > bullish_signals:
            direction = "PUT"
        else:
            direction = None
        
        return {
            "score": score,
            "direction": direction,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals
        }
    
    def _calculate_confluence(self, price_history: List[float], current_price: float) -> Dict[str, Any]:
        """Calculate confluence score from multiple indicators"""
        score = 0
        bullish_signals = 0
        bearish_signals = 0
        
        # 1. RSI confluence
        rsi = RSI.calculate(price_history, 14)
        if rsi:
            if rsi < 30:
                bullish_signals += 1
                score += 1
            elif rsi > 70:
                bearish_signals += 1
                score += 1
            elif 40 < rsi < 60:
                score += 0.5  # Neutral zone
        
        # 2. EMA confluence
        ema_12 = EMA.calculate(price_history, 12)
        ema_26 = EMA.calculate(price_history, 26)
        if ema_12 and ema_26:
            if ema_12 > ema_26:
                bullish_signals += 1
                score += 1
            else:
                bearish_signals += 1
                score += 1
        
        # 3. Bollinger Bands confluence
        bb = BollingerBands.calculate(price_history, 20, 2)
        if bb:
            percent_b = bb.get("percent_b", 0.5)
            if percent_b < 0.2:
                bullish_signals += 1
                score += 1
            elif percent_b > 0.8:
                bearish_signals += 1
                score += 1
        
        # 4. Price momentum confluence
        if len(price_history) >= 5:
            momentum = (price_history[-1] - price_history[-5]) / price_history[-5]
            if momentum > 0.005:
                bullish_signals += 1
                score += 1
            elif momentum < -0.005:
                bearish_signals += 1
                score += 1
        
        # 5. Support/Resistance confluence
        if len(price_history) >= 20:
            recent_high = max(price_history[-20:])
            recent_low = min(price_history[-20:])
            range_size = recent_high - recent_low
            
            # Near resistance
            if current_price > recent_high - (range_size * 0.1):
                bearish_signals += 1
                score += 1
            # Near support
            elif current_price < recent_low + (range_size * 0.1):
                bullish_signals += 1
                score += 1
        
        # Determine direction based on signal count
        if bullish_signals > bearish_signals:
            direction = "CALL"
        elif bearish_signals > bullish_signals:
            direction = "PUT"
        else:
            direction = None
        
        return {
            "score": score,
            "direction": direction,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals
        }
    
    def _adjust_position_size(self, confidence: float, current_price: float):
        """Adjust position size based on confidence and risk"""
        # Higher confidence = larger position (within risk limits)
        risk_adjusted_size = self.base_amount * (confidence / 100)
        
        # Ensure position doesn't exceed max risk
        max_position = self.balance * self.max_risk
        self.current_amount = min(risk_adjusted_size, max_position)
    
    def execute_trade(self, prediction: Prediction, price: float, amount: float = 1.0) -> Dict[str, Any]:
        """Execute trade with sniper precision"""
        # Use adjusted position size
        trade = super().execute_trade(prediction, price, self.current_amount)
        trade["confluence_score"] = self.confluence_score
        trade["market_regime"] = self.market_regime
        return trade
