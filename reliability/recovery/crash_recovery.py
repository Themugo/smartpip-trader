"""
Crash Recovery Manager
=====================

Handles crash detection, reporting, and automatic recovery.
"""

import asyncio
import logging
import time
import traceback
import json
import psutil
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque
from pathlib import Path

logger = logging.getLogger(__name__)


class CrashSeverity(Enum):
    """Severity levels for crashes"""
    FATAL = "fatal"           # Process crashed completely
    CRITICAL = "critical"     # Critical component failed
    ERROR = "error"           # Non-critical error
    WARNING = "warning"       # Warning condition


@dataclass
class CrashReport:
    """Detailed crash report"""
    id: str
    timestamp: float
    severity: CrashSeverity
    service_name: str
    process_id: int
    
    # Crash details
    error_type: str
    error_message: str
    stack_trace: str
    
    # Process state
    memory_mb: float
    cpu_percent: float
    num_threads: int
    num_open_files: int
    
    # Context
    request_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    environment: Optional[Dict[str, str]] = None
    
    # Recovery
    recovery_attempted: bool = False
    recovery_success: bool = False
    recovery_duration_ms: float = 0.0
    
    # Metadata
    occurred_during_startup: bool = False
    first_occurrence: bool = True
    occurrence_count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "service_name": self.service_name,
            "process_id": self.process_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "num_threads": self.num_threads,
            "num_open_files": self.num_open_files,
            "request_id": self.request_id,
            "user_context": self.user_context,
            "environment": self.environment,
            "recovery_attempted": self.recovery_attempted,
            "recovery_success": self.recovery_success,
            "recovery_duration_ms": self.recovery_duration_ms,
            "occurred_during_startup": self.occurred_during_startup,
            "first_occurrence": self.first_occurrence,
            "occurrence_count": self.occurrence_count,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class CrashStats:
    """Statistics for crash tracking"""
    total_crashes: int = 0
    fatal_crashes: int = 0
    critical_crashes: int = 0
    error_crashes: int = 0
    warning_crashes: int = 0
    recovered_crashes: int = 0
    mean_recovery_time_ms: float = 0.0
    last_crash_time: Optional[float] = None
    last_crash_type: Optional[str] = None
    crashes_in_last_hour: int = 0
    crashes_in_last_day: int = 0
    uptime_seconds: float = 0.0


class CrashRecoveryManager:
    """
    Manages crash detection and recovery.
    
    Features:
    - Automatic crash detection
    - Detailed crash reporting
    - Stack trace collection
    - Process state snapshot
    - Recovery actions
    - Crash deduplication
    - Persistent crash logs
    """
    
    def __init__(
        self,
        service_name: str,
        storage_path: Optional[str] = None
    ):
        self.service_name = service_name
        self.storage_path = Path(storage_path) if storage_path else Path(f".crashes_{service_name}")
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._crashes: Dict[str, CrashReport] = {}
        self._crash_counts: Dict[str, int] = {}  # For deduplication
        self._stats = CrashStats()
        self._start_time = time.time()
        
        self._recovery_handlers: List[Callable[[CrashReport], Any]] = []
        self._callbacks: Dict[CrashSeverity, List[Callable]] = {
            severity: [] for severity in CrashSeverity
        }
        
        self._lock = asyncio.Lock()
        self._running = False
        
        # Load previous crashes
        self._load_crashes()
    
    def _load_crashes(self) -> None:
        """Load crashes from storage"""
        try:
            for crash_file in self.storage_path.glob("*.json"):
                try:
                    with open(crash_file) as f:
                        data = json.load(f)
                    
                    crash = CrashReport(
                        id=data["id"],
                        timestamp=data["timestamp"],
                        severity=CrashSeverity(data["severity"]),
                        service_name=data["service_name"],
                        process_id=data["process_id"],
                        error_type=data["error_type"],
                        error_message=data["error_message"],
                        stack_trace=data["stack_trace"],
                        memory_mb=data.get("memory_mb", 0),
                        cpu_percent=data.get("cpu_percent", 0),
                        num_threads=data.get("num_threads", 0),
                        num_open_files=data.get("num_open_files", 0),
                        request_id=data.get("request_id"),
                        user_context=data.get("user_context"),
                        environment=data.get("environment"),
                        recovery_attempted=data.get("recovery_attempted", False),
                        recovery_success=data.get("recovery_success", False),
                        recovery_duration_ms=data.get("recovery_duration_ms", 0),
                        occurred_during_startup=data.get("occurred_during_startup", False),
                        first_occurrence=data.get("first_occurrence", True),
                        occurrence_count=data.get("occurrence_count", 1),
                    )
                    
                    self._crashes[crash.id] = crash
                    
                    # Update counts
                    key = f"{crash.error_type}:{crash.error_message[:100]}"
                    self._crash_counts[key] = crash.occurrence_count
                    
                except Exception as e:
                    logger.error(f"Failed to load crash {crash_file}: {e}")
            
            logger.info(f"Loaded {len(self._crashes)} previous crashes")
            
        except Exception as e:
            logger.error(f"Failed to load crashes: {e}")
    
    def _save_crash(self, crash: CrashReport) -> None:
        """Persist crash report to storage"""
        try:
            crash_file = self.storage_path / f"{crash.id}.json"
            with open(crash_file, 'w') as f:
                f.write(crash.to_json())
        except Exception as e:
            logger.error(f"Failed to save crash: {e}")
    
    def register_recovery_handler(
        self,
        handler: Callable[[CrashReport], Any]
    ) -> None:
        """Register a handler for crash recovery"""
        self._recovery_handlers.append(handler)
    
    def register_callback(
        self,
        severity: CrashSeverity,
        callback: Callable[[CrashReport], None]
    ) -> None:
        """Register a callback for specific severity"""
        self._callbacks[severity].append(callback)
    
    def _collect_process_state(self) -> Dict[str, Any]:
        """Collect current process state"""
        try:
            process = psutil.Process(os.getpid())
            
            return {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "num_open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
                "environment": dict(os.environ),
            }
        except Exception as e:
            logger.error(f"Failed to collect process state: {e}")
            return {}
    
    def _determine_severity(
        self,
        error_type: str,
        error_message: str
    ) -> CrashSeverity:
        """Determine crash severity based on error type"""
        fatal_patterns = [
            "SystemExit",
            "KeyboardInterrupt",
            "MemoryError",
            "SystemError",
        ]
        
        critical_patterns = [
            "ConnectionError",
            "TimeoutError",
            "OSError",
            "IOError",
        ]
        
        for pattern in fatal_patterns:
            if pattern in error_type:
                return CrashSeverity.FATAL
        
        for pattern in critical_patterns:
            if pattern in error_type or pattern in error_message:
                return CrashSeverity.CRITICAL
        
        return CrashSeverity.ERROR
    
    def _generate_crash_id(self) -> str:
        """Generate unique crash ID"""
        import uuid
        return f"crash_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    def _is_duplicate(
        self,
        error_type: str,
        error_message: str
    ) -> tuple[bool, int]:
        """Check if this is a duplicate crash"""
        key = f"{error_type}:{error_message[:100]}"
        
        if key in self._crash_counts:
            self._crash_counts[key] += 1
            return True, self._crash_counts[key]
        
        self._crash_counts[key] = 1
        return False, 1
    
    async def capture_crash(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> CrashReport:
        """
        Capture a crash and generate report.
        
        Args:
            error: The exception that caused the crash
            context: Additional context
            
        Returns:
            Generated CrashReport
        """
        async with self._lock:
            # Generate crash report
            crash_id = self._generate_crash_id()
            error_type = type(error).__name__
            error_message = str(error)
            
            # Get stack trace
            stack_trace = traceback.format_exc()
            
            # Determine severity
            severity = self._determine_severity(error_type, error_message)
            
            # Check for duplicates
            is_duplicate, occurrence_count = self._is_duplicate(
                error_type, error_message
            )
            
            # Collect process state
            process_state = self._collect_process_state()
            
            # Determine if during startup (first 30 seconds)
            startup_time = time.time() - self._start_time
            during_startup = startup_time < 30.0
            
            # Create crash report
            crash = CrashReport(
                id=crash_id,
                timestamp=time.time(),
                severity=severity,
                service_name=self.service_name,
                process_id=os.getpid(),
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                memory_mb=process_state.get("memory_mb", 0),
                cpu_percent=process_state.get("cpu_percent", 0),
                num_threads=process_state.get("num_threads", 0),
                num_open_files=process_state.get("num_open_files", 0),
                request_id=context.get("request_id") if context else None,
                user_context=context.get("user_context") if context else None,
                environment=process_state.get("environment"),
                occurred_during_startup=during_startup,
                first_occurrence=not is_duplicate,
                occurrence_count=occurrence_count,
            )
            
            # Store crash
            self._crashes[crash_id] = crash
            self._save_crash(crash)
            
            # Update stats
            self._update_stats(crash)
            
            # Log crash
            logger.critical(
                f"CRASH [{severity.value.upper()}] {crash_id}: "
                f"{error_type}: {error_message[:200]}"
            )
            
            # Execute callbacks
            for callback in self._callbacks.get(severity, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(crash)
                    else:
                        callback(crash)
                except Exception as e:
                    logger.error(f"Crash callback failed: {e}")
            
            return crash
    
    async def recover(self, crash: CrashReport) -> bool:
        """
        Attempt to recover from a crash.
        
        Args:
            crash: The crash to recover from
            
        Returns:
            True if recovery was successful
        """
        start_time = time.time()
        
        crash.recovery_attempted = True
        
        try:
            # Execute recovery handlers
            for handler in self._recovery_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(crash)
                    else:
                        result = handler(crash)
                    
                    if result is False:  # Handler refused recovery
                        continue
                        
                except Exception as e:
                    logger.error(f"Recovery handler failed: {e}")
            
            # Recovery successful
            crash.recovery_success = True
            crash.recovery_duration_ms = (time.time() - start_time) * 1000
            
            self._stats.recovered_crashes += 1
            self._save_crash(crash)
            
            logger.info(
                f"Recovery successful for crash {crash.id} "
                f"({crash.recovery_duration_ms:.0f}ms)"
            )
            
            return True
            
        except Exception as e:
            crash.recovery_duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Recovery failed for crash {crash.id}: {e}")
            return False
    
    def _update_stats(self, crash: CrashReport) -> None:
        """Update crash statistics"""
        self._stats.total_crashes += 1
        self._stats.last_crash_time = crash.timestamp
        self._stats.last_crash_type = crash.error_type
        
        # Count by severity
        if crash.severity == CrashSeverity.FATAL:
            self._stats.fatal_crashes += 1
        elif crash.severity == CrashSeverity.CRITICAL:
            self._stats.critical_crashes += 1
        elif crash.severity == CrashSeverity.ERROR:
            self._stats.error_crashes += 1
        else:
            self._stats.warning_crashes += 1
        
        # Count by time window
        current_time = time.time()
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        self._stats.crashes_in_last_hour = sum(
            1 for c in self._crashes.values()
            if c.timestamp >= hour_ago
        )
        self._stats.crashes_in_last_day = sum(
            1 for c in self._crashes.values()
            if c.timestamp >= day_ago
        )
        
        self._stats.uptime_seconds = current_time - self._start_time
    
    def get_crash(self, crash_id: str) -> Optional[CrashReport]:
        """Get a specific crash by ID"""
        return self._crashes.get(crash_id)
    
    def get_crashes(
        self,
        limit: Optional[int] = None,
        severity: Optional[CrashSeverity] = None
    ) -> List[CrashReport]:
        """Get crashes, optionally filtered"""
        crashes = list(self._crashes.values())
        
        if severity:
            crashes = [c for c in crashes if c.severity == severity]
        
        # Sort by timestamp descending
        crashes.sort(key=lambda c: c.timestamp, reverse=True)
        
        if limit:
            crashes = crashes[:limit]
        
        return crashes
    
    def get_stats(self) -> CrashStats:
        """Get crash statistics"""
        return self._stats
    
    def clear_crashes(self, before: Optional[float] = None) -> int:
        """Clear old crashes from storage"""
        count = 0
        
        if before is None:
            before = time.time() - 86400 * 7  # Default: 7 days
        
        to_remove = [
            crash_id for crash_id, crash in self._crashes.items()
            if crash.timestamp < before
        ]
        
        for crash_id in to_remove:
            crash_file = self.storage_path / f"{crash_id}.json"
            if crash_file.exists():
                crash_file.unlink()
            del self._crashes[crash_id]
            count += 1
        
        logger.info(f"Cleared {count} old crashes")
        return count
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            "service_name": self.service_name,
            "stats": {
                "total_crashes": self._stats.total_crashes,
                "fatal_crashes": self._stats.fatal_crashes,
                "critical_crashes": self._stats.critical_crashes,
                "error_crashes": self._stats.error_crashes,
                "recovered_crashes": self._stats.recovered_crashes,
                "mean_recovery_time_ms": round(self._stats.mean_recovery_time_ms, 2),
                "last_crash_time": self._stats.last_crash_time,
                "last_crash_type": self._stats.last_crash_type,
                "crashes_in_last_hour": self._stats.crashes_in_last_hour,
                "crashes_in_last_day": self._stats.crashes_in_last_day,
                "uptime_seconds": round(time.time() - self._start_time, 2),
            },
            "crash_rate": {
                "per_hour": round(self._stats.crashes_in_last_hour / max(1, (time.time() - self._start_time) / 3600), 2),
                "per_day": round(self._stats.crashes_in_last_day, 2),
            },
            "recent_crashes": [
                {
                    "id": c.id,
                    "timestamp": c.timestamp,
                    "severity": c.severity.value,
                    "error_type": c.error_type,
                    "error_message": c.error_message[:100],
                    "recovered": c.recovery_success,
                }
                for c in list(self._crashes.values())[-5:]
            ]
        }
