"""
Lifecycle Manager

Manages application lifecycle phases and startup/shutdown hooks.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)


class LifecyclePhase(Enum):
    """Application lifecycle phases"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class LifecycleHook:
    """Lifecycle hook definition"""
    phase: LifecyclePhase
    name: str
    func: Callable
    order: int = 0
    timeout_seconds: float = 30
    required: bool = True
    _ran: bool = False
    _failed: bool = False


class LifecycleManager:
    """
    Manages application lifecycle.
    
    Features:
    - Phase tracking
    - Pre-startup hooks
    - Post-startup hooks
    - Pre-shutdown hooks
    - Error handling
    """
    
    def __init__(self):
        self._phase = LifecyclePhase.INITIALIZING
        self._hooks: Dict[LifecyclePhase, List[LifecycleHook]] = {
            phase: [] for phase in LifecyclePhase
        }
        self._start_time: datetime = None
        self._error: Exception = None
    
    @property
    def phase(self) -> LifecyclePhase:
        return self._phase
    
    @property
    def is_running(self) -> bool:
        return self._phase == LifecyclePhase.RUNNING
    
    @property
    def uptime(self) -> float:
        if self._start_time:
            return (datetime.now(timezone.utc) - self._start_time).total_seconds()
        return 0
    
    def add_hook(
        self,
        phase: LifecyclePhase,
        name: str,
        func: Callable,
        order: int = 0,
        timeout: float = 30,
        required: bool = True,
    ) -> LifecycleHook:
        """Add a lifecycle hook"""
        hook = LifecycleHook(
            phase=phase,
            name=name,
            func=func,
            order=order,
            timeout_seconds=timeout,
            required=required,
        )
        self._hooks[phase].append(hook)
        self._hooks[phase].sort(key=lambda h: h.order)
        return hook
    
    def remove_hook(self, name: str) -> bool:
        """Remove a hook by name"""
        for hooks in self._hooks.values():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    del hooks[i]
                    return True
        return False
    
    async def transition_to(self, target_phase: LifecyclePhase) -> bool:
        """Transition to a new phase"""
        logger.info(f"Transitioning from {self._phase.value} to {target_phase.value}")
        
        try:
            # Run exit hooks for current phase
            if self._phase != target_phase:
                exit_hooks = self._get_exit_hooks(self._phase)
                await self._run_hooks(exit_hooks)
            
            # Run entry hooks for new phase
            entry_hooks = self._get_entry_hooks(target_phase)
            await self._run_hooks(entry_hooks)
            
            self._phase = target_phase
            
            if target_phase == LifecyclePhase.RUNNING:
                self._start_time = datetime.now(timezone.utc)
            
            logger.info(f"Transitioned to {target_phase.value}")
            return True
            
        except Exception as e:
            self._error = e
            self._phase = LifecyclePhase.ERROR
            logger.error(f"Transition failed: {e}")
            return False
    
    def _get_entry_hooks(self, phase: LifecyclePhase) -> List[LifecycleHook]:
        """Get entry hooks for a phase"""
        return self._hooks.get(phase, [])
    
    def _get_exit_hooks(self, phase: LifecyclePhase) -> List[LifecycleHook]:
        """Get exit hooks for a phase"""
        # Exit hooks would be defined here if needed
        return []
    
    async def _run_hooks(self, hooks: List[LifecycleHook]) -> bool:
        """Run a list of hooks"""
        for hook in hooks:
            try:
                logger.debug(f"Running hook: {hook.name}")
                result = hook.func()
                
                # Handle async functions
                if hasattr(result, '__await__'):
                    await result
                
                hook._ran = True
                
            except Exception as e:
                hook._failed = True
                logger.error(f"Hook {hook.name} failed: {e}")
                
                if hook.required:
                    raise
        
        return True
    
    def get_status(self) -> dict:
        """Get lifecycle status"""
        return {
            "phase": self._phase.value,
            "is_running": self.is_running,
            "uptime_seconds": self.uptime,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "error": str(self._error) if self._error else None,
            "hooks_summary": {
                phase.value: len(hooks)
                for phase, hooks in self._hooks.items()
            },
        }
