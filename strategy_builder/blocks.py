"""
Strategy Blocks
=============

Block definitions for visual strategy authoring.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4


class BlockCategory(Enum):
    """Categories of blocks"""
    INPUT = "input"  # Market Input
    FEATURE = "feature"  # Feature Engineering
    INDICATOR = "indicator"  # Indicators
    STATISTICAL = "statistical"  # Statistical Tests
    ML = "ml"  # Machine Learning
    PATTERN = "pattern"  # Pattern Recognition
    RISK = "risk"  # Risk Rules
    LOGIC = "logic"  # Decision Logic
    EXECUTION = "execution"  # Trade Execution
    NOTIFICATION = "notification"  # Notifications
    PORTFOLIO = "portfolio"  # Portfolio Rules
    MEMORY = "memory"  # Memory Lookup
    EXPLAINABILITY = "explainability"  # Explainability
    VALIDATION = "validation"  # Validation


class BlockType(Enum):
    """Types of blocks"""
    # Input
    MARKET_DATA = "market_data"
    TICK_DATA = "tick_data"
    OHLCV_DATA = "ohlcv_data"
    ORDERBOOK = "orderbook"
    NEWS_FEED = "news_feed"
    
    # Feature Engineering
    NORMALIZE = "normalize"
    STANDARDIZE = "standardize"
    LAG = "lag"
    DIFF = "diff"
    ROLLING_STATS = "rolling_stats"
    CROSS_SECTION = "cross_section"
    
    # Indicators
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    ATR = "atr"
    STOCHASTIC = "stochastic"
    ICHIMOKU = "ichimoku"
    FIBONACCI = "fibonacci"
    
    # Statistical Tests
    ZSCORE = "zscore"
    CORRELATION = "correlation"
    COINTEGRATION = "cointegration"
    STATIONARITY = "stationarity"
    ARCH_EFFECT = "arch_effect"
    
    # Machine Learning
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    LOGISTIC_REGRESSION = "logistic_regression"
    CLUSTERING = "clustering"
    
    # Pattern Recognition
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    TRENDLINE = "trendline"
    SUPPORT_RESISTANCE = "support_resistance"
    
    # Risk Rules
    POSITION_SIZE = "position_size"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_DRAWDOWN = "max_drawdown"
    VAR_LIMIT = "var_limit"
    CORRELATION_LIMIT = "correlation_limit"
    
    # Decision Logic
    THRESHOLD = "threshold"
    COMPARISON = "comparison"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    LOGICAL_NOT = "logical_not"
    IF_THEN = "if_then"
    SWITCH = "switch"
    
    # Execution
    MARKET_ORDER = "market_order"
    LIMIT_ORDER = "limit_order"
    STOP_ORDER = "stop_order"
    ORDER_BATCH = "order_batch"
    
    # Notifications
    SLACK_NOTIFY = "slack_notify"
    EMAIL_NOTIFY = "email_notify"
    WEBHOOK = "webhook"
    LOG_MESSAGE = "log_message"
    
    # Portfolio
    ALLOCATION = "allocation"
    REBALANCE = "rebalance"
    HEDGE = "hedge"
    
    # Memory
    LOOKUP = "lookup"
    STORE = "store"
    LEARN = "learn"
    
    # Explainability
    FEATURE_IMPORTANCE = "feature_importance"
    SHAP_VALUES = "shap_values"
    DECISION_PATH = "decision_path"
    
    # Validation
    ASSERT = "assert"
    BENCHMARK = "benchmark"
    STATS_CHECK = "stats_check"


class PortType(Enum):
    """Types of ports"""
    NUMBER = "number"
    BOOLEAN = "boolean"
    STRING = "string"
    SERIES = "series"  # Time series
    DATAFRAME = "dataframe"
    MODEL = "model"
    SIGNAL = "signal"
    ORDER = "order"


@dataclass
class BlockPort:
    """Input or output port for a block"""
    port_id: str
    name: str
    port_type: PortType
    required: bool = True
    default_value: Any = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "port_id": self.port_id,
            "name": self.name,
            "type": self.port_type.value,
            "required": self.required,
            "default_value": self.default_value,
            "description": self.description
        }


@dataclass
class BlockParameter:
    """A configurable parameter for a block"""
    param_id: str
    name: str
    value: Any
    param_type: str  # "number", "string", "boolean", "select", "range"
    options: List[Any] = field(default_factory=list)  # For select type
    min_value: float = None  # For range type
    max_value: float = None  # For range type
    step: float = None  # For range type
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "value": self.value,
            "type": self.param_type,
            "options": self.options,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "description": self.description
        }


@dataclass
class Block:
    """
    A single block in the strategy graph.
    """
    block_id: str
    block_type: BlockType
    name: str
    category: BlockCategory
    
    # Configuration
    parameters: List[BlockParameter] = field(default_factory=list)
    inputs: List[BlockPort] = field(default_factory=list)
    outputs: List[BlockPort] = field(default_factory=list)
    
    # Position (for UI)
    position: Tuple[int, int] = (0, 0)
    
    # Metadata
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    
    # State
    enabled: bool = True
    collapsed: bool = False
    
    # Computed
    estimated_cost: float = 0.0  # Estimated computational cost
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.block_id:
            self.block_id = str(uuid4())
    
    def get_parameter(self, name: str) -> Optional[Any]:
        """Get parameter value by name"""
        for param in self.parameters:
            if param.name == name:
                return param.value
        return None
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """Set parameter value by name"""
        for param in self.parameters:
            if param.name == name:
                param.value = value
                return True
        return False
    
    def compute_cost(self) -> float:
        """Estimate computational cost"""
        # Base cost by category
        category_costs = {
            BlockCategory.INPUT: 1.0,
            BlockCategory.FEATURE: 0.5,
            BlockCategory.INDICATOR: 2.0,
            BlockCategory.STATISTICAL: 5.0,
            BlockCategory.ML: 20.0,
            BlockCategory.PATTERN: 3.0,
            BlockCategory.RISK: 1.0,
            BlockCategory.LOGIC: 0.1,
            BlockCategory.EXECUTION: 1.0,
            BlockCategory.NOTIFICATION: 0.5,
            BlockCategory.PORTFOLIO: 2.0,
            BlockCategory.MEMORY: 1.5,
            BlockCategory.EXPLAINABILITY: 10.0,
            BlockCategory.VALIDATION: 2.0,
        }
        
        base_cost = category_costs.get(self.category, 1.0)
        
        # Multipliers based on parameters
        window_size = self.get_parameter("window") or self.get_parameter("period") or 0
        if window_size:
            base_cost *= (1 + window_size / 1000)
        
        self.estimated_cost = base_cost
        return base_cost
    
    def get_hash(self) -> str:
        """Get deterministic hash for this block"""
        hash_data = {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "name": self.name,
            "parameters": [p.to_dict() for p in self.parameters]
        }
        return hashlib.sha256(
            json.dumps(hash_data, sort_keys=True).encode()
        ).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "name": self.name,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "position": {"x": self.position[0], "y": self.position[1]},
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "enabled": self.enabled,
            "collapsed": self.collapsed,
            "estimated_cost": self.estimated_cost,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
            "hash": self.get_hash()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        return cls(
            block_id=data["block_id"],
            block_type=BlockType(data["block_type"]),
            name=data["name"],
            category=BlockCategory(data["category"]),
            parameters=[BlockParameter(**p) for p in data.get("parameters", [])],
            inputs=[BlockPort(**i) for i in data.get("inputs", [])],
            outputs=[BlockPort(**o) for o in data.get("outputs", [])],
            position=(data["position"]["x"], data["position"]["y"]) if "position" in data else (0, 0),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
            collapsed=data.get("collapsed", False)
        )


class BlockDefinition:
    """
    Registry of all available block definitions.
    """
    
    _definitions: Dict[BlockType, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, block_type: BlockType, definition: Dict[str, Any]) -> None:
        """Register a block definition"""
        cls._definitions[block_type] = definition
    
    @classmethod
    def get_definition(cls, block_type: BlockType) -> Optional[Dict[str, Any]]:
        """Get a block definition"""
        return cls._definitions.get(block_type)
    
    @classmethod
    def get_all_definitions(cls) -> Dict[BlockType, Dict[str, Any]]:
        """Get all block definitions"""
        return cls._definitions.copy()
    
    @classmethod
    def create_block(cls, block_type: BlockType, name: str = None) -> Block:
        """Create a block from its definition"""
        definition = cls._definitions.get(block_type)
        if not definition:
            raise ValueError(f"Unknown block type: {block_type}")
        
        inputs = [
            BlockPort(
                port_id=f"in_{i['name']}",
                name=i["name"],
                port_type=PortType(i["type"]),
                required=i.get("required", True),
                default_value=i.get("default"),
                description=i.get("description", "")
            )
            for i in definition.get("inputs", [])
        ]
        
        outputs = [
            BlockPort(
                port_id=f"out_{o['name']}",
                name=o["name"],
                port_type=PortType(o["type"]),
                required=False,
                description=o.get("description", "")
            )
            for o in definition.get("outputs", [])
        ]
        
        parameters = [
            BlockParameter(
                param_id=f"param_{p['name']}",
                name=p["name"],
                value=p.get("default"),
                param_type=p.get("type", "string"),
                options=p.get("options", []),
                min_value=p.get("min"),
                max_value=p.get("max"),
                step=p.get("step"),
                description=p.get("description", "")
            )
            for p in definition.get("parameters", [])
        ]
        
        return Block(
            block_id=str(uuid4()),
            block_type=block_type,
            name=name or definition.get("name", block_type.value),
            category=BlockCategory(definition.get("category", "logic")),
            parameters=parameters,
            inputs=inputs,
            outputs=outputs,
            description=definition.get("description", ""),
            version=definition.get("version", "1.0.0"),
            author=definition.get("author", ""),
            tags=definition.get("tags", [])
        )


# Register all block definitions
def _register_blocks():
    """Register all built-in block definitions"""
    
    # Market Input
    BlockDefinition.register(BlockType.MARKET_DATA, {
        "name": "Market Data",
        "category": "input",
        "description": "Get market data for a symbol",
        "inputs": [],
        "outputs": [
            {"name": "data", "type": "dataframe", "description": "Market data"}
        ],
        "parameters": [
            {"name": "symbol", "type": "string", "default": "EUR/USD"},
            {"name": "timeframe", "type": "select", "options": ["1m", "5m", "15m", "1h", "4h", "1d"], "default": "1h"}
        ]
    })
    
    # Indicators
    BlockDefinition.register(BlockType.SMA, {
        "name": "SMA",
        "category": "indicator",
        "description": "Simple Moving Average",
        "inputs": [
            {"name": "series", "type": "series"}
        ],
        "outputs": [
            {"name": "result", "type": "series"}
        ],
        "parameters": [
            {"name": "period", "type": "range", "default": 20, "min": 2, "max": 500, "step": 1}
        ]
    })
    
    BlockDefinition.register(BlockType.EMA, {
        "name": "EMA",
        "category": "indicator",
        "description": "Exponential Moving Average",
        "inputs": [
            {"name": "series", "type": "series"}
        ],
        "outputs": [
            {"name": "result", "type": "series"}
        ],
        "parameters": [
            {"name": "period", "type": "range", "default": 20, "min": 2, "max": 500, "step": 1}
        ]
    })
    
    BlockDefinition.register(BlockType.RSI, {
        "name": "RSI",
        "category": "indicator",
        "description": "Relative Strength Index",
        "inputs": [
            {"name": "series", "type": "series"}
        ],
        "outputs": [
            {"name": "rsi", "type": "series"}
        ],
        "parameters": [
            {"name": "period", "type": "range", "default": 14, "min": 2, "max": 100, "step": 1}
        ]
    })
    
    BlockDefinition.register(BlockType.MACD, {
        "name": "MACD",
        "category": "indicator",
        "description": "MACD Indicator",
        "inputs": [
            {"name": "series", "type": "series"}
        ],
        "outputs": [
            {"name": "macd", "type": "series"},
            {"name": "signal", "type": "series"},
            {"name": "histogram", "type": "series"}
        ],
        "parameters": [
            {"name": "fast", "type": "range", "default": 12, "min": 2, "max": 100},
            {"name": "slow", "type": "range", "default": 26, "min": 2, "max": 200},
            {"name": "signal", "type": "range", "default": 9, "min": 2, "max": 50}
        ]
    })
    
    # Decision Logic
    BlockDefinition.register(BlockType.THRESHOLD, {
        "name": "Threshold",
        "category": "logic",
        "description": "Compare value against threshold",
        "inputs": [
            {"name": "value", "type": "number", "required": True}
        ],
        "outputs": [
            {"name": "signal", "type": "signal"}
        ],
        "parameters": [
            {"name": "threshold", "type": "number", "default": 0.5},
            {"name": "direction", "type": "select", "options": ["above", "below", "cross_above", "cross_below"], "default": "above"}
        ]
    })
    
    BlockDefinition.register(BlockType.COMPARISON, {
        "name": "Compare",
        "category": "logic",
        "description": "Compare two values",
        "inputs": [
            {"name": "a", "type": "number", "required": True},
            {"name": "b", "type": "number", "required": True}
        ],
        "outputs": [
            {"name": "result", "type": "boolean"}
        ],
        "parameters": [
            {"name": "operator", "type": "select", "options": ["==", "!=", ">", "<", ">=", "<="], "default": ">"}
        ]
    })
    
    BlockDefinition.register(BlockType.LOGICAL_AND, {
        "name": "AND",
        "category": "logic",
        "description": "Logical AND of multiple inputs",
        "inputs": [
            {"name": "a", "type": "boolean", "required": True},
            {"name": "b", "type": "boolean", "required": True}
        ],
        "outputs": [
            {"name": "result", "type": "boolean"}
        ],
        "parameters": []
    })
    
    BlockDefinition.register(BlockType.LOGICAL_OR, {
        "name": "OR",
        "category": "logic",
        "description": "Logical OR of multiple inputs",
        "inputs": [
            {"name": "a", "type": "boolean", "required": True},
            {"name": "b", "type": "boolean", "required": True}
        ],
        "outputs": [
            {"name": "result", "type": "boolean"}
        ],
        "parameters": []
    })
    
    BlockDefinition.register(BlockType.IF_THEN, {
        "name": "If-Then",
        "category": "logic",
        "description": "Conditional logic",
        "inputs": [
            {"name": "condition", "type": "boolean", "required": True},
            {"name": "then_value", "type": "number"},
            {"name": "else_value", "type": "number"}
        ],
        "outputs": [
            {"name": "result", "type": "number"}
        ],
        "parameters": []
    })
    
    # Risk Rules
    BlockDefinition.register(BlockType.POSITION_SIZE, {
        "name": "Position Size",
        "category": "risk",
        "description": "Calculate position size based on risk",
        "inputs": [
            {"name": "signal", "type": "signal"},
            {"name": "price", "type": "number"}
        ],
        "outputs": [
            {"name": "size", "type": "number"}
        ],
        "parameters": [
            {"name": "risk_pct", "type": "range", "default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}
        ]
    })
    
    BlockDefinition.register(BlockType.STOP_LOSS, {
        "name": "Stop Loss",
        "category": "risk",
        "description": "Stop loss rule",
        "inputs": [
            {"name": "entry_price", "type": "number"},
            {"name": "direction", "type": "number"}
        ],
        "outputs": [
            {"name": "stop_price", "type": "number"}
        ],
        "parameters": [
            {"name": "distance_pct", "type": "range", "default": 2.0, "min": 0.1, "max": 20.0}
        ]
    })
    
    # Execution
    BlockDefinition.register(BlockType.MARKET_ORDER, {
        "name": "Market Order",
        "category": "execution",
        "description": "Place market order",
        "inputs": [
            {"name": "signal", "type": "signal"},
            {"name": "size", "type": "number"}
        ],
        "outputs": [
            {"name": "order", "type": "order"}
        ],
        "parameters": [
            {"name": "symbol", "type": "string", "default": "EUR/USD"}
        ]
    })
    
    # Notifications
    BlockDefinition.register(BlockType.LOG_MESSAGE, {
        "name": "Log Message",
        "category": "notification",
        "description": "Log a message",
        "inputs": [
            {"name": "data", "type": "series"}
        ],
        "outputs": [],
        "parameters": [
            {"name": "level", "type": "select", "options": ["debug", "info", "warning", "error"], "default": "info"},
            {"name": "message", "type": "string", "default": "Signal triggered"}
        ]
    })
    
    # Statistical Tests
    BlockDefinition.register(BlockType.ZSCORE, {
        "name": "Z-Score",
        "category": "statistical",
        "description": "Calculate z-score",
        "inputs": [
            {"name": "series", "type": "series"}
        ],
        "outputs": [
            {"name": "zscore", "type": "series"}
        ],
        "parameters": [
            {"name": "window", "type": "range", "default": 20, "min": 2, "max": 500}
        ]
    })
    
    # Machine Learning
    BlockDefinition.register(BlockType.RANDOM_FOREST, {
        "name": "Random Forest",
        "category": "ml",
        "description": "Random Forest classifier/regressor",
        "inputs": [
            {"name": "features", "type": "dataframe"},
            {"name": "target", "type": "series"}
        ],
        "outputs": [
            {"name": "predictions", "type": "series"},
            {"name": "model", "type": "model"}
        ],
        "parameters": [
            {"name": "n_estimators", "type": "range", "default": 100, "min": 10, "max": 1000},
            {"name": "max_depth", "type": "range", "default": 10, "min": 1, "max": 50}
        ]
    })
    
    # Memory
    BlockDefinition.register(BlockType.LOOKUP, {
        "name": "Lookup",
        "category": "memory",
        "description": "Look up value from memory",
        "inputs": [],
        "outputs": [
            {"name": "value", "type": "number"}
        ],
        "parameters": [
            {"name": "key", "type": "string", "default": "last_signal"}
        ]
    })
    
    BlockDefinition.register(BlockType.STORE, {
        "name": "Store",
        "category": "memory",
        "description": "Store value in memory",
        "inputs": [
            {"name": "value", "type": "number"}
        ],
        "outputs": [],
        "parameters": [
            {"name": "key", "type": "string", "default": "last_signal"}
        ]
    })


# Initialize block definitions
_register_blocks()
