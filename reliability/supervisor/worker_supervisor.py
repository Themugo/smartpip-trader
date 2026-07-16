"""
Worker Supervisor
================

Supervises worker processes and manages their lifecycle.
"""

import asyncio
import logging
import time
import psutil
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """Worker status levels"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class WorkerConfig:
    """Configuration for a worker"""
    name: str
    max_retries: int = 3
    restart_delay: float = 5.0
    shutdown_timeout: float = 30.0
    health_check_interval: float = 10.0
    max_memory_mb: float = 512.0
    max_cpu_percent: float = 80.0


@dataclass
class WorkerProcess:
    """A supervised worker process"""
    name: str
    pid: int
    config: WorkerConfig
    status: WorkerStatus
    started_at: float
    restart_count: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    mean_task_duration_ms: float = 0.0
    last_task_at: Optional[float] = None
    last_restart_at: Optional[float] = None
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    is_healthy: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "pid": self.pid,
            "status": self.status.value,
            "started_at": self.started_at,
            "restart_count": self.restart_count,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "mean_task_duration_ms": self.mean_task_duration_ms,
            "last_task_at": self.last_task_at,
            "last_restart_at": self.last_restart_at,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "is_healthy": self.is_healthy,
            "uptime_seconds": time.time() - self.started_at
        }


@dataclass
class WorkerStats:
    """Statistics for worker management"""
    total_workers: int = 0
    running_workers: int = 0
    failed_workers: int = 0
    total_restarts: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class WorkerSupervisor:
    """
    Supervises worker processes with auto-restart and health monitoring.
    
    Features:
    - Worker lifecycle management
    - Auto-restart on failure
    - Resource monitoring
    - Task tracking
    - Graceful shutdown
    """
    
    def __init__(self, supervisor_name: str):
        self.supervisor_name = supervisor_name
        self._workers: Dict[str, WorkerProcess] = {}
        self._configs: Dict[str, WorkerConfig] = {}
        self._worker_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._lock = asyncio.Lock()
        
        self._start_callbacks: Dict[str, Callable] = {}
        self._stop_callbacks: Dict[str, Callable] = {}
        self._failure_callbacks: List[Callable] = []
        
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info(f"Worker Supervisor '{supervisor_name}' initialized")
    
    def register_worker(
        self,
        name: str,
        start_handler: Callable,
        config: Optional[WorkerConfig] = None,
        stop_handler: Optional[Callable] = None
    ) -> None:
        """
        Register a worker with the supervisor.
        
        Args:
            name: Worker name
            start_handler: Async function that starts the worker
            config: Worker configuration
            stop_handler: Async function that stops the worker
        """
        if config is None:
            config = WorkerConfig(name=name)
        
        self._configs[name] = config
        self._start_callbacks[name] = start_handler
        
        if stop_handler:
            self._stop_callbacks[name] = stop_handler
        
        logger.info(f"Registered worker: {name}")
    
    def register_failure_callback(
        self,
        callback: Callable[[str, Exception], None]
    ) -> None:
        """Register a callback for worker failures"""
        self._failure_callbacks.append(callback)
    
    async def start_worker(self, name: str) -> bool:
        """
        Start a worker.
        
        Args:
            name: Worker name
            
        Returns:
            True if worker started successfully
        """
        async with self._lock:
            if name not in self._configs:
                logger.error(f"Worker {name} not registered")
                return False
            
            if name in self._workers:
                worker = self._workers[name]
                if worker.status == WorkerStatus.RUNNING:
                    logger.warning(f"Worker {name} already running")
                    return True
            
            config = self._configs[name]
            
            # Create worker process entry
            worker = WorkerProcess(
                name=name,
                pid=os.getpid(),
                config=config,
                status=WorkerStatus.STARTING,
                started_at=time.time()
            )
            self._workers[name] = worker
            
            try:
                # Execute start handler
                start_handler = self._start_callbacks.get(name)
                if start_handler:
                    if asyncio.iscoroutinefunction(start_handler):
                        await start_handler()
                    else:
                        start_handler()
                
                worker.status = WorkerStatus.RUNNING
                logger.info(f"Worker {name} started successfully")
                
                return True
                
            except Exception as e:
                worker.status = WorkerStatus.FAILED
                logger.error(f"Failed to start worker {name}: {e}")
                
                # Execute failure callbacks
                for callback in self._failure_callbacks:
                    try:
                        callback(name, e)
                    except Exception as cb_error:
                        logger.error(f"Failure callback error: {cb_error}")
                
                return False
    
    async def stop_worker(self, name: str, force: bool = False) -> bool:
        """
        Stop a worker.
        
        Args:
            name: Worker name
            force: Force stop without graceful shutdown
            
        Returns:
            True if worker stopped successfully
        """
        async with self._lock:
            if name not in self._workers:
                logger.warning(f"Worker {name} not found")
                return False
            
            worker = self._workers[name]
            config = self._configs[name]
            
            worker.status = WorkerStatus.STOPPING
            
            try:
                # Execute stop handler
                stop_handler = self._stop_callbacks.get(name)
                if stop_handler:
                    if asyncio.iscoroutinefunction(stop_handler):
                        await asyncio.wait_for(
                            stop_handler(),
                            timeout=config.shutdown_timeout if not force else 1.0
                        )
                    else:
                        stop_handler()
                else:
                    # Default: just wait
                    await asyncio.sleep(0.1)
                
                worker.status = WorkerStatus.STOPPED
                logger.info(f"Worker {name} stopped")
                
                return True
                
            except asyncio.TimeoutError:
                logger.warning(f"Worker {name} stop timed out, force killing")
                worker.status = WorkerStatus.FAILED
                return False
                
            except Exception as e:
                logger.error(f"Error stopping worker {name}: {e}")
                worker.status = WorkerStatus.FAILED
                return False
    
    async def restart_worker(self, name: str) -> bool:
        """
        Restart a worker.
        
        Args:
            name: Worker name
            
        Returns:
            True if worker restarted successfully
        """
        async with self._lock:
            if name not in self._workers:
                logger.error(f"Worker {name} not registered")
                return False
            
            config = self._configs[name]
            worker = self._workers[name]
            
            # Check if restart is allowed
            if worker.restart_count >= config.max_retries:
                logger.error(
                    f"Worker {name} exceeded max retries ({config.max_retries})"
                )
                worker.status = WorkerStatus.FAILED
                return False
            
            worker.status = WorkerStatus.RESTARTING
            worker.restart_count += 1
            worker.last_restart_at = time.time()
            
            logger.info(f"Restarting worker {name} (attempt {worker.restart_count})")
            
            # Stop worker
            await self.stop_worker(name, force=True)
            
            # Wait for restart delay
            await asyncio.sleep(config.restart_delay)
            
            # Start worker
            return await self.start_worker(name)
    
    async def record_task(
        self,
        name: str,
        duration_ms: float,
        success: bool
    ) -> None:
        """
        Record task execution for a worker.
        
        Args:
            name: Worker name
            duration_ms: Task duration in milliseconds
            success: Whether task succeeded
        """
        async with self._lock:
            if name not in self._workers:
                return
            
            worker = self._workers[name]
            worker.total_tasks += 1
            worker.last_task_at = time.time()
            
            if success:
                worker.completed_tasks += 1
            else:
                worker.failed_tasks += 1
            
            # Update mean duration
            alpha = 0.1
            worker.mean_task_duration_ms = (
                alpha * duration_ms +
                (1 - alpha) * worker.mean_task_duration_ms
            )
    
    async def _monitor_loop(self) -> None:
        """Monitor worker health"""
        while self._running:
            try:
                async with self._lock:
                    for name, worker in self._workers.items():
                        if worker.status != WorkerStatus.RUNNING:
                            continue
                        
                        config = self._configs[name]
                        
                        # Update resource metrics
                        try:
                            process = psutil.Process(worker.pid)
                            worker.memory_mb = (
                                process.memory_info().rss / 1024 / 1024
                            )
                            worker.cpu_percent = process.cpu_percent()
                            
                            # Check health
                            if worker.memory_mb > config.max_memory_mb:
                                logger.warning(
                                    f"Worker {name} exceeded memory limit: "
                                    f"{worker.memory_mb:.1f}MB > {config.max_memory_mb}MB"
                                )
                                worker.is_healthy = False
                            
                            elif worker.cpu_percent > config.max_cpu_percent:
                                logger.warning(
                                    f"Worker {name} exceeded CPU limit: "
                                    f"{worker.cpu_percent:.1f}% > {config.max_cpu_percent}%"
                                )
                                worker.is_healthy = False
                            
                            else:
                                worker.is_healthy = True
                                
                        except psutil.NoSuchProcess:
                            # Process died
                            logger.error(f"Worker {name} process died")
                            await self.restart_worker(name)
                
                await asyncio.sleep(5.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def start(self) -> None:
        """Start the supervisor"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Worker Supervisor '{self.supervisor_name}' started")
    
    async def stop(self) -> None:
        """Stop all workers and the supervisor"""
        self._running = False
        
        # Stop all workers
        for name in list(self._workers.keys()):
            await self.stop_worker(name)
        
        # Stop monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Worker Supervisor '{self.supervisor_name}' stopped")
    
    def get_worker(self, name: str) -> Optional[WorkerProcess]:
        """Get worker information"""
        return self._workers.get(name)
    
    def get_all_workers(self) -> Dict[str, Dict[str, Any]]:
        """Get all workers"""
        return {
            name: worker.to_dict()
            for name, worker in self._workers.items()
        }
    
    def get_stats(self) -> WorkerStats:
        """Get supervisor statistics"""
        return WorkerStats(
            total_workers=len(self._workers),
            running_workers=sum(
                1 for w in self._workers.values()
                if w.status == WorkerStatus.RUNNING
            ),
            failed_workers=sum(
                1 for w in self._workers.values()
                if w.status == WorkerStatus.FAILED
            ),
            total_restarts=sum(
                w.restart_count for w in self._workers.values()
            ),
            total_tasks=sum(
                w.total_tasks for w in self._workers.values()
            ),
            completed_tasks=sum(
                w.completed_tasks for w in self._workers.values()
            ),
            failed_tasks=sum(
                w.failed_tasks for w in self._workers.values()
            ),
        )
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        stats = self.get_stats()
        
        return {
            "supervisor_name": self.supervisor_name,
            "stats": {
                "total_workers": stats.total_workers,
                "running_workers": stats.running_workers,
                "failed_workers": stats.failed_workers,
                "total_restarts": stats.total_restarts,
                "total_tasks": stats.total_tasks,
                "completed_tasks": stats.completed_tasks,
                "failed_tasks": stats.failed_tasks,
                "success_rate": round(
                    stats.completed_tasks / max(1, stats.total_tasks) * 100,
                    2
                ) if stats.total_tasks > 0 else 100.0
            },
            "workers": {
                name: worker.to_dict()
                for name, worker in self._workers.items()
            }
        }
