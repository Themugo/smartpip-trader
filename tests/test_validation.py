"""
Tests for Continuous Validation Pipeline
=======================================
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from validation import (
    ContinuousValidationPipeline,
    ValidationStage,
    ValidationStatus,
    ValidationResult,
    ValidationConfig,
    AcceptanceCriteria,
    AcceptanceResult,
    AcceptancePolicy,
    Criterion,
    CriterionType,
    ComparisonOperator,
    DeploymentReport,
    ReportGenerator,
    ReportFormat
)


class TestValidationPipeline:
    """Tests for validation pipeline"""
    
    def test_initialization(self, tmp_path):
        """Test pipeline initialization"""
        config = ValidationConfig(
            unit_test_timeout=60,
            backtest_days=30
        )
        
        pipeline = ContinuousValidationPipeline(
            config=config,
            db_path=str(tmp_path / "validation.db")
        )
        
        assert pipeline.config.unit_test_timeout == 60
        assert pipeline.config.backtest_days == 30
    
    def test_validate_runs_stages(self, tmp_path):
        """Test that validate runs all stages"""
        config = ValidationConfig(
            unit_test_timeout=300,
            integration_test_enabled=False
        )
        
        pipeline = ContinuousValidationPipeline(
            config=config,
            db_path=str(tmp_path / "validation.db")
        )
        
        # Run with only fast stages
        result = pipeline.validate(
            strategy_id="test_strategy",
            version="1.0.0",
            stages=[ValidationStage.REPLAY_TESTS, ValidationStage.BACKTEST]
        )
        
        assert result["strategy_id"] == "test_strategy"
        assert result["version"] == "1.0.0"
        assert "overall_status" in result
        assert "duration" in result
    
    def test_validation_stages(self, tmp_path):
        """Test all validation stages"""
        config = ValidationConfig()
        config.integration_test_enabled = False
        
        pipeline = ContinuousValidationPipeline(
            config=config,
            db_path=str(tmp_path / "validation.db")
        )
        
        result = pipeline.validate(
            strategy_id="strategy_test",
            version="1.0.0",
            stages=[
                ValidationStage.REPLAY_TESTS,
                ValidationStage.BACKTEST,
                ValidationStage.WALK_FORWARD,
                ValidationStage.STRESS_TESTS,
                ValidationStage.PAPER_TRADING,
                ValidationStage.STATISTICAL_COMPARISON
            ]
        )
        
        assert result["all_passed"] is True
        assert len(result["results"]) == 6
    
    def test_validation_history(self, tmp_path):
        """Test validation history tracking"""
        pipeline = ContinuousValidationPipeline(db_path=str(tmp_path / "validation.db"))
        
        # Run validation
        pipeline.validate(
            strategy_id="history_test",
            version="1.0.0",
            stages=[ValidationStage.REPLAY_TESTS]
        )
        
        # Check history
        history = pipeline.get_validation_history()
        assert len(history) >= 1
    
    def test_stage_callbacks(self, tmp_path):
        """Test stage callbacks"""
        pipeline = ContinuousValidationPipeline(db_path=str(tmp_path / "validation.db"))
        
        callback_results = []
        
        def callback(result):
            callback_results.append(result)
        
        pipeline.add_stage_callback(ValidationStage.REPLAY_TESTS, callback)
        
        pipeline.validate(
            strategy_id="callback_test",
            version="1.0.0",
            stages=[ValidationStage.REPLAY_TESTS]
        )
        
        assert len(callback_results) == 1


class TestValidationResult:
    """Tests for validation result"""
    
    def test_validation_result_properties(self):
        """Test result properties"""
        result = ValidationResult(
            stage=ValidationStage.BACKTEST,
            status=ValidationStatus.PASSED,
            start_time=datetime.now(),
            duration_seconds=10.5
        )
        
        assert result.passed is True
        assert "backtest: passed" in result.summary
    
    def test_result_metrics(self):
        """Test result metrics"""
        result = ValidationResult(
            stage=ValidationStage.BACKTEST,
            status=ValidationStatus.PASSED,
            start_time=datetime.now(),
            metrics={
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.10,
                "trade_count": 150
            }
        )
        
        assert result.metrics["sharpe_ratio"] == 1.5
        assert result.metrics["trade_count"] == 150


class TestAcceptanceCriteria:
    """Tests for acceptance criteria"""
    
    def test_default_criteria(self):
        """Test default criteria setup"""
        criteria = AcceptanceCriteria()
        
        assert len(criteria.criteria) > 0
        
        # Check for expected criteria
        names = [c.name for c in criteria.criteria]
        assert "sharpe_ratio" in names
        assert "max_drawdown" in names
    
    def test_evaluate_metrics(self):
        """Test criteria evaluation"""
        criteria = AcceptanceCriteria()
        
        metrics = {
            "sharpe_ratio": 1.5,
            "total_return": 0.10,
            "max_drawdown": 0.08,
            "win_rate": 0.55,
            "p_value": 0.02,
            "consistency_ratio": 0.75,
            "calibration_error": 0.05
        }
        
        result = criteria.evaluate(metrics)
        
        assert isinstance(result, AcceptanceResult)
        assert "sharpe_ratio" in result.results
        assert "max_drawdown" in result.results
    
    def test_add_criterion(self):
        """Test adding custom criterion"""
        criteria = AcceptanceCriteria()
        
        custom = Criterion(
            name="custom_metric",
            criterion_type=CriterionType.PERFORMANCE,
            metric="custom_value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=1.0,
            weight=2.0
        )
        
        criteria.add_criterion(custom)
        
        assert len(criteria.criteria) > 0
        assert any(c.name == "custom_metric" for c in criteria.criteria)
    
    def test_remove_criterion(self):
        """Test removing criterion"""
        criteria = AcceptanceCriteria()
        
        initial_count = len(criteria.criteria)
        success = criteria.remove_criterion("sharpe_ratio")
        
        assert success is True
    
    def test_criterion_evaluation(self):
        """Test individual criterion evaluation"""
        criterion = Criterion(
            name="test",
            criterion_type=CriterionType.PERFORMANCE,
            metric="value",
            operator=ComparisonOperator.GREATER_THAN,
            threshold=1.0
        )
        
        assert criterion.evaluate(1.5) is True
        assert criterion.evaluate(0.5) is False
        assert criterion.evaluate(1.0) is False  # GREATER_THAN excludes equality
        
        # Test GREATER_EQUAL
        criterion_equal = Criterion(
            name="test_equal",
            criterion_type=CriterionType.PERFORMANCE,
            metric="value",
            operator=ComparisonOperator.GREATER_EQUAL,
            threshold=1.0
        )
        assert criterion_equal.evaluate(1.0) is True


class TestAcceptancePolicy:
    """Tests for acceptance policy"""
    
    def test_default_policies(self):
        """Test default policies"""
        policy = AcceptancePolicy()
        
        assert "staging" in policy.policies
        assert "production" in policy.policies
        assert "paper_trading" in policy.policies
    
    def test_get_policy(self):
        """Test getting policy by name"""
        policy = AcceptancePolicy()
        
        staging = policy.get_policy("staging")
        assert staging is not None
        assert isinstance(staging, AcceptanceCriteria)
    
    def test_evaluate_with_policy(self):
        """Test evaluation with policy"""
        policy = AcceptancePolicy()
        
        metrics = {
            "sharpe_ratio": 1.5,
            "total_return": 0.10,
            "max_drawdown": 0.08,
            "win_rate": 0.55,
            "p_value": 0.02,
            "consistency_ratio": 0.75,
            "calibration_error": 0.05
        }
        
        result = policy.evaluate(metrics, "production")
        
        assert isinstance(result, AcceptanceResult)


class TestDeploymentReport:
    """Tests for deployment report"""
    
    def test_create_report(self):
        """Test report creation"""
        report = DeploymentReport(
            report_id="test_001",
            timestamp=datetime.now(),
            strategy_id="strategy_1",
            version="1.0.0",
            environment="production",
            overall_status="APPROVED",
            weighted_score=0.85,
            validation_duration=120.5,
            stage_results={
                "backtest": {"status": "passed", "metrics": {"sharpe": 1.5}}
            },
            acceptance_results={"overall_passed": True, "weighted_score": 0.85},
            comparison={},
            recommendations=["Looks good"]
        )
        
        assert report.report_id == "test_001"
        assert report.overall_status == "APPROVED"
    
    def test_to_markdown(self):
        """Test markdown conversion"""
        report = DeploymentReport(
            report_id="test_002",
            timestamp=datetime.now(),
            strategy_id="strategy_2",
            version="2.0.0",
            environment="staging",
            overall_status="APPROVED",
            weighted_score=0.90,
            validation_duration=60.0,
            stage_results={},
            acceptance_results={"overall_passed": True, "weighted_score": 0.90, "results": {"sharpe_ratio": True}},
            comparison={},
            recommendations=["Promote to production"]
        )
        
        md = report.to_markdown()
        
        assert "# Deployment Report" in md
        assert "strategy_2" in md
        assert "Promote to production" in md


class TestReportGenerator:
    """Tests for report generator"""
    
    def test_generate_report(self, tmp_path):
        """Test report generation"""
        generator = ReportGenerator(db_path=str(tmp_path / "reports.db"))
        
        # Create mock validation results
        results = [
            ValidationResult(
                stage=ValidationStage.BACKTEST,
                status=ValidationStatus.PASSED,
                start_time=datetime.now(),
                duration_seconds=30.0,
                metrics={"sharpe": 1.5, "drawdown": 0.10}
            )
        ]
        
        # Create mock acceptance result
        acceptance = AcceptanceResult(
            criteria=[],
            results={"sharpe_ratio": True},
            scores={"sharpe_ratio": 1.0},
            weighted_score=0.85,
            overall_passed=True,
            failed_criteria=[]
        )
        
        report = generator.generate_report(
            strategy_id="test_strategy",
            version="1.0.0",
            environment="production",
            validation_results=results,
            acceptance_result=acceptance
        )
        
        assert report.strategy_id == "test_strategy"
        assert report.overall_status == "APPROVED"
    
    def test_export_report(self, tmp_path):
        """Test report export"""
        generator = ReportGenerator(db_path=str(tmp_path / "reports.db"))
        
        # Create a report
        report = DeploymentReport(
            report_id="export_test",
            timestamp=datetime.now(),
            strategy_id="strategy_export",
            version="1.0.0",
            environment="production",
            overall_status="APPROVED",
            weighted_score=0.90,
            validation_duration=60.0,
            stage_results={},
            acceptance_results={"overall_passed": True, "weighted_score": 0.90, "results": {}},
            comparison={},
            recommendations=[]
        )
        
        generator.reports[report.report_id] = report
        
        # Export as markdown
        path = generator.export_report(report.report_id, ReportFormat.MARKDOWN)
        
        assert path.endswith(".md")
    
    def test_get_statistics(self, tmp_path):
        """Test report statistics"""
        generator = ReportGenerator(db_path=str(tmp_path / "reports.db"))
        
        stats = generator.get_report_statistics()
        
        assert "total_reports" in stats
        assert "by_status" in stats


class TestValidationConfig:
    """Tests for validation config"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = ValidationConfig()
        
        assert config.unit_test_timeout == 300
        assert config.integration_test_enabled is True
        assert config.backtest_days == 90
        assert config.walk_forward_window == 30
        assert len(config.stress_test_scenarios) > 0
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ValidationConfig(
            unit_test_timeout=600,
            backtest_days=180,
            stress_test_scenarios=["custom_scenario"]
        )
        
        assert config.unit_test_timeout == 600
        assert config.backtest_days == 180
        assert config.stress_test_scenarios == ["custom_scenario"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
