import unittest
import numpy as np
from indicators import SMA, EMA, RSI, MACD, BollingerBands, TechnicalIndicatorManager


class TestSMA(unittest.TestCase):
    """Test SMA indicator"""
    
    def test_sma_calculate(self):
        """Test SMA calculation"""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma = SMA.calculate(prices, 3)
        
        self.assertEqual(sma, 4.0)
    
    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data"""
        prices = [1.0, 2.0]
        sma = SMA.calculate(prices, 5)
        
        self.assertIsNone(sma)
    
    def test_sma_series(self):
        """Test SMA series calculation"""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        series = SMA.calculate_series(prices, 3)
        
        self.assertEqual(len(series), 5)
        self.assertIsNone(series[0])
        self.assertIsNone(series[1])
        self.assertEqual(series[2], 2.0)
        self.assertEqual(series[3], 3.0)
        self.assertEqual(series[4], 4.0)


class TestEMA(unittest.TestCase):
    """Test EMA indicator"""
    
    def test_ema_calculate(self):
        """Test EMA calculation"""
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        ema = EMA.calculate(prices, 3)
        
        self.assertIsNotNone(ema)
        self.assertGreater(ema, 0)
    
    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data"""
        prices = [1.0]
        ema = EMA.calculate(prices, 5)
        
        self.assertIsNone(ema)


class TestRSI(unittest.TestCase):
    """Test RSI indicator"""
    
    def test_rsi_calculate(self):
        """Test RSI calculation"""
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 111, 113, 112, 114, 116]
        rsi = RSI.calculate(prices, 14)
        
        self.assertIsNotNone(rsi)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data"""
        prices = [100, 102, 104]
        rsi = RSI.calculate(prices, 14)
        
        self.assertIsNone(rsi)


class TestMACD(unittest.TestCase):
    """Test MACD indicator"""
    
    def test_macd_calculate(self):
        """Test MACD calculation"""
        prices = list(range(50, 100))
        macd = MACD.calculate(prices)
        
        self.assertIsNotNone(macd)
        self.assertIn("macd", macd)
        self.assertIn("signal", macd)
        self.assertIn("histogram", macd)
    
    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data"""
        prices = [100, 102, 104]
        macd = MACD.calculate(prices)
        
        self.assertIsNone(macd)


class TestBollingerBands(unittest.TestCase):
    """Test Bollinger Bands indicator"""
    
    def test_bollinger_calculate(self):
        """Test Bollinger Bands calculation"""
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 111, 113, 112, 114, 116, 115, 117, 119, 118, 120]
        bb = BollingerBands.calculate(prices, 20, 2.0)
        
        self.assertIsNotNone(bb)
        self.assertIn("upper", bb)
        self.assertIn("middle", bb)
        self.assertIn("lower", bb)
        self.assertIn("bandwidth", bb)
        self.assertIn("percent_b", bb)
        
        self.assertGreater(bb["upper"], bb["middle"])
        self.assertGreater(bb["middle"], bb["lower"])
    
    def test_bollinger_insufficient_data(self):
        """Test Bollinger Bands with insufficient data"""
        prices = [100, 102, 104]
        bb = BollingerBands.calculate(prices, 20, 2.0)
        
        self.assertIsNone(bb)


class TestTechnicalIndicatorManager(unittest.TestCase):
    """Test TechnicalIndicatorManager"""
    
    def test_calculate_all(self):
        """Test calculating all indicators"""
        manager = TechnicalIndicatorManager()
        prices = list(range(50, 150))
        
        results = manager.calculate_all(prices)
        
        self.assertIn("sma_10", results)
        self.assertIn("sma_20", results)
        self.assertIn("ema_12", results)
        self.assertIn("rsi_14", results)
        self.assertIn("macd", results)
        self.assertIn("bollinger", results)
    
    def test_get_signal(self):
        """Test signal generation"""
        manager = TechnicalIndicatorManager()
        prices = list(range(50, 150))
        
        signals = manager.get_signal(prices)
        
        self.assertIsNotNone(signals)
        self.assertIn("trend", signals)
        self.assertIn("momentum", signals)
        self.assertIn("volatility", signals)


if __name__ == "__main__":
    unittest.main()
