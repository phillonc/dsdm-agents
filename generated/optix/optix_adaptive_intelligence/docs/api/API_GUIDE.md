# API Guide - OPTIX Adaptive Intelligence Engine

## Overview

The OPTIX Adaptive Intelligence Engine provides RESTful API endpoints for pattern recognition, AI analysis, personalization, and alerts. All endpoints return JSON responses and follow consistent error handling patterns.

## Base URL

```
Development: http://localhost:8000
Production: https://api.optix-trading.com
```

## Authentication

All API requests require an API key passed in the header:

```http
X-API-Key: your-api-key-here
```

## Rate Limiting

- **Default**: 100 requests per minute per API key
- **Burst**: Up to 200 requests per minute for short periods
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Timestamp when limit resets

## Response Format

### Success Response

```json
{
  "data": { ... },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Symbol is required",
    "details": { ... }
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_abc123"
  }
}
```

## Endpoints

### Pattern Recognition

#### 1. Detect Chart Patterns

Detect technical chart patterns in price data.

```http
POST /api/v1/patterns/detect/chart
```

**Parameters:**
- `symbol` (required): Trading symbol (e.g., "AAPL")
- `start_date` (optional): Start date for analysis (ISO 8601)
- `end_date` (optional): End date for analysis (ISO 8601)

**Example Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/patterns/detect/chart?symbol=AAPL" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
[
  {
    "pattern_id": "pat_abc123",
    "symbol": "AAPL",
    "pattern_type": "head_shoulders",
    "confidence": 0.87,
    "detected_at": "2024-01-01T12:00:00Z",
    "trend_direction": "bearish",
    "price_target": 175.50,
    "stop_loss": 182.00,
    "support_level": 175.00,
    "resistance_level": 180.00,
    "volume_confirmation": true
  }
]
```

#### 2. Detect Support/Resistance Levels

Find key support and resistance price levels.

```http
POST /api/v1/patterns/detect/support-resistance
```

**Parameters:**
- `symbol` (required): Trading symbol
- `start_date` (optional): Start date for analysis
- `end_date` (optional): End date for analysis

**Example Response:**

```json
[
  {
    "level_id": "level_xyz789",
    "symbol": "AAPL",
    "price_level": 175.50,
    "level_type": "support",
    "strength": 0.85,
    "touches": 5,
    "time_relevance": 0.90,
    "broken": false
  }
]
```

#### 3. Detect Unusual Options Activity

Identify unusual options volume and activity.

```http
POST /api/v1/patterns/detect/unusual-options
```

**Parameters:**
- `symbol` (required): Trading symbol
- `min_volume_multiple` (optional, default: 3.0): Minimum volume multiple threshold

**Example Response:**

```json
[
  {
    "activity_id": "act_def456",
    "symbol": "AAPL",
    "detected_at": "2024-01-01T12:00:00Z",
    "activity_type": "golden_sweep",
    "strike": 180.0,
    "expiration": "2024-01-19T00:00:00Z",
    "option_type": "call",
    "volume": 15000,
    "volume_multiple": 10.5,
    "sentiment": "bullish",
    "confidence": 0.95
  }
]
```

### AI Analysis

#### 4. Generate Price Predictions

Generate ML-based price predictions with confidence intervals.

```http
POST /api/v1/analysis/predict
```

**Parameters:**
- `symbol` (required): Trading symbol
- `time_horizon` (optional, default: "1D"): Prediction horizon (1D, 1W, 1M, 3M)

**Example Response:**

```json
[
  {
    "signal_id": "sig_ghi789",
    "symbol": "AAPL",
    "signal_type": "buy",
    "signal_strength": "strong",
    "confidence": 0.82,
    "current_price": 178.50,
    "predicted_price": 185.00,
    "price_target": 188.00,
    "time_horizon": "1W",
    "prediction_range": {
      "min": 182.00,
      "max": 188.00,
      "std_dev": 2.5
    },
    "risk_reward_ratio": 2.5,
    "contributing_factors": [
      "sma_20: 0.0234 (importance: 0.234)",
      "rsi: 0.0189 (importance: 0.189)"
    ]
  }
]
```

#### 5. Forecast Volatility

Forecast future volatility using EWMA and GARCH models.

```http
POST /api/v1/analysis/volatility/forecast
```

**Parameters:**
- `symbol` (required): Trading symbol
- `forecast_horizon` (optional, default: "1W"): Forecast horizon (1D, 1W, 1M)

**Example Response:**

```json
{
  "forecast_id": "volf_jkl012",
  "symbol": "AAPL",
  "current_volatility": 0.25,
  "forecasted_volatility": 0.32,
  "volatility_regime": "high",
  "regime_change_probability": 0.75,
  "confidence_interval": {
    "lower": 0.28,
    "upper": 0.36
  },
  "historical_percentile": 78.5,
  "mean_reversion_signal": false
}
```

#### 6. Analyze Sentiment

Analyze market sentiment from multiple sources.

```http
POST /api/v1/analysis/sentiment
```

**Parameters:**
- `symbol` (required): Trading symbol
- `include_news` (optional, default: false): Include news sentiment
- `include_options` (optional, default: true): Include options flow sentiment

**Example Response:**

```json
{
  "analysis_id": "sent_mno345",
  "symbol": "AAPL",
  "overall_sentiment": "bullish",
  "sentiment_score": 0.65,
  "confidence": 0.78,
  "sentiment_shift": 0.15,
  "key_drivers": [
    "Strong earnings report",
    "Positive analyst upgrades",
    "Bullish options flow"
  ],
  "source_sentiments": {
    "options_flow": 0.72,
    "market_breadth": 0.58
  }
}
```

### Personalization

#### 7. Get User Profile

Retrieve user's trading profile and preferences.

```http
GET /api/v1/personalization/profile/{user_id}
```

**Example Response:**

```json
{
  "user_id": "user_123",
  "trading_style": "swing_trader",
  "risk_tolerance": "moderate",
  "preferred_symbols": ["AAPL", "MSFT", "GOOGL"],
  "preferred_timeframes": ["1D", "4H"],
  "preferred_strategies": ["momentum", "breakout"],
  "experience_level": "intermediate"
}
```

#### 8. Learn Trading Patterns

Analyze user's trading history to learn patterns.

```http
POST /api/v1/personalization/patterns/{user_id}/learn
```

**Parameters:**
- `user_id` (required, path): User identifier
- `days_back` (optional, default: 30): Number of days to analyze

**Example Response:**

```json
[
  {
    "pattern_id": "tp_pqr678",
    "user_id": "user_123",
    "pattern_type": "entry_rsi_oversold",
    "frequency": 25,
    "success_rate": 0.68,
    "average_return": 0.045,
    "average_holding_period": 36.5,
    "confidence": 0.82
  }
]
```

#### 9. Generate Personalized Insights

Generate customized trading insights for user.

```http
POST /api/v1/personalization/insights/{user_id}/generate
```

**Parameters:**
- `user_id` (required, path): User identifier
- `max_insights` (optional, default: 10): Maximum insights to return

**Example Response:**

```json
[
  {
    "insight_id": "ins_stu901",
    "user_id": "user_123",
    "insight_type": "opportunity",
    "priority": "high",
    "title": "Strong Bullish Setup on AAPL",
    "description": "Based on your swing trading profile...",
    "symbol": "AAPL",
    "actionable": true,
    "action_items": [
      "Consider entry near 178.50",
      "Set stop loss at 175.00",
      "Target price: 185.00"
    ],
    "relevance_score": 0.92,
    "confidence": 0.85,
    "expiry": "2024-01-02T00:00:00Z"
  }
]
```

### Alerts

#### 10. Create Alert Configuration

Configure alert preferences and thresholds.

```http
POST /api/v1/alerts/config/{user_id}
```

**Request Body:**

```json
{
  "enabled": true,
  "alert_type": "pattern_detected",
  "min_confidence": 0.8,
  "min_severity": "medium",
  "preferred_channels": ["in_app", "push"],
  "max_alerts_per_day": 20,
  "quiet_hours": {
    "start_hour": 22,
    "end_hour": 8
  }
}
```

**Example Response:**

```json
{
  "config_id": "cfg_vwx234",
  "user_id": "user_123",
  "enabled": true,
  "alert_type": "pattern_detected",
  "min_confidence": 0.8,
  "min_severity": "medium",
  "preferred_channels": ["in_app", "push"],
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 11. Send Test Alert

Send a test alert to verify configuration.

```http
POST /api/v1/alerts/test/{user_id}
```

**Parameters:**
- `user_id` (required, path): User identifier
- `alert_type` (optional): Type of alert to test
- `channel` (optional): Specific channel to test

**Example Response:**

```json
{
  "status": "success",
  "alert_id": "alert_test_123",
  "delivery_logs": [
    {
      "channel": "in_app",
      "status": "success",
      "delivery_time_ms": 145
    }
  ]
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_PARAMETER | 400 | Missing or invalid request parameter |
| UNAUTHORIZED | 401 | Invalid or missing API key |
| FORBIDDEN | 403 | Access denied to resource |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

## Best Practices

1. **Caching**: Cache responses when appropriate to reduce API calls
2. **Pagination**: Use limit parameters for large result sets
3. **Error Handling**: Always check response status and handle errors gracefully
4. **Rate Limiting**: Implement exponential backoff when rate limited
5. **Webhooks**: Use webhooks for real-time updates instead of polling
6. **Timeouts**: Set appropriate timeout values (recommended: 30 seconds)
7. **Retries**: Implement retry logic with exponential backoff for transient failures

## SDK Examples

### Python

```python
import requests

class OPTIXClient:
    def __init__(self, api_key, base_url="http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
    
    def detect_patterns(self, symbol):
        url = f"{self.base_url}/api/v1/patterns/detect/chart"
        response = self.session.post(url, params={"symbol": symbol})
        response.raise_for_status()
        return response.json()
    
    def get_predictions(self, symbol, time_horizon="1W"):
        url = f"{self.base_url}/api/v1/analysis/predict"
        response = self.session.post(url, params={
            "symbol": symbol,
            "time_horizon": time_horizon
        })
        response.raise_for_status()
        return response.json()

# Usage
client = OPTIXClient(api_key="your-api-key")
patterns = client.detect_patterns("AAPL")
predictions = client.get_predictions("AAPL", "1W")
```

### JavaScript/TypeScript

```javascript
class OPTIXClient {
  constructor(apiKey, baseUrl = 'http://localhost:8000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async detectPatterns(symbol) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/patterns/detect/chart?symbol=${symbol}`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': this.apiKey
        }
      }
    );
    return response.json();
  }

  async getPredictions(symbol, timeHorizon = '1W') {
    const response = await fetch(
      `${this.baseUrl}/api/v1/analysis/predict?symbol=${symbol}&time_horizon=${timeHorizon}`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': this.apiKey
        }
      }
    );
    return response.json();
  }
}

// Usage
const client = new OPTIXClient('your-api-key');
const patterns = await client.detectPatterns('AAPL');
const predictions = await client.getPredictions('AAPL', '1W');
```

## Support

For API support:
- Documentation: http://localhost:8000/docs
- Email: api-support@optix-trading.com
- Issues: GitHub Issues
