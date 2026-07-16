"""
Watchdog Process Implementation
===============================

Monitors process health and triggers recovery actions.
"""

import asyncio
import time
import logging
import psutil
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class WatchdogAction(Enum):
    """Actions watchdog can take"""
    RESTART = "restart"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NOTIFY = "notify"
    ISOLATE = "isolate"
    KILL = "kill"


@dataclass
class WatchdogConfig:
    """Configuration for watchdog monitoring"""
    check_interval: float = 5.0        # Check interval in seconds
    cpu_warning: float = 70.0          # CPU warning threshold %
    cpu_critical: float = 90.0        # CPU critical threshold %
    memory_warning: float = 70.0     # Memory warning threshold %
    memory_critical: float = 90.0    # Memory critical threshold %
    max_restarts: int = 5             # Max restarts per window
    restart_window: float = 300.0     # Restart tracking window (seconds)
    restart_cooldown: float = 60.0     # Cooldown between restarts


@dataclass
class WatchdogEvent:
    """An event detected by the watchdog"""
    timestamp: float
    event_type: str
    severity: str  # info, warning, critical
    service_name: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessSnapshot:
    """Snapshot of process state"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    num_threads: int
    num_fds: int
    status: str
    create_time: float
    num_children: int
    connections: int


class WatchdogProcess:
    """
    Watchdog process for monitoring and auto-recovery.
    
    Features:
    - Process health monitoring
    - Resource threshold detection
    - Automatic restart on failure
    - Restart rate limiting
    - Event history
    - Custom recovery actions
    """
    
    def __init__(
        self,
        service_name: str,
        config: Optional[WatchdogConfig] = None
    ):
        self.service_name = service_name
        self.config = config or WatchdogConfig()
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._process = psutil.Process(os.getpid())
        
        self._restarts: List[float] = []  # Timestamps of restarts
        self._events: List[WatchdogEvent] = []
        self._recovery_handlers: Dict[str, Callable] = {}
        
        self._callbacks: Dict[str, List[Callable]] = {
            "restart": [],
            "scale_up": [],
            "scale_down": [],
            "notify": [],
            "isolate": [],
            "kill": [],
        }
        
        self._lock = asyncio.Lock()
    
    def register_recovery_handler(
        self,
        action: WatchdogAction,
        handler: Callable[[WatchdogEvent], Any]
    ) -> None:
        """Register a handler for a recovery action"""
        action_name = action.value
        if action_name not in self._recovery_handlers:
            self._recovery_handlers[action_name] = []
        self._recovery_handlers[action_name].append(handler)
    
    def register_callback(
        self,
        event_type: str,
        callback: Callable[[WatchdogEvent], Any]
    ) -> None:
        """Register a callback for events"""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
    
    async def _collect_snapshot(self) -> ProcessSnapshot:
        """Collect current process snapshot"""
        try:
            with self._process.oneshot():
                children = self._process.children(recursive=True)
                
                return ProcessSnapshot(
                    pid=self._process.pid,
                    name=self._process.name(),
                    cpu_percent=self._process.cpu_percent(),
                    memory_percent=self._process.memory_percent(),
                    memory_mb=self._process.memory_info().rss / 1024 / 1024,
                    num_threads=self._process.num_threads(),
                    num_fds=len(self._process.open_files()) if hasattr(self._process, 'open_files') else 0,
                    status=self._process.status(),
                    create_time=self._process.create_time(),
                    num_children=len(children),
                    connections=len(self._process.connections())
                )
        except Exception as e:
            logger.error(f"Failed to collect process snapshot: {e}")
            raise
    
    async def _check_resource_thresholds(
        self,
        snapshot: ProcessSnapshot
    ) -> List[WatchdogEvent]:
        """Check if any resource thresholds are exceeded"""
        events = []
        current_time = time.time()
        
        # CPU checks
        if snapshot.cpu_percent >= self.config.cpu_critical:
            events.append(WatchdogEvent(
                timestamp=current_time,
                event_type="cpu_critical",
                severity="critical",
                service_name=self.service_name,
                message=f"CPU critical: {snapshot.cpu_percent:.1f}%",
                details={"cpu_percent": snapshot.cpu_percent}
            ))
        elif snapshot.cpu_percent >= self.config.cpu_warning:
            events.append(WatchdogEvent(
                timestamp=current_time,
                event_type="cpu_warning",
                severity="warning",
                service_name=self.service_name,
                message=f"CPU high: {snapshot.cpu_percent:.1f}%",
                details={"cpu_percent": snapshot.cpu_percent}
            ))
        
        # Memory checks
        if snapshot.memory_percent >= self.config.memory_critical:
            events.append(WatchdogEvent(
                timestamp=current_time,
                event_type="memory_critical",
                severity="critical",
                service_name=self.service_name,
                message=f"Memory critical: {snapshot.memory_percent:.1f}%",
                details={"memory_percent": snapshot.memory_percent, "memory_mb": snapshot.memory_mb}
            ))
        elif snapshot.memory_percent >= self.config.memory_warning:
            events.append(WatchdogEvent(
                timestamp=current_time,
                event_type="memory_warning",
                severity="warning",
                service_name=self.service_name,
                message=f"Memory high: {snapshot.memory_percent:.1f}%",
                details={"memory_percent": snapshot.memory_percent, "memory_mb": snapshot.memory_mb}
            ))
        
        # Check for memory leaks (growing memory over time)
        # This is a simplified check - in production, you'd track history
        
        return events
    
    def _should_restart(self) -> tuple[bool, str]:
        """
        Check if service should be restarted.
        
        Returns:
            (should_restart, reason)
        """
        current_time = time.time()
        
        # Clean old restarts outside window
        self._restarts = [
            t for t in self._restarts
            if current_time - t <= self.config.restart_window
        ]
        
        # Check restart count
        if len(self._restarts) >= self.config.max_restarts:
            return False, f"Max restarts ({self.config.max_restarts}) reached in {self.config.restart_window}s window"
        
        # Check cooldown
        if self._restarts and (current_time - self._restarts[-1]) < self.config.restart_cooldown:
            return False, f"Restart cooldown ({self.config.restart_cooldown}s) not elapsed"
        
        return True, "OK"
    
    def _record_restart(self) -> None:
        """Record a restart attempt"""
        self._restarts.append(time.time())
    
    async def _execute_recovery(
        self,
        event: WatchdogEvent
    ) -> bool:
        """Execute recovery action for an event"""
        action = event.event_type
        
        # Map event to action
        action_map = {
            "cpu_critical": WatchdogAction.SCALE_DOWN,
            "memory_critical": WatchdogAction.SCALE_DOWN,
            "restart_needed": WatchdogAction.RESTART,
            "process_dead": WatchdogAction.RESTART,
        }
        
        watchdog_action = action_map.get(action, WatchdogAction.NOTIFY)
        action_name = watchdog_action.value
        
        # Execute handlers
        handlers = self._recovery_handlers.get(action_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                
                if result is False:  # Handler refused
                    return False
            except Exception as e:
                logger.error(f"Recovery handler failed: {e}")
        
        return True
    
    async def _process_events(
        self,
        events: List[WatchdogEvent]
    ) -> None:
        """Process detected events"""
        for event in events:
            # Record event
            self._events.append(event)
            
            # Execute callbacks
            callbacks = self._callbacks.get(event.event_type, [])
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Event callback failed: {e}")
            
            # Execute recovery if critical
            if event.severity == "critical":
                success = await self._execute_recovery(event)
                if success:
                    logger.info(f"Recovery executed for {event.event_type}")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                # Collect snapshot
                snapshot = await self._collect_snapshot()
                
                # Check thresholds
                events = await self._check_resource_thresholds(snapshot)
                
                if events:
                    await self._process_events(events)
                
                await asyncio.sleep(self.config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog monitor error: {e}")
                await asyncio.sleep(self.config.check_interval)
    
    def get_current_snapshot(self) -> Optional[ProcessSnapshot]:
        """Get current process snapshot"""
        try:
            return asyncio.run(self._collect_snapshot())
        except Exception:
            return None
    
    def get_events(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[WatchdogEvent]:
        """Get watchdog events"""
        events = self._events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_restart_count(self) -> int:
        """Get restart count in current window"""
        current_time = time.time()
        return sum(
            1 for t in self._restarts
            if current_time - t <= self.config.restart_window
        )
    
    async def trigger_restart(self, reason: str) -> bool:
        """
        Manually trigger a restart.
        
        Returns:
            True if restart was allowed
        """
        should_restart, reason_code = self._should_restart()
        
        if not should_restart:
            logger.warning(f"Restart refused: {reason_code}")
            return False
        
        event = WatchdogEvent(
            timestamp=time.time(),
            event_type="manual_restart",
            severity="warning",
            service_name=self.service_name,
            message=f"Manual restart triggered: {reason}"
        )
        
        self._record_restart()
        await self._process_events([event])
        
        return True
    
    async def start(self) -> None:
        """Start the watchdog"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Watchdog started for {self.service_name}")
    
    async def stop(self) -> None:
        """Stop the watchdog"""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Watchdog stopped for {self.service_name}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        snapshot = self.get_current_snapshot()
        
        return {
            "service_name": self.service_name,
            "running": self._running,
            "snapshot": {
                "pid": snapshot.pid if snapshot else None,
                "cpu_percent": snapshot.cpu_percent if snapshot else 0,
                "memory_percent": snapshot.memory_percent if snapshot else 0,
                "memory_mb": snapshot.memory_mb if snapshot else 0,
                "num_threads": snapshot.num_threads if snapshot else 0,
                "num_children": snapshot.num_children if snapshot else 0,
            } if snapshot else None,
            "restart_stats": {
                "total_restarts": len(self._restarts),
                "restarts_in_window": self.get_restart_count(),
                "max_restarts": self.config.max_restarts,
                "window_seconds": self.config.restart_window,
            },
            "thresholds": {
                "cpu_warning": self.config.cpu_warning,
                "cpu_critical": self.config.cpu_critical,
                "memory_warning": self.config.memory_warning,
                "memory_critical": self.config.memory_critical,
            },
            "recent_events": [
                {
                    "timestamp": e.timestamp,
                    "type": e.event_type,
                    "severity": e.severity,
                    "message": e.message
                }
                for e in self._events[-10:]
            ]
        }


# Re-export other recovery modules
from .auto_recovery import AutoRecoveryManager, RecoveryStrategy
from .crash_recovery import CrashRecoveryManager, CrashReport
