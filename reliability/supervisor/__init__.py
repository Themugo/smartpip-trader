"""
Service Registry
================

Central registry for all services with health tracking.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status levels"""
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceMetadata:
    """Metadata for a registered service"""
    name: str
    version: str
    status: ServiceStatus
    endpoint: Optional[str] = None
    port: Optional[int] = None
    health_check_url: Optional[str] = None
    
    # Timestamps
    registered_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    stopped_at: Optional[float] = None
    last_health_check: Optional[float] = None
    
    # Metrics
    requests_served: int = 0
    errors: int = 0
    mean_latency_ms: float = 0.0
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "port": self.port,
            "health_check_url": self.health_check_url,
            "registered_at": self.registered_at,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "last_health_check": self.last_health_check,
            "requests_served": self.requests_served,
            "errors": self.errors,
            "mean_latency_ms": self.mean_latency_ms,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "metadata": self.metadata,
            "uptime_seconds": (
                (self.stopped_at or time.time()) - (self.started_at or self.registered_at)
                if self.started_at else 0
            )
        }


@dataclass
class RegistryStats:
    """Statistics for the registry"""
    total_services: int = 0
    running_services: int = 0
    degraded_services: int = 0
    failed_services: int = 0
    total_requests: int = 0
    total_errors: int = 0


class ServiceRegistry:
    """
    Central registry for all platform services.
    
    Features:
    - Service registration/deregistration
    - Health status tracking
    - Dependency management
    - Automatic cleanup of stale services
    - Service discovery
    """
    
    _instance: Optional['ServiceRegistry'] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._services: Dict[str, ServiceMetadata] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._on_register: List[Callable[[ServiceMetadata], None]] = []
        self._on_unregister: List[Callable[[str], None]] = []
        self._on_status_change: List[Callable[[str, ServiceStatus, ServiceStatus], None]] = []
        
        logger.info("Service Registry initialized")
    
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """Get singleton instance"""
        return cls()
    
    def register_callback(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """Register a callback for registry events"""
        if event == "register":
            self._on_register.append(callback)
        elif event == "unregister":
            self._on_unregister.append(callback)
        elif event == "status_change":
            self._on_status_change.append(callback)
    
    async def register(
        self,
        name: str,
        version: str = "1.0.0",
        endpoint: Optional[str] = None,
        port: Optional[int] = None,
        health_check_url: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceMetadata:
        """
        Register a new service.
        
        Args:
            name: Service name
            version: Service version
            endpoint: Service endpoint URL
            port: Service port
            health_check_url: URL for health checks
            dependencies: List of service names this depends on
            metadata: Additional metadata
            
        Returns:
            ServiceMetadata for the registered service
        """
        async with self._lock:
            if name in self._services:
                logger.warning(f"Service {name} already registered, updating...")
            
            service = ServiceMetadata(
                name=name,
                version=version,
                status=ServiceStatus.STARTING,
                endpoint=endpoint,
                port=port,
                health_check_url=health_check_url,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            self._services[name] = service
            
            # Update dependents of dependencies
            for dep_name in service.dependencies:
                if dep_name in self._services:
                    if name not in self._services[dep_name].dependents:
                        self._services[dep_name].dependents.append(name)
            
            logger.info(f"Registered service: {name} v{version}")
            
            # Execute callbacks
            for callback in self._on_register:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(service)
                    else:
                        callback(service)
                except Exception as e:
                    logger.error(f"Register callback failed: {e}")
            
            return service
    
    async def unregister(self, name: str) -> bool:
        """
        Unregister a service.
        
        Args:
            name: Service name
            
        Returns:
            True if service was unregistered
        """
        async with self._lock:
            if name not in self._services:
                return False
            
            service = self._services[name]
            
            # Remove from dependents of dependencies
            for dep_name in service.dependencies:
                if dep_name in self._services:
                    if name in self._services[dep_name].dependents:
                        self._services[dep_name].dependents.remove(name)
            
            # Update status
            service.status = ServiceStatus.STOPPED
            service.stopped_at = time.time()
            
            del self._services[name]
            
            logger.info(f"Unregistered service: {name}")
            
            # Execute callbacks
            for callback in self._on_unregister:
                try:
                    callback(name)
                except Exception as e:
                    logger.error(f"Unregister callback failed: {e}")
            
            return True
    
    async def update_status(
        self,
        name: str,
        status: ServiceStatus,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update service status.
        
        Args:
            name: Service name
            status: New status
            metrics: Optional metrics update
            
        Returns:
            True if status was updated
        """
        async with self._lock:
            if name not in self._services:
                return False
            
            service = self._services[name]
            old_status = service.status
            
            service.status = status
            
            if status == ServiceStatus.RUNNING and not service.started_at:
                service.started_at = time.time()
            elif status in [ServiceStatus.STOPPED, ServiceStatus.FAILED]:
                service.stopped_at = time.time()
            
            # Update metrics
            if metrics:
                if "requests_served" in metrics:
                    service.requests_served = metrics["requests_served"]
                if "errors" in metrics:
                    service.errors = metrics["errors"]
                if "mean_latency_ms" in metrics:
                    service.mean_latency_ms = metrics["mean_latency_ms"]
            
            # Execute callbacks
            if old_status != status:
                for callback in self._on_status_change:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(name, old_status, status)
                        else:
                            callback(name, old_status, status)
                    except Exception as e:
                        logger.error(f"Status change callback failed: {e}")
                
                logger.info(f"Service {name} status: {old_status.value} -> {status.value}")
            
            return True
    
    async def record_request(
        self,
        name: str,
        latency_ms: float,
        success: bool = True
    ) -> None:
        """
        Record a request for metrics.
        
        Args:
            name: Service name
            latency_ms: Request latency
            success: Whether request was successful
        """
        async with self._lock:
            if name not in self._services:
                return
            
            service = self._services[name]
            service.requests_served += 1
            
            if not success:
                service.errors += 1
            
            # Update mean latency (exponential moving average)
            alpha = 0.1
            service.mean_latency_ms = (
                alpha * latency_ms + (1 - alpha) * service.mean_latency_ms
            )
    
    def get_service(self, name: str) -> Optional[ServiceMetadata]:
        """Get service metadata by name"""
        return self._services.get(name)
    
    def get_all_services(self) -> Dict[str, ServiceMetadata]:
        """Get all registered services"""
        return {
            name: meta.to_dict() if hasattr(meta, 'to_dict') else meta
            for name, meta in self._services.items()
        }
    
    def get_by_status(self, status: ServiceStatus) -> List[ServiceMetadata]:
        """Get services by status"""
        return [
            s for s in self._services.values()
            if s.status == status
        ]
    
    def get_dependents(self, name: str) -> List[str]:
        """Get services that depend on this service"""
        service = self._services.get(name)
        if not service:
            return []
        return service.dependents.copy()
    
    def get_dependencies(self, name: str) -> List[str]:
        """Get services that this service depends on"""
        service = self._services.get(name)
        if not service:
            return []
        return service.dependencies.copy()
    
    def get_stats(self) -> RegistryStats:
        """Get registry statistics"""
        stats = RegistryStats(
            total_services=len(self._services),
            running_services=sum(
                1 for s in self._services.values()
                if s.status == ServiceStatus.RUNNING
            ),
            degraded_services=sum(
                1 for s in self._services.values()
                if s.status == ServiceStatus.DEGRADED
            ),
            failed_services=sum(
                1 for s in self._services.values()
                if s.status == ServiceStatus.FAILED
            ),
            total_requests=sum(
                s.requests_served for s in self._services.values()
            ),
            total_errors=sum(
                s.errors for s in self._services.values()
            ),
        )
        return stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        stats = self.get_stats()
        
        return {
            "stats": {
                "total_services": stats.total_services,
                "running_services": stats.running_services,
                "degraded_services": stats.degraded_services,
                "failed_services": stats.failed_services,
                "total_requests": stats.total_requests,
                "total_errors": stats.total_errors,
                "error_rate": round(
                    stats.total_errors / max(1, stats.total_requests) * 100,
                    2
                )
            },
            "services": {
                name: meta.to_dict() if hasattr(meta, 'to_dict') else meta
                for name, meta in self._services.items()
            },
            "by_status": {
                status.value: [
                    s.name for s in self._services.values()
                    if s.status == status
                ]
                for status in ServiceStatus
            }
        }


# Re-export other supervisor modules
from .dependency_map import DependencyMap, Dependency
from .worker_supervisor import WorkerSupervisor, WorkerProcess
from .message_replay import MessageReplayQueue, EventReplayLog
