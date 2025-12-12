# Project: OPTIX

## Technical Requirements Document - Generative UI API Specifications

**DSDM Atern Methodology**

Version 1.0 | December 12, 2024

---

## 1. Document Overview

This Technical Requirements Document provides comprehensive API specifications for the OPTIX Generative UI Engine and all supporting services. It serves as the authoritative reference for frontend/mobile developers and third-party integrators.

### 1.1 Document Scope

| Attribute | Value |
|-----------|-------|
| **API Version** | v1 |
| **Base URL** | `https://api.optix.io/api/v1` |
| **WebSocket URL** | `wss://api.optix.io/ws` |
| **Authentication** | JWT Bearer Token |
| **Content Type** | `application/json` |
| **Character Encoding** | UTF-8 |

### 1.2 Related Documents

| Document | Purpose |
|----------|---------|
| `OPTIX_TRD_Generative_UI.md` | Architecture and implementation details |
| `OPTIX_TRD_Vertical_Slices.md` | Overall platform vertical slices |
| `OPTIX_PRD_Generative_UI.md` | Product requirements and user stories |

---

## 2. Authentication

### 2.1 Authentication Methods

All API endpoints require JWT Bearer token authentication unless explicitly marked as public.

```http
Authorization: Bearer <access_token>
```

### 2.2 Token Types

| Token Type | Duration | Purpose |
|------------|----------|---------|
| Access Token | 15 minutes | API authentication |
| Refresh Token | 7 days | Obtain new access tokens |
| WebSocket Token | 15 minutes | WebSocket authentication |

### 2.3 Token Refresh Flow

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "string"
}
```

---

## 3. Rate Limiting

### 3.1 Standard Rate Limits

| Endpoint Category | Limit | Window | Notes |
|-------------------|-------|--------|-------|
| Authentication | 5 requests | 1 minute | Brute force protection |
| Registration | 3 requests | 1 minute | Spam prevention |
| Token Refresh | 10 requests | 1 minute | Token refresh throttling |
| GenUI Generation | 20 requests | 1 minute | LLM cost control |
| Standard API | 100 requests | 1 minute | General protection |
| WebSocket | 1 connection | per user | Connection limit |

### 3.2 Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702400000
```

### 3.3 Rate Limit Exceeded Response

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please retry after 45 seconds.",
  "retry_after": 45
}
```

---

## 4. Error Handling

### 4.1 Standard Error Format

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context"
  },
  "request_id": "req_abc123"
}
```

### 4.2 HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid request body |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Maintenance/overload |

### 4.3 Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `invalid_token` | 401 | Token is invalid or expired |
| `token_expired` | 401 | Access token has expired |
| `mfa_required` | 403 | MFA verification needed |
| `insufficient_permissions` | 403 | User lacks required role |
| `resource_not_found` | 404 | Requested resource doesn't exist |
| `validation_error` | 422 | Request body validation failed |
| `rate_limit_exceeded` | 429 | Too many requests |
| `generation_failed` | 500 | UI generation failed |
| `llm_unavailable` | 503 | LLM provider unavailable |

---

## 5. Generative UI API Endpoints

### 5.1 Generate UI

Generate a custom UI from a natural language query.

```http
POST /api/v1/genui/generate
```

**Request Headers:**
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "Show me AAPL options chain with highlighted high OI calls",
  "context": {
    "symbol": "AAPL",
    "current_price": 185.50,
    "positions": [
      {
        "symbol": "AAPL",
        "strike": 190,
        "expiration": "2024-01-19",
        "type": "call",
        "quantity": 5
      }
    ]
  },
  "preferences": {
    "theme": "dark",
    "chart_type": "candlestick",
    "expertise_level": "advanced"
  },
  "stream": false
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural language query (1-2000 chars) |
| `context` | object | No | Additional context for generation |
| `context.symbol` | string | No | Primary symbol for the query |
| `context.current_price` | number | No | Current price of the symbol |
| `context.positions` | array | No | User's relevant positions |
| `preferences` | object | No | UI generation preferences |
| `preferences.theme` | string | No | `dark`, `light`, `system` |
| `preferences.chart_type` | string | No | `candlestick`, `line`, `bar` |
| `preferences.expertise_level` | string | No | `beginner`, `intermediate`, `advanced` |
| `stream` | boolean | No | Enable streaming response (default: true) |

**Response (200 OK):**
```json
{
  "generation_id": "gen_abc123xyz",
  "status": "complete",
  "html": "<!DOCTYPE html><html>...</html>",
  "metadata": {
    "query_parsed": {
      "intent": "options_chain_view",
      "symbol": "AAPL",
      "filters": ["high_oi", "calls"]
    },
    "components_used": ["OptionsChainTable", "OIHighlighter"],
    "data_subscriptions": ["quote:AAPL", "options_chain:AAPL"],
    "evaluation_score": 92.5
  },
  "created_at": "2024-12-12T10:30:00Z",
  "generation_time_ms": 2450
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `generation_id` | string | Unique identifier for this generation |
| `status` | string | `pending`, `generating`, `post_processing`, `complete`, `failed` |
| `html` | string | Generated HTML/CSS/JS (null if still generating) |
| `metadata` | object | Generation metadata and analytics |
| `metadata.query_parsed` | object | Parsed query requirements |
| `metadata.components_used` | array | Pre-built components utilized |
| `metadata.data_subscriptions` | array | Data channels for real-time updates |
| `metadata.evaluation_score` | number | Quality score (0-100) |
| `created_at` | string | ISO 8601 timestamp |
| `generation_time_ms` | integer | Total generation time in milliseconds |

**Error Responses:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `invalid_query` | Query is empty or malformed |
| 401 | `invalid_token` | Authentication failed |
| 422 | `query_too_long` | Query exceeds 2000 characters |
| 429 | `rate_limit_exceeded` | Too many generation requests |
| 500 | `generation_failed` | UI generation failed |

---

### 5.2 Stream UI Generation

Stream UI generation progress with Server-Sent Events.

```http
POST /api/v1/genui/generate/stream
```

**Request Body:** Same as `/generate`

**Response:** Server-Sent Events stream

```text
data: {"event": "started", "generation_id": "gen_abc123"}

data: {"event": "parsing", "progress": 10, "message": "Parsing query..."}

data: {"event": "planning", "progress": 25, "message": "Building component graph..."}

data: {"event": "generating", "progress": 50, "message": "Synthesizing UI code..."}

data: {"event": "post_processing", "progress": 80, "message": "Applying security sanitization..."}

data: {"event": "evaluating", "progress": 90, "message": "Evaluating quality..."}

data: {"event": "complete", "progress": 100, "html": "<!DOCTYPE html>...", "metadata": {...}}

data: [DONE]
```

**Event Types:**

| Event | Description |
|-------|-------------|
| `started` | Generation has started |
| `parsing` | Parsing natural language query |
| `planning` | Building FSM and component graph |
| `generating` | LLM is generating UI code |
| `post_processing` | Applying sanitization and styling |
| `evaluating` | Running quality evaluation |
| `complete` | Generation finished successfully |
| `error` | Generation failed |

---

### 5.3 Refine UI

Refine an existing generated UI with additional instructions.

```http
POST /api/v1/genui/refine
```

**Request Body:**
```json
{
  "generation_id": "gen_abc123xyz",
  "refinement": "Add the puts side and show delta values"
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generation_id` | string | Yes | ID of generation to refine |
| `refinement` | string | Yes | Refinement instructions (1-1000 chars) |

**Response (200 OK):**
```json
{
  "generation_id": "gen_def456uvw",
  "parent_generation_id": "gen_abc123xyz",
  "status": "complete",
  "html": "<!DOCTYPE html><html>...</html>",
  "metadata": {
    "refinement_applied": "Add the puts side and show delta values",
    "changes_made": ["added_puts_columns", "added_delta_display"],
    "components_used": ["OptionsChainTable", "GreeksDisplay"],
    "evaluation_score": 94.2
  },
  "created_at": "2024-12-12T10:32:00Z",
  "generation_time_ms": 1850
}
```

**Error Responses:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `invalid_refinement` | Refinement text is empty |
| 404 | `generation_not_found` | Original generation not found |
| 403 | `not_owner` | User doesn't own this generation |

---

### 5.4 Get Generation History

Retrieve user's generation history.

```http
GET /api/v1/genui/history
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Max results (1-100) |
| `offset` | integer | 0 | Pagination offset |
| `favorites_only` | boolean | false | Filter to favorites only |
| `search` | string | - | Search in query text |

**Response (200 OK):**
```json
{
  "items": [
    {
      "generation_id": "gen_abc123xyz",
      "query": "Show me AAPL options chain",
      "status": "complete",
      "is_favorite": true,
      "thumbnail_url": "https://cdn.optix.io/gen/thumb_abc123.png",
      "created_at": "2024-12-12T10:30:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### 5.5 Get Generation Details

Retrieve a specific generation by ID.

```http
GET /api/v1/genui/generations/{generation_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `generation_id` | string | Generation ID |

**Response (200 OK):**
```json
{
  "generation_id": "gen_abc123xyz",
  "query": "Show me AAPL options chain with highlighted high OI calls",
  "status": "complete",
  "html": "<!DOCTYPE html><html>...</html>",
  "metadata": {
    "query_parsed": {
      "intent": "options_chain_view",
      "symbol": "AAPL"
    },
    "components_used": ["OptionsChainTable"],
    "evaluation_score": 92.5,
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-pro",
    "token_count": 4521,
    "iteration_count": 2
  },
  "is_favorite": false,
  "created_at": "2024-12-12T10:30:00Z",
  "updated_at": "2024-12-12T10:30:02Z"
}
```

---

### 5.6 Favorite/Unfavorite Generation

Toggle favorite status for a generation.

```http
POST /api/v1/genui/generations/{generation_id}/favorite
```

**Request Body:**
```json
{
  "is_favorite": true
}
```

**Response (200 OK):**
```json
{
  "generation_id": "gen_abc123xyz",
  "is_favorite": true
}
```

---

### 5.7 Delete Generation

Delete a generation from history.

```http
DELETE /api/v1/genui/generations/{generation_id}
```

**Response (204 No Content)**

---

### 5.8 List Available Components

Get list of pre-built components available for generation.

```http
GET /api/v1/genui/components
```

**Response (200 OK):**
```json
{
  "components": [
    {
      "name": "OptionsChainTable",
      "description": "Interactive options chain with calls/puts",
      "props": ["symbol", "expiration", "columns", "onStrikeSelect"],
      "preview_url": "https://cdn.optix.io/components/options_chain_preview.png",
      "fsm_states": ["loading", "ready", "filtering", "expanded"]
    },
    {
      "name": "GreeksGauges",
      "description": "Visual gauges for Delta, Gamma, Theta, Vega",
      "props": ["greeks", "ranges", "format"],
      "preview_url": "https://cdn.optix.io/components/greeks_gauges_preview.png",
      "fsm_states": ["loading", "ready", "updating"]
    },
    {
      "name": "PayoffDiagram",
      "description": "Strategy payoff P&L chart",
      "props": ["legs", "underlying_range", "current_price"],
      "preview_url": "https://cdn.optix.io/components/payoff_diagram_preview.png",
      "fsm_states": ["loading", "ready", "hovering", "zooming"]
    },
    {
      "name": "VolatilitySurface",
      "description": "3D implied volatility surface",
      "props": ["symbol", "expirations", "strikes"],
      "preview_url": "https://cdn.optix.io/components/vol_surface_preview.png",
      "fsm_states": ["loading", "ready", "rotating", "zooming"]
    },
    {
      "name": "PositionCard",
      "description": "Single position summary card",
      "props": ["position", "show_greeks", "show_pnl"],
      "preview_url": "https://cdn.optix.io/components/position_card_preview.png",
      "fsm_states": ["collapsed", "expanded"]
    },
    {
      "name": "StrategyBuilder",
      "description": "Drag-drop strategy leg builder",
      "props": ["symbol", "available_legs", "on_change"],
      "preview_url": "https://cdn.optix.io/components/strategy_builder_preview.png",
      "fsm_states": ["idle", "dragging", "validating", "confirmed"]
    },
    {
      "name": "AlertConfigurator",
      "description": "Price/condition alert setup",
      "props": ["symbol", "alert_types", "on_create"],
      "preview_url": "https://cdn.optix.io/components/alert_config_preview.png",
      "fsm_states": ["idle", "configuring", "validating", "created"]
    },
    {
      "name": "EarningsCalendar",
      "description": "Upcoming earnings with options IV",
      "props": ["symbols", "date_range", "show_iv"],
      "preview_url": "https://cdn.optix.io/components/earnings_calendar_preview.png",
      "fsm_states": ["loading", "ready", "filtered"]
    },
    {
      "name": "GEXHeatmap",
      "description": "Gamma exposure heatmap visualization",
      "props": ["symbol", "expiration", "color_scale"],
      "preview_url": "https://cdn.optix.io/components/gex_heatmap_preview.png",
      "fsm_states": ["loading", "ready", "hovering"]
    },
    {
      "name": "FlowTicker",
      "description": "Real-time unusual options flow ticker",
      "props": ["symbols", "min_premium", "flow_types"],
      "preview_url": "https://cdn.optix.io/components/flow_ticker_preview.png",
      "fsm_states": ["loading", "streaming", "paused"]
    }
  ]
}
```

---

### 5.9 Submit Generation Feedback

Submit feedback on a generation for model improvement.

```http
POST /api/v1/genui/generations/{generation_id}/feedback
```

**Request Body:**
```json
{
  "rating": 4,
  "feedback_type": "quality",
  "feedback_text": "The options chain was accurate but loading states could be better"
}
```

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rating` | integer | Yes | Rating 1-5 |
| `feedback_type` | string | Yes | `quality`, `accuracy`, `usefulness`, `speed` |
| `feedback_text` | string | No | Optional detailed feedback |

**Response (201 Created):**
```json
{
  "feedback_id": "fb_xyz789",
  "generation_id": "gen_abc123xyz",
  "rating": 4,
  "feedback_type": "quality",
  "created_at": "2024-12-12T11:00:00Z"
}
```

---

### 5.10 Get/Update User Preferences

Manage user's GenUI preferences.

```http
GET /api/v1/genui/preferences
```

**Response (200 OK):**
```json
{
  "default_theme": "dark",
  "preferred_chart_type": "candlestick",
  "expertise_level": "advanced",
  "favorite_components": ["OptionsChainTable", "PayoffDiagram"],
  "custom_color_scheme": {
    "primary": "#2563EB",
    "positive": "#22C55E",
    "negative": "#EF4444"
  },
  "accessibility_settings": {
    "reduce_motion": false,
    "high_contrast": false,
    "large_text": false
  }
}
```

```http
PATCH /api/v1/genui/preferences
```

**Request Body:**
```json
{
  "default_theme": "light",
  "expertise_level": "intermediate"
}
```

---

## 6. GenUI WebSocket API

### 6.1 WebSocket Connection

Connect to receive real-time data updates for generated UIs.

```
wss://api.optix.io/ws/genui/{generation_id}?token={websocket_token}
```

**Connection Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `generation_id` | string | Generation ID to subscribe to |
| `token` | string | WebSocket authentication token |

**Connection Response:**
```json
{
  "type": "connected",
  "generation_id": "gen_abc123xyz",
  "subscriptions": ["quote:AAPL", "options_chain:AAPL"]
}
```

### 6.2 Message Types

**Data Update Message:**
```json
{
  "type": "data_update",
  "channel": "quote:AAPL",
  "data": {
    "symbol": "AAPL",
    "price": 185.75,
    "change": 1.25,
    "change_percent": 0.68,
    "volume": 45678900,
    "timestamp": "2024-12-12T15:30:00Z"
  }
}
```

**Options Chain Update:**
```json
{
  "type": "data_update",
  "channel": "options_chain:AAPL",
  "data": {
    "symbol": "AAPL",
    "expiration": "2024-01-19",
    "updated_strikes": [
      {
        "strike": 185,
        "call": {"bid": 3.50, "ask": 3.55, "delta": 0.52},
        "put": {"bid": 2.80, "ask": 2.85, "delta": -0.48}
      }
    ],
    "timestamp": "2024-12-12T15:30:00Z"
  }
}
```

**Error Message:**
```json
{
  "type": "error",
  "error": "subscription_failed",
  "message": "Failed to subscribe to channel: quote:INVALID"
}
```

### 6.3 Client Commands

**Subscribe to Additional Channel:**
```json
{
  "action": "subscribe",
  "channel": "flow:AAPL"
}
```

**Unsubscribe from Channel:**
```json
{
  "action": "unsubscribe",
  "channel": "quote:AAPL"
}
```

**Ping/Heartbeat:**
```json
{
  "action": "ping"
}
```

**Response:**
```json
{
  "type": "pong",
  "timestamp": "2024-12-12T15:30:00Z"
}
```

---

## 7. Supporting API Endpoints

The following endpoints support GenUI functionality by providing data and context.

### 7.1 Authentication Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/api/v1/auth/register` | User registration | Complete |
| POST | `/api/v1/auth/login` | User login | Complete |
| POST | `/api/v1/auth/refresh` | Refresh access token | Complete |
| POST | `/api/v1/auth/logout` | Logout current session | Complete |
| POST | `/api/v1/auth/logout-all` | Logout all sessions | Complete |
| POST | `/api/v1/auth/password/change` | Change password | Complete |
| POST | `/api/v1/auth/password/reset` | Request password reset | Complete |
| POST | `/api/v1/auth/password/reset/confirm` | Confirm password reset | Complete |
| POST | `/api/v1/auth/mfa/setup` | Setup MFA | Complete |
| POST | `/api/v1/auth/mfa/verify` | Verify MFA code | Complete |
| POST | `/api/v1/auth/mfa/disable` | Disable MFA | Complete |

#### 7.1.1 Register User

```http
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "email": "trader@example.com",
  "password": "SecureP@ss123!",
  "first_name": "John",
  "last_name": "Trader",
  "accept_terms": true
}
```

**Response (201 Created):**
```json
{
  "user_id": "usr_abc123",
  "email": "trader@example.com",
  "first_name": "John",
  "last_name": "Trader",
  "role": "user",
  "email_verified": false,
  "created_at": "2024-12-12T10:00:00Z"
}
```

#### 7.1.2 Login

```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "email": "trader@example.com",
  "password": "SecureP@ss123!",
  "device_info": {
    "device_id": "device_xyz789",
    "device_name": "iPhone 15 Pro",
    "platform": "ios"
  }
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "user_id": "usr_abc123",
    "email": "trader@example.com",
    "first_name": "John",
    "last_name": "Trader",
    "role": "premium"
  },
  "mfa_required": false
}
```

**Response (MFA Required):**
```json
{
  "mfa_required": true,
  "mfa_token": "mfa_temp_token_xyz",
  "mfa_methods": ["totp", "sms"]
}
```

---

### 7.2 User Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/users/me` | Get current user | Complete |
| PATCH | `/api/v1/users/me` | Update profile | Complete |
| GET | `/api/v1/users/me/profile` | Get detailed profile | Complete |
| GET | `/api/v1/users/me/sessions` | List active sessions | Complete |
| DELETE | `/api/v1/users/me/sessions/{session_id}` | Revoke session | Complete |

#### 7.2.1 Get Current User

```http
GET /api/v1/users/me
```

**Response (200 OK):**
```json
{
  "user_id": "usr_abc123",
  "email": "trader@example.com",
  "first_name": "John",
  "last_name": "Trader",
  "role": "premium",
  "subscription": {
    "tier": "pro",
    "expires_at": "2025-12-12T00:00:00Z",
    "features": ["genui", "flow", "gex"]
  },
  "mfa_enabled": true,
  "email_verified": true,
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

### 7.3 Market Data Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/quotes/{symbol}` | Get real-time quote | Complete |
| GET | `/api/v1/quotes` | Get batch quotes | Complete |
| GET | `/api/v1/options/expirations/{symbol}` | Get option expirations | Complete |
| GET | `/api/v1/options/chain/{symbol}` | Get options chain | Complete |
| GET | `/api/v1/historical/{symbol}` | Get historical data | Complete |
| WS | `/ws/quotes` | Real-time quote stream | Complete |

#### 7.3.1 Get Quote

```http
GET /api/v1/quotes/AAPL
```

**Response (200 OK):**
```json
{
  "symbol": "AAPL",
  "price": 185.50,
  "open": 184.25,
  "high": 186.75,
  "low": 183.50,
  "close": 184.00,
  "volume": 45678900,
  "change": 1.50,
  "change_percent": 0.82,
  "bid": 185.48,
  "ask": 185.52,
  "bid_size": 200,
  "ask_size": 300,
  "last_trade_time": "2024-12-12T15:30:00Z",
  "market_status": "open"
}
```

#### 7.3.2 Get Options Chain

```http
GET /api/v1/options/chain/AAPL?expiration=2024-01-19
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `expiration` | string | Expiration date (YYYY-MM-DD) |
| `strike_min` | number | Minimum strike price |
| `strike_max` | number | Maximum strike price |
| `option_type` | string | `call`, `put`, or `both` (default) |

**Response (200 OK):**
```json
{
  "symbol": "AAPL",
  "underlying_price": 185.50,
  "expiration": "2024-01-19",
  "days_to_expiration": 38,
  "strikes": [
    {
      "strike": 180,
      "call": {
        "symbol": "AAPL240119C00180000",
        "bid": 7.50,
        "ask": 7.60,
        "last": 7.55,
        "volume": 1234,
        "open_interest": 5678,
        "delta": 0.72,
        "gamma": 0.03,
        "theta": -0.08,
        "vega": 0.25,
        "iv": 0.28
      },
      "put": {
        "symbol": "AAPL240119P00180000",
        "bid": 2.10,
        "ask": 2.15,
        "last": 2.12,
        "volume": 890,
        "open_interest": 3456,
        "delta": -0.28,
        "gamma": 0.03,
        "theta": -0.06,
        "vega": 0.25,
        "iv": 0.29
      }
    }
  ]
}
```

---

### 7.4 Watchlist Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/watchlists` | List watchlists | Complete |
| POST | `/api/v1/watchlists` | Create watchlist | Complete |
| GET | `/api/v1/watchlists/{id}` | Get watchlist | Complete |
| PATCH | `/api/v1/watchlists/{id}` | Update watchlist | Complete |
| DELETE | `/api/v1/watchlists/{id}` | Delete watchlist | Complete |
| POST | `/api/v1/watchlists/{id}/symbols` | Add symbol | Complete |
| DELETE | `/api/v1/watchlists/{id}/symbols` | Remove symbol | Complete |

#### 7.4.1 Create Watchlist

```http
POST /api/v1/watchlists
```

**Request Body:**
```json
{
  "name": "Tech Stocks",
  "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA"]
}
```

**Response (201 Created):**
```json
{
  "id": "wl_abc123",
  "name": "Tech Stocks",
  "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA"],
  "symbol_count": 4,
  "created_at": "2024-12-12T10:00:00Z",
  "updated_at": "2024-12-12T10:00:00Z"
}
```

---

### 7.5 Alert Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/api/v1/alerts` | Create alert | Complete |
| GET | `/api/v1/alerts` | List alerts | Complete |
| GET | `/api/v1/alerts/{id}` | Get alert | Complete |
| DELETE | `/api/v1/alerts/{id}` | Delete alert | Complete |
| PATCH | `/api/v1/alerts/{id}/disable` | Disable alert | Complete |
| PATCH | `/api/v1/alerts/{id}/enable` | Enable alert | Complete |

#### 7.5.1 Create Alert

```http
POST /api/v1/alerts
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "alert_type": "price",
  "condition": "above",
  "value": 190.00,
  "notification_channels": ["push", "email"]
}
```

**Response (201 Created):**
```json
{
  "id": "alert_xyz789",
  "symbol": "AAPL",
  "alert_type": "price",
  "condition": "above",
  "value": 190.00,
  "status": "active",
  "notification_channels": ["push", "email"],
  "created_at": "2024-12-12T10:00:00Z",
  "triggered_at": null
}
```

---

### 7.6 Portfolio & Brokerage Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/brokerages` | List available brokerages | Complete |
| POST | `/api/v1/brokerages/{provider}/connect` | Initiate OAuth | Complete |
| GET | `/api/v1/brokerages/{provider}/callback` | OAuth callback | Complete |
| DELETE | `/api/v1/brokerages/{connection_id}/disconnect` | Disconnect | Complete |
| GET | `/api/v1/portfolio` | Get unified portfolio | Complete |
| GET | `/api/v1/portfolio/positions` | List all positions | Complete |
| GET | `/api/v1/portfolio/performance` | Get P&L analytics | Complete |
| POST | `/api/v1/portfolio/sync` | Trigger manual sync | Complete |
| GET | `/api/v1/transactions` | Get transaction history | Complete |

#### 7.6.1 Get Unified Portfolio

```http
GET /api/v1/portfolio
```

**Response (200 OK):**
```json
{
  "total_value": 125678.50,
  "cash_balance": 15000.00,
  "positions_value": 110678.50,
  "day_change": 1234.56,
  "day_change_percent": 0.99,
  "total_return": 15678.50,
  "total_return_percent": 14.25,
  "accounts": [
    {
      "brokerage": "schwab",
      "account_id": "acc_123",
      "account_name": "Individual Brokerage",
      "value": 75000.00,
      "cash": 10000.00
    },
    {
      "brokerage": "fidelity",
      "account_id": "acc_456",
      "account_name": "Roth IRA",
      "value": 50678.50,
      "cash": 5000.00
    }
  ],
  "greeks": {
    "delta": 125.5,
    "gamma": 8.2,
    "theta": -45.3,
    "vega": 234.1
  },
  "last_synced_at": "2024-12-12T15:30:00Z"
}
```

#### 7.6.2 Get Positions

```http
GET /api/v1/portfolio/positions
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `group_by` | string | `symbol`, `account`, `strategy` |
| `type` | string | `stock`, `option`, `all` |

**Response (200 OK):**
```json
{
  "positions": [
    {
      "id": "pos_abc123",
      "symbol": "AAPL",
      "underlying": "AAPL",
      "type": "stock",
      "quantity": 100,
      "avg_cost": 175.00,
      "current_price": 185.50,
      "market_value": 18550.00,
      "unrealized_pnl": 1050.00,
      "unrealized_pnl_percent": 6.00,
      "account": "schwab"
    },
    {
      "id": "pos_def456",
      "symbol": "AAPL240119C00190000",
      "underlying": "AAPL",
      "type": "option",
      "option_type": "call",
      "strike": 190,
      "expiration": "2024-01-19",
      "quantity": 5,
      "avg_cost": 3.50,
      "current_price": 4.25,
      "market_value": 2125.00,
      "unrealized_pnl": 375.00,
      "unrealized_pnl_percent": 21.43,
      "greeks": {
        "delta": 0.45,
        "gamma": 0.03,
        "theta": -0.05,
        "vega": 0.20
      },
      "account": "schwab"
    }
  ],
  "total_count": 15
}
```

---

### 7.7 GEX Visualizer Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| POST | `/api/v1/gex/calculate` | Calculate GEX from options chain | Complete |
| GET | `/api/v1/gex/calculate/{symbol}` | Calculate GEX for symbol | Complete |
| GET | `/api/v1/gex/heatmap/{symbol}` | Get GEX heatmap data | Complete |
| GET | `/api/v1/gex/gamma-flip/{symbol}` | Get gamma flip level | Complete |
| GET | `/api/v1/gex/market-maker/{symbol}` | Get market maker positioning | Complete |
| GET | `/api/v1/gex/alerts` | List GEX alerts | Complete |
| GET | `/api/v1/gex/alerts/active` | List active alerts | Complete |
| POST | `/api/v1/gex/alerts/{id}/acknowledge` | Acknowledge alert | Complete |
| GET | `/api/v1/gex/historical/{symbol}` | Get historical GEX | Complete |

#### 7.7.1 Calculate GEX

```http
GET /api/v1/gex/calculate/SPY
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `expiration` | string | Filter by expiration date |
| `include_all_expirations` | boolean | Include all expirations |

**Response (200 OK):**
```json
{
  "symbol": "SPY",
  "spot_price": 475.50,
  "calculation_time": "2024-12-12T15:30:00Z",
  "total_gex": {
    "call_gex": 2500000000,
    "put_gex": -1800000000,
    "net_gex": 700000000
  },
  "gamma_flip_level": 472.50,
  "current_regime": "positive_gamma",
  "pin_risk": {
    "max_pain": 473.00,
    "pin_probability": 0.35
  },
  "strikes": [
    {
      "strike": 470,
      "call_gex": 150000000,
      "put_gex": -120000000,
      "net_gex": 30000000,
      "call_oi": 45000,
      "put_oi": 38000
    }
  ],
  "market_maker_analysis": {
    "dealer_positioning": "long_gamma",
    "hedging_pressure": "supportive",
    "expected_volatility": "dampened"
  }
}
```

#### 7.7.2 Get GEX Heatmap

```http
GET /api/v1/gex/heatmap/SPY
```

**Response (200 OK):**
```json
{
  "symbol": "SPY",
  "spot_price": 475.50,
  "heatmap_data": [
    {
      "strike": 470,
      "expiration": "2024-12-15",
      "net_gex": 30000000,
      "intensity": 0.75,
      "color": "#22C55E"
    }
  ],
  "color_scale": {
    "positive_max": "#22C55E",
    "neutral": "#6B7280",
    "negative_max": "#EF4444"
  },
  "gamma_flip_level": 472.50
}
```

---

## 8. Adaptive Intelligence Engine Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/v1/ai/insights` | Get personalized insights | Complete |
| GET | `/api/v1/ai/patterns` | Get identified patterns | Complete |
| GET | `/api/v1/ai/guidance/{symbol}` | Get symbol guidance | Complete |
| GET | `/api/v1/ai/risk-calibration` | Get risk assessment | Complete |
| POST | `/api/v1/ai/feedback` | Submit insight feedback | Complete |
| POST | `/api/v1/patterns/detect/chart` | Detect chart patterns | Complete |
| POST | `/api/v1/patterns/detect/unusual-options` | Detect unusual options | Complete |
| POST | `/api/v1/analysis/predict` | Generate prediction signals | Complete |
| POST | `/api/v1/analysis/sentiment` | Get sentiment analysis | Complete |

#### 8.1 Get Personalized Insights

```http
GET /api/v1/ai/insights
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max insights to return |
| `types` | string | Filter by insight types |

**Response (200 OK):**
```json
{
  "insights": [
    {
      "id": "ins_abc123",
      "type": "pattern_match",
      "title": "Conditions match your profitable NVDA setups",
      "description": "Current IV rank (75%) and price consolidation pattern are similar to 3 of your winning NVDA trades in the past 90 days.",
      "symbol": "NVDA",
      "confidence": 0.78,
      "relevance_score": 0.92,
      "action_suggestion": "Review your typical entry criteria for this setup",
      "supporting_data": {
        "similar_trades": 3,
        "avg_return": 0.24,
        "iv_rank": 75
      },
      "created_at": "2024-12-12T09:00:00Z",
      "expires_at": "2024-12-12T16:00:00Z"
    }
  ],
  "total": 5,
  "unread": 2
}
```

#### 8.2 Get Risk Calibration

```http
GET /api/v1/ai/risk-calibration
```

**Response (200 OK):**
```json
{
  "current_exposure": {
    "options_percent": 68,
    "concentrated_positions": ["NVDA", "TSLA"],
    "total_delta": 450,
    "total_theta": -125
  },
  "historical_profile": {
    "typical_options_exposure": 45,
    "win_rate_at_current_exposure": 0.42,
    "optimal_exposure_range": [35, 55]
  },
  "recommendations": [
    {
      "type": "reduce_exposure",
      "severity": "warning",
      "message": "Current options exposure (68%) exceeds your historical comfort zone (35-55%). Your win rate drops to 42% at this exposure level.",
      "suggested_action": "Consider reducing options exposure by 13-23%"
    }
  ],
  "risk_score": 72,
  "risk_level": "elevated"
}
```

---

## 9. SDK & Client Libraries

### 9.1 JavaScript/TypeScript SDK

```typescript
import { OPTIXClient } from '@optix/sdk';

const client = new OPTIXClient({
  apiKey: 'your-api-key',
  environment: 'production'
});

// Generate UI
const generation = await client.genui.generate({
  query: 'Show me AAPL options chain',
  stream: true,
  onProgress: (event) => {
    console.log(`Progress: ${event.progress}%`);
  }
});

// Subscribe to real-time updates
const ws = client.genui.subscribe(generation.generation_id, {
  onDataUpdate: (data) => {
    console.log('Data update:', data);
  }
});
```

### 9.2 Python SDK

```python
from optix import OPTIXClient

client = OPTIXClient(api_key="your-api-key")

# Generate UI
generation = client.genui.generate(
    query="Show me AAPL options chain",
    context={"symbol": "AAPL"}
)

# Get generation result
result = client.genui.get(generation.generation_id)
print(result.html)

# Stream generation
for event in client.genui.generate_stream(query="Show portfolio Greeks"):
    print(f"Progress: {event.progress}%")
```

### 9.3 React Native Integration

```jsx
import { GenUIRenderer } from '@optix/react-native';

function GeneratedInterface({ generationId }) {
  return (
    <GenUIRenderer
      generationId={generationId}
      onDataRequest={(channel, params) => {
        // Bridge to native data layer
        return fetchDataFromBridge(channel, params);
      }}
      onInteraction={(event) => {
        // Handle user interactions
        analytics.track('genui_interaction', event);
      }}
      style={{ flex: 1 }}
    />
  );
}
```

---

## 10. Security Considerations

### 10.1 Generated Code Sandbox

All generated UI code executes in a sandboxed environment with:

- **CSP Headers:** Strict Content-Security-Policy
- **Disabled APIs:** `eval()`, `Function()`, `document.cookie`, `localStorage`
- **Network Isolation:** Only bridged API calls allowed
- **Input Sanitization:** All user inputs sanitized before processing

### 10.2 Data Access Controls

| Data Type | Access Control |
|-----------|----------------|
| Portfolio data | User's own data only |
| Generation history | User's own generations |
| Market data | Based on subscription tier |
| AI insights | Personalized per user |

### 10.3 Audit Logging

All GenUI operations are logged:

```json
{
  "event_type": "genui_generation",
  "user_id": "usr_abc123",
  "generation_id": "gen_xyz789",
  "query_hash": "sha256:...",
  "ip_address": "192.168.1.1",
  "user_agent": "OPTIX-iOS/2.0.0",
  "timestamp": "2024-12-12T10:30:00Z",
  "duration_ms": 2450,
  "status": "success"
}
```

---

## 11. Versioning & Deprecation

### 11.1 API Versioning

- Current version: `v1`
- Version specified in URL path: `/api/v1/...`
- Breaking changes require new major version
- Non-breaking additions to existing version

### 11.2 Deprecation Policy

- Minimum 6 months notice before deprecation
- Deprecated endpoints return `X-Deprecation-Warning` header
- Migration guides provided for breaking changes

### 11.3 Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-12 | 1.0.0 | Initial API release |

---

## 12. Appendix

### 12.1 Common Request Examples

**cURL Example - Generate UI:**
```bash
curl -X POST https://api.optix.io/api/v1/genui/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me AAPL options chain with high OI highlighted",
    "context": {"symbol": "AAPL"},
    "stream": false
  }'
```

**cURL Example - Get Quote:**
```bash
curl https://api.optix.io/api/v1/quotes/AAPL \
  -H "Authorization: Bearer <token>"
```

### 12.2 WebSocket Connection Example

```javascript
const ws = new WebSocket(
  `wss://api.optix.io/ws/genui/gen_abc123?token=${wsToken}`
);

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'data_update') {
    updateUI(message.channel, message.data);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### 12.3 Error Handling Example

```javascript
try {
  const response = await fetch('/api/v1/genui/generate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query: 'Show me AAPL options' })
  });

  if (!response.ok) {
    const error = await response.json();

    switch (error.error) {
      case 'rate_limit_exceeded':
        await sleep(error.retry_after * 1000);
        return retry();
      case 'token_expired':
        await refreshToken();
        return retry();
      case 'generation_failed':
        showError('Failed to generate UI. Please try again.');
        break;
      default:
        showError(error.message);
    }
  }

  const result = await response.json();
  renderGeneratedUI(result.html);

} catch (error) {
  showError('Network error. Please check your connection.');
}
```

---

*End of Document*

*Last Updated: December 12, 2024*
*Version: 1.0*
*Author: DSDM Agents System*
