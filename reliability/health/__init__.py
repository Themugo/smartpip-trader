"""
Health Monitoring System
=======================

Comprehensive health checks for all platform services.
"""

import asyncio
import time
import logging
import psutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Health information for a service"""
    name: str
    status: HealthStatus
    timestamp: float
    latency_ms: float = 0.0
    availability: float = 100.0  # Percentage
    error_rate: float = 0.0     # Percentage
    recovery_time_ms: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, HealthStatus] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    total_requests: int = 0
    total_errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    checks_passed: int = 0
    checks_failed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "availability": self.availability,
            "error_rate": self.error_rate,
            "recovery_time_ms": self.recovery_time_ms,
            "resource_usage": self.resource_usage,
            "details": self.details,
            "dependencies": {k: v.value for k, v in self.dependencies.items()},
            "uptime_seconds": self.uptime_seconds,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
        }


@dataclass
class HealthCheck:
    """A health check configuration"""
    name: str
    check_fn: Callable[[], Any]
    interval: float = 30.0        # Check interval in seconds
    timeout: float = 5.0          # Check timeout
    critical: bool = True         # If check failure makes service unhealthy
    tags: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    check_name: str
    passed: bool
    timestamp: float
    latency_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ServiceHealthMonitor:
    """
    Monitors health of all platform services.
    
    Features:
    - Custom health checks
    - Automatic resource monitoring
    - Dependency health tracking
    - Degraded mode support
    - Alert callbacks
    - Historical tracking
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._health_checks: Dict[str, HealthCheck] = {}
        self._services: Dict[str, ServiceHealth] = {}
        self._health_history: Dict[str, deque] = {}  # Rolling history
        self._check_results: Dict[str, HealthCheckResult] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._start_time = time.time()
        self._alert_callbacks: List[Callable[[str, HealthStatus, ServiceHealth], None]] = []
        self._lock = asyncio.Lock()
        
        # Resource thresholds for degradation
        self._cpu_warning = 70.0
        self._cpu_critical = 90.0
        self._memory_warning = 70.0
        self._memory_critical = 90.0
        self._disk_warning = 80.0
        self._disk_critical = 95.0
    
    def add_health_check(self, check: HealthCheck) -> None:
        """Add a health check"""
        self._health_checks[check.name] = check
        logger.debug(f"Added health check: {check.name}")
    
    def register_alert_callback(
        self,
        callback: Callable[[str, HealthStatus, ServiceHealth], None]
    ) -> None:
        """Register a callback for health alerts"""
        self._alert_callbacks.append(callback)
    
    async def _execute_check(self, check: HealthCheck) -> HealthCheckResult:
        """Execute a single health check"""
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(check.check_fn):
                result = await asyncio.wait_for(
                    check.check_fn(),
                    timeout=check.timeout
                )
            else:
                result = check.check_fn()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if result indicates health
            if isinstance(result, bool):
                passed = result
                message = "OK" if passed else "Check failed"
            elif isinstance(result, dict):
                passed = result.get("passed", True)
                message = result.get("message", "OK")
                result = result  # Already a dict
            else:
                passed = True
                message = "OK"
            
            return HealthCheckResult(
                check_name=check.name,
                passed=passed,
                timestamp=time.time(),
                latency_ms=latency_ms,
                message=message,
                details=result if isinstance(result, dict) else {}
            )
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                check_name=check.name,
                passed=False,
                timestamp=time.time(),
                latency_ms=check.timeout * 1000,
                error=f"Check timed out after {check.timeout}s"
            )
        except Exception as e:
            return HealthCheckResult(
                check_name=check.name,
                passed=False,
                timestamp=time.time(),
                latency_ms=(time.time() - start_time) * 1000,
                error=f"{type(e).__name__}: {e}"
            )
    
    async def _monitor_loop(self, check: HealthCheck) -> None:
        """Continuous monitoring loop for a check"""
        while self._running:
            result = await self._execute_check(check)
            self._check_results[check.name] = result
            
            # Update service health
            await self._update_service_health(check.name, result)
            
            await asyncio.sleep(check.interval)
    
    async def _update_service_health(
        self,
        check_name: str,
        result: HealthCheckResult
    ) -> None:
        """Update service health based on check result"""
        async with self._lock:
            check = self._health_checks[check_name]
            
            # Get or create service health
            if check.tags:
                service_name = check.tags[0]  # First tag is service name
            else:
                service_name = self.service_name
            
            if service_name not in self._services:
                self._services[service_name] = ServiceHealth(
                    name=service_name,
                    status=HealthStatus.UNKNOWN,
                    timestamp=time.time(),
                    uptime_seconds=time.time() - self._start_time
                )
            
            health = self._services[service_name]
            health.timestamp = time.time()
            health.latency_ms = max(health.latency_ms, result.latency_ms)
            
            if result.passed:
                health.checks_passed += 1
            else:
                health.checks_failed += 1
                health.last_error = result.error
                health.last_error_time = result.timestamp
                
                if check.critical:
                    health.status = HealthStatus.UNHEALTHY
            
            # Add to history
            if service_name not in self._health_history:
                self._health_history[service_name] = deque(maxlen=100)
            self._health_history[service_name].append(result)
    
    async def _collect_resource_metrics(self) -> Dict[str, float]:
        """Collect current resource usage"""
        metrics = {}
        
        try:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["disk_percent"] = psutil.disk_usage('/').percent
            
            # Process-specific
            process = psutil.Process()
            metrics["process_cpu_percent"] = process.cpu_percent()
            metrics["process_memory_mb"] = process.memory_info().rss / 1024 / 1024
            metrics["process_threads"] = process.num_threads()
            metrics["process_open_files"] = len(process.open_files())
            
        except Exception as e:
            logger.warning(f"Failed to collect resource metrics: {e}")
        
        return metrics
    
    def _calculate_overall_status(
        self,
        service_name: str,
        resource_usage: Dict[str, float]
    ) -> HealthStatus:
        """Calculate overall service status"""
        if service_name not in self._services:
            return HealthStatus.UNKNOWN
        
        health = self._services[service_name]
        
        # Check critical health checks
        if health.checks_failed > 0:
            critical_checks = [
                c for c in self._health_checks.values()
                if c.critical and c.tags and c.tags[0] == service_name
            ]
            
            if critical_checks:
                failed_critical = sum(
                    1 for result in self._check_results.values()
                    if not result.passed and
                    self._health_checks[result.check_name].critical
                )
                if failed_critical > 0:
                    return HealthStatus.UNHEALTHY
        
        # Check resource usage
        if resource_usage.get("cpu_percent", 0) >= self._cpu_critical:
            return HealthStatus.UNHEALTHY
        if resource_usage.get("memory_percent", 0) >= self._memory_critical:
            return HealthStatus.UNHEALTHY
        if resource_usage.get("disk_percent", 0) >= self._disk_critical:
            return HealthStatus.UNHEALTHY
        
        # Check warning thresholds
        if resource_usage.get("cpu_percent", 0) >= self._cpu_warning:
            return HealthStatus.DEGRADED
        if resource_usage.get("memory_percent", 0) >= self._memory_warning:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    async def record_request(self, service_name: str, success: bool, latency_ms: float) -> None:
        """Record a request for statistics"""
        async with self._lock:
            if service_name not in self._services:
                self._services[service_name] = ServiceHealth(
                    name=service_name,
                    status=HealthStatus.HEALTHY,
                    timestamp=time.time(),
                    uptime_seconds=time.time() - self._start_time
                )
            
            health = self._services[service_name]
            health.total_requests += 1
            
            if not success:
                health.total_errors += 1
            
            # Update error rate
            health.error_rate = (
                health.total_errors / max(1, health.total_requests) * 100
            )
            
            # Update availability
            health.availability = 100.0 - health.error_rate
            
            # Update latency (exponential moving average)
            alpha = 0.1
            health.latency_ms = alpha * latency_ms + (1 - alpha) * health.latency_ms
    
    def get_health(self, service_name: Optional[str] = None) -> ServiceHealth:
        """Get health for a specific service or overall"""
        if service_name:
            return self._services.get(service_name)
        
        # Calculate aggregate health
        if not self._services:
            return ServiceHealth(
                name=self.service_name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                uptime_seconds=time.time() - self._start_time
            )
        
        # Get most critical status
        statuses = [s.status for s in self._services.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        
        # Aggregate stats
        total_requests = sum(s.total_requests for s in self._services.values())
        total_errors = sum(s.total_errors for s in self._services.values())
        mean_latency = sum(s.latency_ms for s in self._services.values()) / max(1, len(self._services))
        
        return ServiceHealth(
            name=self.service_name,
            status=overall,
            timestamp=time.time(),
            latency_ms=mean_latency,
            availability=100.0 - (total_errors / max(1, total_requests) * 100),
            error_rate=total_errors / max(1, total_requests) * 100,
            total_requests=total_requests,
            total_errors=total_errors,
            uptime_seconds=time.time() - self._start_time
        )
    
    def get_all_health(self) -> Dict[str, ServiceHealth]:
        """Get health for all services"""
        return self._services.copy()
    
    async def start(self) -> None:
        """Start health monitoring"""
        self._running = True
        
        # Start monitoring tasks for each check
        for check in self._health_checks.values():
            task = asyncio.create_task(self._monitor_loop(check))
            self._monitoring_tasks[check.name] = task
        
        logger.info(f"Health monitor started for {self.service_name}")
    
    async def stop(self) -> None:
        """Stop health monitoring"""
        self._running = False
        
        for task in self._monitoring_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_tasks.clear()
        logger.info(f"Health monitor stopped for {self.service_name}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        health = self.get_health()
        resource_usage = asyncio.run(self._collect_resource_metrics())
        
        return {
            "service": health.to_dict(),
            "services": {
                name: s.to_dict()
                for name, s in self._services.items()
            },
            "resource_usage": resource_usage,
            "thresholds": {
                "cpu_warning": self._cpu_warning,
                "cpu_critical": self._cpu_critical,
                "memory_warning": self._memory_warning,
                "memory_critical": self._memory_critical,
                "disk_warning": self._disk_warning,
                "disk_critical": self._disk_critical,
            },
            "check_results": {
                name: {
                    "passed": r.passed,
                    "timestamp": r.timestamp,
                    "latency_ms": r.latency_ms,
                    "message": r.message,
                    "error": r.error
                }
                for name, r in self._check_results.items()
            }
        }


# Re-export HeartbeatMonitor
from .heartbeat import HeartbeatMonitor, HeartbeatStatus
