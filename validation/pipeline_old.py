"""
Continuous Validation Pipeline
============================

Permanent validation pipeline for strategy changes.
"""

__version__ = "1.0.0"

from .pipeline import ValidationPipeline, ValidationStage, ValidationResult
from .acceptance import AcceptanceCriteria, AcceptanceResult
from .report import DeploymentReport, ReportGenerator

__all__ = [
    "ValidationPipeline",
    "ValidationStage",
    "ValidationResult",
    "AcceptanceCriteria",
    "AcceptanceResult",
    "DeploymentReport",
    "ReportGenerator",
]
