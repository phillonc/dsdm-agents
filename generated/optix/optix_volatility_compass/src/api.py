"""
API interface for Volatility Compass.
Provides high-level functions for integration with OPTIX Trading Platform.
"""
from typing import List, Dict, Optional
from datetime import datetime

from .volatility_compass import VolatilityCompass
from .models import VolatilityCompassReport, WatchlistVolatilityAnalysis


class VolatilityCompassAPI:
    """
    Main API interface for Volatility Compass feature.
    Provides simplified access to volatility analysis capabilities.
    """
    
    def __init__(self):
        """Initialize the Volatility Compass API."""
        self.compass = VolatilityCompass()
    
    def get_volatility_analysis(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float],
        options_chain: Dict,
        previous_iv: Optional[float] = None
    ) -> Dict:
        """
        Get comprehensive volatility analysis for a symbol.
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility (%)
            iv_history: Historical IV values (most recent first)
            price_history: Historical prices (most recent first)
            options_chain: Options chain data structure
            previous_iv: Previous IV for change detection
            
        Returns:
            Dictionary with complete volatility analysis
        """
        report = self.compass.analyze_symbol(
            symbol, current_iv, iv_history, price_history,
            options_chain, previous_iv
        )
        
        return self._serialize_report(report)
    
    def get_iv_metrics(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float]
    ) -> Dict:
        """
        Get core IV metrics only (faster, no options chain required).
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility
            iv_history: Historical IV values
            price_history: Historical prices
            
        Returns:
            Dictionary with IV Rank, Percentile, HV comparison, etc.
        """
        metrics = self.compass._calculate_metrics(
            symbol, current_iv, iv_history, price_history, datetime.now()
        )
        
        return {
            'symbol': metrics.symbol,
            'timestamp': metrics.timestamp.isoformat(),
            'current_iv': metrics.current_iv,
            'iv_rank': metrics.iv_rank,
            'iv_percentile': metrics.iv_percentile,
            'historical_volatility': {
                '30d': metrics.historical_volatility_30d,
                '60d': metrics.historical_volatility_60d,
                '90d': metrics.historical_volatility_90d
            },
            'iv_hv_ratio': metrics.iv_hv_ratio,
            'condition': metrics.condition.value,
            'averages': {
                'iv_30d': metrics.average_iv_30d,
                'iv_60d': metrics.average_iv_60d
            },
            'extremes_52w': {
                'min': metrics.min_iv_52w,
                'max': metrics.max_iv_52w
            }
        }
    
    def get_trading_strategies(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float],
        options_chain: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get trading strategy recommendations based on volatility.
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility
            iv_history: Historical IV values
            price_history: Historical prices
            options_chain: Optional options chain for enhanced analysis
            
        Returns:
            List of strategy recommendations with confidence scores
        """
        metrics = self.compass._calculate_metrics(
            symbol, current_iv, iv_history, price_history, datetime.now()
        )
        
        # Enhanced analysis with skew if options chain provided
        skew = None
        term_structure = None
        if options_chain:
            skew_analyses = self.compass._analyze_skew(symbol, options_chain)
            skew = skew_analyses[0] if skew_analyses else None
            
            term_structure = self.compass._analyze_term_structure(
                symbol, price_history[0], options_chain, datetime.now()
            )
        
        strategies = self.compass.strategy_engine.generate_strategies(
            metrics, skew, term_structure
        )
        
        return [self._serialize_strategy(s) for s in strategies]
    
    def get_quick_recommendation(self, iv_rank: float) -> str:
        """
        Get a quick one-line trading recommendation.
        
        Args:
            iv_rank: Current IV Rank (0-100)
            
        Returns:
            Quick recommendation string
        """
        return self.compass.strategy_engine.get_quick_recommendation(iv_rank)
    
    def analyze_watchlist(
        self,
        watchlist_name: str,
        symbols_data: Dict[str, Dict]
    ) -> Dict:
        """
        Analyze multiple symbols for volatility opportunities.
        
        Args:
            watchlist_name: Name of the watchlist
            symbols_data: Dict mapping symbols to their data
                Each symbol should have: current_iv, iv_history, price_history
            
        Returns:
            Dictionary with watchlist analysis and opportunities
        """
        analysis = self.compass.analyze_watchlist(watchlist_name, symbols_data)
        
        return {
            'watchlist_name': analysis.watchlist_name,
            'timestamp': analysis.timestamp.isoformat(),
            'total_symbols': len(analysis.symbols),
            'summary': {
                'average_iv_rank': analysis.average_iv_rank,
                'average_iv_percentile': analysis.average_iv_percentile,
                'high_iv_count': len(analysis.high_iv_symbols),
                'low_iv_count': len(analysis.low_iv_symbols)
            },
            'opportunities': {
                'premium_selling': [
                    {'symbol': sym, 'iv_rank': rank}
                    for sym, rank in analysis.premium_selling_candidates
                ],
                'premium_buying': [
                    {'symbol': sym, 'iv_rank': rank}
                    for sym, rank in analysis.premium_buying_candidates
                ]
            },
            'alerts': [self._serialize_alert(a) for a in analysis.active_alerts],
            'symbol_details': {
                sym: self._serialize_metrics(metrics)
                for sym, metrics in analysis.symbol_metrics.items()
            }
        }
    
    def get_volatility_alerts(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float],
        previous_iv: Optional[float] = None
    ) -> List[Dict]:
        """
        Check for volatility alerts.
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility
            iv_history: Historical IV values
            price_history: Historical prices
            previous_iv: Previous IV for change detection
            
        Returns:
            List of active alerts
        """
        metrics = self.compass._calculate_metrics(
            symbol, current_iv, iv_history, price_history, datetime.now()
        )
        
        alerts = self.compass.alert_engine.check_alerts(
            symbol, metrics, previous_iv=previous_iv
        )
        
        return [self._serialize_alert(a) for a in alerts]
    
    def get_skew_analysis(
        self,
        symbol: str,
        options_chain: Dict
    ) -> List[Dict]:
        """
        Get volatility skew analysis across expirations.
        
        Args:
            symbol: Stock symbol
            options_chain: Options chain data
            
        Returns:
            List of skew analyses for different expirations
        """
        skew_analyses = self.compass._analyze_skew(symbol, options_chain)
        
        return [
            {
                'symbol': skew.symbol,
                'expiration_date': skew.expiration_date.isoformat(),
                'days_to_expiration': skew.days_to_expiration,
                'atm_strike': skew.atm_strike,
                'atm_iv': skew.atm_iv,
                'put_call_ratio': skew.put_call_skew_ratio,
                'skew_type': skew.skew_type,
                'call_skew_slope': skew.call_skew_slope,
                'put_skew_slope': skew.put_skew_slope,
                'visualization_data': {
                    'call_strikes': skew.call_strikes,
                    'call_ivs': skew.call_ivs,
                    'put_strikes': skew.put_strikes,
                    'put_ivs': skew.put_ivs
                }
            }
            for skew in skew_analyses
        ]
    
    def get_term_structure(
        self,
        symbol: str,
        current_price: float,
        options_chain: Dict
    ) -> Dict:
        """
        Get volatility term structure analysis.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Options chain data
            
        Returns:
            Term structure analysis with visualization data
        """
        term_structure = self.compass._analyze_term_structure(
            symbol, current_price, options_chain, datetime.now()
        )
        
        return {
            'symbol': term_structure.symbol,
            'timestamp': term_structure.timestamp.isoformat(),
            'current_price': term_structure.current_price,
            'structure_shape': term_structure.structure_shape,
            'front_month_iv': term_structure.front_month_iv,
            'back_month_iv': term_structure.back_month_iv,
            'slope': term_structure.term_structure_slope,
            'term_points': [
                {
                    'expiration_date': tp.expiration_date.isoformat(),
                    'days_to_expiration': tp.days_to_expiration,
                    'atm_iv': tp.atm_iv,
                    'call_iv_avg': tp.call_iv_avg,
                    'put_iv_avg': tp.put_iv_avg,
                    'volume': tp.volume,
                    'open_interest': tp.open_interest
                }
                for tp in term_structure.term_points
            ]
        }
    
    def get_volatility_surface(
        self,
        symbol: str,
        current_price: float,
        options_chain: Dict
    ) -> Dict:
        """
        Get 3D volatility surface data.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            options_chain: Options chain data
            
        Returns:
            Volatility surface data for 3D visualization
        """
        surface = self.compass._build_volatility_surface(
            symbol, current_price, options_chain, datetime.now()
        )
        
        return {
            'symbol': surface.symbol,
            'timestamp': surface.timestamp.isoformat(),
            'current_price': surface.current_price,
            'strike_range': {
                'min': surface.min_strike,
                'max': surface.max_strike
            },
            'curvature': surface.surface_curvature,
            'expirations': [exp.isoformat() for exp in surface.expirations],
            'surface_points': [
                {
                    'strike': pt.strike,
                    'days_to_expiration': pt.days_to_expiration,
                    'implied_volatility': pt.implied_volatility,
                    'delta': pt.delta,
                    'moneyness': pt.moneyness
                }
                for pt in surface.surface_points
            ]
        }
    
    # Serialization helpers
    
    def _serialize_report(self, report: VolatilityCompassReport) -> Dict:
        """Serialize complete report to dictionary."""
        return {
            'symbol': report.symbol,
            'timestamp': report.timestamp.isoformat(),
            'metrics': self._serialize_metrics(report.metrics),
            'term_structure': {
                'shape': report.term_structure.structure_shape,
                'front_month_iv': report.term_structure.front_month_iv,
                'back_month_iv': report.term_structure.back_month_iv,
                'slope': report.term_structure.term_structure_slope
            },
            'skew_summary': {
                'primary_expiration': {
                    'skew_type': report.skew_analysis[0].skew_type,
                    'put_call_ratio': report.skew_analysis[0].put_call_skew_ratio
                } if report.skew_analysis else None
            },
            'strategies': [self._serialize_strategy(s) for s in report.strategies],
            'alerts': [self._serialize_alert(a) for a in report.alerts],
            'historical_context': {
                'iv_rank_trend': report.iv_rank_history[-10:] if len(report.iv_rank_history) > 10 else report.iv_rank_history,
                'iv_percentile_trend': report.iv_percentile_history[-10:] if len(report.iv_percentile_history) > 10 else report.iv_percentile_history
            }
        }
    
    def _serialize_metrics(self, metrics) -> Dict:
        """Serialize metrics to dictionary."""
        return {
            'current_iv': metrics.current_iv,
            'iv_rank': metrics.iv_rank,
            'iv_percentile': metrics.iv_percentile,
            'historical_volatility': {
                '30d': metrics.historical_volatility_30d,
                '60d': metrics.historical_volatility_60d,
                '90d': metrics.historical_volatility_90d
            },
            'iv_hv_ratio': metrics.iv_hv_ratio,
            'condition': metrics.condition.value
        }
    
    def _serialize_strategy(self, strategy) -> Dict:
        """Serialize strategy to dictionary."""
        return {
            'type': strategy.strategy_type.value,
            'name': strategy.strategy_name,
            'confidence': strategy.confidence,
            'description': strategy.description,
            'reasoning': strategy.reasoning,
            'suggested_actions': strategy.suggested_actions,
            'risk_level': strategy.risk_level
        }
    
    def _serialize_alert(self, alert) -> Dict:
        """Serialize alert to dictionary."""
        return {
            'alert_id': alert.alert_id,
            'symbol': alert.symbol,
            'timestamp': alert.timestamp.isoformat(),
            'type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'current_value': alert.current_value,
            'change_percent': alert.change_percent
        }
