"""
Recovery Management
==================

Automatic recovery and incident response.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Recovery action types"""
    RESTART = "restart"
    ROLLBACK = "rollback"
    SWITCHOVER = "switchover"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NOTIFY = "notify"
    ESCALATE = "escalate"
    MANUAL = "manual"


@dataclass
class RecoveryPolicy:
    """Policy for automated recovery"""
    name: str
    condition: str  # e.g., "failure_count > 5"
    action: RecoveryAction
    max_attempts: int = 3
    cooldown_seconds: float = 60.0
    
    # Parameters
    action_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryRecord:
    """Record of a recovery action"""
    record_id: str
    policy_name: str
    action: RecoveryAction
    timestamp: float
    success: bool
    attempts: int = 1
    error: str = ""
    duration_seconds: float = 0


class RecoveryManager:
    """
    Manages automatic recovery actions.
    
    Monitors system health and executes
    recovery policies when conditions are met.
    """
    
    def __init__(self):
        self._policies: Dict[str, RecoveryPolicy] = {}
        self._records: List[RecoveryRecord] = []
        self._cooldowns: Dict[str, float] = {}
        
        # Action handlers
        self._handlers: Dict[RecoveryAction, Callable] = {}
        
        # Initialize default policies
        self._init_default_policies()
    
    def _init_default_policies(self) -> None:
        """Initialize default recovery policies"""
        self.add_policy(RecoveryPolicy(
            name="restart_on_failure",
            condition="failure_count > 5",
            action=RecoveryAction.RESTART,
            cooldown_seconds=300,
        ))
        
        self.add_policy(RecoveryPolicy(
            name="scale_on_degraded",
            condition="latency_p95 > 1000",
            action=RecoveryAction.SCALE_UP,
            cooldown_seconds=600,
        ))
        
        self.add_policy(RecoveryPolicy(
            name="escalate_on_critical",
            condition="health_status == 'unhealthy'",
            action=RecoveryAction.ESCALATE,
            cooldown_seconds=60,
        ))
    
    def add_policy(self, policy: RecoveryPolicy) -> None:
        """Add a recovery policy"""
        self._policies[policy.name] = policy
        logger.info(f"Added recovery policy: {policy.name}")
    
    def remove_policy(self, name: str) -> bool:
        """Remove a recovery policy"""
        return self._policies.pop(name, None) is not None
    
    def register_handler(
        self,
        action: RecoveryAction,
        handler: Callable[[Dict], bool]
    ) -> None:
        """Register a recovery action handler"""
        self._handlers[action] = handler
    
    def execute_recovery(
        self,
        policy_name: str,
        context: Dict[str, Any]
    ) -> RecoveryRecord:
        """
        Execute recovery for a policy.
        
        Returns a record of the recovery attempt.
        """
        if policy_name not in self._policies:
            raise ValueError(f"Unknown policy: {policy_name}")
        
        policy = self._policies[policy_name]
        
        # Check cooldown
        if self._is_in_cooldown(policy_name):
            logger.info(f"Policy {policy_name} is in cooldown")
            return RecoveryRecord(
                record_id="",
                policy_name=policy_name,
                action=policy.action,
                timestamp=time.time(),
                success=False,
                error="In cooldown",
            )
        
        # Execute action
        start_time = time.time()
        record = RecoveryRecord(
            record_id=f"rec_{int(time.time())}",
            policy_name=policy_name,
            action=policy.action,
            timestamp=start_time,
            success=False,
        )
        
        try:
            handler = self._handlers.get(policy.action)
            if handler:
                record.success = handler(policy.action_params)
            else:
                logger.warning(f"No handler for action: {policy.action}")
                record.success = False
                record.error = "No handler registered"
            
        except Exception as e:
            record.error = str(e)
            logger.error(f"Recovery failed: {e}")
        
        record.duration_seconds = time.time() - start_time
        self._records.append(record)
        
        # Update cooldown
        if record.success:
            self._cooldowns[policy_name] = time.time()
        
        return record
    
    def _is_in_cooldown(self, policy_name: str) -> bool:
        """Check if policy is in cooldown period"""
        if policy_name not in self._cooldowns:
            return False
        
        policy = self._policies.get(policy_name)
        if not policy:
            return False
        
        elapsed = time.time() - self._cooldowns[policy_name]
        return elapsed < policy.cooldown_seconds
    
    def evaluate_policies(
        self,
        metrics: Dict[str, Any]
    ) -> List[RecoveryRecord]:
        """Evaluate all policies against current metrics"""
        records = []
        
        for name, policy in self._policies.items():
            if self._is_in_cooldown(name):
                continue
            
            if self._evaluate_condition(policy.condition, metrics):
                record = self.execute_recovery(name, metrics)
                records.append(record)
        
        return records
    
    def _evaluate_condition(
        self,
        condition: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition string against metrics"""
        # Simple condition evaluation
        # In production, use a safe expression evaluator
        
        try:
            # Replace metric names with values
            expr = condition
            
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    expr = expr.replace(key, str(value))
                elif isinstance(value, str):
                    expr = expr.replace(f"'{key}'", f"'{value}'")
            
            return eval(expr)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition} - {e}")
            return False
    
    def get_recovery_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recovery history"""
        records = self._records[-limit:]
        return [
            {
                "record_id": r.record_id,
                "policy": r.policy_name,
                "action": r.action.value,
                "timestamp": r.timestamp,
                "success": r.success,
                "duration": r.duration_seconds,
            }
            for r in records
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        total = len(self._records)
        successful = sum(1 for r in self._records if r.success)
        failed = sum(1 for r in self._records if not r.success)
        
        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "active_policies": len(self._policies),
            "policies_in_cooldown": len(self._cooldowns),
        }
