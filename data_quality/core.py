"""
Data Quality Core
================

Core classes for data quality management.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuarantineStatus(Enum):
    """Data quarantine status"""
    CLEAN = "clean"
    QUARANTINED = "quarantined"
    UNDER_REVIEW = "under_review"
    RESTORED = "restored"


class QualityMetric(Enum):
    """Data quality metrics"""
    MISSING_RECORDS = "missing_records"
    DUPLICATE_RECORDS = "duplicate_records"
    CLOCK_DRIFT = "clock_drift"
    TIMESTAMP_ORDERING = "timestamp_ordering"
    SCHEMA_COMPATIBILITY = "schema_compatibility"
    INTEGRITY_HASH = "integrity_hash"
    FEATURE_COMPLETENESS = "feature_completeness"
    MARKET_COVERAGE = "market_coverage"
    DATA_FRESHNESS = "data_freshness"


@dataclass
class DataIssue:
    """A data quality issue"""
    issue_id: str
    metric: QualityMetric
    severity: str  # critical, high, medium, low
    
    # Details
    description: str
    affected_records: int
    dataset_id: str
    
    # Location
    affected_fields: List[str] = field(default_factory=list)
    file_path: str = ""
    
    # Timestamps
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    
    # Resolution
    resolution: str = ""
    resolved_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "metric": self.metric.value,
            "severity": self.severity,
            "description": self.description,
            "affected_records": self.affected_records,
            "affected_fields": self.affected_fields,
            "dataset_id": self.dataset_id,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
        }


@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    report_id: str
    dataset_id: str
    dataset_name: str
    
    # Status
    status: str  # "pass", "fail", "warning"
    quarantine_status: QuarantineStatus
    
    # Metrics
    quality_score: float  # 0.0 - 1.0
    
    # Detailed metrics
    metrics: Dict[str, float] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)
    
    # Issues
    issues: List[DataIssue] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Coverage
    record_count: int = 0
    field_count: int = 0
    temporal_start: float = 0
    temporal_end: float = 0
    
    # Integrity
    checksum: str = ""
    schema_hash: str = ""
    
    # Metadata
    generated_at: float = field(default_factory=time.time)
    data_source: str = ""
    data_version: str = ""
    
    def is_acceptable(self) -> bool:
        """Check if data is acceptable for use"""
        return (
            self.status != "fail" and
            self.quarantine_status == QuarantineStatus.CLEAN and
            self.quality_score >= 0.8
        )
    
    def get_action(self) -> str:
        """Get recommended action"""
        if self.quarantine_status == QuarantineStatus.QUARANTINED:
            return "DO NOT USE - Data is quarantined"
        elif self.status == "fail":
            return "DO NOT USE - Critical issues found"
        elif self.status == "warning":
            return "USE WITH CAUTION - Warnings present"
        elif self.quality_score < 0.8:
            return "REVIEW REQUIRED - Quality below threshold"
        return "USE - Data passed all checks"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "status": self.status,
            "quarantine_status": self.quarantine_status.value,
            "quality_score": self.quality_score,
            "metrics": self.metrics,
            "issues_count": len(self.issues),
            "critical_issues": self.critical_issues,
            "record_count": self.record_count,
            "generated_at": self.generated_at,
            "action": self.get_action(),
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        status_emoji = {
            "pass": "✅",
            "fail": "❌",
            "warning": "⚠️",
        }.get(self.status, "❓")
        
        md = f"""# Data Quality Report

**Dataset:** {self.dataset_name}
**ID:** {self.dataset_id}
**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.generated_at))}

## Summary

| Metric | Value |
|--------|-------|
| Status | {status_emoji} {self.status.upper()} |
| Quality Score | {self.quality_score:.1%} |
| Records | {self.record_count:,} |
| Quarantine | {self.quarantine_status.value} |

## Quality Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
"""
        
        for metric, value in self.metrics.items():
            threshold = self.thresholds.get(metric, 0)
            threshold_str = f"{threshold:.1%}" if isinstance(threshold, float) else str(threshold)
            value_str = f"{value:.1%}" if isinstance(value, float) else str(value)
            status = "✅" if value >= threshold else "❌"
            md += f"| {metric} | {value_str} | {threshold_str} | {status} |\n"
        
        if self.critical_issues:
            md += "\n## Critical Issues\n\n"
            for issue in self.critical_issues:
                md += f"- ❌ {issue}\n"
        
        if self.warnings:
            md += "\n## Warnings\n\n"
            for warning in self.warnings:
                md += f"- ⚠️ {warning}\n"
        
        md += f"\n## Recommendation\n\n{self.get_action()}\n"
        
        return md


@dataclass
class QualityThresholds:
    """Thresholds for data quality checks"""
    min_quality_score: float = 0.8
    max_missing_ratio: float = 0.05
    max_duplicate_ratio: float = 0.01
    max_clock_drift_seconds: float = 5.0
    min_coverage_ratio: float = 0.95
    min_feature_completeness: float = 0.90
    max_temporal_gap_hours: float = 24
