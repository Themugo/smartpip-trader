"""Backup manifests and verified restore helpers."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class BackupManifest:
    backup_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {"backup_id": self.backup_id, "created_at": self.created_at.isoformat(), "files": self.files}


class BackupManager:
    def create_snapshot(self, source_dir: str, destination_dir: str, backup_id: str) -> BackupManifest:
        source = Path(source_dir)
        destination = Path(destination_dir) / backup_id
        destination.mkdir(parents=True, exist_ok=True)
        manifest = BackupManifest(backup_id=backup_id)
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            manifest.files[str(relative).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
        (destination / "manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    def verify_snapshot(self, destination_dir: str, manifest: BackupManifest) -> bool:
        root = Path(destination_dir) / manifest.backup_id
        for relative, expected_hash in manifest.files.items():
            path = root / relative
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                return False
        return True
