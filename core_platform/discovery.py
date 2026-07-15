"""
Module Discovery

Discovers and registers modules dynamically.
"""

import importlib
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModuleDiscovery:
    """
    Discovers and loads modules dynamically.
    
    Features:
    - Package scanning
    - Auto-registration
    - Dependency ordering
    """
    
    def __init__(self, base_package: str = "modules"):
        self._base_package = base_package
        self._modules: Dict[str, Any] = {}
        self._discovered: List[str] = []
    
    def discover(self, package_path: Optional[str] = None) -> List[str]:
        """
        Discover modules in the base package.
        
        Returns:
            List of discovered module names
        """
        base = package_path or self._base_package
        
        try:
            # Get package directory
            pkg = importlib.import_module(base)
            pkg_dir = os.path.dirname(pkg.__file__)
            
            # Find all Python files
            discovered = []
            for filename in os.listdir(pkg_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    module_name = filename[:-3]
                    full_name = f"{base}.{module_name}"
                    discovered.append(full_name)
                    logger.debug(f"Discovered module: {full_name}")
            
            self._discovered = discovered
            return discovered
            
        except ImportError as e:
            logger.warning(f"Could not import base package {base}: {e}")
            return []
    
    def load(self, module_name: str) -> Any:
        """
        Load a module by name.
        
        Args:
            module_name: Full module path
            
        Returns:
            The loaded module
        """
        if module_name in self._modules:
            return self._modules[module_name]
        
        try:
            module = importlib.import_module(module_name)
            self._modules[module_name] = module
            logger.info(f"Loaded module: {module_name}")
            return module
            
        except ImportError as e:
            logger.error(f"Failed to load {module_name}: {e}")
            raise
    
    def load_all(self) -> Dict[str, Any]:
        """Load all discovered modules"""
        results = {}
        for name in self._discovered:
            try:
                results[name] = self.load(name)
            except Exception:
                pass
        return results
    
    def get_module(self, module_name: str) -> Optional[Any]:
        """Get a loaded module"""
        return self._modules.get(module_name)
    
    def get_discovered(self) -> List[str]:
        """Get list of discovered module names"""
        return self._discovered.copy()
    
    def get_loaded(self) -> List[str]:
        """Get list of loaded module names"""
        return list(self._modules.keys())
