"""
Unit tests for strategy templates.
"""

import pytest
from datetime import date, timedelta
from src.strategy_templates import StrategyTemplates
from src.models import StrategyType, OptionType, PositionType


class TestStrategyTemplates:
    """Test strategy template creation."""
    
    def test_create_iron_condor(self):
        """Test Iron Condor template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_iron_condor(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            wing_width=5.0,
            body_width=10.0,
            quantity=1
        )
        
        assert strategy.strategy_type == StrategyType.IRON_CONDOR
        assert strategy.underlying_symbol == "SPY"
        assert len(strategy.legs) == 4
        
        # Check leg configuration
        put_legs = [leg for leg in strategy.legs if leg.option_type == OptionType.PUT]
        call_legs = [leg for leg in strategy.legs if leg.option_type == OptionType.CALL]
        
        assert len(put_legs) == 2
        assert len(call_legs) == 2
    
    def test_create_butterfly(self):
        """Test Butterfly template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_butterfly(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            wing_width=5.0,
            quantity=1,
            option_type=OptionType.CALL
        )
        
        assert strategy.strategy_type == StrategyType.BUTTERFLY
        assert len(strategy.legs) == 3
        
        # Check strikes are properly spaced
        strikes = sorted([leg.strike for leg in strategy.legs])
        assert strikes[1] - strikes[0] == pytest.approx(5.0, rel=1e-5)
        assert strikes[2] - strikes[1] == pytest.approx(5.0, rel=1e-5)
        
        # Check quantities (1-2-1 pattern)
        quantities = [leg.quantity for leg in sorted(strategy.legs, key=lambda x: x.strike)]
        assert quantities[1] == 2  # Middle leg should have 2 contracts
    
    def test_create_straddle_long(self):
        """Test Long Straddle template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=450.0,
            expiration=expiration,
            quantity=1,
            position_type=PositionType.LONG
        )
        
        assert strategy.strategy_type == StrategyType.STRADDLE
        assert len(strategy.legs) == 2
        
        # Check both legs are at same strike
        strikes = [leg.strike for leg in strategy.legs]
        assert all(strike == 450.0 for strike in strikes)
        
        # Check one call and one put
        option_types = [leg.option_type for leg in strategy.legs]
        assert OptionType.CALL in option_types
        assert OptionType.PUT in option_types
        
        # Check both are long
        assert all(leg.position_type == PositionType.LONG for leg in strategy.legs)
    
    def test_create_straddle_short(self):
        """Test Short Straddle template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=450.0,
            expiration=expiration,
            quantity=1,
            position_type=PositionType.SHORT
        )
        
        assert strategy.strategy_type == StrategyType.STRADDLE
        # Check both are short
        assert all(leg.position_type == PositionType.SHORT for leg in strategy.legs)
    
    def test_create_strangle(self):
        """Test Strangle template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_strangle(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            strike_distance=5.0,
            quantity=1,
            position_type=PositionType.LONG
        )
        
        assert strategy.strategy_type == StrategyType.STRANGLE
        assert len(strategy.legs) == 2
        
        # Check strikes are different
        strikes = [leg.strike for leg in strategy.legs]
        assert len(set(strikes)) == 2
        
        # Check one call and one put
        option_types = [leg.option_type for leg in strategy.legs]
        assert OptionType.CALL in option_types
        assert OptionType.PUT in option_types
    
    def test_create_vertical_spread_bull_call(self):
        """Test Bull Call Spread template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_vertical_spread(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            spread_width=5.0,
            quantity=1,
            option_type=OptionType.CALL,
            is_debit=True
        )
        
        assert strategy.strategy_type == StrategyType.VERTICAL_SPREAD
        assert "Bull Call" in strategy.name
        assert len(strategy.legs) == 2
        
        # Check both are calls
        assert all(leg.option_type == OptionType.CALL for leg in strategy.legs)
        
        # Check one long, one short
        position_types = [leg.position_type for leg in strategy.legs]
        assert PositionType.LONG in position_types
        assert PositionType.SHORT in position_types
    
    def test_create_vertical_spread_bear_put(self):
        """Test Bear Put Spread template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_vertical_spread(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            spread_width=5.0,
            quantity=1,
            option_type=OptionType.PUT,
            is_debit=True
        )
        
        assert strategy.strategy_type == StrategyType.VERTICAL_SPREAD
        assert "Bear Put" in strategy.name
        assert len(strategy.legs) == 2
        
        # Check both are puts
        assert all(leg.option_type == OptionType.PUT for leg in strategy.legs)
    
    def test_create_covered_call(self):
        """Test Covered Call template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_covered_call(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            call_strike=455.0,
            quantity=1
        )
        
        assert strategy.strategy_type == StrategyType.COVERED_CALL
        assert len(strategy.legs) == 1
        
        # Check it's a short call
        leg = strategy.legs[0]
        assert leg.option_type == OptionType.CALL
        assert leg.position_type == PositionType.SHORT
    
    def test_create_protective_put(self):
        """Test Protective Put template creation."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_protective_put(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            put_strike=445.0,
            quantity=1
        )
        
        assert strategy.strategy_type == StrategyType.PROTECTIVE_PUT
        assert len(strategy.legs) == 1
        
        # Check it's a long put
        leg = strategy.legs[0]
        assert leg.option_type == OptionType.PUT
        assert leg.position_type == PositionType.LONG
    
    def test_template_with_custom_quantity(self):
        """Test template creation with custom quantity."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_straddle(
            underlying_symbol="SPY",
            strike=450.0,
            expiration=expiration,
            quantity=5
        )
        
        # Check all legs have correct quantity
        assert all(leg.quantity == 5 for leg in strategy.legs)
    
    def test_template_greeks_present(self):
        """Test that templates include Greeks."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_iron_condor(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration
        )
        
        # Check all legs have Greeks
        for leg in strategy.legs:
            assert leg.greeks is not None
            assert hasattr(leg.greeks, 'delta')
            assert hasattr(leg.greeks, 'gamma')
            assert hasattr(leg.greeks, 'theta')
            assert hasattr(leg.greeks, 'vega')
    
    def test_template_cost_calculation(self):
        """Test that templates have proper cost calculations."""
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_iron_condor(
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration
        )
        
        total_cost = strategy.get_total_cost()
        # Iron condor should typically be a credit (positive)
        assert isinstance(total_cost, float)
