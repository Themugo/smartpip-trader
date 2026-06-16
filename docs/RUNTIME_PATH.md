# SmartPip Trading System - Authoritative Runtime Path

## Single Authoritative Runtime Path

This document defines the single authoritative runtime path for the SmartPip Trading System to eliminate legacy drift and ensure security.

## Primary Entry Point

**File:** `main.py`  
**Function:** `TradingSystem` class initialization  
**Startup:** `uvicorn main:app --host 0.0.0.0 --port 8000`

## Architecture Overview

```
main.py (FastAPI Application)
    ├── TradingSystem (trading_system.py)
    │   ├── DerivConnection (core/deriv_api.py)
    │   ├── AccountManager (core/)
    │   ├── MarketManager (core/)
    │   ├── AnalysisManager (analysis/)
    │   ├── TradeExecutor (trading/)
    │   ├── TradeMonitor (trading/)
    │   ├── RiskManager (trading/)
    │   ├── ZeroLossRiskManager (trading/zero_loss_risk_manager.py)
    │   ├── ZeroLossGuard (trading/instant_kill_switch.py)
    │   ├── PositionSizer (trading/)
    │   ├── ExecutionOptimizer (trading/)
    │   ├── CacheManager (utils/)
    │   ├── PerformanceMetrics (utils/)
    │   ├── DatabaseManager (database/)
    │   └── Settings (config/)
    └── API Routes (api/routes.py)
```

## Security Components Integration

### Zero-Loss Protection
- **File:** `trading/zero_loss_protection.py`
- **File:** `trading/instant_kill_switch.py`
- **Integration:** Loaded in TradingSystem initialization
- **Startup:** Automatic with TradingSystem

### Input Sanitization
- **File:** `middleware/input_sanitizer.py`
- **Integration:** FastAPI middleware
- **Startup:** Applied to all POST/PUT/PATCH requests

### Log Sanitization
- **File:** `utils/log_sanitizer.py`
- **Integration:** Used throughout application
- **Startup:** Automatic when logging

### Rate Limiting
- **File:** `utils/redis_rate_limiter.py`
- **Integration:** API route decorators
- **Startup:** Optional (requires Redis)

### Database Security
- **File:** `database/security_hardening.py`
- **Integration:** DatabaseManager wrapper
- **Startup:** Automatic with DatabaseManager

### Secrets Rotation
- **File:** `utils/secrets_rotation.py`
- **Integration:** External utility
- **Startup:** Manual rotation process

## Deprecated/Legacy Components

### Archived (Do Not Use)
- `legacy-archive/main_old.py` - Old monolithic implementation
- `internal-docs/` - Sensitive operational documentation

### Do Not Use
- Any files in `legacy-archive/` directory
- Any backup files (*.bak, *.old)
- Any duplicate implementations

## Configuration

### Environment Variables
- `DERIV_API_TOKEN` - Deriv API token (required)
- `DERIV_APP_ID` - Deriv app ID (default: 1089)
- `REDIS_URL` - Redis connection URL (optional, for rate limiting)
- `DB_ENCRYPTION_KEY` - Database encryption key (required for production)
- `SANITIZATION_SECRET_KEY` - Payload signature secret (required for production)
- `JWT_SECRET_KEY` - JWT signing key (required)

### Configuration Files
- `config/settings.py` - Application settings
- `config/production_settings.py` - Production-specific settings
- `.env` - Environment variables (not committed)

## Startup Sequence

1. Load environment variables
2. Initialize logging with sanitization
3. Initialize TradingSystem
4. Load security components (zero-loss, input sanitization)
5. Setup API routes with rate limiting
6. Start FastAPI application
7. Connect to Deriv API
8. Subscribe to markets
9. Start monitoring

## Security Checklist

Before deployment, ensure:

- [ ] All environment variables are set
- [ ] Database encryption key is configured
- [ ] Sanitization secret key is configured
- [ ] JWT secret key is configured
- [ ] Redis is available (if using rate limiting)
- [ ] Docker security profile is applied
- [ ] Non-root user is configured
- [ ] Filesystem is read-only where possible
- [ ] Legacy modules are archived
- [ ] Dependencies are audited
- [ ] Secrets are rotated
- [ ] Audit trails are enabled

## Monitoring

### Health Check
- **Endpoint:** `/health`
- **Response:** System status and health indicators

### Security Status
- **Endpoint:** `/api/protection/status`
- **Response:** Zero-loss protection status

### Audit Trail
- **Endpoint:** `/api/audit/trail`
- **Response:** Recent admin actions

## Emergency Procedures

### Kill Switch Activation
- **Endpoint:** `POST /api/kill_switch/activate`
- **Body:** `{"reason": "emergency"}`
- **Response:** Kill switch status

### System Shutdown
- **Endpoint:** `POST /api/shutdown`
- **Response:** Shutdown confirmation

## Version Information

- **Current Version:** 2.1.0
- **Last Updated:** 2026-06-01
- **Security Level:** Enterprise
- **Runtime Path:** Single authoritative (main.py → TradingSystem)

## Contact

For security issues or questions about the runtime path, contact the security team.
