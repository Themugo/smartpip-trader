# main.py - ULTIMATE INTELLIGENT TRADING SYSTEM (Production Enhanced)
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from trading_system import TradingSystem
from api import setup_routes

# Initialize the trading system
platform = TradingSystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
    # Start the trading system in background
    asyncio.create_task(platform.run())
    yield

app = FastAPI(
    title="SmartPip Trading System",
    description="Advanced AI-powered trading bot for Deriv Volatility Indices with technical analysis and backtesting",
    version="2.1.0",
    lifespan=lifespan
)

# CORS — allow custom domain and development origins
site_domain = os.getenv("SITE_DOMAIN", "www.smartpip.site")
root_domain = site_domain.removeprefix("www.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{site_domain}",
        f"https://{root_domain}",
        "http://localhost:8000",
        "http://localhost:9876",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup all API routes
setup_routes(app, platform)

# Mount static files for web interface
app.mount("/static", StaticFiles(directory="web"), name="static")

# Serve the main web interface
@app.get("/web")
async def serve_web_interface():
    return FileResponse("web/index.html")

# Redirect root to web interface
@app.get("/")
async def root_redirect():
    return FileResponse("web/index.html")

def custom_openapi():
    """Custom OpenAPI schema with enhanced documentation"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add tags
    openapi_schema["tags"] = [
        {
            "name": "System",
            "description": "System status and health endpoints"
        },
        {
            "name": "Trading",
            "description": "Trading control and execution endpoints"
        },
        {
            "name": "Configuration",
            "description": "Settings and configuration endpoints"
        },
        {
            "name": "Market",
            "description": "Market selection and data endpoints"
        },
        {
            "name": "Protection",
            "description": "Zero-loss protection endpoints"
        }
    ]
    
    # Add components/schemas
    openapi_schema["components"]["schemas"] = {
        "Settings": {
            "type": "object",
            "properties": {
                "base_amount": {"type": "number", "description": "Base trade amount"},
                "min_confidence": {"type": "number", "description": "Minimum confidence threshold"},
                "stop_loss": {"type": "number", "description": "Stop loss amount"},
                "take_profit": {"type": "number", "description": "Take profit amount"},
                "max_consecutive_losses": {"type": "integer", "description": "Max consecutive losses"},
                "auto_trading": {"type": "boolean", "description": "Auto trading enabled"}
            }
        },
        "Trade": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "market": {"type": "string"},
                "type": {"type": "string"},
                "direction": {"type": "string"},
                "amount": {"type": "number"},
                "confidence": {"type": "number"},
                "entry_price": {"type": "number"},
                "profit": {"type": "number"}
            }
        },
        "Prediction": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "direction": {"type": "string"},
                "confidence": {"type": "number"},
                "reason": {"type": "string"}
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
