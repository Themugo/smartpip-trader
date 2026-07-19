"""
Strategy Compiler - Convert Visual Workflows to Executable Code

Compiles strategy graphs into executable Python code.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from strategy_studio.builder import StrategyGraph, StrategyBlock, BlockType

logger = logging.getLogger(__name__)


class CompilationStatus(Enum):
    """Compilation status"""
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class CompiledStrategy:
    """Compiled strategy ready for execution"""
    name: str
    source_code: str
    
    # Compilation info
    status: CompilationStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Execution info
    estimated_cost: float = 0  # Estimated computational cost
    dependencies: List[str] = field(default_factory=list)
    
    # Graph reference
    original_graph: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "estimated_cost": self.estimated_cost,
            "dependencies": self.dependencies,
        }


class StrategyCompiler:
    """
    Compiler for strategy graphs.
    
    Features:
    - Graph validation
    - Cycle detection
    - Execution order optimization
    - Code generation
    - Static analysis
    - Cost estimation
    """
    
    # Code templates for each block type
    BLOCK_TEMPLATES = {
        BlockType.MARKET_DATA: '''
async def block_{id}(context):
    """Market Data Block"""
    data = await context.get_market_data()
    return {{
        "price": data.price,
        "bid": data.bid,
        "ask": data.ask,
        "volume": data.volume,
    }}
''',
        BlockType.INDICATOR: '''
async def block_{id}(context, price):
    """Indicator Block - {name}"""
    params = {params}
    return await context.calculate_indicator(
        "{block_type}", price, params
    )
''',
        BlockType.STATISTICAL_FEATURE: '''
async def block_{id}(context, data):
    """Statistical Feature - {name}"""
    params = {params}
    return await context.calculate_statistical_feature(
        "{feature_name}", data, params
    )
''',
        BlockType.CONFIDENCE_FILTER: '''
async def block_{id}(context, signal, confidence):
    """Confidence Filter"""
    threshold = {threshold}
    if confidence >= threshold:
        return signal
    return None
''',
        BlockType.CONDITION: '''
async def block_{id}(context, a, b):
    """Condition Check"""
    operator = "{operator}"
    if operator == ">":
        return a > b
    elif operator == "<":
        return a < b
    elif operator == ">=":
        return a >= b
    elif operator == "<=":
        return a <= b
    elif operator == "==":
        return a == b
    elif operator == "!=":
        return a != b
    return False
''',
        BlockType.LOGIC_GATE: '''
async def block_{id}(context, input1, input2):
    """Logic Gate - {gate_type}"""
    gate_type = "{gate_type}"
    if gate_type == "AND":
        return input1 and input2
    elif gate_type == "OR":
        return input1 or input2
    elif gate_type == "NOT":
        return not input1
    return False
''',
        BlockType.RISK_RULE: '''
async def block_{id}(context, signal):
    """Risk Rule"""
    approved, reason = await context.check_risk_rules(signal)
    return {{
        "approved": approved,
        "reason": reason,
        "signal": signal if approved else None,
    }}
''',
        BlockType.POSITION_SIZING: '''
async def block_{id}(context, signal, balance):
    """Position Sizing"""
    params = {params}
    size = await context.calculate_position_size(
        signal, balance, params
    )
    return {{
        "signal": signal,
        "size": size,
    }}
''',
        BlockType.TRADE_EXECUTION: '''
async def block_{id}(context, signal, size):
    """Trade Execution"""
    params = {params}
    if signal and size > 0:
        order = await context.execute_trade(signal, size, params)
        return order
    return None
''',
        BlockType.NOTIFICATION: '''
async def block_{id}(context, message):
    """Send Notification"""
    channel = "{channel}"
    await context.send_notification(message, channel)
    return True
''',
        BlockType.MEMORY_RETRIEVAL: '''
async def block_{id}(context, query):
    """Memory Retrieval"""
    memory_type = "{memory_type}"
    return await context.retrieve_memory(memory_type, query)
''',
        BlockType.REGIME_CLASSIFIER: '''
async def block_{id}(context, features):
    """Regime Classifier"""
    return await context.classify_regime(features)
''',
        BlockType.TIME_FILTER: '''
async def block_{id}(context, signal):
    """Time Filter"""
    params = {params}
    if await context.is_within_trading_hours(params):
        return signal
    return None
''',
    }
    
    def __init__(self):
        self._custom_templates: Dict[str, str] = {}
    
    def compile(self, graph: StrategyGraph) -> CompiledStrategy:
        """
        Compile a strategy graph to executable code.
        
        Args:
            graph: Strategy graph to compile
            
        Returns:
            CompiledStrategy with generated code
        """
        # Validate first
        if not graph.is_valid:
            return CompiledStrategy(
                name=graph.name,
                source_code="",
                status=CompilationStatus.FAILED,
                errors=["Graph validation failed"] + graph.validation_errors,
            )
        
        errors = []
        warnings = []
        
        try:
            # Generate code
            source_code = self._generate_code(graph)
            
            # Perform static analysis
            analysis_errors, analysis_warnings = self._static_analysis(source_code, graph)
            errors.extend(analysis_errors)
            warnings.extend(analysis_warnings)
            
            # Estimate cost
            estimated_cost = self._estimate_cost(graph)
            
            # Get dependencies
            dependencies = self._get_dependencies(graph)
            
            status = CompilationStatus.FAILED if errors else (
                CompilationStatus.WARNING if warnings else CompilationStatus.SUCCESS
            )
            
            compiled = CompiledStrategy(
                name=graph.name,
                source_code=source_code,
                status=status,
                errors=errors,
                warnings=warnings,
                estimated_cost=estimated_cost,
                dependencies=dependencies,
                original_graph=graph.to_dict(),
            )
            
            return compiled
            
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            return CompiledStrategy(
                name=graph.name,
                source_code="",
                status=CompilationStatus.FAILED,
                errors=[str(e)],
            )
    
    def _generate_code(self, graph: StrategyGraph) -> str:
        """Generate Python code from graph"""
        lines = [
            '"""',
            f'Auto-generated strategy: {graph.name}',
            f'Generated: {datetime.now(timezone.utc).isoformat()}',
            '"""',
            '',
            'import asyncio',
            'from typing import Any, Dict, Optional',
            '',
            '',
            'class StrategyContext:',
            '    """Execution context for strategy blocks"""',
            '',
            '    def __init__(self, config: Dict[str, Any]):',
            '        self.config = config',
            '        self._data = {}',
            '',
            '    async def get_market_data(self):',
            '        """Get current market data"""',
            '        # Implement market data retrieval',
            '        pass',
            '',
            '    async def calculate_indicator(self, indicator_type: str, data, params: Dict):',
            '        """Calculate technical indicator"""',
            '        # Implement indicator calculation',
            '        pass',
            '',
            '    async def check_risk_rules(self, signal):',
            '        """Check risk rules"""',
            '        return True, ""',
            '',
            '    async def execute_trade(self, signal, size, params):',
            '        """Execute a trade"""',
            '        # Implement trade execution',
            '        pass',
            '',
            '    async def send_notification(self, message, channel):',
            '        """Send notification"""',
            '        pass',
            '',
            '',
        ]
        
        # Generate block functions
        for block in graph.blocks:
            block_code = self._generate_block_code(block)
            lines.append(block_code)
            lines.append("")
        
        # Generate main execution function
        lines.extend(self._generate_main_function(graph))
        
        return "\n".join(lines)
    
    def _generate_block_code(self, block: StrategyBlock) -> str:
        """Generate code for a single block"""
        template = self._custom_templates.get(block.id)
        
        if not template and block.block_type in self.BLOCK_TEMPLATES:
            template = self.BLOCK_TEMPLATES[block.block_type]
        
        if not template:
            return f'''
async def block_{block.id}(context):
    """Custom Block: {block.name}"""
    # Add custom implementation
    pass
'''
        
        # Format template
        code = template.replace("{id}", block.id)
        code = code.replace("{name}", block.name)
        code = code.replace("{block_type}", block.block_type.value)
        code = code.replace("{feature_name}", block.name.lower().replace(" ", "_"))
        
        # Format parameters
        params = str(block.config.parameters)
        code = code.replace("{params}", params)
        
        # Format specific parameters
        threshold = block.config.parameters.get("threshold", 50)
        code = code.replace("{threshold}", str(threshold))
        
        operator = block.config.parameters.get("operator", ">")
        code = code.replace("{operator}", f'"{operator}"')
        
        gate_type = block.config.parameters.get("gate_type", "AND")
        code = code.replace("{gate_type}", f'"{gate_type}"')
        
        channel = block.config.parameters.get("channel", "all")
        code = code.replace("{channel}", f'"{channel}"')
        
        memory_type = block.config.parameters.get("memory_type", "pattern")
        code = code.replace("{memory_type}", f'"{memory_type}"')
        
        return code
    
    def _generate_main_function(self, graph: StrategyGraph) -> List[str]:
        """Generate main strategy execution function"""
        lines = [
            "async def execute_strategy(context: StrategyContext) -> Dict[str, Any]:",
            '    """Execute the strategy"""',
            "",
            "    results = {}",
            "",
        ]
        
        # Get execution order
        execution_order = self._get_execution_order(graph)
        
        for block_id in execution_order:
            block = next((b for b in graph.blocks if b.id == block_id), None)
            if not block:
                continue
            
            # Build function call
            inputs = [f'        results["{block.id}"]']
            
            # Add input references
            input_refs = []
            for conn in graph.connections:
                if conn.target_block_id == block_id:
                    source_block = next((b for b in graph.blocks if b.id == conn.source_block_id), None)
                    if source_block:
                        input_refs.append(f'results["{conn.source_block_id}"]["{conn.source_port_id}"]')
            
            if input_refs:
                inputs.append(f'    # Input: {", ".join([r.split("[")[1].split("]")[0] for r in input_refs])}')
                for ref in input_refs:
                    inputs.append(f'    {ref.split("[")[1].split("]")[0]}_data = {ref}')
            
            # Simple function call (would be more complex in real implementation)
            lines.append(f'    # Execute {block.name}')
            lines.append(f'    results["{block.id}"] = await block_{block.id}(context)')
            lines.append("")
        
        lines.append("    return results")
        
        return lines
    
    def _get_execution_order(self, graph: StrategyGraph) -> List[str]:
        """Get topological order for execution"""
        in_degree = {b.id: 0 for b in graph.blocks}
        adj_list: Dict[str, List[str]] = {b.id: [] for b in graph.blocks}
        
        for conn in graph.connections:
            adj_list[conn.source_block_id].append(conn.target_block_id)
            in_degree[conn.target_block_id] += 1
        
        queue = [b.id for b in graph.blocks if in_degree[b.id] == 0]
        order = []
        
        while queue:
            block_id = queue.pop(0)
            order.append(block_id)
            
            for target in adj_list[block_id]:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)
        
        return order
    
    def _static_analysis(self, code: str, graph: StrategyGraph) -> tuple[List[str], List[str]]:
        """Perform static analysis on generated code"""
        errors = []
        warnings = []
        
        # Check for undefined variables (simplified)
        # In a real implementation, use AST analysis
        
        # Check for empty blocks
        for block in graph.blocks:
            if not block.config.parameters and block.block_type in [
                BlockType.INDICATOR,
                BlockType.STATISTICAL_FEATURE,
            ]:
                warnings.append(f"Block '{block.name}' has no parameters configured")
        
        # Check for missing risk rules
        has_risk = any(b.block_type == BlockType.RISK_RULE for b in graph.blocks)
        if not has_risk:
            warnings.append("Strategy has no risk management rules")
        
        # Check for notifications
        has_notification = any(b.block_type == BlockType.NOTIFICATION for b in graph.blocks)
        if not has_notification:
            warnings.append("Strategy has no notification blocks")
        
        return errors, warnings
    
    def _estimate_cost(self, graph: StrategyGraph) -> float:
        """Estimate computational cost"""
        cost = 0
        
        # Cost per block type
        block_costs = {
            BlockType.MARKET_DATA: 1,
            BlockType.INDICATOR: 2,
            BlockType.STATISTICAL_FEATURE: 3,
            BlockType.ML_MODEL: 10,
            BlockType.PATTERN_RECOGNITION: 5,
            BlockType.RISK_RULE: 2,
            BlockType.TRADE_EXECUTION: 1,
        }
        
        for block in graph.blocks:
            cost += block_costs.get(block.block_type, 1)
        
        # Add connection overhead
        cost += len(graph.connections) * 0.1
        
        return cost
    
    def _get_dependencies(self, graph: StrategyGraph) -> List[str]:
        """Get required dependencies"""
        deps = set()
        
        for block in graph.blocks:
            if block.block_type == BlockType.INDICATOR:
                deps.add("numpy")
                deps.add("pandas")
            elif block.block_type == BlockType.STATISTICAL_FEATURE:
                deps.add("scipy")
            elif block.block_type == BlockType.ML_MODEL:
                deps.add("sklearn")
            elif block.block_type == BlockType.PATTERN_RECOGNITION:
                deps.add("numpy")
        
        return sorted(list(deps))
    
    def register_template(self, block_id: str, template: str) -> None:
        """Register a custom code template"""
        self._custom_templates[block_id] = template
