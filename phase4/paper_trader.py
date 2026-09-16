"""Phase 4: deterministic paper trading against live/historical opportunities.

Paper trading uses the same approval gate as live execution, but it never calls
Deriv buy/sell. It records every decision, including abstentions and rejects,
so live-vs-paper comparisons are auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence
import json, math, time

from ai_core.trade_approval import TradeApprover
from validation.ai_calibration import Opportunity, summarize


@dataclass
class PaperDecision:
    timestamp: str
    market: str
    contract_type: str
    duration: int
    probability: float
    payout: float
    stake: float
    expected_value: float
    approved: bool
    reasons: List[str]
    won: Optional[bool]
    pnl: float
    model_version: str


class PaperTrader:
    """Paper execution engine with the production approval contract."""

    def __init__(self, *, approver: Optional[TradeApprover] = None, min_probability: float = 0.55, min_expected_value: float = 0.0):
        self.approver = approver or TradeApprover()
        self.min_probability = min_probability
        self.min_expected_value = min_expected_value
        self.decisions: List[PaperDecision] = []
        self.equity = 0.0
        self.peak_equity = 0.0
        self.max_drawdown = 0.0

    def evaluate(self, opportunity: Opportunity, *, model_ready: bool = True, market_data_fresh: bool = True) -> PaperDecision:
        approval = self.approver.approve(
            win_probability=opportunity.probability,
            payout=opportunity.payout,
            stake=opportunity.stake,
            min_expected_value=self.min_expected_value,
            min_probability=self.min_probability,
            model_ready=model_ready,
            market_data_fresh=market_data_fresh,
        )
        pnl = 0.0
        if approval.approved and opportunity.won is not None:
            pnl = opportunity.payout - opportunity.stake if opportunity.won else -opportunity.stake
            self.equity += pnl
            self.peak_equity = max(self.peak_equity, self.equity)
            if self.peak_equity > 0:
                self.max_drawdown = max(self.max_drawdown, (self.peak_equity - self.equity) / self.peak_equity)
        decision = PaperDecision(
            timestamp=opportunity.timestamp, market=opportunity.market,
            contract_type=opportunity.contract_type, duration=opportunity.duration,
            probability=opportunity.probability, payout=opportunity.payout,
            stake=opportunity.stake, expected_value=approval.expected_value,
            approved=approval.approved, reasons=approval.reasons, won=opportunity.won,
            pnl=pnl, model_version=opportunity.model_version,
        )
        self.decisions.append(decision)
        return decision

    def run(self, opportunities: Sequence[Opportunity]) -> Dict[str, Any]:
        for opportunity in opportunities:
            self.evaluate(opportunity)
        realized = [Opportunity(
            timestamp=d.timestamp, market=d.market, contract_type=d.contract_type,
            duration=d.duration, regime="UNKNOWN", probability=d.probability,
            payout=d.payout, stake=d.stake, won=d.won, model_version=d.model_version,
        ) for d in self.decisions if d.approved]
        report = summarize(realized).to_dict()
        report.update({
            "paper_decisions": len(self.decisions),
            "approved_trades": sum(d.approved for d in self.decisions),
            "equity_change": self.equity,
            "max_drawdown": self.max_drawdown,
        })
        return report

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for decision in self.decisions:
                f.write(json.dumps(asdict(decision), default=str) + "\n")
