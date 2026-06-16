from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Settings:
    """Trading system settings"""
    base_amount: float = 1.0
    auto_trading: bool = False
    max_trades_per_hour: int = 10
    min_confidence: int = 70
    stop_loss: float = 50.0
    take_profit: float = 100.0
    max_consecutive_losses: int = 3
    enable_even_odd: bool = True
    enable_rise_fall: bool = True
    enable_over_under: bool = True
    enable_match_diff: bool = True
    enable_digit_analysis: bool = True
    enable_foreign_bot: bool = False
    foreign_bot_endpoint: str = ""
    foreign_bot_api_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_amount": self.base_amount,
            "auto_trading": self.auto_trading,
            "max_trades_per_hour": self.max_trades_per_hour,
            "min_confidence": self.min_confidence,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "max_consecutive_losses": self.max_consecutive_losses,
            "enable_even_odd": self.enable_even_odd,
            "enable_rise_fall": self.enable_rise_fall,
            "enable_over_under": self.enable_over_under,
            "enable_match_diff": self.enable_match_diff,
            "enable_digit_analysis": self.enable_digit_analysis,
            "enable_foreign_bot": self.enable_foreign_bot,
            "foreign_bot_endpoint": self.foreign_bot_endpoint,
            "foreign_bot_api_key": self.foreign_bot_api_key
        }

    def update(self, data: Dict[str, Any]):
        """Update settings from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
