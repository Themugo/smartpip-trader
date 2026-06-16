import unittest
from config import Settings


class TestSettings(unittest.TestCase):
    """Test Settings configuration"""
    
    def test_settings_initialization(self):
        """Test that Settings initializes with default values"""
        settings = Settings()
        
        self.assertEqual(settings.base_amount, 1.0)
        self.assertEqual(settings.min_confidence, 70)
        self.assertEqual(settings.stop_loss, 50)
        self.assertEqual(settings.take_profit, 100)
        self.assertEqual(settings.max_consecutive_losses, 3)
        self.assertFalse(settings.auto_trading)
    
    def test_settings_update(self):
        """Test that Settings can be updated"""
        settings = Settings()
        settings.update({"base_amount": 5.0, "min_confidence": 80})
        
        self.assertEqual(settings.base_amount, 5.0)
        self.assertEqual(settings.min_confidence, 80)
    
    def test_settings_to_dict(self):
        """Test that Settings can be converted to dictionary"""
        settings = Settings()
        settings_dict = settings.to_dict()
        
        self.assertIsInstance(settings_dict, dict)
        self.assertIn("base_amount", settings_dict)
        self.assertIn("min_confidence", settings_dict)
    
    def test_settings_enable_flags(self):
        """Test that analyzer enable flags work correctly"""
        settings = Settings()
        
        self.assertTrue(settings.enable_even_odd)
        self.assertTrue(settings.enable_rise_fall)
        self.assertTrue(settings.enable_over_under)
        self.assertTrue(settings.enable_match_diff)
        self.assertTrue(settings.enable_digit_analysis)


if __name__ == "__main__":
    unittest.main()
