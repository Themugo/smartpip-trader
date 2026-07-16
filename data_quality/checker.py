"""
Data Quality Checker
====================

Automated data quality checks for trading datasets.
"""

import time
import hashlib
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

from .core import (
    DataQualityReport,
    QualityMetric,
    QuarantineStatus,
    DataIssue,
    QualityThresholds,
)

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Automated data quality checker.
    
    Performs comprehensive checks on trading datasets:
    - Missing records
    - Duplicate records
    - Clock drift
    - Timestamp ordering
    - Schema compatibility
    - Integrity hashes
    - Feature completeness
    - Market coverage
    """
    
    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        self.thresholds = thresholds or QualityThresholds()
        self._issue_callbacks: List[Callable] = []
    
    def check(self, dataset: Any, dataset_id: str, dataset_name: str) -> DataQualityReport:
        """
        Perform all quality checks on a dataset.
        
        Args:
            dataset: DataFrame or dict-like data
            dataset_id: Unique identifier
            dataset_name: Human-readable name
        
        Returns:
            DataQualityReport with all findings
        """
        # Convert to DataFrame if needed
        if not isinstance(dataset, pd.DataFrame):
            df = pd.DataFrame(dataset)
        else:
            df = dataset
        
        report = DataQualityReport(
            report_id=f"dq_{dataset_id}_{int(time.time())}",
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            status="pass",
            quarantine_status=QuarantineStatus.CLEAN,
            quality_score=1.0,
            record_count=len(df),
            field_count=len(df.columns),
        )
        
        # Run all checks
        issues = []
        warnings = []
        
        # 1. Missing records
        missing_result = self._check_missing(df, dataset_id)
        report.metrics["missing_ratio"] = missing_result["ratio"]
        if missing_result["issues"]:
            issues.extend(missing_result["issues"])
        
        # 2. Duplicate records
        duplicate_result = self._check_duplicates(df, dataset_id)
        report.metrics["duplicate_ratio"] = duplicate_result["ratio"]
        if duplicate_result["issues"]:
            issues.extend(duplicate_result["issues"])
        
        # 3. Timestamp ordering
        if "timestamp" in df.columns or "date" in df.columns:
            ts_result = self._check_timestamp_ordering(df, dataset_id)
            report.metrics["timestamp_gaps"] = ts_result["gap_count"]
            if ts_result["issues"]:
                issues.extend(ts_result["issues"])
        
        # 4. Clock drift
        clock_result = self._check_clock_drift(df, dataset_id)
        report.metrics["clock_drift_seconds"] = clock_result["max_drift"]
        if clock_result["issues"]:
            issues.extend(clock_result["issues"])
        
        # 5. Schema validation
        schema_result = self._check_schema(df, dataset_id)
        report.metrics["schema_valid"] = 1.0 if schema_result["valid"] else 0.0
        if schema_result["issues"]:
            issues.extend(schema_result["issues"])
        
        # 6. Data freshness
        freshness_result = self._check_data_freshness(df, dataset_id)
        report.metrics["data_freshness_hours"] = freshness_result["hours_old"]
        if freshness_result["issues"]:
            warnings.extend(freshness_result["issues"])
        
        # 7. Feature completeness
        completeness_result = self._check_feature_completeness(df, dataset_id)
        report.metrics["feature_completeness"] = completeness_result["score"]
        if completeness_result["issues"]:
            issues.extend(completeness_result["issues"])
        
        # 8. Market coverage (for trading data)
        if "symbol" in df.columns:
            coverage_result = self._check_market_coverage(df, dataset_id)
            report.metrics["market_coverage"] = coverage_result["coverage"]
            if coverage_result["issues"]:
                warnings.extend(coverage_result["issues"])
        
        # Assign issues and warnings
        report.issues = issues
        report.critical_issues = [i.description for i in issues if i.severity == "critical"]
        report.warnings = warnings
        
        # Calculate quality score
        report.quality_score = self._calculate_quality_score(report.metrics)
        
        # Determine status
        if report.critical_issues:
            report.status = "fail"
        elif warnings or report.quality_score < self.thresholds.min_quality_score:
            report.status = "warning"
        
        # Generate checksums
        report.checksum = self._calculate_checksum(df)
        report.schema_hash = self._calculate_schema_hash(df)
        
        # Notify callbacks
        for issue in issues:
            self._notify_issue(issue)
        
        return report
    
    def _check_missing(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check for missing records"""
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0
        
        issues = []
        if missing_ratio > self.thresholds.max_missing_ratio:
            for col in df.columns:
                col_missing = df[col].isna().sum()
                if col_missing > 0:
                    issues.append(DataIssue(
                        issue_id=f"missing_{dataset_id}_{col}",
                        metric=QualityMetric.MISSING_RECORDS,
                        severity="critical" if missing_ratio > 0.1 else "high",
                        description=f"Column '{col}' has {col_missing} missing values ({col_missing/len(df):.1%})",
                        affected_records=col_missing,
                        affected_fields=[col],
                        dataset_id=dataset_id,
                    ))
        
        return {
            "ratio": missing_ratio,
            "issues": issues,
        }
    
    def _check_duplicates(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check for duplicate records"""
        duplicates = df.duplicated().sum()
        duplicate_ratio = duplicates / len(df) if len(df) > 0 else 0
        
        issues = []
        if duplicate_ratio > self.thresholds.max_duplicate_ratio:
            issues.append(DataIssue(
                issue_id=f"dup_{dataset_id}",
                metric=QualityMetric.DUPLICATE_RECORDS,
                severity="high",
                description=f"Found {duplicates} duplicate records ({duplicate_ratio:.1%})",
                affected_records=duplicates,
                dataset_id=dataset_id,
            ))
        
        return {
            "ratio": duplicate_ratio,
            "issues": issues,
        }
    
    def _check_timestamp_ordering(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check for timestamp ordering issues and gaps"""
        ts_col = "timestamp" if "timestamp" in df.columns else "date"
        timestamps = pd.to_datetime(df[ts_col], errors="coerce")
        
        # Check for NaT (not a time) values
        nat_count = timestamps.isna().sum()
        
        # Check for gaps
        valid_ts = timestamps.dropna().sort_values()
        gaps = valid_ts.diff().dropna()
        
        # Consider gaps > 1 day as significant
        significant_gaps = gaps[gaps > timedelta(hours=self.thresholds.max_temporal_gap_hours)]
        gap_count = len(significant_gaps)
        
        issues = []
        if nat_count > 0:
            issues.append(DataIssue(
                issue_id=f"ts_nat_{dataset_id}",
                metric=QualityMetric.TIMESTAMP_ORDERING,
                severity="medium",
                description=f"Found {nat_count} invalid timestamps",
                affected_records=nat_count,
                dataset_id=dataset_id,
            ))
        
        if gap_count > 0:
            issues.append(DataIssue(
                issue_id=f"ts_gaps_{dataset_id}",
                metric=QualityMetric.TIMESTAMP_ORDERING,
                severity="medium",
                description=f"Found {gap_count} significant temporal gaps (>24h)",
                affected_records=gap_count,
                dataset_id=dataset_id,
            ))
        
        return {
            "gap_count": gap_count,
            "issues": issues,
        }
    
    def _check_clock_drift(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check for clock drift in timestamps"""
        ts_col = "timestamp" if "timestamp" in df.columns else "date"
        timestamps = pd.to_datetime(df[ts_col], errors="coerce")
        
        # Compare with current time for recent data
        now = datetime.now()
        max_drift = 0.0
        
        recent = timestamps[timestamps > now - timedelta(hours=24)]
        if len(recent) > 0:
            drift = abs((now - recent.max()).total_seconds())
            max_drift = drift
        
        issues = []
        if max_drift > self.thresholds.max_clock_drift_seconds:
            issues.append(DataIssue(
                issue_id=f"drift_{dataset_id}",
                metric=QualityMetric.CLOCK_DRIFT,
                severity="high",
                description=f"Clock drift detected: {max_drift:.1f} seconds",
                affected_records=1,
                dataset_id=dataset_id,
            ))
        
        return {
            "max_drift": max_drift,
            "issues": issues,
        }
    
    def _check_schema(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check schema compatibility"""
        issues = []
        
        # Check for required columns
        required_columns = ["timestamp", "symbol"]
        for col in required_columns:
            if col not in df.columns:
                issues.append(DataIssue(
                    issue_id=f"schema_{dataset_id}_{col}",
                    metric=QualityMetric.SCHEMA_COMPATIBILITY,
                    severity="critical",
                    description=f"Missing required column: '{col}'",
                    affected_records=len(df),
                    dataset_id=dataset_id,
                ))
        
        # Check data types
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    issues.append(DataIssue(
                        issue_id=f"dtype_{dataset_id}_{col}",
                        metric=QualityMetric.SCHEMA_COMPATIBILITY,
                        severity="high",
                        description=f"Column '{col}' should be numeric",
                        affected_records=df[col].notna().sum(),
                        dataset_id=dataset_id,
                    ))
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }
    
    def _check_data_freshness(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check data freshness"""
        ts_col = "timestamp" if "timestamp" in df.columns else "date"
        timestamps = pd.to_datetime(df[ts_col], errors="coerce")
        
        now = datetime.now()
        latest = timestamps.max()
        
        if pd.isna(latest):
            hours_old = float('inf')
        else:
            hours_old = (now - latest).total_seconds() / 3600
        
        issues = []
        if hours_old > self.thresholds.max_temporal_gap_hours:
            issues.append(f"Data is {hours_old:.1f} hours old (threshold: {self.thresholds.max_temporal_gap_hours}h)")
        
        return {
            "hours_old": hours_old,
            "issues": issues,
        }
    
    def _check_feature_completeness(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check feature completeness"""
        required_features = ["open", "high", "low", "close", "volume"]
        
        completeness_scores = {}
        issues = []
        
        for feature in required_features:
            if feature in df.columns:
                completeness = df[feature].notna().sum() / len(df) if len(df) > 0 else 0
                completeness_scores[feature] = completeness
                
                if completeness < self.thresholds.min_feature_completeness:
                    issues.append(DataIssue(
                        issue_id=f"feature_{dataset_id}_{feature}",
                        metric=QualityMetric.FEATURE_COMPLETENESS,
                        severity="high",
                        description=f"Feature '{feature}' is only {completeness:.1%} complete",
                        affected_records=int((1 - completeness) * len(df)),
                        affected_fields=[feature],
                        dataset_id=dataset_id,
                    ))
        
        avg_completeness = np.mean(list(completeness_scores.values())) if completeness_scores else 0
        
        return {
            "score": avg_completeness,
            "details": completeness_scores,
            "issues": issues,
        }
    
    def _check_market_coverage(
        self,
        df: pd.DataFrame,
        dataset_id: str
    ) -> Dict[str, Any]:
        """Check market coverage"""
        symbols = df["symbol"].unique()
        
        # In a real implementation, this would compare against a known universe
        # For now, assume we want at least some coverage
        coverage = len(symbols) / 100  # Normalized (assume universe of 100)
        coverage = min(coverage, 1.0)
        
        issues = []
        if coverage < self.thresholds.min_coverage_ratio:
            issues.append(f"Market coverage is only {coverage:.1%} (threshold: {self.thresholds.min_coverage_ratio:.1%})")
        
        return {
            "coverage": coverage,
            "symbol_count": len(symbols),
            "issues": issues,
        }
    
    def _calculate_quality_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall quality score"""
        weights = {
            "missing_ratio": 0.25,
            "duplicate_ratio": 0.15,
            "feature_completeness": 0.30,
            "market_coverage": 0.15,
            "schema_valid": 0.15,
        }
        
        score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in metrics:
                if "ratio" in metric:
                    # Lower is better for ratios
                    value = 1 - metrics[metric]
                elif "valid" in metric or "coverage" in metric:
                    value = metrics[metric]
                else:
                    value = 1.0
                
                score += value * weight
                total_weight += weight
        
        if total_weight > 0:
            score = score / total_weight
        
        return max(0.0, min(1.0, score))
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate data checksum"""
        content = df.to_json(date_format="iso")
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_schema_hash(self, df: pd.DataFrame) -> str:
        """Calculate schema hash"""
        schema = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
        content = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def on_issue(self, callback: Callable[[DataIssue], None]) -> None:
        """Register issue callback"""
        self._issue_callbacks.append(callback)
    
    def _notify_issue(self, issue: DataIssue) -> None:
        """Notify issue callbacks"""
        for callback in self._issue_callbacks:
            try:
                callback(issue)
            except Exception as e:
                logger.error(f"Issue callback error: {e}")
