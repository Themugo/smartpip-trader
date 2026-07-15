"""
Configuration Manager

Manages application configuration from multiple sources.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfigSource:
    """Configuration source"""
    name: str
    priority: int
    values: Dict[str, Any]


class ConfigManager:
    """
    Manages configuration from multiple sources.
    
    Sources (in priority order):
    1. Environment variables
    2. Command line arguments
    3. Configuration files
    4. Default values
    """
    
    def __init__(self):
        self._sources: List[ConfigSource] = []
        self._cache: Dict[str, Any] = {}
        self._cache_valid = False
    
    def add_source(
        self,
        name: str,
        values: Dict[str, Any],
        priority: int = 0,
    ) -> "ConfigManager":
        """Add a configuration source"""
        source = ConfigSource(name=name, priority=priority, values=values)
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority, reverse=True)
        self._cache_valid = False
        return self
    
    def add_file(self, path: str, priority: int = 0) -> "ConfigManager":
        """Add configuration from file"""
        try:
            with open(path, 'r') as f:
                if path.endswith('.json'):
                    values = json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {path}")
                    return self
                
                return self.add_source(name=path, values=values, priority=priority)
        except Exception as e:
            logger.error(f"Failed to load config file {path}: {e}")
            return self
    
    def add_env_prefix(self, prefix: str = "APP_", priority: int = 100) -> "ConfigManager":
        """Add environment variables with prefix as config source"""
        values = {}
        prefix_upper = prefix.upper()
        
        for key, value in os.environ.items():
            if key.startswith(prefix_upper):
                config_key = key[len(prefix):].lower()
                values[config_key] = self._parse_value(value)
        
        if values:
            self.add_source(name=f"env:{prefix}", values=values, priority=priority)
        
        return self
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
        
        Returns:
            Configuration value
        """
        # Check cache
        if self._cache_valid and key in self._cache:
            return self._cache[key]
        
        # Find value from sources
        value = default
        
        for source in self._sources:
            found_value = self._get_nested(source.values, key)
            if found_value is not None:
                value = found_value
                break
        
        # Cache the value
        self._cache[key] = value
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get all values in a section"""
        result = {}
        
        for source in self._sources:
            section_values = self._get_nested(source.values, section)
            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    if key not in result:
                        result[key] = value
        
        return result
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as flat dictionary"""
        result = {}
        
        for source in self._sources:
            self._flatten_dict(source.values, "", result)
        
        return result
    
    def _get_nested(self, data: Dict, key: str) -> Any:
        """Get value using dot notation"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                return None
        
        return current
    
    def _flatten_dict(
        self,
        data: Dict,
        prefix: str,
        result: Dict,
    ) -> None:
        """Flatten nested dictionary"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._flatten_dict(value, full_key, result)
            else:
                result[full_key] = value
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse string value to appropriate type"""
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # JSON
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # String
        return value
    
    def reload(self):
        """Reload configuration"""
        self._cache_valid = False
        self._cache = {}
    
    def validate(self) -> List[str]:
        """Validate configuration and return errors"""
        errors = []
        
        # Check required values
        required = ['environment', 'log_level']
        for key in required:
            if self.get(key) is None:
                errors.append(f"Missing required config: {key}")
        
        return errors
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status"""
        return {
            "sources": [s.name for s in self._sources],
            "keys_cached": len(self._cache),
            "validated": len(self.validate()) == 0,
        }
