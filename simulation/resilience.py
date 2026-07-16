"""
Resilience Analysis
==================

Analyze and report on system resilience.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResilienceReport:
    """Comprehensive resilience report"""
    report_id: str
    generated_at: float
    test_results: List[Dict[str, Any]]
    
    # Overall assessment
    overall_score: float
    overall_grade: str
    
    # Component scores
    execution_resilience: float
    network_resilience: float
    data_resilience: float
    recovery_resilience: float
    
    # Findings
    strengths: List[str]
    weaknesses: List[str]
    risks: List[str]
    
    # Recommendations
    critical_recommendations: List[str]
    recommendations: List[str]
    
    # Deployment assessment
    deployment_ready: bool
    blockers: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "test_results": self.test_results,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "execution_resilience": self.execution_resilience,
            "network_resilience": self.network_resilience,
            "data_resilience": self.data_resilience,
            "recovery_resilience": self.recovery_resilience,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "risks": self.risks,
            "critical_recommendations": self.critical_recommendations,
            "recommendations": self.recommendations,
            "deployment_ready": self.deployment_ready,
            "blockers": self.blockers,
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = f"""# Resilience Report

**Report ID:** {self.report_id}
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.generated_at))}

## Overall Assessment

**Score:** {self.overall_score:.1f}/100
**Grade:** {self.overall_grade}

**Deployment Ready:** {'✅ Yes' if self.deployment_ready else '❌ No'}

---

## Component Scores

| Component | Score |
|-----------|-------|
| Execution Resilience | {self.execution_resilience:.1f}/100 |
| Network Resilience | {self.network_resilience:.1f}/100 |
| Data Resilience | {self.data_resilience:.1f}/100 |
| Recovery Resilience | {self.recovery_resilience:.1f}/100 |

---

## Strengths

"""
        for s in self.strengths:
            md += f"- {s}\n"
        
        md += "\n## Weaknesses\n\n"
        for w in self.weaknesses:
            md += f"- {w}\n"
        
        md += "\n## Risks\n\n"
        for r in self.risks:
            md += f"- {r}\n"
        
        if self.critical_recommendations:
            md += "\n## ⚠️ Critical Recommendations\n\n"
            for r in self.critical_recommendations:
                md += f"- {r}\n"
        
        if self.recommendations:
            md += "\n## Recommendations\n\n"
            for r in self.recommendations:
                md += f"- {r}\n"
        
        if self.blockers:
            md += "\n## 🚫 Deployment Blockers\n\n"
            for b in self.blockers:
                md += f"- {b}\n"
        
        return md


class ResilienceAnalyzer:
    """
    Analyzes test results and generates resilience reports.
    """
    
    def __init__(self):
        self._test_results: List[Dict[str, Any]] = []
        self._historical_reports: List[ResilienceReport] = []
    
    def add_test_result(self, result: Dict[str, Any]) -> None:
        """Add a test result for analysis"""
        self._test_results.append(result)
    
    def add_results(self, results: List[Dict[str, Any]]) -> None:
        """Add multiple test results"""
        self._test_results.extend(results)
    
    def generate_report(self) -> ResilienceReport:
        """Generate comprehensive resilience report"""
        if not self._test_results:
            return self._empty_report()
        
        # Calculate component scores
        exec_score = self._calculate_execution_score()
        net_score = self._calculate_network_score()
        data_score = self._calculate_data_score()
        recovery_score = self._calculate_recovery_score()
        
        # Overall score (weighted average)
        overall = (
            exec_score * 0.35 +
            net_score * 0.25 +
            data_score * 0.20 +
            recovery_score * 0.20
        )
        
        # Determine grade
        grade = self._score_to_grade(overall)
        
        # Generate findings
        strengths = self._identify_strengths()
        weaknesses = self._identify_weaknesses()
        risks = self._identify_risks()
        
        # Generate recommendations
        critical_recs = self._get_critical_recommendations()
        recommendations = self._get_recommendations()
        
        # Deployment assessment
        blockers = self._get_blockers(overall)
        deployment_ready = len(blockers) == 0 and overall >= 70
        
        report = ResilienceReport(
            report_id=f"resilience_{int(time.time())}",
            generated_at=time.time(),
            test_results=self._test_results.copy(),
            overall_score=overall,
            overall_grade=grade,
            execution_resilience=exec_score,
            network_resilience=net_score,
            data_resilience=data_score,
            recovery_resilience=recovery_score,
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            critical_recommendations=critical_recs,
            recommendations=recommendations,
            deployment_ready=deployment_ready,
            blockers=blockers,
        )
        
        self._historical_reports.append(report)
        return report
    
    def _empty_report(self) -> ResilienceReport:
        """Return empty report"""
        return ResilienceReport(
            report_id=f"resilience_{int(time.time())}",
            generated_at=time.time(),
            test_results=[],
            overall_score=0,
            overall_grade="N/A",
            execution_resilience=0,
            network_resilience=0,
            data_resilience=0,
            recovery_resilience=0,
            strengths=[],
            weaknesses=["No test results available"],
            risks=["Unable to assess without testing"],
            critical_recommendations=["Run stress tests to assess resilience"],
            recommendations=["Execute comprehensive test suite"],
            deployment_ready=False,
            blockers=["Insufficient testing data"],
        )
    
    def _calculate_execution_score(self) -> float:
        """Calculate execution resilience score"""
        scores = []
        
        for result in self._test_results:
            if "total_orders" in result and result["total_orders"] > 0:
                success_rate = result.get("successful_orders", 0) / result["total_orders"]
                latency_penalty = min(30, result.get("avg_latency_ms", 0) / 10)
                scores.append(success_rate * 70 + (30 - latency_penalty))
        
        return sum(scores) / len(scores) if scores else 0
    
    def _calculate_network_score(self) -> float:
        """Calculate network resilience score"""
        scores = []
        
        for result in self._test_results:
            failures = result.get("network_failures", 0) + result.get("websocket_drops", 0)
            total_orders = result.get("total_orders", 1)
            
            failure_rate = failures / total_orders if total_orders > 0 else 0
            score = max(0, 100 - failure_rate * 500)  # Penalize heavily for failures
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def _calculate_data_score(self) -> float:
        """Calculate data resilience score"""
        # Based on data quality metrics
        scores = []
        
        for result in self._test_results:
            # Assume good data quality if not explicitly mentioned
            score = 100.0
            
            # Check for data-related failures
            if "data_corruption" in str(result.get("recommendations", [])):
                score -= 20
            
            if "latency" in str(result.get("recommendations", [])):
                score -= 10
            
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 100
    
    def _calculate_recovery_score(self) -> float:
        """Calculate recovery resilience score"""
        scores = []
        
        for result in self._test_results:
            failures = result.get("failures_injected", 0)
            recovered = result.get("failures_recovered", 0)
            
            if failures > 0:
                recovery_rate = recovered / failures
                scores.append(recovery_rate * 100)
            else:
                scores.append(100)  # No failures = perfect recovery
        
        return sum(scores) / len(scores) if scores else 100
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _identify_strengths(self) -> List[str]:
        """Identify system strengths"""
        strengths = []
        
        # Check execution
        exec_score = self._calculate_execution_score()
        if exec_score >= 90:
            strengths.append("Excellent execution resilience with high success rate")
        elif exec_score >= 80:
            strengths.append("Good execution performance under load")
        
        # Check network
        net_score = self._calculate_network_score()
        if net_score >= 90:
            strengths.append("Robust network handling with minimal failures")
        elif net_score >= 80:
            strengths.append("Adequate network resilience")
        
        # Check recovery
        recovery_score = self._calculate_recovery_score()
        if recovery_score >= 95:
            strengths.append("Exceptional recovery capabilities")
        elif recovery_score >= 85:
            strengths.append("Good system recovery after failures")
        
        if not strengths:
            strengths.append("System shows baseline resilience")
        
        return strengths
    
    def _identify_weaknesses(self) -> List[str]:
        """Identify system weaknesses"""
        weaknesses = []
        
        exec_score = self._calculate_execution_score()
        if exec_score < 70:
            weaknesses.append("Poor execution resilience - high failure rate")
        elif exec_score < 80:
            weaknesses.append("Moderate execution resilience needs improvement")
        
        net_score = self._calculate_network_score()
        if net_score < 70:
            weaknesses.append("Network resilience issues - frequent failures")
        elif net_score < 85:
            weaknesses.append("Network handling could be improved")
        
        recovery_score = self._calculate_recovery_score()
        if recovery_score < 80:
            weaknesses.append("Recovery capabilities need enhancement")
        
        return weaknesses
    
    def _identify_risks(self) -> List[str]:
        """Identify potential risks"""
        risks = []
        
        # Check for high latency
        high_latency_count = sum(
            1 for r in self._test_results
            if r.get("p95_latency_ms", 0) > 500
        )
        if high_latency_count > 0:
            risks.append("High latency spikes detected - may cause missed opportunities")
        
        # Check for frequent failures
        failure_count = sum(
            r.get("network_failures", 0) + r.get("api_failures", 0)
            for r in self._test_results
        )
        if failure_count > 10:
            risks.append(f"Frequent failures ({failure_count}) - impact on trading performance")
        
        # Check for deployment blockers
        blockers = self._get_blockers(0)  # Pass overall score
        if len(blockers) > 2:
            risks.append("Multiple deployment blockers identified - review required")
        
        if not risks:
            risks.append("No immediate risks identified")
        
        return risks
    
    def _get_critical_recommendations(self) -> List[str]:
        """Get critical recommendations"""
        critical = []
        
        # Check for critical issues
        exec_score = self._calculate_execution_score()
        if exec_score < 60:
            critical.append("URGENT: Fix execution failures before deployment")
        
        net_score = self._calculate_network_score()
        if net_score < 50:
            critical.append("URGENT: Implement circuit breakers for network failures")
        
        # Check for fragile strategies
        fragile_count = sum(
            len(r.get("fragile_strategies", []))
            for r in self._test_results
        )
        if fragile_count > 0:
            critical.append(f"Remove or fix {fragile_count} fragile strategies before deployment")
        
        return critical
    
    def _get_recommendations(self) -> List[str]:
        """Get general recommendations"""
        recs = []
        
        # Aggregate recommendations from test results
        all_recs = []
        for result in self._test_results:
            all_recs.extend(result.get("recommendations", []))
        
        # Deduplicate and limit
        seen = set()
        for rec in all_recs:
            if rec not in seen:
                recs.append(rec)
                seen.add(rec)
        
        return recs[:10]  # Limit to 10
    
    def _get_blockers(self, overall_score: float) -> List[str]:
        """Get deployment blockers"""
        blockers = []
        
        # Critical score threshold
        if overall_score < 50:
            blockers.append("Overall resilience score below minimum threshold (50)")
        
        # Execution issues
        exec_score = self._calculate_execution_score()
        if exec_score < 60:
            blockers.append("Execution resilience below acceptable level (60)")
        
        # Network issues
        net_score = self._calculate_network_score()
        if net_score < 50:
            blockers.append("Network resilience insufficient for production")
        
        # Fragile strategies
        fragile_strats = set()
        for result in self._test_results:
            for s in result.get("fragile_strategies", []):
                fragile_strats.add(s)
        
        if fragile_strats:
            blockers.append(f"Fragile strategies detected: {', '.join(list(fragile_strats)[:3])}")
        
        return blockers
    
    def get_historical_reports(self) -> List[ResilienceReport]:
        """Get historical reports"""
        return self._historical_reports.copy()
    
    def export_report(self, report: ResilienceReport, filepath: str, format: str = "json") -> None:
        """Export report to file"""
        if format == "json":
            with open(filepath, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
        elif format == "markdown":
            with open(filepath, "w") as f:
                f.write(report.to_markdown())
        elif format == "html":
            html = f"""<!DOCTYPE html>
<html>
<head><title>Resilience Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; }}
.score {{ font-size: 48px; color: {"green" if report.overall_score >= 70 else "red"}; }}
.grade {{ font-size: 72px; color: {"green" if report.overall_score >= 70 else "red"}; }}
</style>
</head>
<body>
<h1>Resilience Report</h1>
<p>Report ID: {report.report_id}</p>
<p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.generated_at))}</p>
<h2>Overall Score: <span class="score">{report.overall_score:.1f}/100</span></h2>
<h2>Grade: <span class="grade">{report.overall_grade}</span></h2>
<h2>Deployment Ready: {"Yes" if report.deployment_ready else "No"}</h2>
</body>
</html>"""
            with open(filepath, "w") as f:
                f.write(html)
