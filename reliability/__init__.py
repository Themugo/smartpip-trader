"""
Reliability Engineering Module
==========================

Mission-critical reliability infrastructure for the trading platform.
Implements circuit breakers, retry policies, dead letter queues,
health checks, watchdog processes, and automatic recovery.
"""

__version__ = "1.0.0"

# Import from core subpackage (circuit breaker is in __init__.py)
from .core import CircuitBreaker, CircuitState, RetryPolicy, RetryStrategy, RetryExhaustedError
from .core import DeadLetterQueue, MessageStatus, FailureReason
from .core import RateLimiter, ResourceQuotaManager, QuotaExceededAction
from .core import FailoverManager, FailoverStrategy
from .core import GracefulShutdownHandler
from .health import ServiceHealthMonitor, HealthStatus, ServiceHealth
from .health import HeartbeatMonitor, HeartbeatStatus
from .recovery import WatchdogProcess, WatchdogConfig
from .recovery import AutoRecoveryManager, RecoveryStrategy
from .recovery import CrashRecoveryManager, CrashReport
from .supervisor import ServiceRegistry, ServiceMetadata
from .supervisor import DependencyMap, Dependency
from .supervisor import WorkerSupervisor, WorkerProcess
from .supervisor import MessageReplayQueue, EventReplayLog

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    # Retry Policy
    "RetryPolicy",
    "RetryStrategy",
    "RetryExhaustedError",
    # Dead Letter Queue
    "DeadLetterQueue",
    "MessageEnvelope",
    # Rate Limiting
    "RateLimiter",
    "ResourceQuota",
    # Failover
    "FailoverManager",
    "FailoverStrategy",
    # Graceful Shutdown
    "GracefulShutdownHandler",
    # Health Monitoring
    "ServiceHealthMonitor",
    "HealthStatus",
    "ServiceHealth",
    # Heartbeat
    "HeartbeatMonitor",
    "HeartbeatStatus",
    # Watchdog
    "WatchdogProcess",
    "WatchdogConfig",
    # Auto Recovery
    "AutoRecoveryManager",
    "RecoveryStrategy",
    # Crash Recovery
    "CrashRecoveryManager",
    "CrashReport",
    # Service Registry
    "ServiceRegistry",
    "ServiceMetadata",
    # Dependency Map
    "DependencyMap",
    "Dependency",
    # Worker Supervisor
    "WorkerSupervisor",
    "WorkerProcess",
    # Message Replay
    "MessageReplayQueue",
    "EventReplayLog",
]
