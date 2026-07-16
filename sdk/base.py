"""
SDK Base Module
==============

Base classes and utilities for all SDKs.
"""

import os
import sys
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Type
from enum import Enum

logger = logging.getLogger(__name__)


class SDKError(Exception):
    """Base SDK error"""
    pass


class SDKWarning(UserWarning):
    """SDK warning"""
    pass


class SDKLogLevel(Enum):
    """Log levels"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class SDKConfig:
    """SDK configuration"""
    api_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    environment: str = "development"
    log_level: SDKLogLevel = SDKLogLevel.INFO
    timeout: float = 30.0
    max_retries: int = 3
    cache_dir: Optional[str] = None
    data_dir: Optional[str] = None
    config_dir: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "SDKConfig":
        """Load config from environment variables"""
        return cls(
            api_url=os.environ.get("SMARTPIP_API_URL", "http://localhost:8000"),
            api_key=os.environ.get("SMARTPIP_API_KEY"),
            environment=os.environ.get("SMARTPIP_ENV", "development"),
            cache_dir=os.environ.get("SMARTPIP_CACHE_DIR"),
            data_dir=os.environ.get("SMARTPIP_DATA_DIR"),
            config_dir=os.environ.get("SMARTPIP_CONFIG_DIR"),
        )
    
    @classmethod
    def from_file(cls, path: str) -> "SDKConfig":
        """Load config from file"""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)


class SDKLogger:
    """SDK Logger with structured logging"""
    
    def __init__(self, name: str, level: SDKLogLevel = SDKLogLevel.INFO):
        self.name = name
        self.level = level
        self._logger = logging.getLogger(f"sdk.{name}")
        self._setup_handler()
    
    def _setup_handler(self) -> None:
        """Setup logging handler"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        self._logger.addHandler(handler)
        self._logger.setLevel(self.level.value)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self._logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self._logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self._logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message"""
        self._logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message"""
        self._logger.critical(message, extra=kwargs)


class SmartPipSDK:
    """
    Base SmartPip SDK class.
    
    All SDKs should inherit from this class.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, config: Optional[SDKConfig] = None):
        self.config = config or SDKConfig.from_env()
        self._logger = SDKLogger(self.__class__.__name__)
        self._initialized = False
        self._extensions: Dict[str, Any] = {}
    
    def initialize(self) -> None:
        """Initialize the SDK"""
        if self._initialized:
            return
        
        self._logger.info(f"Initializing {self.__class__.__name__}")
        self._on_initialize()
        self._initialized = True
    
    def _on_initialize(self) -> None:
        """Override to add custom initialization"""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if SDK is initialized"""
        return self._initialized
    
    def register_extension(self, name: str, extension: Any) -> None:
        """Register an extension"""
        self._extensions[name] = extension
    
    def get_extension(self, name: str) -> Optional[Any]:
        """Get a registered extension"""
        return self._extensions.get(name)
    
    def health_check(self) -> bool:
        """Check SDK health"""
        return self._initialized
    
    def get_version(self) -> str:
        """Get SDK version"""
        return "1.0.0"
    
    def close(self) -> None:
        """Clean up SDK resources"""
        self._on_close()
        self._initialized = False
    
    def _on_close(self) -> None:
        """Override to add custom cleanup"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class SDKDecorator:
    """Base class for SDK decorators"""
    
    def __init__(self, sdk: SmartPipSDK):
        self.sdk = sdk
    
    def wrap(self, func: Callable) -> Callable:
        """Wrap a function"""
        return func
    
    def unwrap(self, func: Callable) -> Callable:
        """Unwrap a function"""
        return func


class SDKHook:
    """Hook system for SDK lifecycle"""
    
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
    
    def register(self, event: str, callback: Callable) -> None:
        """Register a hook callback"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def unregister(self, event: str, callback: Callable) -> None:
        """Unregister a hook callback"""
        if event in self._hooks:
            self._hooks[event].remove(callback)
    
    def trigger(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event"""
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook error for {event}: {e}")
        return results


class SDKContext:
    """Context object for SDK operations"""
    
    def __init__(self, sdk: SmartPipSDK, **kwargs):
        self.sdk = sdk
        self.timestamp = time.time()
        self._data = kwargs
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get context data"""
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set context data"""
        self._data[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sdk": self.sdk.__class__.__name__,
            "timestamp": self.timestamp,
            **self._data
        }


class SDKValidator:
    """Base validator for SDK components"""
    
    def __init__(self):
        self._errors: List[str] = []
        self._warnings: List[str] = []
    
    def validate(self, component: Any) -> bool:
        """Validate a component"""
        raise NotImplementedError
    
    def get_errors(self) -> List[str]:
        """Get validation errors"""
        return self._errors
    
    def get_warnings(self) -> List[str]:
        """Get validation warnings"""
        return self._warnings
    
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return len(self._errors) == 0


# Import requests for HTTP calls
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class APIClient:
    """HTTP API client for SDK"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = None
    
    @property
    def session(self):
        """Get or create session"""
        if self._session is None and HAS_REQUESTS:
            self._session = requests.Session()
            if self.api_key:
                self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        return self._session
    
    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        if not HAS_REQUESTS:
            raise SDKError("requests library not installed")
        
        url = f"{self.base_url}{path}"
        response = self.session.get(url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def post(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        if not HAS_REQUESTS:
            raise SDKError("requests library not installed")
        
        url = f"{self.base_url}{path}"
        response = self.session.post(url, json=data, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def put(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        if not HAS_REQUESTS:
            raise SDKError("requests library not installed")
        
        url = f"{self.base_url}{path}"
        response = self.session.put(url, json=data, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        if not HAS_REQUESTS:
            raise SDKError("requests library not installed")
        
        url = f"{self.base_url}{path}"
        response = self.session.delete(url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def close(self) -> None:
        """Close session"""
        if self._session:
            self._session.close()
            self._session = None
