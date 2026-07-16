"""
Tests for Decision Science Module
================================
"""

import pytest
import time


class TestPrediction:
    """Tests for Prediction class"""
    
    def test_prediction_creation(self):
        """Test prediction creation"""
        from decision_science.core import Prediction
        
        pred = Prediction(
            prediction_id="pred_1",
            opportunity_id="opp_1",
            predicted_direction="up",
            predicted_magnitude=0.05,
            predicted_confidence=0.8,
            predicted_probability=0.7,
        )
        
        assert pred.predicted_direction == "up"
        assert pred.predicted_confidence == 0.8
        assert pred.predicted_probability == 0.7
    
    def test_prediction_to_dict(self):
        """Test prediction serialization"""
        from decision_science.core import Prediction
        
        pred = Prediction(
            prediction_id="pred_1",
            opportunity_id="opp_1",
            predicted_direction="up",
            predicted_magnitude=0.05,
            predicted_confidence=0.8,
            predicted_probability=0.7,
        )
        
        data = pred.to_dict()
        assert data["prediction_id"] == "pred_1"
        assert data["predicted_direction"] == "up"


class TestDecision:
    """Tests for Decision class"""
    
    def test_decision_creation(self):
        """Test decision creation"""
        from decision_science.core import Decision, DecisionAction
        
        decision = Decision(
            decision_id="dec_1",
            opportunity_id="opp_1",
            action=DecisionAction.EXECUTE,
            reason="High confidence",
            confidence=0.85,
            expected_value=0.02,
            risk_adjusted_score=0.7,
            opportunity_cost=0.02,
            capital_required=10000,
        )
        
        assert decision.action == DecisionAction.EXECUTE
        assert decision.confidence == 0.85
        assert decision.expected_value == 0.02


class TestOpportunity:
    """Tests for Opportunity class"""
    
    def test_opportunity_creation(self):
        """Test opportunity creation"""
        from decision_science.core import Opportunity
        
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={"price": 50000, "volatility": 0.02},
        )
        
        assert opp.symbol == "BTC/USD"
        assert opp.market_data["price"] == 50000
        assert not opp.is_resolved()
    
    def test_opportunity_resolution(self):
        """Test opportunity resolution"""
        from decision_science.core import Opportunity
        
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={},
        )
        
        opp.resolved_at = time.time()
        opp.actual_pnl = 100
        
        assert opp.is_resolved()
        assert opp.actual_pnl == 100


class TestOpportunityAnalyzer:
    """Tests for OpportunityAnalyzer"""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        from decision_science.core import OpportunityAnalyzer
        
        analyzer = OpportunityAnalyzer()
        
        assert analyzer.min_confidence == 0.6
        assert analyzer.min_expected_value == 0.01
        assert analyzer.min_probability == 0.55
    
    def test_prediction_generation(self):
        """Test prediction generation"""
        from decision_science.core import OpportunityAnalyzer, Opportunity
        
        analyzer = OpportunityAnalyzer()
        
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={"price": 50000},
        )
        
        # Mock model function
        def mock_model(o):
            return {
                "direction": "up",
                "magnitude": 0.05,
                "confidence": 0.8,
                "probability": 0.7,
                "features": ["trend", "volume"],
                "model_version": "v1.0",
            }
        
        prediction = analyzer.predict(opp, mock_model)
        
        assert prediction.predicted_direction == "up"
        assert prediction.predicted_confidence == 0.8
        assert prediction.predicted_probability == 0.7
    
    def test_decision_making(self):
        """Test decision making"""
        from decision_science.core import OpportunityAnalyzer, Opportunity, DecisionAction
        
        analyzer = OpportunityAnalyzer()
        
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={"price": 50000, "volatility": 0.02},
        )
        
        # Add prediction
        from decision_science.core import Prediction
        opp.prediction = Prediction(
            prediction_id="pred_1",
            opportunity_id="opp_1",
            predicted_direction="up",
            predicted_magnitude=0.05,
            predicted_confidence=0.8,
            predicted_probability=0.7,
        )
        
        decision = analyzer.decide(opp)
        
        assert decision is not None
        assert decision.action in [DecisionAction.EXECUTE, DecisionAction.REJECT, DecisionAction.WAIT]
    
    def test_expected_value_calculation(self):
        """Test EV calculation"""
        from decision_science.core import OpportunityAnalyzer, Opportunity, Prediction
        
        analyzer = OpportunityAnalyzer()
        
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={"price": 50000},
        )
        
        opp.prediction = Prediction(
            prediction_id="pred_1",
            opportunity_id="opp_1",
            predicted_direction="up",
            predicted_magnitude=0.05,
            predicted_confidence=0.8,
            predicted_probability=0.7,
        )
        
        ev = analyzer._calculate_expected_value(opp)
        assert ev > 0  # Should be positive with 70% prob and 5% magnitude


class TestDecisionQualityScore:
    """Tests for DecisionQualityScore"""
    
    def test_quality_score_creation(self):
        """Test quality score creation"""
        from decision_science.core import DecisionQualityScore
        
        score = DecisionQualityScore(
            score_id="qs_1",
            timestamp=time.time(),
            overall_score=0.75,
            prediction_quality=0.8,
            decision_quality=0.7,
            expected_value_score=0.75,
            capital_efficiency_score=0.7,
            opportunity_cost_score=0.8,
            abstention_quality_score=0.6,
            confidence_calibration_score=0.75,
            regret_score=0.2,
            total_opportunities=100,
            executed_trades=50,
            rejected_trades=40,
            waited_trades=10,
            total_pnl=500,
            sharpe_ratio=1.2,
            max_drawdown=0.1,
            win_rate=0.55,
            avg_win=100,
            avg_loss=50,
            profit_factor=1.5,
        )
        
        assert score.overall_score == 0.75
        assert score.total_opportunities == 100
        assert score.win_rate == 0.55


class TestThresholdOptimizer:
    """Tests for ThresholdOptimizer"""
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        from decision_science.core import OpportunityAnalyzer, ThresholdOptimizer
        
        analyzer = OpportunityAnalyzer()
        optimizer = ThresholdOptimizer(analyzer)
        
        assert optimizer.analyzer is not None
    
    def test_threshold_mutation(self):
        """Test threshold mutation"""
        from decision_science.core import OpportunityAnalyzer, ThresholdOptimizer
        
        analyzer = OpportunityAnalyzer()
        optimizer = ThresholdOptimizer(analyzer)
        
        current = optimizer._get_current_thresholds()
        mutated = optimizer._mutate_thresholds(current)
        
        # Should have same keys
        assert set(mutated.keys()) == set(current.keys())


class TestTradeExplainer:
    """Tests for TradeExplainer"""
    
    def test_explainer_initialization(self):
        """Test explainer initialization"""
        from decision_science.core import TradeExplainer
        
        explainer = TradeExplainer()
        assert explainer is not None


class TestMetrics:
    """Tests for metric classes"""
    
    def test_prediction_quality(self):
        """Test PredictionQuality"""
        from decision_science.metrics import PredictionQuality
        
        pq = PredictionQuality(
            prediction_id="pred_1",
            predicted_value=0.05,
            actual_value=0.04,
        ).calculate()
        
        # Direction accuracy should be correct (positive values)
        assert pq.precision == 1.0  # Both are positive, so same direction
    
    def test_expected_value(self):
        """Test ExpectedValue"""
        from decision_science.metrics import ExpectedValue
        
        ev = ExpectedValue(
            opportunity_id="opp_1",
            probability=0.7,
            win_amount=100,
            loss_amount=50,
        ).calculate()
        
        assert ev.expected_value == 70 - 15  # 0.7 * 100 - 0.3 * 50
        assert ev.risk_adjusted_ev < ev.expected_value  # Risk penalty applied
    
    def test_expected_value_from_prediction(self):
        """Test EV from prediction"""
        from decision_science.metrics import ExpectedValue
        
        ev = ExpectedValue.from_prediction(
            opportunity_id="opp_1",
            predicted_probability=0.75,
            predicted_magnitude=0.05,
        )
        
        assert ev.probability == 0.75
        assert ev.win_amount == 0.05
    
    def test_capital_efficiency(self):
        """Test CapitalEfficiency"""
        from decision_science.metrics import CapitalEfficiency
        
        ce = CapitalEfficiency(
            opportunity_id="opp_1",
            capital_required=10000,
            expected_return=500,
            actual_return=450,
            holding_period_seconds=3600,
        ).calculate()
        
        assert ce.return_on_capital == 0.05  # 500 / 10000
        assert ce.annualized_return > ce.return_on_capital
    
    def test_confidence_calibration(self):
        """Test ConfidenceCalibration"""
        from decision_science.metrics import ConfidenceCalibration
        
        cc = ConfidenceCalibration(
            opportunity_id="opp_1",
            confidence=0.8,
            was_correct=True,
        ).calculate()
        
        assert abs(cc.calibration_error - 0.2) < 0.001  # |0.8 - 1.0|
    
    def test_regret_score(self):
        """Test RegretScore"""
        from decision_science.metrics import RegretScore
        
        rs = RegretScore(
            opportunity_id="opp_1",
            action="execute",
            actual_return=50,
            best_possible_return=100,
            best_achieved_return=75,
        ).calculate()
        
        assert rs.opportunity_regret == 50  # 100 - 50
        assert rs.execution_regret == 25  # 75 - 50
        assert rs.total_regret == 75


class TestIntegration:
    """Integration tests"""
    
    def test_full_analysis_flow(self):
        """Test complete analysis flow"""
        from decision_science.core import (
            OpportunityAnalyzer,
            Opportunity,
            DecisionAction,
        )
        
        analyzer = OpportunityAnalyzer()
        
        # Create opportunity
        opp = Opportunity(
            opportunity_id="opp_1",
            symbol="BTC/USD",
            market_data={"price": 50000, "volatility": 0.02},
        )
        
        # Mock model
        def mock_model(o):
            return {
                "direction": "up",
                "magnitude": 0.05,
                "confidence": 0.85,
                "probability": 0.75,
                "features": ["trend"],
                "model_version": "v1.0",
            }
        
        # Analyze
        analyzer.analyze(opp, mock_model)
        
        assert opp.prediction is not None
        assert opp.decision is not None
        assert opp.metrics is not None
    
    def test_quality_score_with_history(self):
        """Test quality score with historical data"""
        from decision_science.core import (
            OpportunityAnalyzer,
            Opportunity,
            DecisionAction,
        )
        
        analyzer = OpportunityAnalyzer()
        
        # Add some resolved opportunities
        for i in range(10):
            opp = Opportunity(
                opportunity_id=f"opp_{i}",
                symbol="BTC/USD",
                market_data={"price": 50000},
            )
            
            # Simulate analysis
            from decision_science.core import Prediction
            opp.prediction = Prediction(
                prediction_id=f"pred_{i}",
                opportunity_id=f"opp_{i}",
                predicted_direction="up" if i % 2 == 0 else "down",
                predicted_magnitude=0.05,
                predicted_confidence=0.7 + (i % 3) * 0.1,
                predicted_probability=0.6 + (i % 4) * 0.1,
            )
            
            opp.decision = analyzer.decide(opp)
            
            # Resolve
            opp.actual_direction = opp.prediction.predicted_direction
            opp.actual_magnitude = 0.04
            opp.actual_pnl = 100 if i % 2 == 0 else -50
            opp.resolved_at = time.time()
            
            analyzer._opportunity_history.append(opp)
        
        # Calculate quality score
        score = analyzer.calculate_decision_quality_score()
        
        assert score.total_opportunities == 10
        assert 0 <= score.overall_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
