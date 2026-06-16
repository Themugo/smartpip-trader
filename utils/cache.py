import hashlib
import json
import time
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheManager:
    """LRU Cache for analysis results to reduce redundant computations"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 5):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of items in cache
            ttl: Time to live in seconds for cache entries
        """
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.timestamps: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, data: Dict[str, Any]) -> str:
        """Generate cache key from data"""
        # Create a deterministic hash of the data
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get(self, data: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached result if available and not expired
        
        Args:
            data: Input data to generate cache key
            
        Returns:
            Cached result if available, None otherwise
        """
        key = self._generate_key(data)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        # Check if entry is expired
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        
        logger.debug(f"Cache hit for key {key[:8]}... (hit rate: {self.hit_rate:.2%})")
        return self.cache[key]
    
    def set(self, data: Dict[str, Any], result: Any):
        """
        Cache a result
        
        Args:
            data: Input data to generate cache key
            result: Result to cache
        """
        key = self._generate_key(data)
        
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[key] = result
        self.timestamps[key] = time.time()
        self.cache.move_to_end(key)
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "ttl": self.ttl
        }
