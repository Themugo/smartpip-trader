# main.py - ULTIMATE INTELLIGENT TRADING SYSTEM (Production Enhanced)
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from fastapi.middleware.cors import CORSMiddleware
from trading_system import TradingSystem
from api import setup_routes
from middleware.input_sanitizer import InputSanitizer, create_sanitize_middleware

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

# Setup all API routes
setup_routes(app, platform)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add input sanitization middleware
sanitizer = InputSanitizer()
app.middleware("http")(create_sanitize_middleware(sanitizer))

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if os.getenv("ENVIRONMENT") != "production" else "An unexpected error occurred"}
    )

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
