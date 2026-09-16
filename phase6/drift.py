
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List
import math

@dataclass(frozen=True)
class DriftReport:
    population_count: int
    recent_count: int
    mean_shift: float
    variance_ratio: float
    alert: bool
    reason: str

    def to_dict(self): return asdict(self)

class DriftMonitor:
    """Lightweight distribution-drift guard for production shadow/paper data."""
    def __init__(self, mean_shift_threshold: float = 0.15, variance_ratio_threshold: float = 2.0):
        self.mean_shift_threshold = mean_shift_threshold
        self.variance_ratio_threshold = variance_ratio_threshold

    def compare(self, baseline: Iterable[float], recent: Iterable[float]) -> DriftReport:
        b, r = list(baseline), list(recent)
        if len(b) < 2 or len(r) < 2:
            return DriftReport(len(b), len(r), 0.0, 1.0, True, "insufficient observations")
        bm, rm = sum(b)/len(b), sum(r)/len(r)
        bv = sum((x-bm)**2 for x in b)/(len(b)-1)
        rv = sum((x-rm)**2 for x in r)/(len(r)-1)
        scale = max(math.sqrt(bv), 1e-12)
        shift = abs(rm-bm)/scale
        ratio = rv/max(bv, 1e-12)
        alert = shift > self.mean_shift_threshold or ratio > self.variance_ratio_threshold or ratio < 1/self.variance_ratio_threshold
        reason = "distribution drift detected" if alert else "stable"
        return DriftReport(len(b), len(r), shift, ratio, alert, reason)
