"""
Strategy Studio - Main Integration Module

Central hub for all strategy development components.
"""

import logging
from typing import Any, Dict, List, Optional

from strategy_studio.builder import VisualBuilder, StrategyGraph, BlockType
from strategy_studio.compiler import StrategyCompiler, CompiledStrategy
from strategy_studio.lifecycle import LifecycleManager, LifecycleState
from strategy_studio.comparison import StrategyComparisonCenter, ComparisonResult
from strategy_studio.coach import AIStrategyCoach, CoachAnalysis

logger = logging.getLogger(__name__)


class StrategyStudio:
    """
    AI Strategy Studio - Professional Strategy Development Platform
    
    Integrates all strategy development components:
    - Visual Strategy Builder
    - Strategy Compiler
    - AI Strategy Generator
    - Strategy Library
    - Strategy Comparison Center
    - AI Strategy Coach
    - Feature Marketplace
    - Hyperparameter Optimization
    - Walk-Forward Evaluation
    - Strategy Lifecycle Manager
    - AI Research Notebook
    - Collaboration Layer
    - Experiment Tracking
    - Quality Gates
    - Institutional Dashboard
    """
    
    def __init__(self):
        # Core components
        self.builder = VisualBuilder()
        self.compiler = StrategyCompiler()
        self.lifecycle = LifecycleManager()
        self.comparison = StrategyComparisonCenter(self.lifecycle)
        self.coach = AIStrategyCoach()
        
        # State
        self._current_strategy_id: Optional[str] = None
        self._current_graph: Optional[StrategyGraph] = None
        
        logger.info("Strategy Studio initialized")
    
    # ========================================================================
    # Strategy Creation
    # ========================================================================
    
    def create_strategy(self, name: str, description: str = "") -> StrategyGraph:
        """Create a new strategy"""
        self._current_graph = self.builder.create_graph(name, description)
        return self._current_graph
    
    def load_strategy(self, data: Dict[str, Any]) -> StrategyGraph:
        """Load a strategy from data"""
        self._current_graph = self.builder.load_graph(data)
        return self._current_graph
    
    def add_block(
        self,
        block_type: BlockType,
        name: Optional[str] = None,
        position: Optional[tuple] = None,
    ):
        """Add a block to the current strategy"""
        if not self._current_graph:
            raise ValueError("No strategy selected. Call create_strategy first.")
        return self.builder.add_block(block_type, name, position)
    
    def connect_blocks(
        self,
        source_block_id: str,
        source_port_id: str,
        target_block_id: str,
        target_port_id: str,
    ):
        """Connect two blocks"""
        return self.builder.connect(
            source_block_id, source_port_id,
            target_block_id, target_port_id
        )
    
    def validate_strategy(self) -> tuple[bool, List[str]]:
        """Validate the current strategy graph"""
        return self.builder.validate_graph()
    
    def compile_strategy(self) -> CompiledStrategy:
        """Compile the current strategy"""
        if not self._current_graph:
            raise ValueError("No strategy selected")
        
        # Validate first
        is_valid, errors = self.validate_strategy()
        if not is_valid:
            return CompiledStrategy(
                name=self._current_graph.name,
                source_code="",
                status=self.compiler.CompilationStatus.FAILED,
                errors=errors,
            )
        
        return self.compiler.compile(self._current_graph)
    
    # ========================================================================
    # Strategy Lifecycle
    # ========================================================================
    
    def register_strategy(
        self,
        name: str,
        author: str = "",
    ) -> Dict[str, Any]:
        """Register a strategy with the lifecycle manager"""
        if not self._current_graph:
            raise ValueError("No strategy selected")
        
        # Compile first
        compiled = self.compile_strategy()
        if compiled.status != self.compiler.CompilationStatus.SUCCESS:
            raise ValueError(f"Strategy compilation failed: {compiled.errors}")
        
        # Create version with source code
        strategy_id = self._current_graph.id
        
        strategy = self.lifecycle.register_strategy(
            strategy_id=strategy_id,
            name=name,
            graph=self._current_graph,
            author=author,
        )
        
        self._current_strategy_id = strategy_id
        return strategy
    
    def transition_strategy(
        self,
        strategy_id: str,
        target_state: LifecycleState,
        reason: str,
    ) -> tuple[bool, str]:
        """Transition a strategy to a new lifecycle state"""
        return self.lifecycle.transition(strategy_id, target_state, reason)
    
    def get_strategy_state(self, strategy_id: str) -> Optional[LifecycleState]:
        """Get current state of a strategy"""
        strategy = self.lifecycle.get_strategy(strategy_id)
        return strategy["state"] if strategy else None
    
    def can_promote(self, strategy_id: str, target_state: LifecycleState) -> tuple[bool, str]:
        """Check if a strategy can be promoted"""
        return self.lifecycle.can_transition(strategy_id, target_state)
    
    # ========================================================================
    # Strategy Analysis
    # ========================================================================
    
    def analyze_strategy(
        self,
        strategy_id: str,
        backtest_results: Dict[str, Any],
    ) -> CoachAnalysis:
        """Analyze a strategy with the AI Coach"""
        strategy = self.lifecycle.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        return self.coach.analyze(
            strategy_id=strategy_id,
            strategy_name=strategy["name"],
            backtest_results=backtest_results,
        )
    
    def compare_strategies(
        self,
        strategy_ids: List[str],
        dataset_name: str,
        start_date: Any,
        end_date: Any,
        symbols: List[str],
        name: Optional[str] = None,
    ) -> ComparisonResult:
        """Compare multiple strategies"""
        return self.comparison.compare_strategies(
            strategy_ids=strategy_ids,
            dataset_name=dataset_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            name=name,
        )
    
    # ========================================================================
    # Dashboard
    # ========================================================================
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get institutional dashboard summary"""
        lifecycle_stats = self.lifecycle.get_statistics()
        by_state = self.lifecycle.get_strategies_by_state()
        
        # Get production strategies
        production = by_state[LifecycleState.PRODUCTION]
        paper_trading = by_state[LifecycleState.PAPER_TRADING]
        testing = by_state[LifecycleState.TESTING]
        
        # Calculate aggregate metrics
        total_return = 0
        avg_sharpe = 0
        total_trades = 0
        
        for strategy in production + paper_trading:
            metrics = strategy["metrics"]
            total_return += metrics.total_return
            avg_sharpe += metrics.sharpe_ratio
            total_trades += metrics.trades_count
        
        n = len(production + paper_trading) or 1
        avg_sharpe /= n
        
        return {
            "overview": {
                "total_strategies": lifecycle_stats["total_strategies"],
                "production": len(production),
                "paper_trading": len(paper_trading),
                "testing": len(testing),
            },
            "performance": {
                "total_return": total_return,
                "avg_sharpe_ratio": avg_sharpe,
                "total_trades": total_trades,
            },
            "pipeline": {
                "draft": len(by_state[LifecycleState.DRAFT]),
                "testing": len(testing),
                "paper_trading": len(paper_trading),
                "validated": len(by_state[LifecycleState.VALIDATED]),
                "production": len(production),
                "paused": len(by_state[LifecycleState.PAUSED]),
            },
            "recent_analyses": self._get_recent_analyses(),
            "leaderboard": self.comparison.get_leaderboard()[:5],
        }
    
    def _get_recent_analyses(self) -> List[Dict[str, Any]]:
        """Get recent AI Coach analyses"""
        recent = []
        for strategy_id in self.coach._analysis_history:
            history = self.coach._analysis_history[strategy_id]
            if history:
                latest = history[-1]
                recent.append({
                    "strategy_id": latest.strategy_id,
                    "strategy_name": latest.strategy_name,
                    "overall_score": latest.overall_score,
                    "readiness_level": latest.readiness_level,
                    "issues_count": len(latest.issues),
                    "analyzed_at": latest.analyzed_at.isoformat(),
                })
        
        # Sort by date and return top 5
        recent.sort(key=lambda x: x["analyzed_at"], reverse=True)
        return recent[:5]
    
    # ========================================================================
    # Export
    # ========================================================================
    
    def export_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Export a strategy"""
        strategy = self.lifecycle.get_strategy(strategy_id)
        if not strategy:
            return None
        
        return {
            "id": strategy["id"],
            "name": strategy["name"],
            "state": strategy["state"].value,
            "graph": strategy["graph"],
            "author": strategy["author"],
            "created_at": strategy["created_at"].isoformat(),
            "metrics": strategy["metrics"].to_dict(),
        }
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Get all strategies with summary info"""
        strategies = []
        
        for strategy in self.lifecycle.get_all_strategies():
            strategies.append({
                "id": strategy["id"],
                "name": strategy["name"],
                "state": strategy["state"].value,
                "author": strategy["author"],
                "metrics": strategy["metrics"].to_dict(),
                "created_at": strategy["created_at"].isoformat(),
            })
        
        return strategies
