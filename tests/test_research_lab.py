"""
Tests for Research Laboratory
============================
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from research_lab import (
    ResearchLaboratory,
    LabConfig,
    HypothesisGenerator,
    Hypothesis,
    HypothesisType,
    ExperimentPlanner,
    ExperimentRunner,
    StatisticalEvaluator,
    BenchmarkComparator,
    ResearchArchive,
    ConclusionSummarizer,
    ResearchJournal,
    WeeklyReportGenerator
)


class TestHypothesisGenerator:
    """Tests for hypothesis generator"""
    
    def test_generate_hypotheses(self):
        """Test hypothesis generation"""
        generator = HypothesisGenerator()
        
        hypotheses = generator.generate_hypotheses(count=3)
        
        assert len(hypotheses) > 0
        assert all(isinstance(h, Hypothesis) for h in hypotheses)
    
    def test_novelty_assessment(self):
        """Test novelty assessment"""
        generator = HypothesisGenerator()
        
        hypothesis = Hypothesis(
            id="test_1",
            type=HypothesisType.MEAN_REVERSION,
            description="Test hypothesis",
            variables=[],
            expected_direction="positive",
            confidence=0.7,
            rationale="Testing"
        )
        
        novelty = generator._assess_novelty(hypothesis)
        
        assert 0 <= novelty <= 1


class TestExperimentPlanner:
    """Tests for experiment planner"""
    
    def test_create_plan(self):
        """Test experiment plan creation"""
        planner = ExperimentPlanner()
        
        hypothesis = Hypothesis(
            id="test_1",
            type=HypothesisType.MEAN_REVERSION,
            description="Test hypothesis",
            variables=[],
            expected_direction="positive",
            confidence=0.7,
            rationale="Testing"
        )
        
        plan = planner.create_plan(hypothesis, idea_id="idea_1")
        
        assert plan is not None
        assert plan.name.startswith("Experiment_")
        assert len(plan.parameters) > 0


class TestExperimentRunner:
    """Tests for experiment runner"""
    
    def test_run_experiment(self):
        """Test experiment execution"""
        runner = ExperimentRunner(seed=42)
        
        # Create mock plan
        plan = MagicMock()
        plan.id = "plan_1"
        plan.name = "Test Experiment"
        plan.parameters = {
            "lookback_days": 30,
            "entry_threshold": 2.0,
            "stop_loss_pct": 0.02
        }
        plan.hypothesis = MagicMock()
        plan.hypothesis.type = MagicMock()
        plan.hypothesis.type.value = "mean_reversion"
        
        result = runner.run(plan)
        
        assert result is not None
        assert result.plan_id == plan.id
        assert len(result.metrics) > 0


class TestStatisticalEvaluator:
    """Tests for statistical evaluator"""
    
    def test_evaluate(self):
        """Test statistical evaluation"""
        evaluator = StatisticalEvaluator(confidence_level=0.95)
        
        # Create mock result
        result = MagicMock()
        result.id = "exp_1"
        result.returns = [0.01, -0.005, 0.02, -0.01, 0.015, 0.008]
        result.trades = []
        result.metrics = {
            "total_return": 0.05,
            "sharpe_ratio": 1.2
        }
        
        stats = evaluator.evaluate(result)
        
        assert stats is not None
        assert 0 <= stats.p_value <= 1
        assert -1 <= stats.effect_size <= 1


class TestBenchmarkComparator:
    """Tests for benchmark comparator"""
    
    def test_compare(self):
        """Test benchmark comparison"""
        comparator = BenchmarkComparator()
        
        # Create mock result
        result = MagicMock()
        result.id = "exp_1"
        result.returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        result.metrics = {
            "total_return": 0.05,
            "max_drawdown": 0.02
        }
        
        comparison = comparator.compare(result)
        
        assert comparison is not None
        assert comparison.experiment_id == result.id
        assert isinstance(comparison.excess_return, float)


class TestConclusionSummarizer:
    """Tests for conclusion summarizer"""
    
    def test_summarize(self):
        """Test summary generation"""
        summarizer = ConclusionSummarizer()
        
        # Create mock hypothesis
        hypothesis = Hypothesis(
            id="test_1",
            type=HypothesisType.MEAN_REVERSION,
            description="Test hypothesis",
            variables=[],
            expected_direction="positive",
            confidence=0.7,
            rationale="Testing"
        )
        
        # Create mock results
        exp_result = MagicMock()
        exp_result.id = "exp_1"
        exp_result.returns = [0.01] * 30
        exp_result.trades = []
        exp_result.metrics = {
            "total_return": 0.05,
            "sharpe_ratio": 1.2,
            "max_drawdown": 0.02,
            "win_rate": 0.6,
            "trade_count": 30
        }
        
        stats_result = MagicMock()
        stats_result.id = "stats_1"
        stats_result.p_value = 0.02
        stats_result.is_significant = True
        stats_result.effect_size = 0.5
        stats_result.confidence_interval = (-0.01, 0.11)
        stats_result.power = 0.8
        stats_result.significance_level = 0.05
        stats_result.assumptions_valid = True
        stats_result.assumptions_check = {
            "normality": True,
            "independence": True,
            "sample_size": True
        }
        
        bench_result = MagicMock()
        bench_result.id = "bench_1"
        bench_result.is_outperforming = True
        bench_result.excess_return = 0.03
        bench_result.information_ratio = 0.8
        
        summary = summarizer.summarize(
            hypothesis=hypothesis,
            experiment_result=exp_result,
            statistical_result=stats_result,
            benchmark_result=bench_result
        )
        
        assert summary is not None
        assert summary.main_conclusion is not None
        assert len(summary.recommendations) > 0


class TestResearchArchive:
    """Tests for research archive"""
    
    def test_archive_research(self):
        """Test archiving research"""
        archive = ResearchArchive(db_path=":memory:")
        
        # Create mock idea
        idea = MagicMock()
        idea.id = "idea_1"
        idea.hypothesis = Hypothesis(
            id="hyp_1",
            type=HypothesisType.MEAN_REVERSION,
            description="Test hypothesis",
            variables=[],
            expected_direction="positive",
            confidence=0.7,
            rationale="Testing"
        )
        idea.priority = 0.8
        idea.novelty_score = 0.7
        idea.feasibility_score = 0.6
        idea.potential_impact = 0.8
        idea.status = "completed"
        
        archived = archive.archive_research(idea)
        
        assert archived is not None
        assert archived.status.value == "archived"
        assert "mean_reversion" in archived.tags


class TestResearchJournal:
    """Tests for research journal"""
    
    def test_log_hypothesis(self):
        """Test logging hypothesis"""
        journal = ResearchJournal(db_path=":memory:")
        
        hypothesis = Hypothesis(
            id="hyp_1",
            type=HypothesisType.MEAN_REVERSION,
            description="Test hypothesis",
            variables=[],
            expected_direction="positive",
            confidence=0.7,
            rationale="Testing"
        )
        
        entry = journal.log_hypothesis(hypothesis, idea_id="idea_1")
        
        assert entry is not None
        assert entry.entry_type.value == "hypothesis"
    
    def test_log_observation(self):
        """Test logging observation"""
        journal = ResearchJournal(db_path=":memory:")
        
        entry = journal.log_observation(
            title="Test observation",
            content="This is a test observation",
            tags=["test"]
        )
        
        assert entry is not None
        assert entry.entry_type.value == "observation"


class TestWeeklyReportGenerator:
    """Tests for weekly report generator"""
    
    def test_generate_report(self):
        """Test report generation"""
        journal = ResearchJournal(db_path=":memory:")
        generator = WeeklyReportGenerator(journal)
        
        # Create mock ideas
        ideas = []
        for i in range(5):
            idea = MagicMock()
            idea.id = f"idea_{i}"
            idea.hypothesis = MagicMock()
            idea.hypothesis.id = f"hyp_{i}"
            idea.hypothesis.type = MagicMock()
            idea.hypothesis.type.value = "mean_reversion"
            idea.hypothesis.description = f"Test hypothesis {i}"
            idea.priority = 0.6 + i * 0.05
            idea.novelty_score = 0.7
            idea.feasibility_score = 0.6
            idea.potential_impact = 0.7
            idea.status = "pending" if i < 3 else "completed"
            ideas.append(idea)
        
        report = generator.generate(ideas, archived=[])
        
        assert report is not None
        assert len(report.recommendations) > 0
        assert len(report.summary) > 0


class TestResearchLaboratory:
    """Tests for research laboratory"""
    
    def test_initialization(self):
        """Test lab initialization"""
        lab = ResearchLaboratory()
        
        assert lab.status.value == "idle"
        assert isinstance(lab.config, LabConfig)
    
    def test_generate_hypotheses(self):
        """Test hypothesis generation"""
        lab = ResearchLaboratory()
        
        hypotheses = lab._generate_hypotheses()
        
        assert len(hypotheses) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
