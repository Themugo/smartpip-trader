
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json

@dataclass
class ShadowDecision:
    decision_id: str
    timestamp: str
    symbol: str
    contract_type: str
    probability: float
    payout: float
    stake: float
    ev: float
    approved: bool
    outcome: Optional[int] = None
    pnl: Optional[float] = None

    def to_dict(self): return asdict(self)

class ShadowSession:
    """Records decisions against live observations without placing broker orders."""
    def __init__(self, path: str = "intelligence_data/phase7_shadow.jsonl"):
        self.path = path
        self.decisions = []

    def record(self, *, decision_id: str, symbol: str, contract_type: str, probability: float, payout: float, stake: float, ev: float, approved: bool) -> ShadowDecision:
        d = ShadowDecision(decision_id, datetime.now(timezone.utc).isoformat(), symbol, contract_type, probability, payout, stake, ev, approved)
        self.decisions.append(d)
        return d

    def settle(self, decision_id: str, outcome: int) -> ShadowDecision:
        for d in reversed(self.decisions):
            if d.decision_id == decision_id:
                d.outcome = int(outcome)
                d.pnl = d.stake * d.payout if d.outcome else -d.stake
                return d
        raise KeyError(decision_id)

    def flush(self) -> None:
        import pathlib
        p = pathlib.Path(self.path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            for d in self.decisions:
                f.write(json.dumps(d.to_dict(), sort_keys=True) + "\n")
        self.decisions.clear()
