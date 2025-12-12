# Quick Start Guide - Volatility Compass

Get up and running with the Volatility Compass in 5 minutes!

## Installation

```bash
# Navigate to project directory
cd optix_volatility_compass

# Install dependencies
pip install -r requirements.txt
```

## Verify Installation

```bash
# Run tests to verify everything works
pytest

# Or use the test runner script
chmod +x run_tests.sh
./run_tests.sh
```

## Basic Usage - 3 Examples

### Example 1: Quick IV Metrics (No Options Chain Needed)

```python
from src import VolatilityCompassAPI

# Initialize API
api = VolatilityCompassAPI()

# Prepare your data
symbol = "AAPL"
current_iv = 30.5  # Current implied volatility %
iv_history = [30.5, 29.8, 31.2, ...]  # 252 days recommended
price_history = [150.25, 149.80, ...]  # 100+ days recommended

# Get metrics
metrics = api.get_iv_metrics(symbol, current_iv, iv_history, price_history)

# Display results
print(f"Symbol: {metrics['symbol']}")
print(f"IV Rank: {metrics['iv_rank']:.1f}%")
print(f"IV Percentile: {metrics['iv_percentile']:.1f}%")
print(f"Condition: {metrics['condition']}")
print(f"IV/HV Ratio: {metrics['iv_hv_ratio']:.2f}")

# Quick recommendation
recommendation = api.get_quick_recommendation(metrics['iv_rank'])
print(f"\nRecommendation: {recommendation}")
```

### Example 2: Get Trading Strategies

```python
from src import VolatilityCompassAPI

api = VolatilityCompassAPI()

# Get strategy recommendations
strategies = api.get_trading_strategies(
    symbol="AAPL",
    current_iv=35.0,
    iv_history=iv_history,
    price_history=price_history
)

# Display primary strategy
primary = strategies[0]
print(f"\nStrategy: {primary['name']}")
print(f"Confidence: {primary['confidence']:.0f}%")
print(f"Risk Level: {primary['risk_level']}")
print("\nSuggested Actions:")
for action in primary['suggested_actions'][:3]:
    print(f"  • {action}")
```

### Example 3: Analyze a Watchlist

```python
from src import VolatilityCompassAPI

api = VolatilityCompassAPI()

# Prepare data for multiple symbols
symbols_data = {
    'AAPL': {
        'current_iv': 30.0,
        'iv_history': [...],  # Your IV history
        'price_history': [...],  # Your price history
        'previous_iv': 28.5
    },
    'MSFT': {
        'current_iv': 35.0,
        'iv_history': [...],
        'price_history': [...],
        'previous_iv': 34.0
    },
    # Add more symbols...
}

# Analyze watchlist
analysis = api.analyze_watchlist("Tech Stocks", symbols_data)

# Display opportunities
print(f"\nWatchlist: {analysis['watchlist_name']}")
print(f"Average IV Rank: {analysis['summary']['average_iv_rank']:.1f}%")

print("\n📈 Premium Selling Opportunities:")
for opp in analysis['opportunities']['premium_selling'][:5]:
    print(f"  {opp['symbol']}: IV Rank {opp['iv_rank']:.1f}%")

print("\n📉 Premium Buying Opportunities:")
for opp in analysis['opportunities']['premium_buying'][:5]:
    print(f"  {opp['symbol']}: IV Rank {opp['iv_rank']:.1f}%")
```

## Run Complete Examples

```bash
# Run the comprehensive example script
python examples/basic_usage.py
```

This will show you 6 different usage scenarios with sample data.

## Understanding the Output

### IV Rank
- **0-20**: Extremely low volatility → Consider buying premium
- **20-40**: Low volatility → Potential buying opportunities
- **40-60**: Normal volatility → Neutral strategies
- **60-80**: High volatility → Potential selling opportunities
- **80-100**: Extremely high volatility → Strong selling opportunities

### IV Percentile
Similar to IV Rank but more robust against outliers. Use both metrics together for confirmation.

### IV/HV Ratio
- **> 1.3**: Options are expensive relative to realized volatility
- **0.8 - 1.3**: Options are fairly priced
- **< 0.8**: Options are cheap relative to realized volatility

## Common Use Cases

### Use Case 1: Daily Opportunity Scanner

```python
# Scan your watchlist daily for opportunities
analysis = api.analyze_watchlist("My Watchlist", symbols_data)

# Focus on highest IV rank for selling premium
sellers = analysis['opportunities']['premium_selling'][:5]

# Focus on lowest IV rank for buying premium
buyers = analysis['opportunities']['premium_buying'][:5]
```

### Use Case 2: Pre-Trade Analysis

```python
# Before trading, check comprehensive analysis
report = api.get_volatility_analysis(
    symbol="AAPL",
    current_iv=current_iv,
    iv_history=iv_history,
    price_history=price_history,
    options_chain=options_chain
)

# Review metrics, strategies, and alerts
print(f"IV Rank: {report['metrics']['iv_rank']:.1f}%")
print(f"Primary Strategy: {report['strategies'][0]['name']}")
if report['alerts']:
    print(f"Alerts: {len(report['alerts'])}")
```

### Use Case 3: Alert Monitoring

```python
# Check for volatility alerts
alerts = api.get_volatility_alerts(
    symbol="AAPL",
    current_iv=current_iv,
    iv_history=iv_history,
    price_history=price_history,
    previous_iv=previous_iv
)

# Process alerts
for alert in alerts:
    if alert['severity'] in ['high', 'critical']:
        print(f"⚠️ {alert['message']}")
```

## Data Format Requirements

### IV History
- List of float values (implied volatility as percentage)
- Most recent value first
- Recommended: 252 trading days (1 year)
- Minimum: 30 days

### Price History
- List of float values (closing prices)
- Most recent value first
- Recommended: 100+ days
- Minimum: 30 days

### Options Chain (Optional, for enhanced analysis)
```python
options_chain = {
    'expirations': [
        {
            'expiration_date': datetime(...),
            'days_to_expiration': 30,
            'atm_strike': 150.0,
            'atm_iv': 30.0,
            'calls': [
                {'strike': 155, 'iv': 28.0, 'delta': 0.35},
                # ... more calls
            ],
            'puts': [
                {'strike': 145, 'iv': 33.0, 'delta': -0.65},
                # ... more puts
            ]
        },
        # ... more expirations
    ]
}
```

## Next Steps

1. **Read the User Guide**: `docs/USER_GUIDE.md` for comprehensive documentation
2. **Review Examples**: `examples/basic_usage.py` for more detailed examples
3. **Explore API**: `docs/TECHNICAL_REQUIREMENTS.md` for complete API reference
4. **Run Tests**: Verify everything with `pytest`

## Troubleshooting

### Import Error
```python
# Make sure you're in the project directory and have installed dependencies
pip install -r requirements.txt
```

### Insufficient Data
```python
# Need at least 30 days of history
# For best results, provide 252 days (1 year)
if len(iv_history) < 30:
    print("Warning: Need more data for accurate calculations")
```

### Division by Zero / NaN Results
```python
# System handles edge cases gracefully
# Returns sensible defaults for edge cases
# Check your input data for zeros or invalid values
```

## Support

- **Documentation**: See `docs/` folder
- **Examples**: See `examples/` folder
- **Tests**: See `tests/` folder for usage patterns
- **Issues**: Contact OPTIX development team

## Performance Tips

1. **Cache IV History**: Don't recalculate every time
2. **Batch Watchlists**: Process multiple symbols in one call
3. **Skip Options Chain**: Use `get_iv_metrics()` for faster results
4. **Async Processing**: Process watchlists asynchronously if needed

---

**You're ready to start using the Volatility Compass!** 🎯

For more advanced usage, explore the comprehensive examples and documentation.
