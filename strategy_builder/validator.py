"""
Strategy Validator
================

Validates strategies for correctness and best practices.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .blocks import Block, BlockCategory, BlockType, PortType
from .graph import StrategyGraph

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class ValidationIssue:
    """A single validation issue"""
    issue_id: str
    level: ValidationLevel
    category: str
    message: str
    
    # Location
    block_id: Optional[str] = None
    edge_id: Optional[str] = None
    
    # Suggestion
    suggestion: Optional[str] = None
    auto_fix: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "block_id": self.block_id,
            "edge_id": self.edge_id,
            "suggestion": self.suggestion,
            "auto_fix": self.auto_fix
        }


@dataclass
class ValidationResult:
    """Result of validation"""
    valid: bool
    timestamp: datetime
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Statistics
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    
    # Cost analysis
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    
    def __post_init__(self):
        self.error_count = sum(1 for i in self.issues if i.level == ValidationLevel.ERROR)
        self.warning_count = sum(1 for i in self.issues if i.level == ValidationLevel.WARNING)
        self.info_count = sum(1 for i in self.issues if i.level in [ValidationLevel.INFO, ValidationLevel.SUGGESTION])
        self.valid = self.error_count == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "timestamp": self.timestamp.isoformat(),
            "issues": [i.to_dict() for i in self.issues],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "estimated_cost": self.estimated_cost,
            "estimated_latency_ms": self.estimated_latency_ms
        }


class StrategyValidator:
    """
    Validates strategies for correctness, best practices, and performance.
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self._issue_counter = 0
    
    def _add_issue(
        self,
        level: ValidationLevel,
        category: str,
        message: str,
        block_id: str = None,
        edge_id: str = None,
        suggestion: str = None
    ) -> ValidationIssue:
        """Add a validation issue"""
        self._issue_counter += 1
        issue = ValidationIssue(
            issue_id=f"issue_{self._issue_counter}",
            level=level,
            category=category,
            message=message,
            block_id=block_id,
            edge_id=edge_id,
            suggestion=suggestion
        )
        self.issues.append(issue)
        return issue
    
    def validate(self, graph: StrategyGraph) -> Dict[str, Any]:
        """Run full validation on strategy"""
        self.issues = []
        self._issue_counter = 0
        
        # Structural validation
        self._validate_structure(graph)
        
        # Connection validation
        self._validate_connections(graph)
        
        # Parameter validation
        self._validate_parameters(graph)
        
        # Risk validation
        self._validate_risk(graph)
        
        # Best practices
        self._validate_best_practices(graph)
        
        # Calculate cost
        cost = graph.calculate_total_cost()
        latency_ms = cost * 10  # Rough estimate
        
        result = ValidationResult(
            valid=True,
            timestamp=datetime.now(),
            issues=self.issues,
            estimated_cost=cost,
            estimated_latency_ms=latency_ms
        )
        
        logger.info(f"Validation complete: {result.error_count} errors, {result.warning_count} warnings")
        
        return result.to_dict()
    
    def _validate_structure(self, graph: StrategyGraph) -> None:
        """Validate graph structure"""
        # Check for empty graph
        if len(graph.nodes) == 0:
            self._add_issue(
                ValidationLevel.ERROR,
                "structure",
                "Strategy has no blocks"
            )
            return
        
        # Check for source nodes
        sources = graph.get_source_nodes()
        if not sources:
            self._add_issue(
                ValidationLevel.ERROR,
                "structure",
                "Strategy has no input blocks (no data source)",
                suggestion="Add a Market Data block to start the strategy"
            )
        
        # Check for sink nodes
        sinks = graph.get_sink_nodes()
        if not sinks:
            self._add_issue(
                ValidationLevel.WARNING,
                "structure",
                "Strategy has no output blocks (no execution or notification)"
            )
        
        # Check for unreachable blocks
        unreachable = graph.find_unreachable_blocks()
        for node in unreachable:
            self._add_issue(
                ValidationLevel.WARNING,
                "structure",
                f"Block '{node.block.name}' is not reachable from any input",
                block_id=node.block.block_id,
                suggestion="Connect the block or remove it"
            )
        
        # Check for isolated blocks
        for node in graph.nodes.values():
            edges = graph.get_node_edges(node.node_id)
            if len(edges) == 0 and len(graph.nodes) > 1:
                self._add_issue(
                    ValidationLevel.WARNING,
                    "structure",
                    f"Block '{node.block.name}' is isolated (not connected)",
                    block_id=node.block.block_id
                )
    
    def _validate_connections(self, graph: StrategyGraph) -> None:
        """Validate block connections"""
        for node in graph.nodes.values():
            block = node.block
            
            # Check required inputs
            for inp in block.inputs:
                if inp.required:
                    has_connection = any(
                        e.target_block_id == block.block_id and e.target_port_id == inp.port_id
                        for e in graph.edges.values()
                    )
                    
                    if not has_connection:
                        self._add_issue(
                            ValidationLevel.ERROR,
                            "connection",
                            f"Required input '{inp.name}' of '{block.name}' is not connected",
                            block_id=block.block_id,
                            suggestion=f"Connect a block to the '{inp.name}' port"
                        )
            
            # Check port type compatibility
            for edge in graph.edges.values():
                if edge.target_block_id == block.block_id:
                    # Find source block
                    source_node_id = graph._block_index.get(edge.source_block_id)
                    if source_node_id:
                        source_node = graph.nodes.get(source_node_id)
                        if source_node:
                            # Find output port
                            source_port = None
                            for port in source_node.block.outputs:
                                if port.port_id == edge.source_port_id:
                                    source_port = port
                                    break
                            
                            # Find input port
                            target_port = None
                            for port in block.inputs:
                                if port.port_id == edge.target_port_id:
                                    target_port = port
                                    break
                            
                            # Check compatibility
                            if source_port and target_port:
                                if not self._ports_compatible(source_port, target_port):
                                    self._add_issue(
                                        ValidationLevel.WARNING,
                                        "connection",
                                        f"Port type mismatch: '{source_port.name}' ({source_port.port_type.value}) to '{target_port.name}' ({target_port.port_type.value})",
                                        block_id=block.block_id,
                                        edge_id=edge.edge_id
                                    )
    
    def _ports_compatible(self, source: Any, target: Any) -> bool:
        """Check if port types are compatible"""
        # Direct match
        if source.port_type == target.port_type:
            return True
        
        # Series can connect to number (for latest value)
        if source.port_type == PortType.SERIES and target.port_type in [PortType.NUMBER, PortType.SIGNAL]:
            return True
        
        # Number can connect to signal
        if source.port_type == PortType.NUMBER and target.port_type == PortType.SIGNAL:
            return True
        
        return False
    
    def _validate_parameters(self, graph: StrategyGraph) -> None:
        """Validate block parameters"""
        for node in graph.nodes.values():
            block = node.block
            
            for param in block.parameters:
                # Check for invalid values
                if param.param_type == "range":
                    if param.min_value is not None and param.value < param.min_value:
                        self._add_issue(
                            ValidationLevel.ERROR,
                            "parameter",
                            f"Parameter '{param.name}' value {param.value} is below minimum {param.min_value}",
                            block_id=block.block_id,
                            suggestion=f"Set '{param.name}' to at least {param.min_value}"
                        )
                    
                    if param.max_value is not None and param.value > param.max_value:
                        self._add_issue(
                            ValidationLevel.ERROR,
                            "parameter",
                            f"Parameter '{param.name}' value {param.value} exceeds maximum {param.max_value}",
                            block_id=block.block_id,
                            suggestion=f"Set '{param.name}' to at most {param.max_value}"
                        )
                
                # Check for zero values where not allowed
                if param.name in ["period", "window", "threshold"] and param.value == 0:
                    self._add_issue(
                        ValidationLevel.ERROR,
                        "parameter",
                        f"Parameter '{param.name}' cannot be zero",
                        block_id=block.block_id,
                        suggestion="Set a positive value for this parameter"
                    )
    
    def _validate_risk(self, graph: StrategyGraph) -> None:
        """Validate risk management"""
        has_stop_loss = any(
            n.block.block_type == BlockType.STOP_LOSS
            for n in graph.nodes.values()
        )
        
        has_position_size = any(
            n.block.block_type == BlockType.POSITION_SIZE
            for n in graph.nodes.values()
        )
        
        has_risk_block = any(
            n.block.category == BlockCategory.RISK
            for n in graph.nodes.values()
        )
        
        has_execution = any(
            n.block.category == BlockCategory.EXECUTION
            for n in graph.nodes.values()
        )
        
        if has_execution and not has_position_size:
            self._add_issue(
                ValidationLevel.WARNING,
                "risk",
                "Strategy has execution blocks but no position sizing",
                suggestion="Add a Position Size block to manage risk"
            )
        
        if has_execution and not has_stop_loss:
            self._add_issue(
                ValidationLevel.WARNING,
                "risk",
                "Strategy has execution blocks but no stop loss",
                suggestion="Add a Stop Loss block to limit losses"
            )
        
        if not has_risk_block and has_execution:
            self._add_issue(
                ValidationLevel.INFO,
                "risk",
                "Strategy has no risk management blocks",
                suggestion="Consider adding risk rules for better protection"
            )
    
    def _validate_best_practices(self, graph: StrategyGraph) -> None:
        """Validate best practices"""
        # Check for hardcoded values
        for node in graph.nodes.values():
            block = node.block
            
            # Check for magic numbers in parameters
            for param in block.parameters:
                if param.param_type == "number":
                    if isinstance(param.value, (int, float)):
                        if param.value > 1000 and param.name not in ["threshold", "price"]:
                            self._add_issue(
                                ValidationLevel.SUGGESTION,
                                "best_practice",
                                f"Large numeric value in '{param.name}': {param.value}",
                                block_id=block.block_id,
                                suggestion="Consider using a variable or parameter block"
                            )
        
        # Check for missing notifications
        has_notification = any(
            n.block.category == BlockCategory.NOTIFICATION
            for n in graph.nodes.values()
        )
        
        if not has_notification:
            self._add_issue(
                ValidationLevel.SUGGESTION,
                "best_practice",
                "Strategy has no notification blocks",
                suggestion="Add notifications for important events"
            )
        
        # Check for long chains of logic blocks
        execution_order = graph.get_execution_order()
        logic_depth = 0
        max_logic_depth = 0
        last_logic_node = None
        
        for depth, node in execution_order:
            if node.block.category == BlockCategory.LOGIC:
                logic_depth += 1
                max_logic_depth = max(max_logic_depth, logic_depth)
                last_logic_node = node
            else:
                logic_depth = 0
        
        if max_logic_depth > 5:
            self._add_issue(
                ValidationLevel.WARNING,
                "best_practice",
                f"Long chain of {max_logic_depth} consecutive logic blocks",
                suggestion="Consider simplifying with decision tables or rule engines"
            )
