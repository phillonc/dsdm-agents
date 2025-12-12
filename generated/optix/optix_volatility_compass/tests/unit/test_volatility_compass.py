"""
Unit tests for main Volatility Compass orchestrator.
"""
import pytest
from datetime import datetime, timedelta

from src.volatility_compass import VolatilityCompass
from src.models import VolatilityCondition


class TestVolatilityCompass:
    """Tests for Volatility Compass main class."""
    
    def setup_method(self):
        self.compass = VolatilityCompass()
    
    def create_sample_options_chain(self):
        """Create sample options chain data for testing."""
        base_date = datetime.now()
        
        return {
            'expirations': [
                {
                    'expiration_date': base_date + timedelta(days=30),
                    'days_to_expiration': 30,
                    'atm_strike': 150.0,
                    'atm_iv': 30.0,
                    'strikes': [140, 145, 150, 155, 160],
                    'total_volume': 10000,
                    'total_oi': 50000,
                    'calls': [
                        {'strike': 150, 'iv': 30.0, 'delta': 0.50},
                        {'strike': 155, 'iv': 28.0, 'delta': 0.35},
                        {'strike': 160, 'iv': 26.0, 'delta': 0.20}
                    ],
                    'puts': [
                        {'strike': 150, 'iv': 30.0, 'delta': -0.50},
                        {'strike': 145, 'iv': 33.0, 'delta': -0.65},
                        {'strike': 140, 'iv': 36.0, 'delta': -0.80}
                    ]
                },
                {
                    'expiration_date': base_date + timedelta(days=60),
                    'days_to_expiration': 60,
                    'atm_strike': 150.0,
                    'atm_iv': 28.0,
                    'strikes': [140, 145, 150, 155, 160],
                    'total_volume': 5000,
                    'total_oi': 30000,
                    'calls': [
                        {'strike': 150, 'iv': 28.0, 'delta': 0.50},
                        {'strike': 155, 'iv': 27.0, 'delta': 0.35},
                        {'strike': 160, 'iv': 26.0, 'delta': 0.20}
                    ],
                    'puts': [
                        {'strike': 150, 'iv': 28.0, 'delta': -0.50},
                        {'strike': 145, 'iv': 30.0, 'delta': -0.65},
                        {'strike': 140, 'iv': 32.0, 'delta': -0.80}
                    ]
                }
            ]
        }
    
    def create_sample_iv_history(self, current_iv=30.0, days=100):
        """Create sample IV history."""
        import numpy as np
        
        # Create some variation around current IV
        history = []
        for i in range(days):
            variation = np.random.uniform(-5, 5)
            iv = max(15, min(45, current_iv + variation))
            history.append(iv)
        
        history[0] = current_iv  # Ensure first value is current
        return history
    
    def create_sample_price_history(self, current_price=150.0, days=100):
        """Create sample price history."""
        import numpy as np
        
        prices = [current_price]
        for i in range(days - 1):
            change = np.random.uniform(-0.02, 0.02)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        return prices
    
    def test_analyze_symbol_complete(self):
        """Test complete symbol analysis."""
        symbol = "AAPL"
        current_iv = 30.0
        iv_history = self.create_sample_iv_history(30.0, 252)
        price_history = self.create_sample_price_history(150.0, 100)
        options_chain = self.create_sample_options_chain()
        
        report = self.compass.analyze_symbol(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history,
            options_chain=options_chain
        )
        
        # Verify report structure
        assert report.symbol == symbol
        assert report.metrics is not None
        assert report.term_structure is not None
        assert len(report.skew_analysis) > 0
        assert report.surface is not None
        assert len(report.strategies) > 0
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        symbol = "AAPL"
        current_iv = 35.0
        iv_history = self.create_sample_iv_history(35.0, 252)
        price_history = self.create_sample_price_history(150.0, 100)
        timestamp = datetime.now()
        
        metrics = self.compass._calculate_metrics(
            symbol, current_iv, iv_history, price_history, timestamp
        )
        
        assert metrics.symbol == symbol
        assert metrics.current_iv == current_iv
        assert 0 <= metrics.iv_rank <= 100
        assert 0 <= metrics.iv_percentile <= 100
        assert metrics.historical_volatility_30d >= 0
        assert metrics.historical_volatility_60d >= 0
        assert metrics.historical_volatility_90d >= 0
        assert metrics.iv_hv_ratio > 0
        assert isinstance(metrics.condition, VolatilityCondition)
    
    def test_analyze_term_structure(self):
        """Test term structure analysis."""
        symbol = "AAPL"
        current_price = 150.0
        options_chain = self.create_sample_options_chain()
        timestamp = datetime.now()
        
        term_structure = self.compass._analyze_term_structure(
            symbol, current_price, options_chain, timestamp
        )
        
        assert term_structure.symbol == symbol
        assert term_structure.current_price == current_price
        assert len(term_structure.term_points) > 0
        assert term_structure.structure_shape in ["contango", "backwardation", "flat"]
        assert term_structure.front_month_iv > 0
        assert term_structure.back_month_iv > 0
    
    def test_analyze_skew(self):
        """Test skew analysis."""
        symbol = "AAPL"
        options_chain = self.create_sample_options_chain()
        
        skew_analyses = self.compass._analyze_skew(symbol, options_chain)
        
        assert len(skew_analyses) > 0
        
        for skew in skew_analyses:
            assert skew.symbol == symbol
            assert skew.days_to_expiration > 0
            assert skew.atm_strike > 0
            assert skew.atm_iv > 0
            assert skew.skew_type in ["normal", "reverse", "flat", "smile"]
            assert skew.put_call_skew_ratio > 0
    
    def test_build_volatility_surface(self):
        """Test volatility surface construction."""
        symbol = "AAPL"
        current_price = 150.0
        options_chain = self.create_sample_options_chain()
        timestamp = datetime.now()
        
        surface = self.compass._build_volatility_surface(
            symbol, current_price, options_chain, timestamp
        )
        
        assert surface.symbol == symbol
        assert surface.current_price == current_price
        assert len(surface.surface_points) > 0
        assert len(surface.expirations) > 0
        assert surface.min_strike < surface.max_strike
        assert surface.surface_curvature >= 0
    
    def test_analyze_watchlist(self):
        """Test watchlist analysis."""
        watchlist_name = "Tech Stocks"
        
        symbols_data = {
            'AAPL': {
                'current_iv': 30.0,
                'iv_history': self.create_sample_iv_history(30.0, 100),
                'price_history': self.create_sample_price_history(150.0, 100),
                'previous_iv': 28.0
            },
            'MSFT': {
                'current_iv': 35.0,
                'iv_history': self.create_sample_iv_history(35.0, 100),
                'price_history': self.create_sample_price_history(300.0, 100),
                'previous_iv': 32.0
            },
            'GOOGL': {
                'current_iv': 25.0,
                'iv_history': self.create_sample_iv_history(25.0, 100),
                'price_history': self.create_sample_price_history(120.0, 100),
                'previous_iv': 26.0
            }
        }
        
        analysis = self.compass.analyze_watchlist(watchlist_name, symbols_data)
        
        assert analysis.watchlist_name == watchlist_name
        assert len(analysis.symbols) == 3
        assert len(analysis.symbol_metrics) == 3
        assert analysis.average_iv_rank >= 0
        assert analysis.average_iv_percentile >= 0
        assert isinstance(analysis.high_iv_symbols, list)
        assert isinstance(analysis.low_iv_symbols, list)
        assert isinstance(analysis.premium_selling_candidates, list)
        assert isinstance(analysis.premium_buying_candidates, list)
    
    def test_analyze_watchlist_categorization(self):
        """Test that watchlist analysis correctly categorizes stocks."""
        watchlist_name = "Test Watchlist"
        
        symbols_data = {
            'HIGH_IV': {
                'current_iv': 45.0,
                'iv_history': [45.0] + [30.0] * 99,  # High IV rank
                'price_history': self.create_sample_price_history(100.0, 100),
                'previous_iv': 40.0
            },
            'LOW_IV': {
                'current_iv': 15.0,
                'iv_history': [15.0] + [30.0] * 99,  # Low IV rank
                'price_history': self.create_sample_price_history(100.0, 100),
                'previous_iv': 16.0
            }
        }
        
        analysis = self.compass.analyze_watchlist(watchlist_name, symbols_data)
        
        # Check categorization
        assert 'HIGH_IV' in analysis.high_iv_symbols
        assert 'LOW_IV' in analysis.low_iv_symbols
        
        # Check opportunities
        selling_symbols = [s for s, _ in analysis.premium_selling_candidates]
        buying_symbols = [s for s, _ in analysis.premium_buying_candidates]
        
        assert 'HIGH_IV' in selling_symbols
        assert 'LOW_IV' in buying_symbols
    
    def test_find_atm_strike(self):
        """Test ATM strike finder."""
        strikes = [140, 145, 150, 155, 160]
        
        # Test exact match
        atm = self.compass._find_atm_strike(150.0, strikes)
        assert atm == 150.0
        
        # Test between strikes (should pick closest)
        atm = self.compass._find_atm_strike(152.0, strikes)
        assert atm == 150.0
        
        atm = self.compass._find_atm_strike(153.0, strikes)
        assert atm == 155.0
    
    def test_find_atm_strike_empty(self):
        """Test ATM strike with empty strikes list."""
        atm = self.compass._find_atm_strike(150.0, [])
        assert atm == 150.0
    
    def test_build_rank_history(self):
        """Test IV rank history building."""
        iv_history = self.create_sample_iv_history(30.0, 60)
        
        rank_history = self.compass._build_rank_history(iv_history, days=30)
        
        assert len(rank_history) <= 30
        for date, rank in rank_history:
            assert isinstance(date, datetime)
            assert 0 <= rank <= 100
    
    def test_build_percentile_history(self):
        """Test IV percentile history building."""
        iv_history = self.create_sample_iv_history(30.0, 60)
        
        percentile_history = self.compass._build_percentile_history(iv_history, days=30)
        
        assert len(percentile_history) <= 30
        for date, percentile in percentile_history:
            assert isinstance(date, datetime)
            assert 0 <= percentile <= 100
    
    def test_analyze_symbol_with_alerts(self):
        """Test that analysis includes alerts when IV changes."""
        symbol = "AAPL"
        current_iv = 36.0
        previous_iv = 30.0
        iv_history = self.create_sample_iv_history(36.0, 252)
        price_history = self.create_sample_price_history(150.0, 100)
        options_chain = self.create_sample_options_chain()
        
        report = self.compass.analyze_symbol(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history,
            options_chain=options_chain,
            previous_iv=previous_iv
        )
        
        # Should have alerts due to IV spike
        assert len(report.alerts) > 0
    
    def test_comprehensive_report_structure(self):
        """Test that complete report has all required components."""
        symbol = "AAPL"
        current_iv = 30.0
        iv_history = self.create_sample_iv_history(30.0, 252)
        price_history = self.create_sample_price_history(150.0, 100)
        options_chain = self.create_sample_options_chain()
        
        report = self.compass.analyze_symbol(
            symbol, current_iv, iv_history, price_history, options_chain
        )
        
        # Check all report components exist
        assert hasattr(report, 'symbol')
        assert hasattr(report, 'timestamp')
        assert hasattr(report, 'metrics')
        assert hasattr(report, 'term_structure')
        assert hasattr(report, 'skew_analysis')
        assert hasattr(report, 'surface')
        assert hasattr(report, 'strategies')
        assert hasattr(report, 'alerts')
        assert hasattr(report, 'iv_rank_history')
        assert hasattr(report, 'iv_percentile_history')
        
        # Verify data types
        assert isinstance(report.skew_analysis, list)
        assert isinstance(report.strategies, list)
        assert isinstance(report.alerts, list)
        assert isinstance(report.iv_rank_history, list)
        assert isinstance(report.iv_percentile_history, list)
