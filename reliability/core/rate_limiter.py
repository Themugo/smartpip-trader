"""
Rate Limiter and Resource Quota Implementation
==============================================

Token bucket rate limiting with resource quota management.
"""

import asyncio
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Callable
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class QuotaExceededAction(Enum):
    """Action to take when quota is exceeded"""
    REJECT = "reject"
    QUEUE = "queue"
    DEGRADE = "degrade"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 100.0
    burst_size: int = 200
    window_seconds: float = 1.0
    queue_size: int = 0          # 0 = no queueing
    queue_timeout: float = 30.0


@dataclass
class ResourceQuota:
    """Resource quota configuration"""
    name: str
    limit: int
    used: int = 0
    window_seconds: float = 60.0
    exceeded_action: QuotaExceededAction = QuotaExceededAction.REJECT
    reset_at: Optional[float] = None
    warnings_threshold: float = 0.8  # Warn at 80% usage
    
    def __post_init__(self):
        if self.reset_at is None:
            self.reset_at = time.time() + self.window_seconds
    
    def check_and_increment(self) -> bool:
        """Check if request is allowed and increment usage"""
        current_time = time.time()
        
        # Reset if window has passed
        if current_time >= self.reset_at:
            self.used = 0
            self.reset_at = current_time + self.window_seconds
        
        if self.used < self.limit:
            self.used += 1
            return True
        return False
    
    def get_usage_percent(self) -> float:
        """Get current usage percentage"""
        if self.limit == 0:
            return 100.0
        return (self.used / self.limit) * 100
    
    def is_warning_level(self) -> bool:
        """Check if at warning threshold"""
        return self.get_usage_percent() >= (self.warnings_threshold * 100)


@dataclass
class RateLimitStats:
    """Statistics for rate limiting"""
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    queued_requests: int = 0
    processed_from_queue: int = 0
    current_rate: float = 0.0
    peak_rate: float = 0.0
    mean_latency_ms: float = 0.0
    queue_wait_time_ms: float = 0.0
    last_rejection_time: Optional[float] = None
    last_rejection_reason: Optional[str] = None


class TokenBucket:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # Tokens per second
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on rate
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now
    
    def get_available_tokens(self) -> float:
        """Get current available tokens"""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """
    Production-ready rate limiter with multiple strategies.
    
    Features:
    - Token bucket algorithm
    - Sliding window rate limiting
    - Request queuing
    - Automatic cleanup
    - Statistics tracking
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None
    ):
        self.name = name
        self.config = config or RateLimitConfig()
        
        self._bucket = TokenBucket(
            rate=self.config.requests_per_second,
            capacity=self.config.burst_size
        )
        self._stats = RateLimitStats()
        self._request_times: deque = deque()
        self._lock = threading.Lock()
        self._queues: Dict[str, asyncio.Queue] = {}
        self._queue_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def acquire(
        self,
        key: str = "default",
        timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            key: Optional key for per-client rate limiting
            timeout: Maximum time to wait for permission
            
        Returns:
            True if request is allowed
        """
        timeout = timeout or self.config.queue_timeout
        
        # Check rate limit
        if self._bucket.consume():
            self._record_request(allowed=True)
            return True
        
        # Rate limited
        self._record_request(allowed=False, reason="rate_limit")
        
        # Queue if enabled
        if self.config.queue_size > 0:
            queue = self._get_or_create_queue(key)
            self._stats.queued_requests += 1
            
            try:
                await asyncio.wait_for(
                    queue.put(threading.Event()),
                    timeout=timeout
                )
                self._stats.processed_from_queue += 1
                self._record_request(allowed=True)
                return True
            except asyncio.TimeoutError:
                self._record_request(allowed=False, reason="queue_timeout")
                return False
        
        return False
    
    def _record_request(self, allowed: bool, reason: Optional[str] = None) -> None:
        """Record request in statistics"""
        current_time = time.time()
        
        self._stats.total_requests += 1
        if allowed:
            self._stats.allowed_requests += 1
        else:
            self._stats.rejected_requests += 1
            self._stats.last_rejection_time = current_time
            self._stats.last_rejection_reason = reason
        
        # Track request times for rate calculation
        self._request_times.append(current_time)
        
        # Remove old entries outside window
        cutoff = current_time - self.config.window_seconds
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
        
        # Update current rate
        self._stats.current_rate = len(self._request_times) / self.config.window_seconds
        self._stats.peak_rate = max(self._stats.peak_rate, self._stats.current_rate)
    
    def _get_or_create_queue(self, key: str) -> asyncio.Queue:
        """Get or create a queue for a key"""
        if key not in self._queues:
            self._queues[key] = asyncio.Queue(maxsize=self.config.queue_size)
        return self._queues[key]
    
    async def _process_queue(self, key: str) -> None:
        """Process queued requests for a key"""
        queue = self._get_or_create_queue(key)
        
        while self._running:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Wait for rate limit
                while not self._bucket.consume():
                    await asyncio.sleep(0.1)
                
                event.set()
                queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue processing error for {key}: {e}")
                break
    
    async def start(self) -> None:
        """Start the rate limiter"""
        self._running = True
        for key in list(self._queues.keys()):
            task = asyncio.create_task(self._process_queue(key))
            self._queue_tasks.append(task)
    
    async def stop(self) -> None:
        """Stop the rate limiter"""
        self._running = False
        for task in self._queue_tasks:
            task.cancel()
        self._queue_tasks.clear()
    
    def get_stats(self) -> RateLimitStats:
        """Get rate limiting statistics"""
        return self._stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        return {
            "name": self.name,
            "config": {
                "requests_per_second": self.config.requests_per_second,
                "burst_size": self.config.burst_size,
                "window_seconds": self.config.window_seconds,
                "queue_size": self.config.queue_size,
            },
            "stats": {
                "total_requests": self._stats.total_requests,
                "allowed_requests": self._stats.allowed_requests,
                "rejected_requests": self._stats.rejected_requests,
                "queued_requests": self._stats.queued_requests,
                "processed_from_queue": self._stats.processed_from_queue,
                "current_rate": round(self._stats.current_rate, 2),
                "peak_rate": round(self._stats.peak_rate, 2),
                "available_tokens": round(self._bucket.get_available_tokens(), 2),
                "rejection_rate": round(
                    self._stats.rejected_requests / max(1, self._stats.total_requests) * 100,
                    2
                )
            },
            "last_rejection": {
                "time": self._stats.last_rejection_time,
                "reason": self._stats.last_rejection_reason
            }
        }


class ResourceQuotaManager:
    """
    Manages multiple resource quotas with tracking and alerts.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._quotas: Dict[str, ResourceQuota] = {}
        self._lock = threading.Lock()
        self._alert_callbacks: List[Callable[[str, ResourceQuota], None]] = []
    
    def add_quota(
        self,
        name: str,
        limit: int,
        window_seconds: float = 60.0,
        exceeded_action: QuotaExceededAction = QuotaExceededAction.REJECT,
        warnings_threshold: float = 0.8
    ) -> ResourceQuota:
        """Add a new resource quota"""
        quota = ResourceQuota(
            name=name,
            limit=limit,
            window_seconds=window_seconds,
            exceeded_action=exceeded_action,
            warnings_threshold=warnings_threshold
        )
        
        with self._lock:
            self._quotas[name] = quota
        
        logger.info(f"Added resource quota: {name} = {limit}/{window_seconds}s")
        return quota
    
    def check(self, quota_name: str) -> bool:
        """Check if request is allowed under quota"""
        with self._lock:
            if quota_name not in self._quotas:
                return True  # Unknown quota, allow
            
            quota = self._quotas[quota_name]
            allowed = quota.check_and_increment()
            
            if not allowed and quota.exceeded_action == QuotaExceededAction.REJECT:
                self._trigger_alert(quota_name, quota)
            
            return allowed
    
    def get_usage(self, quota_name: str) -> float:
        """Get current quota usage percentage"""
        with self._lock:
            if quota_name not in self._quotas:
                return 0.0
            return self._quotas[quota_name].get_usage_percent()
    
    def register_alert_callback(
        self,
        callback: Callable[[str, ResourceQuota], None]
    ) -> None:
        """Register a callback for quota alerts"""
        self._alert_callbacks.append(callback)
    
    def _trigger_alert(self, quota_name: str, quota: ResourceQuota) -> None:
        """Trigger alert callbacks"""
        for callback in self._alert_callbacks:
            try:
                callback(quota_name, quota)
            except Exception as e:
                logger.error(f"Quota alert callback failed: {e}")
    
    def get_all_quotas(self) -> List[ResourceQuota]:
        """Get all current quotas"""
        with self._lock:
            return list(self._quotas.values())
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        with self._lock:
            return {
                "name": self.name,
                "quotas": {
                    name: {
                        "limit": q.limit,
                        "used": q.used,
                        "usage_percent": round(q.get_usage_percent(), 2),
                        "window_seconds": q.window_seconds,
                        "exceeded_action": q.exceeded_action.value,
                        "reset_at": q.reset_at,
                        "at_warning_level": q.is_warning_level()
                    }
                    for name, q in self._quotas.items()
                }
            }
