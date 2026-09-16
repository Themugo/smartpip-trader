"""
API routes v3 — adds /api/signals, /api/patterns, /api/ml-status, /api/entropy, /api/analyzer-weights.
"""
import asyncio
import logging
import os
import time
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, JSONResponse
from dashboard import get_dashboard_html
from ai_core.trade_approval import TradeApprover
from utils import RateLimiter

logger = logging.getLogger(__name__)


class TradeRequest(BaseModel):
    contract_type: str = Field(min_length=2, max_length=32)
    symbol: str = Field(min_length=2, max_length=64)
    amount: float = Field(gt=0, le=10000)
    duration: int = Field(gt=0, le=86400)
    duration_unit: str = Field(default="t", pattern=r"^[tsm]$")
    barrier: str | None = Field(default=None, max_length=32)
    prediction: str | None = Field(default=None, max_length=32)


def setup_routes(app: FastAPI, trading_system):
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
    trade_approver = TradeApprover()

    def get_client_identifier(request: Request) -> str:
        if os.getenv("TRUST_PROXY_HEADERS", "false").lower() in {"1", "true", "yes", "on"}:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # ── System ─────────────────────────────────────────────────────────────

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
        markets = list(trading_system.market.get_all_markets().keys())
        return JSONResponse({"markets": markets, "current_market": trading_system.market.get_current_market()})

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

    @app.post("/api/trade", tags=["Trading"], summary="Execute a broker trade through the canonical AI/risk gate")
    async def execute_trade(payload: TradeRequest, request: Request):
        _check_rate(request)
        if not trading_system.connection.is_connected() or not trading_system.connection.authorized:
            raise HTTPException(status_code=503, detail="Deriv session is not connected/authorized")
        # Manual orders use the same broker quote, equity cap, AI probability,
        # calibration, approval and risk gates as automated execution.
        if not trading_system.settings.live_trading_enabled:
            raise HTTPException(status_code=403, detail="Live trading is disabled")

        if len(trading_system.deriv_execution.get_open_contracts()) >= trading_system.settings.max_open_contracts:
            raise HTTPException(status_code=409, detail="Maximum open contracts reached")

        balance = float(trading_system.account.get_balance() or 0.0)
        trade_amount = float(payload.amount)
        max_stake = balance * trading_system.settings.max_stake_pct_equity if balance > 0 else 0.0
        if max_stake > 0:
            trade_amount = min(trade_amount, max_stake)
        if trade_amount <= 0:
            raise HTTPException(status_code=422, detail="Computed stake is not positive")

        try:
            proposal = await trading_system.deriv_execution.get_proposal(
                symbol=payload.symbol,
                contract_type=payload.contract_type.upper(),
                amount=trade_amount,
                currency=trading_system.account.get_currency(),
                duration=payload.duration,
                duration_unit=payload.duration_unit,
                barrier=payload.barrier,
                prediction=payload.prediction,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Proposal rejected: {exc}")

        # Frontend-provided prediction is informational only; probability comes
        # from the backend AI state and is never accepted from the browser.
        try:
            best = trading_system.best_prediction or {}
            raw_probability = float(best.get("confidence", 0) or 0) / 100.0
            best_direction = str(best.get("direction") or best.get("prediction") or "").upper()
            best_contract_type = str(best.get("contract_type") or best.get("type") or "").upper()
        except Exception:
            raw_probability = 0.0
            best_direction = ""
            best_contract_type = ""
        if raw_probability <= 0:
            raise HTTPException(status_code=422, detail="Backend AI probability is required for live approval")

        requested_contract_type = payload.contract_type.upper()
        requested_direction = str(payload.prediction or "").upper()
        if requested_contract_type == "RISEFALL":
            if best_contract_type != "RISEFALL":
                raise HTTPException(status_code=409, detail="Trade blocked: current AI setup is not a Rise/Fall setup")
            if requested_direction not in {"CALL", "PUT"}:
                raise HTTPException(status_code=422, detail="Rise/Fall trades require CALL or PUT")
            if requested_direction != best_direction:
                raise HTTPException(status_code=409, detail=f"Trade blocked: SmartPip AI currently signals {best_direction or 'WAIT'}")

        regime = getattr(trading_system.analysis, "analysis_result", {}) or {}
        regime_value = regime.get("regime", "UNKNOWN") if isinstance(regime, dict) else "UNKNOWN"
        if isinstance(regime_value, dict):
            regime_value = regime_value.get("regime", "UNKNOWN")
        calibration = trading_system.probability_calibrator.transform(
            raw_probability,
            market=payload.symbol,
            contract_type=payload.contract_type.upper(),
            duration=payload.duration,
            regime=str(regime_value),
        )
        if trading_system.settings.live_trading_enabled and getattr(trading_system.settings, "require_calibrated_probability", True) and not calibration.calibrated:
            raise HTTPException(status_code=409, detail="Trade blocked: no valid calibration artifact for live approval")
        probability = calibration.probability

        approval = trade_approver.approve(
            win_probability=probability,
            payout=proposal.payout,
            stake=proposal.ask_price,
            min_expected_value=trading_system.settings.min_expected_value,
            min_probability=trading_system.settings.min_confidence / 100.0,
            risk_score=getattr(trading_system.risk_manager, "get_risk_score", lambda: 0.0)(),
            model_ready=True,
            market_data_fresh=(time.time() - trading_system._last_tick_epoch) <= trading_system.settings.decision_ttl_seconds,
        )
        if not approval.approved:
            raise HTTPException(status_code=409, detail="Trade blocked: " + "; ".join(approval.reasons))

        try:
            trade = await trading_system.deriv_execution.buy(proposal, max_price=proposal.ask_price)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Broker buy failed: {exc}")

        contract_id = trade.contract_id
        now_iso = datetime.now().astimezone().isoformat()
        canonical = {
            "id": contract_id,
            "market": payload.symbol,
            "type": payload.contract_type.upper(),
            "direction": str(payload.prediction or payload.contract_type).upper(),
            "amount": trade.buy_price,
            "confidence": probability * 100,
            "entry_price": trade.entry_spot if trade.entry_spot is not None else 0.0,
            "buy_price": trade.buy_price,
            "payout": trade.payout,
            "proposal_id": proposal.id,
            "expected_value": approval.expected_value,
            "prediction": payload.prediction,
            "entry_time": now_iso,
            "created_at": now_iso,
        }
        trading_system._canonical_trades[contract_id] = canonical
        trading_system._pending_intel = getattr(trading_system, "_pending_intel", {})
        trading_system._pending_intel[contract_id] = {
            "analyzer_output": getattr(trading_system.analysis, "analysis_result", {}) or {},
            "amount": trade.buy_price,
            "market": payload.symbol,
            "direction": canonical["direction"],
            "type": payload.contract_type.upper(),
            "prediction": payload.prediction,
            "confidence": probability * 100,
            "entry_price": canonical["entry_price"],
            "regime": str(regime_value),
            "entropy": float(getattr(trading_system.analysis, "get_market_entropy", lambda: 3.0)()),
            "volatility": 0.0,
            "proposal": {"id": proposal.id, "ask_price": proposal.ask_price, "payout": proposal.payout, "ev": approval.expected_value},
            "calibration": {"raw_probability": raw_probability, "calibrated_probability": probability, "source": calibration.source, "sample_size": calibration.sample_size, "context": calibration.context},
        }
        trading_system.monitor.add_trade(contract_id, canonical)
        task = asyncio.create_task(trading_system._monitor_deriv_contract(contract_id), name=f"manual-contract-{contract_id}")
        trading_system._pending_contract_tasks[contract_id] = task
        return JSONResponse({
            "success": True,
            "contract_id": contract_id,
            "buy_price": trade.buy_price,
            "payout": trade.payout,
            "status": "open",
            "approval": {
                "approved": True,
                "expected_value": approval.expected_value,
                "win_probability": approval.win_probability,
            },
        })

    # ── Risk controls ─────────────────────────────────────────────────────

    @app.get("/api/risk/zero-loss", tags=["Risk"], summary="Get zero-loss risk metrics")
    async def get_zero_loss_metrics(request: Request):
        _check_rate(request)
        manager = getattr(trading_system, "zero_loss_risk_manager", None)
        if manager is None:
            raise HTTPException(status_code=503, detail="Zero-loss risk manager unavailable")
        return JSONResponse(manager.get_risk_metrics())

    @app.post("/api/risk/zero-loss/reset", tags=["Risk"], summary="Reset daily zero-loss risk counters")
    async def reset_zero_loss_metrics(request: Request):
        _check_rate(request)
        manager = getattr(trading_system, "zero_loss_risk_manager", None)
        if manager is None:
            raise HTTPException(status_code=503, detail="Zero-loss risk manager unavailable")
        manager.reset_daily()
        return JSONResponse({"success": True, "metrics": manager.get_risk_metrics()})

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

    # ── Review / inspection routes ────────────────────────────────────────────
    from api.review_routes import setup_review_routes
    import time as _time
    if not hasattr(app.state, 'boot_time'):
        app.state.boot_time = _time.time()
    setup_review_routes(app, trading_system)
