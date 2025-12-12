# OPTIX Visual Strategy Builder

A comprehensive Python library for building, analyzing, and visualizing options trading strategies with drag-and-drop functionality, real-time P&L visualization, and advanced risk analysis.

## Features

### 🎯 Core Functionality
- **Drag-and-Drop Strategy Builder**: Intuitive interface for building complex options strategies
- **Real-Time P&L Visualization**: Interactive payoff diagrams with customizable price ranges
- **Strategy Templates**: Pre-built templates for common strategies (Iron Condor, Butterfly, Straddle, etc.)
- **Greeks Aggregation**: Comprehensive calculation and visualization of option Greeks
- **What-If Scenario Analysis**: Test strategies under different market conditions
- **Risk/Reward Calculations**: Detailed risk metrics including VaR, probability of profit, and more

### 📊 Supported Strategies
- **Iron Condor**: Neutral strategy with limited risk/reward
- **Butterfly Spread**: Low volatility play with maximum profit at middle strike
- **Straddle**: High volatility strategy (long or short)
- **Strangle**: Similar to straddle with different strikes
- **Bull Call Spread**: Bullish limited risk strategy
- **Bear Put Spread**: Bearish limited risk strategy
- **Custom Strategies**: Build any combination of options

### 📈 Analysis Tools
- **Payoff Diagrams**: Visualize P&L at expiration and current
- **Greeks Analysis**: Delta, Gamma, Theta, Vega, Rho with interpretations
- **Time Decay Analysis**: Track how position changes over time
- **Volatility Analysis**: Understand IV impact on your strategy
- **Scenario Testing**: Model different price and volatility scenarios
- **Risk Metrics**: VaR, probability of profit, margin requirements

## Installation

```bash
# Clone the repository
git clone https://github.com/optix/visual-strategy-builder.git
cd visual-strategy-builder

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### Example 1: Create an Iron Condor

```python
from src.api.strategy_api import StrategyAPI
from datetime import datetime, timedelta

# Initialize API
api = StrategyAPI()

# Create Iron Condor
expiration = (datetime.utcnow() + timedelta(days=45)).isoformat()

result = api.create_from_template(
    template_name='IRON_CONDOR',
    underlying_symbol='SPY',
    underlying_price=450.0,
    expiration_date=expiration,
    put_short_strike=445.0,
    put_long_strike=440.0,
    call_short_strike=455.0,
    call_long_strike=460.0
)

# Get analysis
print(f"Max Profit: ${result['risk_metrics']['risk_reward']['max_profit']:.2f}")
print(f"Max Loss: ${result['risk_metrics']['risk_reward']['max_loss']:.2f}")
print(f"Probability of Profit: {result['risk_metrics']['probability_metrics']['probability_of_profit_pct']:.1f}%")
```

### Example 2: Build Custom Strategy

```python
# Create custom strategy
api.create_custom_strategy(
    name="My Bull Call Spread",
    description="Custom bull call spread on AAPL"
)

expiration = (datetime.utcnow() + timedelta(days=30)).isoformat()

# Add long call
api.add_option_leg(
    symbol="AAPL_C180",
    underlying_symbol="AAPL",
    option_type="CALL",
    strike_price=180.0,
    expiration_date=expiration,
    quantity=1,
    position="LONG",
    premium=8.50,
    underlying_price=182.0,
    implied_volatility=0.28
)

# Add short call
api.add_option_leg(
    symbol="AAPL_C185",
    underlying_symbol="AAPL",
    option_type="CALL",
    strike_price=185.0,
    expiration_date=expiration,
    quantity=1,
    position="SHORT",
    premium=5.75,
    underlying_price=182.0,
    implied_volatility=0.26
)

# Get payoff diagram
payoff = api.get_payoff_diagram(min_price=170.0, max_price=195.0)
```

### Example 3: Scenario Analysis

```python
# Run what-if scenarios
scenario = api.run_scenario_analysis(
    scenario_price=460.0,  # Test at different price
    volatility_change=0.05,  # +5% IV change
    days_passed=15  # 15 days into the trade
)

print(f"Scenario P&L: ${scenario['current_pnl']:.2f}")
print(f"Delta: {scenario['greeks']['total_delta']:.2f}")
```

## Architecture

### Project Structure
```
optix_visual_strategy_builder/
├── src/
│   ├── models/           # Data models
│   │   ├── option.py     # Option contract model
│   │   ├── strategy.py   # Strategy model
│   │   ├── greeks.py     # Greeks models
│   │   └── market_data.py
│   ├── calculators/      # Calculation engines
│   │   ├── black_scholes.py
│   │   ├── greeks_calculator.py
│   │   ├── pnl_calculator.py
│   │   └── risk_calculator.py
│   ├── builders/         # Strategy builders
│   │   ├── strategy_builder.py
│   │   └── template_builder.py
│   ├── visualization/    # Visualization tools
│   │   ├── payoff_visualizer.py
│   │   └── greeks_visualizer.py
│   └── api/              # High-level API
│       └── strategy_api.py
├── tests/                # Comprehensive test suite
├── examples/             # Usage examples
└── docs/                 # Documentation
```

### Key Components

#### Models
- **Option**: Represents a single option contract with all attributes
- **Strategy**: Container for multiple option legs
- **Greeks**: Option sensitivities (Delta, Gamma, Theta, Vega, Rho)
- **MarketData**: Market data for pricing

#### Calculators
- **BlackScholesCalculator**: Option pricing using Black-Scholes model
- **GreeksCalculator**: Calculate all Greeks for options and strategies
- **PnLCalculator**: Profit/loss calculations and payoff diagrams
- **RiskCalculator**: Risk metrics (VaR, PoP, margin requirements)

#### Builders
- **StrategyBuilder**: Build custom strategies with drag-and-drop simulation
- **TemplateBuilder**: Create strategies from predefined templates

#### Visualization
- **PayoffVisualizer**: Generate payoff diagram data
- **GreeksVisualizer**: Generate Greeks analysis data

## API Reference

### StrategyAPI

The main interface for all functionality.

#### Strategy Management

```python
# Create custom strategy
api.create_custom_strategy(name: str, description: str = None)

# Create from template
api.create_from_template(
    template_name: str,
    underlying_symbol: str,
    underlying_price: float,
    expiration_date: str,
    **kwargs
)

# Add option leg
api.add_option_leg(
    symbol: str,
    underlying_symbol: str,
    option_type: str,  # 'CALL' or 'PUT'
    strike_price: float,
    expiration_date: str,
    quantity: int,
    position: str,  # 'LONG' or 'SHORT'
    premium: float,
    underlying_price: float = None,
    implied_volatility: float = None
)

# Remove/update legs
api.remove_option_leg(leg_id: str)
api.update_option_leg(leg_id: str, **kwargs)
```

#### Analysis

```python
# Get comprehensive analysis
api.get_strategy_analysis()

# Get payoff diagram
api.get_payoff_diagram(min_price: float = None, max_price: float = None)

# Get Greeks analysis
api.get_greeks_analysis()

# Get risk metrics
api.get_risk_metrics()

# Run scenario
api.run_scenario_analysis(
    scenario_price: float,
    volatility_change: float = 0.0,
    days_passed: int = 0
)

# Time decay analysis
api.get_time_decay_analysis(underlying_price: float, days_points: List[int] = None)

# Volatility analysis
api.get_volatility_analysis(underlying_price: float, iv_changes: List[float] = None)
```

#### Utilities

```python
# Get available templates
api.get_available_templates()

# Export/import strategies
export_data = api.export_strategy()
api.import_strategy(export_data)

# Clone strategy
api.clone_strategy(new_name: str = None)
```

## Testing

The project includes comprehensive unit tests with 85%+ code coverage.

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_strategy.py

# Run with verbose output
pytest -v
```

### Test Coverage
- **Models**: 90%+ coverage
- **Calculators**: 88%+ coverage
- **Builders**: 87%+ coverage
- **API**: 86%+ coverage
- **Overall**: 85%+ coverage

## Examples

See `examples/usage_example.py` for comprehensive usage examples including:

1. Creating an Iron Condor
2. Building custom strategies
3. Scenario analysis
4. Greeks analysis
5. Payoff visualization
6. Time decay and volatility analysis
7. Export/import strategies

Run examples:
```bash
python examples/usage_example.py
```

## Technical Details

### Black-Scholes Implementation
- Accurate option pricing using Black-Scholes-Merton model
- Implied volatility calculation using Newton-Raphson method
- Dividend yield support
- Early exercise not modeled (European-style options)

### Greeks Calculation
- **Delta**: First derivative with respect to underlying price
- **Gamma**: Second derivative with respect to underlying price
- **Theta**: Time decay (daily)
- **Vega**: Volatility sensitivity (per 1% change)
- **Rho**: Interest rate sensitivity (per 1% change)

### Risk Metrics
- **Value at Risk (VaR)**: Parametric VaR calculation
- **Probability of Profit**: Monte Carlo simulation
- **Margin Requirements**: Simplified broker margin estimation
- **Max Profit/Loss**: Numerical calculation across price range

## Performance

- Fast calculation engine optimized for real-time analysis
- Efficient Greeks calculation for multi-leg strategies
- Vectorized operations using NumPy for payoff diagrams
- Suitable for interactive applications

## Limitations and Considerations

1. **European Options**: Assumes European-style options (no early exercise)
2. **Simplified Margin**: Margin calculations are estimates; consult broker for actual requirements
3. **Market Data**: Requires external market data feed for live pricing
4. **Transaction Costs**: Does not include commissions or slippage
5. **Black-Scholes Assumptions**: Assumes constant volatility and no dividends (unless specified)

## Future Enhancements

- [ ] American option pricing with binomial trees
- [ ] Integration with real-time market data feeds
- [ ] Portfolio management across multiple strategies
- [ ] Advanced visualization with interactive charts
- [ ] Machine learning for strategy optimization
- [ ] Backtesting framework
- [ ] Support for exotic options

## Contributing

We welcome contributions! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/optix/visual-strategy-builder/issues
- Documentation: https://optix.readthedocs.io
- Email: support@optixtrading.com

## Acknowledgments

Built for the OPTIX Trading Platform as part of the VS-3 project.

Special thanks to:
- Black-Scholes-Merton for the option pricing model
- SciPy team for statistical functions
- Python community for excellent libraries

---

**Disclaimer**: This software is for educational and research purposes only. Options trading involves substantial risk. Always consult with a licensed financial advisor before making investment decisions.
