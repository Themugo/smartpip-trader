"""
API Documentation

OpenAPI documentation for the Enterprise API.
"""

API_TITLE = "SmartPip Trader Enterprise API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## Overview

The SmartPip Trader Enterprise API provides programmatic access to all platform features.

## Authentication

All API requests require authentication using Bearer tokens:

```
Authorization: Bearer <access_token>
```

### Obtaining Tokens

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Returns access_token and refresh_token
3. **Refresh**: `POST /api/v1/auth/refresh` → Use refresh_token to get new access_token

## Rate Limiting

| Plan | Requests/minute | Requests/day |
|------|----------------|--------------|
| Free | 10 | 100 |
| Professional | 100 | 5,000 |
| Business | 1,000 | 50,000 |
| Enterprise | Unlimited | Unlimited |

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Error |

## Response Format

All responses follow this format:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-20T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

## Pagination

List endpoints support pagination:

```
GET /api/v1/strategies?page=1&limit=20
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

## Webhooks

Subscribe to events using webhooks:

- `trade.executed` - When a trade is executed
- `trade.closed` - When a trade is closed
- `backtest.completed` - When a backtest finishes
- `strategy.error` - When a strategy encounters an error
- `user.login` - When a user logs in

## SDKs

Official SDKs available:
- Python: `pip install smartpip-sdk`
- JavaScript: `npm install @smartpip/sdk`
- Go: `go get github.com/smartpip/go-sdk`
"""


class APIDocumentation:
    """API documentation generator"""
    
    @staticmethod
    def get_openapi_spec() -> dict:
        """Generate OpenAPI specification"""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": API_TITLE,
                "version": API_VERSION,
                "description": API_DESCRIPTION,
                "contact": {
                    "name": "SmartPip Support",
                    "email": "support@smartpip.io",
                },
            },
            "servers": [
                {"url": "https://api.smartpip.io/v1", "description": "Production"},
                {"url": "https://api.staging.smartpip.io/v1", "description": "Staging"},
                {"url": "http://localhost:8000/api/v1", "description": "Development"},
            ],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    },
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                },
                "schemas": {
                    "Error": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "error_code": {"type": "string"},
                            "details": {"type": "object"},
                        },
                    },
                    "Pagination": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "limit": {"type": "integer"},
                            "total": {"type": "integer"},
                            "pages": {"type": "integer"},
                        },
                    },
                },
            },
            "tags": [
                {"name": "Authentication", "description": "User authentication endpoints"},
                {"name": "Account", "description": "User account management"},
                {"name": "Organizations", "description": "Organization management"},
                {"name": "Teams", "description": "Team collaboration"},
                {"name": "Strategies", "description": "Trading strategy management"},
                {"name": "Backtesting", "description": "Backtesting operations"},
                {"name": "Reports", "description": "Report generation"},
                {"name": "Billing", "description": "Subscription and billing"},
                {"name": "System", "description": "System information"},
            ],
        }
    
    @staticmethod
    def get_api_changelog() -> list:
        """Get API changelog"""
        return [
            {
                "version": "1.0.0",
                "date": "2024-01-20",
                "changes": [
                    "Initial API release",
                    "Authentication with JWT",
                    "Organization and team management",
                    "Strategy CRUD operations",
                    "Backtesting endpoints",
                    "Report generation",
                    "Billing integration",
                ],
            },
        ]
