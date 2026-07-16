"""
Failover Manager Implementation
===============================

Manages service failover with multiple strategies.
"""

import asyncio
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Dict, List, TypeVar, Generic
from functools import wraps

logger = logging.getLogger(__name__)
T = TypeVar('T')


class FailoverStrategy(Enum):
    """Available failover strategies"""
    FAILOVER = "failover"           # Try next endpoint
    CIRCUIT_BREAKER = "circuit_breaker"  # Use circuit breaker
    THROTTLE = "throttle"          # Slow down and retry
    GRACEFUL_DEGRADE = "graceful_degrade"  # Return degraded response
    CACHE_FALLBACK = "cache_fallback"  # Use cached data


@dataclass
class Endpoint:
    """Service endpoint configuration"""
    name: str
    url: str
    priority: int = 0  # Lower = higher priority
    is_healthy: bool = True
    last_check: Optional[float] = None
    latency_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def health_score(self) -> float:
        """Calculate health score (0-100)"""
        if not self.is_healthy:
            return 0.0
        total = self.success_count + self.error_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100


@dataclass
class FailoverConfig:
    """Configuration for failover behavior"""
    strategy: FailoverStrategy = FailoverStrategy.FAILOVER
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    unhealthy_threshold: int = 3  # Consecutive failures to mark unhealthy
    healthy_threshold: int = 2    # Consecutive successes to mark healthy
    enable_cache: bool = True
    cache_ttl: float = 300.0      # Cache TTL in seconds


@dataclass
class FailoverStats:
    """Statistics for failover monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    failovers_triggered: int = 0
    endpoint_switches: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    mean_latency_ms: float = 0.0
    last_failure_time: Optional[float] = None
    current_endpoint: Optional[str] = None
    healthy_endpoints: int = 0
    unhealthy_endpoints: int = 0


class FailoverManager(Generic[T]):
    """
    Manages failover between multiple service endpoints.
    
    Features:
    - Multiple failover strategies
    - Health checking
    - Automatic endpoint switching
    - Response caching
    - Statistics tracking
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[FailoverConfig] = None
    ):
        self.name = name
        self.config = config or FailoverConfig()
        
        self._endpoints: Dict[str, Endpoint] = {}
        self._endpoint_order: List[str] = []
        self._current_index = 0
        self._stats = FailoverStats()
        self._cache: Dict[str, tuple[Any, float]] = {}  # key -> (value, expiry)
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    def add_endpoint(
        self,
        name: str,
        url: str,
        priority: int = 0
    ) -> None:
        """Add a service endpoint"""
        endpoint = Endpoint(name=name, url=url, priority=priority)
        self._endpoints[name] = endpoint
        
        # Sort by priority
        self._endpoint_order = sorted(
            self._endpoints.keys(),
            key=lambda n: self._endpoints[n].priority
        )
        
        logger.info(f"Added failover endpoint: {name} at {url} (priority: {priority})")
    
    def remove_endpoint(self, name: str) -> None:
        """Remove a service endpoint"""
        if name in self._endpoints:
            del self._endpoints[name]
            self._endpoint_order.remove(name)
            logger.info(f"Removed failover endpoint: {name}")
    
    def _get_current_endpoint(self) -> Optional[Endpoint]:
        """Get the current active endpoint"""
        for name in self._endpoint_order:
            ep = self._endpoints[name]
            if ep.is_healthy:
                return ep
        return None
    
    def _record_success(self, endpoint: Endpoint, latency: float) -> None:
        """Record successful request"""
        endpoint.success_count += 1
        endpoint.error_count = 0
        endpoint.latency_ms = latency
        endpoint.last_check = time.time()
        
        if not endpoint.is_healthy:
            endpoint.is_healthy = True
            logger.info(f"Endpoint {endpoint.name} marked as healthy")
        
        self._stats.successful_requests += 1
        self._update_mean_latency(latency)
    
    def _record_failure(self, endpoint: Endpoint) -> None:
        """Record failed request"""
        endpoint.error_count += 1
        endpoint.last_check = time.time()
        
        if endpoint.error_count >= self.config.unhealthy_threshold:
            endpoint.is_healthy = False
            logger.warning(f"Endpoint {endpoint.name} marked as unhealthy")
        
        self._stats.failed_requests += 1
        self._stats.last_failure_time = time.time()
    
    def _update_mean_latency(self, latency: float) -> None:
        """Update mean latency with exponential moving average"""
        alpha = 0.1
        self._stats.mean_latency_ms = (
            alpha * latency + (1 - alpha) * self._stats.mean_latency_ms
        )
    
    def _get_next_endpoint(self) -> Optional[Endpoint]:
        """Get next available endpoint in failover order"""
        if not self._endpoint_order:
            return None
        
        # Find first healthy endpoint after current
        for i in range(len(self._endpoint_order)):
            idx = (self._current_index + i) % len(self._endpoint_order)
            ep = self._endpoints[self._endpoint_order[idx]]
            if ep.is_healthy:
                self._current_index = (idx + 1) % len(self._endpoint_order)
                return ep
        
        return None
    
    def _update_stats(self) -> None:
        """Update failover statistics"""
        self._stats.total_requests = (
            self._stats.successful_requests + self._stats.failed_requests
        )
        self._stats.healthy_endpoints = sum(
            1 for ep in self._endpoints.values() if ep.is_healthy
        )
        self._stats.unhealthy_endpoints = len(self._endpoints) - self._stats.healthy_endpoints
        
        current = self._get_current_endpoint()
        self._stats.current_endpoint = current.name if current else None
    
    async def call(
        self,
        func: Callable[..., T],
        *args,
        cache_key: Optional[str] = None,
        fallback: Optional[Callable[..., T]] = None,
        **kwargs
    ) -> T:
        """
        Execute a function with failover support.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            cache_key: Optional cache key for result caching
            fallback: Optional fallback function
            **kwargs: Keyword arguments
            
        Returns:
            Result of the function
            
        Raises:
            Exception: If all endpoints fail
        """
        self._stats.total_requests += 1
        
        # Check cache first
        if cache_key and self.config.enable_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                self._stats.cache_hits += 1
                return cached
        
        last_exception = None
        retries = 0
        
        while retries < self.config.max_retries:
            endpoint = self._get_current_endpoint()
            
            if not endpoint:
                # No healthy endpoints
                if fallback:
                    logger.warning(f"All endpoints failed for '{self.name}', using fallback")
                    self._stats.failovers_triggered += 1
                    return fallback(*args, **kwargs)
                
                raise FailoverExhaustedError(
                    f"All endpoints exhausted for '{self.name}'"
                )
            
            start_time = time.time()
            
            try:
                # Wrap function with endpoint URL
                kwargs_with_url = {**kwargs, "_endpoint_url": endpoint.url}
                result = await func(*args, **kwargs_with_url)
                
                latency = (time.time() - start_time) * 1000
                self._record_success(endpoint, latency)
                
                # Cache result if enabled
                if cache_key and self.config.enable_cache:
                    self._cache[cache_key] = (result, time.time() + self.config.cache_ttl)
                
                self._update_stats()
                return result
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                self._record_failure(endpoint)
                last_exception = e
                
                logger.warning(
                    f"Endpoint {endpoint.name} failed: {e}. "
                    f"Retrying with next endpoint..."
                )
                
                self._stats.failovers_triggered += 1
                self._stats.endpoint_switches += 1
                
                retries += 1
                
                if retries < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * retries)
        
        # All retries exhausted
        if fallback:
            logger.warning(f"All retries exhausted for '{self.name}', using fallback")
            return fallback(*args, **kwargs)
        
        raise FailoverExhaustedError(
            f"All retries exhausted for '{self.name}': {last_exception}"
        ) from last_exception
    
    def _get_cached(self, key: str) -> Optional[T]:
        """Get cached value if not expired"""
        if key not in self._cache:
            self._stats.cache_misses += 1
            return None
        
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            self._stats.cache_misses += 1
            return None
        
        return value
    
    def invalidate_cache(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    async def health_check_endpoint(self, endpoint: Endpoint) -> bool:
        """Perform health check on an endpoint"""
        import httpx
        
        try:
            async with httpx.AsyncClient(
                timeout=self.config.health_check_timeout
            ) as client:
                response = await client.get(endpoint.url)
                
                if response.status_code < 500:
                    endpoint.is_healthy = True
                    endpoint.success_count += 1
                    endpoint.error_count = 0
                    return True
                else:
                    endpoint.error_count += 1
                    if endpoint.error_count >= self.config.unhealthy_threshold:
                        endpoint.is_healthy = False
                    return False
                    
        except Exception as e:
            endpoint.error_count += 1
            endpoint.last_check = time.time()
            if endpoint.error_count >= self.config.unhealthy_threshold:
                endpoint.is_healthy = False
            logger.debug(f"Health check failed for {endpoint.name}: {e}")
            return False
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
        while self._running:
            try:
                for endpoint in self._endpoints.values():
                    await self.health_check_endpoint(endpoint)
                    self._update_stats()
                
                # Clean expired cache entries
                current_time = time.time()
                expired = [k for k, (_, exp) in self._cache.items() if current_time > exp]
                for k in expired:
                    del self._cache[k]
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)
    
    async def start(self) -> None:
        """Start the failover manager"""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Failover manager '{self.name}' started")
    
    async def stop(self) -> None:
        """Stop the failover manager"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Failover manager '{self.name}' stopped")
    
    def get_stats(self) -> FailoverStats:
        """Get failover statistics"""
        self._update_stats()
        return self._stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        self._update_stats()
        
        return {
            "name": self.name,
            "strategy": self.config.strategy.value,
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "failovers_triggered": self._stats.failovers_triggered,
                "endpoint_switches": self._stats.endpoint_switches,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "mean_latency_ms": round(self._stats.mean_latency_ms, 2),
                "success_rate": round(
                    self._stats.successful_requests / max(1, self._stats.total_requests) * 100,
                    2
                )
            },
            "endpoints": {
                name: {
                    "url": ep.url,
                    "priority": ep.priority,
                    "is_healthy": ep.is_healthy,
                    "health_score": round(ep.health_score, 2),
                    "latency_ms": round(ep.latency_ms, 2),
                    "success_count": ep.success_count,
                    "error_count": ep.error_count,
                    "last_check": ep.last_check
                }
                for name, ep in self._endpoints.items()
            },
            "current_endpoint": self._stats.current_endpoint,
            "healthy_endpoints": self._stats.healthy_endpoints,
            "unhealthy_endpoints": self._stats.unhealthy_endpoints
        }


class FailoverExhaustedError(Exception):
    """Raised when all failover attempts are exhausted"""
    pass
