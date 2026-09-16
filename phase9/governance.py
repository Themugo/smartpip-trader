"""Phase 9 governance: research run manifests, lineage, and reproducibility."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ResearchRun:
    run_id: str
    strategy_id: str
    model_version: str
    dataset_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    code_revision: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def canonical_payload(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "strategy_id": self.strategy_id,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "parameters": self.parameters,
            "code_revision": self.code_revision,
        }

    def fingerprint(self) -> str:
        payload = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {**self.canonical_payload(), "created_at": self.created_at.isoformat(), "fingerprint": self.fingerprint()}


class ResearchLedger:
    """Append-only JSONL ledger for research lineage."""

    def __init__(self, path: str = "intelligence_data/phase9_research_runs.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, run: ResearchRun) -> ResearchRun:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run.to_dict(), sort_keys=True) + "\n")
        return run

    def list_runs(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows


def stable_fingerprint(parts: Iterable[str]) -> str:
    """Build a deterministic fingerprint from ordered string parts."""
    material = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
