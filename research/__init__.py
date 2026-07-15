"""
AI Research Lab - Experimentation and Benchmarking

Comprehensive research environment:
- Strategy comparison
- AI model evaluation
- Feature set analysis
- Ensemble configuration
- Parameter sweeps
- Experiment tracking
"""

from research.lab import ResearchLab, Experiment, ExperimentResult
from research.tracking import ExperimentTracker, MetricTracker

__all__ = [
    "ResearchLab",
    "Experiment",
    "ExperimentResult",
    "ExperimentTracker",
    "MetricTracker",
]
