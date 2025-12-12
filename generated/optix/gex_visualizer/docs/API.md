# GEX Visualizer API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, no authentication is required. For production, implement API key or OAuth2 authentication.

## Endpoints

### GEX Calculations

#### POST /gex/calculate

Calculate GEX for provided options chain data.

**Request Body:**
```json
{
  "symbol": "SPY",
  "spot_price": "450.00",
  "options_chain": [
    {
      "symbol": "SPY",
      "strike": "450.00",
      "expiration": "2024-02-16",
      "option_type": "call",
      "bid": "5.50",
      "ask": "5.75",
      "volume": 1000,
      "open_interest": 5000,
      "implied_volatility": 0.25,
      "delta": 0.55,
      "gamma": 0.01,
      "theta": -0.05,
      "vega": 0.15
    }
  ],
  "calculate_pin_risk": true,
  "include_historical": false
}
```

**Response:**
```json
{
  "symbol": "SPY",
  "spot_price": "450.00",
  "calculation_timestamp": "2024-01-15T10:30:00Z",
  "gamma_exposures": [...],
  "heatmap": {...},
  "gamma_flip": {...},
  "market_maker_position": {...},
  "pin_risk": {...},
  "alerts": [...]
}
```

#### GET /gex/calculate/{symbol}

Calculate GEX by automatically fetching options chain.

**Parameters:**
- `symbol` (path): Underlying symbol
- `spot_price` (query): Current spot price
- `calculate_pin_risk` (query, optional): Include pin risk analysis
- `include_historical` (query, optional): Include historical context

**Response:** Same as POST /gex/calculate

#### GET /gex/heatmap/{symbol}

Get latest GEX heatmap data.

**Response:**
```json
{
  "symbol": "SPY",
  "timestamp": "2024-01-15T10:30:00Z",
  "spot_price": "450.00",
  "strike_data": [
    {
      "strike": "450.00",
      "gex": 1500000000,
      "color": "green"
    }
  ],
  "total_call_gex": 4000000000,
  "total_put_gex": -1500000000,
  "total_net_gex": 2500000000,
  "gamma_flip_strike": "445.00",
  "market_regime": "positive_gamma"
}
```

#### GET /gex/gamma-flip/{symbol}

Get current gamma flip level.

**Response:**
```json
{
  "symbol": "SPY",
  "timestamp": "2024-01-15T10:30:00Z",
  "spot_price": "450.00",
  "gamma_flip_strike": "445.00",
  "distance_pct": 1.11,
  "market_regime": "near_flip",
  "is_near_flip": true
}
```

#### GET /gex/market-maker/{symbol}

Get market maker positioning.

**Response:**
```json
{
  "symbol": "SPY",
  "timestamp": "2024-01-15T10:30:00Z",
  "dealer_gamma_exposure": -2000000000,
  "dealer_position": "short_gamma",
  "hedging_pressure": "sell",
  "is_destabilizing": true
}
```

### Alerts

#### GET /alerts/

Get all alerts with optional filtering.

**Parameters:**
- `symbol` (query, optional): Filter by symbol
- `severity` (query, optional): Minimum severity (low/medium/high/critical)
- `acknowledged` (query, optional): Include acknowledged alerts

**Response:**
```json
[
  {
    "alert_id": "flip_abc123",
    "alert_type": "gamma_flip_proximity",
    "severity": "high",
    "symbol": "SPY",
    "message": "Price within 3% of gamma flip level at 445.00",
    "details": {...},
    "triggered_at": "2024-01-15T10:30:00Z",
    "acknowledged": false
  }
]
```

#### GET /alerts/active

Get all active (unacknowledged) alerts.

#### GET /alerts/critical

Get critical severity alerts only.

#### POST /alerts/{alert_id}/acknowledge

Acknowledge an alert.

**Parameters:**
- `acknowledged_by` (query): Username

**Response:**
```json
{
  "status": "success",
  "message": "Alert flip_abc123 acknowledged",
  "acknowledged_by": "trader1"
}
```

#### GET /alerts/summary

Get alert statistics summary.

**Response:**
```json
{
  "total_active": 5,
  "by_severity": {
    "critical": 1,
    "high": 2,
    "medium": 2,
    "low": 0
  },
  "by_type": {
    "gamma_flip_proximity": 2,
    "high_gex_concentration": 1,
    "pin_risk_warning": 1,
    "regime_change": 1
  },
  "by_symbol": {
    "SPY": 3,
    "QQQ": 2
  },
  "has_critical": true
}
```

### Historical Data

#### GET /historical/{symbol}

Get historical GEX data.

**Parameters:**
- `days` (query, optional): Number of days (default: 30, max: 365)

**Response:**
```json
[
  {
    "symbol": "SPY",
    "timestamp": "2024-01-15T10:30:00Z",
    "spot_price": "450.00",
    "total_gex": 2500000000,
    "call_gex": 4000000000,
    "put_gex": -1500000000,
    "gamma_flip_level": "445.00",
    "market_regime": "positive_gamma"
  }
]
```

#### GET /historical/{symbol}/summary

Get statistical summary of historical data.

**Response:**
```json
{
  "symbol": "SPY",
  "period_days": 30,
  "data_points": 30,
  "total_gex": {
    "current": 2500000000,
    "average": 2000000000,
    "median": 1800000000,
    "min": 500000000,
    "max": 4000000000,
    "std_dev": 800000000
  },
  "regime_distribution": {
    "counts": {
      "positive_gamma": 20,
      "negative_gamma": 8,
      "near_flip": 2
    },
    "percentages": {
      "positive_gamma": 66.67,
      "negative_gamma": 26.67,
      "near_flip": 6.67
    }
  }
}
```

#### GET /historical/{symbol}/chart

Get historical data formatted for charting.

**Response:**
```json
{
  "symbol": "SPY",
  "period_days": 30,
  "timestamps": ["2024-01-01T00:00:00Z", ...],
  "spot_prices": [440.00, 442.00, ...],
  "total_gex": [2000000000, 2100000000, ...],
  "call_gex": [3500000000, 3600000000, ...],
  "put_gex": [-1500000000, -1500000000, ...],
  "gamma_flip_levels": [435.00, 438.00, ...],
  "market_regimes": ["positive_gamma", "positive_gamma", ...]
}
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error response format:
```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

Currently no rate limiting is implemented. For production, implement appropriate rate limits based on your requirements.

## WebSocket Support

Real-time updates via WebSocket are planned for future versions.
