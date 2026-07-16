"""
Auto Recovery Manager
=====================

Automatically recovers from failures with configurable strategies.
"""

import asyncio
import logging
import time
import psutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, TypeVar
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies"""
    RESTART = "restart"              # Restart the process
    RESTART_CHILDREN = "restart_children"  # Restart child processes
    CLEAR_CACHE = "clear_cache"      # Clear caches
    GC_COLLECT = "gc_collect"        # Force garbage collection
    RELEASE_MEMORY = "release_memory"  # Release unused memory
    RESTART_SERVICE = "restart_service"  # Restart entire service
    FAILOVER = "failover"           # Switch to backup
    NOTIFY = "notify"               # Just notify and escalate


@dataclass
class RecoveryAction:
    """A single recovery action"""
    name: str
    strategy: RecoveryStrategy
    handler: Optional[Callable] = None
    timeout: float = 30.0
    critical: bool = True
    cooldown: float = 60.0           # Minimum time between executions


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt"""
    timestamp: float
    strategy: RecoveryStrategy
    success: bool
    duration_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryStats:
    """Statistics for recovery operations"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    mean_recovery_time_ms: float = 0.0
    max_recovery_time_ms: float = 0.0
    last_attempt_time: Optional[float] = None
    last_attempt_strategy: Optional[str] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class AutoRecoveryManager:
    """
    Automatically recovers from failures.
    
    Features:
    - Multiple recovery strategies
    - Configurable triggers
    - Recovery action chains
    - Statistics tracking
    - Cooldown management
    - Rollback support
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        self._strategies: Dict[RecoveryStrategy, RecoveryAction] = {}
        self._strategy_chain: List[RecoveryStrategy] = []
        self._stats = RecoveryStats()
        self._history: deque = deque(maxlen=100)
        self._last_execution: Dict[RecoveryStrategy, float] = {}
        self._running = False
        self._lock = asyncio.Lock()
        
        self._triggers: Dict[str, Callable] = {}
        self._callbacks: Dict[RecoveryStrategy, List[Callable]] = {
            strategy: [] for strategy in RecoveryStrategy
        }
        
        # Setup default strategies
        self._setup_default_strategies()
    
    def _setup_default_strategies(self) -> None:
        """Setup default recovery strategies"""
        self.register_strategy(RecoveryStrategy.GC_COLLECT, "Garbage Collection", timeout=10.0)
        self.register_strategy(RecoveryStrategy.CLEAR_CACHE, "Clear Cache", timeout=15.0)
        self.register_strategy(RecoveryStrategy.RELEASE_MEMORY, "Release Memory", timeout=10.0)
        self.register_strategy(RecoveryStrategy.RESTART, "Process Restart", timeout=30.0, cooldown=120.0)
        
        # Default chain: gc -> cache -> memory -> restart
        self._strategy_chain = [
            RecoveryStrategy.GC_COLLECT,
            RecoveryStrategy.CLEAR_CACHE,
            RecoveryStrategy.RELEASE_MEMORY,
            RecoveryStrategy.RESTART,
        ]
    
    def register_strategy(
        self,
        strategy: RecoveryStrategy,
        name: str,
        handler: Optional[Callable] = None,
        timeout: float = 30.0,
        critical: bool = True,
        cooldown: float = 60.0
    ) -> None:
        """Register a recovery strategy"""
        action = RecoveryAction(
            name=name,
            strategy=strategy,
            handler=handler,
            timeout=timeout,
            critical=critical,
            cooldown=cooldown
        )
        self._strategies[strategy] = action
        logger.info(f"Registered recovery strategy: {name} ({strategy.value})")
    
    def register_callback(
        self,
        strategy: RecoveryStrategy,
        callback: Callable[[RecoveryAttempt], None]
    ) -> None:
        """Register a callback for strategy execution"""
        self._callbacks[strategy].append(callback)
    
    def register_trigger(
        self,
        name: str,
        condition: Callable[[], bool],
        strategy: Optional[RecoveryStrategy] = None
    ) -> None:
        """
        Register a trigger condition.
        
        Args:
            name: Trigger name
            condition: Function that returns True when trigger should fire
            strategy: Optional specific strategy to use (default: chain)
        """
        self._triggers[name] = condition
    
    def set_strategy_chain(self, chain: List[RecoveryStrategy]) -> None:
        """Set the recovery strategy chain"""
        self._strategy_chain = chain
        logger.info(f"Set recovery chain: {[s.value for s in chain]}")
    
    def _is_in_cooldown(self, strategy: RecoveryStrategy) -> bool:
        """Check if strategy is in cooldown"""
        if strategy not in self._last_execution:
            return False
        
        action = self._strategies.get(strategy)
        if not action:
            return False
        
        elapsed = time.time() - self._last_execution[strategy]
        return elapsed < action.cooldown
    
    async def _execute_strategy(
        self,
        strategy: RecoveryStrategy,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """Execute a single recovery strategy"""
        start_time = time.time()
        
        action = self._strategies.get(strategy)
        if not action:
            return RecoveryAttempt(
                timestamp=start_time,
                strategy=strategy,
                success=False,
                duration_ms=0,
                error=f"Unknown strategy: {strategy.value}"
            )
        
        try:
            logger.info(f"Executing recovery strategy: {action.name}")
            
            # Execute handler if provided
            if action.handler:
                if asyncio.iscoroutinefunction(action.handler):
                    await asyncio.wait_for(
                        action.handler(context),
                        timeout=action.timeout
                    )
                else:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: action.handler(context)
                        ),
                        timeout=action.timeout
                    )
            else:
                # Default handlers
                await self._execute_default_handler(strategy, context)
            
            duration_ms = (time.time() - start_time) * 1000
            self._last_execution[strategy] = time.time()
            
            attempt = RecoveryAttempt(
                timestamp=start_time,
                strategy=strategy,
                success=True,
                duration_ms=duration_ms,
                details=context
            )
            
            # Execute callbacks
            for callback in self._callbacks[strategy]:
                try:
                    callback(attempt)
                except Exception as e:
                    logger.error(f"Recovery callback failed: {e}")
            
            return attempt
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Recovery strategy {action.name} timed out")
            
            return RecoveryAttempt(
                timestamp=start_time,
                strategy=strategy,
                success=False,
                duration_ms=duration_ms,
                error=f"Timeout after {action.timeout}s"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Recovery strategy {action.name} failed: {e}")
            
            return RecoveryAttempt(
                timestamp=start_time,
                strategy=strategy,
                success=False,
                duration_ms=duration_ms,
                error=f"{type(e).__name__}: {e}"
            )
    
    async def _execute_default_handler(
        self,
        strategy: RecoveryStrategy,
        context: Dict[str, Any]
    ) -> None:
        """Execute default handler for a strategy"""
        if strategy == RecoveryStrategy.GC_COLLECT:
            import gc
            collected = gc.collect()
            logger.info(f"Garbage collection: {collected} objects collected")
            
        elif strategy == RecoveryStrategy.CLEAR_CACHE:
            # Clear various caches
            import sys
            modules_cleared = 0
            # Don't clear core modules
            for module in list(sys.modules.keys()):
                if not module.startswith(('_', 'sys', 'builtins')):
                    if hasattr(sys.modules[module], '__dict__'):
                        try:
                            del sys.modules[module]
                            modules_cleared += 1
                        except Exception:
                            pass
            logger.info(f"Cache cleared: {modules_cleared} modules")
            
        elif strategy == RecoveryStrategy.RELEASE_MEMORY:
            import gc
            gc.collect()
            # Force memory release
            if hasattr(psutil, 'Process'):
                process = psutil.Process()
                mem_before = process.memory_info().rss / 1024 / 1024
                # Trigger memory cleanup
                del context
                gc.collect()
                mem_after = process.memory_info().rss / 1024 / 1024
                logger.info(f"Memory released: {mem_before:.1f}MB -> {mem_after:.1f}MB")
            
        elif strategy == RecoveryStrategy.RESTART:
            # This should be overridden by a real restart handler
            logger.warning("Default restart handler called - should be overridden!")
            raise NotImplementedError("Default restart requires custom handler")
    
    async def recover(
        self,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        start_strategy: Optional[RecoveryStrategy] = None
    ) -> RecoveryAttempt:
        """
        Execute recovery process.
        
        Args:
            error: Error message that triggered recovery
            context: Additional context
            start_strategy: Strategy to start with (default: chain from beginning)
            
        Returns:
            RecoveryAttempt result
        """
        async with self._lock:
            context = context or {}
            if error:
                context["error"] = error
            
            # Find starting point in chain
            start_idx = 0
            if start_strategy:
                try:
                    start_idx = self._strategy_chain.index(start_strategy)
                except ValueError:
                    pass
            
            # Execute strategies in chain
            for strategy in self._strategy_chain[start_idx:]:
                # Skip if in cooldown
                if self._is_in_cooldown(strategy):
                    continue
                
                attempt = await self._execute_strategy(strategy, context)
                self._history.append(attempt)
                self._update_stats(attempt)
                
                if attempt.success:
                    logger.info(
                        f"Recovery successful with {strategy.value} "
                        f"({attempt.duration_ms:.0f}ms)"
                    )
                    return attempt
                else:
                    logger.warning(
                        f"Recovery strategy {strategy.value} failed, "
                        f"trying next..."
                    )
            
            # All strategies failed
            logger.error("All recovery strategies exhausted")
            return RecoveryAttempt(
                timestamp=time.time(),
                strategy=start_strategy or self._strategy_chain[0],
                success=False,
                duration_ms=0,
                error="All strategies failed"
            )
    
    def _update_stats(self, attempt: RecoveryAttempt) -> None:
        """Update recovery statistics"""
        self._stats.total_attempts += 1
        self._stats.last_attempt_time = attempt.timestamp
        self._stats.last_attempt_strategy = attempt.strategy.value
        
        if attempt.success:
            self._stats.successful_attempts += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
        else:
            self._stats.failed_attempts += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
        
        # Update mean recovery time
        alpha = 0.1
        self._stats.mean_recovery_time_ms = (
            alpha * attempt.duration_ms +
            (1 - alpha) * self._stats.mean_recovery_time_ms
        )
        
        self._stats.max_recovery_time_ms = max(
            self._stats.max_recovery_time_ms,
            attempt.duration_ms
        )
    
    def get_stats(self) -> RecoveryStats:
        """Get recovery statistics"""
        return self._stats
    
    def get_history(self, limit: Optional[int] = None) -> List[RecoveryAttempt]:
        """Get recovery history"""
        history = list(self._history)
        if limit:
            history = history[-limit:]
        return history
    
    def get_cooldown_status(self) -> Dict[str, float]:
        """Get cooldown status for all strategies"""
        status = {}
        current_time = time.time()
        
        for strategy, last_exec in self._last_execution.items():
            action = self._strategies.get(strategy)
            if action:
                elapsed = current_time - last_exec
                remaining = max(0, action.cooldown - elapsed)
                status[strategy.value] = {
                    "remaining_seconds": round(remaining, 1),
                    "cooldown_seconds": action.cooldown,
                    "in_cooldown": remaining > 0
                }
        
        return status
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            "service_name": self.service_name,
            "strategy_chain": [s.value for s in self._strategy_chain],
            "registered_strategies": {
                s.value: {
                    "name": a.name,
                    "timeout": a.timeout,
                    "cooldown": a.cooldown,
                    "critical": a.critical,
                    "last_execution": self._last_execution.get(s)
                }
                for s, a in self._strategies.items()
            },
            "stats": {
                "total_attempts": self._stats.total_attempts,
                "successful_attempts": self._stats.successful_attempts,
                "failed_attempts": self._stats.failed_attempts,
                "success_rate": round(
                    self._stats.successful_attempts / max(1, self._stats.total_attempts) * 100,
                    2
                ),
                "mean_recovery_time_ms": round(self._stats.mean_recovery_time_ms, 2),
                "max_recovery_time_ms": round(self._stats.max_recovery_time_ms, 2),
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_attempt_time": self._stats.last_attempt_time,
                "last_attempt_strategy": self._stats.last_attempt_strategy,
            },
            "cooldown_status": self.get_cooldown_status(),
            "recent_history": [
                {
                    "timestamp": a.timestamp,
                    "strategy": a.strategy.value,
                    "success": a.success,
                    "duration_ms": round(a.duration_ms, 2),
                    "error": a.error
                }
                for a in list(self._history)[-10:]
            ]
        }
