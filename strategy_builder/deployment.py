"""
Deployment Manager
=================

Manages strategy deployment to different targets.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .graph import StrategyGraph

logger = logging.getLogger(__name__)


class DeploymentTarget(Enum):
    """Deployment targets"""
    PAPER_TRADING = "paper_trading"
    BACKTEST = "backtest"
    LIVE = "live"
    EXPORT = "export"


class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class DeploymentConfig:
    """Configuration for deployment"""
    target: DeploymentTarget
    strategy_id: str
    strategy_name: str
    
    # Paper trading
    initial_capital: float = 100000.0
    commission: float = 0.0001
    slippage: float = 0.00005
    
    # Backtest
    start_date: datetime = None
    end_date: datetime = None
    timeframe: str = "1h"
    
    # Live trading
    risk_per_trade: float = 1.0
    max_positions: int = 5
    auto_stop_loss: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target.value,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "initial_capital": self.initial_capital,
            "commission": self.commission,
            "slippage": self.slippage,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "timeframe": self.timeframe,
            "risk_per_trade": self.risk_per_trade,
            "max_positions": self.max_positions,
            "auto_stop_loss": self.auto_stop_loss
        }


@dataclass
class Deployment:
    """A deployment instance"""
    deployment_id: str
    config: DeploymentConfig
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "results": self.results,
            "logs": self.logs,
            "errors": self.errors
        }


class DeploymentManager:
    """
    Manages strategy deployment to various targets.
    
    Supports:
    - Paper trading
    - Backtesting
    - Live deployment
    - Export
    """
    
    def __init__(self):
        self.deployments: Dict[str, Deployment] = {}
        self._backends = {
            DeploymentTarget.PAPER_TRADING: self._deploy_paper,
            DeploymentTarget.BACKTEST: self._deploy_backtest,
            DeploymentTarget.LIVE: self._deploy_live,
            DeploymentTarget.EXPORT: self._deploy_export
        }
    
    def deploy(
        self,
        graph: StrategyGraph,
        config: DeploymentConfig
    ) -> Deployment:
        """Deploy a strategy to a target"""
        deployment_id = str(uuid4())
        
        deployment = Deployment(
            deployment_id=deployment_id,
            config=config,
            status=DeploymentStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.deployments[deployment_id] = deployment
        
        logger.info(f"Created deployment {deployment_id} for {config.target.value}")
        
        # Start deployment in background
        try:
            backend = self._backends.get(config.target)
            if backend:
                deployment.status = DeploymentStatus.DEPLOYING
                deployment.started_at = datetime.now()
                backend(deployment, graph)
            else:
                raise ValueError(f"Unknown target: {config.target}")
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.errors.append(str(e))
            logger.error(f"Deployment failed: {e}")
        
        return deployment
    
    def _deploy_paper(self, deployment: Deployment, graph: StrategyGraph) -> None:
        """Deploy to paper trading"""
        deployment.logs.append(f"Starting paper trading deployment...")
        
        # Generate paper trading configuration
        paper_config = {
            "strategy": graph.name,
            "initial_capital": deployment.config.initial_capital,
            "commission": deployment.config.commission,
            "slippage": deployment.config.slippage,
            "generated_at": datetime.now().isoformat()
        }
        
        deployment.logs.append(f"Configuration: {paper_config}")
        
        # Simulate paper trading
        # In production, this would connect to a broker API
        deployment.logs.append("Paper trading simulation started...")
        
        # Mock results
        deployment.results = {
            "trades": [],
            "equity": [100000],
            "status": "running"
        }
        
        deployment.status = DeploymentStatus.DEPLOYED
        deployment.logs.append("Paper trading deployment complete")
    
    def _deploy_backtest(self, deployment: Deployment, graph: StrategyGraph) -> None:
        """Deploy to backtesting"""
        deployment.logs.append(f"Starting backtest deployment...")
        
        # Generate backtest configuration
        backtest_config = {
            "strategy": graph.name,
            "start_date": deployment.config.start_date.isoformat() if deployment.config.start_date else "2024-01-01",
            "end_date": deployment.config.end_date.isoformat() if deployment.config.end_date else "2024-12-31",
            "timeframe": deployment.config.timeframe,
            "capital": deployment.config.initial_capital,
            "generated_at": datetime.now().isoformat()
        }
        
        deployment.logs.append(f"Configuration: {backtest_config}")
        
        # Simulate backtesting
        deployment.logs.append("Running backtest...")
        
        # Mock results
        deployment.results = {
            "total_return": 0.15,
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.08,
            "win_rate": 0.55,
            "trade_count": 150,
            "equity_curve": [100000 + i * 100 for i in range(100)]
        }
        
        deployment.status = DeploymentStatus.DEPLOYED
        deployment.logs.append("Backtest complete")
    
    def _deploy_live(self, deployment: Deployment, graph: StrategyGraph) -> None:
        """Deploy to live trading"""
        deployment.logs.append(f"WARNING: Live trading deployment requested")
        deployment.logs.append("Validating strategy...")
        
        # Validate for live trading
        has_risk = any(
            n.block.category.value == "risk"
            for n in graph.nodes.values()
        )
        has_execution = any(
            n.block.category.value == "execution"
            for n in graph.nodes.values()
        )
        
        if not has_risk:
            deployment.errors.append("Strategy lacks risk management - NOT RECOMMENDED FOR LIVE")
        
        if not has_execution:
            deployment.errors.append("Strategy lacks execution blocks")
        
        # Request confirmation
        deployment.logs.append("Live trading requires manual approval")
        deployment.logs.append("Please review deployment in the dashboard")
        
        # For now, mark as deployed with warning
        deployment.results = {
            "status": "pending_approval",
            "warnings": deployment.errors
        }
        
        deployment.status = DeploymentStatus.DEPLOYED
    
    def _deploy_export(self, deployment: Deployment, graph: StrategyGraph) -> None:
        """Export strategy"""
        from .generator import CodeGenerator
        
        deployment.logs.append("Generating export...")
        
        generator = CodeGenerator()
        code = generator.generate(graph)
        
        deployment.results = {
            "code": code,
            "filename": f"{graph.name.replace(' ', '_').lower()}_strategy.py"
        }
        
        deployment.logs.append(f"Exported to {deployment.results['filename']}")
        deployment.status = DeploymentStatus.DEPLOYED
    
    def stop(self, deployment_id: str) -> bool:
        """Stop a deployment"""
        deployment = self.deployments.get(deployment_id)
        
        if not deployment:
            return False
        
        deployment.status = DeploymentStatus.STOPPED
        deployment.stopped_at = datetime.now()
        
        deployment.logs.append(f"Deployment stopped at {deployment.stopped_at.isoformat()}")
        
        logger.info(f"Stopped deployment {deployment_id}")
        
        return True
    
    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get a deployment by ID"""
        return self.deployments.get(deployment_id)
    
    def get_active_deployments(self) -> List[Deployment]:
        """Get all active deployments"""
        return [
            d for d in self.deployments.values()
            if d.status in [DeploymentStatus.DEPLOYED, DeploymentStatus.DEPLOYING]
        ]
    
    def get_deployment_history(
        self,
        strategy_id: str = None,
        limit: int = 10
    ) -> List[Deployment]:
        """Get deployment history"""
        deployments = list(self.deployments.values())
        
        if strategy_id:
            deployments = [
                d for d in deployments
                if d.config.strategy_id == strategy_id
            ]
        
        # Sort by creation time, newest first
        deployments.sort(key=lambda d: d.created_at, reverse=True)
        
        return deployments[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get deployment statistics"""
        total = len(self.deployments)
        active = len(self.get_active_deployments())
        failed = sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.FAILED)
        
        return {
            "total_deployments": total,
            "active_deployments": active,
            "failed_deployments": failed,
            "by_target": {
                target.value: sum(
                    1 for d in self.deployments.values()
                    if d.config.target == target
                )
                for target in DeploymentTarget
            }
        }
