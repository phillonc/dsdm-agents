# User Guide - Options Flow Intelligence

## Getting Started

### Installation

```bash
# Navigate to project directory
cd optix_trading_platform

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from src.options_flow_intelligence import OptionsFlowIntelligence; print('Success!')"
```

### Basic Usage

```python
from src.options_flow_intelligence import OptionsFlowIntelligence

# Initialize the engine
engine = OptionsFlowIntelligence(enable_alerts=True)

# Process a trade
from src.models import OptionsTrade, OrderType, TradeType
from datetime import datetime
from decimal import Decimal

trade = OptionsTrade(
    trade_id="TRADE001",
    symbol="AAPL250117C00150000",
    underlying_symbol="AAPL",
    order_type=OrderType.CALL,
    strike=Decimal('150.00'),
    expiration=datetime(2025, 1, 17),
    premium=Decimal('5.50'),
    size=100,
    price=Decimal('150.50'),
    timestamp=datetime.now(),
    trade_type=TradeType.REGULAR,
    exchange="CBOE",
    execution_side="ask",
    is_aggressive=True,
)

# Process the trade
result = engine.process_trade(trade)
print(result)
```

## Understanding Trade Detection

### What is a Sweep?

An options sweep is when a large order is split and executed across multiple exchanges simultaneously to ensure fill at the best available prices.

**Example:**
```
Buyer wants 400 AAPL $150 calls
- 100 contracts filled on CBOE at $5.50
- 100 contracts filled on PHLX at $5.51
- 100 contracts filled on ISE at $5.52
- 100 contracts filled on AMEX at $5.53

All executed within 1-2 seconds = SWEEP DETECTED
```

**Why It Matters:**
Sweeps indicate urgency and strong directional conviction. The buyer is willing to pay through multiple price levels to get filled immediately.

### What is a Block Trade?

A block trade is a large single order, typically negotiated and executed as one piece.

**Characteristics:**
- Large size (100+ contracts minimum, often 500+)
- Often executed at mid-market
- Typically done by institutions
- May be marked as "opening" position

**Example:**
```
500 TSLA $200 calls
- Executed as single fill
- At mid-market price
- $625,000 premium
- Opening position

= BLOCK TRADE DETECTED
```

**Why It Matters:**
Blocks represent significant institutional positioning and often precede major price moves.

### What is a Dark Pool Print?

Dark pool trades are executed off-exchange or reported with a delay, often to minimize market impact.

**Characteristics:**
- Executed on dark pool venues (EDGX, BATS, etc.)
- May show 30+ second reporting delay
- Passive execution (not hitting bid/ask)
- Often large size

**Example:**
```
300 NVDA $500 puts
- Executed on EDGX
- 45 second delay before print
- Mid-market fill
- $262,500 premium

= DARK POOL PRINT DETECTED
```

**Why It Matters:**
Dark pools are used by institutions to hide large orders from the market. Detection provides insight into "hidden" institutional activity.

## Flow Pattern Recognition

### Aggressive Buying Pattern

**What to Look For:**
- Series of aggressive buys (hitting ask)
- Same strike and expiration
- Increasing or consistent size
- Short time window (5 minutes)

**Trading Implication:**
- Strong bullish (calls) or bearish (puts) signal
- Buyer showing urgency
- Often precedes price movement

### Institutional Flow Pattern

**What to Look For:**
- Multiple large trades ($250K+ each)
- Strategic strike selection
- Opening positions
- Directional bias

**Trading Implication:**
- Smart money positioning
- High-conviction trade
- Follow institutional direction

### Spread Patterns

**What to Look For:**
- Simultaneous trades at different strikes
- Same expiration and type
- Executed within seconds

**Common Spreads:**
- **Vertical Spread:** Buy $150 call, sell $155 call
- **Calendar Spread:** Buy March $150 call, sell February $150 call
- **Diagonal:** Different strikes AND dates

**Trading Implication:**
- Defined risk strategy
- Directional with limited risk
- Often used by sophisticated traders

## Market Maker Analysis

### Understanding Greeks

**Delta:** Directional exposure
- Call delta: 0 to 1.0
- Put delta: -1.0 to 0
- Example: 0.5 delta = $0.50 move per $1 stock move

**Gamma:** Rate of delta change
- Highest for ATM options
- Increases as expiration approaches
- "Convexity" of position

**Vega:** Volatility sensitivity
- Measures IV change impact
- ~$0.20 per 1% IV change
- Higher for longer-dated options

**Theta:** Time decay
- Daily loss from time passage
- Accelerates near expiration
- Negative for option buyers

### Position Bias

**Short Gamma (Most Common):**
- Market makers sold options
- Must hedge in direction of move
- Buying pressure on rallies
- Selling pressure on dips
- Can fuel momentum moves

**Long Gamma:**
- Market makers bought options
- Hedge opposite to move
- Dampens volatility
- Provides liquidity

### Gamma Squeeze

**What It Is:**
Market makers with large short gamma positions must aggressively hedge as price moves, amplifying the move.

**Detection:**
```python
position = engine.calculate_market_maker_position("GME")

if position.is_gamma_squeeze_risk:
    print("⚠️ Gamma Squeeze Risk!")
    print(f"Net Gamma: {position.net_gamma}")
    print(f"Hedge Pressure: {position.hedge_pressure}")
```

**Famous Examples:**
- GME January 2021
- AMC June 2021
- Various meme stocks

## Practical Trading Strategies

### Strategy 1: Follow the Sweeps

**Setup:**
1. Subscribe to sweep alerts
2. Filter for high confidence (>80%)
3. Focus on liquid underlyings

**Execution:**
```python
def sweep_alert(alert):
    if alert.confidence_score > 0.8:
        # Check direction
        # Verify with technical analysis
        # Consider same-day expiration for speed
        pass

engine.subscribe_to_alerts(sweep_alert, alert_type='sweep')
```

**Risk Management:**
- Use stop losses
- Size appropriately
- Don't chase if already moved

### Strategy 2: Block Trade Following

**Setup:**
1. Monitor for large blocks
2. Verify institutional characteristics
3. Check positioning (opening vs closing)

**Execution:**
```python
# Get institutional flow
flow = engine.get_institutional_flow()

# Find largest positions
for symbol_data in flow['symbols'][:5]:
    if symbol_data['sentiment'] == 'very_bullish':
        # Investigate further
        # Look at strikes and expirations
        pass
```

### Strategy 3: Market Maker Pressure

**Setup:**
1. Calculate MM positioning
2. Identify short gamma situations
3. Look for hedge pressure

**Execution:**
```python
position = engine.calculate_market_maker_position("AAPL")

if position.hedge_pressure == "buy":
    # MMs need to buy on rallies
    # Can fuel upward movement
    # Consider calls near gamma strike
    pass
```

### Strategy 4: Dark Pool Detection

**Setup:**
1. Monitor dark pool activity
2. Track volume by symbol
3. Note institutional accumulation

**Execution:**
```python
# Get flow by strike
flow = engine.get_flow_by_strike("AAPL")

# Look for concentration at specific strikes
for strike_data in flow['strikes']:
    if strike_data['call_volume'] > 5000:
        # Large call accumulation
        # Potential support level
        pass
```

## Alert Configuration

### Setting Up Alerts

**Console Alerts (Default):**
```python
engine = OptionsFlowIntelligence(enable_alerts=True)
# Alerts print to console automatically
```

**Webhook Alerts:**
```python
engine.add_alert_webhook("https://your-server.com/webhook")
```

**Custom Handlers:**
```python
def telegram_alert(alert):
    # Send to Telegram
    pass

def email_alert(alert):
    # Send email
    pass

engine.alert_dispatcher.add_custom_handler('telegram', telegram_alert)
engine.alert_dispatcher.add_custom_handler('email', email_alert)
```

### Filtering Alerts

**By Severity:**
```python
# Only get high priority alerts
alerts = engine.get_active_alerts(min_severity='high')
```

**By Symbol:**
```python
# Only AAPL alerts
alerts = engine.get_active_alerts(symbol='AAPL')
```

**By Type:**
```python
def my_callback(alert):
    print(f"Sweep detected: {alert.title}")

# Only sweep alerts
engine.subscribe_to_alerts(my_callback, alert_type='sweep')
```

## Best Practices

### 1. Data Quality

**Ensure Clean Data:**
- Validate all fields
- Use correct data types (Decimal for prices)
- Provide underlying price when available
- Include open interest for better analysis

### 2. Processing Speed

**Optimize for Real-Time:**
- Process trades as they arrive
- Don't batch excessively
- Keep lookback windows reasonable
- Clear old data regularly

### 3. Alert Management

**Avoid Alert Fatigue:**
- Set appropriate thresholds
- Filter by confidence
- Acknowledge processed alerts
- Focus on high-severity events

### 4. Statistical Significance

**Require Evidence:**
- Wait for pattern confirmation
- Don't trade single alerts
- Look for multiple signals
- Verify with other analysis

## Troubleshooting

### No Sweeps Detected

**Possible Causes:**
- Thresholds too strict
- Not enough exchanges in data
- Time window too short
- Trades not marked aggressive

**Solutions:**
```python
# Relax detector settings
detector = SweepDetector(
    min_legs=3,  # Lower from 4
    max_time_window_seconds=3.0  # Wider window
)
```

### Memory Usage Growing

**Cause:** Buffers not cleaning up

**Solution:**
```python
# Reduce buffer sizes
engine = OptionsFlowIntelligence(enable_alerts=True)
engine.flow_analyzer.analysis_window = timedelta(minutes=10)  # Reduce from 15
```

### Too Many Alerts

**Cause:** Thresholds too low

**Solution:**
```python
# Increase minimum premiums
engine.block_detector.min_premium = Decimal('200000')  # Up from 100K
engine.dark_pool_detector.min_premium = Decimal('100000')  # Up from 50K
```

## Advanced Usage

### Custom Pattern Detection

```python
# Extend FlowAnalyzer
class CustomFlowAnalyzer(FlowAnalyzer):
    def detect_custom_pattern(self, trade):
        # Your logic here
        pass
```

### Performance Monitoring

```python
import time

start = time.time()
result = engine.process_trade(trade)
elapsed = time.time() - start

print(f"Processing time: {elapsed*1000:.2f}ms")

# Get statistics
stats = engine.get_statistics()
print(f"Total processed: {stats['engine']['trades_processed']}")
```

### Backtesting Framework

```python
# Load historical trades
historical_trades = load_trades_from_csv("history.csv")

# Process through engine
for trade in historical_trades:
    result = engine.process_trade(trade)
    # Log results
    # Track performance

# Analyze results
stats = engine.get_statistics()
print(f"Sweeps detected: {stats['engine']['sweeps_detected']}")
```

## Support and Resources

### Documentation
- API Reference: `docs/API_REFERENCE.md`
- Architecture: `docs/ARCHITECTURE.md`
- Technical Requirements: `docs/TECHNICAL_REQUIREMENTS.md`

### Examples
- Basic Usage: `examples/usage_example.py`
- Test Suite: `tests/`

### Getting Help
- GitHub Issues
- Documentation Wiki
- Community Forum
