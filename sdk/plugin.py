"""
Plugin SDK
==========

SDK for building SmartPip Trader plugins.
"""

import os
import sys
import json
import time
import logging
import importlib
import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Type
from enum import Enum

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = logging.getLogger(__name__)


class PluginHook(Enum):
    """Plugin hook types"""
    ON_INIT = "on_init"
    ON_START = "on_start"
    ON_STOP = "on_stop"
    ON_TICK = "on_tick"
    ON_SIGNAL = "on_signal"
    ON_ORDER = "on_order"
    ON_FILL = "on_fill"
    ON_ERROR = "on_error"
    ON_CONFIG_UPDATE = "on_config_update"
    ON_HEALTH_CHECK = "on_health_check"


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    plugin_id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    hooks: List[PluginHook] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "hooks": [h.value for h in self.hooks],
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PluginMetadata":
        data = data.copy()
        if "hooks" in data:
            data["hooks"] = [PluginHook(h) for h in data["hooks"]]
        return cls(**data)


class Plugin:
    """
    Base Plugin class.
    
    All plugins must inherit from this class.
    """
    
    metadata: PluginMetadata = None  # Override in subclass
    
    def __init__(self):
        self._enabled = False
        self._config: Dict[str, Any] = {}
        self._state: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"plugin.{self.metadata.name if self.metadata else 'unknown'}")
    
    def enable(self) -> None:
        """Enable the plugin"""
        self._enabled = True
        self._logger.info(f"Plugin {self.metadata.name} enabled")
    
    def disable(self) -> None:
        """Disable the plugin"""
        self._enabled = False
        self._logger.info(f"Plugin {self.metadata.name} disabled")
    
    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self._enabled
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin"""
        self._config.update(config)
        self._on_configure()
    
    def _on_configure(self) -> None:
        """Override to handle configuration"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set plugin state"""
        self._state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get plugin state"""
        return self._state.get(key, default)
    
    def clear_state(self) -> None:
        """Clear plugin state"""
        self._state.clear()
    
    # Hook handlers
    def on_init(self) -> None:
        """Called when plugin is initialized"""
        pass
    
    def on_start(self) -> None:
        """Called when plugin starts"""
        pass
    
    def on_stop(self) -> None:
        """Called when plugin stops"""
        pass
    
    def on_tick(self, tick: Dict[str, Any]) -> None:
        """Called on each market tick"""
        pass
    
    def on_signal(self, signal: Dict[str, Any]) -> None:
        """Called when a signal is generated"""
        pass
    
    def on_order(self, order: Dict[str, Any]) -> None:
        """Called when an order is placed"""
        pass
    
    def on_fill(self, fill: Dict[str, Any]) -> None:
        """Called when an order is filled"""
        pass
    
    def on_error(self, error: Exception) -> None:
        """Called on error"""
        pass
    
    def on_config_update(self, config: Dict[str, Any]) -> None:
        """Called when configuration is updated"""
        pass
    
    def on_health_check(self) -> Dict[str, Any]:
        """Return health status"""
        return {"status": "healthy", "plugin": self.metadata.name}


class PluginManager(SmartPipSDK):
    """
    Plugin manager for loading and managing plugins.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None, plugin_dir: Optional[str] = None):
        super().__init__(config)
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_dir = plugin_dir or "./plugins"
        self._hooks: Dict[PluginHook, List[Callable]] = {h: [] for h in PluginHook}
    
    def _on_initialize(self) -> None:
        """Initialize plugin manager"""
        self._load_builtin_plugins()
    
    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins"""
        pass  # Override to load specific plugins
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin"""
        if not plugin.metadata:
            raise SDKError("Plugin must have metadata")
        
        plugin_id = plugin.metadata.plugin_id
        
        if plugin_id in self._plugins:
            raise SDKError(f"Plugin {plugin_id} already registered")
        
        self._plugins[plugin_id] = plugin
        self._register_hooks(plugin)
        self._logger.info(f"Registered plugin: {plugin.metadata.name}")
    
    def _register_hooks(self, plugin: Plugin) -> None:
        """Register plugin hooks"""
        for hook_type in plugin.metadata.hooks:
            method_name = hook_type.value.replace("_", "_")
            if hasattr(plugin, method_name):
                self._hooks[hook_type].append(getattr(plugin, method_name))
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """Unregister a plugin"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins.pop(plugin_id)
        
        # Remove hooks
        for hook_list in self._hooks.values():
            to_remove = [h for h in hook_list if hasattr(h, '__self__') and h.__self__ == plugin]
            for h in to_remove:
                hook_list.remove(h)
        
        self._logger.info(f"Unregistered plugin: {plugin_id}")
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID"""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins"""
        return [p.metadata for p in self._plugins.values()]
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        plugin.enable()
        plugin.on_init()
        return True
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        plugin.disable()
        return True
    
    def load_plugin_from_file(self, filepath: str) -> Plugin:
        """Load a plugin from file"""
        spec = importlib.util.spec_from_file_location("plugin_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find Plugin class
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                plugin = obj()
                self.register_plugin(plugin)
                return plugin
        
        raise SDKError("No Plugin class found in module")
    
    def load_plugins_from_directory(self, directory: str) -> List[Plugin]:
        """Load all plugins from a directory"""
        plugins = []
        
        if not os.path.exists(directory):
            return plugins
        
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("_"):
                filepath = os.path.join(directory, filename)
                try:
                    plugin = self.load_plugin_from_file(filepath)
                    plugins.append(plugin)
                except Exception as e:
                    self._logger.error(f"Failed to load plugin {filename}: {e}")
        
        return plugins
    
    def trigger_hook(self, hook_type: PluginHook, *args, **kwargs) -> List[Any]:
        """Trigger all handlers for a hook"""
        results = []
        for handler in self._hooks.get(hook_type, []):
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Hook error for {hook_type}: {e}")
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all plugins"""
        results = {"status": "healthy", "plugins": []}
        
        for plugin in self._plugins.values():
            if plugin.is_enabled:
                try:
                    health = plugin.on_health_check()
                    results["plugins"].append(health)
                except Exception as e:
                    results["plugins"].append({
                        "status": "unhealthy",
                        "plugin": plugin.metadata.name,
                        "error": str(e)
                    })
                    results["status"] = "degraded"
        
        return results


def create_plugin(
    name: str,
    version: str,
    hooks: List[PluginHook] = None,
    **metadata
) -> Type[Plugin]:
    """Decorator to create a plugin class"""
    
    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        plugin_id = name.lower().replace(" ", "_")
        metadata_obj = PluginMetadata(
            plugin_id=plugin_id,
            name=name,
            version=version,
            hooks=hooks or [],
            **metadata
        )
        cls.metadata = metadata_obj
        return cls
    
    return decorator
