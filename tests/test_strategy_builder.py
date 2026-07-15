"""
Tests for Strategy Builder
========================
"""

import pytest
from datetime import datetime

from strategy_builder import (
    Block,
    BlockType,
    BlockCategory,
    BlockPort,
    BlockDefinition,
    StrategyGraph,
    GraphNode,
    GraphEdge,
    EdgeType,
    StrategyBuilder,
    BuilderState,
    StrategyValidator,
    CodeGenerator,
    DocumentationGenerator,
    TestGenerator,
    VersionManager,
    DeploymentManager,
    DeploymentTarget,
    DeploymentConfig
)


class TestBlocks:
    """Tests for block system"""
    
    def test_create_block(self):
        """Test creating a block"""
        block = BlockDefinition.create_block(BlockType.SMA, "My SMA")
        
        assert block.name == "My SMA"
        assert block.block_type == BlockType.SMA
        assert block.category == BlockCategory.INDICATOR
    
    def test_block_parameters(self):
        """Test block parameters"""
        block = BlockDefinition.create_block(BlockType.SMA)
        
        period = block.get_parameter("period")
        assert period == 20  # Default value
        
        block.set_parameter("period", 50)
        assert block.get_parameter("period") == 50
    
    def test_block_hash(self):
        """Test block hash generation"""
        block1 = BlockDefinition.create_block(BlockType.SMA, "Test1")
        
        # Hash should be a valid hex string
        assert len(block1.get_hash()) > 0
        assert block1.get_hash().isalnum()


class TestGraph:
    """Tests for strategy graph"""
    
    def test_create_graph(self):
        """Test creating a graph"""
        graph = StrategyGraph()
        
        assert graph.name == "Untitled Strategy"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_add_node(self):
        """Test adding nodes to graph"""
        graph = StrategyGraph()
        block = BlockDefinition.create_block(BlockType.MARKET_DATA)
        
        node = graph.add_node(block)
        
        assert node.node_id in graph.nodes
        assert len(graph.nodes) == 1
    
    def test_add_edge(self):
        """Test connecting blocks"""
        graph = StrategyGraph()
        
        # Add blocks
        market_block = BlockDefinition.create_block(BlockType.MARKET_DATA)
        sma_block = BlockDefinition.create_block(BlockType.SMA)
        
        market_node = graph.add_node(market_block)
        sma_node = graph.add_node(sma_block)
        
        # Connect
        edge = graph.add_edge(
            source_block_id=market_block.block_id,
            source_port_id="out_data",
            target_block_id=sma_block.block_id,
            target_port_id="in_series"
        )
        
        assert edge is not None
        assert len(graph.edges) == 1
    
    def test_topological_sort(self):
        """Test topological ordering"""
        graph = StrategyGraph()
        
        market = BlockDefinition.create_block(BlockType.MARKET_DATA)
        sma = BlockDefinition.create_block(BlockType.SMA)
        threshold = BlockDefinition.create_block(BlockType.THRESHOLD)
        
        graph.add_node(market)
        graph.add_node(sma)
        graph.add_node(threshold)
        
        graph.add_edge(market.block_id, "out_data", sma.block_id, "in_series")
        graph.add_edge(sma.block_id, "out_result", threshold.block_id, "in_value")
        
        sorted_nodes = graph.topological_sort()
        
        assert len(sorted_nodes) == 3
        # Market should come first
        assert sorted_nodes[0].block.block_type == BlockType.MARKET_DATA
    
    def test_unreachable_blocks(self):
        """Test finding unreachable blocks"""
        graph = StrategyGraph()
        
        # Create connected chain
        market = BlockDefinition.create_block(BlockType.MARKET_DATA)
        sma = BlockDefinition.create_block(BlockType.SMA)
        
        graph.add_node(market)
        graph.add_node(sma)
        
        # Note: market has no input, so it's a source, sma is connected to market
        graph.add_edge(market.block_id, "out_data", sma.block_id, "in_series")
        
        unreachable = graph.find_unreachable_blocks()
        
        # All blocks are reachable (market is a source)
        assert len(unreachable) == 0
    
    def test_graph_statistics(self):
        """Test graph statistics"""
        graph = StrategyGraph()
        
        market = BlockDefinition.create_block(BlockType.MARKET_DATA)
        sma = BlockDefinition.create_block(BlockType.SMA)
        
        graph.add_node(market)
        graph.add_node(sma)
        
        graph.add_edge(market.block_id, "out_data", sma.block_id, "in_series")
        
        stats = graph.get_statistics()
        
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1


class TestBuilder:
    """Tests for strategy builder"""
    
    def test_create_builder(self):
        """Test creating builder"""
        builder = StrategyBuilder()
        
        assert builder.state == BuilderState.IDLE
        assert len(builder.graph.nodes) == 0
    
    def test_add_block(self):
        """Test adding blocks via builder"""
        builder = StrategyBuilder()
        
        block = builder.add_block(BlockType.SMA, position=(100, 200))
        
        assert block.block_type == BlockType.SMA
        assert block.position == (100, 200)
        assert block.block_id in builder.graph._block_index
    
    def test_connect_blocks(self):
        """Test connecting blocks"""
        builder = StrategyBuilder()
        
        market = builder.add_block(BlockType.MARKET_DATA)
        sma = builder.add_block(BlockType.SMA)
        
        edge = builder.connect(
            source_block_id=market.block_id,
            source_port_id="out_data",
            target_block_id=sma.block_id,
            target_port_id="in_series"
        )
        
        assert edge is not None
        assert len(builder.graph.edges) == 1
    
    def test_live_validation(self):
        """Test live validation"""
        builder = StrategyBuilder()
        
        # Add connected blocks
        market = builder.add_block(BlockType.MARKET_DATA)
        sma = builder.add_block(BlockType.SMA)
        
        builder.connect(
            source_block_id=market.block_id,
            source_port_id="out_data",
            target_block_id=sma.block_id,
            target_port_id="in_series"
        )
        
        result = builder.validate_live()
        
        assert "issues" in result
        assert "stats" in result
    
    def test_code_generation(self):
        """Test code generation"""
        builder = StrategyBuilder()
        
        market = builder.add_block(BlockType.MARKET_DATA)
        sma = builder.add_block(BlockType.SMA)
        
        builder.connect(
            source_block_id=market.block_id,
            source_port_id="out_data",
            target_block_id=sma.block_id,
            target_port_id="in_series"
        )
        
        code = builder.generate_code()
        
        assert "class Strategy" in code
        assert "SMA" in code
        assert "MarketData" in code


class TestValidator:
    """Tests for strategy validator"""
    
    def test_validate_empty_graph(self):
        """Test validation of empty graph"""
        graph = StrategyGraph()
        validator = StrategyValidator()
        
        result = validator.validate(graph)
        
        assert result["valid"] is False
        assert result["error_count"] > 0
    
    def test_validate_missing_inputs(self):
        """Test validation finds missing inputs"""
        graph = StrategyGraph()
        
        sma = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(sma)
        
        validator = StrategyValidator()
        result = validator.validate(graph)
        
        # Should have error about disconnected input
        has_input_error = any(
            "not connected" in i["message"].lower()
            for i in result["issues"]
        )
        assert has_input_error


class TestGenerators:
    """Tests for code generators"""
    
    def test_code_generator(self):
        """Test code generation"""
        graph = StrategyGraph()
        
        market = BlockDefinition.create_block(BlockType.MARKET_DATA)
        sma = BlockDefinition.create_block(BlockType.SMA)
        
        graph.add_node(market)
        graph.add_node(sma)
        
        graph.add_edge(market.block_id, "out_data", sma.block_id, "in_series")
        
        generator = CodeGenerator()
        code = generator.generate(graph)
        
        assert "import pandas" in code
        assert "class Strategy" in code
    
    def test_documentation_generator(self):
        """Test documentation generation"""
        graph = StrategyGraph()
        graph.name = "Test Strategy"
        
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        generator = DocumentationGenerator()
        docs = generator.generate(graph)
        
        assert "Test Strategy" in docs
        assert "## Statistics" in docs
    
    def test_test_generator(self):
        """Test test generation"""
        graph = StrategyGraph()
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        generator = TestGenerator()
        tests = generator.generate(graph)
        
        assert "import pytest" in tests
        assert "class TestStrategy" in tests


class TestVersioning:
    """Tests for version management"""
    
    def test_create_version(self, tmp_path):
        """Test creating versions"""
        db_path = str(tmp_path / "versions.json")
        manager = VersionManager(db_path=db_path)
        
        graph = StrategyGraph()
        graph.name = "Test"
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        version = manager.create_version(
            strategy_id="test_strategy",
            graph=graph,
            version_number="1.0.0",
            author="test",
            message="Initial version"
        )
        
        assert version.version_number == "1.0.0"
        assert version.author == "test"
    
    def test_get_versions(self, tmp_path):
        """Test getting versions"""
        db_path = str(tmp_path / "versions.json")
        manager = VersionManager(db_path=db_path)
        
        graph = StrategyGraph()
        graph.name = "Test"
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        manager.create_version(
            strategy_id="test",
            graph=graph,
            version_number="1.0.0",
            author="test",
            message="v1"
        )
        
        versions = manager.get_versions("test")
        assert len(versions) == 1


class TestDeployment:
    """Tests for deployment"""
    
    def test_deploy_paper(self):
        """Test paper trading deployment"""
        manager = DeploymentManager()
        
        graph = StrategyGraph()
        graph.name = "Test Strategy"
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        config = DeploymentConfig(
            target=DeploymentTarget.PAPER_TRADING,
            strategy_id="test",
            strategy_name="Test"
        )
        
        deployment = manager.deploy(graph, config)
        
        assert deployment.deployment_id is not None
        assert deployment.config.target == DeploymentTarget.PAPER_TRADING
    
    def test_stop_deployment(self):
        """Test stopping deployment"""
        manager = DeploymentManager()
        
        graph = StrategyGraph()
        block = BlockDefinition.create_block(BlockType.SMA)
        graph.add_node(block)
        
        config = DeploymentConfig(
            target=DeploymentTarget.BACKTEST,
            strategy_id="test",
            strategy_name="Test"
        )
        
        deployment = manager.deploy(graph, config)
        
        result = manager.stop(deployment.deployment_id)
        
        assert result is True
        assert deployment.status.value == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
