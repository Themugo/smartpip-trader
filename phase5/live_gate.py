"""Final fail-closed live-trading certificate gate."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


class LiveCertificateGate:
    """Requires a valid Phase-5 certificate plus explicit runtime opt-in."""
    def __init__(self, path: str = "intelligence_data/production_certificate.json"):
        self.path = Path(path)

    def status(self, *, live_enabled: bool, confirmation: str = "") -> Dict[str, Any]:
        if not live_enabled:
            return {"allowed": False, "reason": "LIVE_TRADING_ENABLED is false", "certificate": None}
        if confirmation != "I_UNDERSTAND_LIVE_RISK":
            return {"allowed": False, "reason": "explicit live-risk confirmation missing", "certificate": None}
        if not self.path.exists():
            return {"allowed": False, "reason": "production certificate missing", "certificate": None}
        try:
            cert = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"allowed": False, "reason": f"production certificate unreadable: {exc}", "certificate": None}
        if cert.get("certified") is not True:
            return {"allowed": False, "reason": "production certificate is not certified", "certificate": cert}
        return {"allowed": True, "reason": "production certificate and explicit opt-in present", "certificate": cert}
