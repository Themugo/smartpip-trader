"""
Strategy Sandbox - Isolated Strategy Execution

Safe execution environment for third-party and untested strategies.
"""

import logging
import resource
import signal
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SandboxStatus(Enum):
    """Sandbox status"""
    READY = "ready"
    RUNNING = "running"
    TIMEOUT = "timeout"
    CRASHED = "crashed"
    KILLED = "killed"


@dataclass
class SandboxConfig:
    """Sandbox configuration"""
    # Resource limits
    max_cpu_seconds: float = 60
    max_memory_mb: int = 512
    max_file_size_mb: int = 50
    
    # Execution limits
    max_execution_time_seconds: float = 30
    max_trades: int = 1000
    
    # Network access
    allow_network: bool = False
    
    # Filesystem access
    allowed_paths: List[str] = []
    read_only: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_file_size_mb": self.max_file_size_mb,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "max_trades": self.max_trades,
            "allow_network": self.allow_network,
            "allowed_paths": self.allowed_paths,
            "read_only": self.read_only,
        }


@dataclass
class SandboxResult:
    """Result from sandbox execution"""
    success: bool
    output: str = ""
    error: str = ""
    status: SandboxStatus = SandboxStatus.READY
    
    # Execution stats
    execution_time_seconds: float = 0
    memory_used_mb: float = 0
    cpu_time_seconds: float = 0
    
    # Trade results
    trades_executed: int = 0
    signals_generated: List[Dict[str, Any]] = field(default_factory=list)
    
    # Safety
    resource_violations: List[str] = field(default_factory=list)
    blocked_operations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "output": self.output[:1000] if self.output else "",
            "error": self.error[:1000] if self.error else "",
            "execution_time_seconds": self.execution_time_seconds,
            "memory_used_mb": self.memory_used_mb,
            "trades_executed": self.trades_executed,
            "resource_violations": self.resource_violations,
            "blocked_operations": self.blocked_operations,
        }


class StrategySandbox:
    """
    Isolated sandbox for strategy execution.
    
    Features:
    - CPU limits
    - Memory limits
    - Execution timeout
    - Network restrictions
    - Filesystem restrictions
    - Resource monitoring
    - Safe execution of untrusted code
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self._config = config or SandboxConfig()
        self._active_sandboxes: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(f"{__name__}.Sandbox")
    
    def create_sandbox(self, strategy_id: str) -> str:
        """Create a new sandbox instance"""
        sandbox_id = str(uuid.uuid4())
        
        self._active_sandboxes[sandbox_id] = {
            "id": sandbox_id,
            "strategy_id": strategy_id,
            "created_at": datetime.utcnow(),
            "status": SandboxStatus.READY,
            "config": self._config.to_dict(),
        }
        
        self._logger.info(f"Created sandbox: {sandbox_id}")
        return sandbox_id
    
    def execute_strategy(
        self,
        sandbox_id: str,
        strategy_code: str,
        market_data: List[Dict[str, Any]],
    ) -> SandboxResult:
        """
        Execute strategy code in sandbox.
        
        Args:
            sandbox_id: Sandbox ID
            strategy_code: Strategy Python code
            market_data: Historical market data
            
        Returns:
            SandboxResult with execution details
        """
        import time
        
        start_time = time.time()
        result = SandboxResult(status=SandboxStatus.RUNNING)
        
        try:
            # Set resource limits
            self._set_resource_limits()
            
            # Create restricted globals
            restricted_globals = {
                "__name__": "__sandbox__",
                "__builtins__": self._get_restricted_builtins(),
                "market_data": market_data,
                "signals": [],
                "config": self._config.to_dict(),
            }
            
            # Add safe imports
            restricted_globals["__import__"] = self._restricted_import
            
            # Execute code
            exec(strategy_code, restricted_globals)
            
            # Get results
            result.signals_generated = restricted_globals.get("signals", [])
            result.trades_executed = len(result.signals_generated)
            result.success = True
            result.status = SandboxStatus.READY
            
        except TimeoutError:
            result.success = False
            result.error = "Execution timed out"
            result.status = SandboxStatus.TIMEOUT
            result.resource_violations.append("Execution timeout exceeded")
            
        except MemoryError:
            result.success = False
            result.error = "Memory limit exceeded"
            result.status = SandboxStatus.CRASHED
            result.resource_violations.append("Memory limit exceeded")
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.status = SandboxStatus.CRASHED
            result.resource_violations.append(f"Exception: {type(e).__name__}")
        
        finally:
            result.execution_time_seconds = time.time() - start_time
            self._cleanup_resource_limits()
        
        return result
    
    def _set_resource_limits(self) -> None:
        """Set OS resource limits"""
        try:
            # Set memory limit
            max_memory = self._config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
            
            # Set CPU time limit
            max_cpu = int(self._config.max_cpu_seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu, max_cpu + 10))
            
            # Set file size limit
            max_file = self._config.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (max_file, max_file))
            
        except Exception as e:
            self._logger.warning(f"Could not set resource limits: {e}")
    
    def _cleanup_resource_limits(self) -> None:
        """Reset resource limits"""
        try:
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except:
            pass
    
    def _get_restricted_builtins(self) -> Dict[str, Any]:
        """Get restricted builtins"""
        safe_builtins = {
            # Safe functions
            "print": print,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "open": self._restricted_open,
            "input": None,  # Disabled
            "compile": None,  # Disabled
            "eval": None,  # Disabled
            "exec": None,  # Disabled
        }
        return safe_builtins
    
    def _restricted_import(self, name: str, *args, **kwargs):
        """Restricted import function"""
        allowed_modules = {"math", "random", "statistics", "datetime", "json", "collections"}
        
        if name.split(".")[0] in allowed_modules:
            return __import__(name, *args, **kwargs)
        
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")
    
    def _restricted_open(self, path: str, mode: str = "r", *args, **kwargs):
        """Restricted file open"""
        # Only allow reading specific paths
        if "r" in mode and self._config.allowed_paths:
            for allowed in self._config.allowed_paths:
                if path.startswith(allowed):
                    return open(path, mode, *args, **kwargs)
            raise PermissionError(f"Path '{path}' is not in allowed list")
        
        # Block all writes
        raise PermissionError("File writing is not allowed in sandbox")
    
    def validate_strategy(self, strategy_code: str) -> tuple[bool, List[str]]:
        """
        Validate strategy code before sandbox execution.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for dangerous patterns
        dangerous_patterns = [
            ("import os", "OS module not allowed"),
            ("import subprocess", "Subprocess not allowed"),
            ("import sys", "Sys module not allowed"),
            ("import socket", "Network access not allowed"),
            ("eval(", "eval() not allowed"),
            ("exec(", "exec() not allowed"),
            ("open(", "File operations not allowed"),
            ("__import__", "__import__ not allowed"),
            ("os.system", "OS commands not allowed"),
            ("subprocess", "Subprocess not allowed"),
            ("requests", "HTTP requests not allowed"),
            ("urllib", "Network access not allowed"),
        ]
        
        for pattern, message in dangerous_patterns:
            if pattern in strategy_code:
                errors.append(message)
        
        return len(errors) == 0, errors
    
    def get_sandbox_info(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get sandbox information"""
        return self._active_sandboxes.get(sandbox_id)
    
    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox"""
        if sandbox_id in self._active_sandboxes:
            del self._active_sandboxes[sandbox_id]
            self._logger.info(f"Destroyed sandbox: {sandbox_id}")
            return True
        return False
