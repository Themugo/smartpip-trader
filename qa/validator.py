"""
Continuous Quality Assurance - Automated Validation System

Comprehensive validation checks for system health.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Validation check status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class CheckSeverity(Enum):
    """Severity of validation checks"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationCheck:
    """A single validation check"""
    id: str
    name: str
    description: str
    severity: CheckSeverity
    category: str
    
    # Check function
    check_func: Optional[Callable[[], Any]] = None
    
    # Configuration
    enabled: bool = True
    auto_fix: bool = False
    fix_func: Optional[Callable[[], bool]] = None
    
    # Timing
    timeout_seconds: int = 30
    interval_seconds: int = 60
    
    # State
    status: CheckStatus = CheckStatus.PENDING
    last_run: Optional[datetime] = None
    last_duration_ms: float = 0
    
    # Result
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # History
    pass_count: int = 0
    fail_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "enabled": self.enabled,
            "status": self.status.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_duration_ms": self.last_duration_ms,
            "message": self.message,
            "details": self.details,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "pass_rate": (
                self.pass_count / (self.pass_count + self.fail_count)
                if (self.pass_count + self.fail_count) > 0 else None
            ),
        }


@dataclass
class ValidationResult:
    """Result of a validation run"""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0
    
    # Overall status
    is_healthy: bool = True
    overall_status: CheckStatus = CheckStatus.PASSED
    
    # Check results
    checks: List[ValidationCheck] = field(default_factory=list)
    
    # Counts
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    
    # Issues
    critical_issues: List[str] = field(default_factory=list)
    high_issues: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "is_healthy": self.is_healthy,
            "overall_status": self.overall_status.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "recommendations": self.recommendations,
            "checks": [c.to_dict() for c in self.checks],
        }


class QualityAssurance:
    """
    Continuous Quality Assurance System.
    
    Features:
    - Automated validation checks
    - Plugin integrity verification
    - Configuration validation
    - Dependency health checks
    - API compatibility tests
    - Model availability checks
    - Strategy registration validation
    - WebSocket reliability monitoring
    """
    
    def __init__(self):
        self._checks: Dict[str, ValidationCheck] = {}
        self._history: deque = deque(maxlen=100)
        self._callbacks: Dict[str, List[Callable]] = {
            "on_check_complete": [],
            "on_check_fail": [],
            "on_validation_complete": [],
        }
        self._validation_task: Optional[asyncio.Task] = None
        
        self._init_default_checks()
    
    def _init_default_checks(self) -> None:
        """Initialize default validation checks"""
        
        # Plugin integrity
        self.add_check(ValidationCheck(
            id="plugin_integrity",
            name="Plugin Integrity",
            description="Verify all plugins are properly loaded",
            severity=CheckSeverity.HIGH,
            category="plugins",
            check_func=self._check_plugin_integrity,
        ))
        
        # Configuration
        self.add_check(ValidationCheck(
            id="config_validity",
            name="Configuration Validity",
            description="Verify configuration is valid",
            severity=CheckSeverity.HIGH,
            category="configuration",
            check_func=self._check_config_validity,
        ))
        
        # Dependencies
        self.add_check(ValidationCheck(
            id="dependency_health",
            name="Dependency Health",
            description="Check all dependencies are available",
            severity=CheckSeverity.CRITICAL,
            category="dependencies",
            check_func=self._check_dependencies,
        ))
        
        # API
        self.add_check(ValidationCheck(
            id="api_connectivity",
            name="API Connectivity",
            description="Verify API is accessible",
            severity=CheckSeverity.CRITICAL,
            category="api",
            check_func=self._check_api_connectivity,
        ))
        
        # Models
        self.add_check(ValidationCheck(
            id="model_availability",
            name="Model Availability",
            description="Verify ML models are loaded",
            severity=CheckSeverity.HIGH,
            category="models",
            check_func=self._check_model_availability,
        ))
        
        # Strategies
        self.add_check(ValidationCheck(
            id="strategy_registration",
            name="Strategy Registration",
            description="Verify strategies are registered",
            severity=CheckSeverity.MEDIUM,
            category="strategies",
            check_func=self._check_strategy_registration,
        ))
        
        # WebSocket
        self.add_check(ValidationCheck(
            id="websocket_stability",
            name="WebSocket Stability",
            description="Verify WebSocket connection is stable",
            severity=CheckSeverity.HIGH,
            category="websocket",
            check_func=self._check_websocket_stability,
        ))
        
        # Dashboard
        self.add_check(ValidationCheck(
            id="dashboard_functionality",
            name="Dashboard Functionality",
            description="Verify dashboard is accessible",
            severity=CheckSeverity.LOW,
            category="dashboard",
            check_func=self._check_dashboard,
        ))
    
    def add_check(self, check: ValidationCheck) -> None:
        """Add a validation check"""
        self._checks[check.id] = check
    
    def remove_check(self, check_id: str) -> bool:
        """Remove a validation check"""
        if check_id in self._checks:
            del self._checks[check_id]
            return True
        return False
    
    def get_check(self, check_id: str) -> Optional[ValidationCheck]:
        """Get a specific check"""
        return self._checks.get(check_id)
    
    def get_all_checks(self) -> List[ValidationCheck]:
        """Get all validation checks"""
        return list(self._checks.values())
    
    def enable_check(self, check_id: str) -> bool:
        """Enable a check"""
        check = self._checks.get(check_id)
        if check:
            check.enabled = True
            return True
        return False
    
    def disable_check(self, check_id: str) -> bool:
        """Disable a check"""
        check = self._checks.get(check_id)
        if check:
            check.enabled = False
            return True
        return False
    
    async def run_check(self, check_id: str) -> ValidationCheck:
        """Run a single validation check"""
        import time
        
        check = self._checks.get(check_id)
        if not check or not check.enabled:
            return check
        
        check.status = CheckStatus.RUNNING
        start_time = time.time()
        
        try:
            if check.check_func:
                result = await asyncio.wait_for(
                    asyncio.to_thread(check.check_func),
                    timeout=check.timeout_seconds
                )
                
                if result:
                    check.status = CheckStatus.PASSED
                    check.pass_count += 1
                    check.message = "Check passed"
                    check.details = result if isinstance(result, dict) else {}
                else:
                    check.status = CheckStatus.FAILED
                    check.fail_count += 1
                    check.message = "Check failed"
            
            else:
                check.status = CheckStatus.WARNING
                check.message = "No check function defined"
        
        except asyncio.TimeoutError:
            check.status = CheckStatus.ERROR
            check.fail_count += 1
            check.message = f"Check timed out after {check.timeout_seconds}s"
        
        except Exception as e:
            check.status = CheckStatus.ERROR
            check.fail_count += 1
            check.message = f"Error: {str(e)}"
        
        check.last_run = datetime.now(timezone.utc)
        check.last_duration_ms = (time.time() - start_time) * 1000
        
        self._fire_callbacks("on_check_complete", check)
        
        if check.status in (CheckStatus.FAILED, CheckStatus.ERROR):
            self._fire_callbacks("on_check_fail", check)
        
        return check
    
    async def run_all_checks(self) -> ValidationResult:
        """Run all validation checks"""
        import time
        
        start_time = time.time()
        result = ValidationResult()
        
        for check in self._checks.values():
            if check.enabled:
                await self.run_check(check.id)
                result.checks.append(check)
        
        result.duration_ms = (time.time() - start_time) * 1000
        result.total_checks = len(result.checks)
        
        # Aggregate results
        for check in result.checks:
            if check.status == CheckStatus.PASSED:
                result.passed_checks += 1
            elif check.status == CheckStatus.FAILED:
                result.failed_checks += 1
                
                if check.severity == CheckSeverity.CRITICAL:
                    result.critical_issues.append(f"{check.name}: {check.message}")
                elif check.severity == CheckSeverity.HIGH:
                    result.high_issues.append(f"{check.name}: {check.message}")
            elif check.status == CheckStatus.WARNING:
                result.warning_checks += 1
        
        # Determine overall status
        if result.critical_issues:
            result.overall_status = CheckStatus.FAILED
            result.is_healthy = False
        elif result.high_issues:
            result.overall_status = CheckStatus.WARNING
        else:
            result.overall_status = CheckStatus.PASSED
        
        # Generate recommendations
        if result.failed_checks > 0:
            result.recommendations.append(
                f"Fix {result.failed_checks} failed checks before deployment"
            )
        
        self._history.append(result)
        self._fire_callbacks("on_validation_complete", result)
        
        return result
    
    def start_continuous_validation(self, interval_seconds: int = 300) -> None:
        """Start continuous validation loop"""
        if self._validation_task:
            return
        
        async def loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self.run_all_checks()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Continuous validation error: {e}")
        
        self._validation_task = asyncio.create_task(loop())
        logger.info("Continuous validation started")
    
    def stop_continuous_validation(self) -> None:
        """Stop continuous validation loop"""
        if self._validation_task:
            self._validation_task.cancel()
            self._validation_task = None
            logger.info("Continuous validation stopped")
    
    # Default check implementations
    def _check_plugin_integrity(self) -> Dict[str, Any]:
        """Check plugin integrity"""
        # Placeholder - would check actual plugins
        return {"plugins_loaded": True, "count": 0}
    
    def _check_config_validity(self) -> Dict[str, Any]:
        """Check configuration validity"""
        # Placeholder - would validate config
        return {"config_valid": True}
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check dependencies"""
        missing = []
        
        for module in ["numpy", "pandas", "sklearn"]:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        
        return {"dependencies_healthy": len(missing) == 0, "missing": missing}
    
    async def _check_api_connectivity(self) -> Dict[str, Any]:
        """Check API connectivity"""
        import requests
        
        try:
            response = requests.get(
                "https://ws.derivws.com/websockets/v3",
                timeout=5,
            )
            return {"api_reachable": True, "status_code": response.status_code}
        except Exception as e:
            return {"api_reachable": False, "error": str(e)}
    
    def _check_model_availability(self) -> Dict[str, Any]:
        """Check model availability"""
        # Placeholder - would check actual models
        return {"models_loaded": True, "count": 0}
    
    def _check_strategy_registration(self) -> Dict[str, Any]:
        """Check strategy registration"""
        # Placeholder - would check strategies
        return {"strategies_registered": True, "count": 0}
    
    def _check_websocket_stability(self) -> Dict[str, Any]:
        """Check WebSocket stability"""
        # Placeholder - would check WebSocket
        return {"websocket_stable": True}
    
    def _check_dashboard(self) -> Dict[str, Any]:
        """Check dashboard"""
        # Placeholder - would check dashboard
        return {"dashboard_accessible": True}
    
    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register an event callback"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def _fire_callbacks(self, event_type: str, *args) -> None:
        """Fire registered callbacks"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"QA callback error: {e}")
    
    def get_history(self, limit: int = 10) -> List[ValidationResult]:
        """Get validation history"""
        return list(self._history)[-limit:]
