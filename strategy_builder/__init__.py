"""
Visual Strategy Builder
====================

Professional visual strategy authoring environment with drag-and-drop workflows.
"""

__version__ = "1.0.0"

from .blocks import (
    Block,
    BlockType,
    BlockCategory,
    BlockPort,
    BlockParameter,
    PortType,
    BlockDefinition
)
from .graph import StrategyGraph, GraphNode, GraphEdge, EdgeType
from .builder import StrategyBuilder, BuilderState
from .validator import StrategyValidator, ValidationResult, ValidationLevel
from .generator import CodeGenerator, DocumentationGenerator, TestGenerator
from .versioning import VersionManager, StrategyVersion, VersionDiff
from .deployment import (
    DeploymentManager,
    DeploymentTarget,
    DeploymentStatus,
    DeploymentConfig,
    Deployment
)

__all__ = [
    # Blocks
    "Block",
    "BlockType",
    "BlockCategory",
    "BlockPort",
    "BlockParameter",
    "PortType",
    "BlockDefinition",
    # Graph
    "StrategyGraph",
    "GraphNode",
    "GraphEdge",
    "EdgeType",
    # Builder
    "StrategyBuilder",
    "BuilderState",
    # Validation
    "StrategyValidator",
    "ValidationResult",
    "ValidationLevel",
    # Generators
    "CodeGenerator",
    "DocumentationGenerator",
    "TestGenerator",
    # Versioning
    "VersionManager",
    "StrategyVersion",
    "VersionDiff",
    # Deployment
    "DeploymentManager",
    "DeploymentTarget",
    "DeploymentStatus",
    "DeploymentConfig",
    "Deployment",
]
