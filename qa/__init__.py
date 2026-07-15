"""
Continuous Quality Assurance System

Automated validation:
- Plugin integrity
- Configuration correctness
- Dependency health
- API compatibility
- Model availability
- Strategy registration
- Dashboard functionality
- WebSocket reliability
"""

from qa.validator import QualityAssurance, ValidationCheck, ValidationResult

__all__ = [
    "QualityAssurance",
    "ValidationCheck",
    "ValidationResult",
]
