"""
Strategy Builder
==============

Visual strategy authoring environment.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .blocks import Block, BlockDefinition, BlockType, BlockCategory, BlockPort
from .graph import StrategyGraph, GraphNode, GraphEdge, EdgeType

logger = logging.getLogger(__name__)


class BuilderState(Enum):
    """Builder state"""
    IDLE = "idle"
    BUILDING = "building"
    VALIDATING = "validating"
    VALIDATED = "validated"
    ERROR = "error"


@dataclass
class UndoAction:
    """Action for undo/redo"""
    action_id: str
    action_type: str
    timestamp: datetime
    data: Dict[str, Any]


class StrategyBuilder:
    """
    Visual strategy builder with drag-and-drop support.
    
    Features:
    - Add/remove blocks
    - Connect blocks with edges
    - Validate strategy
    - Generate code/tests/documentation
    - Undo/redo
    - Version history
    """
    
    def __init__(self):
        self.graph = StrategyGraph()
        self.state = BuilderState.IDLE
        
        # Undo/Redo
        self._undo_stack: List[UndoAction] = []
        self._redo_stack: List[UndoAction] = []
        self._max_history = 100
        
        # Validation
        self._validation_cache: Dict[str, Any] = {}
        
        # Callbacks
        self._change_callbacks: List[callable] = []
    
    # === Block Operations ===
    
    def add_block(
        self,
        block_type: BlockType,
        name: str = None,
        position: Tuple[int, int] = (0, 0)
    ) -> Block:
        """Add a new block to the strategy"""
        block = BlockDefinition.create_block(block_type, name)
        block.position = position
        
        node = self.graph.add_node(block)
        
        self._record_action("add_block", {
            "node_id": node.node_id,
            "block": block.to_dict()
        })
        
        self._notify_change()
        
        return block
    
    def remove_block(self, block_id: str) -> bool:
        """Remove a block from the strategy"""
        node_id = self.graph._block_index.get(block_id)
        if not node_id:
            return False
        
        node = self.graph.nodes.get(node_id)
        if not node:
            return False
        
        # Record for undo
        edges = self.graph.get_node_edges(node_id)
        
        self._record_action("remove_block", {
            "node_id": node_id,
            "block": node.block.to_dict(),
            "edges": [e.to_dict() for e in edges]
        })
        
        # Remove
        self.graph.remove_node(node_id)
        
        self._notify_change()
        
        return True
    
    def update_block(self, block_id: str, parameters: Dict[str, Any]) -> bool:
        """Update block parameters"""
        block = self.graph.get_block(block_id)
        if not block:
            return False
        
        old_params = {p.name: p.value for p in block.parameters}
        
        for name, value in parameters.items():
            block.set_parameter(name, value)
        
        self._record_action("update_block", {
            "block_id": block_id,
            "old_parameters": old_params,
            "new_parameters": parameters
        })
        
        self._notify_change()
        
        return True
    
    def move_block(self, block_id: str, position: Tuple[int, int]) -> bool:
        """Move a block to a new position"""
        node_id = self.graph._block_index.get(block_id)
        if not node_id:
            return False
        
        node = self.graph.nodes.get(node_id)
        if not node:
            return False
        
        old_position = node.block.position
        node.block.position = position
        
        self._record_action("move_block", {
            "block_id": block_id,
            "node_id": node_id,
            "old_position": old_position,
            "new_position": position
        })
        
        self._notify_change()
        
        return True
    
    # === Connection Operations ===
    
    def connect(
        self,
        source_block_id: str,
        source_port_id: str,
        target_block_id: str,
        target_port_id: str,
        edge_type: EdgeType = EdgeType.DATA
    ) -> Optional[GraphEdge]:
        """Connect two blocks"""
        edge = self.graph.add_edge(
            source_block_id=source_block_id,
            source_port_id=source_port_id,
            target_block_id=target_block_id,
            target_port_id=target_port_id,
            edge_type=edge_type
        )
        
        if edge:
            self._record_action("connect", {
                "edge": edge.to_dict()
            })
            self._notify_change()
        
        return edge
    
    def disconnect(self, edge_id: str) -> bool:
        """Disconnect two blocks"""
        edge = self.graph.edges.get(edge_id)
        if not edge:
            return False
        
        self._record_action("disconnect", {
            "edge": edge.to_dict()
        })
        
        self.graph.remove_edge(edge_id)
        
        self._notify_change()
        
        return True
    
    # === Validation ===
    
    def validate(self) -> Dict[str, Any]:
        """Validate the strategy"""
        from .validator import StrategyValidator
        
        validator = StrategyValidator()
        result = validator.validate(self.graph)
        
        self.state = BuilderState.VALIDATED if result["valid"] else BuilderState.ERROR
        
        return result
    
    def validate_live(self) -> Dict[str, Any]:
        """Quick live validation"""
        issues = []
        
        # Check for disconnected required inputs
        for node in self.graph.nodes.values():
            for inp in node.block.inputs:
                if inp.required:
                    has_connection = any(
                        e.target_block_id == node.block.block_id and e.target_port_id == inp.port_id
                        for e in self.graph.edges.values()
                    )
                    if not has_connection:
                        issues.append({
                            "type": "disconnected_input",
                            "block_id": node.block.block_id,
                            "port_id": inp.port_id,
                            "message": f"Required input '{inp.name}' is not connected"
                        })
        
        # Check for unreachable blocks
        unreachable = self.graph.find_unreachable_blocks()
        for node in unreachable:
            issues.append({
                "type": "unreachable_block",
                "block_id": node.block.block_id,
                "message": f"Block '{node.block.name}' cannot be reached from inputs"
            })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": self.graph.get_statistics()
        }
    
    # === Undo/Redo ===
    
    def undo(self) -> bool:
        """Undo last action"""
        if not self._undo_stack:
            return False
        
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        
        # Reverse action
        if action.action_type == "add_block":
            self.graph.remove_node(action.data["node_id"])
        elif action.action_type == "remove_block":
            block = Block.from_dict(action.data["block"])
            self.graph.add_node(block, action.data["node_id"])
            for edge_data in action.data.get("edges", []):
                self.graph.add_edge(
                    edge_data["source_block_id"],
                    edge_data["source_port_id"],
                    edge_data["target_block_id"],
                    edge_data["target_port_id"]
                )
        elif action.action_type == "connect":
            self.graph.remove_edge(action.data["edge"]["edge_id"])
        elif action.action_type == "disconnect":
            self.graph.add_edge(
                action.data["edge"]["source_block_id"],
                action.data["edge"]["source_port_id"],
                action.data["edge"]["target_block_id"],
                action.data["edge"]["target_port_id"]
            )
        
        self._notify_change()
        return True
    
    def redo(self) -> bool:
        """Redo last undone action"""
        if not self._redo_stack:
            return False
        
        action = self._redo_stack.pop()
        self._undo_stack.append(action)
        
        # Replay action
        if action.action_type == "add_block":
            block = Block.from_dict(action.data["block"])
            self.graph.add_node(block, action.data["node_id"])
        elif action.action_type == "remove_block":
            self.graph.remove_node(action.data["node_id"])
        elif action.action_type == "connect":
            self.graph.add_edge(
                action.data["edge"]["source_block_id"],
                action.data["edge"]["source_port_id"],
                action.data["edge"]["target_block_id"],
                action.data["edge"]["target_port_id"]
            )
        elif action.action_type == "disconnect":
            self.graph.remove_edge(action.data["edge"]["edge_id"])
        
        self._notify_change()
        return True
    
    def _record_action(self, action_type: str, data: Dict[str, Any]) -> None:
        """Record an action for undo/redo"""
        action = UndoAction(
            action_id=str(uuid4()),
            action_type=action_type,
            timestamp=datetime.now(),
            data=data
        )
        
        self._undo_stack.append(action)
        self._redo_stack.clear()
        
        # Trim history
        if len(self._undo_stack) > self._max_history:
            self._undo_stack = self._undo_stack[-self._max_history:]
    
    # === Code Generation ===
    
    def generate_code(self) -> str:
        """Generate executable code from strategy"""
        from .generator import CodeGenerator
        
        generator = CodeGenerator()
        return generator.generate(self.graph)
    
    def generate_tests(self) -> str:
        """Generate unit tests"""
        from .generator import TestGenerator
        
        generator = TestGenerator()
        return generator.generate(self.graph)
    
    def generate_documentation(self) -> str:
        """Generate documentation"""
        from .generator import DocumentationGenerator
        
        generator = DocumentationGenerator()
        return generator.generate(self.graph)
    
    # === Persistence ===
    
    def save(self) -> Dict[str, Any]:
        """Save strategy to dictionary"""
        return self.graph.to_dict()
    
    def load(self, data: Dict[str, Any]) -> None:
        """Load strategy from dictionary"""
        self.graph = StrategyGraph.from_dict(data)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_change()
    
    # === Callbacks ===
    
    def register_change_callback(self, callback: callable) -> None:
        """Register a callback for changes"""
        self._change_callbacks.append(callback)
    
    def _notify_change(self) -> None:
        """Notify all callbacks of changes"""
        for callback in self._change_callbacks:
            try:
                callback(self.graph)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    # === Utilities ===
    
    def get_available_blocks(self) -> Dict[BlockCategory, List[BlockType]]:
        """Get available block types by category"""
        available = {}
        
        for block_type, definition in BlockDefinition.get_all_definitions().items():
            category = BlockCategory(definition.get("category", "logic"))
            if category not in available:
                available[category] = []
            available[category].append(block_type)
        
        return available
    
    def suggest_simplifications(self) -> List[Dict[str, Any]]:
        """Suggest strategy simplifications"""
        suggestions = []
        
        # Find redundant logic blocks
        logic_blocks = [
            n for n in self.graph.nodes.values()
            if n.block.category == BlockCategory.LOGIC
        ]
        
        # Suggest combining consecutive AND/OR blocks
        for node in logic_blocks:
            incoming = self.graph.get_incoming_edges(node.node_id)
            outgoing = self.graph.get_outgoing_edges(node.node_id)
            
            if len(incoming) == 1 and len(outgoing) == 1:
                suggestions.append({
                    "type": "merge_blocks",
                    "blocks": [node.block.block_id, outgoing[0].target_block_id],
                    "reason": "Consecutive logic blocks can be merged"
                })
        
        # Suggest removing unused blocks
        unreachable = self.graph.find_unreachable_blocks()
        if unreachable:
            suggestions.append({
                "type": "remove_unreachable",
                "blocks": [n.block.block_id for n in unreachable],
                "reason": "Remove unreachable blocks to simplify strategy"
            })
        
        return suggestions
    
    def estimate_performance(self) -> Dict[str, Any]:
        """Estimate strategy performance characteristics"""
        stats = self.graph.get_statistics()
        
        # Estimate based on block types
        ml_blocks = sum(
            1 for n in self.graph.nodes.values()
            if n.block.category == BlockCategory.ML
        )
        
        indicator_blocks = sum(
            1 for n in self.graph.nodes.values()
            if n.block.category == BlockCategory.INDICATOR
        )
        
        # Rough estimates
        avg_bar_time = 0.001  # 1ms base
        if indicator_blocks > 0:
            avg_bar_time *= (1 + indicator_blocks * 0.5)
        if ml_blocks > 0:
            avg_bar_time *= (1 + ml_blocks * 5)
        
        return {
            "estimated_bars_per_second": 1 / avg_bar_time if avg_bar_time > 0 else float('inf'),
            "estimated_latency_ms": avg_bar_time * 1000,
            "estimated_memory_mb": stats["total_cost"] * 0.1,
            "complexity_score": stats["total_cost"],
            "recommendation": self._get_performance_recommendation(stats)
        }
    
    def _get_performance_recommendation(self, stats: Dict) -> str:
        """Get performance recommendation"""
        cost = stats.get("total_cost", 0)
        
        if cost < 10:
            return "Low complexity - suitable for real-time trading"
        elif cost < 50:
            return "Medium complexity - consider optimization for production"
        elif cost < 100:
            return "High complexity - recommend backtesting for performance"
        else:
            return "Very high complexity - may require specialized infrastructure"
