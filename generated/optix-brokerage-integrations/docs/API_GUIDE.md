# OPTIX Brokerage API Guide

Complete API reference for the OPTIX Brokerage Integrations service.

## Base URL

```
Production: https://api.optix.app/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All endpoints require user authentication. Pass the `user_id` as a query parameter:

```
GET /api/v1/portfolio?user_id={uuid}
```

## Endpoints

### List Supported Brokerages

Get list of all supported brokerage providers.

**Endpoint:** `GET /api/v1/brokerages`

**Response:**
```json
{
  "brokerages": [
    {
      "id": "schwab",
      "name": "Charles Schwab",
      "status": "active",
      "oauth_type": "OAuth 2.0"
    },
    {
      "id": "fidelity",
      "name": "Fidelity",
      "status": "active",
      "oauth_type": "OAuth 2.0"
    }
  ]
}
```

### Initiate Brokerage Connection

Start OAuth flow to connect a brokerage account.

**Endpoint:** `POST /api/v1/brokerages/{provider}/connect`

**Parameters:**
- `provider` (path): Brokerage provider ID (schwab, fidelity, robinhood, ibkr, webull)
- `user_id` (query): User UUID

**Response:**
```json
{
  "authorization_url": "https://api.fidelity.com/oauth2/authorize?...",
  "state": "unique-state-uuid",
  "provider": "fidelity"
}
```

**Usage:**
1. Call this endpoint to get the authorization URL
2. Redirect user to the authorization URL
3. User completes OAuth on brokerage site
4. Brokerage redirects back to callback URL

### OAuth Callback

Handle OAuth callback from brokerage (internal endpoint).

**Endpoint:** `GET /api/v1/brokerages/{provider}/callback`

**Parameters:**
- `provider` (path): Brokerage provider ID
- `code` (query): Authorization code from OAuth flow
- `state` (query): CSRF state token

**Response:**
```json
{
  "success": true,
  "connection_id": "connection-uuid",
  "message": "fidelity account connected successfully"
}
```

### Get Unified Portfolio

Retrieve aggregated portfolio across all connected brokerages.

**Endpoint:** `GET /api/v1/portfolio`

**Parameters:**
- `user_id` (query): User UUID

**Response:**
```json
{
  "user_id": "user-uuid",
  "total_value": "50000.00",
  "total_cash": "5000.00",
  "total_equity": "45000.00",
  "day_pl": "500.00",
  "day_pl_percent": "1.0",
  "total_pl": "10000.00",
  "total_pl_percent": "25.0",
  "realized_pl": "2500.00",
  "positions": [
    {
      "id": "position-uuid",
      "connection_id": "connection-uuid",
      "symbol": "AAPL",
      "position_type": "stock",
      "quantity": "100",
      "average_price": "150.00",
      "cost_basis": "15000.00",
      "current_price": "175.00",
      "market_value": "17500.00",
      "unrealized_pl": "2500.00",
      "unrealized_pl_percent": "16.67"
    }
  ],
  "updated_at": "2025-12-16T12:00:00Z"
}
```

### Get Positions

Get all positions for a user.

**Endpoint:** `GET /api/v1/portfolio/positions`

**Parameters:**
- `user_id` (query): User UUID

**Response:**
```json
[
  {
    "id": "position-uuid",
    "connection_id": "connection-uuid",
    "symbol": "AAPL",
    "position_type": "stock",
    "quantity": "100",
    "average_price": "150.00",
    "cost_basis": "15000.00",
    "current_price": "175.00",
    "market_value": "17500.00",
    "unrealized_pl": "2500.00",
    "unrealized_pl_percent": "16.67",
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-16T12:00:00Z"
  }
]
```

### Get Day Change

Get detailed day P&L information.

**Endpoint:** `GET /api/v1/portfolio/day-change`

**Parameters:**
- `user_id` (query): User UUID

**Response:**
```json
{
  "day_pl": "500.00",
  "day_pl_percent": "1.0",
  "total_value": "50000.00",
  "start_of_day_value": "49500.00"
}
```

### Sync Portfolio

Trigger immediate sync of all connected accounts.

**Endpoint:** `POST /api/v1/portfolio/sync`

**Parameters:**
- `user_id` (query): User UUID

**Response:**
```json
{
  "success": true,
  "accounts_synced": 2,
  "positions_synced": 15,
  "transactions_synced": 5,
  "synced_at": "2025-12-16T12:00:00Z"
}
```

### Get Transactions

Retrieve transaction history.

**Endpoint:** `GET /api/v1/transactions`

**Parameters:**
- `user_id` (query): User UUID
- `start_date` (query, optional): Start date (ISO format)
- `end_date` (query, optional): End date (ISO format)
- `limit` (query, optional): Max results (default: 100, max: 1000)

**Response:**
```json
[
  {
    "id": "transaction-uuid",
    "connection_id": "connection-uuid",
    "transaction_type": "buy",
    "symbol": "AAPL",
    "quantity": "100",
    "price": "150.00",
    "amount": "-15000.00",
    "fees": "0.00",
    "transaction_date": "2025-12-01T14:30:00Z",
    "description": "Buy 100 shares of AAPL",
    "created_at": "2025-12-01T14:30:05Z"
  }
]
```

### List Connections

Get all connected brokerages for a user.

**Endpoint:** `GET /api/v1/brokerages/connections`

**Parameters:**
- `user_id` (query): User UUID

**Response:**
```json
[
  {
    "id": "connection-uuid",
    "provider": "fidelity",
    "account_id": "12345",
    "account_name": "My Fidelity Account",
    "is_active": true,
    "last_synced_at": "2025-12-16T12:00:00Z",
    "created_at": "2025-12-01T10:00:00Z"
  }
]
```

### Disconnect Brokerage

Disconnect a brokerage and revoke tokens.

**Endpoint:** `DELETE /api/v1/brokerages/{connection_id}/disconnect`

**Parameters:**
- `connection_id` (path): Connection UUID to disconnect
- `user_id` (query): User UUID for authorization

**Response:**
```json
{
  "success": true,
  "message": "Brokerage disconnected successfully"
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameters or CSRF validation failed
- `403 Forbidden`: Access denied (ownership violation)
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

- 100 requests per minute per user
- Sync operations limited to once per minute per account

## WebSocket (Future)

Real-time updates will be available via WebSocket:

```
ws://api.optix.app/v1/ws/portfolio?user_id={uuid}
```

## Code Examples

### Python

```python
import httpx
import asyncio

async def connect_fidelity(user_id: str):
    async with httpx.AsyncClient() as client:
        # Initiate connection
        response = await client.post(
            f"https://api.optix.app/v1/brokerages/fidelity/connect",
            params={"user_id": user_id}
        )
        data = response.json()
        
        # Redirect user to authorization URL
        print(f"Visit: {data['authorization_url']}")
        
        # After OAuth callback completes, get portfolio
        portfolio_response = await client.get(
            "https://api.optix.app/v1/portfolio",
            params={"user_id": user_id}
        )
        portfolio = portfolio_response.json()
        print(f"Total Value: ${portfolio['total_value']}")

asyncio.run(connect_fidelity("your-user-uuid"))
```

### JavaScript

```javascript
// Initiate connection
async function connectBrokerage(userId, provider) {
  const response = await fetch(
    `https://api.optix.app/v1/brokerages/${provider}/connect?user_id=${userId}`,
    { method: 'POST' }
  );
  const data = await response.json();
  
  // Redirect to OAuth
  window.location.href = data.authorization_url;
}

// Get portfolio
async function getPortfolio(userId) {
  const response = await fetch(
    `https://api.optix.app/v1/portfolio?user_id=${userId}`
  );
  const portfolio = await response.json();
  console.log('Total Value:', portfolio.total_value);
}
```

## Testing

Use the interactive API documentation at `/docs` for testing endpoints.
