"""Phase 5: production certification gate.

Certification is a *permission prerequisite*, never an automatic live-trading
switch. The default outcome is blocked. A certificate is invalidated when its
inputs or model version change.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib, json


@dataclass(frozen=True)
class CertificationPolicy:
    min_oos_samples: int = 500
    min_oos_mean_ev: float = 0.0
    min_oos_positive_ev_rate: float = 0.55
    max_oos_ece: float = 0.08
    max_paper_drawdown: float = 0.20
    min_paper_trades: int = 200
    min_paper_approved_trades: int = 50
    require_calibration: bool = True


@dataclass(frozen=True)
class CertificationResult:
    certified: bool
    reasons: List[str]
    checks: Dict[str, Any]
    issued_at: str
    certificate_id: str
    live_enablement_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionCertification:
    """Fail-closed certification over Phase 3 OOS + Phase 4 paper evidence."""

    def __init__(self, policy: Optional[CertificationPolicy] = None):
        self.policy = policy or CertificationPolicy()

    def evaluate(self, *, oos_report: Dict[str, Any], paper_report: Dict[str, Any], calibration_ready: bool, model_version: str) -> CertificationResult:
        p = self.policy
        reasons: List[str] = []
        checks: Dict[str, Any] = {}
        oos_n = int(oos_report.get("sample_size", 0))
        checks["oos_samples"] = oos_n
        if oos_n < p.min_oos_samples:
            reasons.append(f"OOS samples {oos_n} < {p.min_oos_samples}")
        checks["oos_mean_ev"] = float(oos_report.get("mean_ev", 0.0))
        if checks["oos_mean_ev"] <= p.min_oos_mean_ev:
            reasons.append("OOS mean EV is not positive")
        checks["oos_positive_ev_rate"] = float(oos_report.get("positive_ev_rate", 0.0))
        if checks["oos_positive_ev_rate"] < p.min_oos_positive_ev_rate:
            reasons.append("OOS positive-EV rate is below policy")
        checks["oos_ece"] = float(oos_report.get("ece", 1.0))
        if checks["oos_ece"] > p.max_oos_ece:
            reasons.append("OOS calibration error exceeds policy")
        checks["paper_decisions"] = int(paper_report.get("paper_decisions", 0))
        checks["paper_approved_trades"] = int(paper_report.get("approved_trades", 0))
        checks["paper_drawdown"] = float(paper_report.get("max_drawdown", 1.0))
        if checks["paper_decisions"] < p.min_paper_trades:
            reasons.append("insufficient paper-trading observations")
        if checks["paper_approved_trades"] < p.min_paper_approved_trades:
            reasons.append("insufficient approved paper trades")
        if checks["paper_drawdown"] > p.max_paper_drawdown:
            reasons.append("paper drawdown exceeds policy")
        checks["calibration_ready"] = bool(calibration_ready)
        if p.require_calibration and not calibration_ready:
            reasons.append("calibration artifact is not ready")
        payload = json.dumps({"model_version": model_version, "checks": checks}, sort_keys=True).encode()
        certificate_id = hashlib.sha256(payload).hexdigest()[:20]
        return CertificationResult(
            certified=not reasons,
            reasons=reasons,
            checks=checks,
            issued_at=datetime.now(timezone.utc).isoformat(),
            certificate_id=certificate_id,
            live_enablement_required=True,
        )


def write_certificate(result: CertificationResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)
