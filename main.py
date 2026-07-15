# main.py - Modular Institutional Trading Platform
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
from api.v2_routes import setup_v2_routes
from middleware.input_sanitizer import InputSanitizer, create_sanitize_middleware
from developer.logging_tool import setup_logging, LogCollector, LogFormat

# Import all platform modules
from workspace import WorkspaceManager, WorkspaceLayout
from timeline import TimelineManager, ReplayEngine
from research import ResearchLab
from features import FeatureEngineer
from health import HealthMonitor
from alerts import AlertCenter
from risk_sim import RiskSimulator
from qa import QualityAssurance

# Initialize the trading system
platform = TradingSystem()

# Initialize platform modules
workspace_manager = WorkspaceManager()
timeline_manager = TimelineManager()
research_lab = ResearchLab()
feature_engineer = FeatureEngineer()
health_monitor = HealthMonitor()
alert_center = AlertCenter()
risk_simulator = RiskSimulator()
qa_system = QualityAssurance()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
    # Start the trading system in background
    asyncio.create_task(platform.run())
    
    # Start health monitoring
    health_monitor.start_monitoring()
    
    # Start continuous QA validation
    qa_system.start_continuous_validation(interval_seconds=300)
    
    # Start timeline session
    timeline_manager.start_session()
    
    yield
    
    # Cleanup
    health_monitor.stop_monitoring()
    qa_system.stop_continuous_validation()
    timeline_manager.end_session()

app = FastAPI(
    title="SmartPip Trading Platform",
    description="Institutional-grade modular trading platform with plugin architecture, multi-strategy orchestration, and comprehensive risk management",
    version="4.0.0",
    lifespan=lifespan
)

# Setup v1 API routes
setup_routes(app, platform)

# Setup v2 API routes (modular platform)
setup_v2_routes(app)

# Setup structured logging
log_collector = setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format_type=LogFormat.JSON,
    log_file=os.getenv("LOG_FILE", "logs/app.log"),
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add input sanitization middleware
sanitizer = InputSanitizer(testing=os.getenv("ENVIRONMENT") == "testing")
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
