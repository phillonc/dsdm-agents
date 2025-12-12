"""
Unit tests for Option model
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.option import Option, OptionType, OptionPosition


class TestOption:
    """Test cases for Option model"""
    
    @pytest.fixture
    def valid_call_option(self):
        """Create a valid call option for testing"""
        return Option(
            symbol="AAPL231215C150",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=Decimal('150.00'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.50'),
            underlying_price=Decimal('155.00'),
            implied_volatility=Decimal('0.25')
        )
    
    @pytest.fixture
    def valid_put_option(self):
        """Create a valid put option for testing"""
        return Option(
            symbol="AAPL231215P150",
            underlying_symbol="AAPL",
            option_type=OptionType.PUT,
            strike_price=Decimal('150.00'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=2,
            position=OptionPosition.SHORT,
            premium=Decimal('3.25'),
            underlying_price=Decimal('145.00'),
            implied_volatility=Decimal('0.30')
        )
    
    def test_option_creation(self, valid_call_option):
        """Test successful option creation"""
        assert valid_call_option.symbol == "AAPL231215C150"
        assert valid_call_option.option_type == OptionType.CALL
        assert valid_call_option.strike_price == Decimal('150.00')
        assert valid_call_option.quantity == 1
    
    def test_invalid_quantity(self):
        """Test that negative quantity raises error"""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Option(
                symbol="TEST",
                underlying_symbol="TEST",
                option_type=OptionType.CALL,
                strike_price=Decimal('100'),
                expiration_date=datetime.utcnow() + timedelta(days=30),
                quantity=0,
                position=OptionPosition.LONG,
                premium=Decimal('5.00')
            )
    
    def test_invalid_strike_price(self):
        """Test that negative strike price raises error"""
        with pytest.raises(ValueError, match="Strike price must be positive"):
            Option(
                symbol="TEST",
                underlying_symbol="TEST",
                option_type=OptionType.CALL,
                strike_price=Decimal('-100'),
                expiration_date=datetime.utcnow() + timedelta(days=30),
                quantity=1,
                position=OptionPosition.LONG,
                premium=Decimal('5.00')
            )
    
    def test_invalid_expiration(self):
        """Test that past expiration date raises error"""
        with pytest.raises(ValueError, match="Expiration date must be in the future"):
            Option(
                symbol="TEST",
                underlying_symbol="TEST",
                option_type=OptionType.CALL,
                strike_price=Decimal('100'),
                expiration_date=datetime.utcnow() - timedelta(days=1),
                quantity=1,
                position=OptionPosition.LONG,
                premium=Decimal('5.00')
            )
    
    def test_total_premium_long(self, valid_call_option):
        """Test total premium calculation for long position"""
        # Long position: pays premium (negative cash flow)
        expected = -Decimal('5.50') * 1 * Decimal('100')
        assert valid_call_option.total_premium == expected
    
    def test_total_premium_short(self, valid_put_option):
        """Test total premium calculation for short position"""
        # Short position: receives premium (positive cash flow)
        expected = Decimal('3.25') * 2 * Decimal('100')
        assert valid_put_option.total_premium == expected
    
    def test_intrinsic_value_itm_call(self, valid_call_option):
        """Test intrinsic value for in-the-money call"""
        # Strike 150, Underlying 155 -> Intrinsic = 5
        assert valid_call_option.intrinsic_value() == Decimal('5.00')
    
    def test_intrinsic_value_otm_call(self):
        """Test intrinsic value for out-of-the-money call"""
        option = Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('160'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('2.00'),
            underlying_price=Decimal('155')
        )
        assert option.intrinsic_value() == Decimal('0')
    
    def test_intrinsic_value_itm_put(self, valid_put_option):
        """Test intrinsic value for in-the-money put"""
        # Strike 150, Underlying 145 -> Intrinsic = 5
        assert valid_put_option.intrinsic_value() == Decimal('5.00')
    
    def test_time_value(self, valid_call_option):
        """Test time value calculation"""
        # Premium 5.50, Intrinsic 5.00 -> Time Value = 0.50
        assert valid_call_option.time_value() == Decimal('0.50')
    
    def test_is_in_the_money_call(self, valid_call_option):
        """Test ITM check for call"""
        assert valid_call_option.is_in_the_money() is True
    
    def test_is_in_the_money_put(self, valid_put_option):
        """Test ITM check for put"""
        assert valid_put_option.is_in_the_money() is True
    
    def test_is_at_the_money(self):
        """Test ATM check"""
        option = Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('150.00'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('150.00')
        )
        assert option.is_at_the_money() is True
    
    def test_days_to_expiration(self, valid_call_option):
        """Test days to expiration calculation"""
        days = valid_call_option.days_to_expiration
        assert days >= 29 and days <= 31  # Allow for timing differences
    
    def test_time_to_expiration(self, valid_call_option):
        """Test time to expiration in years"""
        time_years = valid_call_option.time_to_expiration
        expected = Decimal(str(valid_call_option.days_to_expiration / 365.0))
        assert abs(time_years - expected) < Decimal('0.01')
    
    def test_to_dict(self, valid_call_option):
        """Test conversion to dictionary"""
        option_dict = valid_call_option.to_dict()
        
        assert option_dict['symbol'] == "AAPL231215C150"
        assert option_dict['option_type'] == "CALL"
        assert option_dict['strike_price'] == 150.00
        assert option_dict['quantity'] == 1
        assert option_dict['position'] == "LONG"
        assert 'intrinsic_value' in option_dict
        assert 'time_value' in option_dict


class TestOptionEdgeCases:
    """Test edge cases for Option model"""
    
    def test_zero_premium(self):
        """Test option with zero premium"""
        option = Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('0')
        )
        assert option.total_premium == Decimal('0')
    
    def test_no_underlying_price(self):
        """Test option without underlying price"""
        option = Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        assert option.intrinsic_value() == Decimal('0')
        assert option.is_in_the_money() is False
    
    def test_large_quantity(self):
        """Test option with large quantity"""
        option = Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1000,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        expected = -Decimal('5.00') * 1000 * Decimal('100')
        assert option.total_premium == expected
