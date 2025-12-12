"""
Unit tests for builder modules
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.builders.strategy_builder import StrategyBuilder
from src.builders.template_builder import TemplateBuilder
from src.models.option import OptionType, OptionPosition
from src.models.strategy import StrategyTemplate


class TestStrategyBuilder:
    """Test StrategyBuilder functionality"""
    
    @pytest.fixture
    def builder(self):
        """Create a strategy builder"""
        return StrategyBuilder()
    
    def test_create_strategy(self, builder):
        """Test strategy creation"""
        strategy = builder.create_strategy(
            "Test Strategy",
            StrategyTemplate.CUSTOM,
            "Test description"
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.template == StrategyTemplate.CUSTOM
        assert builder.strategy is not None
    
    def test_add_option(self, builder):
        """Test adding option to strategy"""
        builder.create_strategy("Test")
        
        leg = builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        assert leg is not None
        assert len(builder.strategy.legs) == 1
    
    def test_remove_option(self, builder):
        """Test removing option from strategy"""
        builder.create_strategy("Test")
        
        leg = builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        removed = builder.remove_option(leg.leg_id)
        assert removed is True
        assert len(builder.strategy.legs) == 0
    
    def test_update_option(self, builder):
        """Test updating option"""
        builder.create_strategy("Test")
        
        leg = builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        updated = builder.update_option(
            leg.leg_id,
            quantity=2,
            premium=Decimal('6.00')
        )
        
        assert updated is True
        assert leg.option.quantity == 2
        assert leg.option.premium == Decimal('6.00')
    
    def test_calculate_strategy_metrics(self, builder):
        """Test strategy metrics calculation"""
        builder.create_strategy("Test")
        
        builder.add_option(
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
        
        metrics = builder.calculate_strategy_metrics()
        
        assert metrics['is_valid'] is True
        assert 'greeks' in metrics
        assert 'risk_reward' in metrics
        assert 'payoff_diagram' in metrics
    
    def test_get_strategy_summary(self, builder):
        """Test getting strategy summary"""
        builder.create_strategy("Test Strategy")
        
        summary = builder.get_strategy_summary()
        
        assert summary['name'] == "Test Strategy"
        assert 'strategy_id' in summary
        assert 'num_legs' in summary
    
    def test_clone_strategy(self, builder):
        """Test cloning a strategy"""
        builder.create_strategy("Original")
        
        builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        cloned = builder.clone_strategy("Clone")
        
        assert cloned.name == "Clone"
        assert len(cloned.legs) == len(builder.strategy.legs)
        assert cloned.strategy_id != builder.strategy.strategy_id
    
    def test_export_import_strategy(self, builder):
        """Test exporting and importing a strategy"""
        builder.create_strategy("Test")
        
        builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        # Export
        export_data = builder.export_strategy()
        
        assert 'strategy' in export_data
        assert 'export_version' in export_data
        
        # Import into new builder
        new_builder = StrategyBuilder()
        imported = new_builder.import_strategy(export_data)
        
        assert imported.name == "Test"
        assert len(imported.legs) == 1
    
    def test_history_tracking(self, builder):
        """Test modification history tracking"""
        builder.create_strategy("Test")
        
        builder.add_option(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type=OptionType.CALL,
            strike_price=Decimal('100'),
            expiration_date=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            position=OptionPosition.LONG,
            premium=Decimal('5.00')
        )
        
        history = builder.get_history()
        
        assert len(history) >= 2  # create_strategy and add_option
        assert any(h['action'] == 'create_strategy' for h in history)
        assert any(h['action'] == 'add_option' for h in history)


class TestTemplateBuilder:
    """Test TemplateBuilder functionality"""
    
    @pytest.fixture
    def template_builder(self):
        """Create a template builder"""
        return TemplateBuilder()
    
    @pytest.fixture
    def common_params(self):
        """Common parameters for templates"""
        return {
            'underlying_symbol': 'TEST',
            'underlying_price': Decimal('100'),
            'expiration_date': datetime.utcnow() + timedelta(days=30),
            'quantity': 1,
            'implied_volatility': Decimal('0.25')
        }
    
    def test_create_iron_condor(self, template_builder, common_params):
        """Test Iron Condor template creation"""
        strategy = template_builder.create_iron_condor(
            **common_params,
            put_short_strike=Decimal('95'),
            put_long_strike=Decimal('90'),
            call_short_strike=Decimal('105'),
            call_long_strike=Decimal('110')
        )
        
        assert strategy.template == StrategyTemplate.IRON_CONDOR
        assert len(strategy.legs) == 4
        assert strategy.name == "Iron Condor - TEST"
    
    def test_create_butterfly(self, template_builder, common_params):
        """Test Butterfly template creation"""
        strategy = template_builder.create_butterfly(
            **common_params,
            lower_strike=Decimal('95'),
            middle_strike=Decimal('100'),
            upper_strike=Decimal('105')
        )
        
        assert strategy.template == StrategyTemplate.BUTTERFLY
        assert len(strategy.legs) == 3
    
    def test_create_straddle(self, template_builder, common_params):
        """Test Straddle template creation"""
        strategy = template_builder.create_straddle(
            **common_params,
            strike_price=Decimal('100')
        )
        
        assert strategy.template == StrategyTemplate.STRADDLE
        assert len(strategy.legs) == 2
        
        # Should have one call and one put
        option_types = [leg.option.option_type for leg in strategy.legs]
        assert OptionType.CALL in option_types
        assert OptionType.PUT in option_types
    
    def test_create_strangle(self, template_builder, common_params):
        """Test Strangle template creation"""
        strategy = template_builder.create_strangle(
            **common_params,
            put_strike=Decimal('95'),
            call_strike=Decimal('105')
        )
        
        assert strategy.template == StrategyTemplate.STRANGLE
        assert len(strategy.legs) == 2
    
    def test_create_bull_call_spread(self, template_builder, common_params):
        """Test Bull Call Spread template creation"""
        strategy = template_builder.create_bull_call_spread(
            **common_params,
            long_strike=Decimal('98'),
            short_strike=Decimal('102')
        )
        
        assert strategy.template == StrategyTemplate.BULL_CALL_SPREAD
        assert len(strategy.legs) == 2
        
        # Should have one long and one short call
        positions = [leg.option.position for leg in strategy.legs]
        assert OptionPosition.LONG in positions
        assert OptionPosition.SHORT in positions
    
    def test_create_bear_put_spread(self, template_builder, common_params):
        """Test Bear Put Spread template creation"""
        strategy = template_builder.create_bear_put_spread(
            **common_params,
            long_strike=Decimal('102'),
            short_strike=Decimal('98')
        )
        
        assert strategy.template == StrategyTemplate.BEAR_PUT_SPREAD
        assert len(strategy.legs) == 2
    
    def test_get_template_list(self, template_builder):
        """Test getting template list"""
        templates = template_builder.get_template_list()
        
        assert 'IRON_CONDOR' in templates
        assert 'BUTTERFLY' in templates
        assert 'STRADDLE' in templates
        assert isinstance(templates['IRON_CONDOR'], str)
    
    def test_straddle_long_position(self, template_builder, common_params):
        """Test long straddle creates long positions"""
        strategy = template_builder.create_straddle(
            **common_params,
            strike_price=Decimal('100'),
            position=OptionPosition.LONG
        )
        
        # All legs should be long
        assert all(leg.option.position == OptionPosition.LONG for leg in strategy.legs)
    
    def test_straddle_short_position(self, template_builder, common_params):
        """Test short straddle creates short positions"""
        strategy = template_builder.create_straddle(
            **common_params,
            strike_price=Decimal('100'),
            position=OptionPosition.SHORT
        )
        
        # All legs should be short
        assert all(leg.option.position == OptionPosition.SHORT for leg in strategy.legs)
    
    def test_butterfly_call_type(self, template_builder, common_params):
        """Test butterfly with calls"""
        strategy = template_builder.create_butterfly(
            **common_params,
            lower_strike=Decimal('95'),
            middle_strike=Decimal('100'),
            upper_strike=Decimal('105'),
            option_type=OptionType.CALL
        )
        
        # All legs should be calls
        assert all(leg.option.option_type == OptionType.CALL for leg in strategy.legs)
    
    def test_butterfly_put_type(self, template_builder, common_params):
        """Test butterfly with puts"""
        strategy = template_builder.create_butterfly(
            **common_params,
            lower_strike=Decimal('95'),
            middle_strike=Decimal('100'),
            upper_strike=Decimal('105'),
            option_type=OptionType.PUT
        )
        
        # All legs should be puts
        assert all(leg.option.option_type == OptionType.PUT for leg in strategy.legs)
