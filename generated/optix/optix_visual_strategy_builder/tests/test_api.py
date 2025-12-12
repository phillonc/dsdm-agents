"""
Unit tests for API interface
"""
import pytest
from datetime import datetime, timedelta

from src.api.strategy_api import StrategyAPI


class TestStrategyAPI:
    """Test StrategyAPI high-level interface"""
    
    @pytest.fixture
    def api(self):
        """Create API instance"""
        return StrategyAPI()
    
    def test_create_custom_strategy(self, api):
        """Test creating custom strategy through API"""
        result = api.create_custom_strategy(
            name="My Strategy",
            description="Test strategy"
        )
        
        assert result['name'] == "My Strategy"
        assert 'strategy_id' in result
    
    def test_add_option_leg_through_api(self, api):
        """Test adding option leg through API"""
        api.create_custom_strategy("Test")
        
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        result = api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        assert 'leg_id' in result
        assert result['strategy_summary']['num_legs'] == 1
    
    def test_create_iron_condor_template(self, api):
        """Test creating Iron Condor from template"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
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
        
        assert result['strategy']['template'] == 'IRON_CONDOR'
        assert result['strategy']['num_legs'] == 4
    
    def test_create_straddle_template(self, api):
        """Test creating Straddle from template"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        result = api.create_from_template(
            template_name='STRADDLE',
            underlying_symbol='AAPL',
            underlying_price=180.0,
            expiration_date=exp_date
        )
        
        assert result['strategy']['template'] == 'STRADDLE'
        assert result['strategy']['num_legs'] == 2
    
    def test_get_payoff_diagram(self, api):
        """Test getting payoff diagram data"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_from_template(
            template_name='STRADDLE',
            underlying_symbol='TEST',
            underlying_price=100.0,
            expiration_date=exp_date
        )
        
        payoff = api.get_payoff_diagram(min_price=80.0, max_price=120.0)
        
        assert 'expiration_payoff' in payoff
        assert 'current_payoff' in payoff
        assert 'breakeven_points' in payoff
    
    def test_get_greeks_analysis(self, api):
        """Test getting Greeks analysis"""
        exp_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        api.create_custom_strategy("Test")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        greeks = api.get_greeks_analysis()
        
        assert 'current_greeks' in greeks
        assert 'risk_profile' in greeks
        assert 'interpretations' in greeks
    
    def test_get_risk_metrics(self, api):
        """Test getting risk metrics"""
        exp_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        api.create_custom_strategy("Test")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        metrics = api.get_risk_metrics()
        
        assert 'risk_reward' in metrics
        assert 'value_at_risk' in metrics
        assert 'probability_metrics' in metrics
    
    def test_run_scenario_analysis(self, api):
        """Test running scenario analysis"""
        exp_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        api.create_custom_strategy("Test")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        scenario = api.run_scenario_analysis(
            scenario_price=110.0,
            volatility_change=0.05,
            days_passed=10
        )
        
        assert 'scenario_price' in scenario
        assert 'current_pnl' in scenario
        assert 'greeks' in scenario
    
    def test_get_available_templates(self, api):
        """Test getting available templates"""
        templates = api.get_available_templates()
        
        assert 'IRON_CONDOR' in templates
        assert 'BUTTERFLY' in templates
        assert 'STRADDLE' in templates
        assert isinstance(templates, dict)
    
    def test_export_import_strategy(self, api):
        """Test export and import through API"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_custom_strategy("Original")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0
        )
        
        # Export
        export_data = api.export_strategy()
        assert 'strategy' in export_data
        
        # Import into new API instance
        new_api = StrategyAPI()
        imported = new_api.import_strategy(export_data)
        
        assert imported['name'] == "Original"
    
    def test_clone_strategy(self, api):
        """Test cloning strategy through API"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_custom_strategy("Original")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0
        )
        
        cloned = api.clone_strategy("Clone")
        
        assert cloned['name'] == "Clone"
        assert cloned['num_legs'] == 1
    
    def test_remove_option_leg(self, api):
        """Test removing option leg through API"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_custom_strategy("Test")
        result = api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0
        )
        
        leg_id = result['leg_id']
        
        remove_result = api.remove_option_leg(leg_id)
        
        assert remove_result['removed'] is True
        assert remove_result['strategy_summary']['num_legs'] == 0
    
    def test_update_option_leg(self, api):
        """Test updating option leg through API"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_custom_strategy("Test")
        result = api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0
        )
        
        leg_id = result['leg_id']
        
        update_result = api.update_option_leg(
            leg_id=leg_id,
            quantity=2,
            premium=6.0
        )
        
        assert update_result['updated'] is True
    
    def test_get_individual_leg_payoffs(self, api):
        """Test getting individual leg payoffs"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        api.create_from_template(
            template_name='STRADDLE',
            underlying_symbol='TEST',
            underlying_price=100.0,
            expiration_date=exp_date
        )
        
        leg_payoffs = api.get_individual_leg_payoffs()
        
        assert len(leg_payoffs) == 2  # Straddle has 2 legs
        assert all('pnl' in leg for leg in leg_payoffs)
    
    def test_get_time_decay_analysis(self, api):
        """Test time decay analysis"""
        exp_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        api.create_custom_strategy("Test")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        time_decay = api.get_time_decay_analysis(
            underlying_price=100.0,
            days_points=[0, 7, 14, 21, 28]
        )
        
        assert 'time_series' in time_decay
        assert len(time_decay['time_series']) > 0
    
    def test_get_volatility_analysis(self, api):
        """Test volatility impact analysis"""
        exp_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        api.create_custom_strategy("Test")
        api.add_option_leg(
            symbol="TEST_C100",
            underlying_symbol="TEST",
            option_type="CALL",
            strike_price=100.0,
            expiration_date=exp_date,
            quantity=1,
            position="LONG",
            premium=5.0,
            underlying_price=100.0,
            implied_volatility=0.25
        )
        
        vol_analysis = api.get_volatility_analysis(
            underlying_price=100.0,
            iv_changes=[-0.10, -0.05, 0.0, 0.05, 0.10]
        )
        
        assert 'volatility_series' in vol_analysis
        assert len(vol_analysis['volatility_series']) == 5


class TestAPIErrorHandling:
    """Test API error handling"""
    
    @pytest.fixture
    def api(self):
        """Create API instance"""
        return StrategyAPI()
    
    def test_no_active_strategy_error(self, api):
        """Test error when no active strategy"""
        result = api.get_payoff_diagram()
        
        assert 'error' in result
    
    def test_invalid_template_name(self, api):
        """Test error with invalid template name"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        result = api.create_from_template(
            template_name='INVALID_TEMPLATE',
            underlying_symbol='TEST',
            underlying_price=100.0,
            expiration_date=exp_date
        )
        
        assert 'error' in result
    
    def test_add_option_without_strategy(self, api):
        """Test adding option without creating strategy first"""
        exp_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        with pytest.raises(ValueError):
            api.add_option_leg(
                symbol="TEST_C100",
                underlying_symbol="TEST",
                option_type="CALL",
                strike_price=100.0,
                expiration_date=exp_date,
                quantity=1,
                position="LONG",
                premium=5.0
            )
