"""
Core Platform Infrastructure - Enterprise Trading OS Foundation

Core systems:
- Service Registry & Dependency Injection
- Event Bus
- Task Scheduler
- Module Discovery
- Lifecycle Manager
- Configuration & Secrets Management
"""

from core_platform.registry import ServiceRegistry, service_registry
from core_platform.di import DependencyInjector, get_injector
from core_platform.event_bus import EventBus, event_bus
from core_platform.scheduler import TaskScheduler, get_scheduler
from core_platform.lifecycle import LifecycleManager, LifecyclePhase
from core_platform.discovery import ModuleDiscovery
from core_platform.config import ConfigManager
from core_platform.secrets import SecretsManager

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
