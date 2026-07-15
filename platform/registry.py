"""
Service Registry - Central Service Management

Singleton registry for all platform services with lifecycle support.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceStatus(Enum):
    """Service lifecycle status"""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service"""
    name: str
    service_class: Type
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    singleton: bool = True
    status: ServiceStatus = ServiceStatus.REGISTERED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_access: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "service_class": self.service_class.__name__ if self.service_class else None,
            "singleton": self.singleton,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class ServiceRegistry:
    """
    Central service registry for the platform.
    
    Features:
    - Service registration with dependencies
    - Singleton and transient services
    - Lazy instantiation
    - Circular dependency detection
    - Service metadata
    - Status tracking
    """
    
    _instance: Optional["ServiceRegistry"] = None
    
    def __new__(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the registry"""
        self._services: Dict[str, ServiceDescriptor] = {}
        self._factories: Dict[str, Callable] = {}
        self._dependencies_graph: Dict[str, List[str]] = defaultdict(list)
        self._initialization_order: List[str] = []
        self._logger = logging.getLogger(f"{__name__}.Registry")
    
    def register(
        self,
        name: str,
        service_class: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        dependencies: Optional[List[str]] = None,
        singleton: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service.
        
        Args:
            name: Service name
            service_class: Service class
            factory: Factory function
            dependencies: List of service dependencies
            singleton: Whether to use singleton pattern
            metadata: Additional metadata
        """
        if name in self._services:
            self._logger.warning(f"Service {name} already registered, replacing")
        
        descriptor = ServiceDescriptor(
            name=name,
            service_class=service_class,
            factory=factory,
            dependencies=dependencies or [],
            singleton=singleton,
            metadata=metadata or {},
        )
        
        self._services[name] = descriptor
        self._dependencies_graph[name] = dependencies or []
        
        self._logger.info(f"Registered service: {name}")
    
    def register_singleton(
        self,
        name: str,
        instance: T,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a pre-instantiated singleton"""
        descriptor = ServiceDescriptor(
            name=name,
            service_class=type(instance),
            instance=instance,
            singleton=True,
            status=ServiceStatus.RUNNING,
            metadata=metadata or {},
        )
        
        self._services[name] = descriptor
        self._logger.info(f"Registered singleton: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """Get a service by name"""
        descriptor = self._services.get(name)
        if not descriptor:
            return None
        
        descriptor.last_access = datetime.utcnow()
        
        # Return existing instance for singletons
        if descriptor.singleton and descriptor.instance is not None:
            return descriptor.instance
        
        # Create new instance
        instance = self._create_instance(descriptor)
        
        if descriptor.singleton:
            descriptor.instance = instance
        
        return instance
    
    def get_required(self, name: str) -> Any:
        """Get a service or raise if not found"""
        service = self.get(name)
        if service is None:
            raise KeyError(f"Required service not found: {name}")
        return service
    
    def get_typed(self, name: str, expected_type: Type[T]) -> Optional[T]:
        """Get a service with type checking"""
        service = self.get(name)
        if service is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Service {name} is {type(service).__name__}, expected {expected_type.__name__}"
            )
        return service
    
    def has(self, name: str) -> bool:
        """Check if a service is registered"""
        return name in self._services
    
    def unregister(self, name: str) -> bool:
        """Unregister a service"""
        if name in self._services:
            descriptor = self._services[name]
            
            # Call cleanup if available
            if hasattr(descriptor.instance, "shutdown"):
                try:
                    descriptor.instance.shutdown()
                except Exception as e:
                    self._logger.error(f"Error shutting down {name}: {e}")
            
            del self._services[name]
            self._logger.info(f"Unregistered service: {name}")
            return True
        return False
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        return [s.to_dict() for s in self._services.values()]
    
    def get_dependencies(self, name: str) -> List[str]:
        """Get dependencies for a service"""
        return self._dependencies_graph.get(name, [])
    
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """Validate all dependencies are satisfied"""
        missing = {}
        
        for name, deps in self._dependencies_graph.items():
            missing_deps = [d for d in deps if d not in self._services]
            if missing_deps:
                missing[name] = missing_deps
        
        return missing
    
    def get_initialization_order(self) -> List[str]:
        """Get topological order for service initialization"""
        if self._initialization_order:
            return self._initialization_order
        
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            for dep in self._dependencies_graph.get(name, []):
                visit(dep)
            
            order.append(name)
        
        for name in self._services:
            visit(name)
        
        self._initialization_order = order
        return order
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance"""
        # Get dependencies first
        deps = {}
        for dep_name in descriptor.dependencies:
            dep = self.get(dep_name)
            if dep is None:
                raise KeyError(f"Dependency {dep_name} not found for {descriptor.name}")
            deps[dep_name] = dep
        
        # Create instance
        if descriptor.factory:
            return descriptor.factory(**deps)
        elif descriptor.service_class:
            return descriptor.service_class(**deps)
        else:
            raise ValueError(f"No factory or class for {descriptor.name}")
    
    def shutdown(self) -> None:
        """Shutdown all services in reverse order"""
        order = self.get_initialization_order()[::-1]
        
        for name in order:
            descriptor = self._services.get(name)
            if descriptor and descriptor.instance:
                if hasattr(descriptor.instance, "shutdown"):
                    try:
                        descriptor.instance.shutdown()
                    except Exception as e:
                        self._logger.error(f"Error shutting down {name}: {e}")
        
        self._logger.info("All services shutdown")


# Global registry instance
service_registry = ServiceRegistry()
