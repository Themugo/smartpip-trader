import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages risk and kill switch functionality"""
    
    def __init__(self):
        self.kill_switch = {"armed": True, "stop_loss": 50, "max_losses": 3}
        self.consecutive_losses = 0
    
    def check_risk_limits(
        self,
        session_pnl: float,
        consecutive_losses: int,
        settings: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if risk limits are exceeded"""
        # Check kill switch
        if self.kill_switch["armed"]:
            if session_pnl <= -self.kill_switch["stop_loss"]:
                return False, "Kill switch triggered - Stop loss hit"
            if consecutive_losses >= self.kill_switch["max_losses"]:
                return False, "Kill switch triggered - Max losses reached"
        
        # Check settings limits
        if consecutive_losses >= settings.get("max_consecutive_losses", 3):
            return False, "Max consecutive losses reached"
        
        if session_pnl <= -settings.get("stop_loss", 50):
            return False, "Stop loss reached"
        
        return True, "OK"
    
    def update_consecutive_losses(self, profit: float):
        """Update consecutive losses counter"""
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
    
    def reset_consecutive_losses(self):
        """Reset consecutive losses counter"""
        self.consecutive_losses = 0
    
    def get_consecutive_losses(self) -> int:
        """Get consecutive losses count"""
        return self.consecutive_losses
    
    def set_kill_switch(self, armed: bool, stop_loss: float = 50, max_losses: int = 3):
        """Configure kill switch"""
        self.kill_switch = {
            "armed": armed,
            "stop_loss": stop_loss,
            "max_losses": max_losses
        }
    
    def get_kill_switch(self) -> Dict[str, Any]:
        """Get kill switch configuration"""
        return self.kill_switch
