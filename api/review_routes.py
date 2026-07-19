"""
review_routes.py — Project inspection & live Deriv data review endpoint.
Exposes a single /api/review endpoint with full system telemetry so the
ReviewPage can render a real-time project health dashboard.
"""
from __future__ import annotations
import asyncio
import json
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import websockets

logger = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    return Path(__file__).parent.parent


def _count_lines(p: Path) -> int:
    try:
        return sum(1 for _ in p.open("rb"))
    except Exception:
        return 0


def _scan_modules() -> List[Dict[str, Any]]:
    """Walk the project and return a inventory of key Python modules."""
    root = _repo_root()
    groups = {
        "Core":       ["core/connection.py", "core/account.py", "core/deriv_api.py"],
        "Trading":    ["trading_system.py", "trading/executor.py", "trading/trade_journal.py"],
        "ML":         ["ml/ensemble_predictor.py", "ml/feature_engineer.py"],
        "Analysis":   ["analysis/pattern_recognizer.py", "analysis/analysis_manager.py"],
        "Strategy":   ["strategies/unified_strategy.py"],
        "Analytics":  ["analytics/performance_metrics.py", "analytics/weekly_insights.py",
                       "analytics/strategy_recommender.py"],
        "API":        ["api/routes.py", "api/journal_routes.py", "api/review_routes.py"],
        "Config":     ["config/settings.py"],
        "Validation": ["validation/market_simulator.py"],
    }
    rows: List[Dict[str, Any]] = []
    for group, paths in groups.items():
        for rel in paths:
            p = root / rel
            rows.append({
                "group":  group,
                "path":   rel,
                "exists": p.exists(),
                "lines":  _count_lines(p) if p.exists() else 0,
                "size_kb": round(p.stat().st_size / 1024, 1) if p.exists() else 0,
            })
    return rows


def _scan_frontend() -> List[Dict[str, Any]]:
    root = _repo_root() / "src"
    rows: List[Dict[str, Any]] = []
    for p in sorted(root.rglob("*.tsx")):
        rows.append({
            "path":   str(p.relative_to(_repo_root())),
            "lines":  _count_lines(p),
            "size_kb": round(p.stat().st_size / 1024, 1),
        })
    return rows


def _api_endpoints() -> List[Dict[str, str]]:
    return [
        {"method": "GET",  "path": "/api/health",               "tag": "System"},
        {"method": "GET",  "path": "/api/status",               "tag": "System"},
        {"method": "POST", "path": "/api/start",                "tag": "Trading"},
        {"method": "POST", "path": "/api/stop",                 "tag": "Trading"},
        {"method": "POST", "path": "/api/reset",                "tag": "Trading"},
        {"method": "POST", "path": "/api/trade",                "tag": "Trading"},
        {"method": "GET",  "path": "/api/history",              "tag": "Trading"},
        {"method": "GET",  "path": "/api/markets",              "tag": "Market"},
        {"method": "POST", "path": "/api/market/{market}",      "tag": "Market"},
        {"method": "GET",  "path": "/api/signals",              "tag": "AI"},
        {"method": "GET",  "path": "/api/patterns",             "tag": "AI"},
        {"method": "GET",  "path": "/api/ml-status",            "tag": "AI"},
        {"method": "GET",  "path": "/api/entropy",              "tag": "AI"},
        {"method": "GET",  "path": "/api/settings",             "tag": "Config"},
        {"method": "POST", "path": "/api/settings",             "tag": "Config"},
        {"method": "POST", "path": "/api/backtest",             "tag": "Trading"},
        {"method": "GET",  "path": "/api/journal/entries",      "tag": "Journal"},
        {"method": "GET",  "path": "/api/journal/insights",     "tag": "Journal"},
        {"method": "GET",  "path": "/api/journal/recommendations", "tag": "Journal"},
        {"method": "GET",  "path": "/api/journal/heatmap",      "tag": "Journal"},
        {"method": "GET",  "path": "/api/review",               "tag": "Review"},
        {"method": "GET",  "path": "/api/review/deriv-account", "tag": "Review"},
        {"method": "GET",  "path": "/api/review/profit-table",  "tag": "Review"},
        {"method": "WS",   "path": "/ws",                       "tag": "Streaming"},
    ]


# ── Real Deriv data fetch (short-lived WS, no persistent connection) ──────────

DERIV_WS_URL = "wss://ws.binaryws.com/websockets/v3?app_id={app_id}"


async def _deriv_fetch(token: str, app_id: str, *requests) -> List[Dict[str, Any]]:
    """Open a temporary Deriv WS, auth, fire N requests, return responses, close."""
    url = DERIV_WS_URL.format(app_id=app_id)
    results: List[Dict[str, Any]] = []
    try:
        async with websockets.connect(url, open_timeout=8, close_timeout=4) as ws:
            # Authorize
            await ws.send(json.dumps({"authorize": token, "req_id": 0}))
            auth_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
            if auth_resp.get("error"):
                return [{"error": auth_resp["error"]["message"]}]

            for i, payload in enumerate(requests, start=1):
                payload["req_id"] = i
                await ws.send(json.dumps(payload))
                resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
                results.append(resp)
    except Exception as exc:
        results.append({"error": str(exc)})
    return results


async def _get_deriv_account(token: str, app_id: str) -> Dict[str, Any]:
    """Fetch real balance + account info from Deriv API."""
    results = await _deriv_fetch(
        token, app_id,
        {"balance": 1},
        {"get_account_status": 1},
    )
    out: Dict[str, Any] = {}
    for r in results:
        if "balance" in r:
            b = r["balance"]
            out.update({
                "balance":   round(float(b.get("balance", 0)), 2),
                "currency":  b.get("currency", "USD"),
                "loginid":   b.get("loginid", ""),
                "account_type": "real" if not str(b.get("loginid","")).startswith("VR") else "virtual",
            })
        if "get_account_status" in r:
            s = r["get_account_status"]
            out["status_flags"]       = s.get("status", [])
            out["risk_classification"] = s.get("risk_classification", "")
            out["cashier_validation"]  = s.get("cashier_validation", [])
    return out


async def _get_profit_table(token: str, app_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch real closed contracts from Deriv profit table."""
    results = await _deriv_fetch(
        token, app_id,
        {"profit_table": 1, "description": 1, "limit": limit, "sort": "DESC"},
    )
    trades: List[Dict[str, Any]] = []
    for r in results:
        if "profit_table" in r:
            for t in r["profit_table"].get("transactions", []):
                sell_price = t.get("sell_price")
                buy_price  = t.get("buy_price")
                pnl = None
                if sell_price is not None and buy_price is not None:
                    pnl = round(float(sell_price) - float(buy_price), 4)
                trades.append({
                    "contract_id":   t.get("contract_id"),
                    "contract_type": t.get("contract_type"),
                    "shortcode":     t.get("shortcode", ""),
                    "buy_price":     float(buy_price)  if buy_price  is not None else None,
                    "sell_price":    float(sell_price) if sell_price is not None else None,
                    "pnl":           pnl,
                    "duration":      t.get("duration_type", ""),
                    "purchase_time": t.get("purchase_time"),
                    "sell_time":     t.get("sell_time"),
                    "app_id":        t.get("app_id"),
                })
    return trades


# ── Route setup ───────────────────────────────────────────────────────────────

def setup_review_routes(app: FastAPI, trading_system) -> None:

    @app.get("/api/review", tags=["Review"], summary="Full system review — all telemetry in one call")
    async def get_review(request: Request):
        _boot = getattr(app.state, "boot_time", time.time())

        state   = trading_system.get_full_state()
        stats   = state.get("stats", {})
        ticks   = list(getattr(trading_system, "price_history", []))
        digits  = list(getattr(trading_system, "digit_history", []))
        analysis = getattr(trading_system, "analysis", None)

        # ML signals
        signals  = analysis.get_trade_signals()  if analysis else []
        consensus= analysis.get_best_prediction() if analysis else {}
        entropy  = round(analysis.get_market_entropy(), 4) if analysis else None

        # Digit frequency from live data
        digit_freq: Dict[int, int] = {d: 0 for d in range(10)}
        for d in digits[-200:]:
            digit_freq[int(d)] += 1

        # Win streak
        history = state.get("trade_history", [])
        wins    = sum(1 for t in history if (t.get("profit") or 0) > 0)
        losses  = len(history) - wins

        # Module scan
        modules  = _scan_modules()
        frontend = _scan_frontend()
        existing = sum(1 for m in modules if m["exists"])
        total_lines = sum(m["lines"] for m in modules)

        return JSONResponse({
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
            "uptime_seconds": round(time.time() - _boot),
            "python_version": platform.python_version(),
            "system": {
                "status":         state.get("status", "unknown"),
                "market":         state.get("market", "R_100"),
                "tick_count":     len(ticks),
                "last_price":     ticks[-1] if ticks else None,
                "last_digit":     digits[-1] if digits else None,
                "digit_freq":     digit_freq,
                "latency_ms":     state.get("latency_ms", 0),
            },
            "account": {
                "balance":   getattr(trading_system, "account", None) and
                             getattr(trading_system.account, "current_balance", 0),
                "currency":  getattr(trading_system, "account", None) and
                             getattr(trading_system.account, "currency", "USD"),
                "active_account": getattr(trading_system, "account", None) and
                                  getattr(trading_system.account, "active_account", "demo"),
            },
            "performance": {
                "total_trades": stats.get("total_trades", 0),
                "wins":         wins,
                "losses":       losses,
                "win_rate":     round(wins / len(history) * 100, 1) if history else 0.0,
                "total_pnl":    round(stats.get("total_profit", 0), 4),
                "profit_factor": stats.get("profit_factor", 0),
                "max_drawdown": stats.get("max_drawdown", 0),
            },
            "ai": {
                "signals_count":    len(signals),
                "consensus":        consensus,
                "market_entropy":   entropy,
                "top_signals":      signals[:5],
            },
            "modules": {
                "backend_total":    len(modules),
                "backend_present":  existing,
                "backend_missing":  len(modules) - existing,
                "total_lines":      total_lines,
                "inventory":        modules,
            },
            "frontend": {
                "component_count": len(frontend),
                "total_lines":     sum(f["lines"] for f in frontend),
                "components":      frontend,
            },
            "api_endpoints": _api_endpoints(),
        })

    @app.get("/api/review/deriv-account", tags=["Review"], summary="Fetch real Deriv account data")
    async def get_deriv_account_live(api_token: Optional[str] = None, app_id: str = "1089"):
        token = api_token or os.getenv("DERIV_API_TOKEN", "")
        if not token:
            return JSONResponse({"error": "No DERIV_API_TOKEN set. Provide ?api_token=..."}, status_code=400)
        try:
            data = await asyncio.wait_for(_get_deriv_account(token, app_id), timeout=15)
            return JSONResponse(data)
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Deriv API timeout"}, status_code=504)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

    @app.get("/api/review/profit-table", tags=["Review"], summary="Fetch real closed contracts from Deriv")
    async def get_profit_table_live(api_token: Optional[str] = None, app_id: str = "1089", limit: int = 30):
        token = api_token or os.getenv("DERIV_API_TOKEN", "")
        if not token:
            return JSONResponse({"error": "No DERIV_API_TOKEN set. Provide ?api_token=..."}, status_code=400)
        try:
            trades = await asyncio.wait_for(_get_profit_table(token, app_id, min(limit, 100)), timeout=20)
            wins   = [t for t in trades if (t.get("pnl") or 0) > 0]
            total  = sum((t.get("pnl") or 0) for t in trades)
            return JSONResponse({
                "count":    len(trades),
                "wins":     len(wins),
                "losses":   len(trades) - len(wins),
                "total_pnl": round(total, 4),
                "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
                "trades":   trades,
            })
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Deriv API timeout"}, status_code=504)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
