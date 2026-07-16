"""
Compliance Tracking
=================

Compliance tracking and evidence management.
"""

import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Compliance evidence"""
    evidence_id: str
    evidence_type: str  # "document", "test_result", "metric", "signature", "screenshot"
    requirement: str
    title: str
    description: str
    content: Dict[str, Any]  # Can be file reference, metrics, etc.
    hash: str  # Content hash for integrity
    created_at: float
    created_by: str
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[float] = None
    
    def calculate_hash(self) -> str:
        """Calculate content hash"""
        content = json.dumps(self.content, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify(self, verified_by: str) -> bool:
        """Verify evidence"""
        current_hash = self.calculate_hash()
        if current_hash == self.hash:
            self.verified = True
            self.verified_by = verified_by
            self.verified_at = time.time()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "requirement": self.requirement,
            "title": self.title,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "verified": self.verified,
        }


@dataclass
class ComplianceReport:
    """Compliance report"""
    report_id: str
    generated_at: float
    period_start: float
    period_end: float
    
    # Summary
    total_strategies: int
    strategies_compliant: int
    strategies_non_compliant: int
    compliance_rate: float
    
    # Evidence
    total_evidence: int
    verified_evidence: int
    pending_verification: int
    evidence_verification_rate: float
    
    # Non-compliance
    non_compliant_items: List[Dict[str, Any]]
    compliance_gaps: List[str]
    
    # Recommendations
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "period": {
                "start": self.period_start,
                "end": self.period_end,
            },
            "summary": {
                "total_strategies": self.total_strategies,
                "strategies_compliant": self.strategies_compliant,
                "compliance_rate": self.compliance_rate,
            },
            "evidence": {
                "total": self.total_evidence,
                "verified": self.verified_evidence,
                "pending": self.pending_verification,
                "verification_rate": self.evidence_verification_rate,
            },
            "non_compliant_items": self.non_compliant_items,
            "compliance_gaps": self.compliance_gaps,
            "recommendations": self.recommendations,
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = f"""# Compliance Report

**Report ID:** {self.report_id}
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.generated_at))}
**Period:** {time.strftime('%Y-%m-%d', time.localtime(self.period_start))} - {time.strftime('%Y-%m-%d', time.localtime(self.period_end))}

## Summary

| Metric | Value |
|--------|-------|
| Total Strategies | {self.total_strategies} |
| Compliant | {self.strategies_compliant} |
| Non-Compliant | {self.strategies_non_compliant} |
| Compliance Rate | {self.compliance_rate:.1%} |

## Evidence

| Metric | Value |
|--------|-------|
| Total Evidence | {self.total_evidence} |
| Verified | {self.verified_evidence} |
| Pending | {self.pending_verification} |
| Verification Rate | {self.evidence_verification_rate:.1%} |

"""
        
        if self.non_compliant_items:
            md += "\n## Non-Compliant Items\n\n"
            for item in self.non_compliant_items:
                md += f"- **{item['strategy']}**: {item['issue']}\n"
        
        if self.compliance_gaps:
            md += "\n## Compliance Gaps\n\n"
            for gap in self.compliance_gaps:
                md += f"- {gap}\n"
        
        if self.recommendations:
            md += "\n## Recommendations\n\n"
            for rec in self.recommendations:
                md += f"- {rec}\n"
        
        return md


class ComplianceTracker:
    """
    Tracks compliance evidence and generates reports.
    """
    
    def __init__(self):
        self._evidence: Dict[str, List[Evidence]] = {}  # strategy_id -> evidence list
        self._requirements: Dict[str, Dict[str, Any]] = {}  # strategy_id -> requirements
    
    def add_evidence(
        self,
        strategy_id: str,
        evidence_type: str,
        requirement: str,
        title: str,
        description: str,
        content: Dict[str, Any],
        created_by: str
    ) -> Evidence:
        """Add compliance evidence"""
        evidence = Evidence(
            evidence_id=self._generate_id(),
            evidence_type=evidence_type,
            requirement=requirement,
            title=title,
            description=description,
            content=content,
            hash="",  # Will be calculated
            created_at=time.time(),
            created_by=created_by,
        )
        evidence.hash = evidence.calculate_hash()
        
        if strategy_id not in self._evidence:
            self._evidence[strategy_id] = []
        self._evidence[strategy_id].append(evidence)
        
        logger.info(f"Added evidence {evidence.evidence_id} for strategy {strategy_id}")
        return evidence
    
    def verify_evidence(
        self,
        strategy_id: str,
        evidence_id: str,
        verified_by: str
    ) -> bool:
        """Verify evidence"""
        evidence_list = self._evidence.get(strategy_id, [])
        for evidence in evidence_list:
            if evidence.evidence_id == evidence_id:
                return evidence.verify(verified_by)
        return False
    
    def get_evidence(
        self,
        strategy_id: str,
        requirement: Optional[str] = None,
        evidence_type: Optional[str] = None,
        verified_only: bool = False
    ) -> List[Evidence]:
        """Get evidence for a strategy"""
        evidence_list = self._evidence.get(strategy_id, [])
        
        results = evidence_list
        if requirement:
            results = [e for e in results if e.requirement == requirement]
        if evidence_type:
            results = [e for e in results if e.evidence_type == evidence_type]
        if verified_only:
            results = [e for e in results if e.verified]
        
        return results
    
    def get_all_evidence(self) -> Dict[str, List[Evidence]]:
        """Get all evidence"""
        return self._evidence.copy()
    
    def set_requirements(
        self,
        strategy_id: str,
        requirements: Dict[str, Any]
    ) -> None:
        """Set compliance requirements for a strategy"""
        self._requirements[strategy_id] = requirements
    
    def check_compliance(
        self,
        strategy_id: str
    ) -> Dict[str, Any]:
        """Check compliance status for a strategy"""
        requirements = self._requirements.get(strategy_id, {})
        evidence_list = self._evidence.get(strategy_id, [])
        
        required_types = requirements.get("required_evidence", [])
        verified_evidence = [e for e in evidence_list if e.verified]
        
        missing = []
        for req in required_types:
            req_type = req.get("type")
            req_name = req.get("name")
            has_evidence = any(
                e.evidence_type == req_type and e.requirement == req_name
                for e in verified_evidence
            )
            if not has_evidence:
                missing.append(f"{req_type}: {req_name}")
        
        return {
            "strategy_id": strategy_id,
            "compliant": len(missing) == 0,
            "total_evidence": len(evidence_list),
            "verified_evidence": len(verified_evidence),
            "missing_evidence": missing,
        }
    
    def generate_report(
        self,
        period_start: Optional[float] = None,
        period_end: Optional[float] = None
    ) -> ComplianceReport:
        """Generate compliance report"""
        if not period_end:
            period_end = time.time()
        if not period_start:
            period_start = period_end - (30 * 24 * 3600)  # Last 30 days
        
        all_evidence = []
        for evidence_list in self._evidence.values():
            for e in evidence_list:
                if period_start <= e.created_at <= period_end:
                    all_evidence.append(e)
        
        verified = [e for e in all_evidence if e.verified]
        
        # Calculate compliance by strategy
        strategies = set(self._evidence.keys())
        compliant = 0
        non_compliant_items = []
        
        for strategy_id in strategies:
            compliance = self.check_compliance(strategy_id)
            if compliance["compliant"]:
                compliant += 1
            else:
                non_compliant_items.append({
                    "strategy": strategy_id,
                    "issue": ", ".join(compliance["missing_evidence"]),
                })
        
        # Identify compliance gaps
        evidence_types = set(e.evidence_type for e in all_evidence)
        compliance_gaps = []
        if "test_result" not in evidence_types:
            compliance_gaps.append("Missing test result evidence")
        if "document" not in evidence_types:
            compliance_gaps.append("Missing documentation evidence")
        if "signature" not in evidence_types:
            compliance_gaps.append("Missing signature evidence")
        
        # Generate recommendations
        recommendations = []
        compliance_rate = compliant / len(strategies) if strategies else 0
        if compliance_rate < 0.8:
            recommendations.append("Improve compliance rate below 80%")
        if len(verified) / len(all_evidence) < 0.9 if all_evidence else True:
            recommendations.append("Increase evidence verification rate")
        if compliance_gaps:
            recommendations.append("Address missing evidence types")
        
        return ComplianceReport(
            report_id=self._generate_id(),
            generated_at=time.time(),
            period_start=period_start,
            period_end=period_end,
            total_strategies=len(strategies),
            strategies_compliant=compliant,
            strategies_non_compliant=len(strategies) - compliant,
            compliance_rate=compliance_rate,
            total_evidence=len(all_evidence),
            verified_evidence=len(verified),
            pending_verification=len(all_evidence) - len(verified),
            evidence_verification_rate=len(verified) / len(all_evidence) if all_evidence else 0,
            non_compliant_items=non_compliant_items,
            compliance_gaps=compliance_gaps,
            recommendations=recommendations,
        )
    
    def export_evidence(
        self,
        strategy_id: str,
        format: str = "json"
    ) -> str:
        """Export evidence for a strategy"""
        evidence_list = self._evidence.get(strategy_id, [])
        
        if format == "json":
            return json.dumps([
                {
                    "evidence_id": e.evidence_id,
                    "type": e.evidence_type,
                    "requirement": e.requirement,
                    "title": e.title,
                    "verified": e.verified,
                    "created_at": e.created_at,
                }
                for e in evidence_list
            ], indent=2)
        
        elif format == "markdown":
            md = f"# Evidence for {strategy_id}\n\n"
            for e in evidence_list:
                status = "✅" if e.verified else "❌"
                md += f"## {status} {e.title}\n\n"
                md += f"**Type:** {e.evidence_type}\n"
                md += f"**Requirement:** {e.requirement}\n"
                md += f"**Created:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(e.created_at))}\n"
                md += f"**By:** {e.created_by}\n\n"
            return md
        
        return ""
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
