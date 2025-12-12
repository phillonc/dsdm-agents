# API Reference

## Base URL
```
http://localhost:5000/api/v1
```

## Authentication
Currently no authentication required. JWT authentication will be added in future versions.

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response
```json
{
  "error": "Error description"
}
```

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "Visual Strategy Builder",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00"
}
```

---

### Strategy Management

#### POST /api/v1/strategies
Create a new strategy.

**Request Body (From Template):**
```json
{
  "template_type": "IRON_CONDOR",
  "underlying_symbol": "SPY",
  "current_price": 450.0,
  "expiration": "2024-02-15",
  "params": {
    "wing_width": 5.0,
    "body_width": 10.0,
    "quantity": 1
  }
}
```

**Request Body (Custom Strategy):**
```json
{
  "name": "My Custom Strategy",
  "underlying_symbol": "AAPL",
  "strategy_type": "CUSTOM"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "name": "Iron Condor - SPY",
    "strategy_type": "IRON_CONDOR",
    "underlying_symbol": "SPY",
    "legs": [...],
    "total_cost": 200.0,
    "aggregated_greeks": {
      "delta": 0.05,
      "gamma": 0.01,
      "theta": 0.25,
      "vega": -0.10,
      "rho": 0.02
    },
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "message": "Strategy created successfully"
}
```

#### GET /api/v1/strategies
List all strategies.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-1",
      "name": "Iron Condor - SPY",
      "strategy_type": "IRON_CONDOR",
      "underlying_symbol": "SPY",
      ...
    },
    {
      "id": "uuid-2",
      "name": "Long Straddle - AAPL",
      "strategy_type": "STRADDLE",
      "underlying_symbol": "AAPL",
      ...
    }
  ]
}
```

#### GET /api/v1/strategies/{strategy_id}
Get a specific strategy.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "name": "Iron Condor - SPY",
    "strategy_type": "IRON_CONDOR",
    "underlying_symbol": "SPY",
    "legs": [
      {
        "id": "leg-uuid-1",
        "option_type": "PUT",
        "position_type": "LONG",
        "strike": 440.0,
        "expiration": "2024-02-15",
        "quantity": 1,
        "premium": 0.50,
        "underlying_symbol": "SPY",
        "implied_volatility": 0.25,
        "greeks": {
          "delta": -0.10,
          "gamma": 0.02,
          "theta": 0.05,
          "vega": 0.08,
          "rho": -0.02
        },
        "cost": -50.0
      },
      ...
    ],
    "total_cost": 200.0,
    "aggregated_greeks": {...},
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "notes": "Strategy notes"
  }
}
```

#### DELETE /api/v1/strategies/{strategy_id}
Delete a strategy.

**Response:**
```json
{
  "success": true,
  "data": null,
  "message": "Strategy deleted successfully"
}
```

---

### Leg Management

#### POST /api/v1/strategies/{strategy_id}/legs
Add a leg to a strategy.

**Request Body:**
```json
{
  "option_type": "CALL",
  "position_type": "LONG",
  "strike": 455.0,
  "expiration": "2024-02-15",
  "quantity": 1,
  "premium": 5.50,
  "implied_volatility": 0.28,
  "greeks": {
    "delta": 0.55,
    "gamma": 0.03,
    "theta": -0.08,
    "vega": 0.18,
    "rho": 0.05
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "leg-uuid",
    "option_type": "CALL",
    "position_type": "LONG",
    "strike": 455.0,
    ...
  },
  "message": "Leg added successfully"
}
```

#### DELETE /api/v1/strategies/{strategy_id}/legs/{leg_id}
Remove a leg from a strategy.

**Response:**
```json
{
  "success": true,
  "data": null,
  "message": "Leg removed successfully"
}
```

---

### Analysis

#### GET /api/v1/strategies/{strategy_id}/payoff
Get payoff diagram data.

**Query Parameters:**
- `current_price` (required): Current price of underlying

**Example:**
```
GET /api/v1/strategies/{strategy_id}/payoff?current_price=450.0
```

**Response:**
```json
{
  "success": true,
  "data": {
    "price_range": [315.0, 317.0, 319.0, ..., 585.0],
    "pnl_data": [
      {"price": 315.0, "pnl": -300.0},
      {"price": 317.0, "pnl": -290.0},
      ...
    ],
    "max_profit": 200.0,
    "max_loss": -300.0,
    "breakeven_points": [445.0, 455.0],
    "current_price": 450.0,
    "current_pnl": 0.0,
    "total_cost": 200.0,
    "num_legs": 4
  }
}
```

#### POST /api/v1/strategies/{strategy_id}/scenarios
Run scenario analysis.

**Request Body (Price Scenario):**
```json
{
  "current_price": 450.0,
  "scenario_type": "price",
  "params": {
    "price_changes": [-10, -5, 0, 5, 10]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "type": "price",
    "results": [
      {
        "price_change_percent": -10,
        "new_price": 405.0,
        "pnl": -150.0,
        "pnl_change": -150.0,
        "return_percent": -75.0
      },
      ...
    ]
  }
}
```

**Request Body (Volatility Scenario):**
```json
{
  "current_price": 450.0,
  "scenario_type": "volatility",
  "params": {
    "volatility_changes": [-20, -10, 0, 10, 20]
  }
}
```

**Request Body (Time Decay):**
```json
{
  "current_price": 450.0,
  "scenario_type": "time",
  "params": {
    "days_forward": [1, 7, 14, 30]
  }
}
```

**Request Body (Combined Scenario):**
```json
{
  "current_price": 450.0,
  "scenario_type": "combined",
  "params": {
    "price_change_pct": 5,
    "volatility_change_pct": 10,
    "days_forward": 7
  }
}
```

**Request Body (Stress Test):**
```json
{
  "current_price": 450.0,
  "scenario_type": "stress"
}
```

**Response (Stress Test):**
```json
{
  "success": true,
  "data": {
    "type": "stress",
    "results": {
      "market_crash": {
        "description": "Severe market downturn",
        "price_change_percent": -20,
        "volatility_change_percent": 50,
        "estimated_total_pnl": -250.0,
        "price_pnl": -200.0,
        "vega_impact": -50.0,
        "theta_impact": 0.0
      },
      "market_rally": {...},
      "volatility_spike": {...},
      "volatility_crush": {...}
    }
  }
}
```

**Request Body (Sensitivity Analysis):**
```json
{
  "current_price": 450.0,
  "scenario_type": "sensitivity"
}
```

#### GET /api/v1/strategies/{strategy_id}/risk-metrics
Get comprehensive risk metrics.

**Query Parameters:**
- `current_price` (required): Current price of underlying

**Response:**
```json
{
  "success": true,
  "data": {
    "strategy_id": "uuid-string",
    "strategy_name": "Iron Condor - SPY",
    "greeks": {
      "delta": 0.05,
      "gamma": 0.01,
      "theta": 0.25,
      "vega": -0.10,
      "rho": 0.02
    },
    "risk_reward": {
      "max_profit": 200.0,
      "max_loss": -300.0,
      "risk_reward_ratio": 0.67,
      "return_on_risk_percent": 66.67,
      "total_capital_at_risk": 300.0
    },
    "probability_analysis": {
      "probability_of_profit": 67.5,
      "average_profit": 150.0,
      "average_loss": -200.0,
      "expected_value": 35.0,
      "simulations": 10000
    }
  }
}
```

---

### Real-Time P&L

#### POST /api/v1/strategies/{strategy_id}/pnl
Update P&L for a strategy.

**Request Body:**
```json
{
  "current_price": 455.0,
  "timestamp": "2024-01-15T14:30:00"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T14:30:00",
    "underlying_price": 455.0,
    "pnl": -50.0,
    "total_cost": 200.0,
    "greeks": {
      "delta": 0.08,
      "gamma": 0.01,
      "theta": 0.22,
      "vega": -0.09,
      "rho": 0.03
    }
  }
}
```

#### GET /api/v1/strategies/{strategy_id}/pnl/history
Get P&L history for a strategy.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00",
      "underlying_price": 450.0,
      "pnl": 0.0,
      "total_cost": 200.0,
      "greeks": {...}
    },
    {
      "timestamp": "2024-01-15T11:00:00",
      "underlying_price": 452.0,
      "pnl": -25.0,
      "total_cost": 200.0,
      "greeks": {...}
    },
    ...
  ]
}
```

---

### Import/Export

#### GET /api/v1/strategies/{strategy_id}/export
Export a strategy.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "name": "Iron Condor - SPY",
    "strategy_type": "IRON_CONDOR",
    "underlying_symbol": "SPY",
    "legs": [...],
    "total_cost": 200.0,
    "aggregated_greeks": {...},
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "notes": "Strategy notes"
  }
}
```

#### POST /api/v1/strategies/import
Import a strategy.

**Request Body:**
```json
{
  "name": "Imported Strategy",
  "underlying_symbol": "SPY",
  "strategy_type": "CUSTOM",
  "notes": "Imported from another system",
  "legs": [
    {
      "option_type": "CALL",
      "position_type": "LONG",
      "strike": 450.0,
      "expiration": "2024-02-15",
      "quantity": 1,
      "premium": 5.0,
      "underlying_symbol": "SPY",
      "implied_volatility": 0.25,
      "greeks": {
        "delta": 0.5,
        "gamma": 0.02,
        "theta": -0.05,
        "vega": 0.15,
        "rho": 0.03
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "new-uuid",
    "name": "Imported Strategy",
    ...
  },
  "message": "Strategy imported successfully"
}
```

---

### Templates

#### GET /api/v1/templates
List available strategy templates.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "type": "IRON_CONDOR",
      "name": "Iron Condor",
      "description": "Four-leg strategy for low volatility markets",
      "required_params": ["underlying_symbol", "current_price", "expiration"],
      "optional_params": ["wing_width", "body_width", "quantity"]
    },
    {
      "type": "BUTTERFLY",
      "name": "Butterfly Spread",
      "description": "Three-strike strategy for minimal price movement",
      "required_params": ["underlying_symbol", "current_price", "expiration"],
      "optional_params": ["wing_width", "quantity", "option_type"]
    },
    ...
  ]
}
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently no rate limiting. Will be implemented in future versions.

---

## Pagination

Currently no pagination. All results returned in single response.

---

## Versioning

API version included in URL path: `/api/v1/`

Breaking changes will increment major version: `/api/v2/`

---

## Examples

### Example 1: Create and Analyze Iron Condor

```bash
# Create Iron Condor
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "IRON_CONDOR",
    "underlying_symbol": "SPY",
    "current_price": 450.0,
    "expiration": "2024-02-15",
    "params": {
      "wing_width": 5.0,
      "body_width": 10.0
    }
  }'

# Get payoff diagram
curl -X GET "http://localhost:5000/api/v1/strategies/{strategy_id}/payoff?current_price=450.0"

# Run stress test
curl -X POST http://localhost:5000/api/v1/strategies/{strategy_id}/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "current_price": 450.0,
    "scenario_type": "stress"
  }'
```

### Example 2: Build Custom Strategy

```bash
# Create custom strategy
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Bull Call Spread",
    "underlying_symbol": "AAPL",
    "strategy_type": "CUSTOM"
  }'

# Add long call
curl -X POST http://localhost:5000/api/v1/strategies/{strategy_id}/legs \
  -H "Content-Type: application/json" \
  -d '{
    "option_type": "CALL",
    "position_type": "LONG",
    "strike": 170.0,
    "expiration": "2024-02-15",
    "quantity": 1,
    "premium": 5.50,
    "implied_volatility": 0.28
  }'

# Add short call
curl -X POST http://localhost:5000/api/v1/strategies/{strategy_id}/legs \
  -H "Content-Type: application/json" \
  -d '{
    "option_type": "CALL",
    "position_type": "SHORT",
    "strike": 180.0,
    "expiration": "2024-02-15",
    "quantity": 1,
    "premium": 2.50,
    "implied_volatility": 0.26
  }'

# Get risk metrics
curl -X GET "http://localhost:5000/api/v1/strategies/{strategy_id}/risk-metrics?current_price=175.0"
```
