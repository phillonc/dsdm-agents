"""
Unit tests for calculator modules
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import math

from src.models.option import Option, OptionType, OptionPosition
from src.models.strategy import Strategy
from src.calculators.black_scholes import BlackScholesCalculator
from src.calculators.greeks_calculator import GreeksCalculator
from src.calculators.pnl_calculator import PnLCalculator
from src.calculators.risk_calculator import RiskCalculator


class TestBlackScholesCalculator:
    """Test Black-Scholes option pricing"""
    
    def test_call_option_pricing(self):
        """Test call option price calculation"""
        price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('100'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            volatility=Decimal('0.20'),
            option_type=OptionType.CALL
        )
        
        # ATM call should have positive value
        assert price > Decimal('0')
        assert price < Decimal('10')  # Reasonable bounds
    
    def test_put_option_pricing(self):
        """Test put option price calculation"""
        price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('100'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            volatility=Decimal('0.20'),
            option_type=OptionType.PUT
        )
        
        # ATM put should have positive value
        assert price > Decimal('0')
        assert price < Decimal('10')  # Reasonable bounds
    
    def test_expired_option(self):
        """Test pricing of expired option"""
        # ITM call at expiration should equal intrinsic value
        price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('110'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0'),
            risk_free_rate=Decimal('0.05'),
            volatility=Decimal('0.20'),
            option_type=OptionType.CALL
        )
        
        assert price == Decimal('10')
    
    def test_deep_itm_call(self):
        """Test deep in-the-money call pricing"""
        price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('120'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            volatility=Decimal('0.20'),
            option_type=OptionType.CALL
        )
        
        # Should be worth at least intrinsic value
        assert price >= Decimal('20')
    
    def test_deep_otm_put(self):
        """Test deep out-of-the-money put pricing"""
        price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('120'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            volatility=Decimal('0.20'),
            option_type=OptionType.PUT
        )
        
        # Should be near zero
        assert price < Decimal('1')
    
    def test_implied_volatility_calculation(self):
        """Test implied volatility calculation"""
        # First calculate a price with known IV
        known_iv = Decimal('0.25')
        option_price = BlackScholesCalculator.calculate_option_price(
            spot_price=Decimal('100'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            volatility=known_iv,
            option_type=OptionType.CALL
        )
        
        # Now calculate IV from price
        calculated_iv = BlackScholesCalculator.calculate_implied_volatility(
            option_price=option_price,
            spot_price=Decimal('100'),
            strike_price=Decimal('100'),
            time_to_expiration=Decimal('0.25'),
            risk_free_rate=Decimal('0.05'),
            option_type=OptionType.CALL
        )
        
        # Should be close to original IV
        assert abs(calculated_iv - known_iv) < Decimal('0.01')


class TestGreeksCalculator:
    """Test Greeks calculations"""
    
    @pytest.fixture
    def atm_call_option(self):
        """Create an ATM call option"""
        return Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
    
    def test_delta_calculation(self, atm_call_option):
        """Test delta calculation"""
        greeks = GreeksCalculator.calculate_option_greeks(atm_call_option)
        
        # ATM call delta should be around 0.5 (per share)
        delta_per_share = greeks.delta / Decimal('100')
        assert abs(delta_per_share - Decimal('0.5')) < Decimal('0.2')
    
    def test_gamma_positive(self, atm_call_option):
        """Test that gamma is positive for long options"""
        greeks = GreeksCalculator.calculate_option_greeks(atm_call_option)
        
        assert greeks.gamma > Decimal('0')
    
    def test_theta_negative_long(self, atm_call_option):
        """Test that theta is negative for long options"""
        greeks = GreeksCalculator.calculate_option_greeks(atm_call_option)
        
        # Long options lose value over time
        assert greeks.theta < Decimal('0')
    
    def test_vega_positive_long(self, atm_call_option):
        """Test that vega is positive for long options"""
        greeks = GreeksCalculator.calculate_option_greeks(atm_call_option)
        
        # Long options benefit from increased volatility
        assert greeks.vega > Decimal('0')
    
    def test_short_option_greeks(self):
        """Test Greeks for short position"""
        option = Option(
            symbol="TEST_P100",
            underlying_symbol="TEST",
            option_type=OptionType.PUT,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.SHORT,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        
        greeks = GreeksCalculator.calculate_option_greeks(option)
        
        # Short position should have opposite signs
        assert greeks.gamma < Decimal('0')  # Short gamma
        assert greeks.theta > Decimal('0')  # Positive theta (time decay benefit)
        assert greeks.vega < Decimal('0')   # Short vega
    
    def test_strategy_greeks_aggregation(self):
        """Test Greeks aggregation for a strategy"""
        strategy = Strategy(name="Test Strategy")
        
        # Add a long call
        call = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(call)
        
        # Add a short put
        put = Option(
            symbol="TEST_P100",
            underlying_symbol="TEST",
            option_type=OptionType.PUT,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.SHORT,
            premium=Decimal('4.50'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(put)
        
        greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
        
        # Should aggregate both legs
        assert greeks.total_delta != Decimal('0')
        assert 'risk_profile' in greeks.to_dict()


class TestPnLCalculator:
    """Test P&L calculations"""
    
    @pytest.fixture
    def long_call(self):
        """Create a long call option"""
        return Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
    
    def test_pnl_at_expiration_itm(self, long_call):
        """Test P&L at expiration for ITM option"""
        # Call with strike 100, underlying at 110
        pnl = PnLCalculator.calculate_option_pnl_at_expiration(
            long_call,
            Decimal('110')
        )
        
        # Intrinsic value 10, paid 5 -> profit 5 per share * 100
        expected = (Decimal('10') - Decimal('5')) * Decimal('100')
        assert pnl == expected
    
    def test_pnl_at_expiration_otm(self, long_call):
        """Test P&L at expiration for OTM option"""
        # Call with strike 100, underlying at 95
        pnl = PnLCalculator.calculate_option_pnl_at_expiration(
            long_call,
            Decimal('95')
        )
        
        # Expires worthless, lose full premium
        expected = -Decimal('5.00') * Decimal('100')
        assert pnl == expected
    
    def test_payoff_diagram_generation(self):
        """Test payoff diagram data generation"""
        strategy = Strategy(name="Test")
        
        option = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(option)
        
        payoff = PnLCalculator.calculate_payoff_diagram(strategy)
        
        assert 'prices' in payoff
        assert 'pnl' in payoff
        assert 'breakeven_points' in payoff
        assert len(payoff['prices']) == len(payoff['pnl'])
    
    def test_max_profit_calculation(self):
        """Test max profit calculation"""
        strategy = Strategy(name="Test")
        
        # Long call has unlimited profit potential
        option = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(option)
        
        max_profit, price_at_max = PnLCalculator.calculate_max_profit(strategy)
        
        # Max profit should be at highest price in range
        assert max_profit > Decimal('0')
    
    def test_max_loss_calculation(self):
        """Test max loss calculation"""
        strategy = Strategy(name="Test")
        
        # Long call has limited loss (premium paid)
        option = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(option)
        
        max_loss, price_at_max_loss = PnLCalculator.calculate_max_loss(strategy)
        
        # Max loss should be premium paid
        expected = -Decimal('5.00') * Decimal('100')
        assert abs(max_loss - expected) < Decimal('10')  # Allow small variance
    
    def test_risk_reward_ratio(self):
        """Test risk/reward ratio calculation"""
        strategy = Strategy(name="Test")
        
        option = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(option)
        
        metrics = PnLCalculator.calculate_risk_reward_ratio(strategy)
        
        assert 'max_profit' in metrics
        assert 'max_loss' in metrics
        assert 'risk_reward_ratio' in metrics
        assert metrics['max_loss'] <= Decimal('0')


class TestRiskCalculator:
    """Test risk calculations"""
    
    @pytest.fixture
    def simple_strategy(self):
        """Create a simple strategy for testing"""
        strategy = Strategy(name="Test Strategy")
        
        option = Option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=90),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('100'),
            implied_volatility=Decimal('0.25')
        )
        strategy.add_leg(option)
        
        return strategy
    
    def test_value_at_risk(self, simple_strategy):
        """Test VaR calculation"""
        var_metrics = RiskCalculator.calculate_value_at_risk(simple_strategy)
        
        assert 'value_at_risk' in var_metrics
        assert 'confidence_level' in var_metrics
        assert var_metrics['value_at_risk'] > Decimal('0')
    
    def test_probability_of_profit(self, simple_strategy):
        """Test probability of profit calculation"""
        pop_metrics = RiskCalculator.calculate_probability_of_profit(
            simple_strategy,
            num_simulations=100  # Use fewer simulations for speed
        )
        
        assert 'probability_of_profit' in pop_metrics
        assert Decimal('0') <= pop_metrics['probability_of_profit'] <= Decimal('1')
    
    def test_scenario_analysis(self, simple_strategy):
        """Test scenario analysis"""
        scenario = RiskCalculator.analyze_scenario(
            simple_strategy,
            scenario_price=Decimal('110'),
            volatility_change=Decimal('0.05')
        )
        
        assert 'scenario_price' in scenario
        assert 'current_pnl' in scenario
        assert 'greeks' in scenario
    
    def test_margin_requirement(self, simple_strategy):
        """Test margin requirement calculation"""
        margin = RiskCalculator.calculate_margin_requirement(simple_strategy)
        
        assert 'estimated_margin' in margin
        assert 'strategy_cost' in margin
        assert margin['estimated_margin'] >= Decimal('0')
    
    def test_comprehensive_risk_metrics(self, simple_strategy):
        """Test comprehensive risk metrics"""
        metrics = RiskCalculator.calculate_risk_metrics(simple_strategy)
        
        assert 'risk_reward' in metrics
        assert 'value_at_risk' in metrics
        assert 'probability_metrics' in metrics
        assert 'greeks' in metrics
