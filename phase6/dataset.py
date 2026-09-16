
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
import csv, hashlib, json

@dataclass(frozen=True)
class DatasetRow:
    timestamp: str
    symbol: str
    price: float
    outcome_price: Optional[float] = None
    contract_type: Optional[str] = None
    duration: Optional[int] = None
    barrier: Optional[float] = None
    regime: Optional[str] = None
    proposal_price: Optional[float] = None
    payout: Optional[float] = None
    outcome: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    created_at: str
    source_files: List[Dict[str, Any]]
    row_count: int
    symbols: List[str]
    time_start: Optional[str]
    time_end: Optional[str]
    schema_version: str = "phase6.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class DatasetBuilder:
    """Build deterministic, auditable datasets without random train/test leakage."""

    def __init__(self, schema_version: str = "phase6.v1"):
        self.schema_version = schema_version

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def load(self, paths: Sequence[str | Path]) -> List[DatasetRow]:
        rows: List[DatasetRow] = []
        for raw in paths:
            path = Path(raw)
            if path.suffix.lower() == ".csv":
                with path.open("r", encoding="utf-8", newline="") as f:
                    for r in csv.DictReader(f):
                        rows.append(self._row(r))
            elif path.suffix.lower() in {".json", ".jsonl"}:
                text = path.read_text(encoding="utf-8")
                items = [json.loads(x) for x in text.splitlines() if x.strip()] if path.suffix.lower()==".jsonl" else json.loads(text)
                if isinstance(items, dict):
                    items = items.get("rows", [])
                rows.extend(self._row(r) for r in items)
            else:
                raise ValueError(f"Unsupported dataset format: {path}")
        rows.sort(key=lambda x: (x.timestamp, x.symbol, x.price))
        return rows

    @staticmethod
    def _row(r: Dict[str, Any]) -> DatasetRow:
        def opt_float(v):
            return None if v in (None, "") else float(v)
        def opt_int(v):
            return None if v in (None, "") else int(v)
        return DatasetRow(
            timestamp=str(r["timestamp"]),
            symbol=str(r["symbol"]),
            price=float(r["price"]),
            outcome_price=opt_float(r.get("outcome_price")),
            contract_type=r.get("contract_type") or None,
            duration=opt_int(r.get("duration")),
            barrier=opt_float(r.get("barrier")),
            regime=r.get("regime") or None,
            proposal_price=opt_float(r.get("proposal_price")),
            payout=opt_float(r.get("payout")),
            outcome=opt_int(r.get("outcome")),
        )

    def manifest(self, paths: Sequence[str | Path], rows: Sequence[DatasetRow]) -> DatasetManifest:
        files = []
        for p in paths:
            path = Path(p)
            files.append({"path": str(path), "sha256": self._sha256(path), "bytes": path.stat().st_size})
        timestamps = [r.timestamp for r in rows]
        symbols = sorted({r.symbol for r in rows})
        payload = {"schema": self.schema_version, "files": files, "rows": len(rows), "symbols": symbols, "start": min(timestamps) if timestamps else None, "end": max(timestamps) if timestamps else None}
        dataset_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
        return DatasetManifest(dataset_id, datetime.now(timezone.utc).isoformat(), files, len(rows), symbols, payload["start"], payload["end"], self.schema_version)

    def write(self, rows: Iterable[DatasetRow], manifest: DatasetManifest, out_dir: str | Path) -> Path:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        data_path = out / f"dataset-{manifest.dataset_id}.jsonl"
        with data_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")
        (out / f"dataset-{manifest.dataset_id}.manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return data_path
