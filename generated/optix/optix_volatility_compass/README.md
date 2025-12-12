# Volatility Compass - VS-8

## Overview

The **Volatility Compass** is a comprehensive implied volatility analytics feature for the OPTIX Trading Platform. It provides professional-grade volatility analysis tools to help options traders make informed decisions about premium buying and selling opportunities.

## Features

### Core Volatility Metrics
- **IV Rank**: Where current IV stands in its 52-week range (0-100%)
- **IV Percentile**: Percentage of days IV was below current level
- **Historical Volatility Comparison**: IV vs HV across 30/60/90-day windows
- **IV/HV Ratio**: Measure of option pricing relative to realized volatility
- **Volatility Condition Classification**: Automated assessment (extremely low to extremely high)

### Advanced Analytics
- **Volatility Skew Analysis**: Put vs call skew visualization across strikes
- **Term Structure Analysis**: IV patterns across different expirations (contango/backwardation)
- **3D Volatility Surface**: Complete IV surface across strikes and expirations
- **Surface Curvature Metrics**: Quantitative measures of skew and smile patterns

### Strategy Engine
- **Automated Strategy Recommendations**: Based on IV conditions
- **Confidence Scoring**: Quantitative confidence levels for each strategy
- **Multi-Factor Analysis**: Considers IV rank, skew, and term structure
- **Risk Level Assessment**: Clear risk categorization for each strategy
- **Actionable Suggestions**: Specific trade ideas and implementations

### Alert System
- **IV Spike Detection**: Alerts on rapid IV increases (>20% default)
- **IV Crush Detection**: Alerts on rapid IV decreases (>20% default)
- **Threshold Alerts**: Notifications when IV rank crosses key levels
- **IV/HV Divergence**: Alerts when options become significantly overpriced
- **Historical Extremes**: Notifications near 52-week highs/lows
- **Configurable Thresholds**: Customize alert sensitivity

### Watchlist Analysis
- **Bulk Symbol Analysis**: Analyze entire watchlists simultaneously
- **Opportunity Identification**: Auto-identify premium selling/buying candidates
- **Aggregate Statistics**: Portfolio-level IV metrics
- **Comparative Analysis**: Rank symbols by IV opportunities
- **Alert Aggregation**: View all watchlist alerts in one place

## Installation

```bash
# Clone or download the project
cd optix_volatility_compass

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Quick Start

```python
from src.api import VolatilityCompassAPI

# Initialize
api = VolatilityCompassAPI()

# Get IV metrics (fast - no options chain needed)
metrics = api.get_iv_metrics(
    symbol="AAPL",
    current_iv=30.5,
    iv_history=[...],  # 252 days of IV data
    price_history=[...]  # 100+ days of prices
)

print(f"IV Rank: {metrics['iv_rank']:.1f}%")
print(f"Recommendation: {api.get_quick_recommendation(metrics['iv_rank'])}")

# Get trading strategies
strategies = api.get_trading_strategies(
    symbol="AAPL",
    current_iv=35.0,
    iv_history=iv_history,
    price_history=price_history,
    options_chain=options_chain  # Optional
)

for strategy in strategies:
    print(f"{strategy['name']}: {strategy['confidence']:.0f}% confidence")
    for action in strategy['suggested_actions'][:3]:
        print(f"  - {action}")
```

## Usage Examples

See `examples/basic_usage.py` for comprehensive examples including:
1. Quick IV metrics
2. Trading strategy recommendations
3. Watchlist analysis
4. Volatility alerts
5. Skew and term structure analysis
6. Complete analysis reports

Run examples:
```bash
python examples/basic_usage.py
```

## Project Structure

```
optix_volatility_compass/
├── src/
│   ├── models.py              # Data models and enums
│   ├── calculators.py         # Core calculation engines
│   ├── strategy_engine.py     # Strategy recommendation engine
│   ├── alert_engine.py        # Alert detection and management
│   ├── volatility_compass.py  # Main orchestrator
│   └── api.py                 # High-level API interface
├── tests/
│   ├── unit/                  # Unit tests (>85% coverage)
│   │   ├── test_calculators.py
│   │   ├── test_strategy_engine.py
│   │   ├── test_alert_engine.py
│   │   └── test_volatility_compass.py
│   └── integration/           # Integration tests
│       └── test_api_integration.py
├── examples/
│   └── basic_usage.py         # Usage examples
├── docs/
│   ├── USER_GUIDE.md          # Comprehensive user guide
│   ├── TECHNICAL_REQUIREMENTS.md  # Technical specifications
│   └── api/                   # API documentation
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
└── README.md                  # This file
```

## API Reference

### Quick Methods

**`get_iv_metrics(symbol, current_iv, iv_history, price_history)`**
- Fast metrics retrieval without options chain
- Returns: IV Rank, Percentile, HV comparison, condition

**`get_quick_recommendation(iv_rank)`**
- One-line trading recommendation
- Returns: String with emoji indicator and action

**`get_trading_strategies(...)`**
- Strategy recommendations with confidence scores
- Returns: List of strategies sorted by confidence

### Analysis Methods

**`get_volatility_analysis(...)`**
- Complete comprehensive analysis
- Returns: Full report with all metrics, strategies, alerts

**`analyze_watchlist(watchlist_name, symbols_data)`**
- Bulk analysis for multiple symbols
- Returns: Aggregated analysis with opportunities

**`get_volatility_alerts(...)`**
- Check for volatility alerts
- Returns: List of triggered alerts

### Specialized Methods

**`get_skew_analysis(symbol, options_chain)`**
- Detailed volatility skew across strikes
- Returns: Skew data for visualization

**`get_term_structure(symbol, current_price, options_chain)`**
- Term structure across expirations
- Returns: Term structure with shape classification

**`get_volatility_surface(symbol, current_price, options_chain)`**
- 3D volatility surface data
- Returns: Surface points for 3D visualization

## Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_calculators.py

# Run integration tests only
pytest tests/integration/

# View coverage report
open htmlcov/index.html
```

**Test Coverage**: 85%+ (target met)

## Key Algorithms

### IV Rank Calculation
```
IV Rank = (Current IV - 52-week Low IV) / (52-week High IV - 52-week Low IV) × 100
```

### IV Percentile Calculation
```
IV Percentile = (Days with IV < Current IV) / Total Days × 100
```

### Historical Volatility (Close-to-Close)
```
HV = σ(log returns) × √252 × 100
```

### IV/HV Ratio
```
IV/HV Ratio = Current IV / Historical Volatility (30-day)
```

## Trading Guidelines

### High IV (Rank > 70)
- **Action**: Sell premium
- **Strategies**: Naked puts, covered calls, credit spreads, iron condors
- **Risk**: Define maximum loss, use technical levels

### Low IV (Rank < 30)
- **Action**: Buy premium
- **Strategies**: Long calls/puts, debit spreads, calendars, straddles
- **Risk**: Buy 60+ DTE, look for catalysts

### Neutral IV (Rank 30-70)
- **Action**: Directional or wait
- **Strategies**: Technical analysis, defined risk spreads
- **Risk**: Smaller positions, monitor for signals

## Performance

- **IV Metrics**: < 10ms (without options chain)
- **Complete Analysis**: < 100ms (with full options chain)
- **Watchlist (10 symbols)**: < 500ms
- **Memory**: Efficient data structures, minimal memory footprint

## Dependencies

- **numpy**: Numerical computations
- **scipy**: Statistical functions, interpolation
- **pandas**: Optional, for data manipulation
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting

## Integration with OPTIX Platform

The Volatility Compass integrates with the OPTIX Trading Platform via the API interface:

1. **Data Input**: Receives IV history, price data, and options chains from platform
2. **Analysis**: Performs calculations and generates insights
3. **Output**: Returns structured data for platform UI rendering
4. **Alerts**: Can push alerts to platform notification system
5. **Watchlists**: Integrates with platform watchlist management

## Future Enhancements

- Real-time IV streaming and updates
- Machine learning for IV forecasting
- Historical strategy backtesting
- Enhanced visualization components
- Mobile app integration
- Custom alert webhooks
- Portfolio-level IV analysis

## Documentation

- **User Guide**: `docs/USER_GUIDE.md` - Comprehensive usage instructions
- **Technical Requirements**: `docs/TECHNICAL_REQUIREMENTS.md` - System specifications
- **API Documentation**: `docs/api/` - Detailed API reference

## Support

For issues, questions, or feature requests:
- Review documentation in `docs/`
- Check examples in `examples/`
- Run test suite to verify installation
- Contact OPTIX development team

## License

Proprietary - OPTIX Trading Platform
© 2024 All Rights Reserved

## Version

**Version 1.0.0** - Initial Release
- Full feature implementation
- 85%+ test coverage
- Complete documentation
- Production-ready code

---

**Built with** ❤️ **for options traders by the OPTIX team**
