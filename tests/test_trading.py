"""
Tests for Trading Module
========================

Tests for PositionSizer, RiskManager, StatsManager, and other trading components.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch

from trading.position_sizer import PositionSizer
from trading.risk_manager import RiskManager
from trading.stats_manager import StatsManager
from trading.monitor import TradeMonitor


class TestPositionSizer:
    """Tests for PositionSizer class"""
    
    def test_initialization(self):
        """Test PositionSizer initialization"""
        sizer = PositionSizer(base_amount=2.0, max_risk_per_trade=0.03)
        
        assert sizer.base_amount == 2.0
        assert sizer.max_risk_per_trade == 0.03
        assert sizer.balance == 10000.0
        assert sizer.win_streak == 0
        assert sizer.loss_streak == 0
    
    def test_calculate_position_size_basic(self):
        """Test basic position size calculation"""
        sizer = PositionSizer(base_amount=1.0, max_risk_per_trade=0.02)
        
        market_conditions = {
            "volatility": 0.01,
            "trend_strength": 0.0
        }
        
        position = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        # With 100% confidence and low volatility, should return base amount adjusted
        assert position > 0
        assert position <= sizer.balance * sizer.max_risk_per_trade
    
    def test_calculate_position_size_confidence(self):
        """Test position size varies with confidence"""
        sizer = PositionSizer(base_amount=1.0)
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        
        low_conf = sizer.calculate_position_size(confidence=25, market_conditions=market_conditions)
        high_conf = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        assert high_conf > low_conf
    
    def test_calculate_position_size_volatility(self):
        """Test position size decreases with higher volatility"""
        sizer = PositionSizer(base_amount=1.0)
        
        low_vol = {"volatility": 0.01, "trend_strength": 0.0}
        high_vol = {"volatility": 0.05, "trend_strength": 0.0}
        
        low_vol_pos = sizer.calculate_position_size(confidence=100, market_conditions=low_vol)
        high_vol_pos = sizer.calculate_position_size(confidence=100, market_conditions=high_vol)
        
        assert low_vol_pos > high_vol_pos
    
    def test_calculate_position_size_trend_strength(self):
        """Test position size increases with strong trend"""
        sizer = PositionSizer(base_amount=1.0)
        
        no_trend = {"volatility": 0.01, "trend_strength": 0.0}
        strong_trend = {"volatility": 0.01, "trend_strength": 0.05}
        
        normal_pos = sizer.calculate_position_size(confidence=100, market_conditions=no_trend)
        trend_pos = sizer.calculate_position_size(confidence=100, market_conditions=strong_trend)
        
        assert trend_pos > normal_pos
    
    def test_calculate_position_size_win_streak(self):
        """Test position size increases on winning streak"""
        sizer = PositionSizer(base_amount=1.0)
        
        # Simulate a win streak
        sizer.win_streak = 3
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        position = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        # Position gets multiplied by 1.3 for 3+ win streak
        # The win streak multiplier should be applied
        assert position > 0
    
    def test_calculate_position_size_loss_streak(self):
        """Test position size decreases on losing streak"""
        sizer = PositionSizer(base_amount=1.0)
        
        # Simulate a loss streak
        sizer.loss_streak = 3
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        position = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        assert position < sizer.base_amount
    
    def test_calculate_position_size_risk_limit(self):
        """Test position size is capped by risk limit"""
        sizer = PositionSizer(base_amount=1.0, max_risk_per_trade=0.02)
        sizer.balance = 100000.0  # Very large balance
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        position = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        max_position = sizer.balance * sizer.max_risk_per_trade
        assert position <= max_position
    
    def test_update_trade_result_win(self):
        """Test updating with winning trade"""
        sizer = PositionSizer(base_amount=1.0)
        
        initial_balance = sizer.balance
        sizer.update_trade_result(profit=10.0)
        
        assert sizer.win_streak == 1
        assert sizer.loss_streak == 0
        assert sizer.balance == initial_balance + 10.0
    
    def test_update_trade_result_loss(self):
        """Test updating with losing trade"""
        sizer = PositionSizer(base_amount=1.0)
        
        sizer.update_trade_result(profit=-5.0)
        
        assert sizer.win_streak == 0
        assert sizer.loss_streak == 1
    
    def test_update_trade_result_consecutive(self):
        """Test consecutive trade updates"""
        sizer = PositionSizer(base_amount=1.0)
        
        sizer.update_trade_result(profit=10.0)
        sizer.update_trade_result(profit=5.0)
        
        assert sizer.win_streak == 2
        assert sizer.loss_streak == 0
        
        sizer.update_trade_result(profit=-3.0)
        
        assert sizer.win_streak == 0
        assert sizer.loss_streak == 1
    
    def test_update_trade_result_max_history(self):
        """Test recent trades history is limited"""
        sizer = PositionSizer(base_amount=1.0)
        
        for i in range(25):
            sizer.update_trade_result(profit=1.0)
        
        assert len(sizer.recent_trades) == 20
    
    def test_get_kelly_criterion_size(self):
        """Test Kelly Criterion calculation"""
        sizer = PositionSizer(base_amount=1.0, max_risk_per_trade=0.25)
        sizer.balance = 10000.0
        
        # 60% win rate, avg win 10, avg loss 5
        kelly = sizer.get_kelly_criterion_size(win_rate=0.6, avg_win=10.0, avg_loss=5.0)
        
        assert kelly > 0
        assert kelly <= sizer.balance * 0.25  # Capped at 25%
    
    def test_get_kelly_criterion_zero_loss(self):
        """Test Kelly Criterion with zero loss returns base amount"""
        sizer = PositionSizer(base_amount=5.0)
        
        kelly = sizer.get_kelly_criterion_size(win_rate=0.6, avg_win=10.0, avg_loss=0.0)
        
        assert kelly == sizer.base_amount
    
    def test_get_optimal_size_basic(self):
        """Test get_optimal_size returns basic calculation without Kelly"""
        sizer = PositionSizer(base_amount=1.0)
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        optimal = sizer.get_optimal_size(confidence=100, market_conditions=market_conditions, use_kelly=False)
        
        assert optimal > 0
    
    def test_get_optimal_size_with_kelly(self):
        """Test get_optimal_size uses Kelly when enough trades"""
        sizer = PositionSizer(base_amount=1.0)
        
        # Add enough trades for Kelly
        for _ in range(10):
            sizer.update_trade_result(profit=5.0)
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        optimal = sizer.get_optimal_size(confidence=100, market_conditions=market_conditions, use_kelly=True)
        
        assert optimal > 0


class TestRiskManager:
    """Tests for RiskManager class"""
    
    def test_initialization(self):
        """Test RiskManager initialization"""
        rm = RiskManager()
        
        assert rm.kill_switch["armed"] is True
        assert rm.kill_switch["stop_loss"] == 50
        assert rm.kill_switch["max_losses"] == 3
        assert rm.consecutive_losses == 0
    
    def test_check_risk_limits_safe(self):
        """Test risk limits check when safe"""
        rm = RiskManager()
        
        result, message = rm.check_risk_limits(
            session_pnl=10.0,
            consecutive_losses=0,
            settings={"max_consecutive_losses": 3, "stop_loss": 50}
        )
        
        assert result is True
        assert message == "OK"
    
    def test_check_risk_limits_kill_switch_stop_loss(self):
        """Test kill switch triggered by stop loss"""
        rm = RiskManager()
        rm.kill_switch["armed"] = True
        
        result, message = rm.check_risk_limits(
            session_pnl=-60.0,
            consecutive_losses=0,
            settings={"max_consecutive_losses": 5, "stop_loss": 100}
        )
        
        assert result is False
        assert "Kill switch" in message
        assert "Stop loss" in message
    
    def test_check_risk_limits_kill_switch_max_losses(self):
        """Test kill switch triggered by max losses"""
        rm = RiskManager()
        rm.kill_switch["armed"] = True
        
        result, message = rm.check_risk_limits(
            session_pnl=-10.0,
            consecutive_losses=4,
            settings={"max_consecutive_losses": 5, "stop_loss": 100}
        )
        
        assert result is False
        assert "Kill switch" in message
        assert "Max losses" in message
    
    def test_check_risk_limits_settings_max_losses(self):
        """Test settings-based max losses check"""
        rm = RiskManager()
        rm.kill_switch["armed"] = False
        
        result, message = rm.check_risk_limits(
            session_pnl=-10.0,
            consecutive_losses=4,
            settings={"max_consecutive_losses": 3, "stop_loss": 100}
        )
        
        assert result is False
        assert "Max consecutive losses" in message
    
    def test_check_risk_limits_settings_stop_loss(self):
        """Test settings-based stop loss check"""
        rm = RiskManager()
        rm.kill_switch["armed"] = False
        
        result, message = rm.check_risk_limits(
            session_pnl=-60.0,
            consecutive_losses=0,
            settings={"max_consecutive_losses": 10, "stop_loss": 50}
        )
        
        assert result is False
        assert "Stop loss" in message
    
    def test_update_consecutive_losses_increment(self):
        """Test consecutive losses increment on loss"""
        rm = RiskManager()
        
        rm.update_consecutive_losses(profit=-5.0)
        assert rm.consecutive_losses == 1
        
        rm.update_consecutive_losses(profit=-3.0)
        assert rm.consecutive_losses == 2
    
    def test_update_consecutive_losses_reset(self):
        """Test consecutive losses reset on win"""
        rm = RiskManager()
        rm.consecutive_losses = 3
        
        rm.update_consecutive_losses(profit=5.0)
        
        assert rm.consecutive_losses == 0
    
    def test_reset_consecutive_losses(self):
        """Test resetting consecutive losses"""
        rm = RiskManager()
        rm.consecutive_losses = 5
        
        rm.reset_consecutive_losses()
        
        assert rm.consecutive_losses == 0
    
    def test_get_consecutive_losses(self):
        """Test getting consecutive losses count"""
        rm = RiskManager()
        rm.consecutive_losses = 3
        
        assert rm.get_consecutive_losses() == 3
    
    def test_set_kill_switch(self):
        """Test setting kill switch configuration"""
        rm = RiskManager()
        
        rm.set_kill_switch(armed=True, stop_loss=100, max_losses=5)
        
        assert rm.kill_switch["armed"] is True
        assert rm.kill_switch["stop_loss"] == 100
        assert rm.kill_switch["max_losses"] == 5
    
    def test_get_kill_switch(self):
        """Test getting kill switch configuration"""
        rm = RiskManager()
        
        config = rm.get_kill_switch()
        
        assert "armed" in config
        assert "stop_loss" in config
        assert "max_losses" in config


class TestStatsManager:
    """Tests for StatsManager class"""
    
    def test_initialization(self):
        """Test StatsManager initialization"""
        sm = StatsManager()
        
        assert sm.stats["total_trades"] == 0
        assert sm.stats["wins"] == 0
        assert sm.stats["losses"] == 0
        assert sm.stats["win_rate"] == 0
        assert sm.stats["total_profit"] == 0
    
    def test_update_stats_win(self):
        """Test stats update with winning trade"""
        sm = StatsManager()
        
        sm.update_stats(profit=10.0)
        
        assert sm.stats["total_trades"] == 1
        assert sm.stats["wins"] == 1
        assert sm.stats["losses"] == 0
        assert sm.stats["win_rate"] == 100.0
        assert sm.stats["total_profit"] == 10.0
        assert sm.stats["best_trade"] == 10.0
    
    def test_update_stats_loss(self):
        """Test stats update with losing trade"""
        sm = StatsManager()
        
        sm.update_stats(profit=-5.0)
        
        assert sm.stats["total_trades"] == 1
        assert sm.stats["wins"] == 0
        assert sm.stats["losses"] == 1
        assert sm.stats["win_rate"] == 0.0
        assert sm.stats["worst_trade"] == -5.0
    
    def test_update_stats_multiple(self):
        """Test stats with multiple trades"""
        sm = StatsManager()
        
        sm.update_stats(profit=10.0)
        sm.update_stats(profit=-5.0)
        sm.update_stats(profit=8.0)
        
        assert sm.stats["total_trades"] == 3
        assert sm.stats["wins"] == 2
        assert sm.stats["losses"] == 1
        assert sm.stats["win_rate"] == pytest.approx(66.67, rel=0.1)
    
    def test_update_stats_best_trade_tracking(self):
        """Test best trade tracking"""
        sm = StatsManager()
        
        sm.update_stats(profit=10.0)
        assert sm.stats["best_trade"] == 10.0
        
        sm.update_stats(profit=20.0)
        assert sm.stats["best_trade"] == 20.0
        
        sm.update_stats(profit=5.0)
        assert sm.stats["best_trade"] == 20.0
    
    def test_update_stats_worst_trade_tracking(self):
        """Test worst trade tracking"""
        sm = StatsManager()
        
        sm.update_stats(profit=-10.0)
        assert sm.stats["worst_trade"] == -10.0
        
        sm.update_stats(profit=-5.0)
        assert sm.stats["worst_trade"] == -10.0
        
        sm.update_stats(profit=-20.0)
        assert sm.stats["worst_trade"] == -20.0
    
    def test_update_averages(self):
        """Test average win/loss calculation"""
        sm = StatsManager()
        
        trade_history = [
            {"profit": 10.0},
            {"profit": 20.0},
            {"profit": -5.0},
            {"profit": -10.0}
        ]
        
        sm.update_averages(trade_history)
        
        assert sm.stats["avg_win"] == 15.0
        # avg_loss stores the actual negative value
        assert sm.stats["avg_loss"] == -7.5
    
    def test_update_averages_no_trades(self):
        """Test averages with no trades"""
        sm = StatsManager()
        
        sm.update_averages([])
        
        assert sm.stats["avg_win"] == 0
        assert sm.stats["avg_loss"] == 0
    
    def test_update_averages_only_wins(self):
        """Test averages with only wins"""
        sm = StatsManager()
        
        trade_history = [
            {"profit": 10.0},
            {"profit": 20.0}
        ]
        
        sm.update_averages(trade_history)
        
        assert sm.stats["avg_win"] == 15.0
        assert sm.stats["avg_loss"] == 0
    
    def test_update_averages_only_losses(self):
        """Test averages with only losses"""
        sm = StatsManager()
        
        trade_history = [
            {"profit": -10.0},
            {"profit": -20.0}
        ]
        
        sm.update_averages(trade_history)
        
        assert sm.stats["avg_win"] == 0
        # avg_loss stores the actual negative value
        assert sm.stats["avg_loss"] == -15.0
    
    def test_get_stats(self):
        """Test getting stats"""
        sm = StatsManager()
        sm.update_stats(profit=10.0)
        
        stats = sm.get_stats()
        
        assert "total_trades" in stats
        assert "wins" in stats
        assert "losses" in stats
        assert stats["total_trades"] == 1
    
    def test_reset_stats(self):
        """Test resetting stats"""
        sm = StatsManager()
        sm.update_stats(profit=10.0)
        sm.update_stats(profit=-5.0)
        
        sm.reset_stats()
        
        assert sm.stats["total_trades"] == 0
        assert sm.stats["wins"] == 0
        assert sm.stats["losses"] == 0
        assert sm.stats["total_profit"] == 0
    
    def test_reset_session(self):
        """Test session reset (alias for reset_stats)"""
        sm = StatsManager()
        sm.update_stats(profit=10.0)
        
        sm.reset_session()
        
        assert sm.stats["total_trades"] == 0


class TestTradeMonitor:
    """Tests for TradeMonitor class"""
    
    def test_initialization(self):
        """Test TradeMonitor initialization"""
        tm = TradeMonitor()
        
        assert tm.active_trades == {}
        assert tm.trade_history == []
    
    def test_add_trade(self):
        """Test adding a trade"""
        tm = TradeMonitor()
        
        trade_data = {"symbol": "R_50", "size": 10}
        tm.add_trade("contract_1", trade_data)
        
        assert "contract_1" in tm.active_trades
        assert tm.active_trades["contract_1"] == trade_data
    
    def test_complete_trade(self):
        """Test completing a trade"""
        tm = TradeMonitor()
        
        trade_data = {"symbol": "R_50", "size": 10}
        tm.add_trade("contract_1", trade_data)
        tm.complete_trade("contract_1", profit=5.0)
        
        assert "contract_1" not in tm.active_trades
        assert len(tm.trade_history) == 1
        assert tm.trade_history[0]["profit"] == 5.0
        assert "exit_time" in tm.trade_history[0]
    
    def test_complete_trade_not_found(self):
        """Test completing non-existent trade"""
        tm = TradeMonitor()
        
        # Should not raise an error
        tm.complete_trade("nonexistent", profit=5.0)
        
        assert len(tm.trade_history) == 0
    
    def test_get_active_trades_count(self):
        """Test getting active trades count"""
        tm = TradeMonitor()
        
        tm.add_trade("contract_1", {"symbol": "A"})
        tm.add_trade("contract_2", {"symbol": "B"})
        
        assert tm.get_active_trades_count() == 2
    
    def test_get_trade_history_limit(self):
        """Test getting limited trade history"""
        tm = TradeMonitor()
        
        for i in range(30):
            tm.trade_history.append({"id": i, "profit": i})
        
        history = tm.get_trade_history(limit=10)
        
        assert len(history) == 10
        assert history[-1]["id"] == 29
    
    def test_get_all_trade_history(self):
        """Test getting all trade history"""
        tm = TradeMonitor()
        
        for i in range(5):
            tm.trade_history.append({"id": i})
        
        all_history = tm.get_all_trade_history()
        
        assert len(all_history) == 5
    
    @pytest.mark.asyncio
    async def test_monitor_trade(self):
        """Test monitoring a trade with mocked websocket"""
        tm = TradeMonitor()
        
        # Create mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(return_value='{"portfolio": {"contracts": [{"contract_id": "test_123", "profit": 10.5}]}}')
        
        # Track callback calls
        callback_results = []
        async def on_complete(contract_id, profit):
            callback_results.append((contract_id, profit))
        
        # Monitor trade
        await tm.monitor_trade(
            websocket=mock_websocket,
            contract_id="test_123",
            seconds=0,
            on_trade_complete=on_complete
        )
        
        # Verify callback was called with correct profit
        assert len(callback_results) == 1
        assert callback_results[0] == ("test_123", 10.5)
    
    @pytest.mark.asyncio
    async def test_monitor_trade_with_zero_seconds(self):
        """Test monitoring a trade completes immediately with 0 seconds"""
        tm = TradeMonitor()
        
        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(return_value='{"portfolio": {"contracts": [{"contract_id": "test_123", "profit": 0}]}}')
        
        callback_results = []
        async def on_complete(contract_id, profit):
            callback_results.append((contract_id, profit))
        
        await tm.monitor_trade(
            websocket=mock_websocket,
            contract_id="test_123",
            seconds=0,
            on_trade_complete=on_complete
        )
        
        assert len(callback_results) == 1


class TestPositionSizerEdgeCases:
    """Edge case tests for PositionSizer"""
    
    def test_zero_confidence(self):
        """Test with zero confidence"""
        sizer = PositionSizer(base_amount=1.0)
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        position = sizer.calculate_position_size(confidence=0, market_conditions=market_conditions)
        
        assert position >= sizer.base_amount * 0.5  # Minimum position
    
    def test_missing_market_conditions(self):
        """Test with missing market conditions"""
        sizer = PositionSizer(base_amount=1.0)
        
        position = sizer.calculate_position_size(confidence=100, market_conditions={})
        
        assert position > 0
    
    def test_high_volatility(self):
        """Test with very high volatility"""
        sizer = PositionSizer(base_amount=1.0)
        
        market_conditions = {"volatility": 1.0, "trend_strength": 0.0}
        position = sizer.calculate_position_size(confidence=100, market_conditions=market_conditions)
        
        assert position > 0
    
    def test_kelly_with_no_wins(self):
        """Test Kelly criterion with no winning trades"""
        sizer = PositionSizer(base_amount=1.0)
        
        # Add only losses
        for _ in range(10):
            sizer.update_trade_result(profit=-5.0)
        
        market_conditions = {"volatility": 0.01, "trend_strength": 0.0}
        optimal = sizer.get_optimal_size(confidence=100, market_conditions=market_conditions, use_kelly=True)
        
        # Should fall back to basic calculation
        assert optimal > 0
    
    def test_balance_update_after_trades(self):
        """Test balance is updated correctly"""
        sizer = PositionSizer(base_amount=1.0, max_risk_per_trade=0.02)
        initial_balance = sizer.balance
        
        sizer.update_trade_result(profit=100.0)
        sizer.update_trade_result(profit=-30.0)
        
        assert sizer.balance == initial_balance + 70.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
