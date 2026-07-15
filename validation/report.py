"""
Deployment Report Generator
=========================

Generates deployment reports documenting validation results.
"""

import logging
import os
import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Report formats"""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class DeploymentReport:
    """
    Deployment report documenting validation results.
    """
    report_id: str
    timestamp: datetime
    strategy_id: str
    version: str
    environment: str
    
    # Summary
    overall_status: str
    weighted_score: float
    validation_duration: float
    
    # Validation results by stage
    stage_results: Dict[str, Any]
    
    # Acceptance criteria results
    acceptance_results: Dict[str, Any]
    
    # Comparison with previous version
    comparison: Dict[str, Any]
    
    # Recommendations
    recommendations: List[str]
    
    # Approval info
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Metadata
    generated_by: str = "validation_system"
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "strategy_id": self.strategy_id,
            "version": self.version,
            "environment": self.environment,
            "overall_status": self.overall_status,
            "weighted_score": self.weighted_score,
            "validation_duration": self.validation_duration,
            "stage_results": self.stage_results,
            "acceptance_results": self.acceptance_results,
            "comparison": self.comparison,
            "recommendations": self.recommendations,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "generated_by": self.generated_by,
            "notes": self.notes
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format"""
        lines = [
            f"# Deployment Report",
            f"## Strategy: {self.strategy_id}",
            f"### Version: {self.version}",
            f"",
            f"**Status:** {self.overall_status.upper()}",
            f"**Weighted Score:** {self.weighted_score:.2%}",
            f"**Environment:** {self.environment}",
            f"**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"---",
            f"",
            f"## Validation Results",
        ]
        
        for stage, result in self.stage_results.items():
            status_icon = "✅" if result.get("status") == "passed" else "❌"
            lines.append(f"\n### {status_icon} {stage.replace('_', ' ').title()}")
            lines.append(f"**Status:** {result.get('status', 'unknown')}")
            
            if "metrics" in result:
                lines.append(f"\n**Metrics:**")
                for key, value in result["metrics"].items():
                    if isinstance(value, float):
                        lines.append(f"- {key}: {value:.4f}")
                    else:
                        lines.append(f"- {key}: {value}")
            
            if result.get("errors"):
                lines.append(f"\n**Errors:**")
                for err in result["errors"]:
                    lines.append(f"- {err}")
        
        lines.append(f"\n---\n## Acceptance Criteria")
        
        ar = self.acceptance_results
        lines.append(f"\n**Overall:** {'PASSED ✅' if ar.get('overall_passed') else 'FAILED ❌'}")
        lines.append(f"\n**Weighted Score:** {ar.get('weighted_score', 0):.2%}")
        
        if ar.get("results"):
            lines.append(f"\n**Criteria:**")
            for name, passed in ar["results"].items():
                icon = "✅" if passed else "❌"
                lines.append(f"- {icon} {name}: {'passed' if passed else 'failed'}")
        
        if self.comparison:
            lines.append(f"\n---\n## Comparison with Previous Version")
            for key, value in self.comparison.items():
                if isinstance(value, (int, float)):
                    lines.append(f"- {key}: {value:.4f}")
                else:
                    lines.append(f"- {key}: {value}")
        
        if self.recommendations:
            lines.append(f"\n---\n## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
        
        if self.approved_by:
            lines.append(f"\n---\n## Approval")
            lines.append(f"**Approved by:** {self.approved_by}")
            if self.approved_at:
                lines.append(f"**Date:** {self.approved_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)


class ReportGenerator:
    """
    Generates deployment reports documenting validation results.
    """
    
    def __init__(
        self,
        db_path: str = "data/validation/reports.db",
        output_dir: str = "data/validation/reports"
    ):
        self.db_path = db_path
        self.output_dir = output_dir
        self.reports: Dict[str, DeploymentReport] = {}
        
        os.makedirs(output_dir, exist_ok=True)
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Initialize database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployment_reports (
                report_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                strategy_id TEXT,
                version TEXT,
                environment TEXT,
                overall_status TEXT,
                weighted_score REAL,
                validation_duration REAL,
                report_json TEXT,
                approval_info TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def generate_report(
        self,
        strategy_id: str,
        version: str,
        environment: str,
        validation_results: List[Any],
        acceptance_result: Any,
        previous_metrics: Optional[Dict[str, float]] = None,
        current_metrics: Optional[Dict[str, float]] = None
    ) -> DeploymentReport:
        """
        Generate deployment report.
        
        Args:
            strategy_id: Strategy identifier
            version: Strategy version
            environment: Target environment
            validation_results: List of validation stage results
            acceptance_result: Acceptance evaluation result
            previous_metrics: Previous version metrics for comparison
            current_metrics: Current version metrics
            
        Returns:
            DeploymentReport
        """
        report_id = str(uuid4())
        
        # Calculate overall status
        failed_stages = sum(
            1 for r in validation_results
            if hasattr(r, 'status') and r.status.value == "failed"
        )
        
        overall_status = "APPROVED" if (
            failed_stages == 0 and
            acceptance_result.overall_passed
        ) else "REJECTED"
        
        # Build stage results
        stage_results = {}
        total_duration = 0.0
        
        for result in validation_results:
            stage_name = result.stage.value
            stage_results[stage_name] = {
                "status": result.status.value,
                "duration": result.duration_seconds,
                "metrics": result.metrics,
                "errors": result.errors,
                "warnings": result.warnings
            }
            total_duration += result.duration_seconds
        
        # Build comparison
        comparison = {}
        if previous_metrics and current_metrics:
            for key in current_metrics:
                prev = previous_metrics.get(key)
                curr = current_metrics.get(key)
                if prev is not None and curr is not None:
                    comparison[key] = {
                        "previous": prev,
                        "current": curr,
                        "change": curr - prev,
                        "change_pct": (curr - prev) / abs(prev) if prev != 0 else 0
                    }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            validation_results,
            acceptance_result,
            comparison
        )
        
        report = DeploymentReport(
            report_id=report_id,
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            version=version,
            environment=environment,
            overall_status=overall_status,
            weighted_score=acceptance_result.weighted_score,
            validation_duration=total_duration,
            stage_results=stage_results,
            acceptance_results=acceptance_result.to_dict(),
            comparison=comparison,
            recommendations=recommendations
        )
        
        self.reports[report_id] = report
        self._store_report(report)
        
        logger.info(f"Generated report: {report_id}")
        
        return report
    
    def _generate_recommendations(
        self,
        validation_results: List[Any],
        acceptance_result: Any,
        comparison: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        # Check acceptance criteria failures
        for failed in acceptance_result.failed_criteria:
            recommendations.append(
                f"Address failed criterion: {failed}"
            )
        
        # Check validation failures
        for result in validation_results:
            if result.status.value == "failed":
                stage_name = result.stage.value.replace('_', ' ').title()
                recommendations.append(
                    f"Review failed {stage_name} stage"
                )
        
        # Check warnings
        for result in validation_results:
            if result.status.value == "warning":
                stage_name = result.stage.value.replace('_', ' ').title()
                recommendations.append(
                    f"Investigate warnings in {stage_name}"
                )
        
        # Check improvements
        improvements = []
        regressions = []
        for key, comp in comparison.items():
            if comp.get("change", 0) > 0:
                improvements.append(key)
            else:
                regressions.append(key)
        
        if improvements:
            recommendations.append(
                f"Improvements detected in: {', '.join(improvements)}"
            )
        if regressions:
            recommendations.append(
                f"Regressions detected in: {', '.join(regressions)}"
            )
        
        return recommendations
    
    def _store_report(self, report: DeploymentReport) -> None:
        """Store report in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO deployment_reports (
                report_id, timestamp, strategy_id, version, environment,
                overall_status, weighted_score, validation_duration,
                report_json, approval_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.report_id,
            report.timestamp.isoformat(),
            report.strategy_id,
            report.version,
            report.environment,
            report.overall_status,
            report.weighted_score,
            report.validation_duration,
            json.dumps(report.to_dict()),
            json.dumps({
                "approved_by": report.approved_by,
                "approved_at": report.approved_at.isoformat() if report.approved_at else None
            })
        ))
        
        conn.commit()
        conn.close()
    
    def export_report(
        self,
        report_id: str,
        format: ReportFormat = ReportFormat.MARKDOWN
    ) -> str:
        """
        Export report to specified format.
        
        Args:
            report_id: Report identifier
            format: Output format
            
        Returns:
            Path to exported file
        """
        report = self.reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        if format == ReportFormat.JSON:
            path = os.path.join(self.output_dir, f"{report_id}.json")
            with open(path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)
        
        elif format == ReportFormat.MARKDOWN:
            path = os.path.join(self.output_dir, f"{report_id}.md")
            with open(path, 'w') as f:
                f.write(report.to_markdown())
        
        else:
            # For PDF/HTML, just save markdown and note conversion needed
            path = os.path.join(self.output_dir, f"{report_id}.md")
            with open(path, 'w') as f:
                f.write(report.to_markdown())
            logger.info(f"Export as {format.value} requires additional processing")
        
        logger.info(f"Exported report to: {path}")
        return path
    
    def get_reports(
        self,
        strategy_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[DeploymentReport]:
        """Get reports with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT report_json FROM deployment_reports WHERE 1=1"
        params = []
        
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)
        
        if status:
            query += " AND overall_status = ?"
            params.append(status)
        
        if since:
            query += " AND timestamp > ?"
            params.append(since.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        reports = []
        for row in rows:
            data = json.loads(row[0])
            # Create report object from dict (simplified)
            report = DeploymentReport(
                report_id=data["report_id"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                strategy_id=data["strategy_id"],
                version=data["version"],
                environment=data["environment"],
                overall_status=data["overall_status"],
                weighted_score=data["weighted_score"],
                validation_duration=data["validation_duration"],
                stage_results=data["stage_results"],
                acceptance_results=data["acceptance_results"],
                comparison=data["comparison"],
                recommendations=data["recommendations"],
                approved_by=data.get("approved_by"),
                approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None
            )
            reports.append(report)
            self.reports[report.report_id] = report
        
        return reports
    
    def get_latest_report(
        self,
        strategy_id: str
    ) -> Optional[DeploymentReport]:
        """Get latest report for a strategy"""
        reports = self.get_reports(strategy_id=strategy_id, limit=1)
        return reports[0] if reports else None
    
    def get_report_statistics(self) -> Dict[str, Any]:
        """Get report statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT overall_status, COUNT(*) as count
            FROM deployment_reports
            GROUP BY overall_status
        """)
        by_status = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) FROM deployment_reports")
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_reports": total,
            "by_status": by_status
        }
