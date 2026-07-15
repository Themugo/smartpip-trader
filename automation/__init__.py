"""
Automation Engine - Workflow Automation

IF-THEN action automation:
- Retrain models
- Disable strategy
- Enable paper mode
- Send notifications
- Pause execution
- Generate reports
- Archive logs
"""

from automation.engine import AutomationEngine, Workflow, WorkflowStep, WorkflowTrigger

__all__ = [
    "AutomationEngine",
    "Workflow",
    "WorkflowStep",
    "WorkflowTrigger",
]
