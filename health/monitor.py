"""
AI Health Monitoring - System Health Dashboard

Monitors all system components:
- Prediction confidence calibration
- Model drift
- Latency
- Resource usage
- Plugin health
- API reliability
- WebSocket stability
"""

import asyncio
import logging
import os
import psutil
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of system components"""
    PLUGIN = "plugin"
    MODEL = "model"
    API = "api"
    WEBSOCKET = "websocket"
    DATABASE = "database"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    SYSTEM = "system"


@dataclass
class ComponentHealth:
    """Health status of a component"""
    component_id: str
    component_type: ComponentType
    name: str
    status: HealthStatus
    message: str = ""
    
    # Metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Timing
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_failure: Optional[datetime] = None
    uptime_seconds: float = 0
    
    # Counts
    success_count: int = 0
    failure_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "metrics": self.metrics,
            "last_check": self.last_check.isoformat(),
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "uptime_seconds": self.uptime_seconds,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": (
                self.success_count / (self.success_count + self.failure_count)
                if (self.success_count + self.failure_count) > 0 else 0
            ),
        }


@dataclass
class HealthMetrics:
    """Current system health metrics"""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # System resources
    cpu_percent: float = 0
    memory_percent: float = 0
    memory_used_mb: float = 0
    disk_percent: float = 0
    
    # GPU (if available)
    gpu_available: bool = False
    gpu_utilization: float = 0
    gpu_memory_percent: float = 0
    
    # Network
    network_latency_ms: float = 0
    api_response_time_ms: float = 0
    
    # System health
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    
    # Alerts
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "disk_percent": self.disk_percent,
            "gpu_available": self.gpu_available,
            "gpu_utilization": self.gpu_utilization,
            "gpu_memory_percent": self.gpu_memory_percent,
            "network_latency_ms": self.network_latency_ms,
            "api_response_time_ms": self.api_response_time_ms,
            "overall_status": self.overall_status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "active_alerts": self.active_alerts,
        }


@dataclass
class ConfidenceCalibration:
    """Confidence calibration metrics"""
    predicted_confidence: float = 0
    actual_accuracy: float = 0
    calibration_error: float = 0  # |predicted - actual|
    brier_score: float = 0
    
    # Historical calibration
    calibration_history: List[Dict[str, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_confidence": self.predicted_confidence,
            "actual_accuracy": self.actual_accuracy,
            "calibration_error": self.calibration_error,
            "brier_score": self.brier_score,
            "calibration_history": self.calibration_history,
        }


@dataclass
class ModelDrift:
    """Model drift detection"""
    metric_name: str
    baseline_value: float
    current_value: float
    drift_percent: float
    is_significant: bool
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "drift_percent": self.drift_percent,
            "is_significant": self.is_significant,
            "detected_at": self.detected_at.isoformat(),
        }


class HealthMonitor:
    """
    Comprehensive AI health monitoring.
    
    Features:
    - Real-time system metrics
    - Component health tracking
    - Confidence calibration
    - Model drift detection
    - Latency monitoring
    - Alert generation
    """
    
    def __init__(
        self,
        storage_path: str = "data/health",
        check_interval: int = 10,
    ):
        self._storage_path = storage_path
        self._check_interval = check_interval
        
        self._metrics = HealthMetrics()
        self._components: Dict[str, ComponentHealth] = {}
        self._calibration = ConfidenceCalibration()
        self._drift_detectors: Dict[str, deque] = {}  # Metric history
        self._alerts: deque = deque(maxlen=1000)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._alert_callbacks: List[Callable] = []
        
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize system monitoring
        self._init_system_monitor()
    
    def _init_system_monitor(self) -> None:
        """Initialize system monitoring"""
        # Register system component
        self.register_component(
            component_id="system",
            component_type=ComponentType.SYSTEM,
            name="System",
        )
        
        # Register API component
        self.register_component(
            component_id="deriv_api",
            component_type=ComponentType.API,
            name="Deriv API",
        )
        
        # Register WebSocket component
        self.register_component(
            component_id="websocket",
            component_type=ComponentType.WEBSOCKET,
            name="WebSocket",
        )
    
    def start_monitoring(self) -> None:
        """Start health monitoring"""
        if self._monitoring_task:
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                await self.check_health()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
    
    def register_component(
        self,
        component_id: str,
        component_type: ComponentType,
        name: str,
    ) -> ComponentHealth:
        """Register a component for monitoring"""
        component = ComponentHealth(
            component_id=component_id,
            component_type=component_type,
            name=name,
            status=HealthStatus.UNKNOWN,
        )
        self._components[component_id] = component
        return component
    
    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component"""
        if component_id in self._components:
            del self._components[component_id]
            return True
        return False
    
    def record_success(self, component_id: str, latency_ms: Optional[float] = None) -> None:
        """Record a successful operation"""
        component = self._components.get(component_id)
        if not component:
            return
        
        component.success_count += 1
        component.last_check = datetime.now(timezone.utc)
        
        if latency_ms is not None:
            component.metrics["last_latency_ms"] = latency_ms
        
        # Update status
        if component.status in (HealthStatus.UNKNOWN, HealthStatus.WARNING):
            component.status = HealthStatus.HEALTHY
            component.message = "Operating normally"
    
    def record_failure(
        self,
        component_id: str,
        error: str,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Record a failed operation"""
        component = self._components.get(component_id)
        if not component:
            return
        
        component.failure_count += 1
        component.last_check = datetime.now(timezone.utc)
        component.last_failure = datetime.now(timezone.utc)
        
        # Calculate failure rate
        total = component.success_count + component.failure_count
        failure_rate = component.failure_count / total if total > 0 else 0
        
        # Update status based on failure rate
        if failure_rate > 0.5:
            component.status = HealthStatus.CRITICAL
            component.message = f"High failure rate: {failure_rate:.1%}"
        elif failure_rate > 0.2:
            component.status = HealthStatus.WARNING
            component.message = f"Elevated failures: {failure_rate:.1%}"
        else:
            component.message = error
        
        if latency_ms is not None:
            component.metrics["last_latency_ms"] = latency_ms
        
        # Generate alert for critical failures
        if component.status == HealthStatus.CRITICAL:
            self._generate_alert(
                severity="critical",
                component=component.name,
                message=f"Component failure: {error}",
            )
    
    async def check_health(self) -> HealthMetrics:
        """Perform comprehensive health check"""
        self._metrics.timestamp = datetime.now(timezone.utc)
        
        # Check system resources
        await self._check_system_resources()
        
        # Check API latency
        await self._check_api_latency()
        
        # Update component metrics
        self._update_component_metrics()
        
        # Check overall status
        self._update_overall_status()
        
        return self._metrics
    
    async def _check_system_resources(self) -> None:
        """Check system resource usage"""
        try:
            # CPU
            self._metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory
            memory = psutil.virtual_memory()
            self._metrics.memory_percent = memory.percent
            self._metrics.memory_used_mb = memory.used / (1024 * 1024)
            
            # Disk
            disk = psutil.disk_usage("/")
            self._metrics.disk_percent = disk.percent
            
            # Update system component
            system = self._components.get("system")
            if system:
                system.metrics = {
                    "cpu_percent": self._metrics.cpu_percent,
                    "memory_percent": self._metrics.memory_percent,
                    "disk_percent": self._metrics.disk_percent,
                }
                
                # Set status based on thresholds
                if (self._metrics.cpu_percent > 90 or
                    self._metrics.memory_percent > 90 or
                    self._metrics.disk_percent > 90):
                    system.status = HealthStatus.CRITICAL
                    system.message = "High resource usage"
                elif (self._metrics.cpu_percent > 70 or
                      self._metrics.memory_percent > 70 or
                      self._metrics.disk_percent > 70):
                    system.status = HealthStatus.WARNING
                    system.message = "Elevated resource usage"
                else:
                    system.status = HealthStatus.HEALTHY
                    system.message = "Resources normal"
                
                system.last_check = datetime.now(timezone.utc)
            
            # Try GPU metrics (if available)
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    self._metrics.gpu_available = True
                    self._metrics.gpu_utilization = gpus[0].load * 100
                    self._metrics.gpu_memory_percent = gpus[0].memoryUtil * 100
            except ImportError:
                self._metrics.gpu_available = False
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
    
    async def _check_api_latency(self) -> None:
        """Check API latency"""
        import requests
        
        try:
            start = time.time()
            response = requests.get(
                "https://ws.derivws.com/websockets/v3",
                timeout=5,
            )
            latency = (time.time() - start) * 1000
            
            self._metrics.network_latency_ms = latency
            
            # Record in API component
            api = self._components.get("deriv_api")
            if api:
                api.metrics["latency_ms"] = latency
                api.last_check = datetime.now(timezone.utc)
                
                if latency > 1000:
                    api.status = HealthStatus.CRITICAL
                    api.message = f"High latency: {latency:.0f}ms"
                elif latency > 500:
                    api.status = HealthStatus.WARNING
                    api.message = f"Elevated latency: {latency:.0f}ms"
                else:
                    api.status = HealthStatus.HEALTHY
                    api.message = "API responsive"
                    
        except Exception as e:
            api = self._components.get("deriv_api")
            if api:
                api.status = HealthStatus.CRITICAL
                api.message = f"API unreachable: {str(e)}"
                api.last_failure = datetime.now(timezone.utc)
    
    def _update_component_metrics(self) -> None:
        """Update aggregated component metrics"""
        for component in self._components.values():
            total = component.success_count + component.failure_count
            if total > 0:
                component.metrics["success_rate"] = component.success_count / total
                component.metrics["failure_rate"] = component.failure_count / total
    
    def _update_overall_status(self) -> None:
        """Calculate overall system status"""
        statuses = [c.status for c in self._components.values()]
        
        if HealthStatus.CRITICAL in statuses:
            self._metrics.overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            self._metrics.overall_status = HealthStatus.WARNING
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            self._metrics.overall_status = HealthStatus.HEALTHY
        else:
            self._metrics.overall_status = HealthStatus.UNKNOWN
        
        self._metrics.components = self._components
    
    def record_confidence_prediction(
        self,
        predicted_confidence: float,
        actual_outcome: bool,
    ) -> None:
        """Record confidence prediction for calibration tracking"""
        # Update running metrics
        history_entry = {
            "predicted": predicted_confidence,
            "actual": 1.0 if actual_outcome else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self._calibration.calibration_history.append(history_entry)
        
        # Keep last 1000 entries
        if len(self._calibration.calibration_history) > 1000:
            self._calibration.calibration_history = (
                self._calibration.calibration_history[-1000:]
            )
        
        # Recalculate calibration error
        self._recalculate_calibration()
    
    def _recalculate_calibration(self) -> None:
        """Recalculate confidence calibration metrics"""
        history = self._calibration.calibration_history
        if not history:
            return
        
        # Calculate average predicted and actual
        avg_predicted = sum(h["predicted"] for h in history) / len(history)
        avg_actual = sum(h["actual"] for h in history) / len(history)
        
        self._calibration.predicted_confidence = avg_predicted
        self._calibration.actual_accuracy = avg_actual
        self._calibration.calibration_error = abs(avg_predicted - avg_actual)
        
        # Brier score
        brier = sum(
            (h["predicted"] / 100 - h["actual"]) ** 2
            for h in history
        ) / len(history)
        self._calibration.brier_score = brier
    
    def get_confidence_calibration(self) -> ConfidenceCalibration:
        """Get confidence calibration metrics"""
        return self._calibration
    
    def detect_model_drift(
        self,
        metric_name: str,
        current_value: float,
        window_size: int = 100,
        threshold: float = 0.2,
    ) -> Optional[ModelDrift]:
        """Detect model drift in a metric"""
        if metric_name not in self._drift_detectors:
            self._drift_detectors[metric_name] = deque(maxlen=window_size)
        
        self._drift_detectors[metric_name].append(current_value)
        
        history = list(self._drift_detectors[metric_name])
        
        if len(history) < window_size:
            return None
        
        # Calculate baseline (first half) and current (second half)
        baseline = sum(history[:window_size // 2]) / (window_size // 2)
        current = sum(history[window_size // 2:]) / (window_size // 2)
        
        if baseline == 0:
            return None
        
        drift_percent = abs(current - baseline) / abs(baseline)
        is_significant = drift_percent > threshold
        
        drift = ModelDrift(
            metric_name=metric_name,
            baseline_value=baseline,
            current_value=current,
            drift_percent=drift_percent * 100,
            is_significant=is_significant,
        )
        
        if is_significant:
            self._generate_alert(
                severity="warning",
                component="model",
                message=f"Model drift detected in {metric_name}: {drift_percent*100:.1f}% change",
            )
        
        return drift
    
    def _generate_alert(
        self,
        severity: str,
        component: str,
        message: str,
    ) -> None:
        """Generate an alert"""
        alert = {
            "id": len(self._alerts),
            "severity": severity,
            "component": component,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self._alerts.append(alert)
        self._metrics.active_alerts.append(alert)
        
        # Keep only last 10 alerts in metrics
        if len(self._metrics.active_alerts) > 10:
            self._metrics.active_alerts = self._metrics.active_alerts[-10:]
        
        # Fire callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_alerts(
        self,
        since: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        alerts = list(self._alerts)
        
        if since:
            alerts = [
                a for a in alerts
                if datetime.fromisoformat(a["timestamp"]) >= since
            ]
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        return alerts[-limit:]
    
    def on_alert(self, callback: Callable) -> None:
        """Register an alert callback"""
        self._alert_callbacks.append(callback)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for dashboard"""
        return {
            "status": self._metrics.overall_status.value,
            "timestamp": self._metrics.timestamp.isoformat(),
            "resources": {
                "cpu_percent": self._metrics.cpu_percent,
                "memory_percent": self._metrics.memory_percent,
                "disk_percent": self._metrics.disk_percent,
            },
            "components": {
                cid: {
                    "status": c.status.value,
                    "message": c.message,
                    "success_rate": c.success_count / max(c.success_count + c.failure_count, 1),
                }
                for cid, c in self._components.items()
            },
            "calibration": {
                "calibration_error": self._calibration.calibration_error,
                "brier_score": self._calibration.brier_score,
            },
            "recent_alerts": len(self._alerts),
        }
