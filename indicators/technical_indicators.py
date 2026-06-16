import numpy as np
from typing import List, Dict, Any, Optional
from collections import deque


class SMA:
    """Simple Moving Average"""
    
    @staticmethod
    def calculate(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_series(prices: List[float], period: int) -> List[Optional[float]]:
        """Calculate SMA series for all points"""
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(prices[i-period+1:i+1]) / period)
        return result


class EMA:
    """Exponential Moving Average"""
    
    @staticmethod
    def calculate(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_series(prices: List[float], period: int) -> List[Optional[float]]:
        """Calculate EMA series for all points"""
        if len(prices) < period:
            return [None] * len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        result = [ema]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            result.append(ema)
        
        return result


class RSI:
    """Relative Strength Index"""
    
    @staticmethod
    def calculate(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_series(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """Calculate RSI series for all points"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        result = [None]
        
        for i in range(period, len(prices)):
            avg_gain = np.mean(gains[i-period:i])
            avg_loss = np.mean(losses[i-period:i])
            
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                result.append(rsi)
        
        return result


class MACD:
    """Moving Average Convergence Divergence"""
    
    @staticmethod
    def calculate(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Optional[Dict[str, float]]:
        """Calculate MACD"""
        if len(prices) < slow_period + signal_period:
            return None
        
        ema_fast = EMA.calculate_series(prices, fast_period)
        ema_slow = EMA.calculate_series(prices, slow_period)
        
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is None or ema_slow[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(ema_fast[i] - ema_slow[i])
        
        # Filter out None values for signal line calculation
        macd_values = [v for v in macd_line if v is not None]
        if len(macd_values) < signal_period:
            return None
        
        signal_line = EMA.calculate_series(macd_values, signal_period)
        histogram = []
        
        for i in range(len(macd_line)):
            if macd_line[i] is None:
                histogram.append(None)
            else:
                idx = i - len(prices) + len(macd_values)
                if 0 <= idx < len(signal_line) and signal_line[idx] is not None:
                    histogram.append(macd_line[i] - signal_line[idx])
                else:
                    histogram.append(None)
        
        return {
            "macd": macd_line[-1],
            "signal": signal_line[-1],
            "histogram": histogram[-1]
        }


class BollingerBands:
    """Bollinger Bands"""
    
    @staticmethod
    def calculate(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None
        
        sma = SMA.calculate(prices, period)
        if sma is None:
            return None
        
        recent_prices = prices[-period:]
        std = np.std(recent_prices)
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        bandwidth = (upper_band - lower_band) / sma if sma != 0 else 0
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band,
            "bandwidth": bandwidth,
            "percent_b": (prices[-1] - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0
        }


class TechnicalIndicatorManager:
    """Manager for technical indicators"""
    
    def __init__(self):
        self.indicators = {
            "sma": SMA,
            "ema": EMA,
            "rsi": RSI,
            "macd": MACD,
            "bollinger": BollingerBands
        }
    
    def calculate_all(self, prices: List[float]) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        results = {}
        
        # SMA
        results["sma_10"] = SMA.calculate(prices, 10)
        results["sma_20"] = SMA.calculate(prices, 20)
        results["sma_50"] = SMA.calculate(prices, 50)
        
        # EMA
        results["ema_12"] = EMA.calculate(prices, 12)
        results["ema_26"] = EMA.calculate(prices, 26)
        
        # RSI
        results["rsi_14"] = RSI.calculate(prices, 14)
        results["rsi_7"] = RSI.calculate(prices, 7)
        
        # MACD
        results["macd"] = MACD.calculate(prices)
        
        # Bollinger Bands
        results["bollinger"] = BollingerBands.calculate(prices)
        
        return results
    
    def get_signal(self, prices: List[float]) -> Optional[Dict[str, str]]:
        """Generate trading signals from indicators"""
        if len(prices) < 50:
            return None
        
        indicators = self.calculate_all(prices)
        signals = {
            "trend": "NEUTRAL",
            "momentum": "NEUTRAL",
            "volatility": "NORMAL"
        }
        
        # Trend signal from SMA crossover
        sma_10 = indicators.get("sma_10")
        sma_20 = indicators.get("sma_20")
        if sma_10 and sma_20:
            if sma_10 > sma_20:
                signals["trend"] = "BULLISH"
            elif sma_10 < sma_20:
                signals["trend"] = "BEARISH"
        
        # Momentum signal from RSI
        rsi = indicators.get("rsi_14")
        if rsi:
            if rsi > 70:
                signals["momentum"] = "OVERBOUGHT"
            elif rsi < 30:
                signals["momentum"] = "OVERSOLD"
        
        # Volatility signal from Bollinger Bands
        bollinger = indicators.get("bollinger")
        if bollinger:
            if bollinger.get("bandwidth", 0) > 0.02:
                signals["volatility"] = "HIGH"
            elif bollinger.get("bandwidth", 0) < 0.01:
                signals["volatility"] = "LOW"
        
        return signals
