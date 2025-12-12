## API Reference - Options Flow Intelligence

### Core Engine

#### `OptionsFlowIntelligence`

Main engine for options flow analysis.

**Constructor:**
```python
OptionsFlowIntelligence(
    enable_alerts: bool = True,
    alert_dispatch_channels: Optional[List[str]] = None
)
```

**Parameters:**
- `enable_alerts`: Enable real-time alerting
- `alert_dispatch_channels`: Alert dispatch channels (default: ['console'])

---

### Trade Processing

#### `process_trade(trade, market_timestamp=None)`

Process incoming options trade through all detectors.

**Parameters:**
- `trade` (OptionsTrade): Options trade to process
- `market_timestamp` (datetime, optional): Current market time

**Returns:**
```python
{
    'trade_id': str,
    'symbol': str,
    'timestamp': str,
    'detections': [
        {'type': str, 'confidence': float, ...}
    ],
    'patterns': [
        {'pattern_id': str, 'type': str, 'signal': str, ...}
    ],
    'alerts': [str]  # Alert IDs
}
```

**Example:**
```python
result = engine.process_trade(trade)
if result['detections']:
    print(f"Detected: {result['detections']}")
```

---

### Market Maker Analysis

#### `calculate_market_maker_position(symbol, lookback_minutes=60, option_chain_data=None)`

Calculate estimated market maker positioning.

**Parameters:**
- `symbol` (str): Underlying symbol
- `lookback_minutes` (int): Analysis window
- `option_chain_data` (dict, optional): Option chain data

**Returns:** `MarketMakerPosition` object

**Attributes:**
- `net_delta`: Net delta exposure
- `net_gamma`: Net gamma exposure
- `net_vega`: Net vega exposure
- `net_theta`: Net theta exposure
- `position_bias`: Position bias (PositionBias enum)
- `hedge_pressure`: "buy", "sell", or "neutral"
- `max_pain_price`: Max pain strike price
- `is_gamma_squeeze_risk`: Gamma squeeze risk flag

**Example:**
```python
position = engine.calculate_market_maker_position("AAPL")
print(f"Net Gamma: {position.net_gamma}")
print(f"Hedge Pressure: {position.hedge_pressure}")
```

---

### Order Flow Analysis

#### `get_order_flow_summary(symbol, lookback_minutes=None)`

Get aggregated order flow summary.

**Parameters:**
- `symbol` (str): Underlying symbol
- `lookback_minutes` (int, optional): Lookback period

**Returns:**
```python
{
    'symbol': str,
    'timestamp': str,
    'total_trades': int,
    'total_premium': str,
    'total_volume': int,
    'call': {
        'trades': int,
        'premium': str,
        'volume': int,
        'avg_premium': str
    },
    'put': {...},
    'call_put_ratio': {
        'premium': str,
        'volume': str
    },
    'by_type': {
        'sweep': {'count': int, 'premium': str},
        'block': {...},
        'dark_pool': {...}
    },
    'sentiment': str,
    'institutional': {...}
}
```

#### `get_institutional_flow(lookback_minutes=None)`

Get institutional flow summary.

**Returns:**
```python
{
    'timestamp': str,
    'total_trades': int,
    'total_premium': str,
    'unique_symbols': int,
    'symbols': [
        {
            'symbol': str,
            'trades': int,
            'premium': str,
            'call_premium': str,
            'put_premium': str,
            'sentiment': str
        }
    ]
}
```

#### `get_flow_by_strike(symbol, expiration=None)`

Get flow aggregated by strike.

**Parameters:**
- `symbol` (str): Underlying symbol
- `expiration` (datetime, optional): Specific expiration

**Returns:**
```python
{
    'symbol': str,
    'expiration': str,
    'strikes': [
        {
            'strike': str,
            'call_volume': int,
            'put_volume': int,
            'call_premium': str,
            'put_premium': str,
            'net_volume': int,
            'net_premium': str
        }
    ]
}
```

---

### Alert Management

#### `get_active_alerts(symbol=None, min_severity=None)`

Get active alerts with filters.

**Parameters:**
- `symbol` (str, optional): Filter by symbol
- `min_severity` (str, optional): Minimum severity ('critical', 'high', 'medium', 'low', 'info')

**Returns:** List of alert dictionaries

#### `acknowledge_alert(alert_id, user='system')`

Acknowledge an alert.

**Parameters:**
- `alert_id` (str): Alert ID
- `user` (str): User acknowledging

**Returns:** bool - Success status

#### `subscribe_to_alerts(callback, alert_type=None)`

Subscribe to real-time alerts.

**Parameters:**
- `callback` (callable): Function to call on alert
- `alert_type` (str, optional): Specific alert type

**Alert Types:**
- 'sweep': Unusual sweep alerts
- 'block': Large block alerts
- 'dark_pool': Dark pool print alerts
- 'smart_money': Smart money flow alerts
- 'institutional': Institutional pattern alerts
- 'gamma_squeeze': Gamma squeeze alerts
- 'volume': Volume spike alerts

**Example:**
```python
def my_callback(alert):
    print(f"Alert: {alert.title}")
    
engine.subscribe_to_alerts(my_callback, alert_type='sweep')
```

#### `add_alert_webhook(url)`

Add webhook URL for alert dispatch.

**Parameters:**
- `url` (str): Webhook URL

---

### Statistics

#### `get_statistics()`

Get engine statistics.

**Returns:**
```python
{
    'engine': {
        'trades_processed': int,
        'sweeps_detected': int,
        'blocks_detected': int,
        'dark_pools_detected': int,
        'patterns_detected': int,
        'alerts_created': int
    },
    'alerts': {
        'total_created': int,
        'active': int,
        'acknowledged': int,
        'by_type': dict,
        'by_severity': dict
    }
}
```

#### `reset_statistics()`

Reset statistics counters.

---

### Data Models

#### `OptionsTrade`

Core options trade data model.

**Attributes:**
- `trade_id` (str): Unique trade identifier
- `symbol` (str): Option symbol (OSI format)
- `underlying_symbol` (str): Underlying ticker
- `order_type` (OrderType): CALL or PUT
- `strike` (Decimal): Strike price
- `expiration` (datetime): Expiration date
- `premium` (Decimal): Premium per contract
- `size` (int): Number of contracts
- `price` (Decimal): Execution price
- `timestamp` (datetime): Trade timestamp
- `trade_type` (TradeType): Trade classification
- `exchange` (str): Execution exchange
- `execution_side` (str): "bid", "ask", "mid"
- `is_aggressive` (bool): Aggressive execution flag
- `is_opening` (bool): Opening position flag
- `sentiment` (str): "bullish", "bearish", "neutral"
- `underlying_price` (Decimal, optional): Current underlying price
- `open_interest` (int, optional): Open interest
- `implied_volatility` (Decimal, optional): IV

**Properties:**
- `notional_value`: Total premium value
- `is_itm`: In-the-money flag
- `moneyness`: Moneyness ratio
- `days_to_expiration()`: Days to expiration

#### `FlowPattern`

Detected flow pattern.

**Attributes:**
- `pattern_id` (str): Unique pattern ID
- `pattern_type` (PatternType): Pattern classification
- `symbol` (str): Option symbol
- `underlying_symbol` (str): Underlying ticker
- `detected_at` (datetime): Detection timestamp
- `total_premium` (Decimal): Total premium
- `total_contracts` (int): Total contracts
- `trade_count` (int): Number of trades
- `signal` (SmartMoneySignal): Signal strength
- `confidence_score` (float): Confidence (0-1)
- `call_premium` (Decimal): Call premium
- `put_premium` (Decimal): Put premium

**Properties:**
- `net_sentiment`: Overall sentiment
- `is_significant`: Significance flag

#### `MarketMakerPosition`

Market maker positioning estimate.

**Attributes:**
- `symbol` (str): Symbol
- `calculated_at` (datetime): Calculation time
- `net_delta` (Decimal): Net delta
- `net_gamma` (Decimal): Net gamma
- `net_vega` (Decimal): Net vega
- `net_theta` (Decimal): Net theta
- `position_bias` (PositionBias): Position bias
- `hedge_pressure` (str): Hedge direction
- `call_volume` (int): Call volume
- `put_volume` (int): Put volume
- `call_open_interest` (int): Call OI
- `put_open_interest` (int): Put OI
- `max_pain_price` (Decimal, optional): Max pain
- `gamma_strike` (Decimal, optional): Max gamma strike

**Properties:**
- `put_call_volume_ratio`: P/C volume ratio
- `put_call_oi_ratio`: P/C OI ratio
- `is_gamma_squeeze_risk`: Gamma squeeze risk

#### `UnusualActivityAlert`

Unusual activity alert.

**Attributes:**
- `alert_id` (str): Unique alert ID
- `alert_type` (AlertType): Alert classification
- `severity` (AlertSeverity): Severity level
- `symbol` (str): Option symbol
- `underlying_symbol` (str): Underlying ticker
- `created_at` (datetime): Creation time
- `title` (str): Alert title
- `description` (str): Alert description
- `total_premium` (Decimal, optional): Total premium
- `total_contracts` (int, optional): Total contracts
- `confidence_score` (float): Confidence (0-1)
- `is_active` (bool): Active status
- `is_acknowledged` (bool): Acknowledged status

**Properties:**
- `age_seconds`: Alert age in seconds
- `priority_score`: Priority score for routing

**Methods:**
- `acknowledge(user)`: Acknowledge alert
- `deactivate()`: Deactivate alert

---

### Enumerations

#### `OrderType`
- `CALL`: Call option
- `PUT`: Put option

#### `TradeType`
- `SWEEP`: Multi-exchange sweep
- `BLOCK`: Block trade
- `DARK_POOL`: Dark pool print
- `REGULAR`: Regular trade
- `SPLIT`: Split execution

#### `PatternType`
- `AGGRESSIVE_CALL_BUYING`: Aggressive call buying
- `AGGRESSIVE_PUT_BUYING`: Aggressive put buying
- `LARGE_SWEEP`: Large sweep pattern
- `BLOCK_TRADE`: Block trade pattern
- `DARK_POOL_PRINT`: Dark pool pattern
- `SPREAD_PATTERN`: Spread pattern
- `STRADDLE`: Straddle pattern
- `STRANGLE`: Strangle pattern
- `UNUSUAL_VOLUME`: Unusual volume
- `INSTITUTIONAL_FLOW`: Institutional flow

#### `SmartMoneySignal`
- `STRONG_BULLISH`: Strong bullish signal
- `BULLISH`: Bullish signal
- `NEUTRAL`: Neutral signal
- `BEARISH`: Bearish signal
- `STRONG_BEARISH`: Strong bearish signal

#### `PositionBias`
- `LONG_GAMMA`: Long gamma position
- `SHORT_GAMMA`: Short gamma position
- `NEUTRAL`: Neutral position
- `DELTA_HEDGING`: Delta hedging

#### `AlertSeverity`
- `CRITICAL`: Critical severity
- `HIGH`: High severity
- `MEDIUM`: Medium severity
- `LOW`: Low severity
- `INFO`: Informational

#### `AlertType`
- `UNUSUAL_SWEEP`: Unusual sweep
- `LARGE_BLOCK`: Large block
- `DARK_POOL_PRINT`: Dark pool print
- `SMART_MONEY_FLOW`: Smart money flow
- `INSTITUTIONAL_PATTERN`: Institutional pattern
- `GAMMA_SQUEEZE`: Gamma squeeze
- `VOLUME_SPIKE`: Volume spike
- `SPREAD_PATTERN`: Spread pattern
- `UNUSUAL_IV`: Unusual IV
