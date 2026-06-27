"""
Journal API routes — full CRUD + analytics endpoints for the trade journal.
Mounts at /api/journal/...
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse

from trading.trade_journal import TradeJournal
from analytics.weekly_insights import WeeklyInsightsEngine
from analytics.strategy_recommender import StrategyRecommender
from analytics.performance_metrics import PerformanceMetrics
from utils import RateLimiter

logger = logging.getLogger(__name__)

journal = TradeJournal()
insights_engine = WeeklyInsightsEngine()
recommender = StrategyRecommender()
metrics = PerformanceMetrics()
_rate = RateLimiter(max_requests=120, window_seconds=60)


def setup_journal_routes(app: FastAPI, trading_system=None):

    def _check(request: Request):
        client = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown").split(",")[0].strip()
        if not _rate.is_allowed(client):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # ── Trade CRUD ─────────────────────────────────────────────────────────

    @app.post("/api/journal/trade", tags=["Journal"], summary="Log a new trade entry")
    async def log_trade(request: Request):
        _check(request)
        body = await request.json()

        required = ["symbol", "contract_type", "entry_price", "amount", "confidence", "regime"]
        missing = [f for f in required if f not in body]
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing fields: {missing}")

        trade_id = journal.log_trade(
            symbol=body["symbol"],
            contract_type=body["contract_type"],
            entry_price=float(body["entry_price"]),
            amount=float(body["amount"]),
            confidence=float(body["confidence"]),
            regime=body["regime"],
            entry_conditions=body.get("entry_conditions", []),
            entry_digit=body.get("entry_digit"),
            entropy=body.get("entropy"),
            streak=body.get("streak"),
            chi2=body.get("chi2"),
            rsi=body.get("rsi"),
            macd=body.get("macd"),
            score=body.get("score"),
            running_balance=float(body.get("running_balance", 1000.0)),
            notes=body.get("notes"),
        )
        return JSONResponse({"trade_id": trade_id, "status": "logged"}, status_code=201)

    @app.put("/api/journal/trade/{trade_id}", tags=["Journal"], summary="Close/update a trade with outcome")
    async def close_trade(trade_id: str, request: Request):
        _check(request)
        body = await request.json()

        if "pnl" not in body or "exit_price" not in body:
            raise HTTPException(status_code=422, detail="Requires pnl and exit_price")

        ok = journal.close_trade(
            trade_id=trade_id,
            pnl=float(body["pnl"]),
            exit_price=float(body["exit_price"]),
            exit_digit=body.get("exit_digit"),
            exit_conditions=body.get("exit_conditions", []),
            exit_reason=body.get("exit_reason", "contract_settled"),
            duration_ticks=body.get("duration_ticks"),
            running_balance=float(body.get("running_balance", 1000.0)),
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Trade not found or already closed")
        return JSONResponse({"trade_id": trade_id, "status": "closed"})

    @app.patch("/api/journal/trade/{trade_id}/note", tags=["Journal"], summary="Add a note to a trade")
    async def add_note(trade_id: str, request: Request):
        _check(request)
        body = await request.json()
        note = body.get("note", "")
        ok = journal.add_note(trade_id, note)
        if not ok:
            raise HTTPException(status_code=404, detail="Trade not found")
        return JSONResponse({"trade_id": trade_id, "note": note})

    @app.get("/api/journal/trade/{trade_id}", tags=["Journal"], summary="Get a single trade by ID")
    async def get_trade(trade_id: str, request: Request):
        _check(request)
        trade = journal.get_trade(trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        return JSONResponse(trade)

    # ── Trade list ────────────────────────────────────────────────────────

    @app.get("/api/journal/trades", tags=["Journal"], summary="List trades with filters")
    async def list_trades(
        request: Request,
        status: Optional[str] = Query(None, description="open | closed"),
        symbol: Optional[str] = Query(None),
        regime: Optional[str] = Query(None),
        limit: int = Query(50, le=500),
        offset: int = Query(0),
        since: Optional[str] = Query(None, description="ISO datetime"),
        until: Optional[str] = Query(None, description="ISO datetime"),
    ):
        _check(request)
        trades = journal.get_trades(status=status, symbol=symbol, regime=regime,
                                    limit=limit, offset=offset, since=since, until=until)
        return JSONResponse({"trades": trades, "count": len(trades)})

    @app.get("/api/journal/open", tags=["Journal"], summary="Get all open (pending) trades")
    async def open_trades(request: Request):
        _check(request)
        return JSONResponse({"trades": journal.get_open_trades()})

    @app.get("/api/journal/summary", tags=["Journal"], summary="High-level journal summary")
    async def journal_summary(request: Request):
        _check(request)
        return JSONResponse(journal.get_summary())

    # ── Metrics ───────────────────────────────────────────────────────────

    @app.get("/api/journal/metrics", tags=["Journal Analytics"], summary="Full performance metrics")
    async def get_metrics(
        request: Request,
        since: Optional[str] = Query(None),
        until: Optional[str] = Query(None),
    ):
        _check(request)
        trades = journal.get_trades(status="closed", limit=1000, since=since, until=until)
        if not trades:
            return JSONResponse({"error": "No closed trades", "trades": 0})
        report = metrics.full_report(trades)
        return JSONResponse({"timestamp": datetime.now(timezone.utc).isoformat(), **report})

    # ── Weekly insights ────────────────────────────────────────────────────

    @app.get("/api/journal/insights/weekly", tags=["Journal Analytics"],
             summary="Weekly insights: best/worst setups, time-of-day, regime performance")
    async def weekly_insights(
        request: Request,
        week_offset: int = Query(0, description="0=current week, 1=last week, etc."),
        force: bool = Query(False, description="Bypass cache and regenerate"),
    ):
        _check(request)
        now = datetime.now(timezone.utc)
        days_back = now.weekday() + (week_offset * 7)
        week_start = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
        week_key = week_start.date().isoformat()

        # Try cache
        if not force:
            cached = journal.get_cached_insights(week_key)
            if cached:
                return JSONResponse({**cached, "cached": True})

        trades = journal.get_week_trades(week_start)
        if not trades:
            return JSONResponse({
                "week_start": week_key,
                "error": "No trades found for this week",
                "trades": 0
            })

        result = insights_engine.generate(trades, week_start)
        journal.cache_weekly_insights(week_key, result)
        return JSONResponse({**result, "cached": False})

    @app.get("/api/journal/insights/daily", tags=["Journal Analytics"],
             summary="Daily summary stats for today")
    async def daily_insights(request: Request):
        _check(request)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        trades = journal.get_trades(
            status="closed",
            since=today_start.isoformat(),
            limit=200,
        )
        if not trades:
            return JSONResponse({"date": today_start.date().isoformat(), "trades": 0})

        report = metrics.full_report(trades)
        return JSONResponse({
            "date": today_start.date().isoformat(),
            "timestamp": now.isoformat(),
            "total_trades": report["total_trades"],
            "win_rate": report["win_rate"],
            "total_pnl": report["total_pnl"],
            "profit_factor": report["profit_factor"],
            "expected_value": report["expected_value"],
            "max_drawdown": report["max_drawdown"],
            "best_regime_today": max(
                report["regime_performance"].items(),
                key=lambda x: x[1]["win_rate"],
                default=(None, {})
            )[0] if report["regime_performance"] else None,
            "best_hour_today": max(
                [(h, s) for h, s in report["time_of_day"].items() if s["trades"] > 0],
                key=lambda x: x[1]["win_rate"],
                default=(None, {})
            )[0] if report["time_of_day"] else None,
        })

    # ── Recommendations ────────────────────────────────────────────────────

    @app.get("/api/journal/recommendations", tags=["Journal Analytics"],
             summary="AI-driven strategy adjustment recommendations based on historical performance")
    async def get_recommendations(
        request: Request,
        lookback_days: int = Query(30, description="Days of history to analyze"),
    ):
        _check(request)
        since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        trades = journal.get_trades(status="closed", since=since, limit=1000)
        settings = {}
        if trading_system and hasattr(trading_system, "settings"):
            settings = trading_system.settings.to_dict()
        recs = recommender.generate(trades, settings)
        return JSONResponse({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lookback_days": lookback_days,
            **recs,
        })

    # ── Heatmap ────────────────────────────────────────────────────────────

    @app.get("/api/journal/heatmap", tags=["Journal Analytics"],
             summary="24-hour performance heatmap data")
    async def time_heatmap(
        request: Request,
        lookback_days: int = Query(30),
    ):
        _check(request)
        since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        trades = journal.get_trades(status="closed", since=since, limit=1000)
        tod = metrics.time_of_day_performance(trades) if trades else {}
        regime_perf = metrics.regime_performance(trades) if trades else {}
        return JSONResponse({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lookback_days": lookback_days,
            "time_of_day": tod,
            "regime_performance": regime_perf,
            "confidence_bands": metrics.confidence_band_performance(trades) if trades else {},
        })

    # ── Export ────────────────────────────────────────────────────────────

    @app.get("/api/journal/export", tags=["Journal"],
             summary="Export all trades as JSON")
    async def export_trades(
        request: Request,
        since: Optional[str] = Query(None),
        format: str = Query("json"),
    ):
        _check(request)
        trades = journal.get_trades(limit=10000, since=since)
        summary = journal.get_summary()
        return JSONResponse({
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total": len(trades),
            "summary": summary,
            "trades": trades,
        })
