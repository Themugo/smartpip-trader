import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages database persistence via Supabase REST API"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
            "Content-Type": "application/json",
        }
        if not self.url or not self.key:
            logger.warning("Supabase credentials not configured, database persistence disabled")

    def _request(self, method: str, path: str, data: Any = None, params: str = "") -> Any:
        if not self.url or not self.key:
            return None
        url = f"{self.url}/rest/v1/{path}{params}"
        try:
            resp = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            resp.raise_for_status()
            if resp.status_code == 204:
                return None
            return resp.json()
        except Exception as e:
            logger.error(f"Supabase request failed: {e}")
            return None

    def save_trade(self, trade: Dict[str, Any]) -> bool:
        payload = {
            "market": trade.get("market", ""),
            "type": trade.get("type", ""),
            "direction": trade.get("direction", ""),
            "amount": float(trade.get("amount", 0)),
            "confidence": float(trade.get("confidence", 0)),
            "reason": trade.get("reason"),
            "entry_price": float(trade.get("entry_price", 0)),
            "entry_time": trade.get("entry_time", datetime.now().isoformat()),
            "exit_time": trade.get("exit_time"),
            "profit": trade.get("profit"),
            "contract_id": trade.get("contract_id"),
        }
        result = self._request("POST", "trades", payload)
        return result is not None

    def get_recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        params = f"?order=entry_time.desc&limit={limit}"
        result = self._request("GET", "trades", params=params)
        return result or []

    def update_statistics(self, stats: Dict[str, Any]) -> bool:
        payload = {
            "total_trades": stats.get("total_trades", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "win_rate": stats.get("win_rate", 0),
            "total_profit": stats.get("total_profit", 0),
            "session_pnl": stats.get("session_pnl", 0),
            "best_trade": stats.get("best_trade", 0),
            "worst_trade": stats.get("worst_trade", 0),
            "avg_win": stats.get("avg_win", 0),
            "avg_loss": stats.get("avg_loss", 0),
            "updated_at": datetime.now().isoformat(),
        }
        result = self._request("PATCH", "trade_statistics", payload, "?id=eq.1")
        return result is not None

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        result = self._request("GET", "trade_statistics", params="?id=eq.1")
        if result and len(result) > 0:
            return dict(result[0])
        return None

    def save_performance_metric(self, metric_name: str, metric_value: float) -> bool:
        payload = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "timestamp": datetime.now().isoformat(),
        }
        result = self._request("POST", "performance_metrics", payload)
        return result is not None

    def log_audit(self, action: str, actor: str, ip_address: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None) -> bool:
        payload = {
            "action": action,
            "actor": actor,
            "ip_address": ip_address,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        result = self._request("POST", "audit_log", payload)
        return result is not None

    def get_settings(self) -> Optional[Dict[str, Any]]:
        result = self._request("GET", "system_settings", params="?id=eq.1")
        if result and len(result) > 0:
            return dict(result[0])
        return None

    def update_settings(self, updates: Dict[str, Any]) -> bool:
        updates["updated_at"] = datetime.now().isoformat()
        result = self._request("PATCH", "system_settings", updates, "?id=eq.1")
        return result is not None
