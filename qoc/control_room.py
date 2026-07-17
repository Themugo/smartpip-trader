"""
Control Room
============

Mission Control dashboard for the trading platform.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .core import (
    OperationalStatus,
    ComponentStatus,
    HealthScore,
    Alert,
)

logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Health status of a component"""
    name: str
    status: ComponentStatus
    score: float
    latency_ms: float = 0
    error_rate: float = 0
    last_check: float = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class MarketStatus:
    """Market trading status"""
    symbol: str
    connected: bool
    last_price: float = 0
    spread: float = 0
    volume: float = 0
    last_tick: float = 0


@dataclass
class TradingStatus:
    """Trading status"""
    mode: str  # paper, live, disabled
    active_strategies: int = 0
    total_trades: int = 0
    open_positions: int = 0
    pending_orders: int = 0
    pnl_today: float = 0
    sharpe_today: float = 0


class ControlRoom:
    """
    Mission Control dashboard.
    
    Provides unified view of all system components.
    """
    
    def __init__(self):
        # Component statuses
        self._components: Dict[str, ComponentHealth] = {}
        
        # Market statuses
        self._markets: Dict[str, MarketStatus] = {}
        
        # Trading statuses
        self._paper_status = TradingStatus(mode="paper")
        self._live_status = TradingStatus(mode="live")
        
        # Alerts
        self._alerts: List[Alert] = []
        
        # Incidents
        self._incidents: List[Dict] = []
        
        # Validation queue
        self._validation_queue: List[Dict] = []
        
        # Research queue
        self._research_queue: List[Dict] = []
        
        # Deployment status
        self._deployment_status: Dict[str, Any] = {}
    
    # ========== Component Management ==========
    
    def register_component(
        self,
        name: str,
        check_fn: Optional[callable] = None,
    ) -> None:
        """Register a system component"""
        self._components[name] = ComponentHealth(
            name=name,
            status=ComponentStatus.UNKNOWN,
            score=0.0,
        )
    
    def update_component(
        self,
        name: str,
        status: ComponentStatus,
        score: float,
        issues: List[str] = None,
        latency_ms: float = 0,
        error_rate: float = 0,
    ) -> None:
        """Update component status"""
        if name in self._components:
            self._components[name].status = status
            self._components[name].score = score
            self._components[name].latency_ms = latency_ms
            self._components[name].error_rate = error_rate
            self._components[name].last_check = time.time()
            self._components[name].issues = issues or []
    
    def get_component(self, name: str) -> Optional[ComponentHealth]:
        """Get component status"""
        return self._components.get(name)
    
    # ========== Market Management ==========
    
    def update_market(
        self,
        symbol: str,
        connected: bool,
        last_price: float = 0,
        spread: float = 0,
        volume: float = 0,
    ) -> None:
        """Update market status"""
        self._markets[symbol] = MarketStatus(
            symbol=symbol,
            connected=connected,
            last_price=last_price,
            spread=spread,
            volume=volume,
            last_tick=time.time(),
        )
    
    # ========== Trading Status ==========
    
    def update_paper_status(self, status: TradingStatus) -> None:
        """Update paper trading status"""
        self._paper_status = status
    
    def update_live_status(self, status: TradingStatus) -> None:
        """Update live trading status"""
        self._live_status = status
    
    # ========== Alert Management ==========
    
    def raise_alert(
        self,
        severity: str,
        component: str,
        title: str,
        description: str,
    ) -> Alert:
        """Raise an alert"""
        alert = Alert(
            alert_id=f"alert_{int(time.time() * 1000)}",
            severity=severity,
            component=component,
            title=title,
            description=description,
        )
        self._alerts.append(alert)
        logger.warning(f"Alert raised: {title}")
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = time.time()
                return True
        return False
    
    def get_active_alerts(
        self,
        severity: Optional[str] = None,
    ) -> List[Alert]:
        """Get active alerts"""
        alerts = [a for a in self._alerts if not a.resolved]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts
    
    # ========== Incident Management ==========
    
    def add_incident(self, incident: Dict) -> None:
        """Add an incident"""
        incident["created_at"] = time.time()
        self._incidents.append(incident)
    
    def get_active_incidents(self) -> List[Dict]:
        """Get active incidents"""
        return [i for i in self._incidents if i.get("status") != "resolved"]
    
    # ========== Validation Queue ==========
    
    def add_to_validation(self, item: Dict) -> None:
        """Add item to validation queue"""
        item["queued_at"] = time.time()
        self._validation_queue.append(item)
    
    def get_validation_queue(self) -> List[Dict]:
        """Get validation queue"""
        return self._validation_queue.copy()
    
    def complete_validation(self, item_id: str) -> bool:
        """Mark validation as complete"""
        for item in self._validation_queue:
            if item.get("id") == item_id:
                item["completed_at"] = time.time()
                return True
        return False
    
    # ========== Research Queue ==========
    
    def add_to_research(self, item: Dict) -> None:
        """Add item to research queue"""
        item["queued_at"] = time.time()
        self._research_queue.append(item)
    
    def get_research_queue(self) -> List[Dict]:
        """Get research queue"""
        return self._research_queue.copy()
    
    # ========== Deployment ==========
    
    def set_deployment_status(self, status: Dict) -> None:
        """Set deployment status"""
        self._deployment_status = status
        self._deployment_status["updated_at"] = time.time()
    
    # ========== Health Score ==========
    
    def calculate_health_score(self) -> HealthScore:
        """Calculate overall health score"""
        # Calculate component scores
        component_scores = {}
        for name, comp in self._components.items():
            component_scores[name] = comp.score
        
        # System score (infrastructure + system components)
        system_comps = ["database", "api", "cache", "queue"]
        system_score = self._avg_scores([component_scores.get(c, 0.5) for c in system_comps])
        
        # Market score
        market_score = 1.0 if self._markets else 0.5
        if self._markets:
            connected = sum(1 for m in self._markets.values() if m.connected)
            market_score = connected / len(self._markets)
        
        # Paper trading score
        paper_score = 0.8 if self._paper_status else 0.5
        
        # Live trading score
        live_score = 0.8 if self._live_status else 0.5
        
        # Strategy score
        strategy_comps = ["strategy_manager", "strategy_engine"]
        strategy_score = self._avg_scores([component_scores.get(c, 0.8) for c in strategy_comps])
        
        # Model score
        model_comps = ["model_registry", "model_predictor"]
        model_score = self._avg_scores([component_scores.get(c, 0.8) for c in model_comps])
        
        # Risk score
        risk_comps = ["risk_manager", "risk_evaluator"]
        risk_score = self._avg_scores([component_scores.get(c, 0.8) for c in risk_comps])
        
        # Infrastructure score
        infra_score = self._avg_scores([
            system_score,
            market_score,
            self._components.get("monitoring", ComponentHealth("", ComponentStatus.HEALTHY, 0.9)).score,
        ])
        
        # Overall score (weighted average)
        overall = (
            system_score * 0.15 +
            market_score * 0.10 +
            paper_score * 0.10 +
            live_score * 0.15 +
            strategy_score * 0.15 +
            model_score * 0.15 +
            risk_score * 0.10 +
            infra_score * 0.10
        )
        
        return HealthScore(
            overall=overall,
            system=system_score,
            market=market_score,
            paper_trading=paper_score,
            live_trading=live_score,
            strategy=strategy_score,
            model=model_score,
            risk=risk_score,
            infrastructure=infra_score,
            component_scores=component_scores,
        )
    
    def _avg_scores(self, scores: List[float]) -> float:
        """Calculate average of scores"""
        if not scores:
            return 0.5
        return sum(scores) / len(scores)
    
    # ========== Dashboard ==========
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get full dashboard state"""
        health = self.calculate_health_score()
        
        return {
            "timestamp": time.time(),
            
            # Overall status
            "overall_status": health.get_status().value,
            "health_score": health.to_dict(),
            
            # Components
            "components": {
                name: {
                    "status": comp.status.value,
                    "score": comp.score,
                    "latency_ms": comp.latency_ms,
                    "error_rate": comp.error_rate,
                    "last_check": comp.last_check,
                    "issues": comp.issues,
                }
                for name, comp in self._components.items()
            },
            
            # Markets
            "markets": {
                symbol: {
                    "connected": m.connected,
                    "last_price": m.last_price,
                    "spread": m.spread,
                    "volume": m.volume,
                }
                for symbol, m in self._markets.items()
            },
            
            # Trading
            "paper_trading": {
                "mode": self._paper_status.mode,
                "active_strategies": self._paper_status.active_strategies,
                "total_trades": self._paper_status.total_trades,
                "open_positions": self._paper_status.open_positions,
                "pnl_today": self._paper_status.pnl_today,
            },
            "live_trading": {
                "mode": self._live_status.mode,
                "active_strategies": self._live_status.active_strategies,
                "total_trades": self._live_status.total_trades,
                "open_positions": self._live_status.open_positions,
                "pnl_today": self._live_status.pnl_today,
            },
            
            # Alerts
            "alerts": {
                "total": len(self._alerts),
                "active": len(self.get_active_alerts()),
                "critical": len(self.get_active_alerts("critical")),
                "high": len(self.get_active_alerts("high")),
                "recent": self.get_active_alerts()[:10],
            },
            
            # Incidents
            "incidents": {
                "active": len(self.get_active_incidents()),
                "recent": self.get_active_incidents()[:5],
            },
            
            # Queues
            "validation_queue": {
                "pending": len(self._validation_queue),
                "items": self._validation_queue[:10],
            },
            "research_queue": {
                "pending": len(self._research_queue),
                "items": self._research_queue[:10],
            },
            
            # Deployment
            "deployment": self._deployment_status,
        }
    
    def get_mission_control(self) -> str:
        """Generate mission control summary"""
        health = self.calculate_health_score()
        active_alerts = self.get_active_alerts()
        active_incidents = self.get_active_incidents()
        
        status_emoji = {
            OperationalStatus.OPERATIONAL: "🟢",
            OperationalStatus.DEGRADED: "🟡",
            OperationalStatus.PARTIAL_OUTAGE: "🟠",
            OperationalStatus.MAJOR_OUTAGE: "🔴",
            OperationalStatus.MAINTENANCE: "🔵",
        }
        
        lines = [
            f"# Mission Control - SmartPip Trader",
            f"",
            f"**Status:** {status_emoji.get(health.get_status(), '⚪')} {health.get_status().value.upper()}",
            f"**Health Score:** {health.overall:.1%} ({health.get_grade()})",
            f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## Component Health",
            f"",
            f"| Component | Status | Score |",
            f"|-----------|--------|-------|",
        ]
        
        for name, comp in self._components.items():
            status_icon = "✅" if comp.status == ComponentStatus.HEALTHY else "⚠️" if comp.status == ComponentStatus.DEGRADED else "❌"
            lines.append(f"| {name} | {status_icon} {comp.status.value} | {comp.score:.1%} |")
        
        if active_alerts:
            lines.append("")
            lines.append("## Active Alerts")
            for alert in active_alerts[:5]:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(alert.severity, "⚪")
                lines.append(f"- {severity_icon} [{alert.severity.upper()}] {alert.title}")
        
        if active_incidents:
            lines.append("")
            lines.append("## Active Incidents")
            for incident in active_incidents[:5]:
                lines.append(f"- 🔴 {incident.get('title', 'Unknown')}")
        
        lines.append("")
        lines.append(f"## Queues")
        lines.append(f"- Validation: {len(self._validation_queue)} pending")
        lines.append(f"- Research: {len(self._research_queue)} pending")
        
        return "\n".join(lines)
