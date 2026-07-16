"""
Feature SDK
===========

SDK for feature flag management.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = SDKLogger("feature")


@dataclass
class FeatureContext:
    """Context for feature flag evaluation"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: str = "development"
    attributes: Dict[str, Any] = field(default_factory=dict)


class FeatureClient(SmartPipSDK):
    """
    Feature flag client.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._flags: Dict[str, bool] = {}
        self._refresh_interval = 60  # seconds
    
    def _on_initialize(self) -> None:
        """Initialize feature client"""
        self._load_flags()
    
    def _load_flags(self) -> None:
        """Load feature flags"""
        # Load from API or cache
        pass
    
    def is_enabled(self, flag_name: str, context: Optional[FeatureContext] = None) -> bool:
        """Check if a feature flag is enabled"""
        # Check local cache first
        if flag_name in self._flags:
            return self._flags[flag_name]
        
        # Fallback to config service
        try:
            from config import config_service
            return config_service.is_flag_enabled(flag_name, context.__dict__ if context else None)
        except Exception:
            return False
    
    def get_flag_value(self, flag_name: str, default: Any = None, context: Optional[FeatureContext] = None) -> Any:
        """Get feature flag value"""
        if self.is_enabled(flag_name, context):
            return True
        return default
    
    def refresh(self) -> None:
        """Refresh feature flags"""
        self._load_flags()
        logger.info("Feature flags refreshed")
    
    def evaluate_all(self, context: Optional[FeatureContext] = None) -> Dict[str, bool]:
        """Evaluate all flags for a context"""
        return {flag: self.is_enabled(flag, context) for flag in self._flags}
