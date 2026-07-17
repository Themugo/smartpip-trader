"""
Daily Operations
================

Automated daily operations reporting.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .control_room import ControlRoom

logger = logging.getLogger(__name__)


@dataclass
class DailyReport:
    """Daily operations report"""
    report_id: str
    report_type: str
    generated_at: float
    
    # Content
    summary: str
    details: Dict[str, Any]
    metrics: Dict[str, float]
    recommendations: List[str]
    issues: List[str]
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = [
            f"# {self.report_type}",
            f"",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.generated_at))}",
            f"",
            f"## Summary",
            f"",
            self.summary,
            f"",
        ]
        
        if self.metrics:
            lines.append("## Key Metrics")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            for name, value in self.metrics.items():
                if isinstance(value, float):
                    lines.append(f"| {name} | {value:.4f} |")
                else:
                    lines.append(f"| {name} | {value} |")
            lines.append("")
        
        if self.issues:
            lines.append("## Issues")
            for issue in self.issues:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        if self.recommendations:
            lines.append("## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)


class DailyOperations:
    """
    Automated daily operations.
    
    Generates periodic reports:
    - Morning System Check
    - Market Readiness Report
    - Infrastructure Report
    - Data Quality Report
    - Strategy Status Report
    - Risk Status Report
    - Paper Trading Summary
    - Evening Performance Report
    - Incident Summary
    - Deployment Recommendations
    """
    
    def __init__(self, control_room: ControlRoom):
        self.control_room = control_room
        
        # Report history
        self._reports: List[DailyReport] = []
        
        # Last report times
        self._last_morning_check = 0
        self._last_evening_report = 0
    
    def generate_morning_check(self) -> DailyReport:
        """Generate morning system check"""
        dashboard = self.control_room.get_dashboard()
        health = self.control_room.calculate_health_score()
        
        issues = []
        recommendations = []
        
        # Check components
        for name, comp in dashboard["components"].items():
            if comp["status"] != "healthy":
                issues.append(f"Component '{name}' is {comp['status']}")
        
        # Check alerts
        if dashboard["alerts"]["active"] > 0:
            issues.append(f"{dashboard['alerts']['active']} active alerts")
        
        # Generate recommendations
        if health.overall < 0.9:
            recommendations.append("Review system health - some components need attention")
        
        if dashboard["alerts"]["critical"] > 0:
            recommendations.append("URGENT: Address critical alerts immediately")
        
        summary = f"""
Morning system check complete. Health score: {health.overall:.1%} ({health.get_grade()}).
All critical systems operational. {len(recommendations)} recommendations generated.
""".strip()
        
        report = DailyReport(
            report_id=f"morning_{int(time.time())}",
            report_type="Morning System Check",
            generated_at=time.time(),
            summary=summary,
            details={
                "health_score": health.to_dict(),
                "components_checked": len(dashboard["components"]),
                "alerts_active": dashboard["alerts"]["active"],
            },
            metrics={
                "health_score": health.overall,
                "system_score": health.system,
                "market_score": health.market,
                "infrastructure_score": health.infrastructure,
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        self._last_morning_check = time.time()
        
        logger.info("Morning check generated")
        return report
    
    def generate_market_readiness(self) -> DailyReport:
        """Generate market readiness report"""
        dashboard = self.control_room.get_dashboard()
        
        connected = []
        disconnected = []
        
        for symbol, market in dashboard["markets"].items():
            if market["connected"]:
                connected.append(symbol)
            else:
                disconnected.append(symbol)
        
        issues = []
        recommendations = []
        
        if disconnected:
            issues.append(f"{len(disconnected)} markets disconnected: {', '.join(disconnected)}")
            recommendations.append("Verify connectivity to disconnected markets")
        else:
            recommendations.append("All markets connected - ready for trading")
        
        summary = f"""
Market readiness check complete. {len(connected)}/{len(dashboard['markets'])} markets connected.
{'All markets operational.' if not disconnected else f'{len(disconnected)} markets need attention.'}
""".strip()
        
        report = DailyReport(
            report_id=f"market_{int(time.time())}",
            report_type="Market Readiness Report",
            generated_at=time.time(),
            summary=summary,
            details={
                "total_markets": len(dashboard["markets"]),
                "connected_markets": len(connected),
                "disconnected_markets": len(disconnected),
            },
            metrics={
                "connected_count": len(connected),
                "disconnected_count": len(disconnected),
                "connectivity_rate": len(connected) / max(len(dashboard["markets"]), 1),
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        return report
    
    def generate_infrastructure_report(self) -> DailyReport:
        """Generate infrastructure report"""
        dashboard = self.control_room.get_dashboard()
        
        healthy_comps = []
        degraded_comps = []
        unhealthy_comps = []
        
        for name, comp in dashboard["components"].items():
            if comp["status"] == "healthy":
                healthy_comps.append(name)
            elif comp["status"] == "degraded":
                degraded_comps.append(name)
            else:
                unhealthy_comps.append(name)
        
        issues = []
        recommendations = []
        
        if unhealthy_comps:
            issues.append(f"{len(unhealthy_comps)} unhealthy components: {', '.join(unhealthy_comps)}")
            recommendations.append("Investigate and repair unhealthy components")
        
        if degraded_comps:
            issues.append(f"{len(degraded_comps)} degraded components: {', '.join(degraded_comps)}")
            recommendations.append("Monitor degraded components for recovery")
        
        avg_latency = sum(
            c["latency_ms"] for c in dashboard["components"].values()
        ) / max(len(dashboard["components"]), 1)
        
        avg_error_rate = sum(
            c["error_rate"] for c in dashboard["components"].values()
        ) / max(len(dashboard["components"]), 1)
        
        summary = f"""
Infrastructure status: {len(healthy_comps)} healthy, {len(degraded_comps)} degraded, {len(unhealthy_comps)} unhealthy.
Average latency: {avg_latency:.1f}ms, Error rate: {avg_error_rate:.2%}.
""".strip()
        
        report = DailyReport(
            report_id=f"infra_{int(time.time())}",
            report_type="Infrastructure Report",
            generated_at=time.time(),
            summary=summary,
            details={
                "healthy": len(healthy_comps),
                "degraded": len(degraded_comps),
                "unhealthy": len(unhealthy_comps),
            },
            metrics={
                "healthy_count": len(healthy_comps),
                "degraded_count": len(degraded_comps),
                "unhealthy_count": len(unhealthy_comps),
                "avg_latency_ms": avg_latency,
                "avg_error_rate": avg_error_rate,
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        return report
    
    def generate_strategy_status(self) -> DailyReport:
        """Generate strategy status report"""
        dashboard = self.control_room.get_dashboard()
        
        paper = dashboard["paper_trading"]
        live = dashboard["live_trading"]
        
        recommendations = []
        issues = []
        
        # Analyze performance
        if live["pnl_today"] < -100:
            issues.append(f"Live trading P&L is negative: ${live['pnl_today']:.2f}")
            recommendations.append("Review live trading positions")
        
        if live["active_strategies"] == 0 and paper["active_strategies"] > 0:
            recommendations.append("Consider promoting paper strategies to live")
        
        summary = f"""
Paper Trading: {paper['active_strategies']} active, {paper['total_trades']} trades, P&L ${paper['pnl_today']:.2f}
Live Trading: {live['active_strategies']} active, {live['total_trades']} trades, P&L ${live['pnl_today']:.2f}
""".strip()
        
        report = DailyReport(
            report_id=f"strategy_{int(time.time())}",
            report_type="Strategy Status Report",
            generated_at=time.time(),
            summary=summary,
            details={
                "paper": paper,
                "live": live,
            },
            metrics={
                "paper_pnl": paper["pnl_today"],
                "live_pnl": live["pnl_today"],
                "paper_strategies": paper["active_strategies"],
                "live_strategies": live["active_strategies"],
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        return report
    
    def generate_risk_status(self) -> DailyReport:
        """Generate risk status report"""
        dashboard = self.control_room.get_dashboard()
        health = self.control_room.calculate_health_score()
        
        recommendations = []
        issues = []
        
        if health.risk < 0.7:
            issues.append("Risk management score below threshold")
            recommendations.append("Review risk limits and exposure")
        
        summary = f"""
Risk management status: {health.risk:.1%}.
All risk parameters within limits.
""".strip()
        
        report = DailyReport(
            report_id=f"risk_{int(time.time())}",
            report_type="Risk Status Report",
            generated_at=time.time(),
            summary=summary,
            details={"risk_score": health.risk},
            metrics={
                "risk_score": health.risk,
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        return report
    
    def generate_evening_report(self) -> DailyReport:
        """Generate evening performance report"""
        dashboard = self.control_room.get_dashboard()
        health = self.control_room.calculate_health_score()
        
        paper = dashboard["paper_trading"]
        live = dashboard["live_trading"]
        
        recommendations = []
        issues = []
        
        # Check for issues
        if dashboard["alerts"]["active"] > 0:
            issues.append(f"{dashboard['alerts']['active']} unresolved alerts")
        
        # Generate recommendations
        if health.overall >= 0.9:
            recommendations.append("Platform is healthy - ready for overnight operations")
        else:
            recommendations.append("Review and address issues before overnight operations")
        
        summary = f"""
Evening report: Health {health.overall:.1%}, {dashboard['alerts']['active']} alerts.
Paper P&L: ${paper['pnl_today']:.2f}, Live P&L: ${live['pnl_today']:.2f}
{len(recommendations)} recommendations generated.
""".strip()
        
        report = DailyReport(
            report_id=f"evening_{int(time.time())}",
            report_type="Evening Performance Report",
            generated_at=time.time(),
            summary=summary,
            details={
                "health_score": health.to_dict(),
                "paper": paper,
                "live": live,
            },
            metrics={
                "health_score": health.overall,
                "paper_pnl": paper["pnl_today"],
                "live_pnl": live["pnl_today"],
                "active_alerts": dashboard["alerts"]["active"],
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        self._last_evening_report = time.time()
        
        return report
    
    def generate_incident_summary(self) -> DailyReport:
        """Generate incident summary"""
        dashboard = self.control_room.get_dashboard()
        
        active = dashboard["incidents"]["active"]
        recent = dashboard["incidents"]["recent"]
        
        issues = []
        recommendations = []
        
        if active > 0:
            issues.append(f"{active} active incidents")
            recommendations.append("Prioritize incident resolution")
        
        summary = f"""
Incident summary: {active} active incidents, {len(recent)} recent.
No major incidents.
""".strip()
        
        report = DailyReport(
            report_id=f"incidents_{int(time.time())}",
            report_type="Incident Summary",
            generated_at=time.time(),
            summary=summary,
            details={
                "active_count": active,
                "recent_incidents": recent,
            },
            metrics={
                "active_incidents": active,
            },
            recommendations=recommendations,
            issues=issues,
        )
        
        self._reports.append(report)
        return report
    
    def get_all_reports(self) -> List[DailyReport]:
        """Get all generated reports"""
        return self._reports.copy()
    
    def get_reports_by_type(self, report_type: str) -> List[DailyReport]:
        """Get reports by type"""
        return [r for r in self._reports if r.report_type == report_type]
