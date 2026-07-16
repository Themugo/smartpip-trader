"""
Audit Logging System
=================

Comprehensive audit logging for governance.
"""

import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditLog:
    """Audit log entry"""
    log_id: str
    timestamp: float
    action: str
    actor: str
    actor_type: str  # "user", "system", "api"
    resource_type: str  # "strategy", "approval", "deployment"
    resource_id: str
    changes: Dict[str, Any] = field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    previous_hash: Optional[str] = None
    hash: str = ""
    
    def calculate_hash(self) -> str:
        """Calculate entry hash for integrity"""
        content = {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()


class AuditLogger:
    """
    Comprehensive audit logging system.
    """
    
    def __init__(self, retention_days: int = 365):
        self._logs: List[AuditLog] = []
        self._retention_days = retention_days
        self._last_hash: Optional[str] = None
    
    def log(
        self,
        action: str,
        actor: str,
        actor_type: str = "user",
        resource_type: str = "",
        resource_id: str = "",
        changes: Optional[Dict[str, Any]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """Log an audit entry"""
        log = AuditLog(
            log_id=self._generate_id(),
            timestamp=time.time(),
            action=action,
            actor=actor,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            previous_hash=self._last_hash,
        )
        log.hash = log.calculate_hash()
        
        self._logs.append(log)
        self._last_hash = log.hash
        
        logger.info(f"Audit log: {action} by {actor} on {resource_type}/{resource_id}")
        return log
    
    def log_strategy_created(
        self,
        strategy_id: str,
        name: str,
        created_by: str,
        **kwargs
    ) -> AuditLog:
        """Log strategy creation"""
        return self.log(
            action="strategy.created",
            actor=created_by,
            actor_type="user",
            resource_type="strategy",
            resource_id=strategy_id,
            changes={"name": name, **kwargs}
        )
    
    def log_strategy_stage_transition(
        self,
        strategy_id: str,
        from_stage: str,
        to_stage: str,
        triggered_by: str,
        reason: str = ""
    ) -> AuditLog:
        """Log strategy stage transition"""
        return self.log(
            action="strategy.stage_transition",
            actor=triggered_by,
            actor_type="user",
            resource_type="strategy",
            resource_id=strategy_id,
            changes={
                "from_stage": from_stage,
                "to_stage": to_stage,
                "reason": reason
            }
        )
    
    def log_deployment(
        self,
        deployment_id: str,
        strategy_id: str,
        version: str,
        environment: str,
        deployed_by: str,
        status: str
    ) -> AuditLog:
        """Log deployment"""
        return self.log(
            action="deployment.created",
            actor=deployed_by,
            actor_type="user",
            resource_type="deployment",
            resource_id=deployment_id,
            changes={
                "strategy_id": strategy_id,
                "version": version,
                "environment": environment,
                "status": status
            }
        )
    
    def log_rollback(
        self,
        rollback_id: str,
        strategy_id: str,
        from_version: str,
        to_version: str,
        reason: str,
        initiated_by: str
    ) -> AuditLog:
        """Log rollback"""
        return self.log(
            action="deployment.rollback",
            actor=initiated_by,
            actor_type="user",
            resource_type="rollback",
            resource_id=rollback_id,
            changes={
                "strategy_id": strategy_id,
                "from_version": from_version,
                "to_version": to_version,
                "reason": reason
            }
        )
    
    def log_approval_request(
        self,
        request_id: str,
        approval_type: str,
        title: str,
        requested_by: str,
        target_id: str
    ) -> AuditLog:
        """Log approval request"""
        return self.log(
            action="approval.requested",
            actor=requested_by,
            actor_type="user",
            resource_type="approval",
            resource_id=request_id,
            changes={
                "approval_type": approval_type,
                "title": title,
                "target_id": target_id
            }
        )
    
    def log_approval_decision(
        self,
        request_id: str,
        decision: str,
        approver: str,
        comments: str = ""
    ) -> AuditLog:
        """Log approval decision"""
        return self.log(
            action=f"approval.{decision}",
            actor=approver,
            actor_type="user",
            resource_type="approval",
            resource_id=request_id,
            changes={
                "decision": decision,
                "comments": comments
            }
        )
    
    def log_compliance_evidence(
        self,
        evidence_id: str,
        strategy_id: str,
        evidence_type: str,
        requirement: str,
        submitted_by: str
    ) -> AuditLog:
        """Log compliance evidence"""
        return self.log(
            action="compliance.evidence_added",
            actor=submitted_by,
            actor_type="user",
            resource_type="evidence",
            resource_id=evidence_id,
            changes={
                "strategy_id": strategy_id,
                "evidence_type": evidence_type,
                "requirement": requirement
            }
        )
    
    def log_compliance_verification(
        self,
        evidence_id: str,
        verified_by: str
    ) -> AuditLog:
        """Log compliance verification"""
        return self.log(
            action="compliance.verified",
            actor=verified_by,
            actor_type="user",
            resource_type="evidence",
            resource_id=evidence_id
        )
    
    def log_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: str
    ) -> AuditLog:
        """Log configuration change"""
        return self.log(
            action="config.changed",
            actor=changed_by,
            actor_type="user",
            resource_type="config",
            resource_id=config_key,
            previous_state={"value": old_value},
            new_state={"value": new_value},
            changes={
                "key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )
    
    def log_decision(
        self,
        decision_id: str,
        decision_type: str,
        action: str,
        confidence: float,
        actor: str = "system"
    ) -> AuditLog:
        """Log trading decision"""
        return self.log(
            action=f"decision.{decision_type}",
            actor=actor,
            actor_type="system",
            resource_type="decision",
            resource_id=decision_id,
            changes={
                "action": action,
                "confidence": confidence
            }
        )
    
    def get_logs(
        self,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Query audit logs"""
        results = self._logs
        
        if action:
            results = [l for l in results if action in l.action]
        if actor:
            results = [l for l in results if l.actor == actor]
        if resource_type:
            results = [l for l in results if l.resource_type == resource_type]
        if resource_id:
            results = [l for l in results if l.resource_id == resource_id]
        if since:
            results = [l for l in results if l.timestamp >= since]
        if until:
            results = [l for l in results if l.timestamp <= until]
        
        # Sort by timestamp descending and limit
        results = sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return results
    
    def get_strategy_history(self, strategy_id: str) -> List[AuditLog]:
        """Get all audit logs for a strategy"""
        return [
            l for l in self._logs
            if l.resource_id == strategy_id or
            (l.changes.get("strategy_id") == strategy_id)
        ]
    
    def get_deployment_history(self, strategy_id: str) -> List[AuditLog]:
        """Get deployment history for a strategy"""
        return [
            l for l in self._logs
            if "deployment" in l.action and
            (l.resource_id == strategy_id or
             l.changes.get("strategy_id") == strategy_id)
        ]
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify audit log integrity"""
        valid = True
        errors = []
        current_hash = None
        
        for i, log in enumerate(self._logs):
            expected_hash = log.calculate_hash()
            if log.hash != expected_hash:
                valid = False
                errors.append(f"Log {i}: hash mismatch")
            
            if log.previous_hash != current_hash:
                valid = False
                errors.append(f"Log {i}: chain broken")
            
            current_hash = log.hash
        
        return {
            "valid": valid,
            "total_entries": len(self._logs),
            "errors": errors,
        }
    
    def generate_report(
        self,
        since: Optional[float] = None,
        until: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate audit report"""
        logs = self.get_logs(since=since, until=until, limit=10000)
        
        # Count by action
        action_counts: Dict[str, int] = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Count by actor
        actor_counts: Dict[str, int] = {}
        for log in logs:
            actor_counts[log.actor] = actor_counts.get(log.actor, 0) + 1
        
        # Count by resource type
        resource_counts: Dict[str, int] = {}
        for log in logs:
            resource_counts[log.resource_type] = resource_counts.get(log.resource_type, 0) + 1
        
        return {
            "period": {
                "since": since,
                "until": until,
            },
            "total_entries": len(logs),
            "by_action": action_counts,
            "by_actor": actor_counts,
            "by_resource_type": resource_counts,
            "integrity": self.verify_integrity(),
        }
    
    def export_logs(
        self,
        format: str = "json",
        since: Optional[float] = None,
        until: Optional[float] = None
    ) -> str:
        """Export logs in specified format"""
        logs = self.get_logs(since=since, until=until, limit=10000)
        
        if format == "json":
            return json.dumps([
                {
                    "log_id": l.log_id,
                    "timestamp": l.timestamp,
                    "action": l.action,
                    "actor": l.actor,
                    "resource_type": l.resource_type,
                    "resource_id": l.resource_id,
                    "changes": l.changes,
                }
                for l in logs
            ], indent=2)
        
        elif format == "csv":
            lines = ["timestamp,action,actor,resource_type,resource_id"]
            for l in logs:
                lines.append(
                    f"{l.timestamp},{l.action},{l.actor},{l.resource_type},{l.resource_id}"
                )
            return "\n".join(lines)
        
        return ""
    
    def cleanup_old_logs(self) -> int:
        """Remove logs older than retention period"""
        cutoff = time.time() - (self._retention_days * 24 * 3600)
        old_count = len(self._logs)
        self._logs = [l for l in self._logs if l.timestamp >= cutoff]
        removed = old_count - len(self._logs)
        
        if removed > 0:
            logger.info(f"Removed {removed} audit logs older than {self._retention_days} days")
        
        return removed
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
