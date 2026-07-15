"""
API Routes v4 - Modular Trading Platform

Comprehensive API endpoints for the refactored institutional-grade trading platform:
- Plugin management
- Strategy marketplace
- Account center
- Workspaces
- Risk management
- Cloud sync
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse

from plugins import (
    PluginManager,
    PluginMetadata,
    StrategyPlugin,
    Signal,
    StrategyMarketplace,
    MarketplaceListing,
    StrategyOrchestrator,
    ConsensusMode,
    ConsensusResult,
    OrchestratorConfig,
)
from accounts import AccountCenter, AccountInfo, AccountType
from workspaces import WorkspaceManager, WorkspaceType
from risk import RiskController, RiskLimits, RiskValidator, TradeRequest, AccountSnapshot, RiskLevel
from sync import CloudSync, SyncConfig, SyncStatus

logger = logging.getLogger(__name__)


# Initialize platform components (in production, these would be singletons)
_plugin_manager: Optional[PluginManager] = None
_marketplace: Optional[StrategyMarketplace] = None
_orchestrator: Optional[StrategyOrchestrator] = None
_account_center: Optional[AccountCenter] = None
_workspace_manager: Optional[WorkspaceManager] = None
_risk_controller: Optional[RiskController] = None
_cloud_sync: Optional[CloudSync] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugins_dir="plugins/strategies")
    return _plugin_manager


def get_marketplace() -> StrategyMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = StrategyMarketplace(storage_path="data/marketplace")
    return _marketplace


def get_orchestrator() -> StrategyOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = StrategyOrchestrator()
    return _orchestrator


def get_account_center() -> AccountCenter:
    global _account_center
    if _account_center is None:
        _account_center = AccountCenter()
    return _account_center


def get_workspace_manager() -> WorkspaceManager:
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager(storage_path="data/workspaces")
    return _workspace_manager


def get_risk_controller() -> RiskController:
    global _risk_controller
    if _risk_controller is None:
        _risk_controller = RiskController()
    return _risk_controller


def get_cloud_sync() -> CloudSync:
    global _cloud_sync
    if _cloud_sync is None:
        _cloud_sync = CloudSync()
    return _cloud_sync


# Create routers
plugin_router = APIRouter(prefix="/plugins", tags=["Plugins"])
marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
orchestrator_router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])
account_router = APIRouter(prefix="/accounts", tags=["Accounts"])
workspace_router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
risk_router = APIRouter(prefix="/risk", tags=["Risk"])
sync_router = APIRouter(prefix="/sync", tags=["Cloud Sync"])


# =============================================================================
# Plugin Management Routes
# =============================================================================

@plugin_router.get("/")
async def list_plugins():
    """List all loaded plugins"""
    manager = get_plugin_manager()
    return JSONResponse({
        "plugins": manager.get_plugin_metadata(),
        "available_types": manager.get_available_plugin_types(),
    })


@plugin_router.post("/load")
async def load_plugin(
    plugin_id: str,
    plugin_class: str,
    config: Optional[dict] = None,
    enabled: bool = True,
):
    """Load a plugin"""
    manager = get_plugin_manager()
    
    plugin_classes = manager.get_available_plugin_types()
    class_map = {p["class_name"]: p for p in plugin_classes}
    
    if plugin_class not in class_map:
        raise HTTPException(status_code=404, detail="Plugin class not found")
    
    # Get the class (simplified - in production would import properly)
    # This is a placeholder
    raise HTTPException(status_code=501, detail="Dynamic plugin loading requires proper class resolution")


@plugin_router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """Enable a plugin"""
    manager = get_plugin_manager()
    success = await manager.enable_plugin(plugin_id)
    return JSONResponse({"success": success})


@plugin_router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """Disable a plugin"""
    manager = get_plugin_manager()
    success = await manager.disable_plugin(plugin_id)
    return JSONResponse({"success": success})


@plugin_router.post("/{plugin_id}/reload")
async def reload_plugin(plugin_id: str):
    """Hot-reload a plugin"""
    manager = get_plugin_manager()
    success = await manager.reload_plugin(plugin_id)
    return JSONResponse({"success": success})


@plugin_router.delete("/{plugin_id}")
async def unload_plugin(plugin_id: str):
    """Unload a plugin"""
    manager = get_plugin_manager()
    success = await manager.unload_plugin(plugin_id)
    return JSONResponse({"success": success})


@plugin_router.get("/{plugin_id}/config")
async def get_plugin_config(plugin_id: str):
    """Get plugin configuration"""
    manager = get_plugin_manager()
    config = manager.get_plugin_config(plugin_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return JSONResponse(config)


@plugin_router.put("/{plugin_id}/config")
async def update_plugin_config(plugin_id: str, config: dict):
    """Update plugin configuration"""
    manager = get_plugin_manager()
    success = manager.update_plugin_config(plugin_id, config)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return JSONResponse({"success": True})


# =============================================================================
# Marketplace Routes
# =============================================================================

@marketplace_router.get("/")
async def list_marketplace_plugins(
    status: Optional[str] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
):
    """List marketplace plugins"""
    marketplace = get_marketplace()
    
    status_filter = None
    if status:
        from plugins.marketplace import MarketplaceStatus
        status_filter = MarketplaceStatus(status)
    
    tags_list = tags.split(",") if tags else None
    
    plugins = marketplace.get_all_listings(
        status=status_filter,
        tags=tags_list,
        search_query=search,
    )
    
    return JSONResponse({
        "plugins": [p.to_dict() for p in plugins],
        "categories": marketplace.get_categories(),
    })


@marketplace_router.get("/search")
async def search_marketplace(q: str, max_results: int = 20):
    """Search marketplace plugins"""
    marketplace = get_marketplace()
    results = marketplace.search_listings(q, max_results)
    return JSONResponse({
        "results": [p.to_dict() for p in results],
        "count": len(results),
    })


@marketplace_router.post("/{plugin_id}/install")
async def install_plugin(plugin_id: str, version: Optional[str] = None):
    """Install a plugin from marketplace"""
    marketplace = get_marketplace()
    success = marketplace.install_plugin(plugin_id, version)
    return JSONResponse({"success": success})


@marketplace_router.post("/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str):
    """Uninstall a marketplace plugin"""
    marketplace = get_marketplace()
    success = marketplace.uninstall_plugin(plugin_id)
    return JSONResponse({"success": success})


@marketplace_router.post("/{plugin_id}/update")
async def update_plugin(plugin_id: str, version: str):
    """Update a marketplace plugin"""
    marketplace = get_marketplace()
    success = marketplace.update_plugin(plugin_id, version)
    return JSONResponse({"success": success})


@marketplace_router.get("/updates")
async def check_updates():
    """Check for plugin updates"""
    marketplace = get_marketplace()
    updates = marketplace.check_updates()
    return JSONResponse({
        "updates": [p.to_dict() for p in updates],
        "count": len(updates),
    })


@marketplace_router.get("/installed")
async def get_installed():
    """Get installed plugins"""
    marketplace = get_marketplace()
    installed = marketplace.get_installed()
    return JSONResponse({
        "plugins": [p.to_dict() for p in installed],
    })


@marketplace_router.get("/favorites")
async def get_favorites():
    """Get favorite plugins"""
    marketplace = get_marketplace()
    favorites = marketplace.get_favorites()
    return JSONResponse({
        "plugins": [p.to_dict() for p in favorites],
    })


@marketplace_router.post("/{plugin_id}/favorite")
async def add_favorite(plugin_id: str):
    """Add plugin to favorites"""
    marketplace = get_marketplace()
    success = marketplace.add_to_favorites(plugin_id)
    return JSONResponse({"success": success})


@marketplace_router.delete("/{plugin_id}/favorite")
async def remove_favorite(plugin_id: str):
    """Remove plugin from favorites"""
    marketplace = get_marketplace()
    success = marketplace.remove_from_favorites(plugin_id)
    return JSONResponse({"success": success})


# =============================================================================
# Orchestrator Routes
# =============================================================================

@orchestrator_router.get("/config")
async def get_orchestrator_config():
    """Get orchestrator configuration"""
    orch = get_orchestrator()
    return JSONResponse(orch.config.to_dict())


@orchestrator_router.put("/config")
async def update_orchestrator_config(config: dict):
    """Update orchestrator configuration"""
    orch = get_orchestrator()
    orch.update_config(config)
    return JSONResponse({"success": True})


@orchestrator_router.get("/signals")
async def get_signal_history(limit: int = 100, direction: Optional[str] = None):
    """Get signal consensus history"""
    orch = get_orchestrator()
    history = orch.get_signal_history(limit, direction)
    return JSONResponse({
        "signals": [h.to_dict() for h in history],
    })


@orchestrator_router.get("/statistics")
async def get_orchestrator_stats():
    """Get orchestrator statistics"""
    orch = get_orchestrator()
    return JSONResponse(orch.get_statistics())


@orchestrator_router.post("/reset")
async def reset_orchestrator():
    """Reset orchestrator statistics"""
    orch = get_orchestrator()
    orch.reset_statistics()
    return JSONResponse({"success": True})


# =============================================================================
# Account Center Routes
# =============================================================================

@account_router.get("/status")
async def get_account_status():
    """Get account center status"""
    center = get_account_center()
    return JSONResponse(center.get_state())


@account_router.post("/login")
async def login(api_token: str):
    """Login with Deriv API token"""
    center = get_account_center()
    try:
        session = await center.authenticate_with_token(api_token)
        return JSONResponse(session.to_dict())
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@account_router.post("/logout")
async def logout():
    """Logout from account center"""
    center = get_account_center()
    await center.logout()
    return JSONResponse({"success": True})


@account_router.get("/accounts")
async def list_accounts():
    """List all accounts"""
    center = get_account_center()
    return JSONResponse({
        "accounts": [a.to_dict() for a in center.all_accounts],
        "demo_accounts": [a.to_dict() for a in center.demo_accounts],
        "real_accounts": [a.to_dict() for a in center.real_accounts],
    })


@account_router.get("/accounts/{account_id}")
async def get_account(account_id: str):
    """Get specific account details"""
    center = get_account_center()
    account = center.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return JSONResponse(account.to_dict())


@account_router.post("/accounts/{account_id}/switch")
async def switch_account(account_id: str):
    """Switch to a different account"""
    center = get_account_center()
    try:
        account = await center.switch_account(account_id)
        return JSONResponse(account.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@account_router.post("/switch/demo")
async def switch_to_demo():
    """Switch to a demo account"""
    center = get_account_center()
    try:
        account = await center.switch_to_demo()
        return JSONResponse(account.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@account_router.post("/switch/real")
async def switch_to_real():
    """Switch to a real account"""
    center = get_account_center()
    try:
        account = await center.switch_to_real()
        return JSONResponse(account.to_dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@account_router.get("/balances")
async def get_balances():
    """Get all account balances"""
    center = get_account_center()
    return JSONResponse(center.get_total_balance())


# =============================================================================
# Workspace Routes
# =============================================================================

@workspace_router.get("/")
async def list_workspaces():
    """List all workspaces"""
    manager = get_workspace_manager()
    return JSONResponse(manager.get_navigation_tree())


@workspace_router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details"""
    manager = get_workspace_manager()
    workspace = manager.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return JSONResponse(workspace.to_dict())


@workspace_router.post("/{workspace_id}/favorites")
async def add_workspace_favorite(workspace_id: str):
    """Add workspace to favorites"""
    manager = get_workspace_manager()
    success = manager.add_to_favorites(workspace_id)
    return JSONResponse({"success": success})


@workspace_router.delete("/{workspace_id}/favorites")
async def remove_workspace_favorite(workspace_id: str):
    """Remove workspace from favorites"""
    manager = get_workspace_manager()
    success = manager.remove_from_favorites(workspace_id)
    return JSONResponse({"success": success})


@workspace_router.get("/favorites")
async def get_workspace_favorites():
    """Get favorite workspaces"""
    manager = get_workspace_manager()
    favorites = manager.get_favorites()
    return JSONResponse({
        "favorites": [w.to_dict() for w in favorites],
    })


@workspace_router.get("/current")
async def get_current_workspace():
    """Get current active workspace"""
    manager = get_workspace_manager()
    workspace = manager.get_current_workspace()
    if not workspace:
        raise HTTPException(status_code=404, detail="No current workspace")
    return JSONResponse(workspace.to_dict())


@workspace_router.post("/{workspace_id}/activate")
async def activate_workspace(workspace_id: str):
    """Activate a workspace"""
    manager = get_workspace_manager()
    success = manager.set_current_workspace(workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return JSONResponse({"success": True})


@workspace_router.get("/{workspace_id}/preferences")
async def get_workspace_preferences(workspace_id: str):
    """Get workspace-specific preferences"""
    manager = get_workspace_manager()
    prefs = manager.get_workspace_preferences(workspace_id)
    return JSONResponse(prefs)


@workspace_router.put("/{workspace_id}/preferences")
async def update_workspace_preferences(workspace_id: str, preferences: dict):
    """Update workspace preferences"""
    manager = get_workspace_manager()
    success = manager.update_workspace_preferences(workspace_id, preferences)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return JSONResponse({"success": True})


# =============================================================================
# Risk Management Routes
# =============================================================================

@risk_router.get("/status")
async def get_risk_status():
    """Get current risk status"""
    controller = get_risk_controller()
    return JSONResponse(controller.get_risk_report())


@risk_router.get("/limits")
async def get_risk_limits():
    """Get risk limits"""
    controller = get_risk_controller()
    return JSONResponse(controller.validator.limits.to_dict())


@risk_router.put("/limits")
async def update_risk_limits(limits: dict):
    """Update risk limits"""
    controller = get_risk_controller()
    controller.update_limits(limits)
    return JSONResponse({"success": True})


@risk_router.post("/validate")
async def validate_trade(
    plugin_id: str,
    market: str,
    direction: str,
    amount: float,
    balance: float,
    equity: Optional[float] = None,
):
    """Validate a trade request"""
    controller = get_risk_controller()
    
    account = AccountSnapshot(
        balance=balance,
        equity=equity or balance,
        currency="USD",
    )
    
    request = TradeRequest(
        plugin_id=plugin_id,
        market=market,
        direction=direction,
        amount=amount,
    )
    
    result = await controller.validate_and_execute(request, account)
    return JSONResponse(result.to_dict())


@risk_router.get("/metrics")
async def get_risk_metrics():
    """Get current risk metrics"""
    controller = get_risk_controller()
    return JSONResponse(controller.metrics.to_dict())


@risk_router.get("/events")
async def get_risk_events(
    since: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
):
    """Get risk events"""
    controller = get_risk_controller()
    
    since_dt = None
    if since:
        from datetime import datetime
        since_dt = datetime.fromisoformat(since)
    
    level_enum = None
    if level:
        level_enum = RiskLevel(level)
    
    events = controller.get_events(since_dt, level_enum, limit)
    return JSONResponse({
        "events": [e.to_dict() for e in events],
    })


@risk_router.post("/reset")
async def reset_risk():
    """Reset risk controller"""
    controller = get_risk_controller()
    controller.reset()
    return JSONResponse({"success": True})


@risk_router.post("/emergency-stop")
async def emergency_stop(reason: str):
    """Execute emergency stop"""
    controller = get_risk_controller()
    controller.emergency_stop(reason)
    return JSONResponse({"success": True, "message": f"Emergency stop: {reason}"})


@risk_router.get("/kill-switch")
async def get_kill_switch_status():
    """Get kill switch status"""
    controller = get_risk_controller()
    return JSONResponse(controller.validator.get_kill_switch_status())


@risk_router.post("/kill-switch/reset")
async def reset_kill_switch():
    """Reset kill switch"""
    controller = get_risk_controller()
    controller.validator.reset_kill_switch()
    return JSONResponse({"success": True})


# =============================================================================
# Cloud Sync Routes
# =============================================================================

@sync_router.get("/status")
async def get_sync_status():
    """Get synchronization status"""
    sync = get_cloud_sync()
    return JSONResponse(sync.get_sync_summary())


@sync_router.post("/sync")
async def trigger_sync():
    """Trigger manual synchronization"""
    sync = get_cloud_sync()
    success = await sync.sync()
    return JSONResponse({"success": success})


@sync_router.get("/conflicts")
async def get_sync_conflicts():
    """Get pending sync conflicts"""
    sync = get_cloud_sync()
    return JSONResponse({
        "conflicts": [c.to_dict() for c in sync.pending_conflicts],
    })


@sync_router.post("/conflicts/{key}/resolve")
async def resolve_conflict(key: str, resolution: str):
    """Resolve a sync conflict"""
    sync = get_cloud_sync()
    success = sync.resolve_conflict(key, resolution)
    if not success:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return JSONResponse({"success": True})


@sync_router.get("/data")
async def get_sync_data():
    """Get all synchronized data"""
    sync = get_cloud_sync()
    return JSONResponse({
        "data": {key: item.to_dict() for key, item in sync._data.items()},
    })


@sync_router.put("/data/{key}")
async def update_sync_data(key: str, data: dict):
    """Update synchronized data"""
    sync = get_cloud_sync()
    sync.register_data(key, data)
    return JSONResponse({"success": True})


# =============================================================================
# WebSocket Routes
# =============================================================================

def setup_websocket_routes(app):
    """Setup WebSocket routes for real-time updates"""
    
    @app.websocket("/ws/v2")
    async def websocket_v2(websocket: WebSocket):
        """WebSocket v2 for real-time platform updates"""
        await websocket.accept()
        
        try:
            while True:
                # Receive and process messages
                data = await websocket.receive_json()
                
                # Handle different message types
                msg_type = data.get("type")
                
                if msg_type == "subscribe":
                    # Subscribe to updates
                    channel = data.get("channel")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                    })
                
                elif msg_type == "get_state":
                    # Return current state
                    state = {
                        "plugins": get_plugin_manager().get_plugin_metadata(),
                        "accounts": get_account_center().get_state(),
                        "risk": get_risk_controller().get_risk_report(),
                        "sync": get_cloud_sync().get_sync_summary(),
                    }
                    await websocket.send_json({
                        "type": "state",
                        "data": state,
                    })
                
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            try:
                await websocket.close(code=1011, reason=str(e))
            except Exception:
                pass


def setup_v2_routes(app):
    """Setup all v2 API routes"""
    app.include_router(plugin_router)
    app.include_router(marketplace_router)
    app.include_router(orchestrator_router)
    app.include_router(account_router)
    app.include_router(workspace_router)
    app.include_router(risk_router)
    app.include_router(sync_router)
    
    # Setup WebSocket
    setup_websocket_routes(app)
