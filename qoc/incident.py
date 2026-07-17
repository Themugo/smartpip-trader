"""
Incident Management
==================

Automated incident detection and response.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(Enum):
    """Incident status"""
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


@dataclass
class Incident:
    """System incident"""
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    
    status: IncidentStatus
    created_at: float
    detected_at: float
    
    # Source
    source: str
    source_id: str
    
    # Timeline
    acknowledged_at: Optional[float] = None
    investigating_at: Optional[float] = None
    mitigating_at: Optional[float] = None
    resolved_at: Optional[float] = None
    
    # Details
    affected_components: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    error_logs: List[str] = field(default_factory=list)
    
    # Resolution
    root_cause: str = ""
    resolution: str = ""
    lessons_learned: str = ""
    
    # Postmortem
    postmortem_generated: bool = False
    postmortem_path: str = ""
    
    def get_duration(self) -> float:
        """Get incident duration in seconds"""
        end = self.resolved_at or time.time()
        return end - self.detected_at
    
    def get_mttr(self) -> float:
        """Get Mean Time To Resolution in minutes"""
        if not self.resolved_at:
            return 0
        return self.get_duration() / 60
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "duration_seconds": self.get_duration(),
            "mttr_minutes": self.get_mttr(),
            "source": self.source,
            "affected_components": self.affected_components,
        }


class IncidentDetector:
    """Base class for incident detectors"""
    
    def detect(self, context: Dict[str, Any]) -> Optional[Incident]:
        """Detect an incident"""
        raise NotImplementedError


class ModelFailureDetector(IncidentDetector):
    """Detects model failures"""
    
    def detect(self, context: Dict[str, Any]) -> Optional[Incident]:
        if context.get("prediction_error", 0) > 0.3:
            return Incident(
                id=str(uuid.uuid4())[:8],
                title="Model Prediction Failure",
                description=f"Model error rate: {context.get('prediction_error', 0):.1%}",
                severity=IncidentSeverity.HIGH,
                status=IncidentStatus.DETECTED,
                created_at=time.time(),
                detected_at=time.time(),
                source="model_monitor",
                source_id="model_failure",
                metrics={"error_rate": context.get("prediction_error", 0)},
            )
        return None


class ExecutionFailureDetector(IncidentDetector):
    """Detects execution failures"""
    
    def detect(self, context: Dict[str, Any]) -> Optional[Incident]:
        if context.get("execution_failure_rate", 0) > 0.1:
            return Incident(
                id=str(uuid.uuid4())[:8],
                title="Execution Failure Spike",
                description=f"Execution failures: {context.get('execution_failure_rate', 0):.1%}",
                severity=IncidentSeverity.HIGH,
                status=IncidentStatus.DETECTED,
                created_at=time.time(),
                detected_at=time.time(),
                source="execution_monitor",
                source_id="execution_failure",
                metrics={"failure_rate": context.get("execution_failure_rate", 0)},
            )
        return None


class LatencySpikeDetector(IncidentDetector):
    """Detects latency spikes"""
    
    def detect(self, context: Dict[str, Any]) -> Optional[Incident]:
        if context.get("latency_p99_ms", 0) > 500:
            return Incident(
                id=str(uuid.uuid4())[:8],
                title="Latency Spike",
                description=f"P99 latency: {context.get('latency_p99_ms', 0):.0f}ms",
                severity=IncidentSeverity.MEDIUM,
                status=IncidentStatus.DETECTED,
                created_at=time.time(),
                detected_at=time.time(),
                source="latency_monitor",
                source_id="latency_spike",
                metrics={"latency_ms": context.get("latency_p99_ms", 0)},
            )
        return None


class IncidentManager:
    """
    Automated incident management.
    
    Detects, tracks, and manages incidents.
    """
    
    def __init__(self):
        # Active incidents
        self._incidents: Dict[str, Incident] = {}
        
        # Incident history
        self._history: List[Incident] = []
        
        # Detectors
        self._detectors: List[IncidentDetector] = [
            ModelFailureDetector(),
            ExecutionFailureDetector(),
            LatencySpikeDetector(),
        ]
        
        # Callbacks
        self._on_incident: List[Callable] = []
        self._on_resolved: List[Callable] = []
    
    def register_detector(self, detector: IncidentDetector) -> None:
        """Register an incident detector"""
        self._detectors.append(detector)
    
    def on_incident(self, callback: Callable[[Incident], None]) -> None:
        """Register incident callback"""
        self._on_incident.append(callback)
    
    def on_resolved(self, callback: Callable[[Incident], None]) -> None:
        """Register resolved callback"""
        self._on_resolved.append(callback)
    
    def check(self, context: Dict[str, Any]) -> List[Incident]:
        """Run all detectors and return new incidents"""
        new_incidents = []
        
        for detector in self._detectors:
            try:
                incident = detector.detect(context)
                if incident:
                    self._create_incident(incident)
                    new_incidents.append(incident)
            except Exception as e:
                logger.error(f"Detector failed: {e}")
        
        return new_incidents
    
    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        source: str,
        source_id: str = "",
        affected_components: List[str] = None,
        metrics: Dict[str, float] = None,
    ) -> Incident:
        """Manually create an incident"""
        incident = Incident(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.DETECTED,
            created_at=time.time(),
            detected_at=time.time(),
            source=source,
            source_id=source_id,
            affected_components=affected_components or [],
            metrics=metrics or {},
        )
        
        return self._create_incident(incident)
    
    def _create_incident(self, incident: Incident) -> Incident:
        """Internal incident creation"""
        self._incidents[incident.id] = incident
        
        for callback in self._on_incident:
            try:
                callback(incident)
            except Exception as e:
                logger.error(f"Incident callback failed: {e}")
        
        logger.warning(f"Incident created: {incident.title} ({incident.severity.value})")
        return incident
    
    def acknowledge(self, incident_id: str) -> bool:
        """Acknowledge an incident"""
        if incident_id not in self._incidents:
            return False
        
        incident = self._incidents[incident_id]
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = time.time()
        
        return True
    
    def start_investigation(self, incident_id: str) -> bool:
        """Start investigating an incident"""
        if incident_id not in self._incidents:
            return False
        
        incident = self._incidents[incident_id]
        incident.status = IncidentStatus.INVESTIGATING
        incident.investigating_at = time.time()
        
        return True
    
    def start_mitigation(self, incident_id: str) -> bool:
        """Start mitigating an incident"""
        if incident_id not in self._incidents:
            return False
        
        incident = self._incidents[incident_id]
        incident.status = IncidentStatus.MITIGATING
        incident.mitigating_at = time.time()
        
        return True
    
    def resolve(
        self,
        incident_id: str,
        root_cause: str = "",
        resolution: str = "",
    ) -> bool:
        """Resolve an incident"""
        if incident_id not in self._incidents:
            return False
        
        incident = self._incidents[incident_id]
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = time.time()
        incident.root_cause = root_cause
        incident.resolution = resolution
        
        # Move to history
        self._history.append(incident)
        del self._incidents[incident_id]
        
        for callback in self._on_resolved:
            try:
                callback(incident)
            except Exception as e:
                logger.error(f"Resolved callback failed: {e}")
        
        logger.info(f"Incident resolved: {incident_id}")
        return True
    
    def generate_postmortem(self, incident_id: str) -> Dict[str, Any]:
        """Generate postmortem report"""
        if incident_id not in self._incidents:
            # Check history
            for incident in self._history:
                if incident.id == incident_id:
                    return self._generate_postmortem_content(incident)
            return {}
        
        return self._generate_postmortem_content(self._incidents[incident_id])
    
    def _generate_postmortem_content(self, incident: Incident) -> Dict[str, Any]:
        """Generate postmortem content"""
        return {
            "incident_id": incident.id,
            "title": incident.title,
            "severity": incident.severity.value,
            "duration_minutes": incident.get_mttr(),
            "timeline": {
                "detected": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(incident.detected_at)),
                "acknowledged": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(incident.acknowledged_at)) if incident.acknowledged_at else None,
                "resolved": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(incident.resolved_at)) if incident.resolved_at else None,
            },
            "root_cause": incident.root_cause,
            "resolution": incident.resolution,
            "metrics": incident.metrics,
            "lessons_learned": incident.lessons_learned,
        }
    
    def get_active_incidents(self) -> List[Incident]:
        """Get all active incidents"""
        return list(self._incidents.values())
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get an incident by ID"""
        if incident_id in self._incidents:
            return self._incidents[incident_id]
        for incident in self._history:
            if incident.id == incident_id:
                return incident
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get incident summary"""
        active = self.get_active_incidents()
        
        return {
            "active_count": len(active),
            "by_severity": {
                "critical": len([i for i in active if i.severity == IncidentSeverity.CRITICAL]),
                "high": len([i for i in active if i.severity == IncidentSeverity.HIGH]),
                "medium": len([i for i in active if i.severity == IncidentSeverity.MEDIUM]),
                "low": len([i for i in active if i.severity == IncidentSeverity.LOW]),
            },
            "by_status": {
                "detected": len([i for i in active if i.status == IncidentStatus.DETECTED]),
                "acknowledged": len([i for i in active if i.status == IncidentStatus.ACKNOWLEDGED]),
                "investigating": len([i for i in active if i.status == IncidentStatus.INVESTIGATING]),
                "mitigating": len([i for i in active if i.status == IncidentStatus.MITIGATING]),
            },
            "total_resolved": len(self._history),
            "recent_incidents": [i.to_dict() for i in self._history[-10:]],
        }
