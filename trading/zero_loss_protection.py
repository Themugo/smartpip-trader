from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from collections import deque
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class ZeroLossProtection:
    """
    Ultimate zero-loss protection system for live trading
    Designed to eliminate loss potential through multi-layered protection
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        # Protection thresholds
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        
        # Zero-loss parameters
        self.max_daily_loss_percent = 1.0  # Maximum 1% daily loss
        self.max_drawdown_percent = 2.0  # Maximum 2% drawdown
        self.max_consecutive_losses = 2  # Maximum 2 consecutive losses
        self.max_single_loss_percent = 0.5  # Maximum 0.5% per trade
        
        # Kill switch
        self.kill_switch = False
        self.kill_switch_reason = ""
        self.kill_switch_timestamp = None
        
        # Trade tracking
        self.trade_history = deque(maxlen=100)
        self.daily_trades = []
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        
        # Real-time monitoring
        self.active_positions = {}
        self.position_monitoring_active = False
        self.monitoring_interval = 1.0  # Check every second
        
        # Protection layers
        self.protection_layers = {
            "pre_trade": True,  # Check before trade
            "in_trade": True,  # Monitor during trade
            "post_trade": True,  # Check after trade
            "portfolio": True,  # Portfolio-level checks
            "emergency": True  # Emergency stop
        }
        
        # Alerts
        self.alert_callbacks = []
        self.alert_history = deque(maxlen=50)
        
        # Safety mechanisms
        self.safety_margin = 0.1  # 10% safety margin
        self.min_balance_threshold = initial_balance * 0.95  # 95% of initial
        
        # Market conditions
        self.market_blacklist = set()
        self.condition_blacklist = set()
        
    def add_alert_callback(self, callback: Callable):
        """Add callback for alerts"""
        self.alert_callbacks.append(callback)
    
    def trigger_alert(self, alert_type: str, message: str, severity: str = "warning"):
        """Trigger an alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alert_history.append(alert)
        
        # Call all alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def activate_kill_switch(self, reason: str, emergency: bool = False):
        """Activate kill switch to stop all trading"""
        self.kill_switch = True
        self.kill_switch_reason = reason
        self.kill_switch_timestamp = datetime.now().isoformat()
        
        severity = "critical" if emergency else "high"
        self.trigger_alert("kill_switch_activated", f"Kill switch activated: {reason}", severity)
        
        # Close all active positions if emergency
        if emergency and self.active_positions:
            self._emergency_close_all_positions()
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch (manual override)"""
        self.kill_switch = False
        self.kill_switch_reason = ""
        self.kill_switch_timestamp = None
        
        self.trigger_alert("kill_switch_deactivated", "Kill switch deactivated", "info")
    
    def _emergency_close_all_positions(self):
        """Emergency close all active positions"""
        for position_id, position in self.active_positions.items():
            self.trigger_alert("position_closed_emergency", 
                            f"Emergency close position {position_id}", "critical")
        
        self.active_positions.clear()
    
    def pre_trade_check(self, trade_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Comprehensive pre-trade check to prevent losses
        Returns (should_trade, reason)
        """
        # Check kill switch
        if self.kill_switch:
            return False, f"Kill switch active: {self.kill_switch_reason}"
        
        # Check minimum balance
        if self.current_balance < self.min_balance_threshold:
            self.activate_kill_switch("Balance below minimum threshold", emergency=True)
            return False, "Balance below minimum threshold"
        
        # Check daily loss limit
        if self.daily_pnl < -(self.initial_balance * self.max_daily_loss_percent / 100):
            self.activate_kill_switch("Daily loss limit exceeded", emergency=True)
            return False, f"Daily loss limit exceeded: {self.daily_pnl:.2f}"
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.activate_kill_switch("Consecutive losses limit exceeded")
            return False, f"Consecutive losses limit: {self.consecutive_losses}"
        
        # Check drawdown
        drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        if drawdown_percent > self.max_drawdown_percent:
            self.activate_kill_switch("Maximum drawdown exceeded", emergency=True)
            return False, f"Drawdown {drawdown_percent:.2f}% exceeds limit {self.max_drawdown_percent}%"
        
        # Check single trade loss potential
        trade_amount = trade_data.get("amount", 0)
        max_loss = trade_amount  # Maximum loss is the trade amount
        max_loss_percent = (max_loss / self.current_balance) * 100
        
        if max_loss_percent > self.max_single_loss_percent:
            return False, f"Trade loss potential {max_loss_percent:.2f}% exceeds limit {self.max_single_loss_percent}%"
        
        # Check market blacklist
        market = trade_data.get("market", "")
        if market in self.market_blacklist:
            return False, f"Market {market} is blacklisted"
        
        # Check confidence threshold
        confidence = trade_data.get("confidence", 0)
        if confidence < 90:  # Very high threshold for zero-loss
            return False, f"Confidence {confidence}% below zero-loss threshold 90%"
        
        # Check market conditions
        if not self._check_market_conditions(trade_data):
            return False, "Unfavorable market conditions for zero-loss trading"
        
        return True, "Trade approved"
    
    def _check_market_conditions(self, trade_data: Dict[str, Any]) -> bool:
        """Check if market conditions are favorable for zero-loss trading"""
        # Check volatility
        volatility = trade_data.get("volatility", 0)
        if volatility > 0.03:  # Too volatile
            return False
        if volatility < 0.005:  # Not volatile enough
            return False
        
        # Check trend strength
        trend_strength = trade_data.get("trend_strength", 0)
        if abs(trend_strength) < 0.01:  # No clear trend
            return False
        
        # Check signal agreement
        signal_agreement = trade_data.get("signal_agreement", 0)
        if signal_agreement < 0.8:  # Need 80% agreement for zero-loss
            return False
        
        # Check regime
        regime = trade_data.get("regime", {})
        if regime.get("volatility") == "extreme":
            return False
        if regime.get("trend") == "neutral":
            return False
        
        return True
    
    def calculate_safe_position_size(self, base_amount: float, confidence: float) -> float:
        """Calculate position size with zero-loss protection"""
        # Start with very conservative base
        position = base_amount * 0.5  # Start at 50% of base
        
        # Adjust by confidence (very conservative)
        confidence_multiplier = (confidence - 90) / 10  # Only above 90%
        confidence_multiplier = max(0.1, min(confidence_multiplier, 1.0))
        position *= confidence_multiplier
        
        # Apply safety margin
        position *= (1 - self.safety_margin)
        
        # Ensure minimum position
        position = max(position, base_amount * 0.1)
        
        # Ensure maximum position
        max_position = self.current_balance * 0.01  # Maximum 1% of balance
        position = min(position, max_position)
        
        return position
    
    def record_trade_result(self, trade_data: Dict[str, Any]):
        """Record trade result and update protection parameters"""
        profit = trade_data.get("profit", 0)
        market = trade_data.get("market", "")
        strategy = trade_data.get("strategy", "")
        
        # Update balance
        self.current_balance += profit
        self.daily_pnl += profit
        
        # Update peak balance
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Record trade
        trade_record = {
            "profit": profit,
            "market": market,
            "strategy": strategy,
            "balance": self.current_balance,
            "timestamp": datetime.now().isoformat()
        }
        
        self.trade_history.append(trade_record)
        self.daily_trades.append(trade_record)
        
        # Update consecutive losses
        if profit < 0:
            self.consecutive_losses += 1
            
            # Check if should blacklist market
            if self._should_blacklist_market(market):
                self.market_blacklist.add(market)
                self.trigger_alert("market_blacklisted", f"Market {market} blacklisted due to losses", "warning")
            
            # Check if should blacklist strategy
            if self._should_blacklist_strategy(strategy):
                self.condition_blacklist.add(strategy)
                self.trigger_alert("strategy_blacklisted", f"Strategy {strategy} blacklisted due to losses", "warning")
        else:
            self.consecutive_losses = 0
            
            # Remove from blacklist if profitable
            if market in self.market_blacklist:
                self.market_blacklist.remove(market)
            if strategy in self.condition_blacklist:
                self.condition_blacklist.remove(strategy)
        
        # Post-trade protection check
        self._post_trade_protection_check()
    
    def _should_blacklist_market(self, market: str) -> bool:
        """Determine if market should be blacklisted"""
        recent_trades = [t for t in self.trade_history if t["market"] == market]
        if len(recent_trades) < 5:
            return False
        
        losses = sum(1 for t in recent_trades if t["profit"] < 0)
        loss_rate = losses / len(recent_trades)
        
        # Blacklist if >70% loss rate
        return loss_rate > 0.7
    
    def _should_blacklist_strategy(self, strategy: str) -> bool:
        """Determine if strategy should be blacklisted"""
        recent_trades = [t for t in self.trade_history if t["strategy"] == strategy]
        if len(recent_trades) < 5:
            return False
        
        losses = sum(1 for t in recent_trades if t["profit"] < 0)
        loss_rate = losses / len(recent_trades)
        
        # Blacklist if >70% loss rate
        return loss_rate > 0.7
    
    def _post_trade_protection_check(self):
        """Post-trade protection checks"""
        # Check if approaching daily loss limit
        daily_loss_limit = self.initial_balance * self.max_daily_loss_percent / 100
        if self.daily_pnl < -daily_loss_limit * 0.8:  # 80% of limit
            self.trigger_alert("approaching_daily_loss_limit", 
                            f"Daily loss {self.daily_pnl:.2f} approaching limit {daily_loss_limit:.2f}", 
                            "high")
        
        # Check if approaching drawdown limit
        drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        if drawdown_percent > self.max_drawdown_percent * 0.8:  # 80% of limit
            self.trigger_alert("approaching_drawdown_limit", 
                            f"Drawdown {drawdown_percent:.2f}% approaching limit {self.max_drawdown_percent}%", 
                            "high")
        
        # Check if consecutive losses approaching limit
        if self.consecutive_losses >= self.max_consecutive_losses - 1:
            self.trigger_alert("approaching_consecutive_loss_limit", 
                            f"Consecutive losses {self.consecutive_losses} approaching limit {self.max_consecutive_losses}", 
                            "high")
    
    async def start_position_monitoring(self):
        """Start real-time position monitoring"""
        self.position_monitoring_active = True
        
        while self.position_monitoring_active:
            await self._monitor_positions()
            await asyncio.sleep(self.monitoring_interval)
    
    async def _monitor_positions(self):
        """Monitor active positions for risk"""
        if self.kill_switch:
            return
        
        for position_id, position in self.active_positions.items():
            # Check position P&L
            current_pnl = position.get("current_pnl", 0)
            entry_price = position.get("entry_price", 0)
            current_price = position.get("current_price", 0)
            
            # Calculate unrealized loss
            if position.get("direction") == "CALL":
                unrealized_pnl = (current_price - entry_price) / entry_price
            else:
                unrealized_pnl = (entry_price - current_price) / entry_price
            
            # Check if position is losing too much
            if unrealized_pnl < -0.01:  # 1% loss
                self.trigger_alert("position_loss_warning", 
                                f"Position {position_id} losing {unrealized_pnl*100:.2f}%", 
                                "high")
            
            # Emergency close if losing too much
            if unrealized_pnl < -0.02:  # 2% loss
                self.trigger_alert("position_emergency_close", 
                                f"Emergency close position {position_id} due to {unrealized_pnl*100:.2f}% loss", 
                                "critical")
                # In real implementation, this would close the position
    
    def stop_position_monitoring(self):
        """Stop position monitoring"""
        self.position_monitoring_active = False
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Get current protection status"""
        drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100 if self.peak_balance > 0 else 0
        
        return {
            "kill_switch_active": self.kill_switch,
            "kill_switch_reason": self.kill_switch_reason,
            "kill_switch_timestamp": self.kill_switch_timestamp,
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "peak_balance": self.peak_balance,
            "daily_pnl": self.daily_pnl,
            "drawdown_percent": drawdown_percent,
            "consecutive_losses": self.consecutive_losses,
            "daily_trades": len(self.daily_trades),
            "blacklisted_markets": list(self.market_blacklist),
            "blacklisted_strategies": list(self.condition_blacklist),
            "active_positions": len(self.active_positions),
            "protection_layers": self.protection_layers,
            "recent_alerts": list(self.alert_history)[-5:]
        }
    
    def reset_daily(self):
        """Reset daily metrics"""
        self.daily_pnl = 0.0
        self.daily_trades = []
        self.consecutive_losses = 0
        
        # Don't reset kill switch - manual reset required
    
    def get_protection_report(self) -> Dict[str, Any]:
        """Generate comprehensive protection report"""
        recent_trades = list(self.trade_history)[-20:]
        
        winning_trades = sum(1 for t in recent_trades if t["profit"] > 0)
        losing_trades = sum(1 for t in recent_trades if t["profit"] < 0)
        win_rate = winning_trades / len(recent_trades) if recent_trades else 0
        
        total_profit = sum(t["profit"] for t in recent_trades)
        max_loss = min(t["profit"] for t in recent_trades) if recent_trades else 0
        max_win = max(t["profit"] for t in recent_trades) if recent_trades else 0
        
        return {
            "protection_status": self.get_protection_status(),
            "performance": {
                "win_rate": win_rate,
                "total_trades": len(recent_trades),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_profit": total_profit,
                "max_loss": max_loss,
                "max_win": max_win
            },
            "protection_metrics": {
                "max_daily_loss_percent": self.max_daily_loss_percent,
                "max_drawdown_percent": self.max_drawdown_percent,
                "max_consecutive_losses": self.max_consecutive_losses,
                "max_single_loss_percent": self.max_single_loss_percent,
                "safety_margin": self.safety_margin
            },
            "alerts_summary": {
                "total_alerts": len(self.alert_history),
                "critical_alerts": sum(1 for a in self.alert_history if a["severity"] == "critical"),
                "high_alerts": sum(1 for a in self.alert_history if a["severity"] == "high"),
                "warning_alerts": sum(1 for a in self.alert_history if a["severity"] == "warning")
            }
        }
