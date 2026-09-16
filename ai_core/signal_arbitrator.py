"""Contract-aware signal arbitration for SmartPip live decisions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ArbitrationResult:
    contract_type: Optional[str]
    direction: Optional[str]
    confidence: float
    probability: float
    agreement: float
    reason: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def approved(self) -> bool:
        return self.contract_type is not None and self.probability > 0


class SignalArbitrator:
    """Selects one executable contract without mixing incompatible outcome spaces."""

    def arbitrate(self, analyzer_output: Dict[str, Any], min_confidence: float = 70.0) -> ArbitrationResult:
        candidates: List[Dict[str, Any]] = []
        for name, payload in analyzer_output.items():
            if not isinstance(payload, dict):
                continue
            prediction = payload.get("prediction")
            confidence = float(payload.get("confidence") or 0)
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            if not prediction or confidence < min_confidence:
                continue

            contract_type = data.get("contract_type") or data.get("contractType")
            direction = str(prediction).upper()
            if not contract_type:
                mapping = {
                    "EVEN": "DIGITEVEN", "ODD": "DIGITODD",
                    "OVER": "DIGITOVER", "UNDER": "DIGITUNDER",
                    "MATCH": "DIGITMATCH", "DIFF": "DIGITDIFF",
                    "RISE": "CALL", "FALL": "PUT",
                    "CALL": "CALL", "PUT": "PUT",
                }
                contract_type = mapping.get(direction)
            if not contract_type:
                continue
            candidates.append({
                "analyzer": name, "contract_type": str(contract_type).upper(),
                "direction": direction, "confidence": confidence,
                "probability": float(data.get("probability", confidence / 100.0) or 0),
            })

        if not candidates:
            return ArbitrationResult(None, None, 0.0, 0.0, 0.0, "No executable contract signal", [])

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate["contract_type"], []).append(candidate)
        best_type, best_group = max(
            grouped.items(),
            key=lambda item: sum(c["confidence"] for c in item[1]) / len(item[1]),
        )
        best = max(best_group, key=lambda c: c["confidence"])
        agreement = len(best_group) / len(candidates)
        avg_conf = sum(c["confidence"] for c in best_group) / len(best_group)
        avg_prob = sum(c["probability"] for c in best_group) / len(best_group)
        return ArbitrationResult(
            contract_type=best_type,
            direction=best["direction"],
            confidence=avg_conf,
            probability=max(0.0, min(1.0, avg_prob)),
            agreement=agreement,
            reason=f"{len(best_group)}/{len(candidates)} compatible signals selected {best_type}",
            evidence=candidates,
        )
