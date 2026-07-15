"""
Governance Manager
=================

Central governance orchestration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .audit_record import AuditLogger, AuditRecord, DecisionType
from .immutable_log import ImmutableAuditLog, LogEntryType
from .dashboards import (
    CalibrationDriftDashboard,
    ModelHealthDashboard,
    StrategyHealthDashboard,
    DeploymentHistoryDashboard,
    ConfigurationChangesDashboard
)
from .workflows import ApprovalWorkflow, ApprovalType, ApprovalStatus

logger = logging.getLogger(__name__)


class GovernanceEvent(Enum):
    """Types of governance events"""
    AUDIT_RECORD_CREATED = "audit_record_created"
    CALIBRATION_DRIFT_DETECTED = "calibration_drift_detected"
    MODEL_DEGRADING = "model_degrading"
    STRATEGY_DEPLOYED = "strategy_deployed"
    STRATEGY_ROLLED_BACK = "strategy_rolled_back"
    CONFIG_CHANGED = "config_changed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"


@dataclass
class GovernanceConfig:
    """Governance configuration"""
    enable_audit_logging: bool = True
    enable_immutable_log: bool = True
    enable_calibration_monitoring: bool = True
    enable_model_health_monitoring: bool = True
    enable_strategy_health_monitoring: bool = True
    audit_retention_days: int = 365
    calibration_drift_threshold: float = 0.1
    model_degradation_threshold: float = 0.15


class GovernanceManager:
    """
    Central governance orchestration.
    
    Coordinates all governance components:
    - Audit logging
    - Immutable logs
    - Dashboards
    - Approval workflows
    """
    
    def __init__(
        self,
        config: Optional[GovernanceConfig] = None,
        db_path: str = "data/governance/governance.db"
    ):
        self.config = config or GovernanceConfig()
        self.db_path = db_path
        
        # Initialize components
        self.audit_logger = AuditLogger(db_path=f"{db_path}/audit.db")
        self.immutable_log = ImmutableAuditLog(db_path=f"{db_path}/immutable.db")
        
        # Dashboards
        self.calibration_dashboard = CalibrationDriftDashboard()
        self.model_health_dashboard = ModelHealthDashboard()
        self.strategy_health_dashboard = StrategyHealthDashboard()
        self.deployment_dashboard = DeploymentHistoryDashboard()
        self.config_changes_dashboard = ConfigurationChangesDashboard()
        
        # Workflows
        self.approval_workflow = ApprovalWorkflow(db_path=f"{db_path}/approvals.db")
        
        # Event listeners
        self._event_listeners: Dict[GovernanceEvent, List[callable]] = {}
        
        # Config change listener
        self.config_changes_dashboard.add_change_listener(
            self._on_config_change
        )
        
        logger.info("Governance Manager initialized")
    
    # ========== Audit Logging ==========
    
    def log_decision(self, record: AuditRecord) -> str:
        """
        Log an automated decision.
        
        Returns hash of the logged record.
        """
        if not self.config.enable_audit_logging:
            return ""
        
        # Get previous hash for chaining
        chain = self.audit_logger.get_chain_integrity()
        prev_hash = chain.get("last_hash")
        
        # Log to audit system
        record_hash = self.audit_logger.log(record, prev_hash)
        
        # Also log to immutable log
        if self.config.enable_immutable_log:
            self.immutable_log.append(
                LogEntryType.AUDIT_RECORD,
                data={
                    "record_id": record.record_id,
                    "decision_type": record.decision_type.value,
                    "confidence": record.confidence,
                    "action": record.action_taken
                }
            )
        
        # Check calibration drift
        if record.decision_type == DecisionType.TRADE_ENTRY:
            self._check_calibration(record)
        
        # Emit event
        self._emit_event(GovernanceEvent.AUDIT_RECORD_CREATED, record.to_dict())
        
        return record_hash
    
    def _check_calibration(self, record: AuditRecord) -> None:
        """Check for calibration drift after decisions"""
        if not self.config.enable_calibration_monitoring:
            return
        
        # Record calibration
        self.calibration_dashboard.record(
            predicted=record.confidence,
            actual=0.0  # Will be updated with actual outcome
        )
        
        # Check status
        status = self.calibration_dashboard.get_status()
        if status.value in ["drifted", "significantly_drifted"]:
            self._emit_event(
                GovernanceEvent.CALIBRATION_DRIFT_DETECTED,
                {"status": status.value}
            )
    
    def get_audit_records(
        self,
        decision_type: Optional[DecisionType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Get audit records"""
        return self.audit_logger.get_records(
            decision_type=decision_type,
            since=since,
            limit=limit
        )
    
    # ========== Immutable Log ==========
    
    def log_event(
        self,
        event_type: LogEntryType,
        data: Dict[str, Any],
        signature: Optional[str] = None
    ) -> None:
        """Log an event to immutable log"""
        if self.config.enable_immutable_log:
            self.immutable_log.append(event_type, data, signature)
    
    def verify_logs(self) -> Dict[str, Any]:
        """Verify integrity of all logs"""
        audit_integrity = self.audit_logger.get_chain_integrity()
        immutable_integrity = self.immutable_log.verify_integrity()
        
        return {
            "audit_log": audit_integrity,
            "immutable_log": immutable_integrity,
            "all_valid": audit_integrity.get("valid", False) and immutable_integrity.get("valid", False)
        }
    
    # ========== Dashboards ==========
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary of all dashboards"""
        return {
            "calibration": self.calibration_dashboard.get_dashboard_data(),
            "model_health": self.model_health_dashboard.get_dashboard_data(),
            "strategy_health": self.strategy_health_dashboard.get_dashboard_data(),
            "deployments": self.deployment_dashboard.get_dashboard_data(),
            "config_changes": self.config_changes_dashboard.get_dashboard_data()
        }
    
    # ========== Configuration Changes ==========
    
    def _on_config_change(self, change: Any) -> None:
        """Handle configuration change"""
        # Log to immutable log
        self.log_event(
            LogEntryType.CONFIG_CHANGE,
            {
                "config_key": change.config_key,
                "old_value": str(change.old_value),
                "new_value": str(change.new_value),
                "changed_by": change.changed_by
            }
        )
        
        # Emit event
        self._emit_event(GovernanceEvent.CONFIG_CHANGED, {
            "config_key": change.config_key,
            "changed_by": change.changed_by
        })
    
    # ========== Deployments ==========
    
    def record_deployment(
        self,
        version: str,
        component: str,
        status: str,
        deployed_by: str,
        environment: str,
        changes: List[str]
    ) -> None:
        """Record a deployment"""
        record = self.deployment_dashboard.record_deployment(
            version=version,
            component=component,
            status=status,
            deployed_by=deployed_by,
            environment=environment,
            changes=changes
        )
        
        # Log to immutable log
        self.log_event(
            LogEntryType.DEPLOYMENT,
            {
                "deployment_id": record.deployment_id,
                "version": version,
                "component": component,
                "status": status,
                "deployed_by": deployed_by,
                "environment": environment
            }
        )
        
        # Emit event
        event = GovernanceEvent.STRATEGY_DEPLOYED if status == "deployed" else GovernanceEvent.STRATEGY_ROLLED_BACK
        self._emit_event(event, {
            "deployment_id": record.deployment_id,
            "version": version
        })
    
    def record_rollback(
        self,
        deployment_id: str,
        reason: str
    ) -> None:
        """Record a deployment rollback"""
        self.deployment_dashboard.record_rollback(deployment_id, reason)
        
        self._emit_event(GovernanceEvent.STRATEGY_ROLLED_BACK, {
            "deployment_id": deployment_id,
            "reason": reason
        })
    
    # ========== Approvals ==========
    
    def request_approval(
        self,
        approval_type: ApprovalType,
        title: str,
        description: str,
        requested_by: str,
        account_id: str,
        target_id: str,
        target_version: str,
        changes_summary: List[str],
        performance_metrics: Optional[Dict[str, float]] = None,
        risk_metrics: Optional[Dict[str, float]] = None,
        test_results: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create an approval request"""
        request = self.approval_workflow.create_request(
            approval_type=approval_type,
            title=title,
            description=description,
            requested_by=requested_by,
            account_id=account_id,
            target_id=target_id,
            target_version=target_version,
            changes_summary=changes_summary,
            metadata={
                "performance_metrics": performance_metrics or {},
                "risk_metrics": risk_metrics or {},
                "test_results": test_results or {}
            }
        )
        
        # Log to immutable log
        self.log_event(
            LogEntryType.APPROVAL,
            {
                "request_id": request.request_id,
                "approval_type": approval_type.value,
                "title": title,
                "status": request.status.value,
                "required_level": request.required_level.value
            }
        )
        
        # Emit event
        self._emit_event(GovernanceEvent.APPROVAL_REQUESTED, {
            "request_id": request.request_id,
            "approval_type": approval_type.value
        })
        
        return request
    
    def approve(
        self,
        request_id: str,
        approver: str,
        comments: str = "",
        conditions: Optional[List[str]] = None
    ) -> bool:
        """Approve a request"""
        success = self.approval_workflow.approve(
            request_id=request_id,
            approver=approver,
            comments=comments,
            conditions=conditions
        )
        
        if success:
            self.log_event(
                LogEntryType.APPROVAL,
                {
                    "request_id": request_id,
                    "decision": "approved",
                    "approver": approver
                }
            )
            self._emit_event(GovernanceEvent.APPROVAL_GRANTED, {
                "request_id": request_id,
                "approver": approver
            })
        
        return success
    
    def reject_approval(
        self,
        request_id: str,
        approver: str,
        comments: str
    ) -> bool:
        """Reject a request"""
        success = self.approval_workflow.reject(
            request_id=request_id,
            approver=approver,
            comments=comments
        )
        
        if success:
            self.log_event(
                LogEntryType.APPROVAL,
                {
                    "request_id": request_id,
                    "decision": "rejected",
                    "approver": approver,
                    "reason": comments
                }
            )
            self._emit_event(GovernanceEvent.APPROVAL_DENIED, {
                "request_id": request_id,
                "approver": approver
            })
        
        return success
    
    def get_pending_approvals(self) -> List[Any]:
        """Get all pending approval requests"""
        return self.approval_workflow.get_pending_requests()
    
    # ========== Event System ==========
    
    def add_event_listener(
        self,
        event: GovernanceEvent,
        listener: callable
    ) -> None:
        """Add an event listener"""
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(listener)
    
    def _emit_event(
        self,
        event: GovernanceEvent,
        data: Dict[str, Any]
    ) -> None:
        """Emit a governance event"""
        listeners = self._event_listeners.get(event, [])
        for listener in listeners:
            try:
                listener(event, data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
    
    # ========== Status ==========
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall governance status"""
        return {
            "audit_log_entries": len(self.audit_logger.get_records(limit=1)) if hasattr(self.audit_logger, 'get_records') else 0,
            "immutable_log_entries": self.immutable_log.verify_integrity().get("entries", 0),
            "pending_approvals": len(self.approval_workflow.get_pending_requests()),
            "dashboards": self.get_dashboard_summary(),
            "log_integrity": self.verify_logs(),
            "configuration": {
                "enable_audit_logging": self.config.enable_audit_logging,
                "enable_immutable_log": self.config.enable_immutable_log,
                "calibration_threshold": self.config.calibration_drift_threshold
            }
        }
