
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
import math

@dataclass(frozen=True)
class ModelHealth:
    samples: int
    win_rate: float
    mean_ev: float
    brier: float
    healthy: bool
    reasons: list[str]
    def to_dict(self): return asdict(self)

class ModelHealthMonitor:
    """Conservative live-health monitor; unhealthy state should stop promotion."""
    def evaluate(self, probabilities: Iterable[float], outcomes: Iterable[int], evs: Iterable[float], min_samples: int = 100) -> ModelHealth:
        p, y, e = list(probabilities), list(outcomes), list(evs)
        n = min(len(p), len(y), len(e))
        if n == 0:
            return ModelHealth(0, 0.0, 0.0, 1.0, False, ["no settled observations"])
        p, y, e = p[:n], y[:n], e[:n]
        win = sum(y)/n
        brier = sum((a-b)**2 for a,b in zip(p,y))/n
        mean_ev = sum(e)/n
        reasons=[]
        if n < min_samples: reasons.append("insufficient settled observations")
        if mean_ev <= 0: reasons.append("mean EV is not positive")
        if not math.isfinite(brier): reasons.append("invalid calibration metric")
        return ModelHealth(n, win, mean_ev, brier, not reasons, reasons)
