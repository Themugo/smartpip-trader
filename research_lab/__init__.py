"""
Autonomous Quant Research Laboratory
===================================

A self-directed research system for algorithmic trading.

Components:
    - Hypothesis Generator
    - Experiment Planner
    - Experiment Runner
    - Statistical Evaluator
    - Benchmark Comparator
    - Archive
    - Summarizer
    - Research Journal
    - Weekly Report Generator
"""

__version__ = "1.0.0"

from .lab import ResearchLaboratory, LabConfig, ResearchIdea, LabStatus
from .hypothesis import HypothesisGenerator, Hypothesis, HypothesisType, Variable
from .planner import ExperimentPlanner, ExperimentPlan, ExperimentStatus
from .runner import ExperimentRunner, ExperimentResult, TradeRecord
from .statistics import StatisticalEvaluator, StatisticalResult
from .benchmark import BenchmarkComparator, BenchmarkResult, BenchmarkType
from .archive import ResearchArchive, ArchivedResearch, ArchiveStatus
from .summarizer import ConclusionSummarizer, ResearchSummary, Conclusion, ConclusionType
from .journal import ResearchJournal, JournalEntry, JournalEntryType
from .weekly_report import WeeklyReportGenerator, WeeklyReport, Recommendation, RecommendationPriority

__all__ = [
    "ResearchLaboratory",
    "LabConfig",
    "ResearchIdea",
    "LabStatus",
    "HypothesisGenerator",
    "Hypothesis",
    "HypothesisType",
    "Variable",
    "ExperimentPlanner",
    "ExperimentPlan",
    "ExperimentStatus",
    "ExperimentRunner",
    "ExperimentResult",
    "TradeRecord",
    "StatisticalEvaluator",
    "StatisticalResult",
    "BenchmarkComparator",
    "BenchmarkResult",
    "BenchmarkType",
    "ResearchArchive",
    "ArchivedResearch",
    "ArchiveStatus",
    "ConclusionSummarizer",
    "ResearchSummary",
    "Conclusion",
    "ConclusionType",
    "ResearchJournal",
    "JournalEntry",
    "JournalEntryType",
    "WeeklyReportGenerator",
    "WeeklyReport",
    "Recommendation",
    "RecommendationPriority",
]
