# VS-9 Smart Alerts API Guide

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All API endpoints require authentication via JWT Bearer token:
```
Authorization: Bearer <your_token>
```

## Alert Rules Management

### Create Alert Rule
Create a new alert rule with conditions.

**Endpoint**: `POST /alerts/rules`

**Request Body**:
```json
{
  "user_id": "user123",
  "name": "AAPL Breakout Alert",
  "description": "Alert when AAPL breaks above $150",
  "conditions": [
    {
      "condition_type": "price_above",
      "symbol": "AAPL",
      "threshold": 150.0,
      "timeframe": "5m"
    }
  ],
  "logic": "AND",
  "priority": "high",
  "market_hours_only": true,
  "allowed_sessions": ["regular"],
  "cooldown_minutes": 5,
  "tags": ["price", "breakout"]
}
```

**Response** (201 Created):
```json
{
  "rule_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "AAPL Breakout Alert",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Alert Rule
Retrieve details of a specific alert rule.

**Endpoint**: `GET /alerts/rules/{rule_id}`

**Response** (200 OK):
```json
{
  "rule_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "name": "AAPL Breakout Alert",
  "description": "Alert when AAPL breaks above $150",
  "priority": "high",
  "status": "active",
  "trigger_count": 5,
  "action_count": 4,
  "relevance_score": 0.75,
  "created_at": "2024-01-15T10:30:00Z",
  "last_triggered_at": "2024-01-15T14:30:00Z",
  "conditions": [
    {
      "condition_id": "cond-001",
      "condition_type": "price_above",
      "symbol": "AAPL",
      "threshold": 150.0
    }
  ]
}
```

### List Alert Rules
List all alert rules with optional filters.

**Endpoint**: `GET /alerts/rules`

**Query Parameters**:
- `user_id` (optional): Filter by user
- `status` (optional): Filter by status (active, triggered, expired)
- `symbol` (optional): Filter by symbol

**Example**: `GET /alerts/rules?user_id=user123&status=active`

**Response** (200 OK):
```json
{
  "total": 15,
  "rules": [
    {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "AAPL Breakout Alert",
      "priority": "high",
      "status": "active",
      "trigger_count": 5,
      "relevance_score": 0.75
    },
    ...
  ]
}
```

### Update Alert Rule
Update an existing alert rule.

**Endpoint**: `PATCH /alerts/rules/{rule_id}`

**Request Body**:
```json
{
  "name": "Updated Alert Name",
  "priority": "urgent",
  "cooldown_minutes": 10,
  "tags": ["updated", "priority"]
}
```

**Response** (200 OK):
```json
{
  "message": "Alert rule updated",
  "rule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Delete Alert Rule
Delete an alert rule.

**Endpoint**: `DELETE /alerts/rules/{rule_id}`

**Response** (200 OK):
```json
{
  "message": "Alert rule deleted",
  "rule_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Market Data Evaluation

### Evaluate Market Data
Evaluate market data against all active alert rules.

**Endpoint**: `POST /alerts/evaluate`

**Request Body**:
```json
{
  "symbol": "AAPL",
  "price": 155.50,
  "bid": 155.45,
  "ask": 155.55,
  "volume": 1250000,
  "price_change_percent": 3.2,
  "volume_ratio": 2.5,
  "implied_volatility": 0.35,
  "iv_rank": 45.5,
  "put_call_ratio": 0.75,
  "unusual_activity_score": 3.8,
  "session": "regular"
}
```

**Response** (200 OK):
```json
{
  "triggered_alerts": 3,
  "consolidated_alerts": 1,
  "alerts": [
    {
      "alert_id": "alert-001",
      "title": "3 alerts for AAPL",
      "summary": "AAPL: price_above, volume_above | Priority: HIGH",
      "priority": "high",
      "alert_count": 3,
      "delivery_results": {
        "in_app": "sent",
        "push": "sent",
        "email": "sent"
      }
    }
  ]
}
```

## Learning & User Actions

### Record User Action
Record a user action on an alert for learning purposes.

**Endpoint**: `POST /alerts/actions?user_id={user_id}`

**Request Body**:
```json
{
  "alert_id": "alert-001",
  "action_type": "opened_position",
  "action_timestamp": "2024-01-15T14:35:00Z"
}
```

**Action Types**:
- `opened_position`: User opened a trade
- `closed_position`: User closed a trade
- `adjusted_position`: User adjusted position
- `acknowledged`: User acknowledged alert
- `snoozed`: User snoozed alert
- `dismissed`: User dismissed alert

**Response** (200 OK):
```json
{
  "message": "User action recorded",
  "user_id": "user123"
}
```

### Get User Profile
Get learned user profile with preferences and behavior.

**Endpoint**: `GET /alerts/profile/{user_id}`

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "action_rate": 0.75,
  "avg_response_time_seconds": 45.5,
  "most_acted_conditions": [
    "price_above",
    "volume_above",
    "unusual_activity"
  ],
  "preferred_priorities": ["high", "urgent"],
  "active_trading_hours": ["09:00", "10:00", "14:00", "15:00"],
  "symbol_interests": {
    "AAPL": 0.85,
    "SPY": 0.72,
    "NVDA": 0.68
  },
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Get Recommendations
Get personalized alert recommendations based on learned behavior.

**Endpoint**: `GET /alerts/recommendations/{user_id}?top_n=5`

**Query Parameters**:
- `top_n` (optional, default: 5): Number of recommendations

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "recommendations": [
    {
      "condition_type": "price_above",
      "relevance_score": 0.85,
      "reason": "You frequently act on price_above alerts",
      "suggested_priority": "high",
      "rank": 1
    },
    {
      "condition_type": "unusual_activity",
      "relevance_score": 0.78,
      "reason": "You frequently act on unusual_activity alerts",
      "suggested_priority": "high",
      "rank": 2
    }
  ]
}
```

### Get Analytics
Get alert performance analytics for a user.

**Endpoint**: `GET /alerts/analytics/{user_id}?days=30`

**Query Parameters**:
- `days` (optional, default: 30): Analysis period in days

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "period_start": "2023-12-15T00:00:00Z",
  "period_end": "2024-01-15T00:00:00Z",
  "total_triggers": 150,
  "acted_upon_count": 112,
  "action_rate": 0.747,
  "relevance_score": 0.75,
  "triggers_by_condition": {
    "price_above": 45,
    "volume_above": 38,
    "unusual_activity": 32,
    "iv_above": 35
  },
  "triggers_by_priority": {
    "low": 20,
    "medium": 50,
    "high": 60,
    "urgent": 20
  }
}
```

## Delivery Preferences

### Get Delivery Preferences
Get user's notification delivery preferences.

**Endpoint**: `GET /delivery/preferences/{user_id}`

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "enabled_channels": ["in_app", "push", "email"],
  "email": "user@example.com",
  "phone": "+1234567890",
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "07:00",
  "enable_consolidation": true,
  "max_alerts_per_hour": 50
}
```

### Update Delivery Preferences
Update user's notification preferences.

**Endpoint**: `PUT /delivery/preferences/{user_id}`

**Request Body**:
```json
{
  "enabled_channels": ["in_app", "push", "email", "sms"],
  "email": "newemail@example.com",
  "phone": "+1987654321",
  "quiet_hours_start": "23:00",
  "quiet_hours_end": "06:00",
  "enable_consolidation": true,
  "max_alerts_per_hour": 30
}
```

**Response** (200 OK):
```json
{
  "message": "Delivery preferences updated",
  "user_id": "user123"
}
```

### Test Delivery Channel
Test a specific delivery channel.

**Endpoint**: `POST /delivery/test/{user_id}/{channel}`

**Channel Options**: `in_app`, `push`, `email`, `sms`, `webhook`

**Example**: `POST /delivery/test/user123/email`

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "channel": "email",
  "status": "sent",
  "success": true
}
```

## Alert Templates

### List Templates
List available alert templates.

**Endpoint**: `GET /templates`

**Query Parameters**:
- `category` (optional): Filter by category
- `tag` (optional): Filter by tag

**Example**: `GET /templates?category=price_action`

**Response** (200 OK):
```json
{
  "total": 10,
  "templates": [
    {
      "template_id": "tpl-001",
      "name": "Price Breakout Alert",
      "description": "Alert when price breaks above resistance or below support",
      "category": "price_action",
      "tags": ["price", "breakout", "momentum"],
      "usage_count": 245
    },
    ...
  ]
}
```

### Get Template Details
Get detailed information about a specific template.

**Endpoint**: `GET /templates/{template_id}`

**Response** (200 OK):
```json
{
  "template_id": "tpl-001",
  "name": "Price Breakout Alert",
  "description": "Alert when price breaks above resistance or below support",
  "category": "price_action",
  "condition_templates": [
    {
      "condition_type": "price_above",
      "threshold": 0.0,
      "timeframe": "5m"
    }
  ],
  "logic": "AND",
  "default_priority": "high",
  "recommended_cooldown": 15,
  "tags": ["price", "breakout", "momentum"],
  "usage_count": 245
}
```

### Apply Template
Create an alert rule from a template.

**Endpoint**: `POST /templates/apply?user_id={user_id}`

**Request Body**:
```json
{
  "template_id": "tpl-001",
  "symbol": "AAPL",
  "overrides": {
    "threshold": 150.0,
    "priority": "urgent",
    "cooldown_minutes": 30
  }
}
```

**Response** (200 OK):
```json
{
  "rule_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Price Breakout Alert - AAPL",
  "template_id": "tpl-001"
}
```

### Search Templates
Search templates by keyword.

**Endpoint**: `GET /templates/search?q={query}`

**Example**: `GET /templates/search?q=volatility`

**Response** (200 OK):
```json
{
  "query": "volatility",
  "total": 3,
  "results": [
    {
      "template_id": "tpl-002",
      "name": "Volatility Spike",
      "description": "Alert when implied volatility spikes significantly",
      "category": "volatility"
    },
    ...
  ]
}
```

## System Statistics

### Engine Statistics
Get alert engine statistics.

**Endpoint**: `GET /stats/engine`

**Response** (200 OK):
```json
{
  "total_active_rules": 1250,
  "rules_in_cooldown": 45,
  "rules_by_priority": {
    "low": 200,
    "medium": 500,
    "high": 400,
    "urgent": 150
  },
  "rules_by_category": {
    "price_action": 450,
    "volatility": 300,
    "flow": 250,
    "custom": 250
  }
}
```

### Learning Statistics
Get learning engine statistics.

**Endpoint**: `GET /stats/learning`

**Response** (200 OK):
```json
{
  "total_users": 5000,
  "users_with_learned_profiles": 3200,
  "total_actions_recorded": 125000,
  "learning_rate": 0.1,
  "min_samples_for_learning": 10
}
```

### Consolidation Statistics
Get consolidation engine statistics.

**Endpoint**: `GET /stats/consolidation`

**Response** (200 OK):
```json
{
  "total_pending_alerts": 125,
  "users_with_pending": 45,
  "total_consolidations": 5000,
  "total_alerts_consolidated": 18000,
  "avg_alerts_per_consolidation": 3.6,
  "consolidation_window_minutes": 5
}
```

### Delivery Statistics
Get delivery statistics.

**Endpoint**: `GET /stats/delivery?user_id={user_id}`

**Query Parameters**:
- `user_id` (optional): Get stats for specific user

**Response** (200 OK):
```json
{
  "total_deliveries": 8500,
  "by_channel": {
    "in_app": 8500,
    "push": 6000,
    "email": 2500,
    "sms": 500
  },
  "by_status": {
    "sent": 8200,
    "failed": 200,
    "rate_limited": 100
  },
  "success_rate": 96.47
}
```

## Health Check

### Health Status
Check system health.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "version": "1.0.0",
  "components": {
    "alert_engine": "operational",
    "learning_engine": "operational",
    "consolidation_engine": "operational",
    "notification_service": "operational",
    "template_manager": "operational"
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid condition type specified"
}
```

### 404 Not Found
```json
{
  "detail": "Alert rule not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error occurred"
}
```

## Rate Limits

- **API Calls**: 1000 requests per hour per user
- **Alert Evaluations**: 10,000 per minute (system-wide)
- **Notifications**: Configurable per user (default 50/hour)

## WebSocket Support (Future)

Real-time alert streaming will be available via WebSocket:

```
ws://localhost:8000/ws/alerts/{user_id}
```

## SDKs & Client Libraries

Official SDKs available for:
- Python
- JavaScript/TypeScript
- Java
- Go

Example Python SDK usage:
```python
from optix_alerts import AlertsClient

client = AlertsClient(api_key="your_api_key")

# Create alert
rule = client.alerts.create_rule(
    name="AAPL Breakout",
    conditions=[...],
    priority="high"
)

# Get recommendations
recommendations = client.learning.get_recommendations(user_id="user123")
```
