"""Deterministic release gate for research-to-production promotion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str = ""


@dataclass
class ReleaseReport:
    release_id: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def to_dict(self) -> Dict[str, object]:
        return {
            "release_id": self.release_id,
            "passed": self.passed,
            "checks": [check.__dict__ for check in self.checks],
        }


class ReleaseGate:
    def __init__(self, checks: Dict[str, Callable[[], bool]] | None = None) -> None:
        self._checks = checks or {}

    def evaluate(self, release_id: str) -> ReleaseReport:
        results: List[CheckResult] = []
        for name, check in self._checks.items():
            try:
                passed = bool(check())
                details = "ok" if passed else "check returned false"
            except Exception as exc:
                passed = False
                details = f"check failed: {type(exc).__name__}"
            results.append(CheckResult(name=name, passed=passed, details=details))
        return ReleaseReport(release_id=release_id, checks=results)
