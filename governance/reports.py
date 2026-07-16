"""
Governance Reports
================

Automatic governance report generation.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class GovernanceReport:
    """Comprehensive governance report"""
    report_id: str
    generated_at: float
    period_start: float
    period_end: float
    
    # Strategy metrics
    total_strategies: int
    strategies_by_stage: Dict[str, int]
    strategies_production_ready: int
    
    # Deployment metrics
    total_deployments: int
    successful_deployments: int
    failed_deployments: int
    rollbacks: int
    
    # Approval metrics
    approval_requests: int
    approvals_granted: int
    approvals_denied: int
    pending_approvals: int
    avg_approval_time_hours: float
    
    # Compliance metrics
    compliance_rate: float
    evidence_count: int
    verified_evidence: int
    
    # Audit metrics
    audit_entries: int
    critical_actions: int
    
    # Performance
    strategies_performance: Dict[str, Dict[str, float]]
    
    # Findings
    issues: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "period": {
                "start": self.period_start,
                "end": self.period_end,
            },
            "strategies": {
                "total": self.total_strategies,
                "by_stage": self.strategies_by_stage,
                "production_ready": self.strategies_production_ready,
            },
            "deployments": {
                "total": self.total_deployments,
                "successful": self.successful_deployments,
                "failed": self.failed_deployments,
                "rollbacks": self.rollbacks,
            },
            "approvals": {
                "total": self.approval_requests,
                "granted": self.approvals_granted,
                "denied": self.approvals_denied,
                "pending": self.pending_approvals,
                "avg_time_hours": self.avg_approval_time_hours,
            },
            "compliance": {
                "rate": self.compliance_rate,
                "evidence_count": self.evidence_count,
                "verified_evidence": self.verified_evidence,
            },
            "audit": {
                "entries": self.audit_entries,
                "critical_actions": self.critical_actions,
            },
            "issues": self.issues,
            "recommendations": self.recommendations,
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        period_str = f"{datetime.fromtimestamp(self.period_start).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(self.period_end).strftime('%Y-%m-%d')}"
        
        md = f"""# Governance Report

**Report ID:** {self.report_id}
**Generated:** {datetime.fromtimestamp(self.generated_at).strftime('%Y-%m-%d %H:%M:%S')}
**Period:** {period_str}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Strategies | {self.total_strategies} |
| Production Ready | {self.strategies_production_ready} |
| Compliance Rate | {self.compliance_rate:.1%} |
| Approval Rate | {self.approvals_granted / self.approval_requests if self.approval_requests > 0 else 0:.1%} |

---

## Strategy Overview

### By Stage

| Stage | Count |
|-------|-------|
"""
        
        for stage, count in self.strategies_by_stage.items():
            md += f"| {stage.replace('_', ' ').title()} | {count} |\n"
        
        md += f"""

### Performance Metrics

| Strategy | Win Rate | Sharpe Ratio | Max Drawdown |
|----------|----------|--------------|--------------|
"""
        
        for strategy, metrics in self.strategies_performance.items():
            wr = metrics.get("win_rate", 0)
            sharpe = metrics.get("sharpe_ratio", 0)
            dd = metrics.get("max_drawdown", 0)
            md += f"| {strategy[:30]} | {wr:.1%} | {sharpe:.2f} | {dd:.1%} |\n"
        
        md += f"""

---

## Deployment History

| Metric | Value |
|--------|-------|
| Total Deployments | {self.total_deployments} |
| Successful | {self.successful_deployments} |
| Failed | {self.failed_deployments} |
| Rollbacks | {self.rollbacks} |

**Success Rate:** {self.successful_deployments / self.total_deployments if self.total_deployments > 0 else 0:.1%}

---

## Approval Workflow

| Metric | Value |
|--------|-------|
| Requests | {self.approval_requests} |
| Approved | {self.approvals_granted} |
| Denied | {self.approvals_denied} |
| Pending | {self.pending_approvals} |
| Avg Time | {self.avg_approval_time_hours:.1f} hours |

**Approval Rate:** {self.approvals_granted / self.approval_requests if self.approval_requests > 0 else 0:.1%}

---

## Compliance

| Metric | Value |
|--------|-------|
| Compliance Rate | {self.compliance_rate:.1%} |
| Total Evidence | {self.evidence_count} |
| Verified | {self.verified_evidence} |

---

## Audit & Security

| Metric | Value |
|--------|-------|
| Audit Entries | {self.audit_entries} |
| Critical Actions | {self.critical_actions} |

"""
        
        if self.issues:
            md += "\n## Issues\n\n"
            for issue in self.issues:
                md += f"- ⚠️ {issue}\n"
        
        if self.recommendations:
            md += "\n## Recommendations\n\n"
            for rec in self.recommendations:
                md += f"- 💡 {rec}\n"
        
        return md


class ReportGenerator:
    """
    Generates automatic governance reports.
    """
    
    def __init__(self, workflow_manager=None, approval_manager=None, compliance_tracker=None, audit_logger=None):
        self.workflow_manager = workflow_manager
        self.approval_manager = approval_manager
        self.compliance_tracker = compliance_tracker
        self.audit_logger = audit_logger
    
    def generate_report(
        self,
        period_days: int = 30
    ) -> GovernanceReport:
        """Generate governance report"""
        period_end = time.time()
        period_start = period_end - (period_days * 24 * 3600)
        
        # Strategy metrics
        strategies = []
        if self.workflow_manager:
            strategies = self.workflow_manager.get_all_strategies()
        
        strategies_by_stage: Dict[str, int] = {}
        production_ready = 0
        
        for s in strategies:
            stage = s.current_stage.value
            strategies_by_stage[stage] = strategies_by_stage.get(stage, 0) + 1
            if s.is_production_ready():
                production_ready += 1
        
        # Approval metrics
        approval_requests = 0
        approvals_granted = 0
        approvals_denied = 0
        pending_approvals = 0
        avg_approval_time = 0
        
        if self.approval_manager:
            pending_approvals = len(self.approval_manager.get_pending_requests())
            report = self.approval_manager.generate_approval_report(since=period_start)
            approval_requests = report["total_requests"]
            approvals_granted = report["approved"]
            approvals_denied = report["rejected"]
            avg_approval_time = report["avg_approval_time_hours"]
        
        # Compliance metrics
        compliance_rate = 0.0
        evidence_count = 0
        verified_evidence = 0
        
        if self.compliance_tracker:
            compliance_report = self.compliance_tracker.generate_report(
                period_start=period_start,
                period_end=period_end
            )
            compliance_rate = compliance_report.compliance_rate
            evidence_count = compliance_report.total_evidence
            verified_evidence = compliance_report.verified_evidence
        
        # Audit metrics
        audit_entries = 0
        critical_actions = 0
        
        if self.audit_logger:
            audit_report = self.audit_logger.generate_report(
                since=period_start,
                until=period_end
            )
            audit_entries = audit_report["total_entries"]
            critical_actions = audit_report["by_action"].get("deployment.rollback", 0)
        
        # Performance metrics
        strategies_performance: Dict[str, Dict[str, float]] = {}
        for s in strategies:
            if s.total_trades > 0:
                strategies_performance[s.name] = {
                    "win_rate": s.win_rate,
                    "sharpe_ratio": s.sharpe_ratio,
                    "max_drawdown": s.max_drawdown,
                }
        
        # Issues and recommendations
        issues = []
        recommendations = []
        
        if compliance_rate < 0.8:
            issues.append(f"Compliance rate below threshold: {compliance_rate:.1%}")
            recommendations.append("Review and complete compliance documentation")
        
        if approvals_denied > approvals_granted * 0.2:
            issues.append("High rejection rate on approval requests")
            recommendations.append("Review approval criteria and improve submission quality")
        
        if critical_actions > 0:
            issues.append(f"Multiple rollbacks occurred: {critical_actions}")
            recommendations.append("Review deployment procedures and testing requirements")
        
        if not recommendations:
            recommendations.append("Continue monitoring all governance metrics")
        
        return GovernanceReport(
            report_id=f"gov_report_{int(time.time())}",
            generated_at=time.time(),
            period_start=period_start,
            period_end=period_end,
            total_strategies=len(strategies),
            strategies_by_stage=strategies_by_stage,
            strategies_production_ready=production_ready,
            total_deployments=len(strategies),  # Simplified
            successful_deployments=len(strategies) - critical_actions,
            failed_deployments=0,
            rollbacks=critical_actions,
            approval_requests=approval_requests,
            approvals_granted=approvals_granted,
            approvals_denied=approvals_denied,
            pending_approvals=pending_approvals,
            avg_approval_time_hours=avg_approval_time,
            compliance_rate=compliance_rate,
            evidence_count=evidence_count,
            verified_evidence=verified_evidence,
            audit_entries=audit_entries,
            critical_actions=critical_actions,
            strategies_performance=strategies_performance,
            issues=issues,
            recommendations=recommendations,
        )
    
    def export_report(
        self,
        report: GovernanceReport,
        filepath: str,
        format: str = "json"
    ) -> None:
        """Export report to file"""
        if format == "json":
            with open(filepath, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
        elif format == "markdown":
            with open(filepath, "w") as f:
                f.write(report.to_markdown())
        elif format == "html":
            html = self._to_html(report)
            with open(filepath, "w") as f:
                f.write(html)
    
    def _to_html(self, report: GovernanceReport) -> str:
        """Convert report to HTML"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Governance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 20px; background: #f5f5f5; border-radius: 8px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #2196F3; color: white; }}
        .issue {{ color: #f44336; }}
        .recommendation {{ color: #4CAF50; }}
    </style>
</head>
<body>
    <h1>Governance Report</h1>
    <p>Period: {datetime.fromtimestamp(report.period_start).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(report.period_end).strftime('%Y-%m-%d')}</p>
    
    <h2>Summary</h2>
    <div class="metric">
        <div class="metric-value">{report.total_strategies}</div>
        <div class="metric-label">Total Strategies</div>
    </div>
    <div class="metric">
        <div class="metric-value">{report.compliance_rate:.0%}</div>
        <div class="metric-label">Compliance Rate</div>
    </div>
    <div class="metric">
        <div class="metric-value">{report.approvals_granted}</div>
        <div class="metric-label">Approvals Granted</div>
    </div>
    
    <h2>Issues</h2>
    <ul>
        {"".join(f'<li class="issue">{i}</li>' for i in report.issues)}
    </ul>
    
    <h2>Recommendations</h2>
    <ul>
        {"".join(f'<li class="recommendation">{r}</li>' for r in report.recommendations)}
    </ul>
</body>
</html>"""
