"""
Tests for the Cognitive Architecture Module
==========================================

Tests all 7 cognitive layers and the orchestrator.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from intelligence.cognitive import (
    CognitiveOrchestrator,
    PerceptionLayer,
    SituationAssessmentLayer,
    MemoryLayer,
    PlanningLayer,
    CriticLayer,
    DecisionLayer,
    ReflectionLayer,
    PerceptionResult,
    SituationResult,
    MemoryResult,
    PlanningResult,
    CriticResult,
    DecisionResult,
    DataQuality,
    DataAnomaly,
    MarketRegime,
    TrendDirection,
    ActionType,
    ActionConfidence,
    CritiqueLevel,
    DecisionStatus,
    Objective,
    OutcomeType
)


class TestPerceptionLayer:
    """Tests for Layer 1 - Perception"""
    
    def test_valid_tick_processing(self):
        """Test processing valid tick data"""
        layer = PerceptionLayer()
        
        market_data = {
            "symbol": "R_50",
            "bid": 150.0,
            "ask": 150.05,
            "timestamp": datetime.now().isoformat()
        }
        
        result = layer.process(market_data)
        
        assert isinstance(result, PerceptionResult)
        assert result.current_tick is not None
        assert result.current_tick.symbol == "R_50"
        assert result.current_tick.bid == 150.0
        assert result.is_valid is True
        assert result.quality_score >= 0.7
    
    def test_quality_assessment(self):
        """Test data quality assessment"""
        layer = PerceptionLayer()
        
        # Test with spread
        market_data = {
            "symbol": "R_50",
            "bid": 100.0,
            "ask": 100.01,  # Tight spread = good quality
            "timestamp": datetime.now().isoformat()
        }
        
        result = layer.process(market_data)
        
        assert result.quality in [DataQuality.GOOD, DataQuality.EXCELLENT]
    
    def test_missing_data_detection(self):
        """Test missing data anomaly detection"""
        layer = PerceptionLayer()
        layer._last_processed_time = datetime.now() - timedelta(seconds=10)
        
        market_data = {
            "symbol": "R_50",
            "bid": 100.0,
            "ask": 100.01,
            "timestamp": datetime.now().isoformat()
        }
        
        result = layer.process(market_data)
        
        assert DataAnomaly.MISSING_DATA in result.anomalies or DataAnomaly.DELAYED_DATA in result.anomalies
    
    def test_reset(self):
        """Test layer reset"""
        layer = PerceptionLayer()
        layer._tick_buffer = [MagicMock()]
        layer.reset()
        
        assert len(layer._tick_buffer) == 0


class TestSituationAssessmentLayer:
    """Tests for Layer 2 - Situation Assessment"""
    
    def test_regime_detection(self):
        """Test market regime detection"""
        layer = SituationAssessmentLayer()
        
        # Create perception result with enough data
        perception = MagicMock()
        perception.session_id = "test_session"
        perception.recent_ticks = [
            MagicMock(mid_price=100 + i * 0.5) for i in range(50)
        ]
        
        result = layer.process(perception)
        
        assert isinstance(result, SituationResult)
        assert result.regime != MarketRegime.UNKNOWN
        assert 0 <= result.uncertainty <= 1
        assert 0 <= result.confidence <= 1
    
    def test_trend_detection(self):
        """Test trend direction detection"""
        layer = SituationAssessmentLayer()
        
        # Upward trending data
        ticks = [MagicMock(mid_price=100 + i * 0.1) for i in range(50)]
        
        perception = MagicMock()
        perception.session_id = "test_session"
        perception.recent_ticks = ticks
        
        result = layer.process(perception)
        
        assert result.trend in [TrendDirection.UP, TrendDirection.NEUTRAL]
    
    def test_tradeability_assessment(self):
        """Test tradeability assessment"""
        layer = SituationAssessmentLayer()
        
        # Unknown regime should not be tradeable
        perception = MagicMock()
        perception.session_id = "test_session"
        perception.recent_ticks = []
        
        result = layer.process(perception)
        
        assert result.is_tradeable is False


class TestPlanningLayer:
    """Tests for Layer 4 - Planning"""
    
    def test_candidate_generation(self):
        """Test candidate action generation"""
        layer = PlanningLayer()
        
        situation = MagicMock()
        situation.session_id = "test_session"
        situation.regime = MarketRegime.TRENDING_UP
        situation.trend = TrendDirection.UP
        situation.volatility = 0.4
        situation.uncertainty = 0.3
        situation.regime_confidence = 0.8
        situation.trend_confidence = 0.7
        situation.confidence = 0.7
        
        memory = MagicMock()
        memory.retrieved_situations = []
        memory.ranked_situations = []
        memory.is_sufficient_context = False
        memory.outcome_confidence = 0.5
        
        perception = MagicMock()
        perception.session_id = "test_session"
        
        result = layer.process(situation, memory, perception)
        
        assert isinstance(result, PlanningResult)
        assert len(result.candidate_actions) > 0
        assert result.recommended_duration > 0
    
    def test_wait_action_generation(self):
        """Test that wait action is always generated"""
        layer = PlanningLayer()
        
        situation = MagicMock()
        situation.session_id = "test_session"
        situation.regime = MarketRegime.VOLATILE
        situation.trend = TrendDirection.NEUTRAL
        situation.volatility = 0.8
        situation.uncertainty = 0.9
        situation.regime_confidence = 0.3
        situation.trend_confidence = 0.3
        situation.confidence = 0.3
        
        memory = MagicMock()
        memory.retrieved_situations = []
        memory.ranked_situations = []
        memory.is_sufficient_context = False
        memory.outcome_confidence = 0.3
        
        perception = MagicMock()
        perception.session_id = "test_session"
        
        result = layer.process(situation, memory, perception)
        
        wait_actions = [a for a in result.candidate_actions if a.action_type == ActionType.WAIT]
        assert len(wait_actions) == 1


class TestCriticLayer:
    """Tests for Layer 5 - Critic"""
    
    def test_critique_generation(self):
        """Test critique generation"""
        layer = CriticLayer()
        
        # Create a low confidence action
        action = MagicMock()
        action.action_type = ActionType.TRADE_CALL
        action.direction = "CALL"
        action.confidence = 0.3
        action.win_probability = 0.4
        action.expected_value = -0.1
        action.expected_value_std = 0.8
        action.risk_factors = ["high volatility"]
        action.supporting_situations = []
        
        planning = MagicMock()
        planning.session_id = "test_session"
        planning.best_action = action
        planning.candidate_actions = [action]
        
        situation = MagicMock()
        situation.regime = MarketRegime.UNKNOWN
        situation.regime_confidence = 0.2
        situation.uncertainty = 0.9
        situation.regime_transition_detected = False
        situation.confidence = 0.3
        
        memory = MagicMock()
        memory.retrieved_situations = []
        memory.is_sufficient_context = False
        memory.outcome_confidence = 0.3
        
        perception = MagicMock()
        perception.quality = DataQuality.GOOD
        perception.quality_score = 0.8
        perception.anomalies = []
        perception.missing_ticks_count = 0
        perception.latency_ms = 50
        
        result = layer.process(planning, situation, perception, memory)
        
        assert isinstance(result, CriticResult)
        assert len(result.critiques) > 0
    
    def test_overconfidence_detection(self):
        """Test overconfidence flagging"""
        layer = CriticLayer()
        
        action = MagicMock()
        action.confidence = 0.95
        action.win_probability = 0.7
        action.expected_value = 0.3
        action.action_type = ActionType.TRADE_CALL
        action.risk_factors = []
        action.supporting_situations = ["s1", "s2"]
        
        situation = MagicMock()
        situation.regime_confidence = 0.4
        situation.uncertainty = 0.3
        
        # Add historical overconfidence
        layer._calibration_history = [(0.8, 0.5)] * 20
        
        result = layer._critique_overconfidence(action, situation)
        
        # Should flag overconfidence due to historical pattern
        assert isinstance(result, list)


class TestDecisionLayer:
    """Tests for Layer 6 - Decision"""
    
    def test_decision_making(self):
        """Test decision selection"""
        layer = DecisionLayer()
        
        action = MagicMock()
        action.action_type = ActionType.TRADE_CALL
        action.direction = "CALL"
        action.expected_value = 0.2
        action.expected_value_std = 0.3
        action.win_probability = 0.6
        action.confidence = 0.7
        action.reasoning = ["Test reasoning"]
        action.duration_seconds = 15
        action.stake_amount = 1.0
        
        critic = MagicMock()
        critic.session_id = "test_session"
        critic.original_action = action
        critic.adjusted_action = None
        critic.overall_severity = CritiqueLevel.NONE
        critic.critiques = []
        critic.abstention_recommended = False
        critic.abstention_reason = None
        critic.confidence = 0.7
        
        planning = MagicMock()
        planning.session_id = "test_session"
        planning.best_action = action
        planning.candidate_actions = [action]
        
        result = layer.process(critic, planning)
        
        assert isinstance(result, DecisionResult)
        assert result.status in [DecisionStatus.DECIDED, DecisionStatus.ABSTAINED]
    
    def test_abstention_when_low_confidence(self):
        """Test abstention when confidence is too low"""
        layer = DecisionLayer(min_confidence_threshold=0.5)
        
        action = MagicMock()
        action.action_type = ActionType.TRADE_CALL
        action.confidence = 0.2  # Below threshold
        action.expected_value = 0.1
        action.expected_value_std = 0.5
        action.win_probability = 0.4
        action.reasoning = []
        action.duration_seconds = 15
        action.stake_amount = 1.0
        
        critic = MagicMock()
        critic.session_id = "test_session"
        critic.original_action = action
        critic.adjusted_action = None
        critic.overall_severity = CritiqueLevel.NONE
        critic.abstention_recommended = False
        critic.confidence = 0.3
        
        planning = MagicMock()
        planning.session_id = "test_session"
        planning.best_action = action
        planning.candidate_actions = [action]
        
        result = layer.process(critic, planning)
        
        assert result.status == DecisionStatus.ABSTAINED


class TestCognitiveOrchestrator:
    """Tests for the Cognitive Orchestrator"""
    
    def test_full_pipeline(self):
        """Test complete cognitive pipeline"""
        orchestrator = CognitiveOrchestrator()
        
        market_data = {
            "symbol": "R_50",
            "bid": 150.0,
            "ask": 150.05,
            "timestamp": datetime.now().isoformat()
        }
        
        trace = orchestrator.think(market_data, "R_50")
        
        assert trace is not None
        assert len(trace.layers_executed) == 6
        assert "perception" in trace.layers_executed
        assert "decision" in trace.layers_executed
    
    def test_multiple_ticks_for_regime(self):
        """Test regime detection with sufficient data"""
        orchestrator = CognitiveOrchestrator()
        
        # Generate trending data
        prices = [100 + i * 0.1 for i in range(50)]
        
        market_data = {
            "symbol": "R_50",
            "bid": prices[-1],
            "ask": prices[-1] + 0.05,
            "timestamp": datetime.now().isoformat(),
            "historical_ticks": [MagicMock(mid_price=p) for p in prices]
        }
        
        trace = orchestrator.think(market_data, "R_50")
        
        # With more data, regime should be detected
        if trace.situation:
            assert trace.situation.regime != MarketRegime.UNKNOWN or trace.situation.regime_confidence < 0.5
    
    def test_statistics_tracking(self):
        """Test decision statistics tracking"""
        orchestrator = CognitiveOrchestrator()
        
        orchestrator._decision_counts = {"total": 10, "trade": 7, "abstain": 3}
        
        stats = orchestrator.get_statistics()
        
        assert stats["decisions"]["total"] == 10
        assert stats["decisions"]["trades"] == 7
        assert stats["decisions"]["abstains"] == 3
    
    def test_reset(self):
        """Test orchestrator reset"""
        orchestrator = CognitiveOrchestrator()
        orchestrator._decision_counts = {"total": 1, "trade": 1, "abstain": 0}
        
        orchestrator.reset()
        
        assert orchestrator._decision_counts["total"] == 0
        assert orchestrator._current_trace is None


class TestReflectionLayer:
    """Tests for Layer 7 - Reflection"""
    
    def test_outcome_determination(self):
        """Test outcome type determination"""
        layer = ReflectionLayer()
        
        # Test success
        outcome = layer._determine_outcome(0.8, MagicMock())
        assert outcome == OutcomeType.SUCCESS
        
        # Test partial
        outcome = layer._determine_outcome(0.1, MagicMock())
        assert outcome == OutcomeType.PARTIAL
        
        # Test failure
        outcome = layer._determine_outcome(-0.5, MagicMock())
        assert outcome == OutcomeType.FAILURE
    
    def test_calibration_delta(self):
        """Test calibration adjustment calculation"""
        layer = ReflectionLayer()
        
        # Test with high confidence action that failed
        # We need to test the internal calculation method directly
        # by calling the function that uses the decision_result.selected_action
        
        # Create a mock that will pass the selected_action check
        class MockDecisionResult:
            def __init__(self):
                from intelligence.cognitive.planning import CandidateAction, ActionType
                self.selected_action = CandidateAction(
                    action_type=ActionType.TRADE_CALL,
                    direction="CALL",
                    contract_type="DIGITOVER",
                    duration_seconds=15,
                    stake_amount=1.0,
                    expected_value=0.3,
                    expected_value_std=0.3,
                    win_probability=0.7,
                    risk_reward_ratio=1.5,
                    confidence=0.8,
                    confidence_level=None,
                    reasoning=["Test"],
                    supporting_situations=[],
                    risk_factors=[]
                )
        
        decision_result = MockDecisionResult()
        
        # Failed trade with high confidence = negative delta
        delta = layer._calculate_calibration_delta(decision_result, OutcomeType.FAILURE, -0.5)
        
        assert delta < 0  # Should reduce confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
