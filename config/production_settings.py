import os
from typing import Dict, Any


class ProductionSettings:
    """Production market settings - locked and final"""
    
    def __init__(self):
        # Real Deriv API settings (not sandbox)
        self.deriv_api_token = os.getenv("DERIV_API_TOKEN")
        self.deriv_app_id = os.getenv("DERIV_APP_ID", "1089")
        self.api_url = "wss://ws.binaryws.com/websockets/v3"  # Production API
        self.environment = "production"
        
        # Market settings - locked
        self.markets = {
            "R_10": {"enabled": True, "min_stake": 10, "max_stake": 1000},
            "R_25": {"enabled": True, "min_stake": 10, "max_stake": 1000},
            "R_50": {"enabled": True, "min_stake": 10, "max_stake": 1000},
            "R_75": {"enabled": True, "min_stake": 10, "max_stake": 1000},
            "R_100": {"enabled": True, "min_stake": 10, "max_stake": 1000},
            "R_10_10S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_25_10S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_50_10S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_75_10S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_100_10S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_100_25S": {"enabled": True, "min_stake": 10, "max_stake": 500},
            "R_100_50S": {"enabled": True, "min_stake": 10, "max_stake": 500}
        }
        
        # Trading settings - locked
        self.base_amount = 100  # KES
        self.max_risk_per_trade = 0.02  # 2%
        self.min_confidence = 85  # 85%
        self.max_daily_trades = 50
        self.max_position_size = 10000  # KES
        
        # Risk management - locked
        self.daily_loss_limit = 0.05  # 5%
        self.max_consecutive_losses = 3
        self.kill_switch_enabled = True
        
        # Currency settings - locked to KES
        self.base_currency = "KES"
        self.display_currency = "KES"
        self.auto_convert = True
        
        # Compliance settings - locked
        self.cma_licensed = True
        self.cbm_approved = True
        self.kyc_required = True
        self.aml_required = True
        self.tax_rate = 0.20  # 20%
        
        # Security settings - locked
        self.jwt_enabled = True
        self.ip_whitelist_enabled = True
        self.rate_limit_enabled = True
        self.encryption_enabled = True
        
        # Notification settings - locked
        self.email_enabled = True
        self.telegram_enabled = True
        self.discord_enabled = True
        
        # Performance settings - locked
        self.hft_enabled = True
        self.max_latency_ms = 50
        self.cache_enabled = True
        self.cache_ttl = 5
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all production settings"""
        return {
            "environment": self.environment,
            "api_url": self.api_url,
            "markets": self.markets,
            "trading": {
                "base_amount": self.base_amount,
                "max_risk_per_trade": self.max_risk_per_trade,
                "min_confidence": self.min_confidence,
                "max_daily_trades": self.max_daily_trades,
                "max_position_size": self.max_position_size
            },
            "risk_management": {
                "daily_loss_limit": self.daily_loss_limit,
                "max_consecutive_losses": self.max_consecutive_losses,
                "kill_switch_enabled": self.kill_switch_enabled
            },
            "currency": {
                "base_currency": self.base_currency,
                "display_currency": self.display_currency,
                "auto_convert": self.auto_convert
            },
            "compliance": {
                "cma_licensed": self.cma_licensed,
                "cbm_approved": self.cbm_approved,
                "kyc_required": self.kyc_required,
                "aml_required": self.aml_required,
                "tax_rate": self.tax_rate
            },
            "security": {
                "jwt_enabled": self.jwt_enabled,
                "ip_whitelist_enabled": self.ip_whitelist_enabled,
                "rate_limit_enabled": self.rate_limit_enabled,
                "encryption_enabled": self.encryption_enabled
            },
            "notifications": {
                "email_enabled": self.email_enabled,
                "telegram_enabled": self.telegram_enabled,
                "discord_enabled": self.discord_enabled
            },
            "performance": {
                "hft_enabled": self.hft_enabled,
                "max_latency_ms": self.max_latency_ms,
                "cache_enabled": self.cache_enabled,
                "cache_ttl": self.cache_ttl
            }
        }
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == "production"
    
    def validate_settings(self) -> bool:
        """Validate production settings"""
        if not self.deriv_api_token:
            return False
        if self.environment != "production":
            return False
        if not self.cma_licensed or not self.cbm_approved:
            return False
        return True
