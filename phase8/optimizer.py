
"""Phase 8: constrained strategy optimization with immutable-style promotion records."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
import hashlib, json

@dataclass(frozen=True)
class OptimizationResult:
    strategy_id: str
    baseline_ev: float
    candidate_ev: float
    improvement: float
    oos_samples: int
    max_drawdown: float
    accepted: bool
    reasons: List[str]
    candidate: Dict[str, Any]
    created_at: str

    def to_dict(self): return asdict(self)

class ConstrainedOptimizer:
    """Never promotes on in-sample improvement alone."""
    def __init__(self, min_oos_samples: int = 500, min_improvement: float = 0.02, max_drawdown: float = 0.20):
        self.min_oos_samples = min_oos_samples
        self.min_improvement = min_improvement
        self.max_drawdown = max_drawdown

    def evaluate(self, strategy_id: str, baseline_ev: float, candidate_ev: float, oos_samples: int, max_drawdown: float, candidate: Dict[str, Any]) -> OptimizationResult:
        reasons=[]
        improvement = candidate_ev - baseline_ev
        if oos_samples < self.min_oos_samples: reasons.append("insufficient OOS samples")
        if improvement < self.min_improvement: reasons.append("OOS EV improvement below threshold")
        if max_drawdown > self.max_drawdown: reasons.append("candidate drawdown exceeds limit")
        if not candidate.get("model_version"): reasons.append("model version missing")
        return OptimizationResult(strategy_id, baseline_ev, candidate_ev, improvement, oos_samples, max_drawdown, not reasons, reasons, candidate, datetime.now(timezone.utc).isoformat())

    @staticmethod
    def fingerprint(result: OptimizationResult) -> str:
        payload=json.dumps(result.to_dict(), sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()

    def promote(self, result: OptimizationResult, ledger_path: str = "intelligence_data/phase8_promotions.jsonl") -> str:
        if not result.accepted:
            raise ValueError("optimization result is not promotable")
        record={"fingerprint": self.fingerprint(result), "result": result.to_dict()}
        from pathlib import Path
        p=Path(ledger_path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f: f.write(json.dumps(record, sort_keys=True)+"\n")
        return record["fingerprint"]
