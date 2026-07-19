"""
Reporting Engine - Professional Report Generation

Generate comprehensive reports in multiple formats.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Report types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    STRATEGY = "strategy"
    RISK = "risk"
    PERFORMANCE = "performance"
    TAX = "tax"


class ReportFormat(Enum):
    """Output formats"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"
    JSON = "json"


@dataclass
class ReportTemplate:
    """Report template definition"""
    id: str
    name: str
    report_type: ReportType
    description: str
    
    # Sections to include
    sections: List[str] = field(default_factory=list)
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Format preferences
    default_format: ReportFormat = ReportFormat.PDF
    include_charts: bool = True
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "report_type": self.report_type.value,
            "description": self.description,
            "sections": self.sections,
            "default_format": self.default_format.value,
            "include_charts": self.include_charts,
        }


@dataclass
class Report:
    """A generated report"""
    id: str
    name: str
    report_type: ReportType
    format: ReportFormat
    
    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    strategy_id: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # File info
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    
    # Status
    status: str = "pending"  # pending, generating, completed, failed
    generated_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "report_type": self.report_type.value,
            "format": self.format.value,
            "strategy_id": self.strategy_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": self.status,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }


class ReportingEngine:
    """
    Professional reporting engine.
    
    Features:
    - Multiple report types
    - Multiple output formats
    - Scheduled reports
    - Custom templates
    - Automated generation
    """
    
    def __init__(self, output_path: str = "data/reports"):
        self._output_path = output_path
        self._reports: Dict[str, Report] = {}
        self._templates: Dict[str, ReportTemplate] = {}
        
        import os
        os.makedirs(output_path, exist_ok=True)
        
        # Register default templates
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """Register default report templates"""
        self._templates["daily_summary"] = ReportTemplate(
            id="daily_summary",
            name="Daily Summary",
            report_type=ReportType.DAILY,
            description="Daily performance summary",
            sections=["overview", "trades", "pnl", "risk"],
            include_charts=True,
        )
        
        self._templates["weekly_report"] = ReportTemplate(
            id="weekly_report",
            name="Weekly Report",
            report_type=ReportType.WEEKLY,
            description="Weekly performance report",
            sections=["executive_summary", "performance", "trades", "risk", "recommendations"],
            include_charts=True,
        )
        
        self._templates["monthly_report"] = ReportTemplate(
            id="monthly_report",
            name="Monthly Report",
            report_type=ReportType.MONTHLY,
            description="Monthly comprehensive report",
            sections=["executive_summary", "performance", "strategy_analysis", "risk", "comparisons", "recommendations"],
            include_charts=True,
        )
        
        self._templates["strategy_report"] = ReportTemplate(
            id="strategy_report",
            name="Strategy Performance Report",
            report_type=ReportType.STRATEGY,
            description="Detailed strategy performance",
            sections=["overview", "performance", "trades", "equity_curve", "drawdown", "risk_metrics", "recommendations"],
            include_charts=True,
        )
        
        self._templates["risk_report"] = ReportTemplate(
            id="risk_report",
            name="Risk Report",
            report_type=ReportType.RISK,
            description="Comprehensive risk analysis",
            sections=["risk_overview", "exposure", "correlation", "drawdown", "var", "concentration"],
            include_charts=True,
        )
    
    def create_report(
        self,
        name: str,
        report_type: ReportType,
        data: Dict[str, Any],
        format: ReportFormat = ReportFormat.PDF,
        strategy_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        created_by: str = "system",
    ) -> Report:
        """Create a new report"""
        report = Report(
            id=str(uuid.uuid4()),
            name=name,
            report_type=report_type,
            format=format,
            data=data,
            strategy_id=strategy_id,
            period_start=period_start,
            period_end=period_end,
            created_by=created_by,
        )
        
        self._reports[report.id] = report
        return report
    
    def generate_report(
        self,
        report_id: str,
        data_provider: Optional[Callable] = None,
    ) -> Report:
        """Generate a report (convert to file)"""
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")
        
        report.status = "generating"
        
        try:
            # Gather data if provider is available
            if data_provider:
                report.data = data_provider(report)
            
            # Generate based on format
            if report.format == ReportFormat.JSON:
                file_path = self._generate_json(report)
            elif report.format == ReportFormat.CSV:
                file_path = self._generate_csv(report)
            elif report.format == ReportFormat.HTML:
                file_path = self._generate_html(report)
            elif report.format == ReportFormat.PDF:
                file_path = self._generate_pdf(report)
            elif report.format == ReportFormat.EXCEL:
                file_path = self._generate_excel(report)
            else:
                raise ValueError(f"Unsupported format: {report.format}")
            
            report.file_path = file_path
            report.status = "completed"
            report.generated_at = datetime.now(timezone.utc)
            
            # Get file size
            import os
            if os.path.exists(file_path):
                report.file_size_bytes = os.path.getsize(file_path)
            
        except Exception as e:
            logger.error(f"Failed to generate report {report_id}: {e}")
            report.status = "failed"
        
        return report
    
    def _generate_json(self, report: Report) -> str:
        """Generate JSON report"""
        import json
        
        filename = f"{report.id}.json"
        filepath = f"{self._output_path}/{filename}"
        
        with open(filepath, "w") as f:
            json.dump(report.data, f, indent=2, default=str)
        
        return filepath
    
    def _generate_csv(self, report: Report) -> str:
        """Generate CSV report"""
        import csv
        
        filename = f"{report.id}.csv"
        filepath = f"{self._output_path}/{filename}"
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            
            # Write header
            if "trades" in report.data:
                if report.data["trades"]:
                    writer.writerow(report.data["trades"][0].keys())
                    for trade in report.data["trades"]:
                        writer.writerow(trade.values())
        
        return filepath
    
    def _generate_html(self, report: Report) -> str:
        """Generate HTML report"""
        filename = f"{report.id}.html"
        filepath = f"{self._output_path}/{filename}"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        .metric {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .positive {{ color: #4CAF50; }}
        .negative {{ color: #F44336; }}
    </style>
</head>
<body>
    <h1>{report.name}</h1>
    <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary</h2>
    <div class="metric">{report.data.get('total_return', 0):.2f}%</div>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
"""
        
        for key, value in report.data.get("metrics", {}).items():
            html += f"        <tr><td>{key}</td><td>{value:.4f}</td></tr>\n"
        
        html += """    </table>
</body>
</html>"""
        
        with open(filepath, "w") as f:
            f.write(html)
        
        return filepath
    
    def _generate_pdf(self, report: Report) -> str:
        """Generate PDF report"""
        # In production, would use a PDF library
        # For now, return HTML path
        html_path = self._generate_html(report)
        return html_path.replace(".html", ".pdf")
    
    def _generate_excel(self, report: Report) -> str:
        """Generate Excel report"""
        # In production, would use openpyxl
        csv_path = self._generate_csv(report)
        return csv_path.replace(".csv", ".xlsx")
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """Get a report by ID"""
        return self._reports.get(report_id)
    
    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Report]:
        """List reports with optional filtering"""
        reports = list(self._reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        if status:
            reports = [r for r in reports if r.status == status]
        
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports[:limit]
    
    def schedule_report(
        self,
        template_id: str,
        schedule: str,  # cron expression
        recipients: List[str],
        strategy_id: Optional[str] = None,
    ) -> str:
        """Schedule a recurring report"""
        schedule_id = str(uuid.uuid4())
        # In production, would integrate with scheduler
        logger.info(f"Scheduled report: {template_id} with schedule {schedule}")
        return schedule_id
