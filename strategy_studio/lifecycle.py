"""
Strategy Lifecycle Manager - State Machine for Strategy Development

Manages strategy lifecycle states and promotion criteria.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from strategy_studio.builder import StrategyGraph

logger = logging.getLogger(__name__)


class LifecycleState(Enum):
    """Strategy lifecycle states"""
    DRAFT = "draft"
    TESTING = "testing"
    PAPER_TRADING = "paper_trading"
    VALIDATED = "validated"
    PRODUCTION = "production"
    PAUSED = "paused"
    RETIRED = "retired"
    ARCHIVED = "archived"


# State transition rules
VALID_TRANSITIONS = {
    LifecycleState.DRAFT: [LifecycleState.TESTING],
    LifecycleState.TESTING: [LifecycleState.PAPER_TRADING, LifecycleState.DRAFT, LifecycleState.ARCHIVED],
    LifecycleState.PAPER_TRADING: [LifecycleState.VALIDATED, LifecycleState.TESTING, LifecycleState.PAUSED],
    LifecycleState.VALIDATED: [LifecycleState.PRODUCTION, LifecycleState.PAPER_TRADING, LifecycleState.PAUSED],
    LifecycleState.PRODUCTION: [LifecycleState.PAUSED, LifecycleState.RETIRED],
    LifecycleState.PAUSED: [LifecycleState.PRODUCTION, LifecycleState.PAPER_TRADING, LifecycleState.TESTING, LifecycleState.RETIRED],
    LifecycleState.RETIRED: [LifecycleState.ARCHIVED],
    LifecycleState.ARCHIVED: [],  # Terminal state
}


@dataclass
class PromotionCriteria:
    """Criteria for state promotion"""
    name: str
    description: str
    metric: str
    threshold: float
    operator: str = ">="  # >=, <=, ==, !=
    required: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if criteria is met"""
        if self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        elif self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        return False


@dataclass
class StateTransition:
    """Record of a state transition"""
    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime
    reason: str
    triggered_by: str = "system"
    criteria_results: Dict[str, bool] = field(default_factory=dict)


@dataclass
class LifecycleMetrics:
    """Metrics for lifecycle evaluation"""
    # Performance metrics
    total_return: float = 0
    sharpe_ratio: float = 0
    max_drawdown: float = 0
    win_rate: float = 0
    expectancy: float = 0
    profit_factor: float = 0
    
    # Quality metrics
    test_coverage: float = 0
    documentation_score: float = 0
    calibration_score: float = 0
    
    # Operational metrics
    uptime_percent: float = 0
    error_rate: float = 0
    trades_count: int = 0
    avg_confidence: float = 0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "test_coverage": self.test_coverage,
            "documentation_score": self.documentation_score,
            "calibration_score": self.calibration_score,
            "uptime_percent": self.uptime_percent,
            "error_rate": self.error_rate,
            "trades_count": self.trades_count,
            "avg_confidence": self.avg_confidence,
        }


@dataclass
class StrategyVersion:
    """A version of a strategy"""
    version: str
    graph_data: Dict[str, Any]
    source_code: str
    created_at: datetime
    author: str
    changelog: str = ""
    is_active: bool = True


class LifecycleManager:
    """
    Strategy Lifecycle Manager with state machine.
    
    States:
    - Draft: Initial creation
    - Testing: Unit and integration testing
    - Paper Trading: Live data, simulated execution
    - Validated: Meets quality criteria
    - Production: Live trading
    - Paused: Temporarily disabled
    - Retired: No longer used
    - Archived: Archived for reference
    
    Features:
    - State transitions with validation
    - Promotion criteria evaluation
    - Version tracking
    - Transition history
    """
    
    def __init__(self):
        self._strategies: Dict[str, Dict[str, Any]] = {}
        self._transition_history: Dict[str, List[StateTransition]] = {}
        
        # Default promotion criteria for each transition
        self._default_criteria = self._get_default_criteria()
    
    def _get_default_criteria(self) -> Dict[tuple, List[PromotionCriteria]]:
        """Get default promotion criteria"""
        return {
            (LifecycleState.TESTING, LifecycleState.PAPER_TRADING): [
                PromotionCriteria(
                    name="Compilation Success",
                    description="Strategy must compile without errors",
                    metric="compilation_success",
                    threshold=1,
                    operator="==",
                ),
                PromotionCriteria(
                    name="Test Coverage",
                    description="At least 80% test coverage",
                    metric="test_coverage",
                    threshold=80,
                    operator=">=",
                ),
                PromotionCriteria(
                    name="Documentation Score",
                    description="Documentation completeness",
                    metric="documentation_score",
                    threshold=50,
                    operator=">=",
                ),
            ],
            (LifecycleState.PAPER_TRADING, LifecycleState.VALIDATED): [
                PromotionCriteria(
                    name="Minimum Trades",
                    description="At least 50 paper trades",
                    metric="trades_count",
                    threshold=50,
                    operator=">=",
                ),
                PromotionCriteria(
                    name="Positive Return",
                    description="Positive total return",
                    metric="total_return",
                    threshold=0,
                    operator=">",
                ),
                PromotionCriteria(
                    name="Max Drawdown",
                    description="Drawdown below 15%",
                    metric="max_drawdown",
                    threshold=15,
                    operator="<=",
                ),
                PromotionCriteria(
                    name="Sharpe Ratio",
                    description="Sharpe ratio at least 1.0",
                    metric="sharpe_ratio",
                    threshold=1.0,
                    operator=">=",
                ),
                PromotionCriteria(
                    name="Calibration",
                    description="Confidence calibration score",
                    metric="calibration_score",
                    threshold=70,
                    operator=">=",
                ),
            ],
            (LifecycleState.VALIDATED, LifecycleState.PRODUCTION): [
                PromotionCriteria(
                    name="Extended Paper Trading",
                    description="At least 200 total trades",
                    metric="trades_count",
                    threshold=200,
                    operator=">=",
                ),
                PromotionCriteria(
                    name="Stable Sharpe",
                    description="Sharpe ratio at least 1.5",
                    metric="sharpe_ratio",
                    threshold=1.5,
                    operator=">=",
                ),
                PromotionCriteria(
                    name="Low Drawdown",
                    description="Drawdown below 10%",
                    metric="max_drawdown",
                    threshold=10,
                    operator="<=",
                ),
            ],
        }
    
    def register_strategy(
        self,
        strategy_id: str,
        name: str,
        graph: StrategyGraph,
        author: str = "",
    ) -> Dict[str, Any]:
        """Register a new strategy"""
        strategy = {
            "id": strategy_id,
            "name": name,
            "state": LifecycleState.DRAFT,
            "graph": graph.to_dict(),
            "author": author,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "versions": [],
            "metrics": LifecycleMetrics(),
            "criteria": {},
            "notes": [],
        }
        
        # Create initial version
        self._create_version(strategy, graph, author, "Initial version")
        
        self._strategies[strategy_id] = strategy
        self._transition_history[strategy_id] = []
        
        logger.info(f"Registered strategy: {name} ({strategy_id})")
        return strategy
    
    def _create_version(
        self,
        strategy: Dict[str, Any],
        graph: StrategyGraph,
        author: str,
        changelog: str,
    ) -> StrategyVersion:
        """Create a new version"""
        version_num = len(strategy["versions"]) + 1
        version = f"1.{version_num}.0"
        
        strategy_version = StrategyVersion(
            version=version,
            graph_data=graph.to_dict(),
            source_code="",  # Would be filled by compiler
            created_at=datetime.now(timezone.utc),
            author=author,
            changelog=changelog,
        )
        
        strategy["versions"].append(strategy_version)
        return strategy_version
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def get_all_strategies(
        self,
        state: Optional[LifecycleState] = None,
    ) -> List[Dict[str, Any]]:
        """Get all strategies, optionally filtered by state"""
        strategies = list(self._strategies.values())
        
        if state:
            strategies = [s for s in strategies if s["state"] == state]
        
        return strategies
    
    def get_strategies_by_state(self) -> Dict[LifecycleState, List[Dict[str, Any]]]:
        """Get strategies grouped by state"""
        result = {state: [] for state in LifecycleState}
        
        for strategy in self._strategies.values():
            result[strategy["state"]].append(strategy)
        
        return result
    
    def update_metrics(self, strategy_id: str, metrics: LifecycleMetrics) -> bool:
        """Update strategy metrics"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        
        strategy["metrics"] = metrics
        strategy["updated_at"] = datetime.now(timezone.utc)
        return True
    
    def can_transition(
        self,
        strategy_id: str,
        target_state: LifecycleState,
    ) -> tuple[bool, str, Dict[str, bool]]:
        """
        Check if a transition is valid and criteria are met.
        
        Returns:
            (can_transition, reason, criteria_results)
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False, "Strategy not found", {}
        
        current_state = strategy["state"]
        
        # Check if transition is valid
        valid_targets = VALID_TRANSITIONS.get(current_state, [])
        if target_state not in valid_targets:
            return False, f"Invalid transition: {current_state.value} -> {target_state.value}", {}
        
        # Get applicable criteria
        criteria_key = (current_state, target_state)
        criteria = self._default_criteria.get(criteria_key, [])
        
        # Evaluate criteria
        metrics = strategy["metrics"]
        metrics_dict = metrics.to_dict()
        
        criteria_results = {}
        all_passed = True
        
        for criterion in criteria:
            value = metrics_dict.get(criterion.metric, 0)
            passed = criterion.evaluate(value)
            criteria_results[criterion.name] = passed
            
            if criterion.required and not passed:
                all_passed = False
        
        if not all_passed:
            failed = [k for k, v in criteria_results.items() if not v]
            return False, f"Criteria not met: {', '.join(failed)}", criteria_results
        
        return True, "All criteria met", criteria_results
    
    def transition(
        self,
        strategy_id: str,
        target_state: LifecycleState,
        reason: str,
        triggered_by: str = "user",
    ) -> tuple[bool, str]:
        """
        Transition strategy to a new state.
        
        Returns:
            (success, message)
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False, "Strategy not found"
        
        current_state = strategy["state"]
        
        # Validate transition
        can_transition, message, criteria_results = self.can_transition(
            strategy_id, target_state
        )
        
        if not can_transition:
            return False, message
        
        # Perform transition
        strategy["state"] = target_state
        strategy["updated_at"] = datetime.now(timezone.utc)
        
        # Record transition
        transition = StateTransition(
            from_state=current_state,
            to_state=target_state,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            triggered_by=triggered_by,
            criteria_results=criteria_results,
        )
        
        self._transition_history[strategy_id].append(transition)
        
        logger.info(
            f"Strategy {strategy_id} transitioned: {current_state.value} -> {target_state.value}"
        )
        
        return True, f"Transitioned to {target_state.value}"
    
    def get_transition_history(
        self,
        strategy_id: str,
    ) -> List[StateTransition]:
        """Get transition history for a strategy"""
        return self._transition_history.get(strategy_id, [])
    
    def get_promotion_criteria(
        self,
        from_state: LifecycleState,
        to_state: LifecycleState,
    ) -> List[PromotionCriteria]:
        """Get criteria for a state transition"""
        key = (from_state, to_state)
        return self._default_criteria.get(key, [])
    
    def set_custom_criteria(
        self,
        from_state: LifecycleState,
        to_state: LifecycleState,
        criteria: List[PromotionCriteria],
    ) -> None:
        """Set custom promotion criteria"""
        key = (from_state, to_state)
        self._default_criteria[key] = criteria
    
    def add_note(self, strategy_id: str, note: str, author: str = "") -> bool:
        """Add a note to a strategy"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        
        strategy["notes"].append({
            "text": note,
            "author": author,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True
    
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get strategies in active states (not paused/retired/archived)"""
        active_states = [
            LifecycleState.DRAFT,
            LifecycleState.TESTING,
            LifecycleState.PAPER_TRADING,
            LifecycleState.VALIDATED,
            LifecycleState.PRODUCTION,
        ]
        return self.get_all_strategies(state=None)
    
    def get_production_strategies(self) -> List[Dict[str, Any]]:
        """Get strategies in production"""
        return self.get_all_strategies(state=LifecycleState.PRODUCTION)
    
    def get_paper_trading_strategies(self) -> List[Dict[str, Any]]:
        """Get strategies in paper trading"""
        return self.get_all_strategies(state=LifecycleState.PAPER_TRADING)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get lifecycle statistics"""
        by_state = self.get_strategies_by_state()
        
        return {
            "total_strategies": len(self._strategies),
            "by_state": {
                state.value: len(strategies)
                for state, strategies in by_state.items()
            },
            "production": len(by_state[LifecycleState.PRODUCTION]),
            "paper_trading": len(by_state[LifecycleState.PAPER_TRADING]),
            "testing": len(by_state[LifecycleState.TESTING]),
        }
