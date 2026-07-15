"""
Dependency Injection

Provides dependency injection container for the platform.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar('T')


class DependencyInjector:
    """
    Simple dependency injection container.
    
    Features:
    - Singleton registration
    - Factory registration
    - Instance registration
    - Auto-resolution of dependencies
    """
    
    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}
        self._aliases: Dict[str, Type] = {}
    
    def register_singleton(
        self,
        interface: Type[T],
        factory: Callable[..., T],
    ) -> "DependencyInjector":
        """Register a singleton factory"""
        self._factories[interface] = factory
        return self
    
    def register_instance(
        self,
        interface: Type[T],
        instance: T,
    ) -> "DependencyInjector":
        """Register an existing instance"""
        self._singletons[interface] = instance
        return self
    
    def register_alias(
        self,
        alias: str,
        interface: Type,
    ) -> "DependencyInjector":
        """Register an alias for an interface"""
        self._aliases[alias] = interface
        return self
    
    def get(self, interface: Type[T]) -> T:
        """Get an instance of the interface"""
        # Check if already instantiated singleton
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check if factory exists
        if interface in self._factories:
            instance = self._factories[interface]()
            self._singletons[interface] = instance
            return instance
        
        # Check aliases
        if interface in self._aliases:
            return self.get(self._aliases[interface])
        
        raise KeyError(f"No registration found for {interface}")
    
    def has(self, interface: Type) -> bool:
        """Check if interface is registered"""
        return (
            interface in self._singletons
            or interface in self._factories
            or interface in self._aliases
        )
    
    def clear(self):
        """Clear all registrations"""
        self._singletons.clear()
        self._factories.clear()
        self._aliases.clear()


# Global injector instance
_injector: Optional[DependencyInjector] = None


def get_injector() -> DependencyInjector:
    """Get the global injector instance"""
    global _injector
    if _injector is None:
        _injector = DependencyInjector()
    return _injector


def set_injector(injector: DependencyInjector):
    """Set the global injector instance"""
    global _injector
    _injector = injector
