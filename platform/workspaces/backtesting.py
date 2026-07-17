from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .base import WorkspaceBase

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    test_id: str
    strategy: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    win_rate: float
    equity_curve: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "profit_factor": self.profit_factor,
            "win_rate": self.win_rate,
            "equity_curve": self.equity_curve[-200:],
        }


class BacktestingWorkspace(WorkspaceBase):
    """Run strategies against historical data, view results, compare strategies."""

    def __init__(self) -> None:
        super().__init__("backtesting", "Backtesting", "history")
        self._results: List[BacktestResult] = []
        self._current_config: Dict[str, Any] = {
            "strategy": "",
            "symbol": "Volatility 75",
            "timeframe": "1m",
            "start_date": "",
            "end_date": "",
            "initial_balance": 10000.0,
        }

    def initialize(self) -> bool:
        logger.info("Backtesting workspace initialized")
        return True

    def get_layout(self) -> Dict[str, Any]:
        return {
            "columns": 3,
            "rows": 2,
            "panels": [
                {"id": "config_panel", "title": "Backtest Configuration", "col_span": 1, "row_span": 2, "widget": "config_form"},
                {"id": "equity_chart", "title": "Equity Curve", "col_span": 2, "row_span": 1, "widget": "line_chart"},
                {"id": "results_summary", "title": "Results Summary", "col_span": 2, "row_span": 1, "widget": "stats_grid"},
                {"id": "comparison", "title": "Strategy Comparison", "col_span": 3, "row_span": 1, "widget": "comparison_table"},
            ],
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        self._current_config.update(config)
        logger.info("Backtest config updated: %s", self._current_config)

    def run_backtest(self, strategy_signals: Optional[List[Dict[str, Any]]] = None) -> Optional[BacktestResult]:
        cfg = self._current_config
        if not cfg.get("strategy"):
            logger.error("No strategy selected for backtest")
            return None
        signals = strategy_signals or []
        balance = cfg.get("initial_balance", 10000.0)
        equity_curve = [balance]
        wins = 0
        losses = 0
        for sig in signals:
            pnl = sig.get("pnl", 0.0)
            balance += pnl
            equity_curve.append(balance)
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        total = wins + losses
        balance_arr = np.array(equity_curve) if equity_curve else np.array([balance])
        peaks = np.maximum.accumulate(balance_arr)
        drawdowns = (peaks - balance_arr) / np.where(peaks > 0, peaks, 1.0)
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        returns = np.diff(balance_arr) / np.where(balance_arr[:-1] > 0, balance_arr[:-1], 1.0) if len(balance_arr) > 1 else np.array([0.0])
        sharpe = float(np.mean(returns) / (np.std(returns) + 1e-10)) * np.sqrt(252) if len(returns) > 1 else 0.0
        gross_profit = float(np.sum(returns[returns > 0])) if len(returns) > 0 else 0.0
        gross_loss = float(np.abs(np.sum(returns[returns < 0]))) if len(returns) > 0 else 1.0
        pf = gross_profit / gross_loss if gross_loss > 0 else 0.0
        result = BacktestResult(
            test_id=f"BT{len(self._results)+1:04d}",
            strategy=cfg["strategy"],
            symbol=cfg.get("symbol", ""),
            timeframe=cfg.get("timeframe", ""),
            start_date=cfg.get("start_date", ""),
            end_date=cfg.get("end_date", ""),
            initial_balance=cfg.get("initial_balance", 10000.0),
            final_balance=balance,
            total_trades=total,
            winning_trades=wins,
            losing_trades=losses,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            profit_factor=pf,
            win_rate=wins / total if total > 0 else 0.0,
            equity_curve=equity_curve,
        )
        self._results.append(result)
        logger.info("Backtest complete: %s — trades=%d, sharpe=%.3f, dd=%.3f", result.test_id, total, sharpe, max_dd)
        return result

    def get_results(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results[-limit:]]

    def get_result(self, test_id: str) -> Optional[Dict[str, Any]]:
        for r in self._results:
            if r.test_id == test_id:
                return r.to_dict()
        return None

    def compare_strategies(self, test_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        targets = self._results if not test_ids else [r for r in self._results if r.test_id in test_ids]
        comparison = []
        for r in targets:
            comparison.append({
                "test_id": r.test_id,
                "strategy": r.strategy,
                "return_pct": ((r.final_balance - r.initial_balance) / r.initial_balance * 100) if r.initial_balance else 0,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "profit_factor": r.profit_factor,
                "total_trades": r.total_trades,
            })
        comparison.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
        return comparison

    def clear_results(self) -> None:
        self._results.clear()
        logger.info("Backtest results cleared")

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["state"]["config"] = self._current_config
        state["state"]["result_count"] = len(self._results)
        return state
