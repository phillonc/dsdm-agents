# OPTIX Visual Strategy Builder - API Documentation

## Overview

The StrategyAPI class provides a high-level, easy-to-use interface for all Visual Strategy Builder functionality. This document provides detailed API reference documentation.

## Table of Contents

1. [StrategyAPI Class](#strategyapi-class)
2. [Strategy Management](#strategy-management)
3. [Analysis Methods](#analysis-methods)
4. [Utility Methods](#utility-methods)
5. [Data Structures](#data-structures)
6. [Error Handling](#error-handling)

---

## StrategyAPI Class

### Initialization

```python
from src.api.strategy_api import StrategyAPI

api = StrategyAPI()
```

No parameters required for initialization.

---

## Strategy Management

### create_custom_strategy()

Create a new custom strategy.

```python
def create_custom_strategy(name: str, description: str = None) -> Dict
```

**Parameters:**
- `name` (str): Strategy name
- `description` (str, optional): Strategy description

**Returns:**
- Dictionary with strategy summary

**Example:**
```python
result = api.create_custom_strategy(
    name="My Custom Strategy",
    description="A custom bull call spread"
)
```

---

### create_from_template()

Create a strategy from a predefined template.

```python
def create_from_template(
    template_name: str,
    underlying_symbol: str,
    underlying_price: float,
    expiration_date: str,
    **kwargs
) -> Dict
```

**Parameters:**
- `template_name` (str): Template name (e.g., 'IRON_CONDOR', 'STRADDLE')
- `underlying_symbol` (str): Underlying asset symbol
- `underlying_price` (float): Current underlying price
- `expiration_date` (str): ISO format date string
- `**kwargs`: Template-specific parameters

**Template-Specific Parameters:**

**Iron Condor:**
- `put_short_strike` (float)
- `put_long_strike` (float)
- `call_short_strike` (float)
- `call_long_strike` (float)

**Butterfly:**
- `lower_strike` (float)
- `middle_strike` (float)
- `upper_strike` (float)

**Strangle:**
- `put_strike` (float)
- `call_strike` (float)

**Bull/Bear Spreads:**
- `long_strike` (float)
- `short_strike` (float)

**Returns:**
- Dictionary with complete strategy analysis

**Example:**
```python
from datetime import datetime, timedelta

exp_date = (datetime.utcnow() + timedelta(days=45)).isoformat()

result = api.create_from_template(
    template_name='IRON_CONDOR',
    underlying_symbol='SPY',
    underlying_price=450.0,
    expiration_date=exp_date,
    put_short_strike=445.0,
    put_long_strike=440.0,
    call_short_strike=455.0,
    call_long_strike=460.0
)
```

---

### add_option_leg()

Add an option leg to the current strategy.

```python
def add_option_leg(
    symbol: str,
    underlying_symbol: str,
    option_type: str,
    strike_price: float,
    expiration_date: str,
    quantity: int,
    position: str,
    premium: float,
    underlying_price: float = None,
    implied_volatility: float = None
) -> Dict
```

**Parameters:**
- `symbol` (str): Option symbol
- `underlying_symbol` (str): Underlying asset symbol
- `option_type` (str): 'CALL' or 'PUT'
- `strike_price` (float): Strike price
- `expiration_date` (str): ISO format date string
- `quantity` (int): Number of contracts
- `position` (str): 'LONG' or 'SHORT'
- `premium` (float): Option premium per share
- `underlying_price` (float, optional): Current underlying price
- `implied_volatility` (float, optional): IV as decimal (e.g., 0.25 for 25%)

**Returns:**
- Dictionary with leg_id and updated strategy summary

**Example:**
```python
result = api.add_option_leg(
    symbol="AAPL_C180",
    underlying_symbol="AAPL",
    option_type="CALL",
    strike_price=180.0,
    expiration_date="2024-02-16T00:00:00",
    quantity=1,
    position="LONG",
    premium=8.50,
    underlying_price=182.0,
    implied_volatility=0.28
)

leg_id = result['leg_id']
```

---

### remove_option_leg()

Remove an option leg from the strategy.

```python
def remove_option_leg(leg_id: str) -> Dict
```

**Parameters:**
- `leg_id` (str): ID of the leg to remove

**Returns:**
- Dictionary with removed status and updated strategy summary

**Example:**
```python
result = api.remove_option_leg(leg_id)
print(f"Removed: {result['removed']}")
```

---

### update_option_leg()

Update parameters of an existing option leg.

```python
def update_option_leg(
    leg_id: str,
    quantity: int = None,
    premium: float = None,
    underlying_price: float = None,
    implied_volatility: float = None
) -> Dict
```

**Parameters:**
- `leg_id` (str): ID of the leg to update
- `quantity` (int, optional): New quantity
- `premium` (float, optional): New premium
- `underlying_price` (float, optional): New underlying price
- `implied_volatility` (float, optional): New IV

**Returns:**
- Dictionary with updated status and strategy summary

**Example:**
```python
result = api.update_option_leg(
    leg_id=leg_id,
    quantity=2,
    premium=7.25
)
```

---

## Analysis Methods

### get_strategy_analysis()

Get comprehensive analysis of the current strategy.

```python
def get_strategy_analysis() -> Dict
```

**Returns:**
- Dictionary with complete strategy analysis including:
  - Strategy details
  - Greeks
  - Risk/reward metrics
  - Payoff diagram
  - Risk metrics

**Example:**
```python
analysis = api.get_strategy_analysis()

print(f"Max Profit: ${analysis['risk_reward']['max_profit']:.2f}")
print(f"Max Loss: ${analysis['risk_reward']['max_loss']:.2f}")
print(f"Delta: {analysis['greeks']['total_delta']:.2f}")
```

---

### get_payoff_diagram()

Get payoff diagram data for visualization.

```python
def get_payoff_diagram(
    min_price: float = None,
    max_price: float = None,
    num_points: int = 200
) -> Dict
```

**Parameters:**
- `min_price` (float, optional): Minimum price for diagram
- `max_price` (float, optional): Maximum price for diagram
- `num_points` (int, optional): Number of data points (default: 200)

**Returns:**
- Dictionary with:
  - `expiration_payoff`: P&L at expiration
  - `current_payoff`: Current P&L
  - `breakeven_points`: List of breakeven prices
  - `max_profit`: Maximum profit details
  - `max_loss`: Maximum loss details

**Example:**
```python
payoff = api.get_payoff_diagram(min_price=400.0, max_price=500.0)

print(f"Breakeven Points: {payoff['breakeven_points']}")
print(f"Max Profit: ${payoff['max_profit']['value']:.2f} at ${payoff['max_profit']['price']:.2f}")

# Plot with matplotlib
import matplotlib.pyplot as plt
plt.plot(payoff['expiration_payoff']['prices'], payoff['expiration_payoff']['pnl'])
plt.xlabel('Underlying Price')
plt.ylabel('P&L')
plt.title('Payoff Diagram')
plt.grid(True)
plt.show()
```

---

### get_greeks_analysis()

Get detailed Greeks analysis with interpretations.

```python
def get_greeks_analysis() -> Dict
```

**Returns:**
- Dictionary with:
  - `current_greeks`: Current Greek values
  - `risk_profile`: Risk profile assessment
  - `interpretations`: Detailed interpretations of each Greek

**Example:**
```python
greeks = api.get_greeks_analysis()

print(f"Delta: {greeks['current_greeks']['total_delta']:.2f}")
print(f"Delta Interpretation: {greeks['interpretations']['delta']['description']}")
print(f"Risk Profile: {greeks['risk_profile']}")
```

---

### get_greeks_profile()

Get Greeks values across a price range.

```python
def get_greeks_profile(
    min_price: float = None,
    max_price: float = None,
    num_points: int = 100
) -> Dict
```

**Parameters:**
- `min_price` (float, optional): Minimum price
- `max_price` (float, optional): Maximum price
- `num_points` (int, optional): Number of points (default: 100)

**Returns:**
- Dictionary with Greeks values at each price point

**Example:**
```python
profile = api.get_greeks_profile(min_price=400.0, max_price=500.0)

# Plot delta profile
import matplotlib.pyplot as plt
plt.plot(profile['prices'], profile['delta'])
plt.xlabel('Underlying Price')
plt.ylabel('Delta')
plt.title('Delta Profile')
plt.show()
```

---

### get_risk_metrics()

Get comprehensive risk metrics.

```python
def get_risk_metrics() -> Dict
```

**Returns:**
- Dictionary with:
  - `risk_reward`: Max profit/loss and ratios
  - `value_at_risk`: VaR calculations
  - `probability_metrics`: Probability of profit
  - `margin_requirement`: Estimated margin
  - `greeks`: Current Greeks

**Example:**
```python
metrics = api.get_risk_metrics()

print(f"VaR (95%): ${metrics['value_at_risk']['value_at_risk']:.2f}")
print(f"Probability of Profit: {metrics['probability_metrics']['probability_of_profit_pct']:.1f}%")
print(f"Margin Required: ${metrics['margin_requirement']['estimated_margin']:.2f}")
```

---

### run_scenario_analysis()

Run what-if scenario analysis.

```python
def run_scenario_analysis(
    scenario_price: float,
    volatility_change: float = 0.0,
    days_passed: int = 0
) -> Dict
```

**Parameters:**
- `scenario_price` (float): Underlying price in scenario
- `volatility_change` (float, optional): Change in IV (e.g., 0.05 for +5%)
- `days_passed` (int, optional): Number of days passed

**Returns:**
- Dictionary with scenario results including P&L and Greeks

**Example:**
```python
# Test what happens if stock goes to 460, IV drops 5%, after 15 days
scenario = api.run_scenario_analysis(
    scenario_price=460.0,
    volatility_change=-0.05,
    days_passed=15
)

print(f"Scenario P&L: ${scenario['current_pnl']:.2f}")
print(f"Scenario Delta: {scenario['greeks']['total_delta']:.2f}")
```

---

### get_time_decay_analysis()

Analyze time decay impact.

```python
def get_time_decay_analysis(
    underlying_price: float,
    days_points: List[int] = None
) -> Dict
```

**Parameters:**
- `underlying_price` (float): Price to analyze at
- `days_points` (List[int], optional): Days to analyze (e.g., [0, 7, 14, 21, 28])

**Returns:**
- Dictionary with time series data

**Example:**
```python
decay = api.get_time_decay_analysis(
    underlying_price=450.0,
    days_points=[0, 15, 30, 45]
)

for point in decay['time_series']:
    print(f"Day {point['days_passed']}: P&L = ${point['pnl']:.2f}")
```

---

### get_volatility_analysis()

Analyze volatility impact.

```python
def get_volatility_analysis(
    underlying_price: float,
    iv_changes: List[float] = None
) -> Dict
```

**Parameters:**
- `underlying_price` (float): Price to analyze at
- `iv_changes` (List[float], optional): IV changes to test (e.g., [-0.10, 0, 0.10])

**Returns:**
- Dictionary with volatility series data

**Example:**
```python
vol_analysis = api.get_volatility_analysis(
    underlying_price=450.0,
    iv_changes=[-0.10, -0.05, 0.0, 0.05, 0.10]
)

for point in vol_analysis['volatility_series']:
    print(f"IV Change: {point['iv_change_pct']:+.1f}% → P&L: ${point['pnl']:.2f}")
```

---

### get_individual_leg_payoffs()

Get payoff diagrams for individual legs.

```python
def get_individual_leg_payoffs() -> List[Dict]
```

**Returns:**
- List of dictionaries, each containing payoff data for one leg

**Example:**
```python
leg_payoffs = api.get_individual_leg_payoffs()

for leg in leg_payoffs:
    print(f"Leg: {leg['label']}")
    print(f"Strike: ${leg['strike']:.2f}")
```

---

## Utility Methods

### get_available_templates()

Get list of available strategy templates.

```python
def get_available_templates() -> Dict
```

**Returns:**
- Dictionary mapping template names to descriptions

**Example:**
```python
templates = api.get_available_templates()

for name, description in templates.items():
    print(f"{name}: {description}")
```

---

### export_strategy()

Export current strategy to JSON-serializable format.

```python
def export_strategy() -> Dict
```

**Returns:**
- Dictionary with complete strategy export data

**Example:**
```python
export_data = api.export_strategy()

# Save to file
import json
with open('my_strategy.json', 'w') as f:
    json.dump(export_data, f, indent=2)
```

---

### import_strategy()

Import a strategy from export data.

```python
def import_strategy(export_data: Dict) -> Dict
```

**Parameters:**
- `export_data` (Dict): Previously exported strategy data

**Returns:**
- Dictionary with imported strategy summary

**Example:**
```python
# Load from file
import json
with open('my_strategy.json', 'r') as f:
    export_data = json.load(f)

# Import
result = api.import_strategy(export_data)
print(f"Imported: {result['name']}")
```

---

### clone_strategy()

Clone the current strategy.

```python
def clone_strategy(new_name: str = None) -> Dict
```

**Parameters:**
- `new_name` (str, optional): Name for cloned strategy

**Returns:**
- Dictionary with cloned strategy summary

**Example:**
```python
cloned = api.clone_strategy("My Strategy - Copy")
print(f"Cloned: {cloned['name']}")
```

---

### get_modification_history()

Get strategy modification history.

```python
def get_modification_history() -> List[Dict]
```

**Returns:**
- List of historical modifications

**Example:**
```python
history = api.get_modification_history()

for action in history:
    print(f"{action['timestamp']}: {action['action']}")
```

---

## Data Structures

### Strategy Summary

```python
{
    'strategy_id': str,
    'name': str,
    'template': str,
    'num_legs': int,
    'total_cost': float,
    'is_debit': bool,
    'is_credit': bool,
    'underlying_symbols': List[str],
    'expiration_dates': List[str],
    'created_at': str,
    'updated_at': str
}
```

### Analysis Result

```python
{
    'is_valid': bool,
    'strategy': Dict,  # Strategy details
    'greeks': Dict,    # Greeks summary
    'risk_reward': Dict,  # Risk/reward metrics
    'payoff_diagram': Dict,  # Payoff data
    'risk_metrics': Dict  # Comprehensive risk metrics
}
```

### Greeks Dictionary

```python
{
    'total_delta': float,
    'total_gamma': float,
    'total_theta': float,
    'total_vega': float,
    'total_rho': float,
    'delta_per_contract': float,
    'gamma_per_contract': float,
    'theta_per_contract': float,
    'vega_per_contract': float,
    'rho_per_contract': float,
    'risk_profile': Dict
}
```

---

## Error Handling

### Common Errors

**ValueError**: Raised when invalid parameters are provided
```python
try:
    api.add_option_leg(...)
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

**No Active Strategy**: Some methods require an active strategy
```python
result = api.get_payoff_diagram()
if 'error' in result:
    print(f"Error: {result['error']}")
```

### Best Practices

1. Always check for 'error' key in results
2. Validate inputs before passing to API
3. Handle exceptions appropriately
4. Use type hints for better IDE support

---

## Complete Example

```python
from src.api.strategy_api import StrategyAPI
from datetime import datetime, timedelta

# Initialize
api = StrategyAPI()

# Create Iron Condor
exp = (datetime.utcnow() + timedelta(days=45)).isoformat()
result = api.create_from_template(
    template_name='IRON_CONDOR',
    underlying_symbol='SPY',
    underlying_price=450.0,
    expiration_date=exp,
    put_short_strike=445.0,
    put_long_strike=440.0,
    call_short_strike=455.0,
    call_long_strike=460.0
)

# Get analysis
analysis = api.get_strategy_analysis()
print(f"Max Profit: ${analysis['risk_reward']['max_profit']:.2f}")
print(f"Probability of Profit: {analysis['risk_metrics']['probability_metrics']['probability_of_profit_pct']:.1f}%")

# Run scenarios
scenarios = [440, 445, 450, 455, 460]
for price in scenarios:
    scenario = api.run_scenario_analysis(scenario_price=price)
    print(f"At ${price}: P&L = ${scenario['current_pnl']:.2f}")

# Export strategy
export_data = api.export_strategy()
```

---

For more examples, see `examples/usage_example.py`.
