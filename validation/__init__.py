"""
Continuous Validation Pipeline
============================

Permanent validation pipeline for strategy changes.
"""

__version__ = "1.0.0"

from .continuous import (
    ContinuousValidationPipeline,
    ValidationStage,
    ValidationStatus,
    ValidationResult,
    ValidationConfig
)
from .acceptance import (
    AcceptanceCriteria,
    AcceptanceResult,
    AcceptancePolicy,
    Criterion,
    CriterionType,
    ComparisonOperator
)
from .report import (
    DeploymentReport,
    ReportGenerator,
    ReportFormat
)

__all__ = [
    "ContinuousValidationPipeline",
    "ValidationStage",
    "ValidationStatus",
    "ValidationResult",
    "ValidationConfig",
    "AcceptanceCriteria",
    "AcceptanceResult",
    "AcceptancePolicy",
    "Criterion",
    "CriterionType",
    "ComparisonOperator",
    "DeploymentReport",
    "ReportGenerator",
    "ReportFormat",
]
