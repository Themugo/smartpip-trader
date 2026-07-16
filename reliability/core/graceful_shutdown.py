"""
Graceful Shutdown Handler
=========================

Ensures clean shutdown of services with proper cleanup.
"""

import asyncio
import signal
import logging
import time
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any
from enum import Enum
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """Shutdown phases in order"""
    SIGTERM_RECEIVED = "sigterm_received"
    STOP_ACCEPTING = "stop_accepting"
    DRAIN_CONNECTIONS = "drain_connections"
    FLUSH_BUFFERS = "flush_buffers"
    SAVE_STATE = "save_state"
    CLOSE_CONNECTIONS = "close_connections"
    NOTIFY_DEPENDENCIES = "notify_dependencies"
    COMPLETE = "complete"


@dataclass
class ShutdownTask:
    """A task to be executed during shutdown"""
    name: str
    handler: Callable[[], Any]
    timeout: float = 30.0
    critical: bool = True
    phase: ShutdownPhase = ShutdownPhase.CLOSE_CONNECTIONS
    description: str = ""


@dataclass
class ShutdownState:
    """Current state of shutdown process"""
    phase: ShutdownPhase = ShutdownPhase.SIGTERM_RECEIVED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    is_shutting_down: bool = False
    is_force_kill: bool = False


class GracefulShutdownHandler:
    """
    Handles graceful shutdown of the trading platform.
    
    Features:
    - Multi-phase shutdown with proper ordering
    - Task timeout enforcement
    - Force kill after grace period
    - Signal handling (SIGTERM, SIGINT)
    - State persistence
    - Cleanup callbacks
    """
    
    def __init__(
        self,
        service_name: str,
        shutdown_timeout: float = 60.0,
        force_kill_timeout: float = 30.0
    ):
        self.service_name = service_name
        self.shutdown_timeout = shutdown_timeout
        self.force_kill_timeout = force_kill_timeout
        
        self._tasks: Dict[ShutdownPhase, List[ShutdownTask]] = {
            phase: [] for phase in ShutdownPhase
        }
        self._state = ShutdownState()
        self._shutdown_event = asyncio.Event()
        self._force_kill_timer: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks for different phases
        self._phase_callbacks: Dict[ShutdownPhase, List[Callable]] = {
            phase: [] for phase in ShutdownPhase
        }
    
    def register_task(
        self,
        name: str,
        handler: Callable,
        timeout: float = 30.0,
        critical: bool = True,
        phase: ShutdownPhase = ShutdownPhase.CLOSE_CONNECTIONS,
        description: str = ""
    ) -> None:
        """
        Register a shutdown task.
        
        Args:
            name: Task name
            handler: Async or sync function to execute
            timeout: Maximum time for task execution
            critical: If True, force kill if task times out
            phase: When to execute this task
            description: Human-readable description
        """
        task = ShutdownTask(
            name=name,
            handler=handler,
            timeout=timeout,
            critical=critical,
            phase=phase,
            description=description or name
        )
        
        self._tasks[phase].append(task)
        logger.debug(f"Registered shutdown task: {name} (phase: {phase.value})")
    
    def register_callback(
        self,
        phase: ShutdownPhase,
        callback: Callable
    ) -> None:
        """Register a callback for a specific phase"""
        self._phase_callbacks[phase].append(callback)
    
    async def _execute_tasks(self, phase: ShutdownPhase) -> None:
        """Execute all tasks for a given phase"""
        logger.info(f"Executing shutdown phase: {phase.value}")
        
        # Execute phase callbacks
        for callback in self._phase_callbacks[phase]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Phase callback failed in {phase.value}: {e}")
        
        # Execute phase tasks
        tasks = self._tasks[phase]
        
        for task in tasks:
            start_time = time.time()
            
            try:
                logger.info(f"Shutting down: {task.name}")
                
                if asyncio.iscoroutinefunction(task.handler):
                    await asyncio.wait_for(task.handler(), timeout=task.timeout)
                else:
                    # Run sync tasks in thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: asyncio.run(asyncio.wait_for(
                            self._run_sync_task(task.handler),
                            timeout=task.timeout
                        )) if asyncio.iscoroutinefunction(task.handler) else task.handler()
                    )
                
                elapsed = time.time() - start_time
                self._state.tasks_completed += 1
                logger.info(f"Completed: {task.name} ({elapsed:.2f}s)")
                
            except asyncio.TimeoutError:
                self._state.tasks_failed += 1
                logger.error(
                    f"Task timed out: {task.name} ({task.timeout}s). "
                    f"Critical: {task.critical}"
                )
                
                if task.critical:
                    logger.warning(f"Critical task failed, will force kill")
                    self._state.is_force_kill = True
                    
            except Exception as e:
                self._state.tasks_failed += 1
                logger.error(f"Task failed: {task.name}: {e}")
    
    async def _run_sync_task(self, handler: Callable) -> Any:
        """Run a synchronous task"""
        return handler()
    
    async def _execute_shutdown_sequence(self) -> None:
        """Execute the full shutdown sequence"""
        self._state.is_shutting_down = True
        self._state.start_time = time.time()
        
        # Define shutdown phases in order
        phases = [
            ShutdownPhase.SIGTERM_RECEIVED,
            ShutdownPhase.STOP_ACCEPTING,
            ShutdownPhase.DRAIN_CONNECTIONS,
            ShutdownPhase.FLUSH_BUFFERS,
            ShutdownPhase.SAVE_STATE,
            ShutdownPhase.CLOSE_CONNECTIONS,
            ShutdownPhase.NOTIFY_DEPENDENCIES,
            ShutdownPhase.COMPLETE,
        ]
        
        try:
            for phase in phases:
                self._state.phase = phase
                
                # Start force kill timer if this is a critical phase
                if phase in [ShutdownPhase.CLOSE_CONNECTIONS, ShutdownPhase.NOTIFY_DEPENDENCIES]:
                    self._start_force_kill_timer()
                
                await self._execute_tasks(phase)
                
                # Check if force killed
                if self._state.is_force_kill:
                    logger.warning("Force kill triggered, terminating shutdown sequence")
                    break
                
                # Small delay between phases
                await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Shutdown sequence error: {e}")
            self._state.is_force_kill = True
        
        finally:
            self._state.end_time = time.time()
            self._shutdown_event.set()
    
    def _start_force_kill_timer(self) -> None:
        """Start timer for force kill"""
        if self._force_kill_timer:
            self._force_kill_timer.cancel()
        
        self._force_kill_timer = asyncio.create_task(
            self._force_kill_after(self.force_kill_timeout)
        )
    
    async def _force_kill_after(self, delay: float) -> None:
        """Force kill after delay"""
        await asyncio.sleep(delay)
        
        if self._state.is_shutting_down and not self._state.is_force_kill:
            logger.critical(f"Force killing after {delay}s grace period")
            self._state.is_force_kill = True
    
    def _handle_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        
        if not self._state.is_shutting_down:
            asyncio.create_task(self._execute_shutdown_sequence())
        
        elif not self._state.is_force_kill:
            logger.warning("Second signal received, will force kill")
            self._state.is_force_kill = True
    
    def setup_signal_handlers(self) -> None:
        """Setup SIGTERM and SIGINT handlers"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGABRT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: self._handle_signal(s, None)
                )
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, self._handle_signal)
        
        logger.info("Signal handlers registered")
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to complete"""
        await self._shutdown_event.wait()
    
    def get_state(self) -> ShutdownState:
        """Get current shutdown state"""
        return self._state
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self._state.is_shutting_down
    
    def get_shutdown_duration(self) -> float:
        """Get how long shutdown has taken"""
        if self._state.start_time:
            end = self._state.end_time or time.time()
            return end - self._state.start_time
        return 0.0
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        duration = self.get_shutdown_duration()
        
        return {
            "service_name": self.service_name,
            "is_shutting_down": self._state.is_shutting_down,
            "is_force_kill": self._state.is_force_kill,
            "current_phase": self._state.phase.value,
            "shutdown_duration_seconds": round(duration, 2),
            "tasks": {
                "completed": self._state.tasks_completed,
                "failed": self._state.tasks_failed,
                "skipped": self._state.tasks_skipped,
                "total": sum(len(tasks) for tasks in self._tasks.values())
            },
            "phases": {
                phase.value: len(self._tasks[phase])
                for phase in ShutdownPhase
            }
        }


@asynccontextmanager
async def graceful_shutdown_context(
    handler: GracefulShutdownHandler,
    **kwargs
):
    """
    Context manager for graceful shutdown.
    
    Usage:
        handler = GracefulShutdownHandler("my-service")
        async with graceful_shutdown_context(handler):
            # Run service
            ...
    """
    handler.setup_signal_handlers()
    
    # Start shutdown in background
    shutdown_task = asyncio.create_task(handler._execute_shutdown_sequence())
    
    try:
        yield handler
    finally:
        # Wait for shutdown with timeout
        try:
            await asyncio.wait_for(
                handler.wait_for_shutdown(),
                timeout=handler.shutdown_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout exceeded")
        
        # Cancel if still running
        if not shutdown_task.done():
            shutdown_task.cancel()
            try:
                await shutdown_task
            except asyncio.CancelledError:
                pass


class ShutdownManager:
    """
    Singleton manager for coordinated shutdown across modules.
    """
    
    _instance: Optional['ShutdownManager'] = None
    
    def __init__(self):
        self._handlers: Dict[str, GracefulShutdownHandler] = {}
        self._lock = asyncio.Lock()
    
    @classmethod
    def get_instance(cls) -> 'ShutdownManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def register_service(
        self,
        service_name: str,
        timeout: float = 30.0
    ) -> GracefulShutdownHandler:
        """Register a service for coordinated shutdown"""
        async with self._lock:
            if service_name in self._handlers:
                return self._handlers[service_name]
            
            handler = GracefulShutdownHandler(
                service_name,
                shutdown_timeout=timeout
            )
            self._handlers[service_name] = handler
            return handler
    
    async def shutdown_all(self) -> None:
        """Shutdown all registered services"""
        logger.info("Initiating shutdown of all services...")
        
        # Execute all handlers concurrently
        tasks = [
            handler._execute_shutdown_sequence()
            for handler in self._handlers.values()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All services shut down")
    
    def get_all_handlers(self) -> Dict[str, GracefulShutdownHandler]:
        """Get all registered handlers"""
        return self._handlers.copy()
