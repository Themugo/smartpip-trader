"""
Risk SDK
========

SDK for risk management.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import SmartPipSDK, SDKConfig, SDKError, SDKLogger

logger = SDKLogger("risk")


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    max_position_size: float = 1000000
    max_portfolio_exposure: float = 0.25  # 25% of portfolio
    max_daily_loss: float = 0.05  # 5% of portfolio
    max_drawdown: float = 0.15  # 15% of portfolio
    max_leverage: float = 3.0
    max_correlation: float = 0.7
    min_liquidity_ratio: float = 0.2


@dataclass
class RiskCheck:
    """Risk check result"""
    passed: bool
    check_type: str
    message: str
    value: float
    limit: float


class RiskManager(SmartPipSDK):
    """
    Risk management SDK.
    """
    
    def __init__(self, config: Optional[SDKConfig] = None):
        super().__init__(config)
        self._limits = RiskLimits()
        self._daily_pnl = 0.0
        self._peak_equity = 0.0
        self._current_equity = 0.0
    
    def set_limits(self, limits: RiskLimits) -> None:
        """Set risk limits"""
        self._limits = limits
    
    def check_position_size(self, symbol: str, size: float, price: float) -> RiskCheck:
        """Check if position size is within limits"""
        value = size * price
        
        passed = value <= self._limits.max_position_size
        return RiskCheck(
            passed=passed,
            check_type="position_size",
            message=f"Position size {value:.2f} exceeds limit" if not passed else "OK",
            value=value,
            limit=self._limits.max_position_size
        )
    
    def check_portfolio_exposure(self, current_exposure: float, new_exposure: float) -> RiskCheck:
        """Check portfolio exposure"""
        total_exposure = current_exposure + new_exposure
        
        passed = total_exposure <= self._limits.max_portfolio_exposure
        return RiskCheck(
            passed=passed,
            check_type="portfolio_exposure",
            message=f"Total exposure {total_exposure:.2%} exceeds limit" if not passed else "OK",
            value=total_exposure,
            limit=self._limits.max_portfolio_exposure
        )
    
    def check_daily_loss(self, current_loss: float) -> RiskCheck:
        """Check daily loss limit"""
        self._daily_pnl = current_loss
        
        # Daily loss is negative
        loss_pct = abs(current_loss)
        passed = loss_pct <= self._limits.max_daily_loss
        
        return RiskCheck(
            passed=passed,
            check_type="daily_loss",
            message=f"Daily loss {loss_pct:.2%} exceeds limit" if not passed else "OK",
            value=loss_pct,
            limit=self._limits.max_daily_loss
        )
    
    def check_drawdown(self, current_equity: float) -> RiskCheck:
        """Check maximum drawdown"""
        self._current_equity = current_equity
        
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
        
        drawdown = (self._peak_equity - current_equity) / self._peak_equity if self._peak_equity > 0 else 0
        
        passed = drawdown <= self._limits.max_drawdown
        
        return RiskCheck(
            passed=passed,
            check_type="max_drawdown",
            message=f"Drawdown {drawdown:.2%} exceeds limit" if not passed else "OK",
            value=drawdown,
            limit=self._limits.max_drawdown
        )
    
    def check_leverage(self, total_exposure: float, equity: float) -> RiskCheck:
        """Check leverage limits"""
        leverage = total_exposure / equity if equity > 0 else 0
        
        passed = leverage <= self._limits.max_leverage
        
        return RiskCheck(
            passed=passed,
            check_type="leverage",
            message=f"Leverage {leverage:.2f}x exceeds limit" if not passed else "OK",
            value=leverage,
            limit=self._limits.max_leverage
        )
    
    def check_all(self, portfolio_state: Dict[str, Any]) -> List[RiskCheck]:
        """Run all risk checks"""
        checks = []
        
        # Position size
        if "positions" in portfolio_state:
            for pos in portfolio_state["positions"]:
                checks.append(self.check_position_size(
                    pos.get("symbol"),
                    pos.get("size", 0),
                    pos.get("price", 0)
                ))
        
        # Portfolio exposure
        exposure = portfolio_state.get("total_exposure", 0)
        portfolio_value = portfolio_state.get("portfolio_value", 1)
        exposure_ratio = exposure / portfolio_value if portfolio_value > 0 else 0
        checks.append(self.check_portfolio_exposure(0, exposure_ratio))
        
        # Daily loss
        daily_pnl = portfolio_state.get("daily_pnl", 0)
        checks.append(self.check_daily_loss(daily_pnl))
        
        # Drawdown
        equity = portfolio_state.get("equity", 0)
        checks.append(self.check_drawdown(equity))
        
        # Leverage
        checks.append(self.check_leverage(exposure, equity))
        
        return checks
    
    def is_trading_allowed(self, portfolio_state: Dict[str, Any]) -> tuple[bool, str]:
        """Check if trading is allowed"""
        checks = self.check_all(portfolio_state)
        
        failed = [c for c in checks if not c.passed]
        
        if failed:
            return False, failed[0].message
        
        return True, "All risk checks passed"
