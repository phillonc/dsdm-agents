"""
Unit tests for scenario analyzer.
"""

import pytest
from datetime import date, timedelta
from src.scenario_analyzer import ScenarioEngine, ScenarioComparator
from src.models import OptionsStrategy, OptionLeg, OptionType, PositionType, Greeks
from src.strategy_templates import StrategyTemplates


class TestScenarioEngine:
    """Test the ScenarioEngine class."""
    
    def setup_method(self):
        """Set up test strategy."""
        self.strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        self.strategy.add_leg(leg)
    
    def test_analyze_price_change(self):
        """Test price change analysis."""
        results = ScenarioEngine.analyze_price_change(
            strategy=self.strategy,
            current_price=100.0,
            price_changes=[-10, -5, 0, 5, 10]
        )
        
        assert len(results) == 5
        
        for result in results:
            assert 'price_change_percent' in result
            assert 'new_price' in result
            assert 'pnl' in result
            assert 'pnl_change' in result
            assert 'return_percent' in result
    
    def test_analyze_price_change_positive_move(self):
        """Test price increase scenario."""
        results = ScenarioEngine.analyze_price_change(
            strategy=self.strategy,
            current_price=100.0,
            price_changes=[10]
        )
        
        result = results[0]
        assert result['price_change_percent'] == 10
        assert result['new_price'] == 110.0
        # Long call at 100 with 5 premium, at 110 should profit
        assert result['pnl'] > 0
    
    def test_analyze_volatility_change(self):
        """Test volatility change analysis."""
        results = ScenarioEngine.analyze_volatility_change(
            strategy=self.strategy,
            volatility_changes=[-10, -5, 0, 5, 10]
        )
        
        assert len(results) == 5
        
        for result in results:
            assert 'volatility_change_percent' in result
            assert 'estimated_pnl_impact' in result
            assert 'total_vega' in result
            assert 'description' in result
    
    def test_analyze_volatility_increase(self):
        """Test volatility increase impact."""
        results = ScenarioEngine.analyze_volatility_change(
            strategy=self.strategy,
            volatility_changes=[10]
        )
        
        result = results[0]
        # Long call has positive vega, so vol increase is positive
        assert result['estimated_pnl_impact'] > 0
    
    def test_analyze_time_decay(self):
        """Test time decay analysis."""
        results = ScenarioEngine.analyze_time_decay(
            strategy=self.strategy,
            days_forward=[1, 7, 14, 30]
        )
        
        assert len(results) == 4
        
        for result in results:
            assert 'days_forward' in result
            assert 'estimated_pnl_impact' in result
            assert 'total_theta' in result
            assert 'description' in result
    
    def test_analyze_time_decay_long_option(self):
        """Test time decay for long option (negative theta)."""
        results = ScenarioEngine.analyze_time_decay(
            strategy=self.strategy,
            days_forward=[7]
        )
        
        result = results[0]
        # Long option has negative theta, so time passing hurts
        assert result['estimated_pnl_impact'] < 0
    
    def test_analyze_combined_scenario(self):
        """Test combined scenario analysis."""
        result = ScenarioEngine.analyze_combined_scenario(
            strategy=self.strategy,
            current_price=100.0,
            price_change_pct=5,
            volatility_change_pct=10,
            days_forward=7
        )
        
        assert 'price_change_percent' in result
        assert 'new_price' in result
        assert 'volatility_change_percent' in result
        assert 'days_forward' in result
        assert 'price_pnl' in result
        assert 'vega_impact' in result
        assert 'theta_impact' in result
        assert 'estimated_total_pnl' in result
        assert 'greeks_used' in result
        
        assert result['new_price'] == 105.0
        assert result['days_forward'] == 7
    
    def test_stress_test(self):
        """Test stress testing."""
        results = ScenarioEngine.stress_test(
            strategy=self.strategy,
            current_price=100.0
        )
        
        assert 'market_crash' in results
        assert 'market_rally' in results
        assert 'volatility_spike' in results
        assert 'volatility_crush' in results
        
        # Check each scenario has required fields
        for scenario_name, scenario_data in results.items():
            assert 'description' in scenario_data
            assert 'estimated_total_pnl' in scenario_data
            assert 'price_pnl' in scenario_data
    
    def test_stress_test_market_crash(self):
        """Test market crash scenario."""
        results = ScenarioEngine.stress_test(
            strategy=self.strategy,
            current_price=100.0
        )
        
        crash = results['market_crash']
        # Long call in market crash should lose money
        assert crash['price_pnl'] < 0
    
    def test_sensitivity_analysis(self):
        """Test comprehensive sensitivity analysis."""
        results = ScenarioEngine.sensitivity_analysis(
            strategy=self.strategy,
            current_price=100.0
        )
        
        assert 'current_greeks' in results
        assert 'delta_sensitivity' in results
        assert 'vega_sensitivity' in results
        assert 'theta_sensitivity' in results
        assert 'interpretation' in results
        
        # Check delta sensitivity scenarios
        assert len(results['delta_sensitivity']) > 0
        for scenario in results['delta_sensitivity']:
            assert 'price_change_percent' in scenario
            assert 'estimated_pnl' in scenario
        
        # Check vega sensitivity scenarios
        assert len(results['vega_sensitivity']) > 0
        for scenario in results['vega_sensitivity']:
            assert 'volatility_change_percent' in scenario
            assert 'estimated_pnl' in scenario
        
        # Check theta sensitivity scenarios
        assert len(results['theta_sensitivity']) > 0
        for scenario in results['theta_sensitivity']:
            assert 'days_forward' in scenario
            assert 'estimated_pnl' in scenario


class TestScenarioComparator:
    """Test the ScenarioComparator class."""
    
    def test_compare_strategies(self):
        """Test comparing multiple strategies."""
        expiration = date.today() + timedelta(days=30)
        
        # Create two different strategies
        strategy1 = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=100.0,
            expiration=expiration,
            quantity=1,
            position_type=PositionType.LONG
        )
        
        strategy2 = StrategyTemplates.create_strangle(
            underlying_symbol="SPY",
            current_price=100.0,
            expiration=expiration,
            strike_distance=5.0,
            quantity=1,
            position_type=PositionType.LONG
        )
        
        scenario_params = {
            'price_change_pct': 10,
            'volatility_change_pct': 0,
            'days_forward': 0
        }
        
        comparison = ScenarioComparator.compare_strategies(
            strategies=[strategy1, strategy2],
            current_price=100.0,
            scenario_params=scenario_params
        )
        
        assert 'scenario_params' in comparison
        assert 'num_strategies' in comparison
        assert 'results' in comparison
        assert 'best_performer' in comparison
        assert 'worst_performer' in comparison
        
        assert comparison['num_strategies'] == 2
        assert len(comparison['results']) == 2
    
    def test_compare_strategies_ranking(self):
        """Test that strategies are ranked by performance."""
        expiration = date.today() + timedelta(days=30)
        
        strategy1 = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=100.0,
            expiration=expiration,
            quantity=1,
            position_type=PositionType.LONG
        )
        
        strategy2 = StrategyTemplates.create_iron_condor(
            underlying_symbol="SPY",
            current_price=100.0,
            expiration=expiration
        )
        
        scenario_params = {
            'price_change_pct': 15,  # Large move favors straddle
            'volatility_change_pct': 0,
            'days_forward': 0
        }
        
        comparison = ScenarioComparator.compare_strategies(
            strategies=[strategy1, strategy2],
            current_price=100.0,
            scenario_params=scenario_params
        )
        
        # Results should be sorted by P&L
        results = comparison['results']
        for i in range(len(results) - 1):
            current_pnl = results[i]['scenario_result']['estimated_total_pnl']
            next_pnl = results[i + 1]['scenario_result']['estimated_total_pnl']
            assert current_pnl >= next_pnl
    
    def test_compare_single_strategy(self):
        """Test comparison with single strategy."""
        expiration = date.today() + timedelta(days=30)
        
        strategy = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=100.0,
            expiration=expiration
        )
        
        scenario_params = {
            'price_change_pct': 0,
            'volatility_change_pct': 0,
            'days_forward': 0
        }
        
        comparison = ScenarioComparator.compare_strategies(
            strategies=[strategy],
            current_price=100.0,
            scenario_params=scenario_params
        )
        
        assert comparison['num_strategies'] == 1
        assert comparison['best_performer'] == comparison['worst_performer']
    
    def test_compare_strategies_result_structure(self):
        """Test structure of comparison results."""
        expiration = date.today() + timedelta(days=30)
        
        strategy = StrategyTemplates.create_butterfly(
            underlying_symbol="SPY",
            current_price=100.0,
            expiration=expiration
        )
        
        scenario_params = {
            'price_change_pct': 2,
            'volatility_change_pct': 5,
            'days_forward': 7
        }
        
        comparison = ScenarioComparator.compare_strategies(
            strategies=[strategy],
            current_price=100.0,
            scenario_params=scenario_params
        )
        
        result = comparison['results'][0]
        assert 'strategy_id' in result
        assert 'strategy_name' in result
        assert 'strategy_type' in result
        assert 'scenario_result' in result
        assert 'initial_cost' in result
        assert 'num_legs' in result
