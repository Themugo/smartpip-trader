"""
SDK Validators
==============

Validators for plugins, strategies, and dependencies.
"""

import os
import sys
import ast
import importlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class PluginValidator:
    """Validate plugin code"""
    
    REQUIRED_METHODS = ["on_init", "on_start", "on_stop"]
    OPTIONAL_METHODS = ["on_tick", "on_signal", "on_error"]
    
    def validate_file(self, filepath: str) -> ValidationResult:
        """Validate a plugin file"""
        errors = []
        warnings = []
        
        if not os.path.exists(filepath):
            return ValidationResult(False, [f"File not found: {filepath}"], [])
        
        try:
            with open(filepath, "r") as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            # Find Plugin class
            plugin_classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Plugin":
                            plugin_classes.append(node.name)
            
            if not plugin_classes:
                errors.append("No Plugin class found")
            
            # Check for required methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for method in self.REQUIRED_METHODS:
                        if not any(m.name == method for m in node.body if isinstance(m, ast.FunctionDef)):
                            warnings.append(f"{node.name} missing method: {method}")
            
            # Try to import
            try:
                spec = importlib.util.spec_from_file_location("plugin", filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                errors.append(f"Import error: {e}")
        
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_module(self, module) -> ValidationResult:
        """Validate a plugin module"""
        errors = []
        warnings = []
        
        # Check for metadata
        for name in dir(module):
            obj = getattr(module, name)
            if hasattr(obj, 'metadata'):
                if not obj.metadata:
                    errors.append(f"{name} has empty metadata")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class StrategyValidator:
    """Validate strategy code"""
    
    REQUIRED_METHODS = ["on_init", "on_tick"]
    
    def validate_file(self, filepath: str) -> ValidationResult:
        """Validate a strategy file"""
        errors = []
        warnings = []
        
        if not os.path.exists(filepath):
            return ValidationResult(False, [f"File not found: {filepath}"], [])
        
        try:
            with open(filepath, "r") as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            # Find Strategy class
            strategy_classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Strategy":
                            strategy_classes.append(node.name)
            
            if not strategy_classes:
                errors.append("No Strategy class found")
            
            # Check for required methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for method in self.REQUIRED_METHODS:
                        if not any(m.name == method for m in node.body if isinstance(m, ast.FunctionDef)):
                            warnings.append(f"{node.name} missing method: {method}")
        
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class DependencyChecker:
    """Check project dependencies"""
    
    def __init__(self):
        self.required = ["requests", "numpy", "pandas"]
        self.optional = ["scikit-learn", "tensorflow", "torch"]
    
    def check(self) -> ValidationResult:
        """Check all dependencies"""
        errors = []
        warnings = []
        
        for pkg in self.required:
            if not self._is_installed(pkg):
                errors.append(f"Required package not installed: {pkg}")
        
        for pkg in self.optional:
            if not self._is_installed(pkg):
                warnings.append(f"Optional package not installed: {pkg}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _is_installed(self, package: str) -> bool:
        """Check if package is installed"""
        try:
            __import__(package)
            return True
        except ImportError:
            return False
    
    def get_missing(self) -> List[str]:
        """Get list of missing required packages"""
        checker = self.check()
        return checker.errors


class ConfigValidator:
    """Validate configuration files"""
    
    def validate(self, config: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against schema"""
        errors = []
        warnings = []
        
        # Check required fields
        for field, rules in schema.items():
            if rules.get("required", False) and field not in config:
                errors.append(f"Missing required field: {field}")
            
            if field in config:
                value = config[field]
                
                # Type check
                expected_type = rules.get("type")
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
                
                # Range check
                if isinstance(value, (int, float)):
                    if "min" in rules and value < rules["min"]:
                        errors.append(f"{field} below minimum: {rules['min']}")
                    if "max" in rules and value > rules["max"]:
                        errors.append(f"{field} above maximum: {rules['max']}")
                
                # Allowed values
                if "allowed" in rules and value not in rules["allowed"]:
                    errors.append(f"{field} not in allowed values: {rules['allowed']}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
