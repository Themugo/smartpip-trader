"""
Task Scheduler

Background task scheduling with cron-like expressions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Schedule types"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    task_id: str
    name: str
    func: Callable
    schedule_type: ScheduleType
    
    # For interval schedules
    interval_seconds: float = 0
    
    # For cron schedules
    cron_expression: str = ""
    
    # Timing
    next_run: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    
    # Status
    enabled: bool = True
    max_runs: int = 0  # 0 = infinite
    
    # Metadata
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


class TaskScheduler:
    """
    Task scheduler for background jobs.
    
    Features:
    - One-time tasks
    - Interval-based tasks
    - Cron expression support
    - Task cancellation
    - Error handling
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def schedule_interval(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval_seconds: float,
        enabled: bool = True,
    ) -> ScheduledTask:
        """Schedule a task to run at intervals"""
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
            next_run=datetime.utcnow(),
            enabled=enabled,
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        return task
    
    def schedule_once(
        self,
        task_id: str,
        name: str,
        func: Callable,
        run_at: datetime,
        enabled: bool = True,
    ) -> ScheduledTask:
        """Schedule a one-time task"""
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            schedule_type=ScheduleType.ONCE,
            next_run=run_at,
            enabled=enabled,
            max_runs=1,
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        return task
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks"""
        return list(self._tasks.values())
    
    def start(self):
        """Start the scheduler"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Task scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop"""
        while self._running:
            now = datetime.utcnow()
            
            with self._lock:
                tasks_to_run = [
                    task for task in self._tasks.values()
                    if task.enabled and task.next_run <= now
                ]
            
            for task in tasks_to_run:
                self._execute_task(task)
            
            # Sleep for 1 second
            threading.Event().wait(1)
    
    def _execute_task(self, task: ScheduledTask):
        """Execute a task"""
        try:
            task.func()
            task.last_run = datetime.utcnow()
            task.run_count += 1
            
            # Schedule next run for interval tasks
            if task.schedule_type == ScheduleType.INTERVAL:
                task.next_run = datetime.utcnow() + timedelta(seconds=task.interval_seconds)
            
            # Check if task should be disabled
            if task.max_runs > 0 and task.run_count >= task.max_runs:
                task.enabled = False
            
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            logger.error(f"Task {task.name} failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "running": self._running,
        }


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
