# SmartPip Trader API Documentation

## Overview

SmartPip Trader provides a comprehensive REST API for all platform features. The API follows RESTful principles and uses JSON for request/response bodies.

## Base URL

```
Production: https://api.smartpip.trader/v1
Development: http://localhost:8080/api/v1
```

## Authentication

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123",
  "totp_code": "123456"  // Optional, required if 2FA enabled
}
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "session_id": "uuid",
    "token": "jwt_token",
    "user_id": "uuid",
    "expires_at": "2024-01-15T12:00:00Z"
  }
}
```

### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "uuid"
}
```

## Accounts

### List Accounts
```http
GET /api/v1/accounts
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": 200,
  "data": [
    {
      "id": "demo_1",
      "type": "demo",
      "balance": 10000.00,
      "currency": "USD",
      "equity": 10050.00,
      "is_active": true
    },
    {
      "id": "real_1",
      "type": "real",
      "balance": 5000.00,
      "currency": "USD",
      "equity": 4950.00,
      "is_active": true
    }
  ]
}
```

### Get Account
```http
GET /api/v1/accounts/{id}
Authorization: Bearer <token>
```

### Switch Account
```http
POST /api/v1/accounts/{id}/switch
Authorization: Bearer <token>

{
  "account_id": "real_1"
}
```

## Strategies

### List Strategies
```http
GET /api/v1/strategies
Authorization: Bearer <token>

Query Parameters:
- state: Filter by state (draft, testing, paper_trading, validated, production, paused)
- limit: Number of results (default: 50)
- offset: Pagination offset
```

### Create Strategy
```http
POST /api/v1/strategies
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Strategy",
  "description": "Strategy description",
  "graph": {
    "blocks": [...],
    "connections": [...]
  }
}
```

### Get Strategy
```http
GET /api/v1/strategies/{id}
Authorization: Bearer <token>
```

### Update Strategy
```http
PUT /api/v1/strategies/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "graph": {...}
}
```

### Compile Strategy
```http
POST /api/v1/strategies/{id}/compile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "success": true,
    "errors": [],
    "warnings": [],
    "estimated_cost": 15.5
  }
}
```

### Promote Strategy
```http
POST /api/v1/strategies/{id}/promote
Authorization: Bearer <token>
Content-Type: application/json

{
  "target_state": "testing",
  "reason": "Ready for testing after successful compilation"
}
```

## Orders

### List Orders
```http
GET /api/v1/orders
Authorization: Bearer <token>

Query Parameters:
- status: Filter by status (pending, filled, cancelled)
- symbol: Filter by symbol
- limit: Number of results
- since: ISO datetime filter
```

### Create Order
```http
POST /api/v1/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "symbol": "EUR/USD",
  "side": "buy",
  "amount": 100,
  "order_type": "market",
  "price": null,
  "strategy_id": "uuid"  // Optional
}
```

### Get Order
```http
GET /api/v1/orders/{id}
Authorization: Bearer <token>
```

### Cancel Order
```http
POST /api/v1/orders/{id}/cancel
Authorization: Bearer <token>
```

## Analytics

### Performance Analytics
```http
GET /api/v1/analytics/performance
Authorization: Bearer <token>

Query Parameters:
- period: Time period (day, week, month, all)
- strategy_id: Filter by strategy
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "total_return": 15.5,
    "sharpe_ratio": 1.45,
    "sortino_ratio": 1.8,
    "win_rate": 0.58,
    "profit_factor": 1.65,
    "max_drawdown": 8.5,
    "total_trades": 234,
    "avg_trade_duration_hours": 4.2
  }
}
```

### Risk Analytics
```http
GET /api/v1/analytics/risk
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "total_exposure": 3500.00,
    "exposure_ratio": 0.35,
    "max_concentration": 0.25,
    "var_95": 2.5,
    "cvar_95": 4.2,
    "max_drawdown": 8.5,
    "daily_loss_limit": 500.00
  }
}
```

## System

### Health Check
```http
GET /api/v1/system/health
```

**Response:**
```json
{
  "status": 200,
  "data": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "version": "1.0.0",
    "components": {
      "database": "healthy",
      "redis": "healthy",
      "execution": "healthy"
    }
  }
}
```

### System Status
```http
GET /api/v1/system/status
Authorization: Bearer <token>
```

## Error Responses

All errors follow this format:
```json
{
  "status": 400,
  "data": null,
  "message": "Error description",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Common Error Codes
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Rate Limits

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Read endpoints | 100 requests | 60 seconds |
| Write endpoints | 50 requests | 60 seconds |
| Strategy execution | 10 requests | 60 seconds |

## WebSocket

Connect to `ws://localhost:8081/ws` for real-time updates.

### Authentication
```json
{
  "type": "auth",
  "token": "jwt_token"
}
```

### Subscribe to Updates
```json
{
  "type": "subscribe",
  "channel": "orders",
  "account_id": "demo_1"
}
```

## SDK Examples

### Python
```python
from smartpip import Client

client = Client(base_url="http://localhost:8080/api/v1")
client.login("username", "password")

# List accounts
accounts = client.accounts.list()

# Create order
order = client.orders.create(
    symbol="EUR/USD",
    side="buy",
    amount=100
)

# Get performance
perf = client.analytics.performance(period="month")
```

### JavaScript
```javascript
import { SmartPipClient } from '@smartpip/sdk';

const client = new SmartPipClient({
  baseUrl: 'http://localhost:8080/api/v1'
});

await client.auth.login('username', 'password');
const accounts = await client.accounts.list();
```
