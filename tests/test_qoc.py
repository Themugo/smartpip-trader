"""
Tests for Quant Operations Center
================================
"""

import pytest
import time


class TestControlRoom:
    """Tests for Control Room"""
    
    def test_control_room_creation(self):
        """Test control room creation"""
        from qoc.control_room import ControlRoom
        
        cr = ControlRoom()
        
        assert cr is not None
        assert len(cr._components) == 0
    
    def test_register_component(self):
        """Test registering components"""
        from qoc.control_room import ControlRoom, ComponentStatus
        
        cr = ControlRoom()
        cr.register_component("test_component")
        
        assert "test_component" in cr._components
    
    def test_update_component(self):
        """Test updating component status"""
        from qoc.control_room import ControlRoom, ComponentStatus
        
        cr = ControlRoom()
        cr.register_component("test_component")
        cr.update_component(
            "test_component",
            ComponentStatus.HEALTHY,
            score=0.9,
        )
        
        comp = cr.get_component("test_component")
        assert comp.status == ComponentStatus.HEALTHY
        assert comp.score == 0.9
    
    def test_raise_alert(self):
        """Test raising alerts"""
        from qoc.control_room import ControlRoom
        
        cr = ControlRoom()
        alert = cr.raise_alert(
            severity="high",
            component="test",
            title="Test Alert",
            description="Test description",
        )
        
        assert alert.severity == "high"
        assert not alert.resolved
    
    def test_health_score_calculation(self):
        """Test health score calculation"""
        from qoc.control_room import ControlRoom, ComponentStatus
        
        cr = ControlRoom()
        cr.register_component("database")
        cr.update_component("database", ComponentStatus.HEALTHY, score=0.95)
        
        health = cr.calculate_health_score()
        
        assert 0 <= health.overall <= 1
        assert health.system > 0
    
    def test_dashboard_generation(self):
        """Test dashboard generation"""
        from qoc.control_room import ControlRoom, ComponentStatus
        
        cr = ControlRoom()
        cr.register_component("api")
        cr.update_component("api", ComponentStatus.HEALTHY, score=0.9)
        
        dashboard = cr.get_dashboard()
        
        assert "overall_status" in dashboard
        assert "health_score" in dashboard


class TestDailyOperations:
    """Tests for Daily Operations"""
    
    def test_morning_check(self):
        """Test morning check generation"""
        from qoc.daily_ops import DailyOperations
        from qoc.control_room import ControlRoom
        
        cr = ControlRoom()
        ops = DailyOperations(cr)
        
        report = ops.generate_morning_check()
        
        assert report.report_type == "Morning System Check"
        assert "health_score" in report.metrics


class TestContinuousValidation:
    """Tests for Continuous Validation"""
    
    def test_validation_creation(self):
        """Test validation system creation"""
        from qoc.continuous_validation import ContinuousValidation
        
        cv = ContinuousValidation()
        
        assert cv is not None
    
    def test_run_checks(self):
        """Test running validation checks"""
        from qoc.continuous_validation import ContinuousValidation
        
        cv = ContinuousValidation()
        results = cv.run_all_checks()
        
        assert isinstance(results, dict)
    
    def test_validation_summary(self):
        """Test validation summary"""
        from qoc.continuous_validation import ContinuousValidation
        
        cv = ContinuousValidation()
        summary = cv.get_validation_summary()
        
        assert "passed" in summary
        assert "total" in summary


class TestResearchPipeline:
    """Tests for Research Pipeline"""
    
    def test_create_hypothesis(self):
        """Test hypothesis creation"""
        from qoc.research_pipeline import ResearchPipeline
        
        pipeline = ResearchPipeline()
        hypothesis = pipeline.create_hypothesis(
            title="Test Hypothesis",
            description="Test description",
            created_by="test",
        )
        
        assert hypothesis.title == "Test Hypothesis"
    
    def test_register_candidate(self):
        """Test candidate registration"""
        from qoc.research_pipeline import ResearchPipeline
        
        pipeline = ResearchPipeline()
        candidate = pipeline.register_candidate(
            name="Test Strategy",
            strategy_type="momentum",
            metrics={"sharpe_ratio": 1.5, "max_drawdown": 0.1},
        )
        
        assert candidate.name == "Test Strategy"
        assert candidate.sharpe_ratio == 1.5
    
    def test_rank_candidates(self):
        """Test candidate ranking"""
        from qoc.research_pipeline import ResearchPipeline
        
        pipeline = ResearchPipeline()
        pipeline.register_candidate(
            name="Strategy A",
            strategy_type="momentum",
            metrics={"sharpe_ratio": 1.5},
        )
        pipeline.register_candidate(
            name="Strategy B",
            strategy_type="mean_reversion",
            metrics={"sharpe_ratio": 2.0},
        )
        
        ranked = pipeline.rank_candidates()
        
        assert len(ranked) == 2
        assert ranked[0].name == "Strategy B"


class TestKPIs:
    """Tests for Operational KPIs"""
    
    def test_kpi_recording(self):
        """Test recording KPI values"""
        from qoc.kpis import OperationalKPIs
        
        kpis = OperationalKPIs()
        kpis.record("test_metric", 0.95)
        
        assert kpis.get_current("test_metric") == 0.95
    
    def test_kpi_average(self):
        """Test KPI average calculation"""
        from qoc.kpis import OperationalKPIs
        
        kpis = OperationalKPIs()
        kpis.record("test_metric", 0.9)
        kpis.record("test_metric", 0.95)
        kpis.record("test_metric", 1.0)
        
        avg = kpis.get_average("test_metric")
        assert abs(avg - 0.95) < 0.01


class TestIncidentManager:
    """Tests for Incident Management"""
    
    def test_create_incident(self):
        """Test incident creation"""
        from qoc.incident import IncidentManager, IncidentSeverity
        
        manager = IncidentManager()
        incident = manager.create_incident(
            title="Test Incident",
            description="Test description",
            severity=IncidentSeverity.HIGH,
            source="test",
        )
        
        assert incident.title == "Test Incident"
        assert incident.severity == IncidentSeverity.HIGH
    
    def test_resolve_incident(self):
        """Test incident resolution"""
        from qoc.incident import IncidentManager, IncidentSeverity
        
        manager = IncidentManager()
        incident = manager.create_incident(
            title="Test",
            description="Test",
            severity=IncidentSeverity.MEDIUM,
            source="test",
        )
        
        manager.resolve(incident.id, "Fixed", "Restarted service")
        
        assert incident.status.value == "resolved"


class TestGoNoGoBoard:
    """Tests for Go/No-Go Board"""
    
    def test_board_creation(self):
        """Test board creation"""
        from qoc.go_no_go import GoNoGoBoard
        
        board = GoNoGoBoard()
        
        assert board is not None
        assert len(board._gates) > 0
    
    def test_evaluate_all(self):
        """Test evaluating all gates"""
        from qoc.go_no_go import GoNoGoBoard
        
        board = GoNoGoBoard()
        score = board.evaluate_all()
        
        assert score.overall_score >= 0
        assert score.overall_score <= 1
    
    def test_deployment_report(self):
        """Test deployment report generation"""
        from qoc.go_no_go import GoNoGoBoard
        
        board = GoNoGoBoard()
        report = board.generate_deployment_report()
        
        assert "decision" in report
        assert "scores" in report
        assert "production_checklist" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
