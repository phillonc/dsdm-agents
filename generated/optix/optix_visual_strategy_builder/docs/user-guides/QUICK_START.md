# Quick Start Guide

## Introduction

Welcome to the OPTIX Visual Strategy Builder! This guide will help you get started building and analyzing options strategies.

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd optix_visual_strategy_builder
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Verify installation**:
```bash
python -c "from src.strategy_builder import StrategyBuilder; print('Success!')"
```

## Your First Strategy

### Using Python API

Let's create a simple Bull Call Spread:

```python
from datetime import date, timedelta
from src.strategy_builder import StrategyBuilder
from src.models import OptionType, PositionType, Greeks

# Initialize builder
builder = StrategyBuilder()

# Create custom strategy
strategy = builder.create_strategy(
    name="Bull Call Spread",
    underlying_symbol="AAPL"
)

# Set expiration date
expiration = date.today() + timedelta(days=45)

# Add long call (lower strike)
builder.add_leg_to_strategy(
    strategy_id=strategy.id,
    option_type=OptionType.CALL,
    position_type=PositionType.LONG,
    strike=170.0,
    expiration=expiration,
    quantity=1,
    premium=5.50,
    implied_volatility=0.28,
    greeks=Greeks(delta=0.55, gamma=0.03, theta=-0.08, vega=0.18, rho=0.05)
)

# Add short call (higher strike)
builder.add_leg_to_strategy(
    strategy_id=strategy.id,
    option_type=OptionType.CALL,
    position_type=PositionType.SHORT,
    strike=180.0,
    expiration=expiration,
    quantity=1,
    premium=2.50,
    implied_volatility=0.26,
    greeks=Greeks(delta=0.35, gamma=0.02, theta=-0.05, vega=0.12, rho=0.03)
)

# View strategy
print(f"Strategy: {strategy.name}")
print(f"Total Cost: ${strategy.get_total_cost()}")
print(f"Number of Legs: {len(strategy.legs)}")
```

### View Payoff Diagram

```python
# Calculate payoff diagram
payoff = builder.calculate_payoff_diagram(
    strategy_id=strategy.id,
    current_price=175.0
)

print(f"Max Profit: ${payoff['max_profit']}")
print(f"Max Loss: ${payoff['max_loss']}")
print(f"Breakeven: {payoff['breakeven_points']}")
print(f"Current P&L: ${payoff['current_pnl']}")
```

### Analyze Greeks

```python
# Get aggregated Greeks
greeks = strategy.get_aggregated_greeks()

print("Portfolio Greeks:")
print(f"  Delta: {greeks.delta:.4f}")
print(f"  Gamma: {greeks.gamma:.4f}")
print(f"  Theta: {greeks.theta:.4f}")
print(f"  Vega: {greeks.vega:.4f}")
print(f"  Rho: {greeks.rho:.4f}")
```

## Using Strategy Templates

Instead of building from scratch, use pre-configured templates:

### Iron Condor

```python
from src.models import StrategyType

expiration = date.today() + timedelta(days=30)

strategy = builder.create_from_template(
    template_type=StrategyType.IRON_CONDOR,
    underlying_symbol="SPY",
    current_price=450.0,
    expiration=expiration,
    wing_width=5.0,  # Distance between long and short strikes
    body_width=10.0,  # Distance between put and call spreads
    quantity=1
)

print(f"Created: {strategy.name}")
print(f"Legs: {len(strategy.legs)}")
print(f"Net Credit: ${strategy.get_total_cost()}")
```

### Long Straddle

```python
strategy = builder.create_from_template(
    template_type=StrategyType.STRADDLE,
    underlying_symbol="TSLA",
    current_price=250.0,
    expiration=expiration,
    strike=250.0,
    quantity=1,
    position_type=PositionType.LONG
)
```

### Butterfly Spread

```python
strategy = builder.create_from_template(
    template_type=StrategyType.BUTTERFLY,
    underlying_symbol="QQQ",
    current_price=400.0,
    expiration=expiration,
    wing_width=5.0,
    quantity=1,
    option_type=OptionType.CALL
)
```

## Scenario Analysis

### Test Price Movements

```python
# Analyze different price scenarios
price_scenario = builder.analyze_scenario(
    strategy_id=strategy.id,
    current_price=450.0,
    scenario_type='price',
    price_changes=[-10, -5, 0, 5, 10, 15, 20]
)

print("Price Scenarios:")
for result in price_scenario['results']:
    print(f"  {result['price_change_percent']:+.0f}%: "
          f"Price ${result['new_price']:.2f} -> "
          f"P&L ${result['pnl']:.2f}")
```

### Test Volatility Changes

```python
# Analyze IV expansion/contraction
vol_scenario = builder.analyze_scenario(
    strategy_id=strategy.id,
    current_price=450.0,
    scenario_type='volatility',
    volatility_changes=[-20, -10, 0, 10, 20]
)

print("\nVolatility Scenarios:")
for result in vol_scenario['results']:
    print(f"  {result['volatility_change_percent']:+.0f}% IV: "
          f"P&L Impact ${result['estimated_pnl_impact']:.2f}")
```

### Time Decay Analysis

```python
# Analyze theta decay over time
time_scenario = builder.analyze_scenario(
    strategy_id=strategy.id,
    current_price=450.0,
    scenario_type='time',
    days_forward=[1, 7, 14, 21, 30]
)

print("\nTime Decay:")
for result in time_scenario['results']:
    print(f"  {result['days_forward']} days: "
          f"P&L Impact ${result['estimated_pnl_impact']:.2f}")
```

### Stress Testing

```python
# Run stress tests
stress_test = builder.analyze_scenario(
    strategy_id=strategy.id,
    current_price=450.0,
    scenario_type='stress'
)

print("\nStress Tests:")
for scenario_name, result in stress_test['results'].items():
    print(f"  {scenario_name}: ${result['estimated_total_pnl']:.2f}")
```

## Real-Time P&L Tracking

```python
# Start tracking
builder.start_pnl_tracking(strategy.id)

# Simulate price updates
prices = [450.0, 452.0, 455.0, 453.0, 451.0]

for price in prices:
    snapshot = builder.update_pnl(strategy.id, price)
    print(f"Price: ${price:.2f} -> P&L: ${snapshot['pnl']:.2f}")

# Get history
history = builder.get_pnl_history(strategy.id)
print(f"\nTracked {len(history)} price updates")
```

## Risk Metrics

```python
# Get comprehensive risk analysis
metrics = builder.get_risk_metrics(
    strategy_id=strategy.id,
    current_price=450.0
)

print("\nRisk Metrics:")
print(f"  Max Profit: ${metrics['risk_reward']['max_profit']:.2f}")
print(f"  Max Loss: ${metrics['risk_reward']['max_loss']:.2f}")
print(f"  Risk/Reward: {metrics['risk_reward']['risk_reward_ratio']:.2f}")
print(f"  Return on Risk: {metrics['risk_reward']['return_on_risk_percent']:.1f}%")
print(f"  Probability of Profit: {metrics['probability_analysis']['probability_of_profit']:.1f}%")
print(f"  Expected Value: ${metrics['probability_analysis']['expected_value']:.2f}")
```

## Export and Import

### Export Strategy

```python
# Export to dictionary
exported = builder.export_strategy(strategy.id)

# Save to file
import json
with open('my_strategy.json', 'w') as f:
    json.dump(exported, f, indent=2)

print("Strategy exported to my_strategy.json")
```

### Import Strategy

```python
# Load from file
with open('my_strategy.json', 'r') as f:
    strategy_data = json.load(f)

# Import
imported_strategy = builder.import_strategy(strategy_data)
print(f"Imported: {imported_strategy.name}")
```

## Using the REST API

### Start the Server

```bash
python -m src.api
```

Server runs on `http://localhost:5000`

### Create Strategy (API)

```bash
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
```

### Get Payoff Diagram (API)

```bash
curl -X GET "http://localhost:5000/api/v1/strategies/{strategy_id}/payoff?current_price=450.0"
```

### Run Scenario (API)

```bash
curl -X POST http://localhost:5000/api/v1/strategies/{strategy_id}/scenarios \
  -H "Content-Type: application/json" \
  -d '{
    "current_price": 450.0,
    "scenario_type": "stress"
  }'
```

## Common Use Cases

### Use Case 1: Income Generation

```python
# Create Iron Condor for premium collection
strategy = builder.create_from_template(
    template_type=StrategyType.IRON_CONDOR,
    underlying_symbol="SPY",
    current_price=450.0,
    expiration=date.today() + timedelta(days=45),
    wing_width=10.0,  # Wider wings = more safety
    body_width=20.0   # Wider body = higher probability
)

# Check if it meets income goals
metrics = builder.get_risk_metrics(strategy.id, 450.0)
credit_received = strategy.get_total_cost()  # Should be positive

if metrics['probability_analysis']['probability_of_profit'] > 65:
    print(f"Good income trade! Collect ${credit_received:.2f}")
    print(f"Win rate: {metrics['probability_analysis']['probability_of_profit']:.1f}%")
```

### Use Case 2: Earnings Play

```python
# Long Straddle before earnings
strategy = builder.create_from_template(
    template_type=StrategyType.STRADDLE,
    underlying_symbol="NVDA",
    current_price=500.0,
    expiration=date.today() + timedelta(days=7),
    strike=500.0,
    position_type=PositionType.LONG
)

# Test different outcome scenarios
scenarios = builder.analyze_scenario(
    strategy_id=strategy.id,
    current_price=500.0,
    scenario_type='price',
    price_changes=[-15, -10, -5, 0, 5, 10, 15]
)

# Need 10%+ move to profit
for result in scenarios['results']:
    if result['pnl'] > 0:
        print(f"Profitable at {result['price_change_percent']:+.0f}% move")
```

### Use Case 3: Hedging

```python
# Protective Put for downside protection
strategy = builder.create_from_template(
    template_type=StrategyType.PROTECTIVE_PUT,
    underlying_symbol="AAPL",
    current_price=180.0,
    expiration=date.today() + timedelta(days=90),
    put_strike=170.0  # 10-point protection
)

# Analyze protection
payoff = builder.calculate_payoff_diagram(strategy.id, 180.0)
print(f"Max Loss (with protection): ${payoff['max_loss']:.2f}")
print(f"Protection cost: ${abs(strategy.get_total_cost()):.2f}")
```

## Tips and Best Practices

1. **Always check Greeks**: Monitor delta for directional bias, theta for time decay
2. **Use templates**: Start with templates and modify as needed
3. **Test scenarios**: Run multiple what-if scenarios before trading
4. **Check probabilities**: Use Monte Carlo to estimate win rate
5. **Track P&L**: Monitor positions in real-time
6. **Export strategies**: Save successful strategies for reuse

## Next Steps

- Read the [API Reference](../api/API_REFERENCE.md) for complete endpoint documentation
- See [Architecture](../ARCHITECTURE.md) for system design details
- Explore advanced features in the code examples

## Getting Help

If you encounter issues:
1. Check the documentation
2. Review test files for usage examples
3. Contact the development team

Happy trading! 🚀
