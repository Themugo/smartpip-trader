"""
Cognitive Orchestrator
======================

Orchestrates all 7 cognitive layers for complete traceable decision making.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .perception import PerceptionLayer, PerceptionResult, TickData
from .situation import SituationAssessmentLayer, SituationResult
from .memory import MemoryLayer, MemoryResult
from .planning import PlanningLayer, PlanningResult, CandidateAction, ActionType
from .critic import CriticLayer, CriticResult
from .decision import DecisionLayer, DecisionResult, DecisionStatus, Objective
from .reflection import ReflectionLayer, ReflectionResult, OutcomeType

logger = logging.getLogger(__name__)


@dataclass
class CognitiveTrace:
    """Complete trace of cognitive decision process"""
    trace_id: str
    timestamp: datetime
    session_id: str
    
    # Layer inputs and outputs
    perception: Optional[PerceptionResult] = None
    situation: Optional[SituationResult] = None
    memory: Optional[MemoryResult] = None
    planning: Optional[PlanningResult] = None
    critic: Optional[CriticResult] = None
    decision: Optional[DecisionResult] = None
    reflection: Optional[ReflectionResult] = None
    
    # Final decision
    final_action: Optional[CandidateAction] = None
    should_trade: bool = False
    abstention_reason: Optional[str] = None
    
    # Metadata
    total_latency_ms: float = 0.0
    layers_executed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "final_action": self.final_action.to_dict() if self.final_action else None,
            "should_trade": self.should_trade,
            "abstention_reason": self.abstention_reason,
            "total_latency_ms": self.total_latency_ms,
            "layers_executed": self.layers_executed,
            "perception": self.perception.to_dict() if self.perception else None,
            "situation": self.situation.to_dict() if self.situation else None,
            "memory": self.memory.to_dict() if self.memory else None,
            "planning": self.planning.to_dict() if self.planning else None,
            "critic": self.critic.to_dict() if self.critic else None,
            "decision": self.decision.to_dict() if self.decision else None,
            "reflection": self.reflection.to_dict() if self.reflection else None
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = [
            f"Cognitive Trace {self.trace_id[:8]}",
            f"=" * 50,
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Layers executed: {', '.join(self.layers_executed)}",
            f"Total latency: {self.total_latency_ms:.1f}ms",
            ""
        ]
        
        if self.perception:
            lines.append(f"📊 PERCEPTION:")
            lines.append(f"   Quality: {self.perception.quality.value}")
            lines.append(f"   Confidence: {self.perception.confidence:.0%}")
            lines.append("")
        
        if self.situation:
            lines.append(f"🎯 SITUATION:")
            lines.append(f"   Regime: {self.situation.regime.value}")
            lines.append(f"   Trend: {self.situation.trend.value}")
            lines.append(f"   Uncertainty: {self.situation.uncertainty:.0%}")
            lines.append("")
        
        if self.decision:
            lines.append(f"⚖️ DECISION:")
            lines.append(f"   Status: {self.decision.status.value}")
            lines.append(f"   Action: {self.final_action.action_type.value if self.final_action else 'NONE'}")
            lines.append(f"   Proceed: {self.should_trade}")
            lines.append(f"   Confidence: {self.decision.confidence:.0%}")
            lines.append("")
        
        if self.reflection:
            lines.append(f"🔄 REFLECTION:")
            lines.append(f"   Outcome: {self.reflection.outcome.value}")
            lines.append(f"   Errors: {[e.value for e in self.reflection.reasoning_errors]}")
            lines.append(f"   Lessons: {len(self.reflection.lessons_learned)}")
        
        if self.errors:
            lines.append("")
            lines.append(f"❌ ERRORS:")
            for error in self.errors:
                lines.append(f"   - {error}")
        
        return "\n".join(lines)


class CognitiveOrchestrator:
    """
    Cognitive Orchestrator
    
    Coordinates all 7 cognitive layers for complete, traceable
    decision making from perception to reflection.
    
    Layers:
        1. Perception - Data ingestion and validation
        2. Situation - Regime detection and uncertainty
        3. Memory - Historical pattern retrieval
        4. Planning - Candidate action generation
        5. Critic - Challenge and validation
        6. Decision - Final action selection
        7. Reflection - Post-trade analysis
    """
    
    def __init__(
        self,
        enable_reflection: bool = True,
        store_traces: bool = True,
        trace_db_path: str = "data/cognitive_traces.db"
    ):
        # Initialize all layers
        self.perception = PerceptionLayer()
        self.situation = SituationAssessmentLayer()
        self.memory = MemoryLayer()
        self.planning = PlanningLayer()
        self.critic = CriticLayer()
        self.decision = DecisionLayer()
        self.reflection = ReflectionLayer() if enable_reflection else None
        
        self.enable_reflection = enable_reflection
        self.store_traces = store_traces
        self.trace_db_path = trace_db_path
        
        self._current_trace: Optional[CognitiveTrace] = None
        self._session_id = str(uuid4())
        
        # Statistics
        self._decision_counts = {"trade": 0, "abstain": 0, "total": 0}
        self._outcome_counts = {
            OutcomeType.SUCCESS: 0,
            OutcomeType.PARTIAL: 0,
            OutcomeType.FAILURE: 0,
            OutcomeType.NO_TRADE: 0
        }
        
        logger.info("Cognitive orchestrator initialized")
    
    def think(
        self,
        market_data: Dict[str, Any],
        symbol: str,
        objective: Optional[Objective] = None
    ) -> CognitiveTrace:
        """
        Execute full cognitive pipeline on market data.
        
        Args:
            market_data: Raw market data
            symbol: Trading symbol
            objective: Decision objective (uses default if not specified)
            
        Returns:
            CognitiveTrace with complete decision trace
        """
        import time
        start_time = time.time()
        
        # Initialize trace
        trace = CognitiveTrace(
            trace_id=str(uuid4()),
            timestamp=datetime.now(),
            session_id=self._session_id
        )
        
        self._current_trace = trace
        
        try:
            # Layer 1: Perception
            trace.layers_executed.append("perception")
            trace.perception = self.perception.process(market_data)
            
            if not trace.perception.is_valid:
                trace.errors.append("Invalid perception data")
                trace.should_trade = False
                trace.abstention_reason = "Data validation failed"
                return trace
            
            # Layer 2: Situation Assessment
            trace.layers_executed.append("situation")
            trace.situation = self.situation.process(
                trace.perception,
                market_data.get("historical_ticks")
            )
            
            # Layer 3: Memory
            trace.layers_executed.append("memory")
            trace.memory = self.memory.process(
                trace.situation,
                trace.perception,
                symbol
            )
            
            # Layer 4: Planning
            trace.layers_executed.append("planning")
            trace.planning = self.planning.process(
                trace.situation,
                trace.memory,
                trace.perception
            )
            
            # Layer 5: Critic
            trace.layers_executed.append("critic")
            trace.critic = self.critic.process(
                trace.planning,
                trace.situation,
                trace.perception,
                trace.memory
            )
            
            # Layer 6: Decision
            trace.layers_executed.append("decision")
            trace.decision = self.decision.process(
                trace.critic,
                trace.planning,
                objective
            )
            
            # Extract final decision
            trace.final_action = trace.decision.selected_action
            trace.should_trade = trace.decision.proceed
            trace.abstention_reason = trace.decision.abstention_reason
            
            # Update statistics
            self._decision_counts["total"] += 1
            if trace.should_trade:
                self._decision_counts["trade"] += 1
            else:
                self._decision_counts["abstain"] += 1
            
            # Store trace if enabled
            if self.store_traces:
                self._store_trace(trace)
            
            trace.total_latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Cognitive pipeline completed in {trace.total_latency_ms:.1f}ms, "
                       f"decision: {'TRADE' if trace.should_trade else 'ABSTAIN'}")
            
            return trace
            
        except Exception as e:
            logger.error(f"Cognitive pipeline error: {e}")
            trace.errors.append(str(e))
            trace.should_trade = False
            trace.abstention_reason = f"Pipeline error: {e}"
            trace.total_latency_ms = (time.time() - start_time) * 1000
            return trace
    
    def reflect(
        self,
        trace: CognitiveTrace,
        realized_pnl: float,
        trade_id: Optional[str] = None
    ) -> ReflectionResult:
        """
        Perform reflection on completed trade.
        
        Args:
            trace: The cognitive trace from think()
            realized_pnl: Actual PnL from the trade
            trade_id: Optional trade identifier
            
        Returns:
            ReflectionResult with analysis
        """
        if not self.enable_reflection or not self.reflection:
            raise RuntimeError("Reflection is not enabled")
        
        if not trace.decision or not trace.critic or not trace.situation:
            raise RuntimeError("Invalid trace - missing required layers")
        
        if trace.decision.status == DecisionStatus.ABSTAINED:
            result = self.reflection.process_no_trade(
                trace.decision,
                trace.abstention_reason or "Unknown"
            )
        else:
            result = self.reflection.process(
                trace.decision,
                trace.critic,
                trace.situation,
                realized_pnl,
                trade_id
            )
        
        # Update outcome statistics
        self._outcome_counts[result.outcome] += 1
        
        # Update critic calibration
        if trace.critic.original_action:
            self.critic.record_outcome(
                trace.critic.original_action.win_probability,
                1.0 if realized_pnl > 0 else 0.0
            )
        
        # Store reflection result
        trace.reflection = result
        
        logger.info(f"Reflection complete: {result.outcome.value}, "
                   f"calibration_delta={result.confidence_calibration_delta:.3f}")
        
        return result
    
    def think_and_execute(
        self,
        market_data: Dict[str, Any],
        symbol: str,
        executor: Any  # Function that executes the trade
    ) -> Tuple[CognitiveTrace, Optional[Any], Optional[ReflectionResult]]:
        """
        Complete think-execute-reflect cycle.
        
        Args:
            market_data: Raw market data
            symbol: Trading symbol
            executor: Function that executes the trade, returns (success, result)
            
        Returns:
            Tuple of (trace, execution_result, reflection_result)
        """
        # Think
        trace = self.think(market_data, symbol)
        
        if not trace.should_trade or not trace.final_action:
            return trace, None, None
        
        # Execute
        try:
            execution_result = executor(trace.final_action)
            success = execution_result[0] if isinstance(execution_result, tuple) else True
            pnl = execution_result[1] if isinstance(execution_result, tuple) else 0
            trade_id = execution_result[2] if len(execution_result) > 2 else None
        except Exception as e:
            logger.error(f"Execution error: {e}")
            success = False
            pnl = 0
            trade_id = None
        
        # Reflect
        reflection = self.reflect(trace, pnl, trade_id)
        
        return trace, execution_result, reflection
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get decision and outcome statistics"""
        total = self._decision_counts["total"] or 1
        
        return {
            "decisions": {
                "total": self._decision_counts["total"],
                "trades": self._decision_counts["trade"],
                "abstains": self._decision_counts["abstain"],
                "trade_rate": self._decision_counts["trade"] / total
            },
            "outcomes": {
                OutcomeType.SUCCESS.value: self._outcome_counts[OutcomeType.SUCCESS],
                OutcomeType.PARTIAL.value: self._outcome_counts[OutcomeType.PARTIAL],
                OutcomeType.FAILURE.value: self._outcome_counts[OutcomeType.FAILURE],
                OutcomeType.NO_TRADE.value: self._outcome_counts[OutcomeType.NO_TRADE]
            },
            "calibration": {
                "critic_error": self.critic.get_calibration_error(),
                "reflection_error": self.reflection.get_calibration_error() if self.reflection else 0
            }
        }
    
    def get_current_trace(self) -> Optional[CognitiveTrace]:
        """Get the most recent cognitive trace"""
        return self._current_trace
    
    def reset(self) -> None:
        """Reset all layers and statistics"""
        self.perception.reset()
        self.situation.reset()
        self.memory.reset()
        self.critic.reset()
        self.decision.reset()
        if self.reflection:
            self.reflection.reset()
        
        self._current_trace = None
        self._session_id = str(uuid4())
        self._decision_counts = {"trade": 0, "abstain": 0, "total": 0}
        self._outcome_counts = {
            OutcomeType.SUCCESS: 0,
            OutcomeType.PARTIAL: 0,
            OutcomeType.FAILURE: 0,
            OutcomeType.NO_TRADE: 0
        }
        
        logger.info("Cognitive orchestrator reset")
    
    def _store_trace(self, trace: CognitiveTrace) -> None:
        """Store trace in database (simplified implementation)"""
        import json
        import os
        import sqlite3
        
        os.makedirs(os.path.dirname(self.trace_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.trace_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                final_action TEXT,
                should_trade INTEGER,
                abstention_reason TEXT,
                total_latency_ms REAL,
                layers_executed TEXT,
                errors TEXT,
                full_trace TEXT
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO traces (
                trace_id, timestamp, session_id, final_action,
                should_trade, abstention_reason, total_latency_ms,
                layers_executed, errors, full_trace
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.trace_id,
            trace.timestamp.isoformat(),
            trace.session_id,
            json.dumps(trace.final_action.to_dict()) if trace.final_action else None,
            1 if trace.should_trade else 0,
            trace.abstention_reason,
            trace.total_latency_ms,
            json.dumps(trace.layers_executed),
            json.dumps(trace.errors),
            json.dumps(trace.to_dict())
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_traces(self, limit: int = 10) -> List[CognitiveTrace]:
        """Retrieve recent decision traces"""
        # This would load from database in full implementation
        return [self._current_trace] if self._current_trace else []


