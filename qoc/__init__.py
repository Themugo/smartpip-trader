"""
Quant Operations Center (QOC)
===========================

Continuously operating quantitative research and execution platform.

Sections:
1. Control Room - Mission control dashboard
2. Daily Operations - Automated reports
3. Continuous Validation - Hourly checks
4. Research Pipeline - Continuous improvement
5. Operational KPIs - Metrics tracking
6. Incident Management - Automated detection
7. Go/No-Go Board - Deployment gates
"""

__version__ = "1.0.0"

from .core import (
    OperationalStatus,
    ComponentStatus,
    HealthScore,
)
from .control_room import ControlRoom
from .daily_ops import DailyOperations
from .continuous_validation import ContinuousValidation
from .research_pipeline import ResearchPipeline
from .kpis import OperationalKPIs
from .incident import IncidentManager
from .go_no_go import GoNoGoBoard

__all__ = [
    "OperationalStatus",
    "ComponentStatus",
    "HealthScore",
    "ControlRoom",
    "DailyOperations",
    "ContinuousValidation",
    "ResearchPipeline",
    "OperationalKPIs",
    "IncidentManager",
    "GoNoGoBoard",
]
