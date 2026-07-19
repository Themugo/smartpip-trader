"""
AI Core Orchestrator - Central Decision Engine

Central decision-making engine that orchestrates all trading decisions.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions"""
    TRADE = "trade"
    CANCEL = "cancel"
    ADJUST = "adjust"
    HOLD = "hold"
    RETRAIN = "retrain"
    SWITCH_STRATEGY = "switch_strategy"
    RISK_REDUCE = "risk_reduce"


class DecisionStatus(Enum):
    """Decision status"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class DecisionContext:
    """Context for a decision"""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Market data
    symbol: str = ""
    price: float = 0
    bid: float = 0
    ask: float = 0
    volatility: float = 0
    
    # Signal data
    signals: Dict[str, Any] = field(default_factory=dict)
    primary_signal: Optional[Any] = None
    
    # Risk data
    current_exposure: float = 0
    daily_pnl: float = 0
    max_drawdown: float = 0
    risk_score: float = 0
    
    # Account data
    balance: float = 0
    equity: float = 0
    available_margin: float = 0
    
    # AI data
    confidence: float = 0
    regime: str = "unknown"
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy data
    active_strategies: List[str] = field(default_factory=list)
    strategy_signals: Dict[str, float] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volatility": self.volatility,
            "signals": self.signals,
            "confidence": self.confidence,
            "regime": self.regime,
            "market_conditions": self.market_conditions,
            "active_strategies": self.active_strategies,
            "strategy_signals": self.strategy_signals,
            "risk_score": self.risk_score,
            "balance": self.balance,
            "equity": self.equity,
        }


@dataclass
class Decision:
    """A trading decision"""
    id: str
    decision_type: DecisionType
    context: DecisionContext
    status: DecisionStatus = DecisionStatus.PENDING
    
    # Decision details
    action: str = ""  # BUY, SELL, HOLD, etc.
    amount: float = 0
    reason: str = ""
    confidence: float = 0
    
    # Processing
    processing_time_ms: float = 0
    validators_passed: List[str] = field(default_factory=list)
    validators_failed: List[str] = field(default_factory=list)
    
    # Results
    result_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_type": self.decision_type.value,
            "status": self.status.value,
            "action": self.action,
            "amount": self.amount,
            "reason": self.reason,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "validators_passed": self.validators_passed,
            "validators_failed": self.validators_failed,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error": self.error,
        }


@dataclass
class DecisionResult:
    """Result of a decision"""
    decision: Decision
    approved: bool
    reason: str
    risk_score: float = 0
    expected_value: float = 0
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_chain: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "expected_value": self.expected_value,
            "alternatives": self.alternatives,
            "reasoning_chain": self.reasoning_chain,
            "decision": self.decision.to_dict(),
            "metadata": self.metadata,
        }


class DecisionValidator:
    """Base class for decision validators"""
    name: str = "base"
    
    def validate(self, decision: Decision, context: DecisionContext) -> tuple[bool, str]:
        """Validate a decision, returns (passed, reason)"""
        return True, "passed"


class AICoreOrchestrator:
    """
    AI Core Orchestrator - Central decision engine.
    
    Every trading decision passes through this orchestrator:
    1. Receive decision request
    2. Gather context (signals, risk, market data)
    3. Apply validators
    4. Make decision
    5. Log and explain
    """
    
    def __init__(self):
        self._validators: List[DecisionValidator] = []
        self._decision_history: deque = deque(maxlen=10000)
        self._decision_callbacks: List[Callable] = []
        self._logger = logging.getLogger(f"{__name__}.AICore")
    
    def add_validator(self, validator: DecisionValidator) -> None:
        """Add a decision validator"""
        self._validators.append(validator)
        self._logger.info(f"Added validator: {validator.name}")
    
    def remove_validator(self, name: str) -> bool:
        """Remove a validator by name"""
        for i, v in enumerate(self._validators):
            if v.name == name:
                del self._validators[i]
                return True
        return False
    
    async def make_decision(
        self,
        decision_type: DecisionType,
        context: DecisionContext,
    ) -> DecisionResult:
        """
        Make a trading decision.
        
        Args:
            decision_type: Type of decision to make
            context: Decision context with all relevant data
            
        Returns:
            DecisionResult with decision and explanation
        """
        import uuid
        
        decision = Decision(
            id=str(uuid.uuid4()),
            decision_type=decision_type,
            context=context,
            status=DecisionStatus.PROCESSING,
        )
        
        start_time = time.time()
        reasoning_chain = []
        
        try:
            # Step 1: Run validators
            for validator in self._validators:
                passed, reason = validator.validate(decision, context)
                if passed:
                    decision.validators_passed.append(validator.name)
                    reasoning_chain.append(f"[{validator.name}] {reason}")
                else:
                    decision.validators_failed.append(validator.name)
                    reasoning_chain.append(f"[{validator.name}] REJECTED: {reason}")
            
            # Step 2: Check if all validators passed
            if decision.validators_failed:
                decision.status = DecisionStatus.REJECTED
                decision.error = f"Failed validators: {', '.join(decision.validators_failed)}"
                
                result = DecisionResult(
                    decision=decision,
                    approved=False,
                    reason=decision.error,
                    reasoning_chain=reasoning_chain,
                )
            else:
                # Step 3: Make the actual decision
                decision_action, decision_reason, decision_confidence = await self._execute_decision(
                    decision_type, context
                )
                
                decision.action = decision_action
                decision.reason = decision_reason
                decision.confidence = decision_confidence
                decision.status = DecisionStatus.APPROVED
                
                reasoning_chain.append(f"[Decision] {decision_action}: {decision_reason}")
                
                # Calculate expected value and risk
                expected_value = self._calculate_expected_value(context, decision)
                risk_score = self._calculate_risk_score(context, decision)
                
                result = DecisionResult(
                    decision=decision,
                    approved=True,
                    reason=decision_reason,
                    risk_score=risk_score,
                    expected_value=expected_value,
                    reasoning_chain=reasoning_chain,
                )
            
            decision.processed_at = datetime.now(timezone.utc)
            decision.processing_time_ms = (time.time() - start_time) * 1000
            
            # Add to history
            self._decision_history.append(decision)
            
            # Fire callbacks
            for callback in self._decision_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self._logger.error(f"Decision callback error: {e}")
            
            self._logger.info(
                f"Decision {decision.id}: {decision.status.value} "
                f"- {decision.action if decision.action else 'N/A'}"
            )
            
            return result
            
        except Exception as e:
            self._logger.error(f"Decision error: {e}")
            decision.status = DecisionStatus.FAILED
            decision.error = str(e)
            decision.processing_time_ms = (time.time() - start_time) * 1000
            
            return DecisionResult(
                decision=decision,
                approved=False,
                reason=f"Decision failed: {str(e)}",
                reasoning_chain=reasoning_chain + [f"[Error] {str(e)}"],
            )
    
    async def _execute_decision(
        self,
        decision_type: DecisionType,
        context: DecisionContext,
    ) -> tuple[str, str, float]:
        """Execute the actual decision logic"""
        # Aggregate signals from strategies
        signal_scores = list(context.strategy_signals.values())
        avg_signal = sum(signal_scores) / len(signal_scores) if signal_scores else 0
        
        # Determine action based on signals and conditions
        if decision_type == DecisionType.TRADE:
            if avg_signal > 0.3:
                return "BUY", f"Strong bullish signal (score: {avg_signal:.2f})", min(0.9, 0.5 + abs(avg_signal))
            elif avg_signal < -0.3:
                return "SELL", f"Strong bearish signal (score: {avg_signal:.2f})", min(0.9, 0.5 + abs(avg_signal))
            else:
                return "HOLD", f"Neutral signal (score: {avg_signal:.2f})", 0.5
        
        elif decision_type == DecisionType.CANCEL:
            return "CANCEL", "Cancellation requested", 0.95
        
        elif decision_type == DecisionType.RISK_REDUCE:
            return "REDUCE", "Risk reduction required", 0.85
        
        return "HOLD", "Default hold", 0.5
    
    def _calculate_expected_value(
        self,
        context: DecisionContext,
        decision: Decision,
    ) -> float:
        """Calculate expected value of the decision"""
        # Simple EV calculation
        if decision.action in ("BUY", "SELL"):
            win_rate = context.confidence / 100
            avg_win = context.price * 0.01  # 1% avg win
            avg_loss = context.price * 0.005  # 0.5% avg loss
            
            return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        return 0
    
    def _calculate_risk_score(
        self,
        context: DecisionContext,
        decision: Decision,
    ) -> float:
        """Calculate risk score for the decision"""
        risk = 0.5  # Base risk
        
        # Adjust for current exposure
        if context.current_exposure > 0.5:
            risk += 0.2
        elif context.current_exposure > 0.8:
            risk += 0.3
        
        # Adjust for drawdown
        if context.max_drawdown > 5:
            risk += 0.1
        elif context.max_drawdown > 10:
            risk += 0.2
        
        # Adjust for confidence
        if context.confidence < 50:
            risk += 0.1
        
        return min(1.0, risk)
    
    def get_decision_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Decision]:
        """Get decision history"""
        decisions = list(self._decision_history)
        
        if since:
            decisions = [d for d in decisions if d.created_at >= since]
        
        return decisions[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get decision statistics"""
        decisions = list(self._decision_history)
        
        if not decisions:
            return {"total": 0}
        
        approved = sum(1 for d in decisions if d.status == DecisionStatus.APPROVED)
        rejected = sum(1 for d in decisions if d.status == DecisionStatus.REJECTED)
        
        avg_processing_time = sum(d.processing_time_ms for d in decisions) / len(decisions)
        
        return {
            "total_decisions": len(decisions),
            "approved": approved,
            "rejected": rejected,
            "approval_rate": approved / len(decisions) if decisions else 0,
            "avg_processing_time_ms": avg_processing_time,
            "by_type": {
                dt.value: sum(1 for d in decisions if d.decision_type == dt)
                for dt in DecisionType
            },
        }
    
    def on_decision(self, callback: Callable[[DecisionResult], None]) -> None:
        """Register a decision callback"""
        self._decision_callbacks.append(callback)
