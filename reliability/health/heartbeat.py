"""
Heartbeat Monitor
=================

Monitors service liveness through periodic heartbeat signals.
"""

import asyncio
import time
import logging
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class HeartbeatStatus(Enum):
    """Heartbeat status levels"""
    ALIVE = "alive"
    LATE = "late"           # Heartbeat is delayed
    MISSING = "missing"     # Heartbeat missed
    DEAD = "dead"           # Service considered dead


@dataclass
class HeartbeatConfig:
    """Configuration for heartbeat monitoring"""
    interval: float = 5.0          # Heartbeat interval in seconds
    timeout: float = 15.0          # Time before marking as late
    death_timeout: float = 30.0    # Time before marking as dead
    max_buffer: int = 100          # Max heartbeats to keep in history


@dataclass
class HeartbeatRecord:
    """Record of a heartbeat"""
    timestamp: float
    sequence: int
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceHeartbeat:
    """Heartbeat information for a service"""
    name: str
    status: HeartbeatStatus
    last_heartbeat: Optional[float] = None
    first_heartbeat: Optional[float] = None
    sequence: int = 0
    missed_heartbeats: int = 0
    total_heartbeats: int = 0
    mean_latency_ms: float = 0.0
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "first_heartbeat": self.first_heartbeat,
            "sequence": self.sequence,
            "missed_heartbeats": self.missed_heartbeats,
            "total_heartbeats": self.total_heartbeats,
            "mean_latency_ms": self.mean_latency_ms,
            "uptime_seconds": self.uptime_seconds,
            "metadata": self.metadata,
        }


class HeartbeatMonitor:
    """
    Monitors service heartbeats to detect failures.
    
    Features:
    - Automatic heartbeat tracking
    - Configurable timeouts
    - Status escalation (alive -> late -> missing -> dead)
    - Historical tracking
    - Alert callbacks
    - Heartbeat acknowledgment
    """
    
    def __init__(
        self,
        service_name: str,
        config: Optional[HeartbeatConfig] = None
    ):
        self.service_name = service_name
        self.config = config or HeartbeatConfig()
        
        self._heartbeats: Dict[str, ServiceHeartbeat] = {}
        self._history: Dict[str, deque] = {}
        self._pending_acks: Dict[str, asyncio.Event] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._start_time = time.time()
        self._last_global_heartbeat = time.time()
        
        self._alert_callbacks: Dict[HeartbeatStatus, List[Callable]] = {
            status: [] for status in HeartbeatStatus
        }
        
        self._lock = asyncio.Lock()
    
    def register_alert_callback(
        self,
        status: HeartbeatStatus,
        callback: Callable[[str, ServiceHeartbeat], None]
    ) -> None:
        """Register a callback for status alerts"""
        self._alert_callbacks[status].append(callback)
    
    async def register_service(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a service for heartbeat monitoring"""
        async with self._lock:
            if name not in self._heartbeats:
                self._heartbeats[name] = ServiceHeartbeat(
                    name=name,
                    status=HeartbeatStatus.DEAD,
                    metadata=metadata or {}
                )
                self._history[name] = deque(maxlen=self.config.max_buffer)
                
                # Start monitoring task
                task = asyncio.create_task(self._monitor_loop(name))
                self._monitoring_tasks[name] = task
                
                logger.info(f"Registered service for heartbeat monitoring: {name}")
    
    async def unregister_service(self, name: str) -> None:
        """Unregister a service"""
        async with self._lock:
            if name in self._monitoring_tasks:
                self._monitoring_tasks[name].cancel()
                try:
                    await self._monitoring_tasks[name]
                except asyncio.CancelledError:
                    pass
                del self._monitoring_tasks[name]
            
            if name in self._heartbeats:
                del self._heartbeats[name]
            
            if name in self._history:
                del self._history[name]
            
            logger.info(f"Unregistered service from heartbeat monitoring: {name}")
    
    async def send_heartbeat(
        self,
        name: str,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a heartbeat from a service.
        
        Args:
            name: Service name
            latency_ms: Round-trip latency
            metadata: Optional metadata
            
        Returns:
            True if heartbeat was recorded
        """
        async with self._lock:
            current_time = time.time()
            
            if name not in self._heartbeats:
                await self.register_service(name)
            
            heartbeat = self._heartbeats[name]
            heartbeat.sequence += 1
            heartbeat.last_heartbeat = current_time
            
            if heartbeat.first_heartbeat is None:
                heartbeat.first_heartbeat = current_time
            
            heartbeat.total_heartbeats += 1
            heartbeat.missed_heartbeats = 0
            heartbeat.status = HeartbeatStatus.ALIVE
            
            # Update mean latency
            alpha = 0.1
            heartbeat.mean_latency_ms = (
                alpha * latency_ms + (1 - alpha) * heartbeat.mean_latency_ms
            )
            
            # Update metadata
            if metadata:
                heartbeat.metadata.update(metadata)
            
            # Update uptime
            if heartbeat.first_heartbeat:
                heartbeat.uptime_seconds = current_time - heartbeat.first_heartbeat
            
            # Add to history
            record = HeartbeatRecord(
                timestamp=current_time,
                sequence=heartbeat.sequence,
                latency_ms=latency_ms,
                metadata=metadata or {}
            )
            self._history[name].append(record)
            
            # Signal any pending acks
            if name in self._pending_acks:
                self._pending_acks[name].set()
            
            self._last_global_heartbeat = current_time
            
            return True
    
    async def wait_for_heartbeat(
        self,
        name: str,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Wait for the next heartbeat from a service.
        
        Args:
            name: Service name
            timeout: Maximum time to wait
            
        Returns:
            True if heartbeat received within timeout
        """
        timeout = timeout or self.config.timeout
        
        if name not in self._pending_acks:
            self._pending_acks[name] = asyncio.Event()
        
        event = self._pending_acks[name]
        event.clear()
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
    
    async def acknowledge(self, name: str) -> None:
        """Acknowledge a service (from the service itself)"""
        await self.send_heartbeat(name)
    
    async def _monitor_loop(self, name: str) -> None:
        """Monitor loop for a service"""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                async with self._lock:
                    if name not in self._heartbeats:
                        continue
                    
                    heartbeat = self._heartbeats[name]
                    current_time = time.time()
                    
                    if heartbeat.last_heartbeat is None:
                        heartbeat.status = HeartbeatStatus.DEAD
                        continue
                    
                    time_since_heartbeat = current_time - heartbeat.last_heartbeat
                    
                    # Determine status based on time since last heartbeat
                    old_status = heartbeat.status
                    
                    if time_since_heartbeat <= self.config.timeout:
                        heartbeat.status = HeartbeatStatus.ALIVE
                    elif time_since_heartbeat <= self.config.death_timeout:
                        if heartbeat.status != HeartbeatStatus.LATE:
                            heartbeat.status = HeartbeatStatus.LATE
                            heartbeat.missed_heartbeats = int(
                                time_since_heartbeat / self.config.interval
                            )
                    else:
                        heartbeat.status = HeartbeatStatus.DEAD
                        heartbeat.missed_heartbeats = int(
                            time_since_heartbeat / self.config.interval
                        )
                    
                    # Trigger alerts on status change
                    if old_status != heartbeat.status:
                        await self._trigger_alert(name, heartbeat)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error for {name}: {e}")
    
    async def _trigger_alert(self, name: str, heartbeat: ServiceHeartbeat) -> None:
        """Trigger alert callbacks for status change"""
        callbacks = self._alert_callbacks.get(heartbeat.status, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(name, heartbeat)
                else:
                    callback(name, heartbeat)
            except Exception as e:
                logger.error(f"Heartbeat alert callback failed: {e}")
        
        # Log status changes
        if heartbeat.status == HeartbeatStatus.DEAD:
            logger.error(f"Service {name} heartbeat dead!")
        elif heartbeat.status == HeartbeatStatus.MISSING:
            logger.warning(f"Service {name} missing heartbeats")
        elif heartbeat.status == HeartbeatStatus.LATE:
            logger.info(f"Service {name} heartbeat late")
    
    async def start(self) -> None:
        """Start heartbeat monitoring"""
        self._running = True
        
        # Send our own heartbeat periodically
        asyncio.create_task(self._self_heartbeat_loop())
        
        logger.info(f"Heartbeat monitor started for {self.service_name}")
    
    async def _self_heartbeat_loop(self) -> None:
        """Send our own heartbeat periodically"""
        while self._running:
            await self.send_heartbeat(
                self.service_name,
                metadata={"type": "monitor"}
            )
            await asyncio.sleep(self.config.interval)
    
    async def stop(self) -> None:
        """Stop heartbeat monitoring"""
        self._running = False
        
        for task in self._monitoring_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_tasks.clear()
        logger.info(f"Heartbeat monitor stopped for {self.service_name}")
    
    def get_heartbeat(self, name: Optional[str] = None) -> ServiceHeartbeat:
        """Get heartbeat info for a service"""
        if name:
            return self._heartbeats.get(name)
        
        # Get aggregate heartbeat
        if not self._heartbeats:
            return ServiceHeartbeat(
                name=self.service_name,
                status=HeartbeatStatus.DEAD
            )
        
        # Most critical status
        statuses = [h.status for h in self._heartbeats.values()]
        if HeartbeatStatus.DEAD in statuses:
            overall = HeartbeatStatus.DEAD
        elif HeartbeatStatus.MISSING in statuses:
            overall = HeartbeatStatus.MISSING
        elif HeartbeatStatus.LATE in statuses:
            overall = HeartbeatStatus.LATE
        else:
            overall = HeartbeatStatus.ALIVE
        
        return ServiceHeartbeat(
            name=self.service_name,
            status=overall,
            total_heartbeats=sum(h.total_heartbeats for h in self._heartbeats.values()),
            uptime_seconds=time.time() - self._start_time
        )
    
    def get_all_heartbeats(self) -> Dict[str, ServiceHeartbeat]:
        """Get heartbeat info for all services"""
        return {
            name: h.to_dict() if hasattr(h, 'to_dict') else h
            for name, h in self._heartbeats.items()
        }
    
    def get_history(
        self,
        name: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get heartbeat history for a service"""
        if name not in self._history:
            return []
        
        history = list(self._history[name])
        if limit:
            history = history[-limit:]
        
        return [
            {
                "timestamp": r.timestamp,
                "sequence": r.sequence,
                "latency_ms": r.latency_ms,
                "metadata": r.metadata
            }
            for r in history
        ]
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        heartbeat = self.get_heartbeat()
        
        return {
            "monitor": {
                "name": self.service_name,
                "status": heartbeat.status.value,
                "uptime_seconds": heartbeat.uptime_seconds,
                "total_heartbeats": heartbeat.total_heartbeats,
            },
            "services": {
                name: h.to_dict()
                for name, h in self._heartbeats.items()
            },
            "statistics": {
                "total_services": len(self._heartbeats),
                "alive": sum(1 for h in self._heartbeats.values() if h.status == HeartbeatStatus.ALIVE),
                "late": sum(1 for h in self._heartbeats.values() if h.status == HeartbeatStatus.LATE),
                "missing": sum(1 for h in self._heartbeats.values() if h.status == HeartbeatStatus.MISSING),
                "dead": sum(1 for h in self._heartbeats.values() if h.status == HeartbeatStatus.DEAD),
            },
            "last_global_heartbeat": self._last_global_heartbeat,
            "config": {
                "interval": self.config.interval,
                "timeout": self.config.timeout,
                "death_timeout": self.config.death_timeout,
            }
        }
