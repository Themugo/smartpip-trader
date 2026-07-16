"""
Research Events
==============

Events related to research and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import Event, EventType, EventMetadata


@dataclass
class ResearchEvent(Event):
    """Research activity event"""
    
    def __init__(
        self,
        research_id: str,
        activity: str,  # hypothesis_created, experiment_started, analysis_completed
        description: str,
        timestamp: float,
        researcher: str = "",
        hypothesis: str = "",
        results: Optional[Dict[str, Any]] = None,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "research_id": research_id,
            "activity": activity,
            "description": description,
            "researcher": researcher,
            "hypothesis": hypothesis,
            "results": results or {},
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.RESEARCH_EVENT,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class ValidationEvent(Event):
    """Validation event"""
    
    def __init__(
        self,
        validation_id: str,
        validation_type: str,  # walk_forward, out_of_sample, backtest, paper_trading
        strategy_id: str,
        passed: bool,
        metrics: Dict[str, float],
        thresholds: Dict[str, float],
        timestamp: float,
        test_period_start: float = 0,
        test_period_end: float = 0,
        sample_size: int = 0,
        failure_reasons: List[str] = None,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "validation_id": validation_id,
            "validation_type": validation_type,
            "strategy_id": strategy_id,
            "passed": passed,
            "metrics": metrics,
            "thresholds": thresholds,
            "test_period_start": test_period_start,
            "test_period_end": test_period_end,
            "sample_size": sample_size,
            "failure_reasons": failure_reasons or [],
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
            metadata.strategy_version = strategy_id
        
        super().__init__(
            event_type=EventType.VALIDATION_EVENT,
            metadata=metadata,
            payload=payload,
        )
