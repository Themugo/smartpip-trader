import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from dashboard import get_dashboard_html
from utils import RateLimiter
from middleware.input_sanitizer import TradeRequest, MarketSwitchRequest, SettingsUpdate

logger = logging.getLogger(__name__)


def setup_routes(app: FastAPI, trading_system):
    """Setup all API routes for the trading system with rate limiting and documentation"""
    
    # Initialize rate limiters
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
    ws_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
    
    def get_client_identifier(request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Use IP address as identifier
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    @app.get(
        "/",
        tags=["System"],
        summary="Get dashboard",
        description="Returns the HTML dashboard interface"
    )
    async def root():
        return HTMLResponse(get_dashboard_html())
    
    @app.get(
        "/api/status",
        tags=["System"],
        summary="Get system status",
        description="Returns the full system state including trading status, balance, and analysis results"
    )
    async def get_status(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return JSONResponse(trading_system.get_full_state())
    
    @app.post(
        "/api/start",
        tags=["Trading"],
        summary="Start trading bot",
        description="Starts the automated trading bot"
    )
    async def start_bot(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.start_bot()
        trading_system.settings.auto_trading = True
        return JSONResponse({"success": True})
    
    @app.post(
        "/api/stop",
        tags=["Trading"],
        summary="Stop trading bot",
        description="Stops the automated trading bot"
    )
    async def stop_bot(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.stop_bot()
        trading_system.settings.auto_trading = False
        return JSONResponse({"success": True})
    
    @app.post(
        "/api/settings",
        tags=["Configuration"],
        summary="Update settings",
        description="Update trading system settings"
    )
    async def update_settings(request: Request, settings: SettingsUpdate):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.settings.update(settings.model_dump(exclude_none=True))
        return JSONResponse({"success": True})
    
    @app.post(
        "/api/switch_market",
        tags=["Market"],
        summary="Switch market",
        description="Switch to a different trading market"
    )
    async def switch_market(request: Request, market_req: MarketSwitchRequest):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.switch_market(market_req.market)
        return JSONResponse({"success": True})
    
    @app.post(
        "/api/manual_trade",
        tags=["Trading"],
        summary="Execute manual trade",
        description="Execute a manual trade with specified direction and amount"
    )
    async def manual_trade(request: Request, trade: TradeRequest):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.settings.base_amount = trade.amount
        from models import Prediction
        trading_system.best_prediction = Prediction(
            type="MANUAL",
            direction=trade.direction,
            confidence=trade.confidence,
            reason="Manual trade"
        )
        result = await trading_system.execute_intelligent_trade()
        return JSONResponse({"success": result is not None})
    
    @app.post(
        "/api/reset_session",
        tags=["Trading"],
        summary="Reset session",
        description="Reset session statistics and trade history"
    )
    async def reset_session(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        trading_system.reset_session()
        return JSONResponse({"success": True})
    
    @app.websocket(
        "/ws",
        tags=["System"],
        summary="WebSocket connection",
        description="Real-time WebSocket connection for live updates"
    )
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        client_ip = websocket.client.host if websocket.client else "unknown"
        if not ws_rate_limiter.is_allowed(client_ip):
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return
        try:
            while True:
                await websocket.send_json(trading_system.get_full_state())
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass
    
    @app.get(
        "/health",
        tags=["System"],
        summary="Health check",
        description="System health check endpoint"
    )
    async def health():
        return JSONResponse({"status": "healthy"})
    
    @app.get(
        "/api/markets/analyze",
        tags=["Market"],
        summary="Analyze all markets",
        description="Analyze all markets and select the best trading opportunity"
    )
    async def analyze_markets(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        evaluation = trading_system.market_selector.evaluate_markets()
        return JSONResponse(evaluation)
    
    @app.get(
        "/api/markets/ranking",
        tags=["Market"],
        summary="Get market ranking",
        description="Get markets ranked by score"
    )
    async def get_market_ranking(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        ranking = trading_system.market_selector.get_market_ranking()
        return JSONResponse({"ranking": ranking})
    
    @app.post(
        "/api/markets/switch",
        tags=["Market"],
        summary="Force switch market",
        description="Force switch to a specific market"
    )
    async def force_switch_market(request: Request, market_req: MarketSwitchRequest):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        trading_system.market_selector.force_switch(market_req.market)
        trading_system.switch_market(market_req.market)
        return JSONResponse({"success": True, "market": market_req.market})
    
    @app.get(
        "/api/risk/zero-loss",
        tags=["Risk"],
        summary="Get zero-loss risk metrics",
        description="Get current zero-loss risk management metrics"
    )
    async def get_zero_loss_metrics(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        metrics = trading_system.zero_loss_risk_manager.get_risk_metrics()
        return JSONResponse(metrics)
    
    @app.post(
        "/api/risk/zero-loss/reset",
        tags=["Risk"],
        summary="Reset daily zero-loss metrics",
        description="Reset daily PnL and consecutive losses"
    )
    async def reset_zero_loss_metrics(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        trading_system.zero_loss_risk_manager.reset_daily()
        return JSONResponse({"success": True, "message": "Daily metrics reset"})
    
    @app.post(
        "/api/risk/zero-loss/adjust",
        tags=["Risk"],
        summary="Adjust zero-loss parameters",
        description="Adjust confidence threshold and position multiplier based on performance"
    )
    async def adjust_zero_loss_parameters(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        data = await request.json()
        performance = data.get("performance", {})
        
        trading_system.zero_loss_risk_manager.adjust_parameters(performance)
        metrics = trading_system.zero_loss_risk_manager.get_risk_metrics()
        
        return JSONResponse({
            "success": True,
            "metrics": metrics
        })
    
    @app.get(
        "/api/test/run-full",
        tags=["Test"],
        summary="Run full Deriv test suite",
        description="Run comprehensive test on all markets and analysis types"
    )
    async def run_full_deriv_test(request: Request):
        client_id = get_client_identifier(request)
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Run test in background
        import asyncio
        from tests.test_deriv_full import DerivFullTest
        import os
        
        api_token = os.getenv("DERIV_API_TOKEN")
        if not api_token:
            return JSONResponse({"success": False, "error": "DERIV_API_TOKEN not set"})
        
        tester = DerivFullTest(api_token)
        
        # Run test asynchronously
        async def run_test():
            return await tester.run_full_test()
        
        result = await run_test()
        
        return JSONResponse(result)
