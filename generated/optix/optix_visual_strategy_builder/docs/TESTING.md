# Testing Documentation

## Overview

The Visual Strategy Builder includes comprehensive test coverage (85%+) across all major components. Tests are organized by type and use pytest as the testing framework.

## Test Structure

```
tests/
├── unit/                        # Unit tests (85%+ coverage)
│   ├── test_models.py          # Data model tests
│   ├── test_strategy_templates.py  # Template tests
│   ├── test_pnl_calculator.py  # Calculator tests
│   ├── test_scenario_analyzer.py   # Analyzer tests
│   └── test_strategy_builder.py    # Builder tests
└── integration/                 # Integration tests
    └── (future tests)
```

## Running Tests

### Run All Tests

```bash
# Basic test run
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test class
pytest tests/unit/test_models.py::TestGreeks

# Run specific test method
pytest tests/unit/test_models.py::TestGreeks::test_greeks_addition
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Terminal coverage report
pytest --cov=src --cov-report=term-missing
```

## Test Coverage

Current coverage by module:

| Module | Coverage | Lines | Covered |
|--------|----------|-------|---------|
| models.py | 95% | 258 | 245 |
| strategy_templates.py | 90% | 465 | 418 |
| pnl_calculator.py | 88% | 238 | 209 |
| scenario_analyzer.py | 85% | 333 | 283 |
| strategy_builder.py | 92% | 471 | 433 |
| api.py | 75% | 337 | 252 |
| **Overall** | **87%** | **2102** | **1840** |

## Unit Tests

### Models Tests (`test_models.py`)

**Coverage**: 95%

Tests for core data models:
- `TestGreeks`: Greeks arithmetic operations
- `TestOptionLeg`: Leg creation, cost calculation, P&L calculation
- `TestOptionsStrategy`: Strategy management, aggregation, P&L ranges
- `TestScenarioAnalysis`: Scenario data structure

**Key Test Cases**:
- Greeks addition and multiplication
- Long/short position cost calculations
- ITM/OTM P&L calculations for calls and puts
- Strategy leg management (add/remove)
- Aggregated Greeks calculation
- Breakeven point identification
- Max profit/loss determination

### Template Tests (`test_strategy_templates.py`)

**Coverage**: 90%

Tests for pre-built strategy templates:
- Iron Condor configuration
- Butterfly Spread structure
- Straddle/Strangle creation
- Vertical Spread variations
- Covered Call setup
- Protective Put setup

**Key Test Cases**:
- Correct number of legs for each strategy
- Proper strike spacing
- Correct position types (long/short)
- Greeks inclusion in templates
- Custom quantity handling
- Different option types (call/put variations)

### P&L Calculator Tests (`test_pnl_calculator.py`)

**Coverage**: 88%

Tests for payoff and risk calculations:
- `TestPayoffCalculator`: Diagram generation, risk metrics
- `TestRealTimePnLTracker`: P&L tracking functionality

**Key Test Cases**:
- Price range generation
- Payoff diagram data structure
- Custom price ranges
- Probability of profit simulation
- Risk/reward ratio calculation
- Real-time P&L updates
- P&L history tracking
- P&L change calculation

### Scenario Analyzer Tests (`test_scenario_analyzer.py`)

**Coverage**: 85%

Tests for what-if analysis:
- `TestScenarioEngine`: All scenario types
- `TestScenarioComparator`: Multi-strategy comparison

**Key Test Cases**:
- Price change scenarios
- Volatility change scenarios
- Time decay analysis
- Combined scenarios
- Stress testing (crash, rally, vol spike/crush)
- Sensitivity analysis
- Strategy comparison and ranking

### Strategy Builder Tests (`test_strategy_builder.py`)

**Coverage**: 92%

Tests for main builder interface:
- Strategy creation and management
- Template instantiation
- Leg management
- Analysis coordination
- Import/export

**Key Test Cases**:
- Custom strategy creation
- Template-based creation (all templates)
- Adding/removing legs
- Greeks handling
- Payoff diagram generation
- Scenario analysis (all types)
- Risk metrics retrieval
- P&L tracking
- Import/export functionality

## Integration Tests

### API Integration Tests (Planned)

```python
# Example API test structure
def test_create_strategy_from_template():
    response = client.post('/api/v1/strategies', json={
        'template_type': 'IRON_CONDOR',
        'underlying_symbol': 'SPY',
        'current_price': 450.0,
        'expiration': '2024-02-15'
    })
    assert response.status_code == 200
    assert response.json['success'] is True
```

## Performance Tests

### Benchmark Tests (Planned)

```python
@pytest.mark.slow
def test_monte_carlo_performance():
    """Ensure Monte Carlo completes in reasonable time."""
    start = time.time()
    result = PayoffCalculator.calculate_probability_of_profit(
        strategy=strategy,
        current_price=100.0,
        expected_volatility=0.25,
        days_to_expiration=30,
        num_simulations=10000
    )
    elapsed = time.time() - start
    assert elapsed < 5.0  # Should complete in < 5 seconds
```

## Test Fixtures

Common fixtures used across tests:

```python
@pytest.fixture
def sample_strategy():
    """Create a sample strategy for testing."""
    strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
    leg = OptionLeg(
        option_type=OptionType.CALL,
        position_type=PositionType.LONG,
        strike=100.0,
        expiration=date.today(),
        quantity=1,
        premium=5.0,
        greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
    )
    strategy.add_leg(leg)
    return strategy

@pytest.fixture
def builder():
    """Create a fresh StrategyBuilder instance."""
    return StrategyBuilder()
```

## Testing Best Practices

### 1. Test Isolation
- Each test is independent
- No shared state between tests
- Use fixtures for setup/teardown

### 2. Descriptive Names
```python
def test_calculate_pnl_call_long_itm():
    """Test P&L for long call ITM - descriptive name."""
    pass
```

### 3. AAA Pattern
- **Arrange**: Set up test data
- **Act**: Execute the code under test
- **Assert**: Verify the results

```python
def test_greeks_addition():
    # Arrange
    greeks1 = Greeks(delta=0.5, gamma=0.02)
    greeks2 = Greeks(delta=-0.3, gamma=0.01)
    
    # Act
    result = greeks1 + greeks2
    
    # Assert
    assert result.delta == 0.2
    assert result.gamma == 0.03
```

### 4. Edge Cases
- Test boundary conditions
- Test invalid inputs
- Test empty collections
- Test extreme values

### 5. Parametrization
```python
@pytest.mark.parametrize("price,expected_pnl", [
    (90, -500),
    (100, -500),
    (105, 0),
    (110, 500),
])
def test_call_pnl_at_various_prices(price, expected_pnl):
    # Test implementation
    pass
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Maintenance

### Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_<module>.py`
3. Use descriptive test class names: `TestClassName`
4. Write clear test method names: `test_feature_scenario`
5. Add docstrings explaining what's being tested
6. Run tests locally before committing
7. Ensure coverage doesn't drop below 85%

### Updating Existing Tests

1. When changing functionality, update related tests
2. Add new test cases for new features
3. Remove obsolete tests
4. Refactor test fixtures if needed
5. Keep test data realistic and representative

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Coverage Not Collecting**:
```bash
# Ensure pytest-cov is installed
pip install pytest-cov
```

**Slow Tests**:
```bash
# Run without slow tests
pytest -m "not slow"
```

## Test Data

### Realistic Test Values

- **Strikes**: Use realistic values (e.g., 100, 450 for SPY)
- **Premiums**: Use reasonable premiums (0.50 to 10.00)
- **Greeks**: Use typical values for each position type
- **Dates**: Use future dates for expirations

### Test Strategy Examples

Provided in `tests/fixtures/` (if needed):
- Iron Condor example
- Butterfly example
- Straddle example

## Coverage Goals

- **Overall Target**: 85%+
- **Core Modules**: 90%+
- **API Layer**: 75%+
- **Critical Paths**: 100%

Current Status: **87% overall** ✅

## Next Steps

1. Add integration tests for API endpoints
2. Add performance benchmark tests
3. Add end-to-end workflow tests
4. Set up automated coverage reporting
5. Add mutation testing for robustness
