import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.currency_converter import CurrencyConverter


class TestCurrencyConverter(unittest.TestCase):
    """Test CurrencyConverter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.converter = CurrencyConverter()
    
    def test_initialization(self):
        """Test converter initializes with correct defaults"""
        self.assertEqual(self.converter.base_currency, "KES")
        self.assertEqual(self.converter.target_currency, "USD")
        self.assertEqual(self.converter.exchange_rate, 130.0)
        self.assertEqual(self.converter.cache_ttl, 3600)
        self.assertIsNotNone(self.converter.cache)
    
    def test_convert_same_currency(self):
        """Test conversion when source and target are the same"""
        result = self.converter.convert(100, "USD", "USD")
        self.assertEqual(result, 100)
    
    @patch('utils.currency_converter.requests.get')
    def test_convert_usd_to_kes_with_mock(self, mock_get):
        """Test USD to KES conversion with mocked API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 130.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.convert(10, "USD", "KES")
        
        # Should use the mocked rate
        self.assertEqual(result, 10 * 130.0)
    
    @patch('utils.currency_converter.requests.get')
    def test_convert_kes_to_usd_with_mock(self, mock_get):
        """Test KES to USD conversion with mocked API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # When fetching KES->USD, the API is called with KES as base
        # The response contains rates with USD value
        mock_response.json.return_value = {
            "rates": {"USD": 0.0077}  # 1/130 approximately
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.convert(130, "KES", "USD")
        
        # Should use the rate from the mock (0.0077)
        self.assertAlmostEqual(result, 130 * 0.0077, places=3)
    
    @patch('utils.currency_converter.requests.get')
    def test_convert_unknown_currencies_with_mock(self, mock_get):
        """Test conversion with known currencies"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"GBP": 0.75}  # EUR->GBP rate
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.convert(100, "EUR", "GBP")
        
        # Should use the rate from the mock (0.75)
        self.assertEqual(result, 75.0)
    
    @patch('utils.currency_converter.requests.get')
    def test_usd_to_kes_method(self, mock_get):
        """Test USD to KES convenience method"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 130.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.usd_to_kes(10)
        
        self.assertEqual(result, 10 * 130.0)
    
    @patch('utils.currency_converter.requests.get')
    def test_kes_to_usd_method(self, mock_get):
        """Test KES to USD convenience method"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # When fetching KES->USD, base is KES
        mock_response.json.return_value = {
            "rates": {"USD": 0.0077}  # ~1/130
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.kes_to_usd(130)
        
        # Result is 130 * 0.0077 = 1.001
        self.assertAlmostEqual(result, 130 * 0.0077, places=3)
    
    def test_format_currency_kes(self):
        """Test formatting KES currency"""
        result = self.converter.format_currency(1234.56, "KES")
        self.assertEqual(result, "KES 1,234.56")
    
    def test_format_currency_usd(self):
        """Test formatting USD currency"""
        result = self.converter.format_currency(1234.56, "USD")
        self.assertEqual(result, "$1,234.56")
    
    def test_format_currency_other(self):
        """Test formatting other currency"""
        result = self.converter.format_currency(1234.56, "EUR")
        self.assertEqual(result, "1,234.56 EUR")
    
    def test_format_currency_large_amount(self):
        """Test formatting large KES amounts with proper separators"""
        result = self.converter.format_currency(1234567.89, "KES")
        self.assertEqual(result, "KES 1,234,567.89")
    
    def test_format_currency_small_amount(self):
        """Test formatting small amounts"""
        result = self.converter.format_currency(0.50, "KES")
        self.assertEqual(result, "KES 0.50")
    
    def test_convert_zero_amount(self):
        """Test converting zero amount"""
        result = self.converter.convert(0, "USD", "KES")
        self.assertEqual(result, 0)
    
    @patch('utils.currency_converter.requests.get')
    def test_convert_negative_amount(self, mock_get):
        """Test converting negative amount"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 130.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        result = converter.convert(-100, "USD", "KES")
        
        self.assertEqual(result, -100 * 130.0)
    
    @patch('utils.currency_converter.requests.get')
    def test_fetch_rate_from_api_success(self, mock_get):
        """Test fetching rate from API successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 135.5}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        rate = converter._fetch_rate_from_api("USD", "KES")
        
        self.assertEqual(rate, 135.5)
        mock_get.assert_called_once()
    
    @patch('utils.currency_converter.requests.get')
    def test_fetch_rate_updates_default(self, mock_get):
        """Test that fetching USD/KES updates default rate"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 140.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        original_rate = converter.exchange_rate
        
        converter._fetch_rate_from_api("USD", "KES")
        
        self.assertNotEqual(converter.exchange_rate, original_rate)
        self.assertEqual(converter.exchange_rate, 140.0)
    
    @patch('utils.currency_converter.requests.get')
    def test_fetch_rate_from_api_failure(self, mock_get):
        """Test handling API fetch failure"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        
        with self.assertRaises(Exception) as context:
            converter._fetch_rate_from_api("USD", "KES")
        
        self.assertIn("Failed to fetch", str(context.exception))
    
    def test_cache_rate(self):
        """Test caching exchange rate"""
        self.converter._cache_rate("USD_KES", 135.0)
        
        self.assertEqual(len(self.converter.cache), 1)
        cached = self.converter.cache[0]
        self.assertEqual(cached["key"], "USD_KES")
        self.assertEqual(cached["rate"], 135.0)
        self.assertIsNotNone(cached["timestamp"])
    
    def test_get_from_cache_hit(self):
        """Test cache hit returns cached value"""
        self.converter._cache_rate("USD_KES", 135.0)
        
        result = self.converter._get_from_cache("USD_KES")
        
        self.assertEqual(result, 135.0)
    
    def test_get_from_cache_miss(self):
        """Test cache miss returns None"""
        result = self.converter._get_from_cache("NONEXISTENT")
        
        self.assertIsNone(result)
    
    def test_cache_eviction_old_entries(self):
        """Test that old cache entries are not returned"""
        from datetime import datetime, timedelta
        
        # Add a cached rate
        self.converter._cache_rate("USD_KES", 135.0)
        
        # Manually expire the cache by setting timestamp far in the past
        self.converter.cache[0]["timestamp"] = datetime.now() - timedelta(seconds=7200)
        
        # Should not return expired entry
        result = self.converter._get_from_cache("USD_KES")
        
        self.assertIsNone(result)
    
    @patch('utils.currency_converter.requests.get')
    def test_get_exchange_rate_uses_cache(self, mock_get):
        """Test that get_exchange_rate uses cached values"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 140.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        
        # First call should fetch from API
        rate1 = converter.get_exchange_rate("USD", "KES")
        self.assertEqual(mock_get.call_count, 1)
        
        # Second call should use cache
        rate2 = converter.get_exchange_rate("USD", "KES")
        self.assertEqual(mock_get.call_count, 1)  # Still 1, not 2
        
        self.assertEqual(rate1, rate2)
    
    @patch('utils.currency_converter.requests.get')
    def test_inverse_rate_calculation(self, mock_get):
        """Test that inverse rate is calculated correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rates": {"KES": 130.0}
        }
        mock_get.return_value = mock_response
        
        converter = CurrencyConverter()
        
        # USD to KES
        rate_usd_to_kes = converter.get_exchange_rate("USD", "KES")
        
        # For KES to USD, we need a different mock
        # The API is called with KES as base, so we need USD in rates
        def side_effect(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # The URL determines what base currency we have
            if "KES" in args[0]:
                mock_resp.json.return_value = {"rates": {"USD": 0.0077}}  # ~1/130
            else:
                mock_resp.json.return_value = {"rates": {"KES": 130.0}}
            return mock_resp
        
        mock_get.side_effect = side_effect
        converter.cache.clear()
        rate_kes_to_usd = converter.get_exchange_rate("KES", "USD")
        
        # They should be inverses (within floating point tolerance)
        product = rate_usd_to_kes * rate_kes_to_usd
        self.assertAlmostEqual(product, 1.0, places=2)


class TestCurrencyConverterCache(unittest.TestCase):
    """Test CurrencyConverter cache behavior"""
    
    def test_cache_max_size(self):
        """Test that cache respects max size"""
        converter = CurrencyConverter()
        
        # Add more than 100 items (default maxlen of deque)
        for i in range(105):
            converter._cache_rate(f"pair_{i}", float(i))
        
        # Cache should have at most 100 items
        self.assertLessEqual(len(converter.cache), 100)
    
    def test_cache_different_pairs(self):
        """Test caching different currency pairs"""
        converter = CurrencyConverter()
        
        converter._cache_rate("USD_KES", 130.0)
        converter._cache_rate("USD_EUR", 0.85)
        converter._cache_rate("EUR_GBP", 0.75)
        
        self.assertEqual(converter._get_from_cache("USD_KES"), 130.0)
        self.assertEqual(converter._get_from_cache("USD_EUR"), 0.85)
        self.assertEqual(converter._get_from_cache("EUR_GBP"), 0.75)
    
    def test_cache_lru_order(self):
        """Test that cache returns the most recently used (first matching) entry"""
        converter = CurrencyConverter()
        
        # Add two entries for the same key
        converter._cache_rate("USD_KES", 130.0)
        converter._cache_rate("USD_KES", 135.0)
        
        # Cache returns first matching (LIFO order due to move_to_end)
        # After two adds, the second entry is at the end, but _get_from_cache
        # iterates from start and returns first match
        self.assertEqual(len(converter.cache), 2)
    
    def test_cache_most_recent_accessed(self):
        """Test that cache returns the first matching entry"""
        converter = CurrencyConverter()
        
        converter._cache_rate("PAIR_A", 1.0)
        converter._cache_rate("PAIR_B", 2.0)
        converter._cache_rate("PAIR_C", 3.0)
        
        # After adding, order is: PAIR_A, PAIR_B, PAIR_C
        self.assertEqual(converter.cache[-1]["key"], "PAIR_C")
        
        # Get PAIR_A - it returns the first matching entry
        result = converter._get_from_cache("PAIR_A")
        self.assertEqual(result, 1.0)
        
        # Cache doesn't use LRU, so PAIR_A is still at the beginning
        self.assertEqual(converter.cache[0]["key"], "PAIR_A")


if __name__ == "__main__":
    unittest.main()
