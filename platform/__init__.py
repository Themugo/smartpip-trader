"""
Platform Infrastructure - Enterprise Trading OS Foundation

Core systems:
- Service Registry & Dependency Injection
- Event Bus
- Task Scheduler
- Module Discovery
- Lifecycle Manager
- Configuration & Secrets Management
"""

from platform.registry import ServiceRegistry, service_registry
from platform.di import DependencyInjector, get_injector
from platform.event_bus import EventBus, event_bus
from platform.scheduler import TaskScheduler, get_scheduler
from platform.lifecycle import LifecycleManager, LifecyclePhase
from platform.discovery import ModuleDiscovery
from platform.config import ConfigManager
from platform.secrets import SecretsManager

__all__ = [
    "ServiceRegistry",
    "service_registry",
    "DependencyInjector",
    "get_injector",
    "EventBus",
    "event_bus",
    "TaskScheduler",
    "get_scheduler",
    "LifecycleManager",
    "LifecyclePhase",
    "ModuleDiscovery",
    "ConfigManager",
    "SecretsManager",
]
