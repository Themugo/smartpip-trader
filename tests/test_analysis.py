import unittest
from analysis import EvenOddAnalyzer, RiseFallAnalyzer, TechnicalAnalyzer


class TestEvenOddAnalyzer(unittest.TestCase):
    """Test EvenOddAnalyzer"""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        analyzer = EvenOddAnalyzer()
        
        self.assertTrue(analyzer.is_enabled())
    
    def test_analyze_with_sufficient_data(self):
        """Test analysis with sufficient data"""
        analyzer = EvenOddAnalyzer()
        data = {
            "last_20_digits": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
            "price_history": [100, 101, 102, 103, 104]
        }
        
        result = analyzer.analyze(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.model_name, "even_odd")
    
    def test_analyze_with_insufficient_data(self):
        """Test analysis with insufficient data (early termination)"""
        analyzer = EvenOddAnalyzer()
        data = {
            "last_20_digits": [1, 2, 3],
            "price_history": [100, 101, 102]
        }
        
        result = analyzer.analyze(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.confidence, 0)
        self.assertTrue(result.data.get("skipped"))
    
    def test_analyzer_enable_disable(self):
        """Test enabling/disabling analyzer"""
        analyzer = EvenOddAnalyzer()
        
        analyzer.set_enabled(False)
        self.assertFalse(analyzer.is_enabled())
        
        analyzer.set_enabled(True)
        self.assertTrue(analyzer.is_enabled())


class TestRiseFallAnalyzer(unittest.TestCase):
    """Test RiseFallAnalyzer"""
    
    def test_analyze_with_sufficient_data(self):
        """Test analysis with sufficient data"""
        analyzer = RiseFallAnalyzer()
        data = {
            "last_20_digits": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
            "price_history": list(range(100, 150))
        }
        
        result = analyzer.analyze(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.model_name, "rise_fall")
    
    def test_analyze_with_insufficient_data(self):
        """Test analysis with insufficient data"""
        analyzer = RiseFallAnalyzer()
        data = {
            "last_20_digits": [1, 2, 3],
            "price_history": [100, 101, 102]
        }
        
        result = analyzer.analyze(data)
        
        self.assertTrue(result.data.get("skipped"))


class TestTechnicalAnalyzer(unittest.TestCase):
    """Test TechnicalAnalyzer"""
    
    def test_analyze_with_sufficient_data(self):
        """Test technical analysis with sufficient data"""
        analyzer = TechnicalAnalyzer()
        digits = [i % 10 for i in range(30)]
        data = {
            "last_20_digits": digits,
            "price_history": list(range(100, 150))
        }
        
        result = analyzer.analyze(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.model_name, "technical")
        self.assertIn("indicators", result.data)
        self.assertIn("signals", result.data)
    
    def test_analyze_with_insufficient_data(self):
        """Test technical analysis with insufficient data"""
        analyzer = TechnicalAnalyzer()
        data = {
            "last_20_digits": [1, 2, 3],
            "price_history": [100, 101, 102]
        }
        
        result = analyzer.analyze(data)
        
        self.assertTrue(result.data.get("skipped"))
    
    def test_indicator_calculation(self):
        """Test that indicators are calculated correctly"""
        analyzer = TechnicalAnalyzer()
        digits = [i % 10 for i in range(30)]
        data = {
            "last_20_digits": digits,
            "price_history": list(range(100, 150))
        }
        
        result = analyzer.analyze(data)
        indicators = result.data.get("indicators", {})
        
        self.assertIn("sma_10", indicators)
        self.assertIn("rsi_14", indicators)
        self.assertIn("macd", indicators)
        self.assertIn("bollinger", indicators)


if __name__ == "__main__":
    unittest.main()
