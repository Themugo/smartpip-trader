"""
Weekly Report Generator
======================

Generates weekly research reports with recommendations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class RecommendationPriority(Enum):
    """Priority levels for recommendations"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Recommendation:
    """A research recommendation"""
    priority: RecommendationPriority
    title: str
    description: str
    hypothesis_id: Optional[str]
    justification: str
    estimated_impact: str


@dataclass
class WeeklyReport:
    """Weekly research report"""
    id: str
    week_start: datetime
    week_end: datetime
    content: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    summary: str
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "summary": self.summary,
            "recommendations_count": len(self.recommendations),
            "generated_at": self.generated_at.isoformat()
        }
    
    def to_markdown(self) -> str:
        """Convert report to markdown format"""
        lines = [
            f"# Weekly Research Report",
            f"## {self.week_start.strftime('%Y-%m-%d')} to {self.week_end.strftime('%Y-%m-%d')}",
            "",
            "## Summary",
            self.summary,
            "",
            "## Recommendations"
        ]
        
        for i, rec in enumerate(self.recommendations, 1):
            lines.append(f"\n### {i}. {rec['title']}")
            lines.append(f"**Priority:** {rec['priority']}")
            lines.append(f"\n{rec['description']}")
            lines.append(f"\n**Justification:** {rec['justification']}")
        
        return "\n".join(lines)


class WeeklyReportGenerator:
    """
    Generates weekly research reports with recommendations.
    """
    
    def __init__(self, journal: Any):
        self.journal = journal
        self.reports: Dict[str, WeeklyReport] = {}
    
    def generate(
        self,
        ideas: List[Any],
        archived: List[Any],
        week_start: Optional[datetime] = None,
        week_end: Optional[datetime] = None
    ) -> WeeklyReport:
        """
        Generate weekly research report.
        
        Args:
            ideas: Active research ideas
            archived: Recently archived ideas
            week_start: Start of week (defaults to 7 days ago)
            week_end: End of week (defaults to now)
            
        Returns:
            WeeklyReport
        """
        week_end = week_end or datetime.now()
        week_start = week_start or (week_end - timedelta(days=7))
        
        # Analyze ideas
        ideas_analysis = self._analyze_ideas(ideas)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(ideas, ideas_analysis)
        
        # Generate summary
        summary = self._generate_summary(ideas_analysis, recommendations)
        
        # Create content
        content = {
            "ideas_analysis": ideas_analysis,
            "active_count": len(ideas),
            "archived_count": len(archived),
            "by_status": self._count_by_status(ideas),
            "by_priority": self._count_by_priority(ideas)
        }
        
        report = WeeklyReport(
            id=str(uuid4()),
            week_start=week_start,
            week_end=week_end,
            content=content,
            recommendations=recommendations,
            summary=summary
        )
        
        self.reports[report.id] = report
        
        logger.info(f"Generated weekly report: {report.id}")
        
        return report
    
    def _analyze_ideas(self, ideas: List[Any]) -> Dict[str, Any]:
        """Analyze research ideas"""
        if not ideas:
            return {
                "total": 0,
                "high_priority_count": 0,
                "average_priority": 0,
                "by_type": {}
            }
        
        # Count by type
        by_type = {}
        high_priority = 0
        
        for idea in ideas:
            htype = idea.hypothesis.type.value if hasattr(idea.hypothesis.type, 'value') else "unknown"
            by_type[htype] = by_type.get(htype, 0) + 1
            
            if idea.priority > 0.7:
                high_priority += 1
        
        return {
            "total": len(ideas),
            "high_priority_count": high_priority,
            "average_priority": sum(i.priority for i in ideas) / len(ideas),
            "by_type": by_type
        }
    
    def _generate_recommendations(
        self,
        ideas: List[Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for further investigation"""
        recommendations = []
        
        # Find ideas worth investigating
        for idea in ideas:
            if idea.status in ["pending", "planned"] and idea.priority > 0.6:
                rec = {
                    "priority": self._get_priority(idea.priority),
                    "title": f"Investigate: {idea.hypothesis.description[:50]}...",
                    "description": (
                        f"Priority: {idea.priority:.2f}\n"
                        f"Novelty: {idea.novelty_score:.2f}\n"
                        f"Feasibility: {idea.feasibility_score:.2f}\n"
                        f"Potential Impact: {idea.potential_impact:.2f}"
                    ),
                    "hypothesis_id": idea.hypothesis.id if hasattr(idea.hypothesis, 'id') else None,
                    "justification": (
                        f"This hypothesis has high priority ({idea.priority:.2f}) and "
                        f"shows promising novelty ({idea.novelty_score:.2f}) and "
                        f"potential impact ({idea.potential_impact:.2f})."
                    ),
                    "estimated_impact": self._estimate_impact(idea)
                }
                recommendations.append(rec)
        
        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3
        }
        
        recommendations.sort(key=lambda x: priority_order.get(RecommendationPriority(x["priority"]), 99))
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _get_priority(self, score: float) -> str:
        """Convert score to priority"""
        if score >= 0.85:
            return RecommendationPriority.CRITICAL.value
        elif score >= 0.7:
            return RecommendationPriority.HIGH.value
        elif score >= 0.5:
            return RecommendationPriority.MEDIUM.value
        else:
            return RecommendationPriority.LOW.value
    
    def _estimate_impact(self, idea: Any) -> str:
        """Estimate potential impact"""
        impact = idea.potential_impact
        
        if impact >= 0.8:
            return "High - could significantly improve strategy performance"
        elif impact >= 0.6:
            return "Medium - could moderately improve results"
        elif impact >= 0.4:
            return "Low - incremental improvement expected"
        else:
            return "Minimal - marginal gains possible"
    
    def _generate_summary(
        self,
        analysis: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate report summary"""
        total = analysis.get("total", 0)
        high_priority = analysis.get("high_priority_count", 0)
        avg_priority = analysis.get("average_priority", 0)
        
        summary_parts = [
            f"This week we analyzed {total} research ideas.",
            f"{high_priority} ideas are flagged as high priority for investigation.",
            f"The average priority score is {avg_priority:.2f}."
        ]
        
        if recommendations:
            critical = sum(1 for r in recommendations if r["priority"] == "critical")
            high = sum(1 for r in recommendations if r["priority"] == "high")
            
            if critical > 0:
                summary_parts.append(f"{critical} critical recommendations require immediate attention.")
            if high > 0:
                summary_parts.append(f"{high} high priority recommendations should be explored.")
        
        return " ".join(summary_parts)
    
    def _count_by_status(self, ideas: List[Any]) -> Dict[str, int]:
        """Count ideas by status"""
        counts = {}
        for idea in ideas:
            counts[idea.status] = counts.get(idea.status, 0) + 1
        return counts
    
    def _count_by_priority(self, ideas: List[Any]) -> Dict[str, int]:
        """Count ideas by priority level"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for idea in ideas:
            if idea.priority >= 0.85:
                counts["critical"] += 1
            elif idea.priority >= 0.7:
                counts["high"] += 1
            elif idea.priority >= 0.5:
                counts["medium"] += 1
            else:
                counts["low"] += 1
        
        return counts
    
    def get_recent_reports(self, n: int = 4) -> List[WeeklyReport]:
        """Get n most recent reports"""
        sorted_reports = sorted(
            self.reports.values(),
            key=lambda x: x.generated_at,
            reverse=True
        )
        return sorted_reports[:n]
    
    def get_report(self, report_id: str) -> Optional[WeeklyReport]:
        """Get report by ID"""
        return self.reports.get(report_id)
    
    def compare_reports(
        self,
        report1_id: str,
        report2_id: str
    ) -> Dict[str, Any]:
        """Compare two weekly reports"""
        r1 = self.reports.get(report1_id)
        r2 = self.reports.get(report2_id)
        
        if not r1 or not r2:
            return {}
        
        return {
            "report1": {
                "id": r1.id,
                "week": r1.week_start.strftime("%Y-%m-%d"),
                "ideas_count": r1.content.get("active_count", 0),
                "recommendations_count": len(r1.recommendations)
            },
            "report2": {
                "id": r2.id,
                "week": r2.week_start.strftime("%Y-%m-%d"),
                "ideas_count": r2.content.get("active_count", 0),
                "recommendations_count": len(r2.recommendations)
            },
            "trend": self._calculate_trend(r1, r2)
        }
    
    def _calculate_trend(
        self,
        r1: WeeklyReport,
        r2: WeeklyReport
    ) -> str:
        """Calculate research trend between reports"""
        count1 = r1.content.get("active_count", 0)
        count2 = r2.content.get("active_count", 0)
        
        if count2 > count1:
            return "EXPANDING - More active research"
        elif count2 < count1:
            return "CONSOLIDATING - Research focus narrowing"
        else:
            return "STABLE - Consistent research activity"
