from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"


@dataclass
class PluginMetadata:
    plugin_id: str
    name: str
    version: str
    plugin_type: str  # strategy | indicator | risk | notification | utility
    author: str = ""
    description: str = ""
    min_platform_version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    settings_schema: Dict[str, Any] = field(default_factory=dict)
    state: str = PluginState.INSTALLED
    installed_at: str = ""
    updated_at: str = ""
    enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type,
            "author": self.author,
            "description": self.description,
            "min_platform_version": self.min_platform_version,
            "dependencies": self.dependencies,
            "settings_schema": self.settings_schema,
            "state": self.state,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "enabled": self.enabled,
        }


@dataclass
class PluginUpdate:
    plugin_id: str
    current_version: str
    available_version: str
    changelog: str = ""
    download_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "current_version": self.current_version,
            "available_version": self.available_version,
            "changelog": self.changelog,
            "download_url": self.download_url,
        }


class PluginManager:
    """Generic plugin management for non-strategy plugins."""

    def __init__(self, registry_path: str = "plugins_registry.json") -> None:
        self._registry_path = Path(registry_path)
        self._plugins: Dict[str, PluginMetadata] = {}
        self._hooks: Dict[str, List[Callable[..., Any]]] = {}
        self._settings: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
        logger.info("PluginManager initialized (%d plugins)", len(self._plugins))

    def _load_registry(self) -> None:
        if self._registry_path.exists():
            try:
                raw = json.loads(self._registry_path.read_text(encoding="utf-8"))
                for pid, pdata in raw.get("plugins", {}).items():
                    self._plugins[pid] = PluginMetadata(**pdata)
                self._settings = raw.get("settings", {})
                logger.info("Plugin registry loaded from %s", self._registry_path)
            except Exception:
                logger.exception("Failed to load plugin registry")

    def _save_registry(self) -> None:
        data = {
            "plugins": {pid: p.to_dict() for pid, p in self._plugins.items()},
            "settings": self._settings,
        }
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Plugin registry saved")

    def install(self, metadata: PluginMetadata) -> bool:
        if metadata.plugin_id in self._plugins:
            logger.warning("Plugin %s already installed", metadata.plugin_id)
            return False
        for dep in metadata.dependencies:
            if dep not in self._plugins:
                logger.error("Missing dependency %s for %s", dep, metadata.plugin_id)
                return False
        metadata.state = PluginState.INSTALLED
        metadata.installed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._plugins[metadata.plugin_id] = metadata
        self._settings[metadata.plugin_id] = {}
        self._save_registry()
        logger.info("Plugin installed: %s v%s", metadata.name, metadata.version)
        return True

    def enable(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.error("Plugin not found: %s", plugin_id)
            return False
        for dep in plugin.dependencies:
            dep_plugin = self._plugins.get(dep)
            if not dep_plugin or not dep_plugin.enabled:
                logger.error("Dependency %s not enabled for %s", dep, plugin_id)
                return False
        plugin.enabled = True
        plugin.state = PluginState.ENABLED
        self._save_registry()
        logger.info("Plugin enabled: %s", plugin_id)
        self._emit("plugin_enabled", plugin_id)
        return True

    def disable(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        for other in self._plugins.values():
            if plugin_id in other.dependencies and other.enabled:
                logger.error("Cannot disable %s: still required by %s", plugin_id, other.plugin_id)
                return False
        plugin.enabled = False
        plugin.state = PluginState.DISABLED
        self._save_registry()
        logger.info("Plugin disabled: %s", plugin_id)
        self._emit("plugin_disabled", plugin_id)
        return True

    def uninstall(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        plugin = self._plugins[plugin_id]
        for other in self._plugins.values():
            if plugin_id in other.dependencies:
                logger.error("Cannot uninstall %s: dependency of %s", plugin_id, other.plugin_id)
                return False
        if plugin.enabled:
            self.disable(plugin_id)
        del self._plugins[plugin_id]
        self._settings.pop(plugin_id, None)
        self._save_registry()
        logger.info("Plugin uninstalled: %s", plugin_id)
        return True

    def list_plugins(self, plugin_type: Optional[str] = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
        result = list(self._plugins.values())
        if plugin_type:
            result = [p for p in result if p.plugin_type == plugin_type]
        if enabled_only:
            result = [p for p in result if p.enabled]
        return [p.to_dict() for p in result]

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        plugin = self._plugins.get(plugin_id)
        return plugin.to_dict() if plugin else None

    def update_plugin(self, plugin_id: str, new_version: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.version = new_version
        plugin.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        plugin.state = PluginState.INSTALLED
        self._save_registry()
        logger.info("Plugin updated: %s -> v%s", plugin_id, new_version)
        return True

    def check_updates(self) -> List[Dict[str, Any]]:
        updates: List[PluginUpdate] = []
        for pid, plugin in self._plugins.items():
            if plugin.enabled:
                updates.append(PluginUpdate(
                    plugin_id=pid,
                    current_version=plugin.version,
                    available_version=plugin.version,
                ))
        return [u.to_dict() for u in updates]

    def register_hook(self, event: str, callback: Callable[..., Any]) -> None:
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def _emit(self, event: str, *args: Any) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(*args)
            except Exception:
                logger.exception("Hook error for event %s", event)

    def get_settings(self, plugin_id: str) -> Dict[str, Any]:
        return dict(self._settings.get(plugin_id, {}))

    def update_settings(self, plugin_id: str, settings: Dict[str, Any]) -> bool:
        if plugin_id not in self._plugins:
            return False
        self._settings.setdefault(plugin_id, {}).update(settings)
        self._save_registry()
        logger.info("Settings updated for %s", plugin_id)
        return True

    def get_enabled_by_type(self, plugin_type: str) -> List[PluginMetadata]:
        return [p for p in self._plugins.values() if p.plugin_type == plugin_type and p.enabled]

    def summary(self) -> Dict[str, Any]:
        return {
            "total": len(self._plugins),
            "enabled": sum(1 for p in self._plugins.values() if p.enabled),
            "by_type": {
                t: sum(1 for p in self._plugins.values() if p.plugin_type == t)
                for t in {"strategy", "indicator", "risk", "notification", "utility"}
            },
        }
