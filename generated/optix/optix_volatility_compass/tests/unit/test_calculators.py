"""
Unit tests for volatility calculators.
"""
import pytest
import numpy as np
from datetime import datetime, timedelta

from src.calculators import (
    IVRankCalculator, HistoricalVolatilityCalculator,
    SkewCalculator, TermStructureCalculator,
    VolatilitySurfaceCalculator, IVConditionClassifier
)


class TestIVRankCalculator:
    """Tests for IV Rank calculator."""
    
    def setup_method(self):
        self.calculator = IVRankCalculator()
    
    def test_calculate_iv_rank_mid_range(self):
        """Test IV rank calculation with mid-range value."""
        current_iv = 30.0
        iv_history = [25.0, 28.0, 35.0, 20.0, 40.0, 30.0, 32.0]
        
        rank = self.calculator.calculate_iv_rank(current_iv, iv_history)
        
        assert 0 <= rank <= 100
        assert 40 < rank < 60  # Should be mid-range
    
    def test_calculate_iv_rank_at_max(self):
        """Test IV rank when current IV is at maximum."""
        current_iv = 50.0
        iv_history = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
        
        rank = self.calculator.calculate_iv_rank(current_iv, iv_history)
        
        assert rank == 100.0
    
    def test_calculate_iv_rank_at_min(self):
        """Test IV rank when current IV is at minimum."""
        current_iv = 20.0
        iv_history = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
        
        rank = self.calculator.calculate_iv_rank(current_iv, iv_history)
        
        assert rank == 0.0
    
    def test_calculate_iv_rank_insufficient_data(self):
        """Test IV rank with insufficient data."""
        current_iv = 30.0
        iv_history = [30.0]
        
        rank = self.calculator.calculate_iv_rank(current_iv, iv_history)
        
        assert rank == 50.0  # Default middle value
    
    def test_calculate_iv_rank_no_variation(self):
        """Test IV rank when all values are the same."""
        current_iv = 30.0
        iv_history = [30.0] * 10
        
        rank = self.calculator.calculate_iv_rank(current_iv, iv_history)
        
        assert rank == 50.0
    
    def test_calculate_iv_percentile(self):
        """Test IV percentile calculation."""
        current_iv = 30.0
        iv_history = [20.0, 25.0, 28.0, 35.0, 40.0]
        
        percentile = self.calculator.calculate_iv_percentile(current_iv, iv_history)
        
        assert 0 <= percentile <= 100
        assert percentile == 60.0  # 3 out of 5 values below 30
    
    def test_calculate_iv_percentile_all_below(self):
        """Test percentile when all history is below current."""
        current_iv = 50.0
        iv_history = [20.0, 25.0, 30.0, 35.0, 40.0]
        
        percentile = self.calculator.calculate_iv_percentile(current_iv, iv_history)
        
        assert percentile == 100.0
    
    def test_get_52_week_extremes(self):
        """Test 52-week min/max calculation."""
        iv_history = [30.0, 25.0, 40.0, 20.0, 35.0, 45.0]
        
        min_iv, max_iv = self.calculator.get_52_week_extremes(iv_history)
        
        assert min_iv == 20.0
        assert max_iv == 45.0
    
    def test_get_52_week_extremes_empty(self):
        """Test extremes with empty history."""
        iv_history = []
        
        min_iv, max_iv = self.calculator.get_52_week_extremes(iv_history)
        
        assert min_iv == 0.0
        assert max_iv == 0.0


class TestHistoricalVolatilityCalculator:
    """Tests for Historical Volatility calculator."""
    
    def setup_method(self):
        self.calculator = HistoricalVolatilityCalculator()
    
    def test_calculate_hv_basic(self):
        """Test basic HV calculation."""
        # Generate synthetic price data with known volatility
        prices = [100.0, 102.0, 101.0, 103.0, 102.5, 104.0, 103.0, 105.0]
        prices.reverse()  # Most recent first
        
        hv = self.calculator.calculate_hv(prices, window_days=7)
        
        assert hv > 0
        assert isinstance(hv, float)
    
    def test_calculate_hv_no_movement(self):
        """Test HV with no price movement."""
        prices = [100.0] * 31
        
        hv = self.calculator.calculate_hv(prices, window_days=30)
        
        assert hv == 0.0
    
    def test_calculate_hv_insufficient_data(self):
        """Test HV with insufficient data."""
        prices = [100.0, 101.0]
        
        hv = self.calculator.calculate_hv(prices, window_days=30)
        
        assert hv == 0.0
    
    def test_calculate_hv_high_volatility(self):
        """Test HV with high volatility prices."""
        # Prices with large swings
        prices = [100, 110, 95, 115, 90, 120, 85, 125]
        prices.reverse()
        
        hv = self.calculator.calculate_hv(prices, window_days=7)
        
        assert hv > 50  # Should indicate high volatility
    
    def test_calculate_parkinson_hv(self):
        """Test Parkinson HV calculation."""
        high_low_data = [
            (105, 95), (108, 98), (110, 100), (107, 97),
            (112, 102), (109, 99), (115, 105)
        ]
        
        hv = self.calculator.calculate_parkinson_hv(high_low_data, window_days=7)
        
        assert hv > 0
        assert isinstance(hv, float)
    
    def test_calculate_parkinson_hv_insufficient_data(self):
        """Test Parkinson HV with insufficient data."""
        high_low_data = [(105, 95)]
        
        hv = self.calculator.calculate_parkinson_hv(high_low_data, window_days=7)
        
        assert hv == 0.0


class TestSkewCalculator:
    """Tests for Skew calculator."""
    
    def setup_method(self):
        self.calculator = SkewCalculator()
    
    def test_calculate_skew_slope_downward(self):
        """Test skew slope with downward sloping data."""
        strikes = [90, 95, 100, 105, 110]
        ivs = [35, 32, 30, 28, 26]  # Decreasing IV
        
        slope = self.calculator.calculate_skew_slope(strikes, ivs)
        
        assert slope < 0  # Negative slope
    
    def test_calculate_skew_slope_upward(self):
        """Test skew slope with upward sloping data."""
        strikes = [90, 95, 100, 105, 110]
        ivs = [26, 28, 30, 32, 35]  # Increasing IV
        
        slope = self.calculator.calculate_skew_slope(strikes, ivs)
        
        assert slope > 0  # Positive slope
    
    def test_calculate_skew_slope_flat(self):
        """Test skew slope with flat data."""
        strikes = [90, 95, 100, 105, 110]
        ivs = [30, 30, 30, 30, 30]  # Flat IV
        
        slope = self.calculator.calculate_skew_slope(strikes, ivs)
        
        assert abs(slope) < 0.001  # Near zero
    
    def test_calculate_skew_slope_insufficient_data(self):
        """Test skew slope with insufficient data."""
        strikes = [100]
        ivs = [30]
        
        slope = self.calculator.calculate_skew_slope(strikes, ivs)
        
        assert slope == 0.0
    
    def test_classify_skew_type_normal(self):
        """Test normal skew classification."""
        put_skew_slope = -0.05
        call_skew_slope = -0.01
        put_call_ratio = 1.15
        
        skew_type = self.calculator.classify_skew_type(
            put_skew_slope, call_skew_slope, put_call_ratio
        )
        
        assert skew_type == "normal"
    
    def test_classify_skew_type_reverse(self):
        """Test reverse skew classification."""
        put_skew_slope = -0.01
        call_skew_slope = 0.05
        put_call_ratio = 0.85
        
        skew_type = self.calculator.classify_skew_type(
            put_skew_slope, call_skew_slope, put_call_ratio
        )
        
        assert skew_type == "reverse"
    
    def test_classify_skew_type_smile(self):
        """Test smile skew classification."""
        put_skew_slope = -0.05
        call_skew_slope = 0.05
        put_call_ratio = 1.02
        
        skew_type = self.calculator.classify_skew_type(
            put_skew_slope, call_skew_slope, put_call_ratio
        )
        
        assert skew_type == "smile"
    
    def test_classify_skew_type_flat(self):
        """Test flat skew classification."""
        put_skew_slope = 0.0
        call_skew_slope = 0.0
        put_call_ratio = 1.0
        
        skew_type = self.calculator.classify_skew_type(
            put_skew_slope, call_skew_slope, put_call_ratio
        )
        
        assert skew_type == "flat"
    
    def test_calculate_put_call_skew_ratio(self):
        """Test put/call skew ratio calculation."""
        put_ivs = [35, 32, 30]
        call_ivs = [28, 26, 24]
        
        ratio = self.calculator.calculate_put_call_skew_ratio(put_ivs, call_ivs)
        
        assert ratio > 1.0  # Puts should have higher IV
        assert isinstance(ratio, float)
    
    def test_calculate_put_call_skew_ratio_empty(self):
        """Test ratio with empty data."""
        put_ivs = []
        call_ivs = []
        
        ratio = self.calculator.calculate_put_call_skew_ratio(put_ivs, call_ivs)
        
        assert ratio == 1.0


class TestTermStructureCalculator:
    """Tests for Term Structure calculator."""
    
    def setup_method(self):
        self.calculator = TermStructureCalculator()
    
    def test_classify_term_structure_contango(self):
        """Test contango classification."""
        term_ivs = [(30, 25.0), (60, 28.0), (90, 30.0)]
        
        structure = self.calculator.classify_term_structure(term_ivs)
        
        assert structure == "contango"
    
    def test_classify_term_structure_backwardation(self):
        """Test backwardation classification."""
        term_ivs = [(30, 35.0), (60, 30.0), (90, 28.0)]
        
        structure = self.calculator.classify_term_structure(term_ivs)
        
        assert structure == "backwardation"
    
    def test_classify_term_structure_flat(self):
        """Test flat classification."""
        term_ivs = [(30, 30.0), (60, 30.5), (90, 30.2)]
        
        structure = self.calculator.classify_term_structure(term_ivs)
        
        assert structure == "flat"
    
    def test_classify_term_structure_insufficient_data(self):
        """Test with insufficient data."""
        term_ivs = [(30, 30.0)]
        
        structure = self.calculator.classify_term_structure(term_ivs)
        
        assert structure == "flat"


class TestVolatilitySurfaceCalculator:
    """Tests for Volatility Surface calculator."""
    
    def setup_method(self):
        self.calculator = VolatilitySurfaceCalculator()
    
    def test_calculate_surface_curvature(self):
        """Test surface curvature calculation."""
        surface_points = [
            (90, 30, 35.0),
            (95, 30, 32.0),
            (100, 30, 30.0),
            (105, 30, 32.0),
            (110, 30, 35.0)
        ]
        
        curvature = self.calculator.calculate_surface_curvature(surface_points)
        
        assert curvature > 0  # Should show positive curvature (smile)
        assert isinstance(curvature, float)
    
    def test_calculate_surface_curvature_flat(self):
        """Test curvature with flat surface."""
        surface_points = [
            (90, 30, 30.0),
            (95, 30, 30.0),
            (100, 30, 30.0),
            (105, 30, 30.0),
            (110, 30, 30.0)
        ]
        
        curvature = self.calculator.calculate_surface_curvature(surface_points)
        
        assert curvature == 0.0
    
    def test_calculate_surface_curvature_insufficient_data(self):
        """Test curvature with insufficient data."""
        surface_points = [(100, 30, 30.0)]
        
        curvature = self.calculator.calculate_surface_curvature(surface_points)
        
        assert curvature == 0.0
    
    def test_interpolate_surface(self):
        """Test surface interpolation."""
        known_points = [
            (95, 30, 32.0),
            (100, 30, 30.0),
            (105, 30, 32.0),
            (100, 60, 28.0)
        ]
        
        grid_strikes = np.array([95, 100, 105])
        grid_dtes = np.array([30, 60])
        
        surface = self.calculator.interpolate_surface(
            known_points, grid_strikes, grid_dtes
        )
        
        assert surface.shape == (len(grid_dtes), len(grid_strikes))


class TestIVConditionClassifier:
    """Tests for IV Condition classifier."""
    
    def setup_method(self):
        self.classifier = IVConditionClassifier()
    
    def test_classify_condition_extremely_high(self):
        """Test extremely high IV classification."""
        condition = self.classifier.classify_condition(iv_rank=85, iv_percentile=90)
        
        assert condition == "extremely_high"
    
    def test_classify_condition_high(self):
        """Test high IV classification."""
        condition = self.classifier.classify_condition(iv_rank=65, iv_percentile=70)
        
        assert condition == "high"
    
    def test_classify_condition_normal(self):
        """Test normal IV classification."""
        condition = self.classifier.classify_condition(iv_rank=50, iv_percentile=50)
        
        assert condition == "normal"
    
    def test_classify_condition_low(self):
        """Test low IV classification."""
        condition = self.classifier.classify_condition(iv_rank=25, iv_percentile=30)
        
        assert condition == "low"
    
    def test_classify_condition_extremely_low(self):
        """Test extremely low IV classification."""
        condition = self.classifier.classify_condition(iv_rank=10, iv_percentile=15)
        
        assert condition == "extremely_low"
    
    def test_calculate_iv_hv_ratio(self):
        """Test IV/HV ratio calculation."""
        ratio = self.classifier.calculate_iv_hv_ratio(
            current_iv=30.0, historical_vol=20.0
        )
        
        assert ratio == 1.5
    
    def test_calculate_iv_hv_ratio_zero_hv(self):
        """Test ratio with zero HV."""
        ratio = self.classifier.calculate_iv_hv_ratio(
            current_iv=30.0, historical_vol=0.0
        )
        
        assert ratio == 1.0
    
    def test_calculate_iv_hv_ratio_equal(self):
        """Test ratio when IV equals HV."""
        ratio = self.classifier.calculate_iv_hv_ratio(
            current_iv=25.0, historical_vol=25.0
        )
        
        assert ratio == 1.0
