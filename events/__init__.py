"""
Event Sourcing Platform
=====================

Deterministic event-driven architecture for the trading platform.

Every important action generates immutable events that can be replayed,
queried, and verified for complete auditability.

Event Types:
- Market Events: Tick, Snapshot
- AI Events: Prediction, Risk Evaluation, Confidence
- Trading Events: Decision, Approval, Rejection, Execution
- System Events: Configuration, Plugin, Health
- Research Events: Validation, Research
"""

__version__ = "1.0.0"

from .core import (
    Event,
    EventType,
    EventStore,
    EventMetadata,
    SequenceNumber,
)
from .market import (
    MarketTickEvent,
    MarketSnapshotEvent,
    FeatureCalculationEvent,
)
from .ai import (
    AIPredictionEvent,
    RiskEvaluationEvent,
    ConfidenceCalculationEvent,
    StrategyDecisionEvent,
)
from .trading import (
    TradeApprovalEvent,
    TradeRejectionEvent,
    ExecutionRequestEvent,
    ExecutionConfirmationEvent,
    ExecutionFailureEvent,
)
from .system import (
    ConfigurationChangeEvent,
    PluginEvent,
    SystemAlertEvent,
    HealthEvent,
)
from .research import (
    ResearchEvent,
    ValidationEvent,
)
from .store import (
    EventStoreDB,
    EventQuery,
    EventReplay,
)

__all__ = [
    "Event",
    "EventType",
    "EventStore",
    "EventMetadata",
    "SequenceNumber",
    "MarketTickEvent",
    "MarketSnapshotEvent",
    "FeatureCalculationEvent",
    "AIPredictionEvent",
    "RiskEvaluationEvent",
    "ConfidenceCalculationEvent",
    "StrategyDecisionEvent",
    "TradeApprovalEvent",
    "TradeRejectionEvent",
    "ExecutionRequestEvent",
    "ExecutionConfirmationEvent",
    "ExecutionFailureEvent",
    "ConfigurationChangeEvent",
    "PluginEvent",
    "SystemAlertEvent",
    "HealthEvent",
    "ResearchEvent",
    "ValidationEvent",
    "EventStoreDB",
    "EventQuery",
    "EventReplay",
]
