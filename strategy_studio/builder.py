"""
Visual Strategy Builder - Block-Based Strategy Designer

Drag-and-drop strategy designer using reusable blocks.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class BlockType(Enum):
    """Types of strategy blocks"""
    # Data blocks
    MARKET_DATA = "market_data"
    INDICATOR = "indicator"
    STATISTICAL_FEATURE = "statistical_feature"
    PATTERN_RECOGNITION = "pattern_recognition"
    
    # AI blocks
    ML_MODEL = "ml_model"
    CONFIDENCE_FILTER = "confidence_filter"
    REGIME_CLASSIFIER = "regime_classifier"
    
    # Logic blocks
    CONDITION = "condition"
    LOGIC_GATE = "logic_gate"
    TIME_FILTER = "time_filter"
    SESSION_FILTER = "session_filter"
    
    # Risk blocks
    RISK_RULE = "risk_rule"
    POSITION_SIZING = "position_sizing"
    PORTFOLIO_CONSTRAINT = "portfolio_constraint"
    
    # Execution blocks
    TRADE_EXECUTION = "trade_execution"
    ORDER_TYPE = "order_type"
    
    # Utility blocks
    NOTIFICATION = "notification"
    MEMORY_RETRIEVAL = "memory_retrieval"
    VARIABLE = "variable"
    FUNCTION = "function"


class BlockCategory(Enum):
    """Block categories"""
    DATA = "data"
    AI = "ai"
    LOGIC = "logic"
    RISK = "risk"
    EXECUTION = "execution"
    UTILITY = "utility"


@dataclass
class Port:
    """Input or output port for a block"""
    id: str
    name: str
    data_type: str  # "number", "boolean", "string", "any"
    required: bool = True
    default_value: Any = None
    description: str = ""


@dataclass
class BlockConfig:
    """Configuration for a block instance"""
    parameters: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    # UI state
    position_x: float = 0
    position_y: float = 0
    width: float = 200
    height: float = 100
    collapsed: bool = False


@dataclass
class StrategyBlock:
    """A single block in the strategy graph"""
    id: str
    block_type: BlockType
    name: str
    category: BlockCategory
    
    # Ports
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
    
    # Configuration
    config: BlockConfig = field(default_factory=BlockConfig)
    
    # Metadata
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Block definition
    is_builtin: bool = True
    python_code: Optional[str] = None  # For custom blocks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "block_type": self.block_type.value,
            "name": self.name,
            "category": self.category.value,
            "inputs": [{"id": p.id, "name": p.name, "data_type": p.data_type} for p in self.inputs],
            "outputs": [{"id": p.id, "name": p.name, "data_type": p.data_type} for p in self.outputs],
            "config": {
                "parameters": self.config.parameters,
                "position_x": self.config.position_x,
                "position_y": self.config.position_y,
            },
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
        }


@dataclass
class Connection:
    """A connection between two blocks"""
    id: str
    source_block_id: str
    source_port_id: str
    target_block_id: str
    target_port_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_block_id": self.source_block_id,
            "source_port_id": self.source_port_id,
            "target_block_id": self.target_block_id,
            "target_port_id": self.target_port_id,
        }


@dataclass
class StrategyGraph:
    """A complete strategy graph"""
    id: str
    name: str
    description: str = ""
    
    blocks: List[StrategyBlock] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0.0"
    author: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # State
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "blocks": [b.to_dict() for b in self.blocks],
            "connections": [c.to_dict() for c in self.connections],
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_valid": self.is_valid,
        }


class BlockLibrary:
    """Library of available blocks"""
    
    @staticmethod
    def get_builtin_blocks() -> Dict[str, StrategyBlock]:
        """Get all builtin blocks"""
        return {
            # Market Data
            "market_data": StrategyBlock(
                id="market_data",
                block_type=BlockType.MARKET_DATA,
                name="Market Data",
                category=BlockCategory.DATA,
                description="Get current market data",
                inputs=[],
                outputs=[
                    Port("price", "Price", "number"),
                    Port("bid", "Bid", "number"),
                    Port("ask", "Ask", "number"),
                    Port("volume", "Volume", "number"),
                ],
            ),
            
            # Indicators
            "rsi": StrategyBlock(
                id="rsi",
                block_type=BlockType.INDICATOR,
                name="RSI",
                category=BlockCategory.DATA,
                description="Relative Strength Index",
                inputs=[Port("price", "Price", "number")],
                outputs=[Port("value", "RSI Value", "number")],
            ),
            "moving_average": StrategyBlock(
                id="moving_average",
                block_type=BlockType.INDICATOR,
                name="Moving Average",
                category=BlockCategory.DATA,
                description="Simple or Exponential Moving Average",
                inputs=[Port("price", "Price", "number")],
                outputs=[Port("value", "MA Value", "number")],
                config=BlockConfig(parameters={"period": 14, "type": "SMA"}),
            ),
            "bollinger_bands": StrategyBlock(
                id="bollinger_bands",
                block_type=BlockType.INDICATOR,
                name="Bollinger Bands",
                category=BlockCategory.DATA,
                description="Bollinger Bands indicator",
                inputs=[Port("price", "Price", "number")],
                outputs=[
                    Port("upper", "Upper Band", "number"),
                    Port("middle", "Middle Band", "number"),
                    Port("lower", "Lower Band", "number"),
                ],
            ),
            
            # Statistical Features
            "entropy": StrategyBlock(
                id="entropy",
                block_type=BlockType.STATISTICAL_FEATURE,
                name="Entropy",
                category=BlockCategory.DATA,
                description="Calculate Shannon entropy",
                inputs=[Port("data", "Data", "any")],
                outputs=[Port("value", "Entropy", "number")],
                config=BlockConfig(parameters={"window": 20}),
            ),
            "volatility": StrategyBlock(
                id="volatility",
                block_type=BlockType.STATISTICAL_FEATURE,
                name="Volatility",
                category=BlockCategory.DATA,
                description="Historical volatility measure",
                inputs=[Port("returns", "Returns", "any")],
                outputs=[Port("value", "Volatility", "number")],
            ),
            "momentum": StrategyBlock(
                id="momentum",
                block_type=BlockType.STATISTICAL_FEATURE,
                name="Momentum",
                category=BlockCategory.DATA,
                description="Price momentum indicator",
                inputs=[Port("price", "Price", "number")],
                outputs=[Port("value", "Momentum", "number")],
            ),
            
            # Confidence Filter
            "confidence_filter": StrategyBlock(
                id="confidence_filter",
                block_type=BlockType.CONFIDENCE_FILTER,
                name="Confidence Filter",
                category=BlockCategory.AI,
                description="Filter signals based on confidence threshold",
                inputs=[
                    Port("signal", "Signal", "any"),
                    Port("confidence", "Confidence", "number"),
                ],
                outputs=[Port("filtered", "Filtered Signal", "any")],
                config=BlockConfig(parameters={"threshold": 70}),
            ),
            
            # Regime Classifier
            "regime_classifier": StrategyBlock(
                id="regime_classifier",
                block_type=BlockType.REGIME_CLASSIFIER,
                name="Regime Classifier",
                category=BlockCategory.AI,
                description="Classify market regime",
                inputs=[Port("features", "Features", "any")],
                outputs=[
                    Port("regime", "Regime", "string"),
                    Port("confidence", "Confidence", "number"),
                ],
            ),
            
            # Condition
            "condition": StrategyBlock(
                id="condition",
                block_type=BlockType.CONDITION,
                name="Condition",
                category=BlockCategory.LOGIC,
                description="Evaluate a condition",
                inputs=[
                    Port("a", "Value A", "any"),
                    Port("b", "Value B", "any"),
                ],
                outputs=[Port("result", "Result", "boolean")],
                config=BlockConfig(parameters={"operator": ">"}),
            ),
            
            # Logic Gate
            "logic_gate": StrategyBlock(
                id="logic_gate",
                block_type=BlockType.LOGIC_GATE,
                name="Logic Gate",
                category=BlockCategory.LOGIC,
                description="AND, OR, NOT gate",
                inputs=[
                    Port("input1", "Input 1", "boolean"),
                    Port("input2", "Input 2", "boolean"),
                ],
                outputs=[Port("output", "Output", "boolean")],
                config=BlockConfig(parameters={"gate_type": "AND"}),
            ),
            
            # Time Filter
            "time_filter": StrategyBlock(
                id="time_filter",
                block_type=BlockType.TIME_FILTER,
                name="Time Filter",
                category=BlockCategory.LOGIC,
                description="Filter by time of day",
                inputs=[Port("signal", "Signal", "any")],
                outputs=[Port("filtered", "Filtered", "any")],
                config=BlockConfig(parameters={"start_hour": 9, "end_hour": 16}),
            ),
            
            # Risk Rule
            "risk_rule": StrategyBlock(
                id="risk_rule",
                block_type=BlockType.RISK_RULE,
                name="Risk Rule",
                category=BlockCategory.RISK,
                description="Apply risk management rule",
                inputs=[Port("signal", "Signal", "any")],
                outputs=[Port("approved", "Approved", "boolean"), Port("reason", "Reason", "string")],
            ),
            
            # Position Sizing
            "position_sizing": StrategyBlock(
                id="position_sizing",
                block_type=BlockType.POSITION_SIZING,
                name="Position Sizing",
                category=BlockCategory.RISK,
                description="Calculate position size",
                inputs=[Port("signal", "Signal", "any"), Port("balance", "Balance", "number")],
                outputs=[Port("size", "Size", "number")],
                config=BlockConfig(parameters={"method": "fixed", "size": 10}),
            ),
            
            # Trade Execution
            "trade_execution": StrategyBlock(
                id="trade_execution",
                block_type=BlockType.TRADE_EXECUTION,
                name="Execute Trade",
                category=BlockCategory.EXECUTION,
                description="Execute a trade",
                inputs=[
                    Port("signal", "Signal", "any"),
                    Port("size", "Size", "number"),
                ],
                outputs=[Port("order_id", "Order ID", "string"), Port("status", "Status", "string")],
                config=BlockConfig(parameters={"order_type": "market"}),
            ),
            
            # Notification
            "notification": StrategyBlock(
                id="notification",
                block_type=BlockType.NOTIFICATION,
                name="Send Notification",
                category=BlockCategory.UTILITY,
                description="Send a notification",
                inputs=[Port("message", "Message", "string")],
                outputs=[],
                config=BlockConfig(parameters={"channel": "all"}),
            ),
            
            # Memory Retrieval
            "memory_retrieval": StrategyBlock(
                id="memory_retrieval",
                block_type=BlockType.MEMORY_RETRIEVAL,
                name="Memory Lookup",
                category=BlockCategory.UTILITY,
                description="Retrieve from memory",
                inputs=[Port("query", "Query", "string")],
                outputs=[Port("result", "Result", "any")],
                config=BlockConfig(parameters={"memory_type": "pattern"}),
            ),
        }


class VisualBuilder:
    """
    Visual strategy builder with drag-and-drop blocks.
    
    Features:
    - Block library
    - Graph editing
    - Connection management
    - Validation
    - Import/export
    """
    
    def __init__(self):
        self._blocks: Dict[str, StrategyBlock] = {}
        self._current_graph: Optional[StrategyGraph] = None
        self._block_library = BlockLibrary()
        
        # Load builtin blocks
        for block_id, block in self._block_library.get_builtin_blocks().items():
            self._blocks[block_id] = block
    
    def create_graph(self, name: str, description: str = "") -> StrategyGraph:
        """Create a new strategy graph"""
        self._current_graph = StrategyGraph(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
        )
        return self._current_graph
    
    def load_graph(self, data: Dict[str, Any]) -> StrategyGraph:
        """Load a graph from data"""
        graph = StrategyGraph(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
        )
        
        # Load blocks
        for block_data in data.get("blocks", []):
            block_type = BlockType(block_data["block_type"])
            category = BlockCategory(block_data["category"])
            
            block = StrategyBlock(
                id=block_data["id"],
                block_type=block_type,
                name=block_data["name"],
                category=category,
                description=block_data.get("description", ""),
                inputs=[Port(**p) for p in block_data.get("inputs", [])],
                outputs=[Port(**p) for p in block_data.get("outputs", [])],
                config=BlockConfig(
                    parameters=block_data.get("config", {}).get("parameters", {}),
                    position_x=block_data.get("config", {}).get("position_x", 0),
                    position_y=block_data.get("config", {}).get("position_y", 0),
                ),
            )
            graph.blocks.append(block)
        
        # Load connections
        for conn_data in data.get("connections", []):
            connection = Connection(
                id=conn_data["id"],
                source_block_id=conn_data["source_block_id"],
                source_port_id=conn_data["source_port_id"],
                target_block_id=conn_data["target_block_id"],
                target_port_id=conn_data["target_port_id"],
            )
            graph.connections.append(connection)
        
        self._current_graph = graph
        return graph
    
    def add_block(
        self,
        block_type: BlockType,
        name: Optional[str] = None,
        position: Optional[tuple[float, float]] = None,
    ) -> StrategyBlock:
        """Add a block to the current graph"""
        if not self._current_graph:
            raise ValueError("No graph selected")
        
        # Get block definition
        block_def = self._block_library.get_builtin_blocks().get(block_type.value)
        if not block_def:
            raise ValueError(f"Unknown block type: {block_type}")
        
        # Create instance
        block = StrategyBlock(
            id=str(uuid.uuid4()),
            block_type=block_type,
            name=name or block_def.name,
            category=block_def.category,
            description=block_def.description,
            inputs=[Port(**p.__dict__) for p in block_def.inputs],
            outputs=[Port(**p.__dict__) for p in block_def.outputs],
            config=BlockConfig(
                parameters=block_def.config.parameters.copy(),
                position_x=position[0] if position else 0,
                position_y=position[1] if position else 0,
            ),
        )
        
        self._current_graph.blocks.append(block)
        self._current_graph.updated_at = datetime.utcnow()
        
        return block
    
    def remove_block(self, block_id: str) -> bool:
        """Remove a block and its connections"""
        if not self._current_graph:
            return False
        
        # Remove block
        self._current_graph.blocks = [
            b for b in self._current_graph.blocks if b.id != block_id
        ]
        
        # Remove connections
        self._current_graph.connections = [
            c for c in self._current_graph.connections
            if c.source_block_id != block_id and c.target_block_id != block_id
        ]
        
        self._current_graph.updated_at = datetime.utcnow()
        return True
    
    def connect(
        self,
        source_block_id: str,
        source_port_id: str,
        target_block_id: str,
        target_port_id: str,
    ) -> Optional[Connection]:
        """Connect two blocks"""
        if not self._current_graph:
            return None
        
        # Validate blocks exist
        source_block = self._get_block(source_block_id)
        target_block = self._get_block(target_block_id)
        
        if not source_block or not target_block:
            return None
        
        # Validate ports
        source_port = self._get_port(source_block, source_port_id, is_output=True)
        target_port = self._get_port(target_block, target_port_id, is_output=False)
        
        if not source_port or not target_port:
            return None
        
        # Check for existing connection to target port
        for conn in self._current_graph.connections:
            if conn.target_block_id == target_block_id and conn.target_port_id == target_port_id:
                return None  # Port already connected
        
        connection = Connection(
            id=str(uuid.uuid4()),
            source_block_id=source_block_id,
            source_port_id=source_port_id,
            target_block_id=target_block_id,
            target_port_id=target_port_id,
        )
        
        self._current_graph.connections.append(connection)
        self._current_graph.updated_at = datetime.utcnow()
        
        return connection
    
    def disconnect(self, connection_id: str) -> bool:
        """Remove a connection"""
        if not self._current_graph:
            return False
        
        original_count = len(self._current_graph.connections)
        self._current_graph.connections = [
            c for c in self._current_graph.connections if c.id != connection_id
        ]
        
        return len(self._current_graph.connections) < original_count
    
    def validate_graph(self) -> tuple[bool, List[str]]:
        """Validate the strategy graph"""
        if not self._current_graph:
            return False, ["No graph selected"]
        
        errors = []
        
        # Check for blocks
        if not self._current_graph.blocks:
            errors.append("Graph has no blocks")
        
        # Check for execution block
        has_execution = any(
            b.block_type == BlockType.TRADE_EXECUTION
            for b in self._current_graph.blocks
        )
        if not has_execution:
            errors.append("Graph has no execution block")
        
        # Check connections are valid
        for conn in self._current_graph.connections:
            source_block = self._get_block(conn.source_block_id)
            target_block = self._get_block(conn.target_block_id)
            
            if not source_block:
                errors.append(f"Connection references unknown source block: {conn.source_block_id}")
            if not target_block:
                errors.append(f"Connection references unknown target block: {conn.target_block_id}")
        
        # Check for cycles
        if self._has_cycle():
            errors.append("Graph contains circular dependencies")
        
        # Check required inputs are connected
        for block in self._current_graph.blocks:
            for inp in block.inputs:
                if inp.required and not self._is_port_connected(block.id, inp.id):
                    errors.append(f"Block '{block.name}' requires input '{inp.name}'")
        
        is_valid = len(errors) == 0
        self._current_graph.is_valid = is_valid
        self._current_graph.validation_errors = errors
        
        return is_valid, errors
    
    def _has_cycle(self) -> bool:
        """Check if the graph has cycles using DFS"""
        if not self._current_graph:
            return False
        
        visited = set()
        rec_stack = set()
        
        def dfs(block_id: str) -> bool:
            visited.add(block_id)
            rec_stack.add(block_id)
            
            # Find all blocks this block connects to
            for conn in self._current_graph.connections:
                if conn.source_block_id == block_id:
                    target = conn.target_block_id
                    if target not in visited:
                        if dfs(target):
                            return True
                    elif target in rec_stack:
                        return True
            
            rec_stack.remove(block_id)
            return False
        
        for block in self._current_graph.blocks:
            if block.id not in visited:
                if dfs(block.id):
                    return True
        
        return False
    
    def _get_block(self, block_id: str) -> Optional[StrategyBlock]:
        """Get a block by ID"""
        if not self._current_graph:
            return None
        return next((b for b in self._current_graph.blocks if b.id == block_id), None)
    
    def _get_port(
        self,
        block: StrategyBlock,
        port_id: str,
        is_output: bool
    ) -> Optional[Port]:
        """Get a port by ID"""
        ports = block.outputs if is_output else block.inputs
        return next((p for p in ports if p.id == port_id), None)
    
    def _is_port_connected(self, block_id: str, port_id: str) -> bool:
        """Check if a port is connected"""
        if not self._current_graph:
            return False
        
        for conn in self._current_graph.connections:
            if conn.target_block_id == block_id and conn.target_port_id == port_id:
                return True
        return False
    
    def get_execution_order(self) -> List[str]:
        """Get topological order for execution"""
        if not self._current_graph or not self._current_graph.is_valid:
            return []
        
        # Build adjacency list
        in_degree = {b.id: 0 for b in self._current_graph.blocks}
        adj_list: Dict[str, List[str]] = {b.id: [] for b in self._current_graph.blocks}
        
        for conn in self._current_graph.connections:
            adj_list[conn.source_block_id].append(conn.target_block_id)
            in_degree[conn.target_block_id] += 1
        
        # Topological sort
        queue = [b for b in self._current_graph.blocks if in_degree[b.id] == 0]
        order = []
        
        while queue:
            block = queue.pop(0)
            order.append(block.id)
            
            for target in adj_list[block.id]:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)
        
        return order
    
    def get_current_graph(self) -> Optional[StrategyGraph]:
        """Get the current graph"""
        return self._current_graph
    
    def export_graph(self) -> Optional[Dict[str, Any]]:
        """Export current graph to dict"""
        if self._current_graph:
            return self._current_graph.to_dict()
        return None
