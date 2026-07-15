"""
Code Generators
==============

Generate code, documentation, and tests from strategy graphs.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .blocks import Block, BlockType, BlockCategory
from .graph import StrategyGraph

logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    Generates executable Python code from strategy graphs.
    """
    
    def __init__(self):
        self.imports: List[str] = [
            "import pandas as pd",
            "import numpy as np",
            "from typing import Dict, List, Optional",
            "from datetime import datetime"
        ]
        self._generated_vars: Dict[str, str] = {}
    
    def generate(self, graph: StrategyGraph) -> str:
        """Generate Python code from strategy graph"""
        self.imports = [
            "import pandas as pd",
            "import numpy as np",
            "from typing import Dict, List, Optional",
            "from datetime import datetime"
        ]
        self._generated_vars = {}
        
        lines = [
            '"""',
            f"Auto-generated Strategy: {graph.name}",
            f"Generated: {datetime.now().isoformat()}",
            '"""',
            "",
            "# Imports",
            *self.imports,
            "",
            "class Strategy:",
            '    """Generated strategy class."""',
            "",
            "    def __init__(self):",
            "        self.data = {}",
            "        self.signals = []",
            "        self.positions = []",
            "",
        ]
        
        # Generate block code in topological order
        execution_order = graph.get_execution_order()
        
        for depth, node in execution_order:
            block = node.block
            var_name = f"block_{block.block_id[:8]}"
            self._generated_vars[block.block_id] = var_name
            
            block_code = self._generate_block_code(block, graph)
            if block_code:
                lines.append(f"    # {block.name}")
                lines.append(f"    {block_code}")
                lines.append("")
        
        # Generate main method
        lines.extend([
            "    def on_tick(self, tick: Dict) -> Optional[Dict]:",
            '        """Process incoming tick data."""',
            "        pass",
            "",
            "    def on_bar(self, bar: pd.DataFrame) -> List[Dict]:",
            '        """Process incoming bar data."""',
            "        signals = []",
            ""
        ])
        
        # Add signal generation logic
        for block_id, var_name in self._generated_vars.items():
            block = graph.get_block(block_id)
            if block and block.category == BlockCategory.LOGIC:
                lines.append(f"        # {block.name}")
                lines.append(f"        signal = {var_name}.evaluate()")
                lines.append("        if signal:")
                lines.append("            signals.append(signal)")
                lines.append("")
        
        lines.extend([
            "        return signals",
            "",
            "    def get_parameters(self) -> Dict:",
            '        """Get strategy parameters."""',
            "        return {}",
            "",
        ])
        
        return "\n".join(lines)
    
    def _generate_block_code(self, block: Block, graph: StrategyGraph) -> str:
        """Generate code for a single block"""
        if block.block_type == BlockType.MARKET_DATA:
            symbol = block.get_parameter("symbol") or "EUR/USD"
            timeframe = block.get_parameter("timeframe") or "1h"
            return f"self.{self._generated_vars[block.block_id]} = MarketData('{symbol}', '{timeframe}')"
        
        elif block.block_type == BlockType.SMA:
            period = block.get_parameter("period") or 20
            return f"self.{self._generated_vars[block.block_id]} = SMA(period={period})"
        
        elif block.block_type == BlockType.EMA:
            period = block.get_parameter("period") or 20
            return f"self.{self._generated_vars[block.block_id]} = EMA(period={period})"
        
        elif block.block_type == BlockType.RSI:
            period = block.get_parameter("period") or 14
            return f"self.{self._generated_vars[block.block_id]} = RSI(period={period})"
        
        elif block.block_type == BlockType.MACD:
            fast = block.get_parameter("fast") or 12
            slow = block.get_parameter("slow") or 26
            signal = block.get_parameter("signal") or 9
            return f"self.{self._generated_vars[block.block_id]} = MACD(fast={fast}, slow={slow}, signal={signal})"
        
        elif block.block_type == BlockType.THRESHOLD:
            threshold = block.get_parameter("threshold") or 0.5
            direction = block.get_parameter("direction") or "above"
            return f"self.{self._generated_vars[block.block_id]} = Threshold(threshold={threshold}, direction='{direction}')"
        
        elif block.block_type == BlockType.COMPARISON:
            operator = block.get_parameter("operator") or ">"
            return f"self.{self._generated_vars[block.block_id]} = Compare(operator='{operator}')"
        
        elif block.block_type == BlockType.LOGICAL_AND:
            return f"self.{self._generated_vars[block.block_id]} = LogicalAnd()"
        
        elif block.block_type == BlockType.LOGICAL_OR:
            return f"self.{self._generated_vars[block.block_id]} = LogicalOr()"
        
        elif block.block_type == BlockType.STOP_LOSS:
            distance = block.get_parameter("distance_pct") or 2.0
            return f"self.{self._generated_vars[block.block_id]} = StopLoss(distance_pct={distance})"
        
        elif block.block_type == BlockType.POSITION_SIZE:
            risk_pct = block.get_parameter("risk_pct") or 1.0
            return f"self.{self._generated_vars[block.block_id]} = PositionSize(risk_pct={risk_pct})"
        
        elif block.block_type == BlockType.MARKET_ORDER:
            symbol = block.get_parameter("symbol") or "EUR/USD"
            return f"self.{self._generated_vars[block.block_id]} = MarketOrder(symbol='{symbol}')"
        
        elif block.block_type == BlockType.ZSCORE:
            window = block.get_parameter("window") or 20
            return f"self.{self._generated_vars[block.block_id]} = ZScore(window={window})"
        
        else:
            return f"# {block.name} ({block.block_type.value}) - manual implementation required"


class DocumentationGenerator:
    """
    Generates documentation from strategy graphs.
    """
    
    def generate(self, graph: StrategyGraph) -> str:
        """Generate markdown documentation"""
        stats = graph.get_statistics()
        
        lines = [
            f"# Strategy Documentation: {graph.name}",
            "",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Version:** {graph.version}",
            "",
            f"## Overview",
            "",
            graph.description or "Auto-generated strategy documentation.",
            "",
            f"## Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Blocks | {stats['total_nodes']} |",
            f"| Total Connections | {stats['total_edges']} |",
            f"| Execution Depth | {stats['execution_depth']} |",
            f"| Estimated Cost | {stats['total_cost']:.1f} |",
            "",
            "## Block Categories",
            "",
        ]
        
        # Add category breakdown
        for cat, count in stats.get("category_counts", {}).items():
            lines.append(f"- **{cat.title()}**: {count} blocks")
        
        lines.extend([
            "",
            "## Strategy Graph",
            "",
            "### Entry Points (Data Sources)",
            ""
        ])
        
        # List source nodes
        sources = graph.get_source_nodes()
        if sources:
            for node in sources:
                lines.append(f"- {node.block.name}")
        else:
            lines.append("*No data sources defined*")
        
        lines.extend([
            "",
            "### Execution Flow",
            ""
        ])
        
        # List execution order
        for depth, node in graph.get_execution_order():
            indent = "  " * depth
            lines.append(f"{indent}- {node.block.name}")
        
        lines.extend([
            "",
            "## Block Details",
            ""
        ])
        
        # Detailed block information
        for node in graph.nodes.values():
            block = node.block
            
            lines.extend([
                f"### {block.name}",
                "",
                f"**Type:** `{block.block_type.value}`",
                f"**Category:** {block.category.value}",
                ""
            ])
            
            if block.description:
                lines.append(f"{block.description}")
                lines.append("")
            
            if block.parameters:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Parameter | Value |")
                lines.append("|-----------|-------|")
                
                for param in block.parameters:
                    lines.append(f"| {param.name} | `{param.value}` |")
                
                lines.append("")
            
            if block.inputs:
                lines.append("**Inputs:**")
                for inp in block.inputs:
                    req = "(required)" if inp.required else "(optional)"
                    lines.append(f"- {inp.name} `{inp.port_type.value}` {req}")
                lines.append("")
            
            if block.outputs:
                lines.append("**Outputs:**")
                for out in block.outputs:
                    lines.append(f"- {out.name} `{out.port_type.value}`")
                lines.append("")
        
        lines.extend([
            "## Notes",
            "",
            "- This documentation was auto-generated",
            "- Strategy may require additional configuration before use",
            "- Backtesting recommended before live trading"
        ])
        
        return "\n".join(lines)


class TestGenerator:
    """
    Generates unit tests from strategy graphs.
    """
    
    def generate(self, graph: StrategyGraph) -> str:
        """Generate pytest unit tests"""
        
        lines = [
            '"""',
            f"Auto-generated Tests for: {graph.name}",
            f"Generated: {datetime.now().isoformat()}",
            '"""',
            "",
            "import pytest",
            "import pandas as pd",
            "import numpy as np",
            "from datetime import datetime, timedelta",
            "",
            "",
            "class TestStrategy:",
            '    """Test cases for generated strategy."""',
            "",
            "    @pytest.fixture",
            "    def sample_data(self):",
            '        """Generate sample market data for testing."""',
            "        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')",
            "        data = pd.DataFrame({",
            "            'open': np.random.randn(100).cumsum() + 100,",
            "            'high': np.random.randn(100).cumsum() + 102,",
            "            'low': np.random.randn(100).cumsum() + 98,",
            "            'close': np.random.randn(100).cumsum() + 100,",
            "            'volume': np.random.randint(1000, 10000, 100)",
            "        }, index=dates)",
            "        return data",
            "",
            "    @pytest.fixture",
            "    def strategy(self):",
            '        """Initialize strategy."""',
            "        from strategy import Strategy",
            "        return Strategy()",
            "",
        ]
        
        # Add test for each block type present
        block_types = set(n.block.block_type for n in graph.nodes.values())
        
        for block_type in block_types:
            test_name = f"test_{block_type.value}"
            lines.extend([
                f"    def {test_name}(self, sample_data):",
                f'        """Test {block_type.value} block."""',
                "        # TODO: Implement specific test",
                "        pass",
                "",
            ])
        
        # Add general tests
        lines.extend([
            "    def test_strategy_initialization(self, strategy):",
            '        """Test strategy initializes correctly."""',
            "        assert strategy is not None",
            "        assert hasattr(strategy, 'on_bar')",
            "",
            "    def test_strategy_on_bar(self, strategy, sample_data):",
            '        """Test strategy processes bars."""',
            "        signals = strategy.on_bar(sample_data)",
            "        assert isinstance(signals, list)",
            "",
            "    def test_strategy_parameters(self, strategy):",
            '        """Test strategy parameters."""',
            "        params = strategy.get_parameters()",
            "        assert isinstance(params, dict)",
            "",
        ])
        
        # Add data validation tests
        lines.extend([
            "    def test_empty_data(self, strategy):",
            '        """Test strategy with empty data."""',
            "        empty_data = pd.DataFrame()",
            "        signals = strategy.on_bar(empty_data)",
            "        assert signals == []",
            "",
            "    def test_missing_columns(self, strategy):",
            '        """Test strategy with missing columns."""',
            "        incomplete_data = pd.DataFrame({",
            "            'close': [100, 101, 102]",
            "        })",
            "        # Should handle gracefully",
            "        signals = strategy.on_bar(incomplete_data)",
            "        assert isinstance(signals, list)",
            "",
            "    def test_nan_values(self, strategy, sample_data):",
            '        """Test strategy with NaN values."""',
            "        data = sample_data.copy()",
            "        data.iloc[0:10] = np.nan",
            "        signals = strategy.on_bar(data)",
            "        assert isinstance(signals, list)",
            "",
        ])
        
        # Add edge case tests
        lines.extend([
            "    def test_single_bar(self, strategy):",
            '        """Test strategy with single bar."""',
            "        single_bar = pd.DataFrame({",
            "            'open': [100],",
            "            'high': [101],",
            "            'low': [99],",
            "            'close': [100],",
            "            'volume': [1000]",
            "        }, index=[datetime.now()])",
            "        signals = strategy.on_bar(single_bar)",
            "        assert isinstance(signals, list)",
            "",
            "    def test_negative_prices(self, strategy):",
            '        """Test strategy handles edge case data."""',
            "        edge_data = pd.DataFrame({",
            "            'open': [100, -50, 101],",
            "            'high': [102, 102, 103],",
            "            'low': [98, -50, 99],",
            "            'close': [100, -50, 101],",
            "            'volume': [1000, 1000, 1000]",
            "        })",
            "        signals = strategy.on_bar(edge_data)",
            "        assert isinstance(signals, list)",
            "",
        ])
        
        lines.extend([
            "",
            "if __name__ == '__main__':",
            "    pytest.main([__file__, '-v'])",
        ])
        
        return "\n".join(lines)
