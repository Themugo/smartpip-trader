"""
AI Mission Control - Central Dashboard

Central dashboard showing:
- Active agents
- Workloads
- Research status
- Experiment queue
- Validation queue
- System health
- Resource utilization
- Completed discoveries
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ai_cluster.bus import AICollaborationBus
from ai_cluster.scheduler import TaskScheduler, JobStatus, JobType

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status indicators"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentSnapshot:
    """Snapshot of an agent's state"""
    agent_id: str
    agent_name: str
    agent_type: str
    
    # Status
    status: AgentStatus
    state: str
    
    # Workload
    current_tasks: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    
    # Performance
    avg_task_duration: float = 0
    last_task_at: Optional[datetime] = None
    
    # Discovery metrics
    discoveries: int = 0
    recommendations: int = 0
    confidence_avg: float = 0
    
    # Health
    heartbeat_age_seconds: float = 0
    error_count: int = 0
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "state": self.state,
            "current_tasks": self.current_tasks,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "discoveries": self.discoveries,
            "recommendations": self.recommendations,
            "confidence_avg": self.confidence_avg,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QueueItem:
    """Item in a queue"""
    id: str
    name: str
    priority: str
    status: str
    submitted_at: datetime
    estimated_duration_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat(),
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }


@dataclass
class SystemHealth:
    """System health metrics"""
    cpu_percent: float = 0
    memory_percent: float = 0
    disk_percent: float = 0
    network_latency_ms: float = 0
    
    # AI specific
    active_agents: int = 0
    active_jobs: int = 0
    queue_depth: int = 0
    
    # Reliability
    uptime_seconds: float = 0
    error_rate: float = 0
    
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Discovery:
    """A completed discovery"""
    id: str
    agent_name: str
    title: str
    description: str
    confidence: float
    evidence: List[str]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
        }


class MissionControl:
    """
    AI Mission Control Dashboard.
    
    Features:
    - Real-time agent monitoring
    - Workload visualization
    - Queue management
    - Discovery tracking
    - System health
    - Resource utilization
    """
    
    def __init__(self, bus: AICollaborationBus, scheduler: TaskScheduler):
        self.bus = bus
        self.scheduler = scheduler
        
        # Snapshots
        self._agent_snapshots: Dict[str, AgentSnapshot] = {}
        self._discovery_history: List[Discovery] = []
        self._max_discoveries = 100
        
        # Start monitoring
        self._running = False
    
    async def start_monitoring(self) -> None:
        """Start the monitoring loop"""
        self._running = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("Mission Control monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop"""
        self._running = False
        logger.info("Mission Control monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            await self._collect_snapshots()
            await asyncio.sleep(5)  # Collect every 5 seconds
    
    async def _collect_snapshots(self) -> None:
        """Collect snapshots of all agents"""
        agents = self.bus.get_active_agents()
        
        for reg in agents:
            snapshot = AgentSnapshot(
                agent_id=reg.agent_id,
                agent_name=reg.agent_name,
                agent_type=reg.agent_type,
                status=self._get_agent_status(reg),
                state="working" if reg.current_tasks > 0 else "idle",
                current_tasks=reg.current_tasks,
            )
            
            self._agent_snapshots[reg.agent_id] = snapshot
    
    def _get_agent_status(self, reg) -> AgentStatus:
        """Determine agent status"""
        # Check heartbeat age
        heartbeat_age = (datetime.utcnow() - reg.last_heartbeat).total_seconds()
        
        if heartbeat_age > 60:
            return AgentStatus.OFFLINE
        elif heartbeat_age > 30:
            return AgentStatus.WARNING
        
        return AgentStatus.HEALTHY
    
    async def record_discovery(self, discovery: Discovery) -> None:
        """Record a new discovery"""
        self._discovery_history.append(discovery)
        
        # Trim history
        if len(self._discovery_history) > self._max_discoveries:
            self._discovery_history.pop(0)
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get full dashboard data"""
        return {
            "agents": self._get_agent_summary(),
            "workloads": self._get_workload_summary(),
            "research_status": self._get_research_summary(),
            "experiment_queue": self._get_experiment_queue(),
            "validation_queue": self._get_validation_queue(),
            "system_health": self._get_health_summary(),
            "discoveries": self._get_recent_discoveries(),
        }
    
    def _get_agent_summary(self) -> Dict[str, Any]:
        """Get agent summary"""
        snapshots = list(self._agent_snapshots.values())
        
        healthy = sum(1 for s in snapshots if s.status == AgentStatus.HEALTHY)
        warning = sum(1 for s in snapshots if s.status == AgentStatus.WARNING)
        offline = sum(1 for s in snapshots if s.status == AgentStatus.OFFLINE)
        
        return {
            "total": len(snapshots),
            "healthy": healthy,
            "warning": warning,
            "offline": offline,
            "agents": [s.to_dict() for s in snapshots],
        }
    
    def _get_workload_summary(self) -> Dict[str, Any]:
        """Get workload summary"""
        snapshots = list(self._agent_snapshots.values())
        
        total_tasks = sum(s.current_tasks for s in snapshots)
        total_completed = sum(s.tasks_completed for s in snapshots)
        total_failed = sum(s.tasks_failed for s in snapshots)
        
        return {
            "active_tasks": total_tasks,
            "tasks_completed": total_completed,
            "tasks_failed": total_failed,
            "success_rate": (
                total_completed / (total_completed + total_failed)
                if (total_completed + total_failed) > 0 else 1.0
            ),
        }
    
    def _get_research_summary(self) -> Dict[str, Any]:
        """Get research status"""
        jobs = self.scheduler.get_jobs(job_type=JobType.RESEARCH)
        
        pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "total": len(jobs),
        }
    
    def _get_experiment_queue(self) -> List[QueueItem]:
        """Get experiment queue"""
        jobs = self.scheduler.get_jobs(job_type=JobType.OPTIMIZATION)
        
        return [
            QueueItem(
                id=j.id,
                name=j.name,
                priority=j.priority.value,
                status=j.status.value,
                submitted_at=j.created_at,
            )
            for j in jobs
            if j.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]
        ]
    
    def _get_validation_queue(self) -> List[QueueItem]:
        """Get validation queue"""
        jobs = self.scheduler.get_jobs(job_type=JobType.VALIDATION)
        
        return [
            QueueItem(
                id=j.id,
                name=j.name,
                priority=j.priority.value,
                status=j.status.value,
                submitted_at=j.created_at,
            )
            for j in jobs
            if j.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]
        ]
    
    def _get_health_summary(self) -> Dict[str, Any]:
        """Get system health"""
        stats = self.scheduler.get_statistics()
        
        return {
            "active_agents": stats["active_workers"],
            "active_jobs": stats["running"],
            "queue_depth": stats["pending"] + stats["queued"],
            "cpu_percent": 0,  # Would come from system monitoring
            "memory_percent": 0,
        }
    
    def _get_recent_discoveries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent discoveries"""
        return [
            d.to_dict()
            for d in sorted(
                self._discovery_history,
                key=lambda x: x.created_at,
                reverse=True
            )[:limit]
        ]
    
    def get_agent_detail(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed agent information"""
        snapshot = self._agent_snapshots.get(agent_id)
        if not snapshot:
            return None
        
        return snapshot.to_dict()
    
    def get_queue_detail(self, queue_type: str) -> Dict[str, Any]:
        """Get detailed queue information"""
        if queue_type == "experiment":
            jobs = self.scheduler.get_jobs(job_type=JobType.OPTIMIZATION)
        elif queue_type == "validation":
            jobs = self.scheduler.get_jobs(job_type=JobType.VALIDATION)
        else:
            jobs = []
        
        return {
            "total": len(jobs),
            "by_status": {
                status.value: sum(1 for j in jobs if j.status.value == status.value)
                for status in JobStatus
            },
            "jobs": [j.to_dict() for j in jobs],
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        snapshots = list(self._agent_snapshots.values())
        
        total_discoveries = sum(s.discoveries for s in snapshots)
        total_recommendations = sum(s.recommendations for s in snapshots)
        avg_confidence = (
            sum(s.confidence_avg for s in snapshots) / len(snapshots)
            if snapshots else 0
        )
        
        return {
            "total_discoveries": total_discoveries,
            "total_recommendations": total_recommendations,
            "avg_confidence": avg_confidence,
            "avg_task_duration": (
                sum(s.avg_task_duration for s in snapshots) / len(snapshots)
                if snapshots else 0
            ),
        }
