# OPTIX Trading Platform - API Reference

**Version:** 1.0.0  
**Base URL:** `https://api.optix.com`  
**Documentation:** Interactive docs at `/docs`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Market Data](#market-data)
3. [Watchlists](#watchlists)
4. [Alerts](#alerts)
5. [Brokerage](#brokerage)
6. [Portfolio](#portfolio)
7. [WebSocket](#websocket)
8. [Error Codes](#error-codes)

---

## Authentication

All API requests (except auth endpoints) require authentication via JWT bearer token.

### Register User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "trader@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Trader",
  "accepted_tos": true
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "trader@example.com",
  "password": "SecurePass123",
  "mfa_code": "123456"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

---

## Market Data

### Get Real-Time Quote

**Endpoint:** `GET /api/v1/quotes/{symbol}`

**Parameters:**
- `symbol` (path) - Stock or ETF ticker (e.g., AAPL, SPY)

**Response:** `200 OK`
```json
{
  "symbol": "AAPL",
  "last_price": 175.25,
  "bid": 175.24,
  "ask": 175.26,
  "bid_size": 100,
  "ask_size": 200,
  "change": 2.50,
  "change_percent": 1.45,
  "volume": 52847392,
  "high": 176.00,
  "low": 173.50,
  "open_price": 174.00,
  "previous_close": 172.75,
  "status": "real_time",
  "timestamp": "2024-12-11T14:30:00Z"
}
```

### Get Options Chain

**Endpoint:** `GET /api/v1/options/chain/{symbol}`

**Parameters:**
- `symbol` (path) - Underlying symbol
- `expiration` (query) - Expiration date (YYYY-MM-DD)

**Response:** `200 OK`
```json
{
  "symbol": "AAPL",
  "expiration_date": "2025-01-17",
  "underlying_price": 175.25,
  "calls": [
    {
      "option_symbol": "AAPL250117C00175000",
      "strike": 175.00,
      "last_price": 5.50,
      "bid": 5.45,
      "ask": 5.55,
      "greeks": {
        "delta": 0.52,
        "gamma": 0.05,
        "theta": -0.10,
        "vega": 0.15,
        "rho": 0.03
      },
      "implied_volatility": 0.35,
      "volume": 1250,
      "open_interest": 8430,
      "in_the_money": true
    }
  ],
  "puts": [...],
  "total_call_volume": 45000,
  "total_put_volume": 38000
}
```

---

## Watchlists

### Create Watchlist

**Endpoint:** `POST /api/v1/watchlists`

**Request Body:**
```json
{
  "name": "Tech Stocks",
  "description": "Large cap technology companies",
  "is_default": false
}
```

**Response:** `201 Created`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "...",
  "name": "Tech Stocks",
  "symbols": [],
  "is_default": false,
  "created_at": "2024-12-11T14:30:00Z"
}
```

### Add Symbol to Watchlist

**Endpoint:** `POST /api/v1/watchlists/{watchlist_id}/symbols`

**Request Body:**
```json
{
  "symbol": "AAPL",
  "notes": "Long-term hold"
}
```

---

## Brokerage

### Connect Brokerage

**Endpoint:** `POST /api/v1/brokerages/{provider}/connect`

**Parameters:**
- `provider` (path) - Brokerage provider (schwab, fidelity, robinhood, ibkr, webull)

**Response:** `200 OK`
```json
{
  "authorization_url": "https://api.schwabapi.com/oauth2/authorize?client_id=...",
  "state": "...",
  "provider": "schwab"
}
```

### Get Unified Portfolio

**Endpoint:** `GET /api/v1/portfolio`

**Response:** `200 OK`
```json
{
  "user_id": "...",
  "total_value": 125000.50,
  "total_cash": 15000.00,
  "total_stocks_value": 85000.00,
  "total_options_value": 25000.50,
  "total_unrealized_pl": 12500.25,
  "total_unrealized_pl_percent": 11.11,
  "total_delta": 150.5,
  "total_gamma": 25.3,
  "total_theta": -45.2,
  "total_vega": 180.7,
  "positions": [
    {
      "symbol": "AAPL",
      "position_type": "stock",
      "quantity": 100,
      "average_price": 150.00,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pl": 2525.00,
      "unrealized_pl_percent": 16.83
    }
  ],
  "last_updated": "2024-12-11T14:30:00Z"
}
```

---

## WebSocket

### Real-Time Quote Streaming

**Endpoint:** `WS /ws/quotes`

**Connect:**
```javascript
const ws = new WebSocket('wss://api.optix.com/ws/quotes');
```

**Subscribe:**
```json
{
  "action": "subscribe",
  "symbols": ["AAPL", "MSFT", "GOOGL"]
}
```

**Quote Updates:**
```json
{
  "type": "quote",
  "data": {
    "symbol": "AAPL",
    "last_price": 175.26,
    "bid": 175.25,
    "ask": 175.27,
    "timestamp": "2024-12-11T14:30:01.250Z"
  }
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "symbols": ["MSFT"]
}
```

---

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

**Error Response Format:**
```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "detail": "Additional context"
}
```

---

## Rate Limiting

- **Default Limit:** 100 requests per minute per IP
- **Authenticated:** 500 requests per minute per user
- **WebSocket:** 1000 messages per minute

**Rate Limit Headers:**
```
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 498
X-RateLimit-Reset: 1702310400
```

---

## Pagination

For endpoints returning lists (e.g., transactions):

**Query Parameters:**
- `limit` - Items per page (default: 100, max: 500)
- `offset` - Starting position (default: 0)

**Response:**
```json
{
  "total": 1543,
  "limit": 100,
  "offset": 0,
  "results": [...]
}
```

---

**Last Updated:** December 2025
