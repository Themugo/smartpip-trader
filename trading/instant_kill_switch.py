from typing import Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class InstantKillSwitch:
    """
    Instant kill switch for immediate trading halt
    Provides millisecond-level response for emergency stops
    """
    
    def __init__(self):
        self.active = False
        self.reason = ""
        self.timestamp = None
        self.emergency_level = "normal"  # normal, high, critical
        
        # Callbacks for kill switch activation
        self.activation_callbacks = []
        self.deactivation_callbacks = []
        
        # Kill switch triggers
        self.triggers = {
            "manual": False,
            "daily_loss": False,
            "drawdown": False,
            "consecutive_losses": False,
            "balance_threshold": False,
            "market_conditions": False,
            "api_failure": False,
            "system_error": False
        }
        
        # Emergency actions
        self.emergency_actions = {
            "close_all_positions": True,
            "cancel_pending_orders": True,
            "disconnect_api": False,
            "notify_admin": True,
            "log_incident": True
        }
        
        # Kill switch history
        self.history = []
        
        # Monitoring
        self.monitoring_active = False
        self.check_interval = 0.1  # 100ms checks
        
    def add_activation_callback(self, callback: Callable):
        """Add callback for kill switch activation"""
        self.activation_callbacks.append(callback)
    
    def add_deactivation_callback(self, callback: Callable):
        """Add callback for kill switch deactivation"""
        self.deactivation_callbacks.append(callback)
    
    def activate(self, reason: str, trigger: str = "manual", emergency_level: str = "normal"):
        """
        Activate kill switch instantly
        """
        if self.active:
            return  # Already active
        
        self.active = True
        self.reason = reason
        self.timestamp = datetime.now().isoformat()
        self.emergency_level = emergency_level
        self.triggers[trigger] = True
        
        # Record activation
        activation_record = {
            "timestamp": self.timestamp,
            "reason": reason,
            "trigger": trigger,
            "emergency_level": emergency_level
        }
        self.history.append(activation_record)
        
        # Execute activation callbacks
        for callback in self.activation_callbacks:
            try:
                callback(activation_record)
            except Exception as e:
                logger.error(f"Kill switch activation callback failed: {e}")
        
        # Execute emergency actions if critical
        if emergency_level == "critical":
            self._execute_emergency_actions(activation_record)
        
        return True
    
    def deactivate(self, reason: str = "manual"):
        """
        Deactivate kill switch
        """
        if not self.active:
            return  # Already inactive
        
        self.active = False
        self.reason = ""
        self.emergency_level = "normal"
        
        # Reset triggers
        for trigger in self.triggers:
            self.triggers[trigger] = False
        
        # Record deactivation
        deactivation_record = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "action": "deactivation"
        }
        self.history.append(deactivation_record)
        
        # Execute deactivation callbacks
        for callback in self.deactivation_callbacks:
            try:
                callback(deactivation_record)
            except Exception as e:
                logger.error(f"Kill switch deactivation callback failed: {e}")
        
        return True
    
    def _execute_emergency_actions(self, activation_record: Dict[str, Any]):
        """Execute emergency actions for critical situations"""
        if self.emergency_actions["close_all_positions"]:
            # This would close all positions in real implementation
            pass
        
        if self.emergency_actions["cancel_pending_orders"]:
            # This would cancel all pending orders
            pass
        
        if self.emergency_actions["disconnect_api"]:
            # This would disconnect from trading API
            pass
        
        if self.emergency_actions["notify_admin"]:
            # This would send notification to admin
            pass
        
        if self.emergency_actions["log_incident"]:
            # This would log the incident
            pass
    
    def check_and_activate_if_needed(self, metrics: Dict[str, Any]) -> Optional[str]:
        """
        Check metrics and activate kill switch if thresholds exceeded
        Returns reason if activated, None otherwise
        """
        # Check daily loss
        daily_loss = metrics.get("daily_pnl", 0)
        max_daily_loss = metrics.get("max_daily_loss", 0)
        if daily_loss < -max_daily_loss:
            return self.activate(
                f"Daily loss {daily_loss:.2f} exceeded limit {max_daily_loss:.2f}",
                trigger="daily_loss",
                emergency_level="critical"
            )
        
        # Check drawdown
        drawdown = metrics.get("drawdown_percent", 0)
        max_drawdown = metrics.get("max_drawdown", 0)
        if drawdown > max_drawdown:
            return self.activate(
                f"Drawdown {drawdown:.2f}% exceeded limit {max_drawdown:.2f}%",
                trigger="drawdown",
                emergency_level="critical"
            )
        
        # Check consecutive losses
        consecutive_losses = metrics.get("consecutive_losses", 0)
        max_consecutive = metrics.get("max_consecutive_losses", 0)
        if consecutive_losses >= max_consecutive:
            return self.activate(
                f"Consecutive losses {consecutive_losses} exceeded limit {max_consecutive}",
                trigger="consecutive_losses",
                emergency_level="high"
            )
        
        # Check balance threshold
        current_balance = metrics.get("current_balance", 0)
        min_balance = metrics.get("min_balance", 0)
        if current_balance < min_balance:
            return self.activate(
                f"Balance {current_balance:.2f} below minimum {min_balance:.2f}",
                trigger="balance_threshold",
                emergency_level="critical"
            )
        
        # Check market conditions
        market_conditions = metrics.get("market_conditions", {})
        if market_conditions.get("extreme_volatility", False):
            return self.activate(
                "Extreme market volatility detected",
                trigger="market_conditions",
                emergency_level="high"
            )
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current kill switch status"""
        return {
            "active": self.active,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "emergency_level": self.emergency_level,
            "triggers": self.triggers.copy(),
            "emergency_actions": self.emergency_actions.copy(),
            "activation_count": len([h for h in self.history if "activation" in str(h)])
        }
    
    def get_history(self, limit: int = 10) -> list:
        """Get kill switch history"""
        return self.history[-limit:]
    
    def reset_triggers(self):
        """Reset all triggers"""
        for trigger in self.triggers:
            self.triggers[trigger] = False
    
    def set_emergency_action(self, action: str, enabled: bool):
        """Enable or disable emergency action"""
        if action in self.emergency_actions:
            self.emergency_actions[action] = enabled


class RealTimeMonitor:
    """
    Real-time monitoring system for instant threat detection
    Runs continuous checks with configurable intervals
    """
    
    def __init__(self, kill_switch: InstantKillSwitch):
        self.kill_switch = kill_switch
        self.monitoring_active = False
        self.check_interval = 0.1  # 100ms default
        self.metrics_callback = None
        self.alert_callback = None
        
        # Monitoring thresholds
        self.thresholds = {
            "daily_loss_percent": 1.0,
            "drawdown_percent": 2.0,
            "consecutive_losses": 2,
            "balance_percent": 95.0,
            "volatility": 0.05
        }
        
        # Alert history
        self.alerts = []
        
    def set_metrics_callback(self, callback: Callable):
        """Set callback to get current metrics"""
        self.metrics_callback = callback
    
    def set_alert_callback(self, callback: Callable):
        """Set callback for alerts"""
        self.alert_callback = callback
    
    def set_threshold(self, threshold_name: str, value: float):
        """Set monitoring threshold"""
        self.thresholds[threshold_name] = value
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        self.monitoring_active = True
        
        while self.monitoring_active:
            await self._check_metrics()
            await asyncio.sleep(self.check_interval)
    
    async def _check_metrics(self):
        """Check current metrics and activate kill switch if needed"""
        if not self.metrics_callback:
            return
        
        try:
            metrics = self.metrics_callback()
            
            # Build metrics dict for kill switch check
            check_metrics = {
                "daily_pnl": metrics.get("daily_pnl", 0),
                "max_daily_loss": metrics.get("initial_balance", 1000) * self.thresholds["daily_loss_percent"] / 100,
                "drawdown_percent": metrics.get("drawdown_percent", 0),
                "max_drawdown": self.thresholds["drawdown_percent"],
                "consecutive_losses": metrics.get("consecutive_losses", 0),
                "max_consecutive_losses": self.thresholds["consecutive_losses"],
                "current_balance": metrics.get("current_balance", 1000),
                "min_balance": metrics.get("initial_balance", 1000) * self.thresholds["balance_percent"] / 100,
                "market_conditions": {
                    "extreme_volatility": metrics.get("volatility", 0) > self.thresholds["volatility"]
                }
            }
            
            # Check and activate kill switch if needed
            reason = self.kill_switch.check_and_activate_if_needed(check_metrics)
            
            if reason:
                self._send_alert("kill_switch_activated", f"Kill switch activated: {reason}", "critical")
            
        except Exception as e:
            self._send_alert("monitoring_error", f"Monitoring error: {e}", "high")
    
    def _send_alert(self, alert_type: str, message: str, severity: str):
        """Send alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
    
    def get_alerts(self, limit: int = 20) -> list:
        """Get recent alerts"""
        return self.alerts[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status"""
        return {
            "monitoring_active": self.monitoring_active,
            "check_interval": self.check_interval,
            "thresholds": self.thresholds.copy(),
            "total_alerts": len(self.alerts)
        }


class ZeroLossGuard:
    """
    Complete zero-loss guard system combining all protection mechanisms
    """
    
    def __init__(self, initial_balance: float = 1000.0):
        from trading.zero_loss_protection import ZeroLossProtection
        
        self.protection = ZeroLossProtection(initial_balance)
        self.kill_switch = InstantKillSwitch()
        self.monitor = RealTimeMonitor(self.kill_switch)
        
        # Integrate components
        self._setup_integration()
    
    def _setup_integration(self):
        """Setup integration between components"""
        # Set metrics callback for monitor
        self.monitor.set_metrics_callback(self._get_metrics)
        
        # Set alert callback
        self.monitor.set_alert_callback(self._handle_alert)
        
        # Add kill switch activation callback
        self.kill_switch.add_activation_callback(self._on_kill_switch_activation)
        
        # Add kill switch deactivation callback
        self.kill_switch.add_deactivation_callback(self._on_kill_switch_deactivation)
        
        # Add alert callback to protection
        self.protection.add_alert_callback(self._handle_protection_alert)
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get current metrics from protection system"""
        status = self.protection.get_protection_status()
        
        return {
            "daily_pnl": status["daily_pnl"],
            "current_balance": status["current_balance"],
            "initial_balance": status["initial_balance"],
            "peak_balance": status["peak_balance"],
            "drawdown_percent": status["drawdown_percent"],
            "consecutive_losses": status["consecutive_losses"],
            "volatility": 0.01  # Would get from regime detector
        }
    
    def _handle_alert(self, alert: Dict[str, Any]):
        """Handle alert from monitor"""
        # Could send notifications, log, etc.
        pass
    
    def _on_kill_switch_activation(self, activation_record: Dict[str, Any]):
        """Handle kill switch activation"""
        # Activate protection kill switch
        self.protection.activate_kill_switch(
            activation_record["reason"],
            emergency=activation_record["emergency_level"] == "critical"
        )
    
    def _on_kill_switch_deactivation(self, deactivation_record: Dict[str, Any]):
        """Handle kill switch deactivation"""
        # Deactivate protection kill switch
        self.protection.deactivate_kill_switch()
    
    def _handle_protection_alert(self, alert: Dict[str, Any]):
        """Handle alert from protection system"""
        # Could send notifications, log, etc.
        pass
    
    async def start(self):
        """Start zero-loss guard system"""
        # Start monitoring
        await self.monitor.start_monitoring()
    
    def stop(self):
        """Stop zero-loss guard system"""
        self.monitor.stop_monitoring()
    
    def pre_trade_check(self, trade_data: Dict[str, Any]) -> tuple[bool, str]:
        """Pre-trade check using protection system"""
        return self.protection.pre_trade_check(trade_data)
    
    def record_trade_result(self, trade_data: Dict[str, Any]):
        """Record trade result"""
        self.protection.record_trade_result(trade_data)
    
    def calculate_safe_position_size(self, base_amount: float, confidence: float) -> float:
        """Calculate safe position size"""
        return self.protection.calculate_safe_position_size(base_amount, confidence)
    
    def get_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        return {
            "protection": self.protection.get_protection_status(),
            "kill_switch": self.kill_switch.get_status(),
            "monitor": self.monitor.get_status()
        }
    
    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive report"""
        return self.protection.get_protection_report()
    
    def manual_kill_switch(self, reason: str = "Manual activation"):
        """Manually activate kill switch"""
        self.kill_switch.activate(reason, trigger="manual", emergency_level="high")
    
    def manual_kill_switch_release(self, reason: str = "Manual release"):
        """Manually release kill switch"""
        self.kill_switch.deactivate(reason)
