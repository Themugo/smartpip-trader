"""
Tests for Institutional Risk Intelligence
==========================================
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from risk.intelligence import (
    RiskIntelligenceEngine,
    RiskLimits,
    DrawdownAnalyzer,
    ExpectedShortfallCalculator,
    CapitalAllocator,
    AllocationMethod,
    ConcentrationAnalyzer,
    CircuitBreaker,
    KillSwitch,
    RecoveryManager,
    RiskScoreCalculator,
    ScenarioAnalyzer,
    SensitivityAnalyzer
)


class TestRiskIntelligenceEngine:
    """Tests for the core risk engine"""
    
    def test_initialization(self):
        """Test engine initialization"""
        engine = RiskIntelligenceEngine(
            initial_capital=100000.0,
            limits=RiskLimits()
        )
        
        assert engine.initial_capital == 100000.0
        assert engine._portfolio_value == 100000.0
        assert engine._system_state.value == "normal"
    
    def test_add_position(self):
        """Test adding a position"""
        engine = RiskIntelligenceEngine(initial_capital=100000.0)
        
        accepted, reason = engine.add_position(
            symbol="R_50",
            direction="LONG",
            size=100,
            entry_price=150.0,
            confidence=0.8
        )
        
        # Position may be rejected due to HHI, but shouldn't be due to size
        if not accepted:
            assert "HHI" in reason or "concentration" in reason.lower() or "exceeds" in reason
        else:
            assert len(engine._positions) == 1
    
    def test_reject_low_confidence(self):
        """Test rejection of low confidence trades"""
        engine = RiskIntelligenceEngine(
            initial_capital=100000.0,
            limits=RiskLimits(min_confidence_to_trade=0.7)
        )
        
        accepted, reason = engine.add_position(
            symbol="R_50",
            direction="LONG",
            size=1000,
            entry_price=150.0,
            confidence=0.5
        )
        
        assert accepted is False
        assert "Confidence" in reason
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        engine = RiskIntelligenceEngine(initial_capital=100000.0)
        
        size = engine.calculate_position_size(
            symbol="R_50",
            confidence=0.8,
            entry_price=150.0,
            stop_loss_pct=0.02
        )
        
        assert size > 0
    
    def test_risk_assessment(self):
        """Test risk assessment runs"""
        engine = RiskIntelligenceEngine(initial_capital=100000.0)
        
        metrics = engine.run_risk_assessment()
        
        assert metrics is not None
        assert metrics.risk_score >= 0
        assert metrics.risk_score <= 100


class TestDrawdownAnalyzer:
    """Tests for drawdown analyzer"""
    
    def test_update(self):
        """Test drawdown update"""
        analyzer = DrawdownAnalyzer()
        
        analyzer.update(current_value=100000, peak_value=100000)
        assert analyzer.current_drawdown == 0.0
        
        analyzer.update(current_value=95000, peak_value=100000)
        assert analyzer.current_drawdown > 0
    
    def test_max_drawdown(self):
        """Test max drawdown tracking"""
        analyzer = DrawdownAnalyzer()
        
        values = [100000, 98000, 96000, 95000, 97000, 99000]
        peaks = [100000, 100000, 100000, 100000, 100000, 100000]
        
        for val, peak in zip(values, peaks):
            analyzer.update(val, peak)
        
        assert analyzer.max_drawdown > 0


class TestExpectedShortfallCalculator:
    """Tests for VaR/CVaR calculator"""
    
    def test_calculate_var(self):
        """Test VaR calculation"""
        calculator = ExpectedShortfallCalculator()
        
        # Mock positions
        positions = [MagicMock(
            size=100,
            current_price=150.0
        )]
        
        var, cvar = calculator.calculate(
            positions=positions,
            portfolio_value=100000.0,
            confidence=0.95
        )
        
        assert var >= 0
        assert cvar >= var


class TestCapitalAllocator:
    """Tests for capital allocator"""
    
    def test_equal_weight(self):
        """Test equal weight allocation"""
        allocator = CapitalAllocator()
        
        positions = [
            {"symbol": "A", "volatility": 0.2},
            {"symbol": "B", "volatility": 0.2}
        ]
        
        allocation = allocator.allocate(
            positions=positions,
            total_capital=100000,
            method=AllocationMethod.EQUAL_WEIGHT
        )
        
        assert len(allocation) == 2
        assert allocation["A"] == allocation["B"]
    
    def test_inverse_volatility(self):
        """Test inverse volatility allocation"""
        allocator = CapitalAllocator()
        
        positions = [
            {"symbol": "A", "volatility": 0.1},
            {"symbol": "B", "volatility": 0.2}
        ]
        
        allocation = allocator.allocate(
            positions=positions,
            total_capital=100000,
            method=AllocationMethod.INVERSE_VOLATILITY
        )
        
        # Lower vol should get more capital
        assert allocation["A"] > allocation["B"]


class TestConcentrationAnalyzer:
    """Tests for concentration analyzer"""
    
    def test_calculate_hhi(self):
        """Test HHI calculation"""
        analyzer = ConcentrationAnalyzer()
        
        positions = [MagicMock(
            size=100,
            current_price=100.0
        )]
        
        hhi = analyzer.calculate(positions, 10000)
        
        assert hhi > 0
        assert hhi <= 1
    
    def test_check_addition(self):
        """Test position addition check"""
        analyzer = ConcentrationAnalyzer()
        
        existing = {"pos1": MagicMock(
            size=100,
            current_price=100.0
        )}
        
        # Adding a very large position should be rejected
        allowed, reason = analyzer.check_addition(
            symbol="R_50",
            position_value=5000,  # 50% of total
            existing_positions=existing
        )
        
        # Should be rejected due to concentration
        assert allowed is False or "HHI" in reason


class TestCircuitBreaker:
    """Tests for circuit breaker"""
    
    def test_trip(self):
        """Test circuit breaker trip"""
        breaker = CircuitBreaker(MagicMock())
        
        breaker.trip(
            trigger_type="daily_loss",
            triggered_at=-0.06
        )
        
        assert breaker.is_tripped()
    
    def test_check_daily_loss(self):
        """Test daily loss check"""
        breaker = CircuitBreaker(MagicMock())
        
        should_trip, reason = breaker.check(
            daily_loss=-0.06,
            hourly_loss=0,
            volatility_ratio=1.0,
            consecutive_loss=False
        )
        
        assert should_trip is True


class TestKillSwitch:
    """Tests for kill switch"""
    
    def test_trigger(self):
        """Test kill switch trigger"""
        ks = KillSwitch(MagicMock())
        
        ks.trigger(reason="drawdown", drawdown=0.16)
        
        assert ks.is_triggered is True
    
    def test_check_drawdown(self):
        """Test drawdown check"""
        ks = KillSwitch(MagicMock())
        
        should_trigger, reason = ks.check(
            current_drawdown=0.16,
            daily_loss=0,
            consecutive_losses=0
        )
        
        assert should_trigger is True


class TestRecoveryManager:
    """Tests for recovery manager"""
    
    def test_start_recovery(self):
        """Test recovery start"""
        manager = RecoveryManager()
        
        manager.start_recovery(peak_value=100000)
        
        assert manager.in_recovery is True
        assert manager.phase.value == "phase_1_conservative"
    
    def test_stake_multiplier(self):
        """Test stake multiplier in recovery"""
        manager = RecoveryManager()
        
        manager.start_recovery()
        
        assert manager.get_stake_multiplier() < 1.0


class TestRiskScoreCalculator:
    """Tests for risk score calculator"""
    
    def test_score_calculation(self):
        """Test risk score calculation"""
        calculator = RiskScoreCalculator(MagicMock())
        
        score = calculator.calculate(
            drawdown=0.05,
            volatility=0.15,
            concentration=0.2,
            var_95=0.02,
            system_state=MagicMock(value="NORMAL"),
            circuit_breaker_tripped=False,
            positions=[MagicMock(risk_contribution=0.2)]
        )
        
        assert 0 <= score <= 100
    
    def test_risk_level(self):
        """Test risk level determination"""
        calculator = RiskScoreCalculator(MagicMock())
        
        level, color = calculator.get_risk_level(15)
        assert level == "VERY_LOW"
        
        level, color = calculator.get_risk_level(85)
        assert level == "VERY_HIGH"


class TestScenarioAnalyzer:
    """Tests for scenario analyzer"""
    
    def test_analyze(self):
        """Test scenario analysis"""
        analyzer = ScenarioAnalyzer()
        
        result = analyzer.analyze(
            symbol="R_50",
            positions=[],
            portfolio_value=100000
        )
        
        assert "scenarios" in result
        assert len(result["scenarios"]) > 0


class TestSensitivityAnalyzer:
    """Tests for sensitivity analyzer"""
    
    def test_analyze(self):
        """Test sensitivity analysis"""
        analyzer = SensitivityAnalyzer()
        
        result = analyzer.analyze(
            symbol="R_50",
            positions=[],
            portfolio_value=100000
        )
        
        assert "sensitivities" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
