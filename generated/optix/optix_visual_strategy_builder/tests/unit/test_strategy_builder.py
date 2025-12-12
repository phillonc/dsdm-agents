"""
Unit tests for strategy builder.
"""

import pytest
from datetime import date, timedelta
from src.strategy_builder import StrategyBuilder
from src.models import (
    OptionsStrategy, OptionType, PositionType, 
    StrategyType, Greeks
)


class TestStrategyBuilder:
    """Test the StrategyBuilder class."""
    
    def setup_method(self):
        """Set up test builder."""
        self.builder = StrategyBuilder()
    
    def test_initialization(self):
        """Test builder initialization."""
        assert len(self.builder.strategies) == 0
        assert len(self.builder.pnl_trackers) == 0
    
    def test_create_strategy(self):
        """Test creating a custom strategy."""
        strategy = self.builder.create_strategy(
            name="My Strategy",
            underlying_symbol="SPY",
            strategy_type=StrategyType.CUSTOM
        )
        
        assert strategy.name == "My Strategy"
        assert strategy.underlying_symbol == "SPY"
        assert strategy.strategy_type == StrategyType.CUSTOM
        assert strategy.id in self.builder.strategies
    
    def test_create_from_template_iron_condor(self):
        """Test creating strategy from Iron Condor template."""
        expiration = date.today() + timedelta(days=30)
        strategy = self.builder.create_from_template(
            template_type=StrategyType.IRON_CONDOR,
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            wing_width=5.0,
            body_width=10.0
        )
        
        assert strategy.strategy_type == StrategyType.IRON_CONDOR
        assert len(strategy.legs) == 4
        assert strategy.id in self.builder.strategies
    
    def test_create_from_template_straddle(self):
        """Test creating strategy from Straddle template."""
        expiration = date.today() + timedelta(days=30)
        strategy = self.builder.create_from_template(
            template_type=StrategyType.STRADDLE,
            underlying_symbol="SPY",
            current_price=450.0,
            expiration=expiration,
            strike=450.0
        )
        
        assert strategy.strategy_type == StrategyType.STRADDLE
        assert len(strategy.legs) == 2
    
    def test_create_from_template_invalid(self):
        """Test creating strategy with invalid template type."""
        expiration = date.today() + timedelta(days=30)
        
        with pytest.raises(ValueError):
            self.builder.create_from_template(
                template_type=StrategyType.CUSTOM,  # Not a valid template
                underlying_symbol="SPY",
                current_price=450.0,
                expiration=expiration
            )
    
    def test_add_leg_to_strategy(self):
        """Test adding a leg to a strategy."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        leg = self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            implied_volatility=0.25
        )
        
        assert leg.option_type == OptionType.CALL
        assert leg.strike == 100.0
        assert len(strategy.legs) == 1
    
    def test_add_leg_with_greeks(self):
        """Test adding a leg with custom Greeks."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        greeks = Greeks(delta=0.6, gamma=0.03, theta=-0.08, vega=0.18, rho=0.04)
        
        leg = self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            greeks=greeks
        )
        
        assert leg.greeks.delta == 0.6
        assert leg.greeks.gamma == 0.03
    
    def test_add_leg_invalid_strategy(self):
        """Test adding leg to nonexistent strategy."""
        expiration = date.today() + timedelta(days=30)
        
        with pytest.raises(ValueError):
            self.builder.add_leg_to_strategy(
                strategy_id="invalid-id",
                option_type=OptionType.CALL,
                position_type=PositionType.LONG,
                strike=100.0,
                expiration=expiration,
                quantity=1,
                premium=5.0
            )
    
    def test_remove_leg_from_strategy(self):
        """Test removing a leg from a strategy."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        leg = self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        assert len(strategy.legs) == 1
        
        result = self.builder.remove_leg_from_strategy(strategy.id, leg.id)
        assert result is True
        assert len(strategy.legs) == 0
    
    def test_get_strategy(self):
        """Test getting a strategy by ID."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        retrieved = self.builder.get_strategy(strategy.id)
        assert retrieved == strategy
    
    def test_get_nonexistent_strategy(self):
        """Test getting a nonexistent strategy."""
        result = self.builder.get_strategy("invalid-id")
        assert result is None
    
    def test_list_strategies(self):
        """Test listing all strategies."""
        strategy1 = self.builder.create_strategy(name="Strategy 1", underlying_symbol="SPY")
        strategy2 = self.builder.create_strategy(name="Strategy 2", underlying_symbol="QQQ")
        
        strategies = self.builder.list_strategies()
        assert len(strategies) == 2
        assert strategy1 in strategies
        assert strategy2 in strategies
    
    def test_delete_strategy(self):
        """Test deleting a strategy."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        assert strategy.id in self.builder.strategies
        
        result = self.builder.delete_strategy(strategy.id)
        assert result is True
        assert strategy.id not in self.builder.strategies
    
    def test_delete_nonexistent_strategy(self):
        """Test deleting a nonexistent strategy."""
        result = self.builder.delete_strategy("invalid-id")
        assert result is False
    
    def test_calculate_payoff_diagram(self):
        """Test calculating payoff diagram."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        payoff = self.builder.calculate_payoff_diagram(
            strategy_id=strategy.id,
            current_price=100.0
        )
        
        assert 'price_range' in payoff
        assert 'pnl_data' in payoff
        assert 'max_profit' in payoff
        assert 'max_loss' in payoff
    
    def test_start_pnl_tracking(self):
        """Test starting P&L tracking."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        self.builder.start_pnl_tracking(strategy.id)
        assert strategy.id in self.builder.pnl_trackers
    
    def test_update_pnl(self):
        """Test updating P&L."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        snapshot = self.builder.update_pnl(strategy.id, 105.0)
        
        assert 'pnl' in snapshot
        assert 'underlying_price' in snapshot
        assert snapshot['underlying_price'] == 105.0
    
    def test_get_pnl_history(self):
        """Test getting P&L history."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        self.builder.update_pnl(strategy.id, 100.0)
        self.builder.update_pnl(strategy.id, 105.0)
        
        history = self.builder.get_pnl_history(strategy.id)
        assert len(history) == 2
    
    def test_analyze_scenario_price(self):
        """Test price scenario analysis."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        
        result = self.builder.analyze_scenario(
            strategy_id=strategy.id,
            current_price=100.0,
            scenario_type='price',
            price_changes=[-5, 0, 5]
        )
        
        assert result['type'] == 'price'
        assert 'results' in result
        assert len(result['results']) == 3
    
    def test_analyze_scenario_volatility(self):
        """Test volatility scenario analysis."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        
        result = self.builder.analyze_scenario(
            strategy_id=strategy.id,
            current_price=100.0,
            scenario_type='volatility',
            volatility_changes=[-5, 0, 5]
        )
        
        assert result['type'] == 'volatility'
        assert 'results' in result
    
    def test_analyze_scenario_stress(self):
        """Test stress test scenario."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        
        result = self.builder.analyze_scenario(
            strategy_id=strategy.id,
            current_price=100.0,
            scenario_type='stress'
        )
        
        assert result['type'] == 'stress'
        assert 'results' in result
        assert 'market_crash' in result['results']
    
    def test_get_risk_metrics(self):
        """Test getting risk metrics."""
        strategy = self.builder.create_strategy(
            name="Test",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        
        metrics = self.builder.get_risk_metrics(
            strategy_id=strategy.id,
            current_price=100.0
        )
        
        assert 'strategy_id' in metrics
        assert 'greeks' in metrics
        assert 'risk_reward' in metrics
        assert 'probability_analysis' in metrics
    
    def test_export_strategy(self):
        """Test exporting a strategy."""
        strategy = self.builder.create_strategy(
            name="Test Export",
            underlying_symbol="SPY"
        )
        
        expiration = date.today() + timedelta(days=30)
        self.builder.add_leg_to_strategy(
            strategy_id=strategy.id,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=expiration,
            quantity=1,
            premium=5.0
        )
        
        exported = self.builder.export_strategy(strategy.id)
        
        assert exported['name'] == "Test Export"
        assert 'legs' in exported
        assert len(exported['legs']) == 1
    
    def test_import_strategy(self):
        """Test importing a strategy."""
        strategy_dict = {
            'name': 'Imported Strategy',
            'underlying_symbol': 'SPY',
            'strategy_type': 'CUSTOM',
            'notes': 'Test import',
            'legs': [
                {
                    'option_type': 'CALL',
                    'position_type': 'LONG',
                    'strike': 100.0,
                    'expiration': (date.today() + timedelta(days=30)).isoformat(),
                    'quantity': 1,
                    'premium': 5.0,
                    'underlying_symbol': 'SPY',
                    'implied_volatility': 0.25,
                    'greeks': {
                        'delta': 0.5,
                        'gamma': 0.02,
                        'theta': -0.05,
                        'vega': 0.15,
                        'rho': 0.03
                    }
                }
            ]
        }
        
        strategy = self.builder.import_strategy(strategy_dict)
        
        assert strategy.name == 'Imported Strategy'
        assert strategy.underlying_symbol == 'SPY'
        assert len(strategy.legs) == 1
        assert strategy.id in self.builder.strategies
