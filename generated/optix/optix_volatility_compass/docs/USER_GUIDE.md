# Volatility Compass User Guide

## Overview

The Volatility Compass is a comprehensive implied volatility analytics feature for the OPTIX Trading Platform. It provides traders with deep insights into option volatility to make informed trading decisions.

## Key Features

### 1. IV Rank and IV Percentile

**IV Rank** tells you where current IV stands relative to its 52-week range:
- **0-20**: Extremely low volatility - consider buying premium
- **20-40**: Low volatility - potential premium buying opportunities
- **40-60**: Normal volatility - neutral strategies
- **60-80**: High volatility - potential premium selling opportunities
- **80-100**: Extremely high volatility - strong premium selling opportunities

**IV Percentile** shows the percentage of days IV was below the current level:
- More robust measure than IV Rank
- Less affected by extreme outliers
- Used in conjunction with IV Rank for confirmation

### 2. Volatility Skew Analysis

The volatility skew shows how IV varies across strike prices:

**Normal Skew** (most common):
- OTM puts have higher IV than OTM calls
- Reflects market's fear of downside moves
- Opportunity: Sell put spreads

**Reverse Skew** (unusual):
- OTM calls have higher IV than OTM puts
- Often seen in commodities or takeover targets
- Opportunity: Sell call spreads

**Volatility Smile**:
- Both OTM puts and calls have elevated IV
- Often before major events
- Opportunity: Sell iron condors

### 3. Term Structure Analysis

Term structure shows how IV changes across different expirations:

**Contango** (normal):
- Back-month IV higher than front-month
- Standard volatility term structure
- Strategy: Regular premium selling

**Backwardation**:
- Front-month IV higher than back-month
- Often indicates near-term event or uncertainty
- Strategy: Sell front-month premium or calendar spreads

### 4. Historical Volatility (HV) Comparison

Compare implied volatility to realized volatility:

**IV/HV Ratio**:
- **> 1.3**: Options are expensive relative to realized moves
- **0.8 - 1.3**: Options fairly priced
- **< 0.8**: Options are cheap relative to realized moves

### 5. Volatility Surface (3D Visualization)

The volatility surface provides a comprehensive view of IV across:
- Strike prices (moneyness)
- Time to expiration
- Helps identify arbitrage opportunities and market inefficiencies

## Quick Start Guide

### Basic Usage

```python
from src.api import VolatilityCompassAPI

# Initialize the API
api = VolatilityCompassAPI()

# Get quick IV metrics (no options chain required)
metrics = api.get_iv_metrics(
    symbol="AAPL",
    current_iv=30.5,
    iv_history=[30.5, 29.8, 31.2, ...],  # 252 days recommended
    price_history=[150.25, 149.80, ...]  # 100+ days recommended
)

print(f"IV Rank: {metrics['iv_rank']:.1f}%")
print(f"IV Percentile: {metrics['iv_percentile']:.1f}%")
print(f"Condition: {metrics['condition']}")
```

### Get Trading Strategies

```python
# Get strategy recommendations
strategies = api.get_trading_strategies(
    symbol="AAPL",
    current_iv=35.0,
    iv_history=iv_history,
    price_history=price_history,
    options_chain=options_chain  # Optional for enhanced analysis
)

# Display primary strategy
primary = strategies[0]
print(f"Strategy: {primary['name']}")
print(f"Confidence: {primary['confidence']:.0f}%")
print("Actions:")
for action in primary['suggested_actions']:
    print(f"  - {action}")
```

### Analyze a Watchlist

```python
# Prepare data for multiple symbols
symbols_data = {
    'AAPL': {
        'current_iv': 30.0,
        'iv_history': [...],
        'price_history': [...],
        'previous_iv': 28.5
    },
    'MSFT': {
        'current_iv': 35.0,
        'iv_history': [...],
        'price_history': [...],
        'previous_iv': 34.0
    },
    # ... more symbols
}

# Analyze watchlist
analysis = api.analyze_watchlist("Tech Stocks", symbols_data)

# View opportunities
print(f"Average IV Rank: {analysis['summary']['average_iv_rank']:.1f}%")
print("\nPremium Selling Opportunities:")
for opp in analysis['opportunities']['premium_selling'][:5]:
    print(f"  {opp['symbol']}: IV Rank {opp['iv_rank']:.1f}%")
```

### Check for Alerts

```python
# Get volatility alerts
alerts = api.get_volatility_alerts(
    symbol="AAPL",
    current_iv=36.0,
    iv_history=iv_history,
    price_history=price_history,
    previous_iv=30.0  # For spike/crush detection
)

# Display alerts
for alert in alerts:
    print(f"[{alert['severity'].upper()}] {alert['message']}")
```

## Trading Strategy Guidelines

### When IV Rank > 70 (High Volatility)

**Primary Strategy: SELL PREMIUM**

Recommended trades:
1. **Naked Puts** - On quality stocks with support levels
2. **Covered Calls** - On existing positions
3. **Credit Spreads** - Bull put spreads, bear call spreads
4. **Iron Condors** - For range-bound expectations
5. **Short Strangles** - For advanced traders

**Risk Management**:
- Define maximum loss per trade
- Use technical support/resistance for strike selection
- Consider position sizing based on IV rank level
- Monitor for upcoming earnings or events

### When IV Rank < 30 (Low Volatility)

**Primary Strategy: BUY PREMIUM**

Recommended trades:
1. **Long Calls/Puts** - Directional plays with cheap premium
2. **Debit Spreads** - Defined risk directional trades
3. **Calendar Spreads** - Benefit from IV expansion
4. **Long Straddles** - Before expected volatility events
5. **Protective Puts** - Portfolio insurance

**Risk Management**:
- Buy options with sufficient time value (60+ DTE)
- Look for catalysts that could increase volatility
- Consider buying on pullbacks
- Don't fight the trend for direction

### When IV Rank 30-70 (Neutral)

**Primary Strategy: DIRECTIONAL or BALANCED**

Focus on:
1. Technical analysis for direction
2. Defined risk strategies (spreads)
3. Smaller position sizes
4. Wait for clearer volatility signals

## Advanced Features

### Volatility Skew Analysis

```python
# Get detailed skew analysis
skew_analyses = api.get_skew_analysis("AAPL", options_chain)

# Analyze primary expiration
skew = skew_analyses[0]
print(f"Skew Type: {skew['skew_type']}")
print(f"Put/Call Ratio: {skew['put_call_ratio']:.2f}")

# Visualization data available in:
# skew['visualization_data']['call_strikes']
# skew['visualization_data']['call_ivs']
# skew['visualization_data']['put_strikes']
# skew['visualization_data']['put_ivs']
```

### Term Structure Analysis

```python
# Get term structure
term_structure = api.get_term_structure("AAPL", 150.0, options_chain)

print(f"Structure Shape: {term_structure['structure_shape']}")
print(f"Front Month IV: {term_structure['front_month_iv']:.1f}%")
print(f"Back Month IV: {term_structure['back_month_iv']:.1f}%")

# Term points for visualization
for point in term_structure['term_points']:
    print(f"{point['days_to_expiration']} DTE: {point['atm_iv']:.1f}% IV")
```

### 3D Volatility Surface

```python
# Get surface data
surface = api.get_volatility_surface("AAPL", 150.0, options_chain)

print(f"Surface Curvature: {surface['curvature']:.4f}")
print(f"Strike Range: {surface['strike_range']['min']} - {surface['strike_range']['max']}")

# Surface points available for 3D plotting
for point in surface['surface_points']:
    strike = point['strike']
    dte = point['days_to_expiration']
    iv = point['implied_volatility']
    # Use for 3D visualization
```

## Alert System

The Volatility Compass monitors for:

1. **IV Spikes** - Rapid IV increases (>20% default)
2. **IV Crushes** - Rapid IV decreases (>20% default)
3. **IV Rank Thresholds** - Crossing 80% or 20% levels
4. **IV/HV Divergence** - When IV significantly exceeds HV
5. **Historical Extremes** - Near 52-week highs or lows

Configure alert thresholds:
```python
api.compass.alert_engine.update_thresholds({
    'iv_spike_percent': 25.0,  # Increase spike threshold
    'iv_rank_high': 75.0,      # Custom high IV threshold
})
```

## Best Practices

### 1. Data Quality
- Use at least 252 days of IV history for accurate IV Rank
- Ensure price history is clean and adjusted for splits
- Verify options chain data is current

### 2. Multiple Confirmations
- Don't rely on IV Rank alone
- Check IV Percentile for confirmation
- Consider term structure and skew
- Look at historical context

### 3. Risk Management
- Size positions based on IV level
- Use defined-risk strategies when appropriate
- Monitor for upcoming events
- Set profit targets and stop losses

### 4. Regular Monitoring
- Check volatility metrics daily
- Review watchlist for new opportunities
- Respond to alerts promptly
- Track strategy performance

## Interpreting Results

### High Confidence Strategies (>80%)
- Strong volatility signal
- Multiple confirming indicators
- Clear opportunity for edge
- Consider increasing position size (within risk limits)

### Medium Confidence Strategies (60-80%)
- Decent volatility signal
- Some confirming factors
- Normal position sizing
- Monitor closely

### Low Confidence Strategies (<60%)
- Weak or mixed signals
- Consider waiting for better setup
- Reduce position size if trading
- Focus on risk management

## Common Questions

**Q: How often should I check volatility metrics?**
A: Daily for active positions, weekly for watchlist monitoring.

**Q: Can I use this for day trading?**
A: Volatility Compass is optimized for swing and position trading (multi-day to weeks).

**Q: What if IV Rank and IV Percentile disagree?**
A: Use IV Percentile as the tiebreaker - it's more robust against outliers.

**Q: Should I trade every high/low IV signal?**
A: No. Consider overall market conditions, stock fundamentals, and technical setup.

**Q: How do I handle earnings events?**
A: IV typically spikes before earnings and crushes after. Consider this in timing.

## Support and Resources

- Technical Documentation: See `TECHNICAL_REQUIREMENTS.md`
- API Reference: See `docs/api/`
- Code Examples: See `examples/`
- Issue Reporting: Contact development team

## Version History

- v1.0.0 - Initial release with comprehensive IV analytics
- Full feature set including IV Rank, Percentile, Skew, Term Structure, Surface
- Strategy engine with confidence scoring
- Real-time alert system
- Watchlist bulk analysis
