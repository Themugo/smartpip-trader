"""Canonical Deriv options execution adapter.

Live orders follow the broker lifecycle: proposal -> buy -> proposal_open_contract.
The adapter never reads directly from the shared websocket; all messages are
correlated by DerivConnection.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DIGIT_TYPES = {
    "DIGITMATCH", "DIGITDIFF", "DIGITOVER", "DIGITUNDER", "DIGITEVEN", "DIGITODD",
}
DIRECTION_TYPES = {"CALL", "PUT", "RISEFALL", "RISE", "FALL"}


@dataclass(frozen=True)
class DerivProposal:
    id: str
    ask_price: float
    payout: float
    spot: Optional[float]
    proposal_raw: Dict[str, Any]

    @property
    def gross_return_multiple(self) -> float:
        return self.payout / self.ask_price if self.ask_price > 0 else 0.0

    @property
    def profit_multiple(self) -> float:
        return self.gross_return_multiple - 1.0


@dataclass(frozen=True)
class DerivTrade:
    contract_id: str
    proposal_id: str
    symbol: str
    contract_type: str
    amount: float
    buy_price: float
    payout: float
    entry_spot: Optional[float]
    opened_at: float
    raw: Dict[str, Any]


def expected_value_per_stake(win_probability: float, payout: float, stake: float) -> float:
    """Expected P&L in account currency using the broker quote.

    ``payout`` is treated as gross settlement and ``stake`` as the buy price.
    EV = p * payout - stake.
    """
    p = max(0.0, min(1.0, float(win_probability)))
    s = max(0.0, float(stake))
    return p * float(payout) - s


def required_win_probability(payout: float, stake: float) -> float:
    """Break-even win probability for a gross payout quote."""
    if payout <= 0:
        return 1.0
    return min(1.0, max(0.0, stake / payout))


class DerivExecutionAdapter:
    """One canonical execution adapter for the live trading system."""

    def __init__(self, connection):
        self.connection = connection
        self._open_contracts: Dict[str, DerivTrade] = {}
        self._contract_waiters: Dict[str, asyncio.Event] = {}
        self._contract_latest: Dict[str, Dict[str, Any]] = {}
        self._handlers_registered = False

    async def _ensure_handlers(self):
        if self._handlers_registered:
            return
        self.connection.add_handler("proposal_open_contract", self._on_contract_update)
        self._handlers_registered = True

    async def _on_contract_update(self, message: Dict[str, Any]):
        contract = message.get("proposal_open_contract") or {}
        cid = str(contract.get("contract_id")) if contract.get("contract_id") is not None else None
        if not cid:
            return
        self._contract_latest[cid] = contract
        if cid in self._contract_waiters and self._is_terminal(contract):
            self._contract_waiters[cid].set()

    @staticmethod
    def _is_terminal(contract: Dict[str, Any]) -> bool:
        if contract.get("is_sold") in (1, True):
            return True
        status = str(contract.get("status", "")).lower()
        return status in {"won", "lost", "sold", "expired"}

    async def get_proposal(
        self,
        *,
        symbol: str,
        contract_type: str,
        amount: float,
        currency: str,
        duration: int,
        duration_unit: str,
        barrier: Optional[str] = None,
        prediction: Optional[str] = None,
        timeout: float = 8.0,
    ) -> DerivProposal:
        if not self.connection.authorized:
            raise PermissionError("Deriv session is not authorized")
        if amount <= 0:
            raise ValueError("Trade amount must be positive")
        if duration <= 0:
            raise ValueError("Duration must be positive")
        payload: Dict[str, Any] = {
            "proposal": 1,
            "amount": float(amount),
            "basis": "stake",
            "contract_type": contract_type.upper(),
            "currency": currency,
            "duration": int(duration),
            "duration_unit": duration_unit,
            "underlying_symbol": symbol,
        }
        if barrier is not None:
            payload["barrier"] = str(barrier)
        if prediction is not None:
            payload["prediction"] = str(prediction)
        response = await self.connection.request(payload, timeout=timeout)
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "Proposal failed"))
        proposal = response.get("proposal") or {}
        proposal_id = proposal.get("id")
        if proposal_id is None:
            raise RuntimeError("Deriv returned no proposal id")
        ask = float(proposal.get("ask_price", proposal.get("display_value", 0)) or 0)
        payout = float(proposal.get("payout", 0) or 0)
        if ask <= 0 or payout <= 0:
            raise RuntimeError("Deriv proposal returned unusable pricing")
        spot = proposal.get("spot")
        return DerivProposal(
            id=str(proposal_id),
            ask_price=ask,
            payout=payout,
            spot=float(spot) if spot is not None else None,
            proposal_raw=proposal,
        )

    async def buy(self, proposal: DerivProposal, max_price: Optional[float] = None, timeout: float = 8.0) -> DerivTrade:
        await self._ensure_handlers()
        price = float(max_price if max_price is not None else proposal.ask_price)
        if price <= 0:
            raise ValueError('Buy price must be positive')
        if price > proposal.ask_price + 1e-12:
            raise ValueError('Buy price exceeds quoted proposal price')
        response = await self.connection.request(
            {"buy": proposal.id, "price": price},
            timeout=timeout,
        )
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "Buy failed"))
        buy = response.get("buy") or {}
        cid = buy.get("contract_id")
        if cid is None:
            raise RuntimeError("Deriv buy response contained no contract id")
        trade = DerivTrade(
            contract_id=str(cid),
            proposal_id=proposal.id,
            symbol=str(buy.get("underlying_symbol") or proposal.proposal_raw.get("underlying_symbol") or ""),
            contract_type=str(buy.get("contract_type") or proposal.proposal_raw.get("contract_type") or ""),
            amount=price,
            buy_price=float(buy.get("buy_price", price) or price),
            payout=float(buy.get("payout", proposal.payout) or proposal.payout),
            entry_spot=float(buy["spot"]) if buy.get("spot") is not None else proposal.spot,
            opened_at=time.time(),
            raw=buy,
        )
        self._open_contracts[trade.contract_id] = trade
        return trade

    async def watch_contract(self, contract_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        await self._ensure_handlers()
        cid = str(contract_id)
        response = await self.connection.request(
            {"proposal_open_contract": 1, "contract_id": int(cid) if cid.isdigit() else cid, "subscribe": 1},
            timeout=8.0,
        )
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "Contract subscription failed"))
        contract = response.get("proposal_open_contract") or {}
        self._contract_latest[cid] = contract
        if self._is_terminal(contract):
            self._open_contracts.pop(cid, None)
            self._contract_waiters.pop(cid, None)
            return contract
        event = self._contract_waiters.setdefault(cid, asyncio.Event())
        try:
            if timeout is None:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._contract_latest.get(cid, contract)
        finally:
            self._contract_waiters.pop(cid, None)
            self._open_contracts.pop(cid, None)

    async def sell(self, contract_id: str, price: float = 0.0, timeout: float = 8.0) -> Dict[str, Any]:
        response = await self.connection.request(
            {"sell": str(contract_id), "price": price},
            timeout=timeout,
        )
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "Sell failed"))
        return response.get("sell") or {}

    def get_open_contracts(self) -> Dict[str, DerivTrade]:
        return dict(self._open_contracts)
