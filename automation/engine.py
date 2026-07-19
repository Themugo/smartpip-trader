"""
Automation Engine - Workflow Automation

IF-THEN automation system for trading workflows.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Trigger types"""
    CONDITION = "condition"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"


class ActionType(Enum):
    """Action types"""
    RETRAIN_MODEL = "retrain_model"
    DISABLE_STRATEGY = "disable_strategy"
    ENABLE_PAPER_MODE = "enable_paper_mode"
    ENABLE_LIVE_MODE = "enable_live_mode"
    SEND_NOTIFICATION = "send_notification"
    PAUSE_EXECUTION = "pause_execution"
    RESUME_EXECUTION = "resume_execution"
    GENERATE_REPORT = "generate_report"
    ARCHIVE_LOGS = "archive_logs"
    UPDATE_CONFIG = "update_config"
    CALLBACK = "callback"


@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration"""
    trigger_type: TriggerType
    
    # Condition trigger
    condition: Optional[str] = None  # e.g., "risk_score > 80"
    
    # Schedule trigger
    cron_expression: Optional[str] = None
    
    # Event trigger
    event_type: Optional[str] = None
    
    # Metadata
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.value,
            "condition": self.condition,
            "cron_expression": self.cron_expression,
            "event_type": self.event_type,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
        }


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution control
    continue_on_failure: bool = True
    retry_count: int = 0
    timeout_seconds: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "continue_on_failure": self.continue_on_failure,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class Workflow:
    """An automation workflow"""
    id: str
    name: str
    description: str
    
    trigger: WorkflowTrigger
    steps: List[WorkflowStep]
    
    # Status
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_run: Optional[datetime] = None
    
    # Execution tracking
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
        }


class AutomationEngine:
    """
    Automation engine for IF-THEN workflows.
    
    Supported actions:
    - Retrain models
    - Disable strategy
    - Enable paper mode
    - Send notifications
    - Pause execution
    - Generate reports
    - Archive logs
    """
    
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._action_handlers: Dict[ActionType, Callable] = {}
        self._event_subscriptions: List[str] = []
        
        # Initialize default handlers
        self._init_default_handlers()
    
    def _init_default_handlers(self) -> None:
        """Initialize default action handlers"""
        # These would be connected to actual platform components
        self._action_handlers = {
            ActionType.SEND_NOTIFICATION: self._send_notification,
            ActionType.UPDATE_CONFIG: self._update_config,
            ActionType.CALLBACK: self._execute_callback,
        }
    
    def create_workflow(
        self,
        name: str,
        description: str,
        trigger: WorkflowTrigger,
        steps: List[WorkflowStep],
    ) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            trigger=trigger,
            steps=steps,
        )
        
        self._workflows[workflow.id] = workflow
        self._logger.info(f"Created workflow: {name}")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        return self._workflows.get(workflow_id)
    
    def get_all_workflows(self) -> List[Workflow]:
        """Get all workflows"""
        return list(self._workflows.values())
    
    def update_workflow(
        self,
        workflow_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Workflow]:
        """Update a workflow"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        if "name" in updates:
            workflow.name = updates["name"]
        if "description" in updates:
            workflow.description = updates["description"]
        if "enabled" in updates:
            workflow.enabled = updates["enabled"]
        if "steps" in updates:
            workflow.steps = updates["steps"]
        
        return workflow
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow"""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False
    
    def enable_workflow(self, workflow_id: str) -> bool:
        """Enable a workflow"""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.enabled = True
            return True
        return False
    
    def disable_workflow(self, workflow_id: str) -> bool:
        """Disable a workflow"""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            workflow.enabled = False
            return True
        return False
    
    async def trigger_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Manually trigger a workflow"""
        workflow = self._workflows.get(workflow_id)
        if not workflow or not workflow.enabled:
            return False
        
        return await self._execute_workflow(workflow, context or {})
    
    async def check_triggers(self, event_type: str, event_data: Any) -> None:
        """Check if any workflows should be triggered"""
        for workflow in self._workflows.values():
            if not workflow.enabled:
                continue
            
            if workflow.trigger.trigger_type == TriggerType.EVENT:
                if workflow.trigger.event_type == event_type:
                    await self._execute_workflow(workflow, {"event_type": event_type, "event_data": event_data})
    
    async def _execute_workflow(
        self,
        workflow: Workflow,
        context: Dict[str, Any],
    ) -> bool:
        """Execute a workflow"""
        workflow.total_runs += 1
        workflow.last_run = datetime.now(timezone.utc)
        
        self._logger.info(f"Executing workflow: {workflow.name}")
        
        all_succeeded = True
        
        for step in workflow.steps:
            try:
                success = await self._execute_step(step, context)
                
                if not success and not step.continue_on_failure:
                    all_succeeded = False
                    break
                    
            except Exception as e:
                self._logger.error(f"Step {step.action_type.value} failed: {e}")
                all_succeeded = False
                
                if not step.continue_on_failure:
                    break
        
        if all_succeeded:
            workflow.successful_runs += 1
        else:
            workflow.failed_runs += 1
        
        return all_succeeded
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> bool:
        """Execute a single workflow step"""
        handler = self._action_handlers.get(step.action_type)
        
        if not handler:
            self._logger.warning(f"No handler for action: {step.action_type.value}")
            return False
        
        try:
            if asyncio.iscoroutinefunction(handler):
                await asyncio.wait_for(
                    handler(step.parameters, context),
                    timeout=step.timeout_seconds,
                )
            else:
                handler(step.parameters, context)
            
            return True
            
        except asyncio.TimeoutError:
            self._logger.error(f"Step timeout: {step.action_type.value}")
            return False
        except Exception as e:
            self._logger.error(f"Step error: {step.action_type.value} - {e}")
            return False
    
    async def _send_notification(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Send a notification"""
        message = params.get("message", "Workflow notification")
        # Would integrate with notification system
        self._logger.info(f"Notification: {message}")
    
    async def _update_config(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Update configuration"""
        key = params.get("key")
        value = params.get("value")
        # Would integrate with config manager
        self._logger.info(f"Config update: {key} = {value}")
    
    async def _execute_callback(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Execute a callback function"""
        callback_name = params.get("callback")
        # Would call registered callback
        self._logger.info(f"Callback: {callback_name}")
    
    def register_action_handler(
        self,
        action_type: ActionType,
        handler: Callable,
    ) -> None:
        """Register a custom action handler"""
        self._action_handlers[action_type] = handler
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get automation statistics"""
        total = len(self._workflows)
        enabled = sum(1 for w in self._workflows.values() if w.enabled)
        
        total_runs = sum(w.total_runs for w in self._workflows.values())
        successful = sum(w.successful_runs for w in self._workflows.values())
        
        return {
            "total_workflows": total,
            "enabled_workflows": enabled,
            "total_runs": total_runs,
            "successful_runs": successful,
            "success_rate": successful / total_runs if total_runs > 0 else 0,
        }
