"""Unified Account Center for SmartPip Trader.

Public API
----------
DerivAuthManager   – OAuth authentication and session persistence.
AccountCenter      – Single entry point for account queries, switching, and portfolios.
PortfolioTracker   – In-memory position/P&L tracker with numpy-powered metrics.

Dataclasses
-----------
AuthResult         – Output of authentication attempts.
AccountInfo        – Metadata for one Deriv account.
TradeRecord        – One historical trade record.
PortfolioState     – Snapshot of the open portfolio.
AccountState       – Full state object for the trading engine.
PositionSnapshot   – Point-in-time position data held by the tracker.
PortfolioMetrics   – Aggregated portfolio-level metrics.
"""

from .auth import AuthResult, DerivAuthManager
from .account_center import (
    AccountCenter,
    AccountInfo,
    AccountState,
    PortfolioState,
    TradeRecord,
)
from .portfolio import PortfolioMetrics, PortfolioTracker, PositionSnapshot

__all__ = [
    "DerivAuthManager",
    "AuthResult",
    "AccountCenter",
    "AccountInfo",
    "AccountState",
    "PortfolioState",
    "TradeRecord",
    "PortfolioTracker",
    "PortfolioMetrics",
    "PositionSnapshot",
]
