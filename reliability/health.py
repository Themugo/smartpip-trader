"""
Health Monitoring
================

Comprehensive health monitoring for all system components.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """A health check definition"""
    name: str
    component: str
    check_fn: Callable[[], bool]
    
    # Configuration
    timeout_seconds: float = 5.0
    critical: bool = True
    
    # State
    last_check_time: float = 0
    last_status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    
    def execute(self) -> bool:
        """Execute the health check"""
        try:
            start = time.time()
            result = self.check_fn()
            elapsed = time.time() - start
            
            self.last_check_time = time.time()
            self.consecutive_failures = 0
            
            if elapsed > self.timeout_seconds:
                self.last_status = HealthStatus.DEGRADED
                return False
            
            self.last_status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            return result
            
        except Exception as e:
            self.last_check_time = time.time()
            self.consecutive_failures += 1
            self.last_status = HealthStatus.UNHEALTHY
            logger.warning(f"Health check '{self.name}' failed: {e}")
            return False


@dataclass
class HealthMonitor:
    """
    Centralized health monitoring.
    
    Monitors all system components and provides
    unified health status.
    """
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._dependencies: Dict[str, List[str]] = {}  # component -> depends_on
        self._callbacks: List[Callable] = []
        self._lock = threading.RLock()
        self._last_overall_status = HealthStatus.UNKNOWN
    
    def register_check(
        self,
        name: str,
        component: str,
        check_fn: Callable[[], bool],
        critical: bool = True
    ) -> None:
        """Register a health check"""
        with self._lock:
            self._checks[name] = HealthCheck(
                name=name,
                component=component,
                check_fn=check_fn,
                critical=critical,
            )
    
    def add_dependency(self, component: str, depends_on: str) -> None:
        """Add a dependency relationship"""
        with self._lock:
            if component not in self._dependencies:
                self._dependencies[component] = []
            self._dependencies[component].append(depends_on)
    
    def check(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute health checks.
        
        Returns comprehensive health status.
        """
        with self._lock:
            checks = self._checks
            
            if component:
                checks = {
                    k: v for k, v in checks.items()
                    if v.component == component
                }
            
            results = {}
            overall_status = HealthStatus.HEALTHY
            
            for name, check in checks.items():
                check.execute()
                
                results[name] = {
                    "component": check.component,
                    "status": check.last_status.value,
                    "last_check": check.last_check_time,
                    "critical": check.critical,
                    "consecutive_failures": check.consecutive_failures,
                }
                
                # Update overall status
                if check.critical:
                    if check.last_status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                    elif (check.last_status == HealthStatus.DEGRADED and
                          overall_status != HealthStatus.UNHEALTHY):
                        overall_status = HealthStatus.DEGRADED
            
            # Check dependencies
            dependency_errors = self._check_dependencies()
            
            if dependency_errors:
                results["dependencies"] = dependency_errors
                overall_status = HealthStatus.UNHEALTHY
            
            # Notify if status changed
            if overall_status != self._last_overall_status:
                self._notify_status_change(overall_status)
                self._last_overall_status = overall_status
            
            return {
                "status": overall_status.value,
                "components": results,
                "timestamp": time.time(),
            }
    
    def _check_dependencies(self) -> List[str]:
        """Check if dependencies are healthy"""
        errors = []
        
        for component, deps in self._dependencies.items():
            component_checks = [
                c for c in self._checks.values()
                if c.component == component
            ]
            
            if not component_checks:
                continue
            
            for dep in deps:
                dep_checks = [
                    c for c in self._checks.values()
                    if c.component == dep
                ]
                
                for check in dep_checks:
                    if check.last_status == HealthStatus.UNHEALTHY:
                        errors.append(
                            f"{component} depends on unhealthy {dep}"
                        )
        
        return errors
    
    def get_component_status(self, component: str) -> HealthStatus:
        """Get status of a specific component"""
        with self._lock:
            component_checks = [
                c for c in self._checks.values()
                if c.component == component
            ]
            
            if not component_checks:
                return HealthStatus.UNKNOWN
            
            # Return worst status
            statuses = [c.last_status for c in component_checks]
            
            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            elif HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            elif HealthStatus.HEALTHY in statuses:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
    
    def on_status_change(self, callback: Callable) -> None:
        """Register status change callback"""
        self._callbacks.append(callback)
    
    def _notify_status_change(self, new_status: HealthStatus) -> None:
        """Notify listeners of status change"""
        for callback in self._callbacks:
            try:
                callback(new_status)
            except Exception as e:
                logger.error(f"Health status callback error: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        with self._lock:
            components = set(c.component for c in self._checks.values())
            
            component_status = {}
            for component in components:
                status = self.get_component_status(component)
                component_status[component] = status.value
            
            return {
                "total_components": len(components),
                "healthy": sum(1 for s in component_status.values() if s == "healthy"),
                "degraded": sum(1 for s in component_status.values() if s == "degraded"),
                "unhealthy": sum(1 for s in component_status.values() if s == "unhealthy"),
                "by_component": component_status,
            }
