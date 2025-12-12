"""
Unit tests for Strategy model
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.strategy import Strategy, StrategyTemplate, StrategyLeg
from src.models.option import Option, OptionType, OptionPosition


class TestStrategy:
    """Test cases for Strategy model"""
    
    @pytest.fixture
    def basic_strategy(self):
        """Create a basic strategy for testing"""
        return Strategy(
            name="Test Strategy",
            template=StrategyTemplate.CUSTOM,
            description="Test description"
        )
    
    @pytest.fixture
    def call_option(self):
        """Create a call option"""
        return Option(
            symbol="TEST_C150",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('150'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=Decimal('155'),
            implied_volatility=Decimal('0.25')
        )
    
    @pytest.fixture
    def put_option(self):
        """Create a put option"""
        return Option(
            symbol="TEST_P140",
            underlying_symbol="TEST",
            option_type=OptionType.PUT,
            strike_price=Decimal('140'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.SHORT,
            premium=Decimal('3.00'),
            underlying_price=Decimal('155'),
            implied_volatility=Decimal('0.25')
        )
    
    def test_strategy_creation(self, basic_strategy):
        """Test successful strategy creation"""
        assert basic_strategy.name == "Test Strategy"
        assert basic_strategy.template == StrategyTemplate.CUSTOM
        assert len(basic_strategy.legs) == 0
        assert basic_strategy.strategy_id is not None
    
    def test_add_leg(self, basic_strategy, call_option):
        """Test adding a leg to strategy"""
        leg = basic_strategy.add_leg(call_option, "Long call leg")
        
        assert len(basic_strategy.legs) == 1
        assert leg.option == call_option
        assert leg.notes == "Long call leg"
        assert leg.leg_id is not None
    
    def test_remove_leg(self, basic_strategy, call_option):
        """Test removing a leg from strategy"""
        leg = basic_strategy.add_leg(call_option)
        leg_id = leg.leg_id
        
        removed = basic_strategy.remove_leg(leg_id)
        assert removed is True
        assert len(basic_strategy.legs) == 0
    
    def test_remove_nonexistent_leg(self, basic_strategy):
        """Test removing a leg that doesn't exist"""
        removed = basic_strategy.remove_leg("nonexistent_id")
        assert removed is False
    
    def test_get_leg(self, basic_strategy, call_option):
        """Test getting a specific leg"""
        leg = basic_strategy.add_leg(call_option)
        
        retrieved_leg = basic_strategy.get_leg(leg.leg_id)
        assert retrieved_leg == leg
    
    def test_get_nonexistent_leg(self, basic_strategy):
        """Test getting a leg that doesn't exist"""
        leg = basic_strategy.get_leg("nonexistent_id")
        assert leg is None
    
    def test_total_cost_debit(self, basic_strategy, call_option):
        """Test total cost calculation for debit strategy"""
        basic_strategy.add_leg(call_option)
        
        # Long call: pays premium (negative)
        expected = -Decimal('5.00') * 1 * Decimal('100')
        assert basic_strategy.total_cost == expected
        assert basic_strategy.is_debit_strategy is True
        assert basic_strategy.is_credit_strategy is False
    
    def test_total_cost_credit(self, basic_strategy, put_option):
        """Test total cost calculation for credit strategy"""
        basic_strategy.add_leg(put_option)
        
        # Short put: receives premium (positive)
        expected = Decimal('3.00') * 1 * Decimal('100')
        assert basic_strategy.total_cost == expected
        assert basic_strategy.is_credit_strategy is True
        assert basic_strategy.is_debit_strategy is False
    
    def test_net_quantity(self, basic_strategy, call_option, put_option):
        """Test net quantity calculation"""
        basic_strategy.add_leg(call_option)  # Long 1
        basic_strategy.add_leg(put_option)   # Short 1
        
        assert basic_strategy.net_quantity == 0
    
    def test_get_underlying_symbols(self, basic_strategy, call_option):
        """Test getting underlying symbols"""
        basic_strategy.add_leg(call_option)
        
        symbols = basic_strategy.get_underlying_symbols()
        assert symbols == ["TEST"]
    
    def test_get_expiration_dates(self, basic_strategy, call_option):
        """Test getting expiration dates"""
        basic_strategy.add_leg(call_option)
        
        dates = basic_strategy.get_expiration_dates()
        assert len(dates) == 1
        assert isinstance(dates[0], datetime)
    
    def test_validate_empty_strategy(self, basic_strategy):
        """Test validation of empty strategy"""
        is_valid, errors = basic_strategy.validate()
        
        assert is_valid is False
        assert "at least one leg" in errors[0].lower()
    
    def test_validate_valid_strategy(self, basic_strategy, call_option):
        """Test validation of valid strategy"""
        basic_strategy.add_leg(call_option)
        
        is_valid, errors = basic_strategy.validate()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_multiple_underlyings(self, basic_strategy):
        """Test validation with multiple underlying symbols"""
        option1 = Option(
            symbol="AAPL_C150",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=Decimal('150'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        option2 = Option(
            symbol="GOOGL_C100",
            underlying_symbol="GOOGL",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('3.00')
        )
        
        basic_strategy.add_leg(option1)
        basic_strategy.add_leg(option2)
        
        is_valid, errors = basic_strategy.validate()
        assert is_valid is False
        assert any("multiple underlying symbols" in error.lower() for error in errors)
    
    def test_to_dict(self, basic_strategy, call_option):
        """Test conversion to dictionary"""
        basic_strategy.add_leg(call_option)
        
        strategy_dict = basic_strategy.to_dict()
        
        assert strategy_dict['name'] == "Test Strategy"
        assert strategy_dict['template'] == "CUSTOM"
        assert len(strategy_dict['legs']) == 1
        assert 'strategy_id' in strategy_dict
        assert 'total_cost' in strategy_dict
        assert 'is_valid' in strategy_dict


class TestStrategyTemplates:
    """Test strategy template enumeration"""
    
    def test_all_templates_exist(self):
        """Test that all expected templates exist"""
        expected_templates = [
            'CUSTOM', 'IRON_CONDOR', 'BUTTERFLY', 'STRADDLE',
            'STRANGLE', 'BULL_CALL_SPREAD', 'BEAR_PUT_SPREAD'
        ]
        
        for template_name in expected_templates:
            assert hasattr(StrategyTemplate, template_name)
    
    def test_template_values(self):
        """Test template enum values"""
        assert StrategyTemplate.IRON_CONDOR.value == "IRON_CONDOR"
        assert StrategyTemplate.BUTTERFLY.value == "BUTTERFLY"


class TestStrategyLeg:
    """Test StrategyLeg model"""
    
    @pytest.fixture
    def option(self):
        """Create an option for testing"""
        return Option(
            symbol="TEST",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
    
    def test_strategy_leg_creation(self, option):
        """Test strategy leg creation"""
        leg = StrategyLeg(option=option, notes="Test leg")
        
        assert leg.option == option
        assert leg.notes == "Test leg"
        assert leg.leg_id is not None
    
    def test_strategy_leg_to_dict(self, option):
        """Test strategy leg to dictionary"""
        leg = StrategyLeg(option=option, notes="Test leg")
        leg_dict = leg.to_dict()
        
        assert 'leg_id' in leg_dict
        assert 'option' in leg_dict
        assert leg_dict['notes'] == "Test leg"
