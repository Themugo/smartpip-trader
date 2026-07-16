"""
Data Quality Platform
====================

Automated data quality checks for trading datasets.

Measures:
- Missing records
- Duplicate records
- Clock drift
- Timestamp ordering
- Schema compatibility
- Integrity hashes
- Feature completeness
- Market coverage
- Quality score

Automatically quarantines corrupted datasets.
"""

__version__ = "1.0.0"

from .core import (
    DataQualityReport,
    QualityMetric,
    QuarantineStatus,
    DataIssue,
)
from .checker import DataQualityChecker
from .quarantine import DataQuarantine

__all__ = [
    "DataQualityReport",
    "QualityMetric",
    "QuarantineStatus",
    "DataIssue",
    "DataQualityChecker",
    "DataQuarantine",
]
