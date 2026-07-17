"""
QOC Core
========

Core classes for Quant Operations Center.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OperationalStatus(Enum):
    """Overall operational status"""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


class ComponentStatus(Enum):
    """Component status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


@dataclass
class HealthScore:
    """Overall health score with breakdown"""
    overall: float  # 0.0 - 1.0
    system: float
    market: float
    paper_trading: float
    live_trading: float
    strategy: float
    model: float
    risk: float
    infrastructure: float
    
    timestamp: float = field(default_factory=time.time)
    
    # Component details
    component_scores: Dict[str, float] = field(default_factory=dict)
    
    def get_status(self) -> OperationalStatus:
        """Get operational status from health score"""
        if self.overall >= 0.9:
            return OperationalStatus.OPERATIONAL
        elif self.overall >= 0.7:
            return OperationalStatus.DEGRADED
        elif self.overall >= 0.5:
            return OperationalStatus.PARTIAL_OUTAGE
        else:
            return OperationalStatus.MAJOR_OUTAGE
    
    def get_grade(self) -> str:
        """Get letter grade"""
        if self.overall >= 0.95:
            return "A+"
        elif self.overall >= 0.90:
            return "A"
        elif self.overall >= 0.85:
            return "B+"
        elif self.overall >= 0.80:
            return "B"
        elif self.overall >= 0.70:
            return "C"
        elif self.overall >= 0.60:
            return "D"
        else:
            return "F"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "grade": self.get_grade(),
            "status": self.get_status().value,
            "components": {
                "system": self.system,
                "market": self.market,
                "paper_trading": self.paper_trading,
                "live_trading": self.live_trading,
                "strategy": self.strategy,
                "model": self.model,
                "risk": self.risk,
                "infrastructure": self.infrastructure,
            },
            "component_scores": self.component_scores,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricSnapshot:
    """Snapshot of a metric at a point in time"""
    name: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Operational alert"""
    alert_id: str
    severity: str  # critical, high, medium, low, info
    component: str
    title: str
    description: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class DeploymentInfo:
    """Deployment information"""
    version: str
    environment: str  # paper, staging, production
    deployed_at: float
    deployed_by: str
    status: str  # deployed, failed, rolled_back
    checksums: Dict[str, str] = field(default_factory=dict)
