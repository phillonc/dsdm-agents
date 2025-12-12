# OPTIX Time Machine Backtester

## Overview

The OPTIX Time Machine Backtester is a comprehensive, production-ready backtesting engine for options trading strategies. It provides accurate historical simulation, robust optimization tools, and professional-grade performance analytics.

## Features

### Core Capabilities

1. **Historical Data Replay**
   - Accurate market conditions simulation
   - Multiple data frequencies (1min, 5min, hourly, daily)
   - Options chain reconstruction
   - Implied volatility surface modeling

2. **Multi-Leg Strategy Support**
   - Single leg options
   - Spreads (vertical, horizontal, diagonal)
   - Iron Condors
   - Butterflies and custom strategies
   - Unlimited legs per strategy

3. **Transaction Cost Modeling**
   - Per-contract commissions
   - Bid-ask spread costs
   - Market impact and slippage
   - Liquidity-based adjustments

4. **Walk-Forward Optimization**
   - Prevents overfitting
   - Multiple time periods
   - Parameter grid search
   - In-sample vs out-of-sample analysis

5. **Monte Carlo Simulation**
   - Bootstrap resampling
   - Parametric simulation
   - Trade order randomization
   - Risk of ruin analysis

6. **Realistic Execution Simulation**
   - Market orders
   - Limit orders with fill probability
   - Mid-price execution
   - Position sizing strategies

7. **Comprehensive Performance Metrics**
   - Total return and annualized return
   - Sharpe, Sortino, and Calmar ratios
   - Maximum drawdown
   - Win rate and profit factor
   - Value at Risk (VaR)
   - Conditional VaR (CVaR)

8. **Volatility Regime Analysis**
   - Performance by volatility environment
   - Regime classification (low, medium, high)
   - Strategy adaptation recommendations

9. **Visual Analytics**
   - Equity curves
   - Drawdown charts
   - Monthly returns heatmap
   - Trade distribution analysis
   - Interactive Plotly dashboards

10. **REST API**
    - Complete FastAPI implementation
    - Async endpoint support
    - Background task processing
    - Comprehensive error handling

## Installation

```bash
# Clone repository
git clone <repository-url>
cd optix_backtester

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Running a Backtest

```python
from datetime import datetime
from src.engine.backtester import BacktestEngine
from src.models.backtest import BacktestConfig, TransactionCostModel
from src.data.market_data import SimulatedMarketDataProvider
from src.strategies.example import SimpleStrategy

# Configure backtest
config = BacktestConfig(
    initial_capital=100000.0,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    symbols=["SPY", "QQQ"],
    transaction_costs=TransactionCostModel(
        commission_per_contract=0.65,
        slippage_percent=0.1
    ),
    max_positions=10
)

# Create engine and run
data_provider = SimulatedMarketDataProvider(seed=42)
engine = BacktestEngine(data_provider, config)
strategy = SimpleStrategy()

result = await engine.run(strategy)

# Print results
print(f"Total Trades: {result.performance.total_trades}")
print(f"Win Rate: {result.performance.win_rate:.2f}%")
print(f"Total Return: {result.performance.total_return:.2f}%")
print(f"Sharpe Ratio: {result.performance.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.performance.max_drawdown_percent:.2f}%")
```

### Starting the API Server

```bash
# Start server
python -m src.api.main

# Or with uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using the REST API

```bash
# Create backtest
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_capital": 100000,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-12-31T00:00:00",
    "symbols": ["SPY"],
    "max_positions": 5
  }'

# Get backtest results
curl "http://localhost:8000/api/v1/backtest/{backtest_id}"

# Run Monte Carlo simulation
curl -X POST "http://localhost:8000/api/v1/backtest/{backtest_id}/monte-carlo?iterations=1000"

# Compare backtests
curl -X POST "http://localhost:8000/api/v1/backtest/compare" \
  -H "Content-Type: application/json" \
  -d '["backtest_id_1", "backtest_id_2"]'
```

## Creating Custom Strategies

```python
from src.strategies.base import StrategyBase
from src.models.option import OptionStrategy, OptionLeg, OptionContract

class MyCustomStrategy(StrategyBase):
    """Custom options strategy"""
    
    def __init__(self, params=None):
        super().__init__("MyStrategy", params)
        self.entry_iv_threshold = params.get('entry_iv', 0.25)
    
    async def generate_signals(
        self,
        market_condition,
        current_positions,
        available_capital
    ):
        """Generate trading signals"""
        signals = []
        
        # Your strategy logic here
        if market_condition.implied_volatility < self.entry_iv_threshold:
            # Create strategy
            strategy = OptionStrategy(...)
            signals.append(strategy)
        
        return signals
    
    async def should_exit(
        self,
        position,
        market_condition,
        available_capital
    ):
        """Check exit conditions"""
        # Your exit logic here
        return False, ""
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_option_models.py

# Run integration tests
pytest tests/integration/

# View coverage report
open htmlcov/index.html
```

## Performance Metrics Explained

### Sharpe Ratio
Risk-adjusted return metric. Higher is better. Above 1.0 is good, above 2.0 is excellent.

### Sortino Ratio
Similar to Sharpe but only penalizes downside volatility. Better for strategies with asymmetric returns.

### Calmar Ratio
Return divided by maximum drawdown. Measures return per unit of worst-case risk.

### Profit Factor
Gross profit divided by gross loss. Above 1.5 is good, above 2.0 is excellent.

### Win Rate
Percentage of profitable trades. Interpret with average win/loss sizes.

### Maximum Drawdown
Largest peak-to-trough decline. Critical for capital preservation.

### VaR (Value at Risk)
Expected loss at 5th percentile. Estimates downside risk.

### CVaR (Conditional VaR)
Expected loss when loss exceeds VaR. Tail risk measure.

## Walk-Forward Optimization

Prevents overfitting by:
1. Splitting data into train/test periods
2. Optimizing on training data
3. Testing on unseen data
4. Rolling forward through time
5. Analyzing degradation from IS to OOS

```python
from src.optimization.walk_forward import WalkForwardOptimizer

optimizer = WalkForwardOptimizer(
    data_provider,
    train_ratio=0.7,
    num_periods=5
)

result = await optimizer.optimize(
    config,
    SimpleStrategy,
    param_grid={
        'entry_threshold': [0.01, 0.02, 0.03],
        'exit_target': [0.15, 0.20, 0.25]
    }
)

print(f"In-Sample Sharpe: {result.in_sample_sharpe:.2f}")
print(f"Out-of-Sample Sharpe: {result.out_of_sample_sharpe:.2f}")
print(f"Degradation: {result.degradation_percent:.2f}%")
```

## Monte Carlo Simulation

Test robustness through resampling:

```python
from src.optimization.monte_carlo import MonteCarloSimulator

simulator = MonteCarloSimulator(iterations=10000, seed=42)
mc_result = simulator.simulate(backtest_result, method="bootstrap")

print(f"Mean Return: {mc_result.mean_return:.2f}%")
print(f"95% CI: [{mc_result.return_confidence_95[0]:.2f}%, "
      f"{mc_result.return_confidence_95[1]:.2f}%]")
print(f"Probability of Profit: {mc_result.probability_of_profit:.1%}")
print(f"Risk of Ruin: {mc_result.probability_of_ruin:.1%}")
```

## Visualization

```python
from src.visualization.charts import BacktestVisualizer

visualizer = BacktestVisualizer(backtest_result)

# Create charts
visualizer.plot_equity_curve(save_path="equity_curve.png")
visualizer.plot_returns_distribution(save_path="returns.png")
visualizer.plot_monthly_returns(save_path="monthly.png")
visualizer.plot_trade_analysis(save_path="trades.png")

# Create interactive dashboard
fig = visualizer.create_interactive_dashboard()
fig.write_html("dashboard.html")
```

## Architecture

### Core Components

- **Engine**: `src/engine/backtester.py` - Main backtesting engine
- **Models**: `src/models/` - Data models and schemas
- **Data**: `src/data/` - Market data providers and replay
- **Execution**: `src/execution/` - Order execution simulation
- **Strategies**: `src/strategies/` - Trading strategy framework
- **Optimization**: `src/optimization/` - Walk-forward and Monte Carlo
- **Visualization**: `src/visualization/` - Charting and analytics
- **API**: `src/api/` - FastAPI REST endpoints

### Data Flow

1. Historical data loaded from provider
2. Market conditions replayed chronologically
3. Strategy generates signals
4. Orders executed with realistic fills
5. Positions tracked and managed
6. Performance metrics calculated
7. Results visualized and analyzed

## Configuration

Edit `config/settings.py` to customize:

- API settings (host, port)
- Default capital and costs
- Monte Carlo iterations
- Walk-forward parameters
- Risk-free rate
- Logging configuration

## API Documentation

Once the server is running, access interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Best Practices

1. **Always use walk-forward optimization** to prevent overfitting
2. **Run Monte Carlo simulations** to test robustness
3. **Include realistic transaction costs** (don't underestimate)
4. **Test across multiple volatility regimes**
5. **Use proper position sizing** (not over-leveraged)
6. **Account for slippage** on large orders
7. **Validate results** with out-of-sample data
8. **Consider market impact** for large strategies

## Limitations

- Historical data availability
- Assumes liquid options markets
- Cannot predict future market changes
- Model risk in volatility estimation
- Execution assumptions may vary in practice

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests for new features
4. Ensure 85%+ test coverage
5. Submit pull request

## License

MIT License - See LICENSE file

## Support

For issues and questions:
- GitHub Issues: <repository-url>/issues
- Documentation: `docs/`
- Email: dev@optix.com

## Roadmap

- [ ] Real market data integration (CBOE, IB, etc.)
- [ ] Live trading execution bridge
- [ ] Machine learning strategy optimization
- [ ] Portfolio backtesting
- [ ] Greeks-based risk management
- [ ] Earnings and dividend adjustments
- [ ] Real-time performance monitoring
- [ ] Cloud deployment templates

## Acknowledgments

Built with:
- FastAPI
- Pydantic
- NumPy/Pandas
- Matplotlib/Plotly
- Pytest

## Version History

### v1.0.0 (2024-12-12)
- Initial release
- Complete backtesting engine
- Walk-forward optimization
- Monte Carlo simulation
- REST API
- Comprehensive testing (85%+ coverage)
