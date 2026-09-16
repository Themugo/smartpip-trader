"""Phase 3: historical opportunity generation and walk-forward laboratory.

This module is broker-economics aware but never places an order. It replays
ordered tick data, asks a supplied predictor for a probability, evaluates the
contract against a supplied historical quote, and records the outcome after
its expiry.  It intentionally requires quotes when EV is evaluated; synthetic
payout assumptions are never silently substituted.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
import csv, json

from validation.ai_calibration import Opportunity, summarize, walk_forward


@dataclass(frozen=True)
class HistoricalTick:
    timestamp: str
    symbol: str
    price: float
    digit: Optional[int] = None
    epoch: Optional[float] = None

    @classmethod
    def from_mapping(cls, row: Dict[str, Any]) -> "HistoricalTick":
        price = float(row.get("price", row.get("quote")))
        digit = row.get("digit")
        if digit is None:
            text = format(price, ".8f").rstrip("0")
            digit = int(text[-1]) if text and text[-1].isdigit() else None
        return cls(
            timestamp=str(row.get("timestamp", row.get("epoch", ""))),
            symbol=str(row.get("symbol", row.get("market", ""))),
            price=price,
            digit=int(digit) if digit is not None else None,
            epoch=float(row["epoch"]) if row.get("epoch") is not None else None,
        )


def load_ticks(path: str) -> List[HistoricalTick]:
    """Load ordered ticks from JSONL, JSON array, or CSV."""
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            return [HistoricalTick.from_mapping(r) for r in csv.DictReader(f)]
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if text.startswith("["):
        return [HistoricalTick.from_mapping(r) for r in json.loads(text)]
    return [HistoricalTick.from_mapping(json.loads(line)) for line in text.splitlines() if line.strip()]


def _digit(tick: HistoricalTick) -> int:
    if tick.digit is not None:
        return int(tick.digit)
    text = format(tick.price, ".8f").rstrip("0")
    return int(text[-1])


def _won(contract_type: str, entry: HistoricalTick, expiry: HistoricalTick, barrier: Optional[str], prediction: Optional[str]) -> Optional[bool]:
    c = contract_type.upper()
    if c in {"CALL", "RISE", "RISEFALL"}:
        return expiry.price > entry.price if c != "RISEFALL" or prediction is None else (expiry.price > entry.price if prediction.upper() == "CALL" else expiry.price < entry.price)
    if c in {"PUT", "FALL"}:
        return expiry.price < entry.price
    d = _digit(expiry)
    if c == "DIGITEVEN": return d % 2 == 0
    if c == "DIGITODD": return d % 2 == 1
    if c == "DIGITMATCH": return barrier is not None and d == int(float(barrier))
    if c == "DIGITDIFF": return barrier is not None and d != int(float(barrier))
    if c == "DIGITOVER": return barrier is not None and d > int(float(barrier))
    if c == "DIGITUNDER": return barrier is not None and d < int(float(barrier))
    return None


class HistoricalOpportunityEngine:
    """Generate realistic historical opportunities from a predictor and quotes."""

    def generate(
        self,
        ticks: Sequence[HistoricalTick],
        *,
        market: Optional[str] = None,
        contract_type: str,
        duration: int,
        regime: str = "UNKNOWN",
        stake: float = 1.0,
        predictor: Callable[[Sequence[HistoricalTick]], float],
        quote_provider: Callable[[HistoricalTick, str, int], Dict[str, Any]],
        barrier: Optional[str] = None,
        prediction: Optional[str] = None,
        model_version: str = "historical-lab-v1",
    ) -> List[Opportunity]:
        if duration <= 0:
            raise ValueError("duration must be positive")
        ordered = list(ticks)
        rows: List[Opportunity] = []
        for i in range(max(0, len(ordered) - duration)):
            entry = ordered[i]
            if market and entry.symbol != market:
                continue
            history = ordered[: i + 1]
            try:
                probability = float(predictor(history))
                quote = quote_provider(entry, contract_type, duration)
                payout = float(quote["payout"])
                quote_stake = float(quote.get("stake", stake))
            except (KeyError, TypeError, ValueError):
                continue
            expiry = ordered[i + duration]
            won = _won(contract_type, entry, expiry, barrier, prediction)
            if won is None:
                continue
            rows.append(Opportunity(
                timestamp=entry.timestamp,
                market=entry.symbol,
                contract_type=contract_type.upper(),
                duration=duration,
                regime=regime,
                probability=max(0.0, min(1.0, probability)),
                payout=payout,
                stake=quote_stake,
                won=won,
                barrier=barrier,
                model_version=model_version,
            ))
        return rows

    @staticmethod
    def matrix(rows: Sequence[Opportunity], *, train_size: int = 500, test_size: int = 100) -> Dict[str, Any]:
        """Return grouped metrics plus temporal OOS windows."""
        report = summarize(rows).to_dict()
        report["walk_forward"] = walk_forward(rows, train_size=train_size, test_size=test_size)
        return report

    @staticmethod
    def save_jsonl(rows: Iterable[Opportunity], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(asdict(row), default=str) + "\n")
