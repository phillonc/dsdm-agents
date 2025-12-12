"""
Integration tests for Volatility Compass API.
"""
import pytest
from datetime import datetime, timedelta
import numpy as np

from src.api import VolatilityCompassAPI


class TestVolatilityCompassAPIIntegration:
    """Integration tests for the complete API."""
    
    def setup_method(self):
        self.api = VolatilityCompassAPI()
    
    def create_test_data(self):
        """Create comprehensive test data."""
        # Generate realistic IV history
        iv_history = []
        base_iv = 30.0
        for i in range(252):
            variation = np.random.normal(0, 3)
            iv = max(15, min(50, base_iv + variation))
            iv_history.append(iv)
        
        # Generate price history
        price_history = []
        base_price = 150.0
        for i in range(100):
            change = np.random.normal(0, 0.015)
            price = base_price * (1 + change)
            price_history.append(price)
            base_price = price
        
        # Create options chain
        base_date = datetime.now()
        options_chain = {
            'expirations': []
        }
        
        for days in [30, 60, 90]:
            exp_data = {
                'expiration_date': base_date + timedelta(days=days),
                'days_to_expiration': days,
                'atm_strike': 150.0,
                'atm_iv': 30.0 - (days * 0.02),  # Term structure
                'strikes': list(range(130, 171, 5)),
                'total_volume': 10000,
                'total_oi': 50000,
                'calls': [],
                'puts': []
            }
            
            # Generate options data with skew
            for strike in range(145, 166, 5):
                # Calls - decreasing IV as strike increases
                call_iv = 30.0 - ((strike - 145) * 0.2)
                exp_data['calls'].append({
                    'strike': strike,
                    'iv': max(20, call_iv),
                    'delta': 0.5 - ((strike - 150) * 0.05)
                })
                
                # Puts - increasing IV as strike decreases
                put_iv = 30.0 + ((150 - strike) * 0.3)
                exp_data['puts'].append({
                    'strike': strike,
                    'iv': min(45, put_iv),
                    'delta': -0.5 + ((strike - 150) * 0.05)
                })
            
            options_chain['expirations'].append(exp_data)
        
        return iv_history, price_history, options_chain
    
    def test_get_volatility_analysis_complete(self):
        """Test complete volatility analysis workflow."""
        symbol = "AAPL"
        current_iv = 35.0
        iv_history, price_history, options_chain = self.create_test_data()
        
        result = self.api.get_volatility_analysis(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history,
            options_chain=options_chain,
            previous_iv=30.0
        )
        
        # Verify structure
        assert 'symbol' in result
        assert result['symbol'] == symbol
        assert 'metrics' in result
        assert 'term_structure' in result
        assert 'strategies' in result
        assert 'alerts' in result
        
        # Verify metrics
        metrics = result['metrics']
        assert 'iv_rank' in metrics
        assert 'iv_percentile' in metrics
        assert 'condition' in metrics
        assert 0 <= metrics['iv_rank'] <= 100
        assert 0 <= metrics['iv_percentile'] <= 100
        
        # Verify strategies exist
        assert len(result['strategies']) > 0
        
        # Verify strategy structure
        strategy = result['strategies'][0]
        assert 'type' in strategy
        assert 'confidence' in strategy
        assert 'suggested_actions' in strategy
    
    def test_get_iv_metrics_fast(self):
        """Test fast IV metrics retrieval."""
        symbol = "MSFT"
        current_iv = 28.0
        iv_history, price_history, _ = self.create_test_data()
        
        result = self.api.get_iv_metrics(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history
        )
        
        assert result['symbol'] == symbol
        assert result['current_iv'] == current_iv
        assert 'iv_rank' in result
        assert 'iv_percentile' in result
        assert 'historical_volatility' in result
        assert 'iv_hv_ratio' in result
        assert 'condition' in result
        
        # Verify HV structure
        hv = result['historical_volatility']
        assert '30d' in hv
        assert '60d' in hv
        assert '90d' in hv
    
    def test_get_trading_strategies(self):
        """Test strategy recommendations."""
        symbol = "GOOGL"
        current_iv = 40.0  # High IV
        iv_history = [40.0] + [25.0] * 251  # Will have high IV rank
        price_history = [120.0] * 100
        
        strategies = self.api.get_trading_strategies(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history
        )
        
        assert len(strategies) > 0
        
        # With high IV, should recommend selling premium
        primary_strategy = strategies[0]
        assert 'sell' in primary_strategy['name'].lower() or primary_strategy['type'] == 'sell_premium'
        assert primary_strategy['confidence'] > 50
    
    def test_get_quick_recommendation(self):
        """Test quick recommendation."""
        # High IV
        rec_high = self.api.get_quick_recommendation(85)
        assert 'SELL' in rec_high or 'Sell' in rec_high
        
        # Low IV
        rec_low = self.api.get_quick_recommendation(15)
        assert 'BUY' in rec_low or 'Buy' in rec_low
        
        # Neutral
        rec_neutral = self.api.get_quick_recommendation(50)
        assert 'Neutral' in rec_neutral or 'neutral' in rec_neutral
    
    def test_analyze_watchlist(self):
        """Test watchlist analysis."""
        watchlist_name = "Tech Portfolio"
        
        # Create data for multiple symbols
        symbols_data = {}
        for symbol, base_iv in [('AAPL', 30), ('MSFT', 45), ('GOOGL', 20)]:
            iv_history, price_history, _ = self.create_test_data()
            # Adjust first value to match base_iv
            iv_history[0] = base_iv
            
            symbols_data[symbol] = {
                'current_iv': base_iv,
                'iv_history': iv_history,
                'price_history': price_history,
                'previous_iv': base_iv - 2
            }
        
        result = self.api.analyze_watchlist(watchlist_name, symbols_data)
        
        assert result['watchlist_name'] == watchlist_name
        assert result['total_symbols'] == 3
        assert 'summary' in result
        assert 'opportunities' in result
        assert 'symbol_details' in result
        
        # Verify opportunities
        opportunities = result['opportunities']
        assert 'premium_selling' in opportunities
        assert 'premium_buying' in opportunities
        
        # High IV symbol should be in selling opportunities
        selling_symbols = [opp['symbol'] for opp in opportunities['premium_selling']]
        assert 'MSFT' in selling_symbols  # Highest IV
    
    def test_get_volatility_alerts(self):
        """Test alert detection."""
        symbol = "TSLA"
        current_iv = 40.0
        previous_iv = 30.0  # 33% increase - should trigger alert
        iv_history, price_history, _ = self.create_test_data()
        
        alerts = self.api.get_volatility_alerts(
            symbol=symbol,
            current_iv=current_iv,
            iv_history=iv_history,
            price_history=price_history,
            previous_iv=previous_iv
        )
        
        assert len(alerts) > 0
        
        # Should have IV spike alert
        alert_types = [a['type'] for a in alerts]
        assert 'iv_spike' in alert_types
        
        # Verify alert structure
        alert = alerts[0]
        assert 'alert_id' in alert
        assert 'symbol' in alert
        assert 'severity' in alert
        assert 'message' in alert
    
    def test_get_skew_analysis(self):
        """Test skew analysis."""
        symbol = "AAPL"
        _, _, options_chain = self.create_test_data()
        
        skew_analyses = self.api.get_skew_analysis(symbol, options_chain)
        
        assert len(skew_analyses) > 0
        
        skew = skew_analyses[0]
        assert skew['symbol'] == symbol
        assert 'skew_type' in skew
        assert 'put_call_ratio' in skew
        assert 'visualization_data' in skew
        
        # Verify visualization data
        viz = skew['visualization_data']
        assert 'call_strikes' in viz
        assert 'call_ivs' in viz
        assert 'put_strikes' in viz
        assert 'put_ivs' in viz
    
    def test_get_term_structure(self):
        """Test term structure analysis."""
        symbol = "MSFT"
        current_price = 300.0
        _, _, options_chain = self.create_test_data()
        
        term_structure = self.api.get_term_structure(
            symbol, current_price, options_chain
        )
        
        assert term_structure['symbol'] == symbol
        assert term_structure['current_price'] == current_price
        assert 'structure_shape' in term_structure
        assert term_structure['structure_shape'] in ['contango', 'backwardation', 'flat']
        assert 'term_points' in term_structure
        assert len(term_structure['term_points']) > 0
        
        # Verify term points are sorted by DTE
        dtes = [tp['days_to_expiration'] for tp in term_structure['term_points']]
        assert dtes == sorted(dtes)
    
    def test_get_volatility_surface(self):
        """Test volatility surface generation."""
        symbol = "GOOGL"
        current_price = 120.0
        _, _, options_chain = self.create_test_data()
        
        surface = self.api.get_volatility_surface(
            symbol, current_price, options_chain
        )
        
        assert surface['symbol'] == symbol
        assert surface['current_price'] == current_price
        assert 'surface_points' in surface
        assert len(surface['surface_points']) > 0
        assert 'strike_range' in surface
        assert surface['strike_range']['min'] < surface['strike_range']['max']
        
        # Verify surface point structure
        point = surface['surface_points'][0]
        assert 'strike' in point
        assert 'days_to_expiration' in point
        assert 'implied_volatility' in point
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        symbol = "AAPL"
        current_iv = 32.0
        previous_iv = 28.0
        iv_history, price_history, options_chain = self.create_test_data()
        
        # 1. Get quick metrics
        metrics = self.api.get_iv_metrics(
            symbol, current_iv, iv_history, price_history
        )
        assert metrics['iv_rank'] >= 0
        
        # 2. Get detailed analysis
        analysis = self.api.get_volatility_analysis(
            symbol, current_iv, iv_history, price_history,
            options_chain, previous_iv
        )
        assert len(analysis['strategies']) > 0
        
        # 3. Check for alerts
        alerts = self.api.get_volatility_alerts(
            symbol, current_iv, iv_history, price_history, previous_iv
        )
        # May or may not have alerts
        
        # 4. Get specific analyses
        skew = self.api.get_skew_analysis(symbol, options_chain)
        assert len(skew) > 0
        
        term_structure = self.api.get_term_structure(
            symbol, price_history[0], options_chain
        )
        assert term_structure['structure_shape'] is not None
        
        surface = self.api.get_volatility_surface(
            symbol, price_history[0], options_chain
        )
        assert len(surface['surface_points']) > 0
        
        # All components should work together
        assert analysis['symbol'] == metrics['symbol'] == symbol
    
    def test_watchlist_with_mixed_volatility(self):
        """Test watchlist with mixed volatility conditions."""
        watchlist_name = "Mixed Volatility"
        
        iv_history_base, price_history, _ = self.create_test_data()
        
        symbols_data = {
            'HIGH_IV': {
                'current_iv': 45.0,
                'iv_history': [45.0] + [25.0] * 251,
                'price_history': price_history,
                'previous_iv': 44.0
            },
            'LOW_IV': {
                'current_iv': 15.0,
                'iv_history': [15.0] + [30.0] * 251,
                'price_history': price_history,
                'previous_iv': 16.0
            },
            'NORMAL_IV': {
                'current_iv': 30.0,
                'iv_history': [30.0] * 252,
                'price_history': price_history,
                'previous_iv': 30.0
            }
        }
        
        result = self.api.analyze_watchlist(watchlist_name, symbols_data)
        
        # Verify categorization
        opportunities = result['opportunities']
        
        selling_symbols = [opp['symbol'] for opp in opportunities['premium_selling']]
        buying_symbols = [opp['symbol'] for opp in opportunities['premium_buying']]
        
        assert 'HIGH_IV' in selling_symbols
        assert 'LOW_IV' in buying_symbols
        
        # Verify IV ranks are calculated correctly
        assert result['symbol_details']['HIGH_IV']['iv_rank'] > 70
        assert result['symbol_details']['LOW_IV']['iv_rank'] < 30
