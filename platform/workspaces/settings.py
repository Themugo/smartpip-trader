from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class APIKeyConfig:
    provider: str
    key_masked: str
    is_valid: bool = True
    last_validated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "key_masked": self.key_masked,
            "is_valid": self.is_valid,
            "last_validated": self.last_validated,
        }


@dataclass
class NotificationPrefs:
    trade_alerts: bool = True
    risk_alerts: bool = True
    system_alerts: bool = True
    email_enabled: bool = False
    telegram_enabled: bool = False
    webhook_enabled: bool = False
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_alerts": self.trade_alerts,
            "risk_alerts": self.risk_alerts,
            "system_alerts": self.system_alerts,
            "email_enabled": self.email_enabled,
            "telegram_enabled": self.telegram_enabled,
            "webhook_enabled": self.webhook_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
        }


@dataclass
class AppSettings:
    theme: str = "dark"
    language: str = "en"
    timezone: str = "UTC"
    default_symbol: str = "Volatility 75"
    default_timeframe: str = "1m"
    auto_trade: bool = False
    max_open_trades: int = 5
    risk_per_trade: float = 0.02
    dashboard_layout: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "default_symbol": self.default_symbol,
            "default_timeframe": self.default_timeframe,
            "auto_trade": self.auto_trade,
            "max_open_trades": self.max_open_trades,
            "risk_per_trade": self.risk_per_trade,
            "dashboard_layout": self.dashboard_layout,
        }


class SettingsWorkspace(WorkspaceBase):
    """All configuration, API keys, notification prefs, workspace layout."""

    def __init__(self) -> None:
        super().__init__("settings", "Settings", "settings")
        self._api_keys: Dict[str, APIKeyConfig] = {}
        self._notification_prefs = NotificationPrefs()
        self._app_settings = AppSettings()
        self._workspace_order: List[str] = []

    def initialize(self) -> bool:
        logger.info("Settings workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 2,
            "rows": 3,
            "panels": [
                {"id": "api_keys", "title": "API Keys", "col_span": 1, "row_span": 1, "widget": "key_manager"},
                {"id": "trading_settings", "title": "Trading Settings", "col_span": 1, "row_span": 1, "widget": "config_form"},
                {"id": "notification_prefs", "title": "Notifications", "col_span": 1, "row_span": 1, "widget": "toggle_grid"},
                {"id": "appearance", "title": "Appearance", "col_span": 1, "row_span": 1, "widget": "theme_picker"},
                {"id": "workspace_layout", "title": "Workspace Layout", "col_span": 2, "row_span": 1, "widget": "sortable_list"},
                {"id": "export_import", "title": "Export / Import", "col_span": 2, "row_span": 1, "widget": "button_panel"},
            ],
        }

    def set_api_key(self, provider: str, key: str) -> APIKeyConfig:
        masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
        config = APIKeyConfig(provider=provider, key_masked=masked)
        self._api_keys[provider] = config
        logger.info("API key set for %s", provider)
        return config

    def remove_api_key(self, provider: str) -> bool:
        if provider in self._api_keys:
            del self._api_keys[provider]
            logger.info("API key removed for %s", provider)
            return True
        return False

    def get_api_keys(self) -> List[Dict[str, Any]]:
        return [k.to_dict() for k in self._api_keys.values()]

    def update_notification_prefs(self, prefs: Dict[str, Any]) -> None:
        for k, v in prefs.items():
            if hasattr(self._notification_prefs, k):
                setattr(self._notification_prefs, k, v)
        logger.info("Notification prefs updated: %s", prefs)

    def get_notification_prefs(self) -> Dict[str, Any]:
        return self._notification_prefs.to_dict()

    def update_app_settings(self, settings: Dict[str, Any]) -> None:
        for k, v in settings.items():
            if hasattr(self._app_settings, k):
                setattr(self._app_settings, k, v)
        logger.info("App settings updated: %s", settings)

    def get_app_settings(self) -> Dict[str, Any]:
        return self._app_settings.to_dict()

    def set_workspace_order(self, order: List[str]) -> None:
        self._workspace_order = list(order)
        logger.info("Workspace order updated: %s", order)

    def get_workspace_order(self) -> List[str]:
        return list(self._workspace_order)

    def export_settings(self) -> Dict[str, Any]:
        return {
            "api_keys": self.get_api_keys(),
            "notification_prefs": self.get_notification_prefs(),
            "app_settings": self.get_app_settings(),
            "workspace_order": self.get_workspace_order(),
        }

    def import_settings(self, data: Dict[str, Any]) -> bool:
        try:
            if "notification_prefs" in data:
                self.update_notification_prefs(data["notification_prefs"])
            if "app_settings" in data:
                self.update_app_settings(data["app_settings"])
            if "workspace_order" in data:
                self.set_workspace_order(data["workspace_order"])
            logger.info("Settings imported successfully")
            return True
        except Exception:
            logger.exception("Settings import failed")
            return False

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["api_key_count"] = len(self._api_keys)
        state["state"]["app_settings"] = self.get_app_settings()
        return state
