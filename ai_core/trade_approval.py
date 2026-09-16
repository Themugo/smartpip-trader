"""Final trade approval gate shared by API/manual/automated execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from trading.deriv_execution import expected_value_per_stake


@dataclass(frozen=True)
class ApprovalResult:
    approved: bool
    reasons: List[str] = field(default_factory=list)
    expected_value: float = 0.0
    win_probability: float = 0.0
    risk_score: float = 0.0


class TradeApprover:
    """Hard fail-closed gate for a quoted Deriv contract."""

    def approve(
        self,
        *,
        win_probability: float,
        payout: float,
        stake: float,
        min_expected_value: float = 0.0,
        min_probability: float = 0.55,
        risk_score: float = 0.0,
        max_risk_score: float = 50.0,
        model_ready: bool = True,
        market_data_fresh: bool = True,
    ) -> ApprovalResult:
        reasons: List[str] = []
        p = max(0.0, min(1.0, float(win_probability)))
        ev = expected_value_per_stake(p, payout, stake)
        if not model_ready:
            reasons.append("AI model not ready")
        if not market_data_fresh:
            reasons.append("market data stale")
        if p < min_probability:
            reasons.append(f"win probability {p:.3f} below {min_probability:.3f}")
        if ev < min_expected_value:
            reasons.append(f"EV {ev:.6f} below {min_expected_value:.6f}")
        if risk_score > max_risk_score:
            reasons.append(f"risk score {risk_score:.1f} above {max_risk_score:.1f}")
        return ApprovalResult(
            approved=not reasons, reasons=reasons, expected_value=ev,
            win_probability=p, risk_score=float(risk_score),
        )
