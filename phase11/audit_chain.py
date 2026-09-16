"""Tamper-evident audit chain for sensitive operational events."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class AuditEntry:
    event_id: str
    action: str
    actor_id: str
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def digest(self) -> str:
        payload = {
            "event_id": self.event_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "created_at": self.created_at.isoformat(),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AuditChain:
    def __init__(self, path: str = "data/audit/chain.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_id: str, action: str, actor_id: str, details: Dict[str, Any] | None = None) -> AuditEntry:
        previous = self.last_hash()
        entry = AuditEntry(event_id=event_id, action=action, actor_id=actor_id, details=details or {}, previous_hash=previous)
        row = {**entry.__dict__, "created_at": entry.created_at.isoformat(), "digest": entry.digest()}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return entry

    def last_hash(self) -> str:
        if not self.path.exists():
            return ""
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return ""
        return json.loads(lines[-1])["digest"]

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        previous = ""
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            entry = AuditEntry(
                event_id=row["event_id"], action=row["action"], actor_id=row["actor_id"],
                details=row.get("details", {}), previous_hash=row.get("previous_hash", ""),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            if entry.previous_hash != previous or entry.digest() != row.get("digest"):
                return False
            previous = row["digest"]
        return True
