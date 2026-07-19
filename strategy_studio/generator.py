"""
AI Strategy Generator - Plain English to Strategy

Generate strategies from natural language descriptions.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from strategy_studio.builder import StrategyGraph, StrategyBlock, BlockType, BlockCategory, VisualBuilder, Port


class AIStrategyGenerator:
    """
    AI Strategy Generator for creating strategies from natural language.
    
    Parses plain English descriptions and generates draft strategies.
    """
    
    # Keyword mappings
    CONDITION_PATTERNS = {
        "confidence": {
            "keywords": ["confidence", "certain", "sure", "high conviction"],
            "threshold_default": 70,
        },
        "volatility": {
            "keywords": ["volatile", "high volatility", "turbulent", "unstable"],
        },
        "agreement": {
            "keywords": ["agree", "consensus", "multiple", "all"],
        },
        "trend": {
            "keywords": ["trend", "direction", "moving", "direction"],
        },
    }
    
    def __init__(self):
        self._builder = VisualBuilder()
    
    def generate_from_description(self, description: str) -> StrategyGraph:
        """
        Generate a strategy graph from a plain English description.
        
        Args:
            description: Natural language strategy description
            
        Returns:
            StrategyGraph with generated blocks and connections
        """
        # Parse description
        components = self._parse_description(description)
        
        # Create graph
        graph = self._builder.create_graph(
            name=self._extract_name(description) or "Generated Strategy",
            description=description,
        )
        
        # Generate blocks based on components
        self._add_market_data_block(graph)
        
        if components.get("indicators"):
            indicator_blocks = self._add_indicator_blocks(graph, components["indicators"])
        else:
            indicator_blocks = []
        
        if components.get("confidence_filter"):
            self._add_confidence_block(graph, components["confidence_filter"])
        
        if components.get("volatility_filter"):
            self._add_volatility_block(graph)
        
        if components.get("analyzer_agreement"):
            self._add_agreement_block(graph)
        
        if components.get("trade_execution"):
            self._add_execution_block(graph)
        
        # Add risk management
        self._add_risk_block(graph)
        
        # Validate
        self._builder._current_graph = graph
        self._builder.validate_graph()
        
        return graph
    
    def _parse_description(self, description: str) -> Dict[str, Any]:
        """Parse description into components"""
        components = {}
        desc_lower = description.lower()
        
        # Check for indicators
        indicators = []
        if "rsi" in desc_lower:
            indicators.append("rsi")
        if "moving average" in desc_lower or "ma" in desc_lower:
            indicators.append("moving_average")
        if "bollinger" in desc_lower:
            indicators.append("bollinger_bands")
        if "macd" in desc_lower:
            indicators.append("macd")
        if "momentum" in desc_lower:
            indicators.append("momentum")
        
        if indicators:
            components["indicators"] = indicators
        
        # Check for confidence filter
        confidence_patterns = [
            r"confidence (?:is|>=|>|=)\s*(\d+)",
            r"confidence exceeds?\s*(\d+)",
        ]
        for pattern in confidence_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                components["confidence_filter"] = {
                    "threshold": int(match.group(1)),
                }
                break
        
        if "confidence" in desc_lower:
            components["confidence_filter"] = {"threshold": 70}
        
        # Check for volatility
        if "volatility" in desc_lower or "volatile" in desc_lower:
            components["volatility_filter"] = True
        
        # Check for analyzer agreement
        if any(word in desc_lower for word in ["agree", "consensus", "multiple", "all"]):
            components["analyzer_agreement"] = True
        
        # Check for trade execution
        if any(word in desc_lower for word in ["trade", "buy", "sell", "execute"]):
            components["trade_execution"] = True
        
        return components
    
    def _extract_name(self, description: str) -> Optional[str]:
        """Extract a name from the description"""
        # Try to find a quoted name
        match = re.search(r'["\']([^"\']+)["\']', description)
        if match:
            return match.group(1)
        
        # Use first sentence
        sentences = description.split(".")
        if sentences:
            first = sentences[0].strip()
            return first[:50] if len(first) > 50 else first
        
        return None
    
    def _add_market_data_block(self, graph: StrategyGraph) -> StrategyBlock:
        """Add market data block"""
        return self._builder.add_block(BlockType.MARKET_DATA, "Market Data")
    
    def _add_indicator_blocks(
        self,
        graph: StrategyGraph,
        indicators: List[str],
    ) -> List[StrategyBlock]:
        """Add indicator blocks"""
        blocks = []
        
        indicator_map = {
            "rsi": (BlockType.INDICATOR, "RSI Indicator"),
            "moving_average": (BlockType.INDICATOR, "Moving Average"),
            "bollinger_bands": (BlockType.INDICATOR, "Bollinger Bands"),
            "macd": (BlockType.INDICATOR, "MACD"),
            "momentum": (BlockType.STATISTICAL_FEATURE, "Momentum"),
        }
        
        for ind in indicators:
            block_type, name = indicator_map.get(ind, (BlockType.INDICATOR, ind))
            block = self._builder.add_block(block_type, name)
            blocks.append(block)
        
        return blocks
    
    def _add_confidence_block(
        self,
        graph: StrategyGraph,
        config: Dict[str, Any],
    ) -> StrategyBlock:
        """Add confidence filter block"""
        block = self._builder.add_block(
            BlockType.CONFIDENCE_FILTER,
            "Confidence Filter",
        )
        block.config.parameters["threshold"] = config.get("threshold", 70)
        return block
    
    def _add_volatility_block(self, graph: StrategyGraph) -> StrategyBlock:
        """Add volatility filter block"""
        return self._builder.add_block(
            BlockType.STATISTICAL_FEATURE,
            "Volatility Check",
        )
    
    def _add_agreement_block(self, graph: StrategyGraph) -> StrategyBlock:
        """Add analyzer agreement block"""
        return self._builder.add_block(
            BlockType.LOGIC_GATE,
            "Analyzer Agreement",
        )
    
    def _add_execution_block(self, graph: StrategyGraph) -> StrategyBlock:
        """Add trade execution block"""
        return self._builder.add_block(
            BlockType.TRADE_EXECUTION,
            "Execute Trade",
        )
    
    def _add_risk_block(self, graph: StrategyGraph) -> StrategyBlock:
        """Add risk management block"""
        return self._builder.add_block(
            BlockType.RISK_RULE,
            "Risk Management",
        )
    
    def generate_code_template(self, description: str) -> str:
        """Generate a code template from description"""
        components = self._parse_description(description)
        
        template = '''
"""
Strategy generated from description:
{description}

Generated: {timestamp}
"""

class GeneratedStrategy:
    """
    Auto-generated trading strategy based on natural language description.
    """
    
    def __init__(self, config):
        self.config = config
        self._setup_components()
    
    def _setup_components(self):
        """Initialize strategy components"""
'''
        
        # Add components based on parsed description
        if components.get("indicators"):
            template += '''
        # Indicators: {indicators}
        self.indicators = {indicators}
'''.format(indicators=components["indicators"])
        
        if components.get("confidence_filter"):
            template += '''
        # Confidence threshold: {threshold}%
        self.confidence_threshold = {threshold}
'''.format(threshold=components["confidence_filter"]["threshold"])
        
        template += '''
    
    async def on_tick(self, market_data):
        """Process incoming market data"""
        # Generate signals
        signals = await self.generate_signals(market_data)
        
        # Filter by confidence
        if self.config.get("min_confidence"):
            signals = self.filter_by_confidence(signals)
        
        # Execute if conditions met
        if signals:
            await self.execute(signals)
    
    async def generate_signals(self, market_data):
        """Generate trading signals"""
        signals = []
        
        # Add signal generation logic here
        return signals
    
    def filter_by_confidence(self, signals):
        """Filter signals by confidence threshold"""
        return [
            s for s in signals
            if s.get("confidence", 0) >= self.confidence_threshold
        ]
    
    async def execute(self, signals):
        """Execute trading signals"""
        # Add execution logic here
        pass
'''.format(timestamp=datetime.now(timezone.utc).isoformat())
        
        return template
