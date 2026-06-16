import unittest
import time
from utils import CacheManager, PerformanceMetrics, RateLimiter


class TestCacheManager(unittest.TestCase):
    """Test CacheManager functionality"""
    
    def test_cache_set_get(self):
        """Test basic cache set and get"""
        cache = CacheManager(max_size=10, ttl=5)
        
        cache.set({"test": "data"}, "result")
        result = cache.get({"test": "data"})
        
        self.assertEqual(result, "result")
    
    def test_cache_miss(self):
        """Test cache miss for non-existent key"""
        cache = CacheManager(max_size=10, ttl=5)
        
        result = cache.get({"nonexistent": "data"})
        
        self.assertIsNone(result)
    
    def test_cache_hit_rate(self):
        """Test cache hit rate calculation"""
        cache = CacheManager(max_size=10, ttl=5)
        
        cache.set({"test": "data"}, "result")
        cache.get({"test": "data"})  # Hit
        cache.get({"miss": "data"})  # Miss
        
        self.assertGreater(cache.hit_rate, 0)
        self.assertLess(cache.hit_rate, 1)
    
    def test_cache_clear(self):
        """Test cache clearing"""
        cache = CacheManager(max_size=10, ttl=5)
        
        cache.set({"test": "data"}, "result")
        cache.clear()
        
        self.assertEqual(cache.size, 0)
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.misses, 0)


class TestPerformanceMetrics(unittest.TestCase):
    """Test PerformanceMetrics functionality"""
    
    def test_counter_increment(self):
        """Test counter increment"""
        metrics = PerformanceMetrics()
        
        metrics.increment_counter("test")
        metrics.increment_counter("test", 5)
        
        self.assertEqual(metrics.get_counter("test"), 6)
    
    def test_timing(self):
        """Test timing measurements"""
        metrics = PerformanceMetrics()
        
        metrics.start_timer("operation")
        time.sleep(0.01)
        duration = metrics.stop_timer("operation")
        
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 0)
    
    def test_record_timing(self):
        """Test direct timing recording"""
        metrics = PerformanceMetrics()
        
        metrics.record_timing("test", 0.5)
        metrics.record_timing("test", 0.7)
        
        avg = metrics.get_average("test")
        
        self.assertEqual(avg, 0.6)
    
    def test_percentile(self):
        """Test percentile calculation"""
        metrics = PerformanceMetrics()
        
        for i in range(100):
            metrics.record_timing("test", i)
        
        p50 = metrics.get_percentile("test", 50)
        p95 = metrics.get_percentile("test", 95)
        
        self.assertEqual(p50, 50)
        self.assertEqual(p95, 95)
    
    def test_metrics_summary(self):
        """Test metrics summary generation"""
        metrics = PerformanceMetrics()
        
        metrics.increment_counter("test")
        metrics.record_timing("operation", 0.5)
        
        summary = metrics.get_summary()
        
        self.assertIn("counters", summary)
        self.assertIn("timings", summary)


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter functionality"""
    
    def test_rate_limit_allow(self):
        """Test that requests are allowed under limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            self.assertTrue(limiter.is_allowed("test_client"))
    
    def test_rate_limit_block(self):
        """Test that requests are blocked over limit"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed("test_client")
        
        self.assertFalse(limiter.is_allowed("test_client"))
    
    def test_rate_limit_remaining(self):
        """Test remaining requests calculation"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("test_client")
        
        remaining = limiter.get_remaining("test_client")
        
        self.assertEqual(remaining, 7)
    
    def test_rate_limit_different_clients(self):
        """Test that different clients have separate limits"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed("client1")
        
        self.assertFalse(limiter.is_allowed("client1"))
        self.assertTrue(limiter.is_allowed("client2"))
    
    def test_rate_limit_reset(self):
        """Test rate limit reset"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            limiter.is_allowed("test_client")
        
        limiter.reset("test_client")
        
        self.assertTrue(limiter.is_allowed("test_client"))


if __name__ == "__main__":
    unittest.main()
