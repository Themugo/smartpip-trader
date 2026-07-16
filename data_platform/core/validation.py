"""
Dataset Validator

Automatic validation of datasets before use.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from data_platform.models.dataset import (
    DataQuality,
    MissingDataReport,
    DuplicateReport,
)

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels"""
    BASIC = "basic"  # Quick validation
    STANDARD = "standard"  # Standard checks
    STRICT = "strict"  # Comprehensive validation


class ValidationError:
    """A validation error"""
    
    def __init__(
        self,
        field: str,
        message: str,
        severity: str = "error",  # error, warning, info
        details: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.message = message
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
            "details": self.details,
        }


class ValidationResult:
    """Result of dataset validation"""
    
    def __init__(
        self,
        dataset_id: str,
        passed: bool,
        level: ValidationLevel,
        errors: Optional[List[ValidationError]] = None,
        warnings: Optional[List[ValidationError]] = None,
        quality: Optional[DataQuality] = None,
        missing_report: Optional[MissingDataReport] = None,
        duplicate_report: Optional[DuplicateReport] = None,
        validation_time_ms: float = 0,
        validated_at: datetime = None,
        validator: str = "system",
    ):
        self.dataset_id = dataset_id
        self.passed = passed
        self.level = level
        self.errors = errors or []
        self.warnings = warnings or []
        self.quality = quality
        self.missing_report = missing_report
        self.duplicate_report = duplicate_report
        self.validation_time_ms = validation_time_ms
        self.validated_at = validated_at or datetime.utcnow()
        self.validator = validator
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "passed": self.passed,
            "level": self.level.value,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "quality": self.quality.to_dict() if self.quality else None,
            "missing_report": self.missing_report.to_dict() if self.missing_report else None,
            "duplicate_report": self.duplicate_report.to_dict() if self.duplicate_report else None,
            "validation_time_ms": self.validation_time_ms,
            "validated_at": self.validated_at.isoformat() if isinstance(self.validated_at, datetime) else self.validated_at,
            "validator": self.validator,
        }


class DatasetValidator:
    """
    Dataset Validator for automatic data quality checks.
    
    Every dataset must be validated before use.
    
    Features:
    - Automatic validation
    - Configurable validation levels
    - Quality scoring
    - Missing data analysis
    - Duplicate detection
    - Schema validation
    - Statistical validation
    """
    
    def __init__(
        self,
        default_level: ValidationLevel = ValidationLevel.STANDARD,
        min_quality_threshold: float = 0.7,
    ):
        self._default_level = default_level
        self._min_quality_threshold = min_quality_threshold
        
        # Custom validators
        self._validators: Dict[str, Callable] = {}
        
        # Validation history
        self._history: Dict[str, List[ValidationResult]] = {}
    
    def register_validator(
        self,
        name: str,
        validator_func: Callable[[Any], Tuple[bool, str]],
    ) -> None:
        """Register a custom validator"""
        self._validators[name] = validator_func
    
    def validate(
        self,
        dataset_id: str,
        data: Any,  # DataFrame, list of dicts, or bytes
        level: Optional[ValidationLevel] = None,
        validator: str = "system",
        schema: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate a dataset.
        
        Automatically validates every dataset before use.
        """
        import time
        start_time = time.time()
        
        level = level or self._default_level
        
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # Convert to DataFrame if needed
        df = self._to_dataframe(data)
        
        if df is None:
            errors.append(ValidationError(
                field="data",
                message="Unable to parse data",
                severity="error",
            ))
            return ValidationResult(
                dataset_id=dataset_id,
                passed=False,
                level=level,
                errors=errors,
                validation_time_ms=(time.time() - start_time) * 1000,
                validator=validator,
            )
        
        # Basic validation (all levels)
        basic_errors, basic_warnings = self._validate_basic(df)
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)
        
        # Standard validation
        if level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            std_errors, std_warnings = self._validate_standard(df)
            errors.extend(std_errors)
            warnings.extend(std_warnings)
        
        # Strict validation
        if level == ValidationLevel.STRICT:
            strict_errors, strict_warnings = self._validate_strict(df)
            errors.extend(strict_errors)
            warnings.extend(strict_warnings)
        
        # Schema validation
        if schema:
            schema_errors, schema_warnings = self._validate_schema(df, schema)
            errors.extend(schema_errors)
            warnings.extend(schema_warnings)
        
        # Custom validators
        for name, validator_func in self._validators.items():
            try:
                passed, message = validator_func(data)
                if not passed:
                    errors.append(ValidationError(
                        field=name,
                        message=message,
                        severity="error",
                    ))
            except Exception as e:
                warnings.append(ValidationError(
                    field=name,
                    message=f"Custom validator failed: {e}",
                    severity="warning",
                ))
        
        # Compute quality metrics
        quality = self._compute_quality(df, errors, warnings)
        missing_report = self._analyze_missing(df)
        duplicate_report = self._analyze_duplicates(df)
        
        # Determine if passed
        passed = (
            len(errors) == 0 and
            quality.overall_score >= self._min_quality_threshold
        )
        
        result = ValidationResult(
            dataset_id=dataset_id,
            passed=passed,
            level=level,
            errors=errors,
            warnings=warnings,
            quality=quality,
            missing_report=missing_report,
            duplicate_report=duplicate_report,
            validation_time_ms=(time.time() - start_time) * 1000,
            validator=validator,
        )
        
        # Store in history
        if dataset_id not in self._history:
            self._history[dataset_id] = []
        self._history[dataset_id].append(result)
        
        # Keep only recent history
        if len(self._history[dataset_id]) > 100:
            self._history[dataset_id] = self._history[dataset_id][-100:]
        
        if passed:
            logger.info(f"Dataset {dataset_id} passed validation (quality: {quality.overall_score:.2%})")
        else:
            logger.warning(f"Dataset {dataset_id} failed validation: {len(errors)} errors")
        
        return result
    
    def _to_dataframe(self, data: Any):
        """Convert data to DataFrame"""
        try:
            import pandas as pd
            
            if isinstance(data, pd.DataFrame):
                return data
            elif isinstance(data, bytes):
                import io
                return pd.read_parquet(io.BytesIO(data))
            elif isinstance(data, (list, tuple)):
                return pd.DataFrame(data)
            elif isinstance(data, str):
                if data.endswith(".parquet"):
                    return pd.read_parquet(data)
                elif data.endswith(".csv"):
                    return pd.read_csv(data)
                elif data.endswith(".json"):
                    return pd.read_json(data)
            
            return None
        except Exception as e:
            logger.error(f"Error converting to DataFrame: {e}")
            return None
    
    def _validate_basic(self, df) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Basic validation checks"""
        errors = []
        warnings = []
        
        if df is None or len(df) == 0:
            errors.append(ValidationError(
                field="data",
                message="Dataset is empty",
                severity="error",
            ))
            return errors, warnings
        
        # Check for no columns
        if len(df.columns) == 0:
            errors.append(ValidationError(
                field="columns",
                message="Dataset has no columns",
                severity="error",
            ))
        
        # Check for null dataset
        if df.empty:
            errors.append(ValidationError(
                field="data",
                message="DataFrame is empty",
                severity="error",
            ))
        
        return errors, warnings
    
    def _validate_standard(self, df) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Standard validation checks"""
        errors = []
        warnings = []
        
        # Check for all-null columns
        for col in df.columns:
            null_pct = df[col].isnull().sum() / len(df)
            if null_pct > 0.5:
                warnings.append(ValidationError(
                    field=col,
                    message=f"Column is {null_pct:.1%} null",
                    severity="warning",
                    details={"null_percentage": null_pct},
                ))
        
        # Check for constant columns
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].nunique() == 1:
                warnings.append(ValidationError(
                    field=col,
                    message="Column has only one unique value",
                    severity="warning",
                ))
        
        # Check for duplicates
        dup_count = df.duplicated().sum()
        dup_pct = dup_count / len(df) if len(df) > 0 else 0
        if dup_pct > 0.1:
            warnings.append(ValidationError(
                field="data",
                message=f"Dataset has {dup_pct:.1%} duplicate rows",
                severity="warning",
                details={"duplicate_count": dup_count, "duplicate_percentage": dup_pct},
            ))
        
        # Check for future dates
        date_cols = df.select_dtypes(include=["datetime64", "datetime"]).columns
        for col in date_cols:
            future_count = (df[col] > datetime.utcnow()).sum()
            if future_count > 0:
                warnings.append(ValidationError(
                    field=col,
                    message=f"Column has {future_count} future dates",
                    severity="warning",
                ))
        
        return errors, warnings
    
    def _validate_strict(self, df) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Strict validation checks"""
        errors = []
        warnings = []
        
        # Check for data type consistency
        for col in df.columns:
            dtype = df[col].dtype
            
            # Check for mixed types in object columns
            if dtype == "object":
                sample = df[col].dropna().head(100)
                if len(sample) > 0:
                    type_counts = sample.apply(type).value_counts()
                    if len(type_counts) > 3:
                        warnings.append(ValidationError(
                            field=col,
                            message="Column has mixed data types",
                            severity="warning",
                            details={"type_distribution": type_counts.to_dict()},
                        ))
        
        # Check for outliers in numeric columns
        for col in df.select_dtypes(include=[np.number]).columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 3 * iqr
                upper_bound = q3 + 3 * iqr
                outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                outlier_pct = outlier_count / len(df)
                
                if outlier_pct > 0.05:
                    warnings.append(ValidationError(
                        field=col,
                        message=f"Column has {outlier_pct:.1%} outliers",
                        severity="warning",
                        details={"outlier_count": outlier_count, "outlier_percentage": outlier_pct},
                    ))
        
        # Check for temporal gaps
        datetime_cols = df.select_dtypes(include=["datetime64"]).columns
        if len(datetime_cols) > 0:
            for col in datetime_cols:
                sorted_dates = df[col].dropna().sort_values()
                if len(sorted_dates) > 1:
                    deltas = sorted_dates.diff().dropna()
                    if len(deltas) > 0:
                        median_delta = deltas.median()
                        large_gaps = (deltas > median_delta * 10).sum()
                        if large_gaps > len(deltas) * 0.1:
                            warnings.append(ValidationError(
                                field=col,
                                message=f"Column has {large_gaps} large temporal gaps",
                                severity="warning",
                            ))
        
        return errors, warnings
    
    def _validate_schema(self, df, schema: Dict[str, Any]) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate against schema"""
        errors = []
        warnings = []
        
        expected_columns = schema.get("columns", {})
        
        # Check for missing columns
        for col in expected_columns:
            if col not in df.columns:
                errors.append(ValidationError(
                    field=col,
                    message="Required column is missing",
                    severity="error",
                ))
        
        # Check for extra columns
        for col in df.columns:
            if col not in expected_columns and schema.get("strict", False):
                warnings.append(ValidationError(
                    field=col,
                    message="Column not in schema",
                    severity="warning",
                ))
        
        # Check column types
        for col, expected_type in expected_columns.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if not self._types_compatible(actual_type, expected_type):
                    warnings.append(ValidationError(
                        field=col,
                        message=f"Column type mismatch: expected {expected_type}, got {actual_type}",
                        severity="warning",
                    ))
        
        return errors, warnings
    
    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if types are compatible"""
        type_map = {
            "int": ["int64", "int32", "int16", "int8"],
            "float": ["float64", "float32"],
            "string": ["object", "string"],
            "datetime": ["datetime64"],
        }
        
        expected_lower = expected.lower()
        if expected_lower in type_map:
            return actual in type_map[expected_lower]
        
        return expected_lower in actual.lower()
    
    def _compute_quality(self, df, errors: List[ValidationError], warnings: List[ValidationError]) -> DataQuality:
        """Compute data quality metrics"""
        if df is None or len(df) == 0:
            return DataQuality(0, 0, 0, 0, 0)
        
        # Completeness (based on missing data)
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        completeness = 1 - (missing_cells / total_cells) if total_cells > 0 else 0
        
        # Accuracy (based on errors)
        error_rate = len(errors) / max(len(df), 1)
        accuracy = max(0, 1 - error_rate)
        
        # Consistency (based on warnings)
        warning_rate = len(warnings) / max(len(df), 1)
        consistency = max(0, 1 - warning_rate)
        
        # Timeliness (would need timestamp column)
        timeliness = 1.0  # Placeholder
        
        # Validity (based on data types)
        validity = 0.9  # Placeholder
        
        return DataQuality(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity,
        )
    
    def _analyze_missing(self, df) -> Optional[MissingDataReport]:
        """Analyze missing data"""
        if df is None:
            return None
        
        total_missing = df.isnull().sum().sum()
        total_cells = len(df) * len(df.columns)
        missing_pct = total_missing / total_cells if total_cells > 0 else 0
        
        missing_by_column = {}
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_pct = null_count / len(df) if len(df) > 0 else 0
            missing_by_column[col] = (int(null_count), float(null_pct))
        
        return MissingDataReport(
            total_missing=int(total_missing),
            missing_percentage=float(missing_pct),
            missing_by_column=missing_by_column,
            missing_time_ranges=[],  # Would need timestamp analysis
            imputation_applied=False,
        )
    
    def _analyze_duplicates(self, df) -> Optional[DuplicateReport]:
        """Analyze duplicate data"""
        if df is None:
            return None
        
        dup_count = df.duplicated().sum()
        dup_pct = dup_count / len(df) if len(df) > 0 else 0
        
        # Get duplicate row indices
        dup_mask = df.duplicated(keep=False)
        dup_indices = df[dup_mask].index.tolist()
        
        return DuplicateReport(
            total_duplicates=int(dup_count),
            duplicate_percentage=float(dup_pct),
            duplicate_rows=dup_indices[:1000],  # Limit to first 1000
            duplicate_groups=[],  # Would need more complex grouping
        )
    
    def get_validation_result(
        self,
        dataset_id: str,
    ) -> Optional[ValidationResult]:
        """Get the most recent validation result"""
        history = self._history.get(dataset_id, [])
        return history[-1] if history else None
    
    def get_validation_history(
        self,
        dataset_id: str,
        limit: int = 100,
    ) -> List[ValidationResult]:
        """Get validation history"""
        return self._history.get(dataset_id, [])[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total_validations = sum(len(h) for h in self._history.values())
        passed = sum(1 for h in self._history.values() for r in h if r.passed)
        
        return {
            "total_datasets_validated": len(self._history),
            "total_validations": total_validations,
            "passed_validations": passed,
            "failed_validations": total_validations - passed,
            "pass_rate": passed / total_validations if total_validations > 0 else 0,
            "custom_validators": len(self._validators),
        }
