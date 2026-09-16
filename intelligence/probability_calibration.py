"""Probability calibration store used by the canonical live approval path.

Artifacts are produced offline from settled opportunities. Live execution may
only use a calibrated probability when an artifact explicitly covers the
current contract context; otherwise the caller can fail closed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json

try:
    from sklearn.isotonic import IsotonicRegression
except Exception:  # pragma: no cover
    IsotonicRegression = None


def context_key(market: str, contract_type: str, duration: int, regime: str) -> str:
    return f"{market}|{contract_type.upper()}|{int(duration)}|{regime or 'UNKNOWN'}"


@dataclass(frozen=True)
class CalibrationResult:
    probability: float
    calibrated: bool
    source: str
    sample_size: int
    context: str


class ProbabilityCalibrator:
    """Load/apply offline isotonic calibration artifacts."""
    def __init__(self, path: str = "intelligence_data/calibration.json", min_context_samples: int = 200):
        self.path = Path(path)
        self.min_context_samples = min_context_samples
        self.artifact: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if self.path.exists():
            try:
                self.artifact = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                self.artifact = {"error": str(exc)}
        else:
            self.artifact = {}

    @property
    def ready(self) -> bool:
        return bool(self.artifact.get("global")) and not self.artifact.get("error")

    def transform(self, probability: float, *, market: str, contract_type: str, duration: int, regime: str) -> CalibrationResult:
        raw = max(0.0, min(1.0, float(probability)))
        key = context_key(market, contract_type, duration, regime)
        model = self.artifact.get("contexts", {}).get(key)
        source = key
        if not model or int(model.get("sample_size", 0)) < self.min_context_samples:
            model = self.artifact.get("global")
            source = "global"
        if not model:
            return CalibrationResult(raw, False, "uncalibrated", 0, key)
        xs = model.get("x", [])
        ys = model.get("y", [])
        if not xs or not ys or len(xs) != len(ys):
            return CalibrationResult(raw, False, "invalid_artifact", 0, key)
        if raw <= xs[0]: value = ys[0]
        elif raw >= xs[-1]: value = ys[-1]
        else:
            i = next(i for i in range(len(xs)-1) if xs[i] <= raw <= xs[i+1])
            span = xs[i+1]-xs[i]
            value = ys[i] if span <= 0 else ys[i] + (ys[i+1]-ys[i]) * ((raw-xs[i])/span)
        return CalibrationResult(max(0.0,min(1.0,float(value))), True, source, int(model.get("sample_size",0)), key)


def fit_artifact(rows: list[dict], *, min_context_samples: int = 200) -> Dict[str, Any]:
    """Fit global and sufficiently large context-specific isotonic models."""
    if IsotonicRegression is None:
        raise RuntimeError("scikit-learn is required to fit calibration artifacts")
    labeled=[r for r in rows if r.get("won") is not None]
    if len(labeled) < 2:
        raise ValueError("At least two labeled opportunities are required")

    def fit(sub):
        x=[max(0.0,min(1.0,float(r["probability"]))) for r in sub]
        y=[1 if bool(r["won"]) else 0 for r in sub]
        model=IsotonicRegression(y_min=0.0,y_max=1.0,out_of_bounds="clip").fit(x,y)
        xs=sorted(set(x))
        ys=[float(model.predict([v])[0]) for v in xs]
        return {"sample_size":len(sub),"x":xs,"y":ys}

    artifact={"version":1,"method":"isotonic","min_context_samples":min_context_samples,
              "global":fit(labeled),"contexts":{}}
    groups={}
    for r in labeled:
        k=context_key(str(r["market"]),str(r["contract_type"]),int(r["duration"]),str(r.get("regime") or "UNKNOWN"))
        groups.setdefault(k,[]).append(r)
    for k,sub in groups.items():
        if len(sub)>=min_context_samples:
            artifact["contexts"][k]=fit(sub)
    return artifact
