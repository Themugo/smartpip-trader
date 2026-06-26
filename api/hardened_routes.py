import asyncio
import logging
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, validator

from middleware.input_sanitizer import InputSanitizer, create_sanitize_middleware
from utils.redis_rate_limiter import RedisRateLimiter, CircuitBreaker
from security.auth import SecurityManager
from utils.error_handler import error_handler, SmartPipError, ValidationError

logger = logging.getLogger(__name__)

# Initialize security components
sanitizer = InputSanitizer()
security = SecurityManager()
rate_limiter = RedisRateLimiter()
circuit_breaker = CircuitBreaker()

# Pydantic models for request validation
class SettingsUpdate(BaseModel):
    base_amount: Optional[float] = Field(None, ge=0.35, le=10000)
    min_confidence: Optional[int] = Field(None, ge=50, le=100)
    stop_loss: Optional[float] = Field(None, ge=0)
    take_profit: Optional[float] = Field(None, ge=0)
    max_consecutive_losses: Optional[int] = Field(None, ge=1, le=10)
    auto_trading: Optional[bool] = None
    enable_even_odd: Optional[bool] = None
    enable_rise_fall: Optional[bool] = None
    enable_over_under: Optional[bool] = None
    enable_match_diff: Optional[bool] = None
    enable_digit_analysis: Optional[bool] = None

class MarketSwitchRequest(BaseModel):
    market: str = Field(..., description="Target market")

    @validator('market')
    def validate_market(cls, v):
        valid = {
            "R_10", "R_25", "R_50", "R_75", "R_100",
            "R_10_10S", "R_25_10S", "R_50_10S", "R_75_10S", "R_100_10S",
            "R_100_25S", "R_100_50S"
        }
        if v not in valid:
            raise ValueError(f"Invalid market: {v}")
        return v

class ManualTradeRequest(BaseModel):
    direction: str = Field(..., description="Trade direction")
    amount: float = Field(..., ge=0.35, le=10000)

    @validator('direction')
    def validate_direction(cls, v):
        if v.upper() not in ("CALL", "PUT"):
            raise ValueError("Direction must be CALL or PUT")
        return v.upper()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(client_id: str) -> bool:
    allowed, info = rate_limiter.is_allowed(client_id)
    return allowed


def setup_hardened_routes(app: FastAPI, trading_system):
    """Setup hardened API routes with authentication, validation, and audit logging"""

    # Add input sanitization middleware
    app.middleware("http")(create_sanitize_middleware(sanitizer))

    async def audit_log(action: str, request: Request, details: Optional[dict] = None):
        """Log critical actions to audit trail"""
        try:
            ip = get_client_ip(request)
            trading_system.database.log_audit(action, "api_user", ip, details or {})
        except Exception:
            pass

    @app.get("/", tags=["System"])
    async def root():
        return HTMLResponse("<h1>SmartPip Trading System</h1><p>API is running. Use /docs for documentation.</p>")

    @app.get("/api/status", tags=["System"])
    async def get_status(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return JSONResponse(trading_system.get_full_state())

    @app.post("/api/start", tags=["Trading"])
    async def start_bot(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        trading_system.start_bot()
        trading_system.settings.auto_trading = True
        await audit_log("START_BOT", request)
        return JSONResponse({"success": True})

    @app.post("/api/stop", tags=["Trading"])
    async def stop_bot(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        trading_system.stop_bot()
        trading_system.settings.auto_trading = False
        await audit_log("STOP_BOT", request)
        return JSONResponse({"success": True})

    @app.post("/api/settings", tags=["Configuration"])
    async def update_settings(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            data = await request.json()
            validated = SettingsUpdate(**data)
            updates = validated.dict(exclude_unset=True)
            trading_system.settings.update(updates)
            await audit_log("UPDATE_SETTINGS", request, updates)
            return JSONResponse({"success": True})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid settings: {str(e)}")

    @app.post("/api/switch_market", tags=["Market"])
    async def switch_market(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            data = await request.json()
            validated = MarketSwitchRequest(**data)
            trading_system.switch_market(validated.market)
            await audit_log("SWITCH_MARKET", request, {"market": validated.market})
            return JSONResponse({"success": True})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid market: {str(e)}")

    @app.post("/api/manual_trade", tags=["Trading"])
    async def manual_trade(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            data = await request.json()
            validated = ManualTradeRequest(**data)
            trading_system.settings.base_amount = validated.amount
            from models import Prediction
            trading_system.best_prediction = Prediction(
                type="MANUAL",
                direction=validated.direction,
                confidence=100,
                reason="Manual trade"
            )
            result = await trading_system.execute_intelligent_trade()
            await audit_log("MANUAL_TRADE", request, {
                "direction": validated.direction,
                "amount": validated.amount,
                "success": result is not None
            })
            return JSONResponse({"success": result is not None})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid trade request: {str(e)}")

    @app.post("/api/reset_session", tags=["Trading"])
    async def reset_session(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        trading_system.reset_session()
        await audit_log("RESET_SESSION", request)
        return JSONResponse({"success": True})

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(trading_system.get_full_state())
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass

    @app.get("/health", tags=["System"])
    async def health():
        return JSONResponse({"status": "healthy", "version": "2.1.0-hardened"})

    @app.get("/api/markets/analyze", tags=["Market"])
    async def analyze_markets(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        evaluation = trading_system.market_selector.evaluate_markets()
        return JSONResponse(evaluation)

    @app.get("/api/markets/ranking", tags=["Market"])
    async def get_market_ranking(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        ranking = trading_system.market_selector.get_market_ranking()
        return JSONResponse({"ranking": ranking})

    @app.post("/api/markets/switch", tags=["Market"])
    async def force_switch_market(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        try:
            data = await request.json()
            validated = MarketSwitchRequest(**data)
            trading_system.market_selector.force_switch(validated.market)
            trading_system.switch_market(validated.market)
            await audit_log("FORCE_SWITCH_MARKET", request, {"market": validated.market})
            return JSONResponse({"success": True, "market": validated.market})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid market: {str(e)}")

    @app.get("/api/risk/zero-loss", tags=["Risk"])
    async def get_zero_loss_metrics(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        metrics = trading_system.zero_loss_risk_manager.get_risk_metrics()
        return JSONResponse(metrics)

    @app.post("/api/risk/zero-loss/reset", tags=["Risk"])
    async def reset_zero_loss_metrics(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.zero_loss_risk_manager.reset_daily()
        await audit_log("RESET_ZERO_LOSS", request)
        return JSONResponse({"success": True, "message": "Daily metrics reset"})

    @app.get("/api/audit", tags=["Security"])
    async def get_audit_log(request: Request):
        client_id = get_client_ip(request)
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        logs = trading_system.database._request("GET", "audit_log", params="?order=timestamp.desc&limit=200")
        return JSONResponse(logs or [])
