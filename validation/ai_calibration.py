"""Evidence-driven AI calibration and contract EV validation.

Phase 2 is deliberately offline/paper-trading oriented. It does not place
orders. It evaluates probability forecasts against realized outcomes and the
actual contract economics supplied by Deriv proposals.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import defaultdict
from math import sqrt, log
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json


@dataclass(frozen=True)
class Opportunity:
    timestamp: str
    market: str
    contract_type: str
    duration: int
    regime: str
    probability: float
    payout: float
    stake: float
    won: Optional[bool] = None
    barrier: Optional[str] = None
    model_version: str = "unknown"

    @property
    def break_even_probability(self) -> float:
        if self.payout <= 0:
            return 1.0
        return min(1.0, max(0.0, self.stake / self.payout))

    @property
    def expected_value(self) -> float:
        # payout is gross settlement, stake is buy price.
        return self.probability * self.payout - self.stake

    @property
    def edge_over_break_even(self) -> float:
        return self.probability - self.break_even_probability


@dataclass
class CalibrationReport:
    sample_size: int
    brier_score: float
    log_loss: float
    ece: float
    mean_predicted_probability: float
    empirical_win_rate: float
    mean_ev: float
    positive_ev_rate: float
    groups: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationGate:
    passed: bool
    reasons: List[str]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp_probability(p: float) -> float:
    return min(1.0 - 1e-12, max(1e-12, float(p)))


def _ece(rows: Sequence[Opportunity], bins: int = 10) -> float:
    if not rows:
        return 1.0
    total = len(rows)
    error = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        bucket = [r for r in rows if lo <= r.probability < hi or (i == bins - 1 and r.probability <= hi)]
        if not bucket:
            continue
        empirical = sum(bool(r.won) for r in bucket) / len(bucket)
        predicted = sum(r.probability for r in bucket) / len(bucket)
        error += len(bucket) / total * abs(empirical - predicted)
    return error


def _wilson_interval(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    den = 1 + z*z/n
    centre = (p + z*z/(2*n)) / den
    margin = z * sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0.0, centre-margin), min(1.0, centre+margin))


def summarize(rows: Sequence[Opportunity]) -> CalibrationReport:
    realized = [r for r in rows if r.won is not None]
    if not realized:
        return CalibrationReport(0, 1.0, float('inf'), 1.0, 0.0, 0.0, 0.0, 0.0, [])
    brier = sum((r.probability - float(bool(r.won)))**2 for r in realized) / len(realized)
    logloss = -sum(float(bool(r.won))*log(_clamp_probability(r.probability)) + (1-float(bool(r.won)))*log(1-_clamp_probability(r.probability)) for r in realized) / len(realized)
    evs = [r.expected_value for r in realized]
    groups = []
    grouped: Dict[Tuple[str,str,int,str], List[Opportunity]] = defaultdict(list)
    for r in realized:
        grouped[(r.market, r.contract_type, r.duration, r.regime)].append(r)
    for (market, contract, duration, regime), g in sorted(grouped.items()):
        wins = sum(bool(x.won) for x in g)
        lo, hi = _wilson_interval(wins, len(g))
        groups.append({
            'market': market, 'contract_type': contract, 'duration': duration, 'regime': regime,
            'sample_size': len(g), 'win_rate': wins/len(g), 'win_rate_ci95': [lo,hi],
            'mean_probability': sum(x.probability for x in g)/len(g),
            'mean_ev': sum(x.expected_value for x in g)/len(g),
            'positive_ev_rate': sum(x.expected_value > 0 for x in g)/len(g),
            'break_even_probability': sum(x.break_even_probability for x in g)/len(g),
        })
    return CalibrationReport(
        sample_size=len(realized),
        brier_score=brier,
        log_loss=logloss,
        ece=_ece(realized),
        mean_predicted_probability=sum(x.probability for x in realized)/len(realized),
        empirical_win_rate=sum(bool(x.won) for x in realized)/len(realized),
        mean_ev=sum(evs)/len(evs),
        positive_ev_rate=sum(x > 0 for x in evs)/len(evs),
        groups=groups,
    )


def walk_forward(rows: Sequence[Opportunity], train_size: int, test_size: int, step: Optional[int] = None) -> List[Dict[str, Any]]:
    """Evaluate sequential OOS windows without shuffling or leakage.

    Training rows are returned as metadata only; model fitting belongs to the
    caller. This function defines the temporal split and evaluates each OOS
    window independently.
    """
    if train_size <= 0 or test_size <= 0:
        raise ValueError('train_size and test_size must be positive')
    ordered = sorted(rows, key=lambda x: x.timestamp)
    step = step or test_size
    out = []
    start = train_size
    while start + test_size <= len(ordered):
        train = ordered[start-train_size:start]
        test = ordered[start:start+test_size]
        rep = summarize(test)
        out.append({'train_start': train[0].timestamp, 'train_end': train[-1].timestamp,
                    'test_start': test[0].timestamp, 'test_end': test[-1].timestamp,
                    'train_size': len(train), 'test_size': len(test),
                    'oos': rep.to_dict()})
        start += step
    return out


def validation_gate(report: CalibrationReport, *, min_samples: int = 500,
                     max_ece: float = 0.08, max_brier: float = 0.25,
                     min_mean_ev: float = 0.0, min_positive_ev_rate: float = 0.55) -> ValidationGate:
    reasons=[]
    if report.sample_size < min_samples: reasons.append(f'insufficient samples: {report.sample_size} < {min_samples}')
    if report.ece > max_ece: reasons.append(f'calibration error too high: {report.ece:.4f} > {max_ece:.4f}')
    if report.brier_score > max_brier: reasons.append(f'brier score too high: {report.brier_score:.4f} > {max_brier:.4f}')
    if report.mean_ev <= min_mean_ev: reasons.append(f'mean EV not positive: {report.mean_ev:.6f}')
    if report.positive_ev_rate < min_positive_ev_rate: reasons.append(f'positive-EV rate too low: {report.positive_ev_rate:.3f} < {min_positive_ev_rate:.3f}')
    return ValidationGate(not reasons, reasons, {
        'sample_size': report.sample_size, 'ece': report.ece, 'brier_score': report.brier_score,
        'mean_ev': report.mean_ev, 'positive_ev_rate': report.positive_ev_rate,
    })


def load_jsonl(path: str) -> List[Opportunity]:
    rows=[]
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip(): rows.append(Opportunity(**json.loads(line)))
    return rows


def save_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, 'w', encoding='utf-8') as f: json.dump(payload, f, indent=2, default=str)
