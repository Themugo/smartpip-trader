"""
API routes v3 — adds /api/signals, /api/patterns, /api/ml-status, /api/entropy, /api/analyzer-weights.
"""
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from dashboard import get_dashboard_html
from utils import RateLimiter

logger = logging.getLogger(__name__)


def setup_routes(app: FastAPI, trading_system):
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

    def get_client_identifier(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # ── System ─────────────────────────────────────────────────────────────

    @app.get("/", tags=["System"], summary="Dashboard", description="HTML dashboard interface")
    async def root():
        return HTMLResponse(get_dashboard_html())

    @app.get("/api/status", tags=["System"], summary="Full system status")
    async def get_status(request: Request):
        _check_rate(request)
        return JSONResponse(trading_system.get_full_state())

    @app.get("/api/health", tags=["System"], summary="Health check")
    async def health():
        return JSONResponse({"status": "ok", "timestamp": datetime.now().isoformat(), "version": "3.0.0"})

    # ── Trading controls ───────────────────────────────────────────────────

    @app.post("/api/start", tags=["Trading"], summary="Start trading bot")
    async def start_bot(request: Request):
        _check_rate(request)
        trading_system.start_bot()
        trading_system.settings.auto_trading = True
        return JSONResponse({"success": True, "status": trading_system.bot_status})

    @app.post("/api/stop", tags=["Trading"], summary="Stop trading bot")
    async def stop_bot(request: Request):
        _check_rate(request)
        trading_system.stop_bot()
        trading_system.settings.auto_trading = False
        return JSONResponse({"success": True, "status": trading_system.bot_status})

    @app.post("/api/reset", tags=["Trading"], summary="Reset session stats")
    async def reset_session(request: Request):
        _check_rate(request)
        if hasattr(trading_system, "stats_manager"):
            trading_system.stats_manager.reset_session()
        return JSONResponse({"success": True})

    # ── Configuration ──────────────────────────────────────────────────────

    @app.post("/api/settings", tags=["Configuration"], summary="Update settings")
    async def update_settings(request: Request):
        _check_rate(request)
        body = await request.json()
        trading_system.settings.update(body)
        # Propagate entropy filter if changed
        if hasattr(trading_system, "analysis") and "min_entropy_threshold" in body:
            trading_system.analysis.set_entropy_filter(body["min_entropy_threshold"])
        return JSONResponse({"success": True, "settings": trading_system.settings.to_dict()})

    @app.get("/api/settings", tags=["Configuration"], summary="Get current settings")
    async def get_settings(request: Request):
        _check_rate(request)
        return JSONResponse(trading_system.settings.to_dict())

    # ── Market ─────────────────────────────────────────────────────────────

    @app.post("/api/market/{market}", tags=["Market"], summary="Switch market")
    async def switch_market(market: str, request: Request):
        _check_rate(request)
        trading_system.switch_market(market)
        return JSONResponse({"success": True, "market": market})

    @app.get("/api/markets", tags=["Market"], summary="List available markets")
    async def list_markets(request: Request):
        _check_rate(request)
        markets = ["R_10", "R_25", "R_50", "R_75", "R_100",
                   "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V"]
        return JSONResponse({"markets": markets})

    # ── AI Signals (NEW v3) ────────────────────────────────────────────────

    @app.get("/api/signals", tags=["AI"], summary="Get all current AI signals with confidence scores")
    async def get_signals(request: Request):
        _check_rate(request)
        analysis = getattr(trading_system, "analysis", None)
        if not analysis:
            return JSONResponse({"signals": [], "consensus": None})

        best = analysis.get_best_prediction()
        signals = analysis.get_trade_signals()
        weights = analysis.get_analyzer_weights()

        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "consensus": best,
            "signals": signals,
            "analyzer_weights": weights,
            "market_entropy": round(analysis.get_market_entropy(), 4),
            "entropy_pct": round(analysis.get_market_entropy() / 3.321928 * 100, 1),
            "pattern_health": analysis.get_pattern_health(),
        })

    # ── Pattern Analysis (NEW v3) ──────────────────────────────────────────

    @app.get("/api/patterns", tags=["AI"], summary="Get statistical pattern analysis of current digit stream")
    async def get_patterns(request: Request):
        _check_rate(request)
        analysis = getattr(trading_system, "analysis", None)
        if not analysis:
            return JSONResponse({"error": "Analysis not initialised"})

        pr = analysis.analyzers.get("pattern_recognizer")
        if not pr:
            return JSONResponse({"error": "Pattern recognizer not available"})

        data = {
            "last_20_digits": trading_system.last_20_digits,
            "price_history": list(trading_system.price_history),
            "current_price": trading_system.current_price,
        }
        result = pr.analyze(data)
        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "prediction": result.prediction,
            "confidence": result.confidence,
            "metrics": result.data,
            "market_health": pr.get_market_health(),
        })

    # ── ML Status (NEW v3) ─────────────────────────────────────────────────

    @app.get("/api/ml-status", tags=["AI"], summary="Get ML model status, accuracy, and feature importance")
    async def get_ml_status(request: Request):
        _check_rate(request)
        ml_analyzer = None
        analysis = getattr(trading_system, "analysis", None)
        if analysis:
            ml_analyzer = analysis.analyzers.get("ml")

        if not ml_analyzer:
            return JSONResponse({"error": "ML analyzer not available"})

        predictor = getattr(ml_analyzer, "predictor", None)
        if not predictor:
            return JSONResponse({"error": "No predictor attached to ML analyzer"})

        status = predictor.get_status() if hasattr(predictor, "get_status") else {"is_trained": predictor.is_trained}
        feature_importance = predictor.get_feature_importance() or {}
        top_features = dict(list(feature_importance.items())[:10])

        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "top_features": top_features,
            "ensemble_tracker": status.get("ensemble", {}).get("tracker", {}),
        })

    # ── Entropy (NEW v3) ───────────────────────────────────────────────────

    @app.get("/api/entropy", tags=["AI"], summary="Get current market entropy and randomness metrics")
    async def get_entropy(request: Request):
        _check_rate(request)
        analysis = getattr(trading_system, "analysis", None)
        entropy = analysis.get_market_entropy() if analysis else 3.32
        health = analysis.get_pattern_health() if analysis else {}
        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "entropy": round(entropy, 4),
            "entropy_pct": round(entropy / 3.321928 * 100, 1),
            "max_entropy": 3.321928,
            "health": health,
            "digits": list(getattr(trading_system, "last_20_digits", [])),
        })

    # ── Analyzer Weights (NEW v3) ──────────────────────────────────────────

    @app.get("/api/analyzer-weights", tags=["AI"], summary="Get current adaptive analyzer weights")
    async def get_analyzer_weights(request: Request):
        _check_rate(request)
        analysis = getattr(trading_system, "analysis", None)
        weights = analysis.get_analyzer_weights() if analysis else {}
        return JSONResponse({"weights": weights, "timestamp": datetime.now().isoformat()})

    # ── Trade execution ────────────────────────────────────────────────────

    @app.post("/api/trade", tags=["Trading"], summary="Execute a manual trade")
    async def execute_trade(request: Request):
        _check_rate(request)
        body = await request.json()
        contract_type = body.get("contract_type", "CALL")
        amount = float(body.get("amount", trading_system.settings.base_amount))
        market = body.get("market", None)
        duration = int(body.get("duration", 1))

        if not trading_system.connection.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Deriv API")

        result = await trading_system.executor.execute_trade(
            trading_system.connection.websocket,
            contract_type=contract_type,
            amount=amount,
            market=market or trading_system.market.get_current_market(),
            duration=duration,
        )
        return JSONResponse(result if result else {"error": "Trade execution failed"})

    # ── History ────────────────────────────────────────────────────────────

    @app.get("/api/history", tags=["Trading"], summary="Get trade history")
    async def get_history(request: Request):
        _check_rate(request)
        db = getattr(trading_system, "database", None)
        if db:
            trades = db.get_recent_trades(limit=100) if hasattr(db, "get_recent_trades") else []
        else:
            trades = []
        return JSONResponse({"trades": trades, "count": len(trades)})

    # ── WebSocket: live data stream ─────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                try:
                    state = trading_system.get_full_state()
                    analysis = getattr(trading_system, "analysis", None)
                    if analysis:
                        state["signals"] = analysis.get_trade_signals()
                        state["consensus"] = analysis.get_best_prediction()
                        state["market_entropy"] = round(analysis.get_market_entropy(), 4)
                        state["pattern_health"] = analysis.get_pattern_health()
                    await websocket.send_json(state)
                except Exception as e:
                    logger.debug("WS send error: %s", e)
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("WS error: %s", e)

    # ── Backtesting ────────────────────────────────────────────────────────

    @app.post("/api/backtest", tags=["Trading"], summary="Run quick backtest on current data")
    async def quick_backtest(request: Request):
        _check_rate(request)
        body = await request.json()
        strategy = body.get("strategy", "unified")
        min_confidence = float(body.get("min_confidence", 75))

        data = {
            "last_20_digits": trading_system.last_20_digits,
            "price_history": list(trading_system.price_history),
            "current_price": trading_system.current_price,
        }
        analysis = getattr(trading_system, "analysis", None)
        if not analysis:
            return JSONResponse({"error": "Analysis system not ready"})

        result = analysis.get_comprehensive_analysis(data)
        signals = analysis.get_trade_signals()
        consensus = analysis.get_best_prediction()

        return JSONResponse({
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy,
            "min_confidence": min_confidence,
            "signals_count": len(signals),
            "consensus": consensus,
            "would_trade": bool(consensus and consensus.get("confidence", 0) >= min_confidence),
            "analysis": {k: {"prediction": v.get("prediction"), "confidence": v.get("confidence")}
                        for k, v in result.items() if isinstance(v, dict) and "prediction" in v},
        })

    # ── Journal routes ─────────────────────────────────────────────────────
    from api.journal_routes import setup_journal_routes
    setup_journal_routes(app, trading_system)
