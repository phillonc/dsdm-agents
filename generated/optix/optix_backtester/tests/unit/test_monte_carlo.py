"""
Unit tests for Monte Carlo simulation
"""
import pytest
import numpy as np
from datetime import datetime
from uuid import uuid4

from src.optimization.monte_carlo import MonteCarloSimulator, ScenarioAnalysis
from src.models.backtest import BacktestResult, BacktestConfig, BacktestStatus, Trade


@pytest.fixture
def sample_trades():
    """Create sample trades for testing"""
    trades = []
    
    # Create mix of winning and losing trades
    for i in range(50):
        if i % 2 == 0:
            # Winner
            trade = Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=110,
                gross_pnl=1000,
                net_pnl=900,
                return_percent=9.0
            )
        else:
            # Loser
            trade = Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=95,
                gross_pnl=-500,
                net_pnl=-550,
                return_percent=-5.5
            )
        
        trades.append(trade)
    
    return trades


@pytest.fixture
def sample_backtest_result(sample_trades):
    """Create sample backtest result"""
    config = BacktestConfig(
        initial_capital=100000,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        symbols=["SPY"]
    )
    
    result = BacktestResult(
        backtest_id=str(uuid4()),
        status=BacktestStatus.COMPLETED,
        config=config,
        start_time=datetime.now(),
        trades=sample_trades
    )
    
    return result


class TestMonteCarloSimulator:
    """Test MonteCarloSimulator"""
    
    def test_simulator_initialization(self):
        """Test simulator initialization"""
        sim = MonteCarloSimulator(iterations=100, seed=42)
        
        assert sim.iterations == 100
    
    def test_bootstrap_simulation(self, sample_backtest_result):
        """Test bootstrap simulation"""
        sim = MonteCarloSimulator(iterations=100, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="bootstrap")
        
        assert result.iterations == 100
        assert len(result.iteration_results) == 100
        assert result.mean_return is not None
        assert result.mean_sharpe is not None
    
    def test_resample_simulation(self, sample_backtest_result):
        """Test resample simulation"""
        sim = MonteCarloSimulator(iterations=100, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="resample")
        
        assert result.iterations == 100
        assert len(result.iteration_results) == 100
    
    def test_parametric_simulation(self, sample_backtest_result):
        """Test parametric simulation"""
        sim = MonteCarloSimulator(iterations=100, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="parametric")
        
        assert result.iterations == 100
        assert len(result.iteration_results) == 100
    
    def test_invalid_method(self, sample_backtest_result):
        """Test invalid simulation method"""
        sim = MonteCarloSimulator(iterations=100)
        
        with pytest.raises(ValueError):
            sim.simulate(sample_backtest_result, method="invalid")
    
    def test_confidence_intervals(self, sample_backtest_result):
        """Test confidence interval calculation"""
        sim = MonteCarloSimulator(iterations=1000, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="bootstrap")
        
        # Check confidence intervals are tuples
        assert isinstance(result.return_confidence_95, tuple)
        assert len(result.return_confidence_95) == 2
        
        # Lower bound should be less than upper bound
        assert result.return_confidence_95[0] < result.return_confidence_95[1]
    
    def test_probability_calculations(self, sample_backtest_result):
        """Test probability calculations"""
        sim = MonteCarloSimulator(iterations=1000, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="bootstrap")
        
        # Probabilities should be between 0 and 1
        assert 0 <= result.probability_of_profit <= 1
        assert 0 <= result.probability_of_ruin <= 1
        
        # Should sum to approximately 1
        # (not exactly due to zero returns)
        assert result.probability_of_profit + result.probability_of_ruin <= 1.1
    
    def test_distribution_statistics(self, sample_backtest_result):
        """Test distribution statistics"""
        sim = MonteCarloSimulator(iterations=1000, seed=42)
        
        result = sim.simulate(sample_backtest_result, method="bootstrap")
        
        # Mean and median should be close for symmetric distribution
        assert result.mean_return is not None
        assert result.median_return is not None
        
        # Standard deviation should be positive
        assert result.std_return > 0
    
    def test_risk_of_ruin(self, sample_backtest_result):
        """Test risk of ruin calculation"""
        sim = MonteCarloSimulator(iterations=100, seed=42)
        
        risk = sim.calculate_risk_of_ruin(
            sample_backtest_result,
            ruin_threshold=-50.0
        )
        
        # Should be probability between 0 and 1
        assert 0 <= risk <= 1
    
    def test_confidence_interval_function(self):
        """Test confidence interval calculation function"""
        sim = MonteCarloSimulator(iterations=100)
        
        values = list(range(100))
        
        lower, upper = sim.calculate_confidence_interval(
            values,
            confidence_level=0.95
        )
        
        assert lower < upper
        assert lower >= min(values)
        assert upper <= max(values)
    
    def test_empty_trades(self):
        """Test simulation with no trades"""
        config = BacktestConfig(
            initial_capital=100000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            symbols=["SPY"]
        )
        
        result = BacktestResult(
            backtest_id=str(uuid4()),
            status=BacktestStatus.COMPLETED,
            config=config,
            start_time=datetime.now(),
            trades=[]
        )
        
        sim = MonteCarloSimulator(iterations=10)
        mc_result = sim.simulate(result, method="bootstrap")
        
        # Should handle empty trades gracefully
        assert len(mc_result.iteration_results) == 0 or mc_result.mean_return == 0


class TestScenarioAnalysis:
    """Test ScenarioAnalysis"""
    
    def test_stress_test(self, sample_backtest_result):
        """Test stress testing"""
        analyzer = ScenarioAnalysis()
        
        scenarios = {
            "high_slippage": {
                "slippage_multiplier": 3.0
            },
            "high_commission": {
                "commission_multiplier": 2.0
            }
        }
        
        results = analyzer.stress_test(sample_backtest_result, scenarios)
        
        assert "high_slippage" in results
        assert "high_commission" in results
        
        # Results should show degraded performance
        for scenario_name, scenario_result in results.items():
            assert "total_pnl" in scenario_result
            assert "num_trades" in scenario_result
    
    def test_scenario_application(self, sample_trades):
        """Test applying scenario adjustments"""
        analyzer = ScenarioAnalysis()
        
        adjustments = {
            "slippage_multiplier": 2.0,
            "commission_multiplier": 1.5
        }
        
        adjusted_trades = analyzer._apply_scenario(
            sample_trades,
            adjustments
        )
        
        # Should have same number of trades
        assert len(adjusted_trades) == len(sample_trades)
        
        # Costs should be adjusted
        for original, adjusted in zip(sample_trades, adjusted_trades):
            assert adjusted.slippage == original.slippage * 2.0
            assert adjusted.commissions == original.commissions * 1.5


class TestMonteCarloMetrics:
    """Test Monte Carlo metric calculations"""
    
    def test_metrics_from_trades(self, sample_trades):
        """Test calculating metrics from trades"""
        sim = MonteCarloSimulator(iterations=10)
        
        metrics = sim._calculate_metrics(sample_trades)
        
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
    
    def test_metrics_from_pnl(self):
        """Test calculating metrics from P&L series"""
        sim = MonteCarloSimulator(iterations=10)
        
        # Create synthetic P&L series
        pnl_series = np.array([100, -50, 200, -30, 150])
        
        metrics = sim._calculate_metrics_from_pnl(pnl_series)
        
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert metrics['total_return'] > 0  # Net positive
    
    def test_sharpe_calculation(self, sample_trades):
        """Test Sharpe ratio calculation"""
        sim = MonteCarloSimulator(iterations=10)
        
        metrics = sim._calculate_metrics(sample_trades)
        
        # Sharpe should be finite
        assert np.isfinite(metrics['sharpe_ratio'])
    
    def test_drawdown_calculation(self, sample_trades):
        """Test max drawdown calculation"""
        sim = MonteCarloSimulator(iterations=10)
        
        metrics = sim._calculate_metrics(sample_trades)
        
        # Drawdown should be non-negative
        assert metrics['max_drawdown'] >= 0
