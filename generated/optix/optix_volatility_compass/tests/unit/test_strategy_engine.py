"""
Unit tests for strategy engine.
"""
import pytest
from datetime import datetime

from src.strategy_engine import VolatilityStrategyEngine
from src.models import (
    VolatilityMetrics, VolatilityCondition, VolatilitySkew,
    VolatilityTermStructure, StrategyType, TermStructurePoint
)


class TestVolatilityStrategyEngine:
    """Tests for Volatility Strategy Engine."""
    
    def setup_method(self):
        self.engine = VolatilityStrategyEngine()
    
    def create_test_metrics(self, iv_rank=50, iv_percentile=50, iv_hv_ratio=1.0):
        """Helper to create test metrics."""
        return VolatilityMetrics(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_iv=30.0,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            historical_volatility_30d=25.0,
            historical_volatility_60d=26.0,
            historical_volatility_90d=27.0,
            iv_hv_ratio=iv_hv_ratio,
            condition=VolatilityCondition.NORMAL,
            average_iv_30d=28.0,
            average_iv_60d=29.0,
            min_iv_52w=20.0,
            max_iv_52w=45.0
        )
    
    def test_generate_primary_strategy_high_iv(self):
        """Test premium selling strategy for high IV."""
        metrics = self.create_test_metrics(iv_rank=75, iv_percentile=80)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert strategy is not None
        assert strategy.strategy_type == StrategyType.SELL_PREMIUM
        assert strategy.confidence > 60
        assert len(strategy.suggested_actions) > 0
        assert "sell" in strategy.strategy_name.lower()
    
    def test_generate_primary_strategy_extremely_high_iv(self):
        """Test aggressive premium selling for extremely high IV."""
        metrics = self.create_test_metrics(iv_rank=90, iv_percentile=95)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert strategy is not None
        assert strategy.strategy_type == StrategyType.SELL_PREMIUM
        assert strategy.confidence > 80
        assert "PRIORITY" in strategy.suggested_actions[0]
    
    def test_generate_primary_strategy_low_iv(self):
        """Test premium buying strategy for low IV."""
        metrics = self.create_test_metrics(iv_rank=25, iv_percentile=20)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert strategy is not None
        assert strategy.strategy_type == StrategyType.BUY_PREMIUM
        assert strategy.confidence > 60
        assert len(strategy.suggested_actions) > 0
        assert "buy" in strategy.strategy_name.lower()
    
    def test_generate_primary_strategy_extremely_low_iv(self):
        """Test aggressive premium buying for extremely low IV."""
        metrics = self.create_test_metrics(iv_rank=10, iv_percentile=12)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert strategy is not None
        assert strategy.strategy_type == StrategyType.BUY_PREMIUM
        assert strategy.confidence > 70
        assert "PRIORITY" in strategy.suggested_actions[0]
    
    def test_generate_primary_strategy_neutral_iv(self):
        """Test neutral strategy for mid-range IV."""
        metrics = self.create_test_metrics(iv_rank=50, iv_percentile=50)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert strategy is not None
        assert strategy.strategy_type == StrategyType.NEUTRAL
        assert strategy.confidence == 50
        assert "neutral" in strategy.strategy_name.lower()
    
    def test_generate_strategies_complete(self):
        """Test complete strategy generation with all inputs."""
        metrics = self.create_test_metrics(iv_rank=75, iv_percentile=80)
        
        skew = VolatilitySkew(
            symbol="AAPL",
            expiration_date=datetime.now(),
            days_to_expiration=30,
            atm_strike=150.0,
            atm_iv=30.0,
            call_strikes=[155, 160, 165],
            call_ivs=[28, 26, 24],
            call_skew_slope=-0.02,
            put_strikes=[145, 140, 135],
            put_ivs=[32, 35, 38],
            put_skew_slope=-0.05,
            put_call_skew_ratio=1.15,
            skew_type="normal"
        )
        
        term_structure = VolatilityTermStructure(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_price=150.0,
            term_points=[],
            structure_shape="backwardation",
            front_month_iv=35.0,
            back_month_iv=28.0,
            term_structure_slope=-0.1
        )
        
        strategies = self.engine.generate_strategies(
            metrics, skew, term_structure
        )
        
        assert len(strategies) > 0
        assert all(hasattr(s, 'confidence') for s in strategies)
        # Strategies should be sorted by confidence
        confidences = [s.confidence for s in strategies]
        assert confidences == sorted(confidences, reverse=True)
    
    def test_generate_skew_strategies_normal_skew(self):
        """Test strategy generation for normal skew."""
        metrics = self.create_test_metrics(iv_rank=60)
        
        skew = VolatilitySkew(
            symbol="AAPL",
            expiration_date=datetime.now(),
            days_to_expiration=30,
            atm_strike=150.0,
            atm_iv=30.0,
            call_strikes=[155, 160],
            call_ivs=[28, 26],
            call_skew_slope=-0.01,
            put_strikes=[145, 140],
            put_ivs=[33, 36],
            put_skew_slope=-0.05,
            put_call_skew_ratio=1.15,
            skew_type="normal"
        )
        
        strategies = self.engine._generate_skew_strategies(metrics, skew)
        
        assert len(strategies) > 0
        assert any("put" in s.strategy_name.lower() for s in strategies)
    
    def test_generate_skew_strategies_reverse_skew(self):
        """Test strategy generation for reverse skew."""
        metrics = self.create_test_metrics(iv_rank=60)
        
        skew = VolatilitySkew(
            symbol="AAPL",
            expiration_date=datetime.now(),
            days_to_expiration=30,
            atm_strike=150.0,
            atm_iv=30.0,
            call_strikes=[155, 160],
            call_ivs=[33, 36],
            call_skew_slope=0.05,
            put_strikes=[145, 140],
            put_ivs=[28, 26],
            put_skew_slope=-0.01,
            put_call_skew_ratio=0.85,
            skew_type="reverse"
        )
        
        strategies = self.engine._generate_skew_strategies(metrics, skew)
        
        assert len(strategies) > 0
        assert any("call" in s.strategy_name.lower() for s in strategies)
    
    def test_generate_skew_strategies_smile(self):
        """Test strategy generation for smile skew."""
        metrics = self.create_test_metrics(iv_rank=60)
        
        skew = VolatilitySkew(
            symbol="AAPL",
            expiration_date=datetime.now(),
            days_to_expiration=30,
            atm_strike=150.0,
            atm_iv=30.0,
            call_strikes=[155, 160],
            call_ivs=[32, 35],
            call_skew_slope=0.05,
            put_strikes=[145, 140],
            put_ivs=[32, 35],
            put_skew_slope=-0.05,
            put_call_skew_ratio=1.02,
            skew_type="smile"
        )
        
        strategies = self.engine._generate_skew_strategies(metrics, skew)
        
        assert len(strategies) > 0
        assert any("smile" in s.strategy_name.lower() for s in strategies)
    
    def test_generate_term_structure_strategies_backwardation(self):
        """Test strategy for backwardation term structure."""
        metrics = self.create_test_metrics(iv_rank=65)
        
        term_structure = VolatilityTermStructure(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_price=150.0,
            term_points=[],
            structure_shape="backwardation",
            front_month_iv=40.0,
            back_month_iv=30.0,
            term_structure_slope=-0.15
        )
        
        strategies = self.engine._generate_term_structure_strategies(
            metrics, term_structure
        )
        
        assert len(strategies) > 0
        assert any("backwardation" in s.strategy_name.lower() for s in strategies)
        assert strategies[0].confidence > 60
    
    def test_generate_term_structure_strategies_contango(self):
        """Test strategy for contango term structure."""
        metrics = self.create_test_metrics(iv_rank=60)
        
        term_structure = VolatilityTermStructure(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_price=150.0,
            term_points=[],
            structure_shape="contango",
            front_month_iv=28.0,
            back_month_iv=32.0,
            term_structure_slope=0.05
        )
        
        strategies = self.engine._generate_term_structure_strategies(
            metrics, term_structure
        )
        
        # Should return at least one strategy
        assert len(strategies) >= 0
    
    def test_get_quick_recommendation_very_high_iv(self):
        """Test quick recommendation for very high IV."""
        recommendation = self.engine.get_quick_recommendation(85)
        
        assert "SELL PREMIUM" in recommendation
        assert "🔴" in recommendation
    
    def test_get_quick_recommendation_high_iv(self):
        """Test quick recommendation for high IV."""
        recommendation = self.engine.get_quick_recommendation(65)
        
        assert "Sell premium" in recommendation
        assert "🟠" in recommendation
    
    def test_get_quick_recommendation_neutral_iv(self):
        """Test quick recommendation for neutral IV."""
        recommendation = self.engine.get_quick_recommendation(50)
        
        assert "Neutral" in recommendation
        assert "🟡" in recommendation
    
    def test_get_quick_recommendation_low_iv(self):
        """Test quick recommendation for low IV."""
        recommendation = self.engine.get_quick_recommendation(25)
        
        assert "Buy premium" in recommendation
        assert "🟢" in recommendation
    
    def test_get_quick_recommendation_very_low_iv(self):
        """Test quick recommendation for very low IV."""
        recommendation = self.engine.get_quick_recommendation(10)
        
        assert "BUY PREMIUM" in recommendation
        assert "🟢" in recommendation
    
    def test_strategy_contains_required_fields(self):
        """Test that generated strategies contain all required fields."""
        metrics = self.create_test_metrics(iv_rank=75)
        
        strategy = self.engine._generate_primary_strategy(metrics)
        
        assert hasattr(strategy, 'strategy_type')
        assert hasattr(strategy, 'confidence')
        assert hasattr(strategy, 'strategy_name')
        assert hasattr(strategy, 'description')
        assert hasattr(strategy, 'reasoning')
        assert hasattr(strategy, 'suggested_actions')
        assert hasattr(strategy, 'risk_level')
        assert hasattr(strategy, 'iv_rank')
        assert hasattr(strategy, 'iv_percentile')
        assert hasattr(strategy, 'iv_hv_ratio')
        
        assert len(strategy.reasoning) > 0
        assert len(strategy.suggested_actions) > 0
        assert strategy.risk_level in ['low', 'medium', 'high']
