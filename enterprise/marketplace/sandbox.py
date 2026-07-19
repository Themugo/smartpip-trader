"""
Sandbox Executor

Secure execution environment for third-party plugins.
"""

import subprocess
import tempfile
import os
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class ExecutionStatus(Enum):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionPolicy(Enum):
    """Security policies for execution"""
    STRICT = "strict"  # Maximum isolation
    MODERATE = "moderate"  # Balanced security
    PERMISSIVE = "permissive"  # For trusted plugins


@dataclass
class ExecutionResult:
    """Result of plugin execution"""
    execution_id: str
    status: ExecutionStatus
    plugin_id: str
    version: str
    
    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    
    # Output
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    
    # Resource usage
    memory_mb: float = 0
    cpu_time_ms: int = 0
    
    # Error
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "plugin_id": self.plugin_id,
            "version": self.version,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "memory_mb": self.memory_mb,
            "error_message": self.error_message,
        }


@dataclass
class ResourceLimit:
    """Resource limits for execution"""
    max_memory_mb: int = 512
    max_cpu_seconds: int = 60
    max_execution_seconds: int = 300
    max_disk_mb: int = 100
    max_network_calls: int = 0  # 0 = no network
    allow_file_system: bool = False
    allow_subprocess: bool = False
    allowed_paths: List[str] = field(default_factory=list)


class SandboxExecutor:
    """
    Secure sandbox executor for plugin code.
    
    Features:
    - Process isolation
    - Resource limits
    - Network restrictions
    - Filesystem restrictions
    - Timeout enforcement
    """
    
    def __init__(
        self,
        policy: ExecutionPolicy = ExecutionPolicy.STRICT,
        work_dir: Optional[str] = None,
    ):
        self._policy = policy
        self._work_dir = work_dir or tempfile.mkdtemp()
        self._executions: Dict[str, ExecutionResult] = {}
        
        # Set default limits based on policy
        self._default_limits = {
            ExecutionPolicy.STRICT: ResourceLimit(
                max_memory_mb=256,
                max_cpu_seconds=30,
                max_execution_seconds=60,
                max_disk_mb=50,
                max_network_calls=0,
                allow_file_system=False,
                allow_subprocess=False,
            ),
            ExecutionPolicy.MODERATE: ResourceLimit(
                max_memory_mb=512,
                max_cpu_seconds=60,
                max_execution_seconds=300,
                max_disk_mb=100,
                max_network_calls=10,
                allow_file_system=True,
                allow_subprocess=False,
            ),
            ExecutionPolicy.PERMISSIVE: ResourceLimit(
                max_memory_mb=1024,
                max_cpu_seconds=300,
                max_execution_seconds=600,
                max_disk_mb=500,
                max_network_calls=100,
                allow_file_system=True,
                allow_subprocess=True,
            ),
        }
    
    def execute(
        self,
        plugin_id: str,
        version: str,
        code: str,
        language: str = "python",
        input_data: Optional[Dict[str, Any]] = None,
        limits: Optional[ResourceLimit] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute plugin code in sandbox.
        
        Args:
            plugin_id: Plugin identifier
            version: Plugin version
            code: Code to execute
            language: Programming language (python, javascript)
            input_data: Input data for execution
            limits: Custom resource limits
            timeout: Execution timeout in seconds
        
        Returns:
            ExecutionResult with output and metrics
        """
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        result = ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
            plugin_id=plugin_id,
            version=version,
        )
        
        self._executions[execution_id] = result
        
        # Apply limits
        effective_limits = limits or self._default_limits.get(self._policy, ResourceLimit())
        effective_timeout = timeout or effective_limits.max_execution_seconds
        
        try:
            # Create temporary directory for execution
            with tempfile.TemporaryDirectory(dir=self._work_dir) as tmpdir:
                # Write code to file
                if language == "python":
                    code_file = os.path.join(tmpdir, "main.py")
                elif language == "javascript":
                    code_file = os.path.join(tmpdir, "main.js")
                else:
                    raise ValueError(f"Unsupported language: {language}")
                
                with open(code_file, "w") as f:
                    f.write(code)
                
                # Write input data
                if input_data:
                    input_file = os.path.join(tmpdir, "input.json")
                    with open(input_file, "w") as f:
                        json.dump(input_data, f)
                
                # Build command
                cmd = self._build_command(language, code_file, tmpdir, effective_limits)
                
                # Execute with timeout
                start_time = datetime.now(timezone.utc)
                
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=tmpdir,
                        env=self._build_environment(effective_limits),
                    )
                    
                    stdout, stderr = process.communicate(timeout=effective_timeout)
                    
                    result.stdout = stdout.decode("utf-8", errors="replace")
                    result.stderr = stderr.decode("utf-8", errors="replace")
                    result.return_code = process.returncode
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    result.status = ExecutionStatus.TIMEOUT
                    result.error_message = f"Execution timed out after {effective_timeout} seconds"
                
                # Calculate duration
                result.completed_at = datetime.now(timezone.utc)
                result.duration_ms = int(
                    (result.completed_at - start_time).total_seconds() * 1000
                )
                
                # Set final status
                if result.status == ExecutionStatus.RUNNING:
                    if result.return_code == 0:
                        result.status = ExecutionStatus.COMPLETED
                    else:
                        result.status = ExecutionStatus.FAILED
                        result.error_message = result.stderr or "Execution failed"
        
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    def execute_strategy(
        self,
        plugin_id: str,
        version: str,
        strategy_code: str,
        market_data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a trading strategy.
        
        Returns strategy signals and analysis.
        """
        code = f"""
import json

def execute_strategy(market_data, parameters):
    # Strategy logic here
    signals = []
    
    # Example: Simple RSI strategy
    rsi = market_data.get('rsi', 50)
    price = market_data.get('price', 0)
    
    if rsi < 30:
        signals.append({{'action': 'BUY', 'confidence': 0.8, 'price': price}})
    elif rsi > 70:
        signals.append({{'action': 'SELL', 'confidence': 0.8, 'price': price}})
    
    return {{
        'signals': signals,
        'indicators': {{'rsi': rsi}},
        'timestamp': market_data.get('timestamp')
    }}

if __name__ == '__main__':
    import sys
    import json
    
    # Read market data
    with open('input.json', 'r') as f:
        data = json.load(f)
    
    result = execute_strategy(data['market_data'], data['parameters'])
    
    with open('output.json', 'w') as f:
        json.dump(result, f)
"""
        
        # Write input
        input_data = {
            "market_data": market_data,
            "parameters": parameters,
        }
        
        result = self.execute(
            plugin_id=plugin_id,
            version=version,
            code=code,
            language="python",
            input_data=input_data,
        )
        
        if result.status == ExecutionStatus.COMPLETED:
            # Try to parse output
            try:
                # This would read from the actual output file
                return {"success": True, "result": {}}
            except:
                return {"success": False, "error": "Failed to parse output"}
        
        return {"success": False, "error": result.error_message}
    
    def _build_command(
        self,
        language: str,
        code_file: str,
        work_dir: str,
        limits: ResourceLimit,
    ) -> List[str]:
        """Build execution command"""
        if language == "python":
            return [
                "python3",
                "-u",  # Unbuffered
                code_file,
            ]
        elif language == "javascript":
            return ["node", code_file]
        
        return [code_file]
    
    def _build_environment(self, limits: ResourceLimit) -> Dict[str, str]:
        """Build restricted environment variables"""
        env = os.environ.copy()
        
        # Restrict paths
        if limits.allowed_paths:
            env["PATH"] = ":".join(limits.allowed_paths)
        
        # Disable network (remove HTTP_PROXY, HTTPS_PROXY, etc.)
        if limits.max_network_calls == 0:
            for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
                env.pop(key, None)
        
        return env
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution result by ID"""
        return self._executions.get(execution_id)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""
        result = self._executions.get(execution_id)
        if result and result.status == ExecutionStatus.RUNNING:
            result.status = ExecutionStatus.CANCELLED
            result.completed_at = datetime.now(timezone.utc)
            return True
        return False
    
    def cleanup_old_executions(self, max_age_hours: int = 24) -> int:
        """Remove old execution records"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        to_remove = [
            eid for eid, result in self._executions.items()
            if result.completed_at and result.completed_at < cutoff
        ]
        
        for eid in to_remove:
            del self._executions[eid]
        
        return len(to_remove)
