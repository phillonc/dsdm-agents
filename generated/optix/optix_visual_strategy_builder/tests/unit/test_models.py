"""
Unit tests for data models.
"""

import pytest
from datetime import date, datetime, timedelta
from src.models import (
    Greeks, OptionLeg, OptionsStrategy, OptionType, 
    PositionType, StrategyType, ScenarioAnalysis
)


class TestGreeks:
    """Test the Greeks class."""
    
    def test_greeks_initialization(self):
        """Test Greeks initialization."""
        greeks = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        assert greeks.delta == 0.5
        assert greeks.gamma == 0.02
        assert greeks.theta == -0.05
        assert greeks.vega == 0.15
        assert greeks.rho == 0.03
    
    def test_greeks_addition(self):
        """Test Greeks addition."""
        greeks1 = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        greeks2 = Greeks(delta=-0.3, gamma=0.01, theta=-0.03, vega=0.10, rho=-0.02)
        result = greeks1 + greeks2
        
        assert result.delta == 0.2
        assert result.gamma == 0.03
        assert result.theta == -0.08
        assert result.vega == 0.25
        assert result.rho == 0.01
    
    def test_greeks_multiplication(self):
        """Test Greeks multiplication by scalar."""
        greeks = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        result = greeks * 2
        
        assert result.delta == 1.0
        assert result.gamma == 0.04
        assert result.theta == -0.10
        assert result.vega == 0.30
        assert result.rho == 0.06
    
    def test_greeks_to_dict(self):
        """Test Greeks to dictionary conversion."""
        greeks = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        result = greeks.to_dict()
        
        assert isinstance(result, dict)
        assert result['delta'] == 0.5
        assert 'gamma' in result
        assert 'theta' in result


class TestOptionLeg:
    """Test the OptionLeg class."""
    
    def test_option_leg_initialization(self):
        """Test OptionLeg initialization."""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date(2024, 12, 31),
            quantity=1,
            premium=5.0,
            underlying_symbol="SPY"
        )
        
        assert leg.option_type == OptionType.CALL
        assert leg.position_type == PositionType.LONG
        assert leg.strike == 100.0
        assert leg.quantity == 1
        assert leg.premium == 5.0
    
    def test_get_cost_long(self):
        """Test cost calculation for long position."""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        cost = leg.get_cost()
        assert cost == -500.0  # Long is a debit (negative)
    
    def test_get_cost_short(self):
        """Test cost calculation for short position."""
        leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.SHORT,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=3.0
        )
        
        cost = leg.get_cost()
        assert cost == 300.0  # Short is a credit (positive)
    
    def test_calculate_pnl_call_long_itm(self):
        """Test P&L for long call ITM."""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        pnl = leg.calculate_pnl(110.0)  # $10 ITM
        # Intrinsic value: $10 * 100 = $1000
        # Cost: $500
        # P&L: $1000 - $500 = $500
        assert pnl == 500.0
    
    def test_calculate_pnl_call_long_otm(self):
        """Test P&L for long call OTM."""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        pnl = leg.calculate_pnl(95.0)  # OTM
        # Intrinsic value: $0
        # Cost: $500
        # P&L: $0 - $500 = -$500
        assert pnl == -500.0
    
    def test_calculate_pnl_put_short(self):
        """Test P&L for short put."""
        leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.SHORT,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=3.0
        )
        
        pnl = leg.calculate_pnl(105.0)  # OTM for put
        # Intrinsic value: $0
        # Credit: $300
        # P&L: $300 - $0 = $300
        assert pnl == 300.0
    
    def test_get_position_greeks(self):
        """Test position Greeks calculation."""
        greeks = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=2,
            premium=5.0,
            greeks=greeks
        )
        
        position_greeks = leg.get_position_greeks()
        assert position_greeks.delta == 1.0  # 0.5 * 2
        assert position_greeks.gamma == 0.04
    
    def test_to_dict(self):
        """Test leg to dictionary conversion."""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date(2024, 12, 31),
            quantity=1,
            premium=5.0,
            underlying_symbol="SPY"
        )
        
        result = leg.to_dict()
        assert isinstance(result, dict)
        assert result['option_type'] == 'CALL'
        assert result['strike'] == 100.0
        assert 'greeks' in result


class TestOptionsStrategy:
    """Test the OptionsStrategy class."""
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = OptionsStrategy(
            name="Test Strategy",
            underlying_symbol="SPY",
            strategy_type=StrategyType.CUSTOM
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.underlying_symbol == "SPY"
        assert strategy.strategy_type == StrategyType.CUSTOM
        assert len(strategy.legs) == 0
    
    def test_add_leg(self):
        """Test adding a leg to a strategy."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg)
        assert len(strategy.legs) == 1
        assert strategy.legs[0] == leg
    
    def test_remove_leg(self):
        """Test removing a leg from a strategy."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg1 = OptionLeg(strike=100.0, expiration=date.today(), quantity=1, premium=5.0)
        leg2 = OptionLeg(strike=105.0, expiration=date.today(), quantity=1, premium=3.0)
        
        strategy.add_leg(leg1)
        strategy.add_leg(leg2)
        
        assert len(strategy.legs) == 2
        
        result = strategy.remove_leg(leg1.id)
        assert result is True
        assert len(strategy.legs) == 1
        assert strategy.legs[0] == leg2
    
    def test_remove_nonexistent_leg(self):
        """Test removing a nonexistent leg."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        result = strategy.remove_leg("nonexistent-id")
        assert result is False
    
    def test_get_total_cost(self):
        """Test total cost calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg1 = OptionLeg(
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        leg2 = OptionLeg(
            position_type=PositionType.SHORT,
            strike=105.0,
            expiration=date.today(),
            quantity=1,
            premium=3.0
        )
        
        strategy.add_leg(leg1)
        strategy.add_leg(leg2)
        
        total_cost = strategy.get_total_cost()
        # Long: -$500, Short: +$300
        # Total: -$200 (net debit)
        assert total_cost == -200.0
    
    def test_get_aggregated_greeks(self):
        """Test aggregated Greeks calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        greeks1 = Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        greeks2 = Greeks(delta=-0.3, gamma=0.01, theta=-0.03, vega=0.10, rho=-0.02)
        
        leg1 = OptionLeg(
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0,
            greeks=greeks1
        )
        leg2 = OptionLeg(
            strike=105.0,
            expiration=date.today(),
            quantity=1,
            premium=3.0,
            greeks=greeks2
        )
        
        strategy.add_leg(leg1)
        strategy.add_leg(leg2)
        
        total_greeks = strategy.get_aggregated_greeks()
        assert total_greeks.delta == pytest.approx(0.2, rel=1e-5)
        assert total_greeks.gamma == pytest.approx(0.03, rel=1e-5)
    
    def test_calculate_pnl(self):
        """Test P&L calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg1 = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg1)
        
        pnl = strategy.calculate_pnl(110.0)
        assert pnl == 500.0  # $10 ITM * 100 - $500 cost
    
    def test_calculate_pnl_range(self):
        """Test P&L range calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg)
        
        price_range = [95.0, 100.0, 105.0, 110.0]
        pnl_range = strategy.calculate_pnl_range(price_range)
        
        assert len(pnl_range) == 4
        assert all('price' in item and 'pnl' in item for item in pnl_range)
    
    def test_get_max_profit(self):
        """Test maximum profit calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg)
        
        price_range = [95.0, 100.0, 105.0, 110.0, 115.0]
        max_profit = strategy.get_max_profit(price_range)
        
        # Max profit at $115: ($15 * 100) - $500 = $1000
        assert max_profit == 1000.0
    
    def test_get_max_loss(self):
        """Test maximum loss calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg)
        
        price_range = [90.0, 95.0, 100.0, 105.0]
        max_loss = strategy.get_max_loss(price_range)
        
        # Max loss when OTM: -$500 (premium paid)
        assert max_loss == -500.0
    
    def test_get_breakeven_points(self):
        """Test breakeven point calculation."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        
        strategy.add_leg(leg)
        
        # Breakeven should be at $105 (strike + premium)
        price_range = [i for i in range(95, 115)]
        breakeven_points = strategy.get_breakeven_points(price_range)
        
        assert len(breakeven_points) > 0
        assert any(104 <= point <= 106 for point in breakeven_points)
    
    def test_to_dict(self):
        """Test strategy to dictionary conversion."""
        strategy = OptionsStrategy(
            name="Test Strategy",
            underlying_symbol="SPY",
            strategy_type=StrategyType.STRADDLE
        )
        
        leg = OptionLeg(
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0
        )
        strategy.add_leg(leg)
        
        result = strategy.to_dict()
        
        assert isinstance(result, dict)
        assert result['name'] == "Test Strategy"
        assert result['strategy_type'] == 'STRADDLE'
        assert len(result['legs']) == 1
        assert 'aggregated_greeks' in result


class TestScenarioAnalysis:
    """Test the ScenarioAnalysis class."""
    
    def test_scenario_initialization(self):
        """Test scenario initialization."""
        scenario = ScenarioAnalysis(
            name="Test Scenario",
            underlying_price_change=5.0,
            volatility_change=10.0,
            days_to_expiration_change=7
        )
        
        assert scenario.name == "Test Scenario"
        assert scenario.underlying_price_change == 5.0
        assert scenario.volatility_change == 10.0
        assert scenario.days_to_expiration_change == 7
    
    def test_scenario_to_dict(self):
        """Test scenario to dictionary conversion."""
        scenario = ScenarioAnalysis(
            name="Test Scenario",
            underlying_price_change=5.0,
            volatility_change=10.0,
            days_to_expiration_change=7
        )
        
        result = scenario.to_dict()
        assert isinstance(result, dict)
        assert result['name'] == "Test Scenario"
        assert 'id' in result
