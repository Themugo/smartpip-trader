"""
Plugin Manager

Manages the lifecycle of trading strategy plugins including:
- Dynamic loading and unloading
- State management
- Configuration management
- Dependency resolution
- Hot-reload capability
"""

import asyncio
import importlib
import importlib.util
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Optional watchdog for hot-reload
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

from plugins.base import (
    PluginState,
    PluginMetadata,
    StrategyPlugin,
    TickData,
    Signal,
    RiskValidation,
    PerformanceMetrics,
)

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Raised when a plugin fails to load"""
    pass


class PluginDependencyError(Exception):
    """Raised when plugin dependencies are not met"""
    pass


class PluginManager:
    """
    Manages the lifecycle of all trading strategy plugins.
    
    Features:
    - Dynamic plugin discovery and loading
    - Plugin state management (enable/disable/pause)
    - Hot-reload via file watching
    - Dependency resolution
    - Configuration persistence
    - Isolated execution per plugin
    """
    
    def __init__(self, plugins_dir: Optional[str] = None):
        self._plugins_dir = plugins_dir or "plugins/strategies"
        self._plugins: Dict[str, StrategyPlugin] = {}
        self._enabled_plugins: Dict[str, bool] = {}
        self._plugin_classes: Dict[str, Type[StrategyPlugin]] = {}
        self._plugin_config: Dict[str, Dict[str, Any]] = {}
        self._observer: Optional[Observer] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._load_lock = asyncio.Lock()
        
    @property
    def plugins_dir(self) -> str:
        return self._plugins_dir
    
    @plugins_dir.setter
    def plugins_dir(self, path: str) -> None:
        self._plugins_dir = path
        if self._observer:
            self._observer.stop()
            self._observer = None
    
    async def initialize(self, event_loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Initialize the plugin manager"""
        self._event_loop = event_loop
        await self.discover_plugins()
        await self.load_builtin_strategies()
        logger.info(f"Plugin manager initialized with {len(self._plugin_classes)} plugin types")
    
    async def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory"""
        discovered = []
        plugins_path = Path(self._plugins_dir)
        
        if not plugins_path.exists():
            plugins_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created plugins directory: {plugins_path}")
            return discovered
        
        for file_path in plugins_path.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name.startswith("base"):
                continue
            
            try:
                module_name = f"plugins.strategies.{file_path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    # Find plugin classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, StrategyPlugin) and 
                            attr != StrategyPlugin):
                            self._plugin_classes[attr_name.lower()] = attr
                            discovered.append(attr_name)
                            logger.info(f"Discovered plugin: {attr_name}")
            except Exception as e:
                logger.warning(f"Failed to load plugin from {file_path}: {e}")
        
        return discovered
    
    async def load_builtin_strategies(self) -> None:
        """Load built-in strategies from the strategies directory"""
        builtin_strategies = {
            "unified": "strategies.unified_strategy.UnifiedStrategy",
            "martingale": "strategies.martingale_strategy.MartingaleStrategy",
            "anti_martingale": "strategies.anti_martingale_strategy.AntiMartingaleStrategy",
            "grid": "strategies.grid_strategy.GridStrategy",
            "hft": "strategies.hft_strategy.HFTStrategy",
            "sniper": "strategies.sniper_strategy.SniperStrategy",
        }
        
        for name, module_path in builtin_strategies.items():
            try:
                module_name, class_name = module_path.rsplit(".", 1)
                spec = importlib.util.find_spec(module_name)
                if spec:
                    module = importlib.import_module(module_name)
                    plugin_class = getattr(module, class_name, None)
                    if plugin_class and issubclass(plugin_class, StrategyPlugin):
                        self._plugin_classes[name] = plugin_class
                        logger.info(f"Loaded built-in strategy: {name}")
            except Exception as e:
                logger.debug(f"Could not load {name}: {e}")
    
    async def load_plugin(
        self,
        plugin_id: str,
        plugin_class: Type[StrategyPlugin],
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ) -> StrategyPlugin:
        """
        Load and initialize a plugin instance.
        
        Args:
            plugin_id: Unique identifier for this plugin instance
            plugin_class: The plugin class to instantiate
            config: Plugin configuration
            enabled: Whether to enable the plugin immediately
            
        Returns:
            The initialized plugin instance
        """
        async with self._load_lock:
            if plugin_id in self._plugins:
                raise PluginLoadError(f"Plugin {plugin_id} already loaded")
            
            # Create plugin instance
            plugin = plugin_class()
            await plugin.initialize()
            
            # Apply configuration
            if config:
                plugin.configure(config)
            
            # Store plugin
            self._plugins[plugin_id] = plugin
            self._enabled_plugins[plugin_id] = enabled
            self._plugin_config[plugin_id] = config or {}
            
            plugin._set_state(PluginState.INITIALIZED)
            if enabled:
                plugin._set_state(PluginState.RUNNING)
            
            logger.info(f"Loaded plugin: {plugin_id} ({plugin.metadata.name})")
            return plugin
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin and clean up resources.
        
        Args:
            plugin_id: Plugin to unload
            
        Returns:
            True if successful
        """
        async with self._load_lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            plugin._set_state(PluginState.UNLOADING)
            
            try:
                await plugin.cleanup()
                del self._plugins[plugin_id]
                self._enabled_plugins.pop(plugin_id, None)
                self._plugin_config.pop(plugin_id, None)
                logger.info(f"Unloaded plugin: {plugin_id}")
                return True
            except Exception as e:
                logger.error(f"Error unloading plugin {plugin_id}: {e}")
                plugin._set_state(PluginState.ERROR)
                plugin._set_error(str(e))
                return False
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        if plugin.state in (PluginState.ERROR, PluginState.UNLOADED):
            return False
        
        self._enabled_plugins[plugin_id] = True
        if plugin.state == PluginState.PAUSED:
            plugin.resume()
        elif plugin.state == PluginState.INITIALIZED:
            plugin._set_state(PluginState.RUNNING)
        
        logger.info(f"Enabled plugin: {plugin_id}")
        return True
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        self._enabled_plugins[plugin_id] = False
        plugin.pause()
        
        logger.info(f"Disabled plugin: {plugin_id}")
        return True
    
    def is_enabled(self, plugin_id: str) -> bool:
        """Check if a plugin is enabled"""
        return self._enabled_plugins.get(plugin_id, False)
    
    def get_plugin(self, plugin_id: str) -> Optional[StrategyPlugin]:
        """Get a plugin by ID"""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> Dict[str, StrategyPlugin]:
        """Get all loaded plugins"""
        return self._plugins.copy()
    
    def get_enabled_plugins(self) -> List[StrategyPlugin]:
        """Get all enabled plugins"""
        return [
            plugin for plugin_id, plugin in self._plugins.items()
            if self._enabled_plugins.get(plugin_id, False)
        ]
    
    def get_plugin_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all available plugins"""
        result = []
        for plugin_id, plugin in self._plugins.items():
            result.append({
                "id": plugin_id,
                "metadata": plugin.metadata.to_dict(),
                "state": plugin.state.value,
                "enabled": self._enabled_plugins.get(plugin_id, False),
                "metrics": plugin.metrics.to_dict(),
            })
        return result
    
    def get_available_plugin_types(self) -> List[Dict[str, Any]]:
        """Get all available plugin types"""
        return [
            {
                "class_name": name,
                "metadata": cls().metadata.to_dict() if hasattr(cls, "__call__") else {},
            }
            for name, cls in self._plugin_classes.items()
        ]
    
    async def broadcast_tick(self, tick: TickData) -> None:
        """Broadcast a tick to all enabled plugins"""
        tasks = []
        for plugin_id, plugin in self._plugins.items():
            if self._enabled_plugins.get(plugin_id, False):
                tasks.append(plugin.on_tick(tick))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def collect_signals(self, tick: TickData) -> List[Signal]:
        """Collect signals from all enabled plugins"""
        signals = []
        for plugin_id, plugin in self._plugins.items():
            if self._enabled_plugins.get(plugin_id, False):
                try:
                    signal = await plugin.generate_signal(tick)
                    if signal:
                        signal.plugin_id = plugin_id
                        signal.plugin_name = plugin.metadata.name
                        signals.append(signal)
                except Exception as e:
                    logger.error(f"Error generating signal from {plugin_id}: {e}")
                    plugin._set_state(PluginState.ERROR)
                    plugin._set_error(str(e))
        return signals
    
    async def validate_signal(
        self,
        signal: Signal,
        account_balance: float,
    ) -> RiskValidation:
        """Validate a signal through its source plugin"""
        plugin = self._plugins.get(signal.plugin_id)
        if not plugin:
            return RiskValidation(
                plugin_id=signal.plugin_id,
                is_valid=False,
                approved_amount=0.0,
                max_amount=0.0,
                errors=[f"Plugin {signal.plugin_id} not found"],
            )
        
        return await plugin.validate_risk(signal, account_balance)
    
    def update_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Update plugin configuration"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        self._plugin_config[plugin_id] = config
        plugin.configure(config)
        return True
    
    def get_plugin_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin configuration"""
        return self._plugin_config.get(plugin_id)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all plugin configurations"""
        return self._plugin_config.copy()
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """Hot-reload a plugin"""
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        enabled = self._enabled_plugins.get(plugin_id, False)
        config = self._plugin_config.get(plugin_id, {})
        metadata = plugin.metadata
        
        # Cleanup old instance
        await plugin.cleanup()
        del self._plugins[plugin_id]
        
        # Create new instance
        plugin_class = self._plugin_classes.get(metadata.name.lower())
        if not plugin_class:
            logger.error(f"Cannot reload: class not found for {metadata.name}")
            return False
        
        new_plugin = plugin_class()
        await new_plugin.initialize()
        if config:
            new_plugin.configure(config)
        
        self._plugins[plugin_id] = new_plugin
        self._enabled_plugins[plugin_id] = enabled
        new_plugin._set_state(PluginState.RUNNING if enabled else PluginState.PAUSED)
        
        logger.info(f"Reloaded plugin: {plugin_id}")
        return True
    
    async def shutdown(self) -> None:
        """Shutdown all plugins and cleanup"""
        if self._observer:
            self._observer.stop()
            self._observer = None
        
        for plugin_id in list(self._plugins.keys()):
            await self.unload_plugin(plugin_id)
        
        logger.info("Plugin manager shutdown complete")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state for persistence"""
        return {
            "plugins": {
                plugin_id: {
                    "class_name": plugin.__class__.__name__,
                    "state": plugin.state.value,
                    "enabled": self._enabled_plugins.get(plugin_id, False),
                    "config": self._plugin_config.get(plugin_id, {}),
                    "metrics": plugin.metrics.to_dict(),
                }
                for plugin_id, plugin in self._plugins.items()
            },
            "available_types": list(self._plugin_classes.keys()),
        }
    
    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore state from persistence"""
        for plugin_id, plugin_state in state.get("plugins", {}).items():
            self._enabled_plugins[plugin_id] = plugin_state.get("enabled", False)
            self._plugin_config[plugin_id] = plugin_state.get("config", {})


class PluginFileWatcher(FileSystemEventHandler):
    """File system watcher for hot-reload functionality"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self._debounce_timers: Dict[str, asyncio.TimerHandle] = {}
    
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return
        
        plugin_id = Path(event.src_path).stem
        self._schedule_reload(plugin_id)
    
    def _schedule_reload(self, plugin_id: str) -> None:
        """Debounce reload requests"""
        # Cancel existing timer
        if plugin_id in self._debounce_timers:
            self._debounce_timers[plugin_id].cancel()
        
        # Schedule new reload
        loop = asyncio.get_event_loop()
        timer = loop.call_later(1.0, lambda: asyncio.create_task(
            self.plugin_manager.reload_plugin(plugin_id)
        ))
        self._debounce_timers[plugin_id] = timer


def create_plugin_manager(plugins_dir: Optional[str] = None) -> PluginManager:
    """Factory function to create a plugin manager"""
    return PluginManager(plugins_dir=plugins_dir)
