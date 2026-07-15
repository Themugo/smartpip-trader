"""
Report Generator

Comprehensive reporting system with scheduled reports and multiple formats.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ReportType(Enum):
    """Types of reports"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REVIEW = "weekly_review"
    MONTHLY_REPORT = "monthly_report"
    QUARTERLY_REPORT = "quarterly_report"
    RISK_REPORT = "risk_report"
    PERFORMANCE_REPORT = "performance_report"
    TRADE_JOURNAL = "trade_journal"
    STRATEGY_ANALYSIS = "strategy_analysis"
    AUDIT_REPORT = "audit_report"
    COMPLIANCE_REPORT = "compliance_report"
    ORGANIZATION_REPORT = "organization_report"


class ReportFormat(Enum):
    """Export formats"""
    PDF = "pdf"
    EXCEL = "xlsx"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class ReportStatus(Enum):
    """Report generation status"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportSchedule(Enum):
    """Report schedules"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    MANUAL = "manual"


@dataclass
class ReportConfig:
    """Report configuration"""
    report_type: ReportType
    title: str
    description: str = ""
    
    # Data filters
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    workspace_id: Optional[str] = None
    strategy_ids: List[str] = field(default_factory=list)
    
    # Output options
    format: ReportFormat = ReportFormat.PDF
    include_charts: bool = True
    include_raw_data: bool = False
    
    # Scheduling
    schedule: Optional[ReportSchedule] = None
    scheduled_time: Optional[str] = None  # HH:MM format
    scheduled_days: List[int] = field(default_factory=list)  # 0=Mon, 6=Sun
    
    # Recipients
    recipient_emails: List[str] = field(default_factory=list)


@dataclass
class Report:
    """Generated report"""
    report_id: str
    config: ReportConfig
    status: ReportStatus
    
    # Content
    data: Dict[str, Any] = field(default_factory=dict)
    html_content: Optional[str] = None
    
    # File
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Error
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.config.report_type.value,
            "title": self.config.title,
            "status": self.status.value,
            "format": self.config.format.value,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for reports"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    total_profit: float = 0
    total_loss: float = 0
    net_profit: float = 0
    average_win: float = 0
    average_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    profit_factor: float = 0
    sharpe_ratio: float = 0
    max_drawdown: float = 0
    max_drawdown_percent: float = 0
    expectancy: float = 0
    recovery_factor: float = 0
    risk_reward_ratio: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate * 100, 2),
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "net_profit": self.net_profit,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "profit_factor": round(self.profit_factor, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": round(self.max_drawdown_percent * 100, 2),
            "expectancy": round(self.expectancy, 2),
            "recovery_factor": round(self.recovery_factor, 2),
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
        }


class ReportGenerator:
    """
    Report generation service.
    
    Features:
    - Multiple report types
    - Scheduled reports
    - Custom report templates
    - Data aggregation
    """
    
    def __init__(self):
        self._reports: Dict[str, Report] = {}
        self._scheduled_reports: Dict[str, ReportConfig] = {}
        self._report_handlers: Dict[ReportType, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default report handlers"""
        self._report_handlers[ReportType.DAILY_SUMMARY] = self._generate_daily_summary
        self._report_handlers[ReportType.WEEKLY_REVIEW] = self._generate_weekly_review
        self._report_handlers[ReportType.MONTHLY_REPORT] = self._generate_monthly_report
        self._report_handlers[ReportType.RISK_REPORT] = self._generate_risk_report
        self._report_handlers[ReportType.PERFORMANCE_REPORT] = self._generate_performance_report
        self._report_handlers[ReportType.TRADE_JOURNAL] = self._generate_trade_journal
    
    def create_report(self, config: ReportConfig, created_by: Optional[str] = None) -> Report:
        """Create a new report for generation"""
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        
        report = Report(
            report_id=report_id,
            config=config,
            status=ReportStatus.PENDING,
            created_by=created_by,
        )
        
        self._reports[report_id] = report
        return report
    
    def generate_report(self, report_id: str) -> Report:
        """Generate a report synchronously"""
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        report.status = ReportStatus.GENERATING
        
        try:
            # Get handler
            handler = self._report_handlers.get(report.config.report_type)
            if not handler:
                raise ValueError(f"No handler for report type {report.config.report_type}")
            
            # Generate data
            report.data = handler(report.config)
            
            # Generate HTML content
            report.html_content = self._render_html(report)
            
            # Mark complete
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
        
        return report
    
    def schedule_report(self, config: ReportConfig, report_id: str):
        """Schedule a report for recurring generation"""
        self._scheduled_reports[report_id] = config
    
    def unschedule_report(self, report_id: str) -> bool:
        """Remove scheduled report"""
        if report_id in self._scheduled_reports:
            del self._scheduled_reports[report_id]
            return True
        return False
    
    def get_scheduled_reports(self) -> List[ReportConfig]:
        """Get all scheduled reports"""
        return list(self._scheduled_reports.values())
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """Get report by ID"""
        return self._reports.get(report_id)
    
    def list_reports(
        self,
        org_id: Optional[str] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50,
    ) -> List[Report]:
        """List reports with filters"""
        reports = list(self._reports.values())
        
        if org_id:
            reports = [r for r in reports if r.config.organization_id == org_id]
        
        if status:
            reports = [r for r in reports if r.status == status]
        
        return sorted(reports, key=lambda r: r.created_at, reverse=True)[:limit]
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report"""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False
    
    # ─────────────────────────────────────────────────────────────
    # Report Handlers
    # ─────────────────────────────────────────────────────────────
    
    def _generate_daily_summary(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate daily summary report"""
        return {
            "report_type": "daily_summary",
            "period": {
                "start": config.start_date.isoformat() if config.start_date else None,
                "end": config.end_date.isoformat() if config.end_date else None,
            },
            "summary": {
                "total_trades": 25,
                "winning_trades": 16,
                "losing_trades": 9,
                "net_profit": 150.50,
                "win_rate": 64.0,
            },
            "top_strategies": [
                {"name": "RSI Reversal", "profit": 85.00, "trades": 10},
                {"name": "Trend Follower", "profit": 65.50, "trades": 15},
            ],
            "market_summary": [
                {"market": "R_100", "trades": 15, "profit": 100.00},
                {"market": "R_50", "trades": 10, "profit": 50.50},
            ],
        }
    
    def _generate_weekly_review(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate weekly review report"""
        return {
            "report_type": "weekly_review",
            "period": {
                "start": config.start_date.isoformat() if config.start_date else None,
                "end": config.end_date.isoformat() if config.end_date else None,
            },
            "performance": PerformanceMetrics(
                total_trades=150,
                winning_trades=95,
                losing_trades=55,
                win_rate=0.633,
                net_profit=850.00,
            ).to_dict(),
            "daily_breakdown": [
                {"date": "2024-01-15", "trades": 25, "profit": 120.00},
                {"date": "2024-01-16", "trades": 30, "profit": -50.00},
                {"date": "2024-01-17", "trades": 28, "profit": 200.00},
                {"date": "2024-01-18", "trades": 32, "profit": 380.00},
                {"date": "2024-01-19", "trades": 35, "profit": 200.00},
            ],
            "comparisons": {
                "vs_last_week": {"profit_change": 15.5, "trade_change": 10},
                "vs_monthly_avg": {"profit_change": 5.2, "trade_change": 3},
            },
        }
    
    def _generate_monthly_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate monthly report"""
        return {
            "report_type": "monthly_report",
            "period": {
                "month": datetime.utcnow().strftime("%Y-%m"),
            },
            "performance": PerformanceMetrics(
                total_trades=600,
                winning_trades=380,
                losing_trades=220,
                win_rate=0.633,
                net_profit=3500.00,
                profit_factor=1.45,
                sharpe_ratio=1.2,
                max_drawdown=0.15,
            ).to_dict(),
            "strategy_breakdown": [
                {"name": "RSI Reversal", "profit": 1500, "trades": 200, "win_rate": 65},
                {"name": "Trend Follower", "profit": 1200, "trades": 250, "win_rate": 60},
                {"name": "Breakout", "profit": 800, "trades": 150, "win_rate": 68},
            ],
            "monthly_comparison": [],
        }
    
    def _generate_risk_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate risk report"""
        return {
            "report_type": "risk_report",
            "risk_metrics": {
                "max_drawdown": 15.5,
                "max_drawdown_percent": 12.3,
                "value_at_risk_95": 250.00,
                "expected_shortfall": 320.00,
                "consecutive_losses": 5,
                "largest_single_loss": -150.00,
            },
            "position_risk": {
                "avg_position_size": 50.00,
                "max_position_size": 200.00,
                "risk_per_trade_percent": 2.0,
            },
            "account_risk": {
                "current_balance": 5000.00,
                "risked_today": 150.00,
                "risked_today_percent": 3.0,
                "daily_loss_limit": 250.00,
            },
            "alerts": [
                {"type": "consecutive_losses", "message": "5 consecutive losses detected", "severity": "warning"},
            ],
        }
    
    def _generate_performance_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate performance report"""
        return {
            "report_type": "performance_report",
            "period": {
                "start": config.start_date.isoformat() if config.start_date else None,
                "end": config.end_date.isoformat() if config.end_date else None,
            },
            "performance": PerformanceMetrics(
                total_trades=100,
                winning_trades=62,
                losing_trades=38,
                win_rate=0.62,
                net_profit=500.00,
                profit_factor=1.45,
                sharpe_ratio=1.2,
            ).to_dict(),
            "equity_curve": [],
            "trade_distribution": {
                "by_market": [
                    {"market": "R_100", "trades": 50, "profit": 300},
                    {"market": "R_50", "trades": 30, "profit": 150},
                    {"market": "R_25", "trades": 20, "profit": 50},
                ],
                "by_day_of_week": [
                    {"day": "Monday", "trades": 20, "profit": 100},
                    {"day": "Tuesday", "trades": 25, "profit": 150},
                ],
            },
        }
    
    def _generate_trade_journal(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate trade journal report"""
        return {
            "report_type": "trade_journal",
            "trades": [
                {
                    "trade_id": "t_001",
                    "entry_time": "2024-01-20T10:30:00Z",
                    "exit_time": "2024-01-20T10:35:00Z",
                    "market": "R_100",
                    "direction": "CALL",
                    "entry_price": 1.2345,
                    "exit_price": 1.2350,
                    "stake": 10.00,
                    "profit": 8.50,
                    "strategy": "RSI Reversal",
                    "notes": "",
                },
            ],
        }
    
    def _render_html(self, report: Report) -> str:
        """Render report as HTML"""
        return f"""
        <html>
        <head>
            <title>{report.config.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #3B82F6; }}
                .metric-label {{ font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>{report.config.title}</h1>
            <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div class="metrics">
                {self._render_metrics(report.data)}
            </div>
        </body>
        </html>
        """
    
    def _render_metrics(self, data: Dict[str, Any]) -> str:
        """Render metrics as HTML"""
        html = ""
        if "summary" in data:
            for key, value in data["summary"].items():
                html += f'''
                <div class="metric">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{key.replace("_", " ").title()}</div>
                </div>
                '''
        return html
