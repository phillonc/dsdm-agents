"""
Unit tests for P&L calculator and payoff diagram generation.
"""

import pytest
import numpy as np
from datetime import date, timedelta
from src.pnl_calculator import PayoffCalculator, RealTimePnLTracker
from src.models import OptionsStrategy, OptionLeg, OptionType, PositionType, Greeks


class TestPayoffCalculator:
    """Test the PayoffCalculator class."""
    
    def test_generate_price_range(self):
        """Test price range generation."""
        current_price = 100.0
        price_range = PayoffCalculator.generate_price_range(
            current_price=current_price,
            range_percentage=0.20,
            num_points=50
        )
        
        assert len(price_range) == 50
        assert min(price_range) == pytest.approx(80.0, rel=1e-5)
        assert max(price_range) == pytest.approx(120.0, rel=1e-5)
    
    def test_generate_price_range_default(self):
        """Test default price range generation."""
        current_price = 100.0
        price_range = PayoffCalculator.generate_price_range(current_price)
        
        assert len(price_range) == 100
        assert min(price_range) == pytest.approx(70.0, rel=1e-5)
        assert max(price_range) == pytest.approx(130.0, rel=1e-5)
    
    def test_calculate_payoff_diagram(self):
        """Test payoff diagram calculation."""
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
        
        current_price = 100.0
        payoff_data = PayoffCalculator.calculate_payoff_diagram(
            strategy=strategy,
            current_price=current_price
        )
        
        assert 'price_range' in payoff_data
        assert 'pnl_data' in payoff_data
        assert 'max_profit' in payoff_data
        assert 'max_loss' in payoff_data
        assert 'breakeven_points' in payoff_data
        assert 'current_pnl' in payoff_data
        assert 'total_cost' in payoff_data
        
        assert len(payoff_data['pnl_data']) > 0
        assert payoff_data['total_cost'] == -500.0
    
    def test_calculate_payoff_diagram_custom_range(self):
        """Test payoff diagram with custom price range."""
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
        
        custom_range = [90.0, 95.0, 100.0, 105.0, 110.0]
        payoff_data = PayoffCalculator.calculate_payoff_diagram(
            strategy=strategy,
            price_range=custom_range
        )
        
        assert len(payoff_data['pnl_data']) == 5
        assert payoff_data['price_range'] == custom_range
    
    def test_calculate_probability_of_profit(self):
        """Test probability of profit calculation."""
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
        
        prob_data = PayoffCalculator.calculate_probability_of_profit(
            strategy=strategy,
            current_price=100.0,
            expected_volatility=0.25,
            days_to_expiration=30,
            num_simulations=1000
        )
        
        assert 'probability_of_profit' in prob_data
        assert 'average_profit' in prob_data
        assert 'average_loss' in prob_data
        assert 'expected_value' in prob_data
        assert 'simulations' in prob_data
        
        assert 0 <= prob_data['probability_of_profit'] <= 100
        assert prob_data['simulations'] == 1000
    
    def test_calculate_risk_reward_ratio(self):
        """Test risk/reward ratio calculation."""
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
        
        price_range = PayoffCalculator.generate_price_range(100.0)
        risk_metrics = PayoffCalculator.calculate_risk_reward_ratio(strategy, price_range)
        
        assert 'max_profit' in risk_metrics
        assert 'max_loss' in risk_metrics
        assert 'risk_reward_ratio' in risk_metrics
        assert 'return_on_risk_percent' in risk_metrics
        assert 'total_capital_at_risk' in risk_metrics
        
        assert risk_metrics['max_loss'] == -500.0
        assert risk_metrics['total_capital_at_risk'] == 500.0
    
    def test_calculate_risk_reward_iron_condor(self):
        """Test risk/reward for Iron Condor (defined risk strategy)."""
        from src.strategy_templates import StrategyTemplates
        
        expiration = date.today() + timedelta(days=30)
        strategy = StrategyTemplates.create_iron_condor(
            underlying_symbol="SPY",
            current_price=100.0,
            expiration=expiration,
            wing_width=5.0,
            body_width=10.0
        )
        
        price_range = PayoffCalculator.generate_price_range(100.0, range_percentage=0.30)
        risk_metrics = PayoffCalculator.calculate_risk_reward_ratio(strategy, price_range)
        
        # Iron condor should have both defined max profit and max loss
        assert risk_metrics['max_profit'] is not None
        assert risk_metrics['max_loss'] is not None
        assert risk_metrics['risk_reward_ratio'] is not None


class TestRealTimePnLTracker:
    """Test the RealTimePnLTracker class."""
    
    def test_tracker_initialization(self):
        """Test tracker initialization."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        tracker = RealTimePnLTracker(strategy)
        
        assert tracker.strategy == strategy
        assert len(tracker.pnl_history) == 0
    
    def test_update_pnl(self):
        """Test P&L update."""
        strategy = OptionsStrategy(name="Test", underlying_symbol="SPY")
        
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=100.0,
            expiration=date.today(),
            quantity=1,
            premium=5.0,
            greeks=Greeks(delta=0.5, gamma=0.02, theta=-0.05, vega=0.15, rho=0.03)
        )
        strategy.add_leg(leg)
        
        tracker = RealTimePnLTracker(strategy)
        
        snapshot = tracker.update_pnl(current_price=105.0)
        
        assert 'timestamp' in snapshot
        assert 'underlying_price' in snapshot
        assert 'pnl' in snapshot
        assert 'total_cost' in snapshot
        assert 'greeks' in snapshot
        
        assert snapshot['underlying_price'] == 105.0
        assert len(tracker.pnl_history) == 1
    
    def test_multiple_updates(self):
        """Test multiple P&L updates."""
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
        
        tracker = RealTimePnLTracker(strategy)
        
        tracker.update_pnl(100.0)
        tracker.update_pnl(105.0)
        tracker.update_pnl(110.0)
        
        assert len(tracker.pnl_history) == 3
        assert tracker.pnl_history[0]['underlying_price'] == 100.0
        assert tracker.pnl_history[2]['underlying_price'] == 110.0
    
    def test_get_pnl_change(self):
        """Test P&L change calculation."""
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
        
        tracker = RealTimePnLTracker(strategy)
        
        # First update
        tracker.update_pnl(100.0)
        change = tracker.get_pnl_change()
        assert change is None  # Not enough data
        
        # Second update
        tracker.update_pnl(105.0)
        change = tracker.get_pnl_change()
        assert change is not None
        assert isinstance(change, float)
    
    def test_get_pnl_history(self):
        """Test getting P&L history."""
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
        
        tracker = RealTimePnLTracker(strategy)
        
        prices = [100.0, 102.0, 105.0, 103.0]
        for price in prices:
            tracker.update_pnl(price)
        
        history = tracker.get_pnl_history()
        assert len(history) == 4
        assert all('pnl' in snapshot for snapshot in history)
    
    def test_reset_history(self):
        """Test resetting P&L history."""
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
        
        tracker = RealTimePnLTracker(strategy)
        
        tracker.update_pnl(100.0)
        tracker.update_pnl(105.0)
        assert len(tracker.pnl_history) == 2
        
        tracker.reset_history()
        assert len(tracker.pnl_history) == 0
    
    def test_custom_timestamp(self):
        """Test P&L update with custom timestamp."""
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
        
        tracker = RealTimePnLTracker(strategy)
        
        custom_timestamp = "2024-01-01T12:00:00"
        snapshot = tracker.update_pnl(current_price=105.0, timestamp=custom_timestamp)
        
        assert snapshot['timestamp'] == custom_timestamp
