"""
Simulation Framework
==================

Realistic execution simulator for testing trading strategies under adverse conditions.

Features:
- Latency Simulation: Model realistic network delays
- Network Interruptions: Simulate connection drops
- WebSocket Drops: Simulate WebSocket disconnections
- API Failures: Simulate exchange API errors
- Clock Drift: Time synchronization issues
- Delayed Market Data: Out-of-order data arrival
- Execution Delays: Order execution latency
- Resource Constraints: CPU, memory limitations
- Partial Failures: Partial fills, cancellations
- Recovery Scenarios: System recovery patterns
- Market Data Corruption: Invalid data injection
- Incident Replay: Replay production incidents
- Stress Testing: Adverse condition testing
- Resilience Reports: Strategy resilience analysis
"""

__version__ = "1.0.0"

from .simulator import (
    ExecutionSimulator,
    SimulationConfig,
    SimulationResult,
)
from .failures import (
    FailureInjector,
    FailureType,
    FailureScenario,
    NetworkConditions,
)
from .incidents import (
    IncidentRecorder,
    IncidentReplayer,
    Incident,
)
from .stress_test import (
    StressTestRunner,
    StressTestConfig,
    StressTestResult,
)
from .resilience import (
    ResilienceAnalyzer,
    ResilienceReport,
)

__all__ = [
    "ExecutionSimulator",
    "SimulationConfig",
    "SimulationResult",
    "FailureInjector",
    "FailureType",
    "FailureScenario",
    "NetworkConditions",
    "IncidentRecorder",
    "IncidentReplayer",
    "Incident",
    "StressTestRunner",
    "StressTestConfig",
    "StressTestResult",
    "ResilienceAnalyzer",
    "ResilienceReport",
]
