"""
Explainability & Governance
==========================

Enterprise governance and audit system for algorithmic trading.

Components:
    - Audit Records
    - Immutable Audit Logs
    - Calibration Drift Dashboard
    - Model Health Dashboard
    - Strategy Health Dashboard
    - Deployment History Dashboard
    - Configuration Changes Tracking
    - Approval Workflows
"""

__version__ = "1.0.0"

from .audit_record import (
    AuditRecord, AuditLogger, DecisionType, RiskCheckResult,
    MarketState, ModelVersion, FeatureSnapshot, AlternativeAction,
    RiskCheck, HistoricalAnalogue
)
from .immutable_log import ImmutableAuditLog, LogIntegrityError, LogEntry, LogEntryType
from .dashboards import (
    CalibrationDriftDashboard, CalibrationStatus,
    ModelHealthDashboard, ModelHealthStatus,
    StrategyHealthDashboard, StrategyHealthStatus,
    DeploymentHistoryDashboard, DeploymentRecord,
    ConfigurationChangesDashboard, ConfigChange,
    CalibrationMetric, ModelHealthMetric, StrategyHealthMetric
)
from .workflows import (
    ApprovalWorkflow, ApprovalRequest, ApprovalStatus, ApprovalType,
    ApprovalLevel, ApprovalRequirement, ApprovalDecision
)
from .governance import GovernanceManager, GovernanceConfig, GovernanceEvent

__all__ = [
    # Audit Records
    "AuditRecord",
    "AuditLogger",
    "DecisionType",
    "RiskCheckResult",
    "MarketState",
    "ModelVersion",
    "FeatureSnapshot",
    "AlternativeAction",
    "RiskCheck",
    "HistoricalAnalogue",
    # Immutable Log
    "ImmutableAuditLog",
    "LogIntegrityError",
    "LogEntry",
    "LogEntryType",
    # Dashboards
    "CalibrationDriftDashboard",
    "CalibrationStatus",
    "CalibrationMetric",
    "ModelHealthDashboard",
    "ModelHealthStatus",
    "ModelHealthMetric",
    "StrategyHealthDashboard",
    "StrategyHealthStatus",
    "StrategyHealthMetric",
    "DeploymentHistoryDashboard",
    "DeploymentRecord",
    "ConfigurationChangesDashboard",
    "ConfigChange",
    # Workflows
    "ApprovalWorkflow",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalType",
    "ApprovalLevel",
    "ApprovalRequirement",
    "ApprovalDecision",
    # Governance
    "GovernanceManager",
    "GovernanceConfig",
    "GovernanceEvent",
]
