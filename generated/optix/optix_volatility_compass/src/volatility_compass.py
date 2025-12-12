"""
Main Volatility Compass orchestrator that coordinates all volatility analysis components.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from .models import (
    VolatilityMetrics, VolatilitySkew, VolatilityTermStructure,
    VolatilitySurface, VolatilityCompassReport, VolatilityCondition,
    TermStructurePoint, VolatilitySurfacePoint, WatchlistVolatilityAnalysis
)
from .calculators import (
    IVRankCalculator, HistoricalVolatilityCalculator, SkewCalculator,
    TermStructureCalculator, VolatilitySurfaceCalculator, IVConditionClassifier
)
from .strategy_engine import VolatilityStrategyEngine
from .alert_engine import VolatilityAlertEngine


class VolatilityCompass:
    """
    Main class for comprehensive volatility analysis.
    Coordinates all volatility calculations, analysis, and reporting.
    """
    
    def __init__(self):
        """Initialize Volatility Compass with calculation engines."""
        self.iv_rank_calc = IVRankCalculator()
        self.hv_calc = HistoricalVolatilityCalculator()
        self.skew_calc = SkewCalculator()
        self.term_calc = TermStructureCalculator()
        self.surface_calc = VolatilitySurfaceCalculator()
        self.condition_classifier = IVConditionClassifier()
        self.strategy_engine = VolatilityStrategyEngine()
        self.alert_engine = VolatilityAlertEngine()
    
    def analyze_symbol(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float],
        options_chain: Dict,
        previous_iv: Optional[float] = None
    ) -> VolatilityCompassReport:
        """
        Perform comprehensive volatility analysis for a symbol.
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility
            iv_history: Historical IV values (most recent first)
            price_history: Historical price data (most recent first)
            options_chain: Options chain data with strikes, IVs, expirations
            previous_iv: Previous IV for alert detection
            
        Returns:
            Complete VolatilityCompassReport with all analyses
        """
        timestamp = datetime.now()
        
        # Calculate core metrics
        metrics = self._calculate_metrics(
            symbol, current_iv, iv_history, price_history, timestamp
        )
        
        # Analyze term structure
        term_structure = self._analyze_term_structure(
            symbol, price_history[0], options_chain, timestamp
        )
        
        # Analyze skew for multiple expirations
        skew_analyses = self._analyze_skew(symbol, options_chain)
        
        # Build volatility surface
        surface = self._build_volatility_surface(
            symbol, price_history[0], options_chain, timestamp
        )
        
        # Generate strategies
        primary_skew = skew_analyses[0] if skew_analyses else None
        strategies = self.strategy_engine.generate_strategies(
            metrics, primary_skew, term_structure
        )
        
        # Check for alerts
        alerts = self.alert_engine.check_alerts(
            symbol, metrics, previous_iv=previous_iv
        )
        
        # Build historical context
        iv_rank_history = self._build_rank_history(iv_history)
        iv_percentile_history = self._build_percentile_history(iv_history)
        
        return VolatilityCompassReport(
            symbol=symbol,
            timestamp=timestamp,
            metrics=metrics,
            term_structure=term_structure,
            skew_analysis=skew_analyses,
            surface=surface,
            strategies=strategies,
            alerts=alerts,
            iv_rank_history=iv_rank_history,
            iv_percentile_history=iv_percentile_history
        )
    
    def _calculate_metrics(
        self,
        symbol: str,
        current_iv: float,
        iv_history: List[float],
        price_history: List[float],
        timestamp: datetime
    ) -> VolatilityMetrics:
        """Calculate core volatility metrics."""
        
        # IV Rank and Percentile
        iv_rank = self.iv_rank_calc.calculate_iv_rank(current_iv, iv_history)
        iv_percentile = self.iv_rank_calc.calculate_iv_percentile(current_iv, iv_history)
        
        # Historical volatility at different windows
        hv_30d = self.hv_calc.calculate_hv(price_history, 30)
        hv_60d = self.hv_calc.calculate_hv(price_history, 60)
        hv_90d = self.hv_calc.calculate_hv(price_history, 90)
        
        # IV/HV ratio
        iv_hv_ratio = self.condition_classifier.calculate_iv_hv_ratio(
            current_iv, hv_30d
        )
        
        # Volatility condition
        condition_str = self.condition_classifier.classify_condition(
            iv_rank, iv_percentile
        )
        condition = VolatilityCondition(condition_str)
        
        # Historical IV averages
        avg_iv_30d = np.mean(iv_history[:30]) if len(iv_history) >= 30 else current_iv
        avg_iv_60d = np.mean(iv_history[:60]) if len(iv_history) >= 60 else current_iv
        
        # 52-week extremes
        min_iv_52w, max_iv_52w = self.iv_rank_calc.get_52_week_extremes(iv_history)
        
        return VolatilityMetrics(
            symbol=symbol,
            timestamp=timestamp,
            current_iv=current_iv,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            historical_volatility_30d=hv_30d,
            historical_volatility_60d=hv_60d,
            historical_volatility_90d=hv_90d,
            iv_hv_ratio=iv_hv_ratio,
            condition=condition,
            average_iv_30d=avg_iv_30d,
            average_iv_60d=avg_iv_60d,
            min_iv_52w=min_iv_52w,
            max_iv_52w=max_iv_52w
        )
    
    def _analyze_term_structure(
        self,
        symbol: str,
        current_price: float,
        options_chain: Dict,
        timestamp: datetime
    ) -> VolatilityTermStructure:
        """Analyze volatility term structure across expirations."""
        
        term_points = []
        expirations = options_chain.get('expirations', [])
        
        for exp_data in expirations:
            exp_date = exp_data['expiration_date']
            days_to_exp = (exp_date - timestamp).days
            
            # Get ATM strike and IV
            atm_strike = self._find_atm_strike(current_price, exp_data['strikes'])
            atm_iv = exp_data.get('atm_iv', 0.0)
            
            # Calculate average call and put IVs
            call_ivs = [opt['iv'] for opt in exp_data.get('calls', [])]
            put_ivs = [opt['iv'] for opt in exp_data.get('puts', [])]
            
            call_iv_avg = np.mean(call_ivs) if call_ivs else atm_iv
            put_iv_avg = np.mean(put_ivs) if put_ivs else atm_iv
            
            term_points.append(TermStructurePoint(
                expiration_date=exp_date,
                days_to_expiration=days_to_exp,
                atm_iv=atm_iv,
                call_iv_avg=call_iv_avg,
                put_iv_avg=put_iv_avg,
                volume=exp_data.get('total_volume', 0),
                open_interest=exp_data.get('total_oi', 0)
            ))
        
        # Sort by DTE
        term_points.sort(key=lambda x: x.days_to_expiration)
        
        # Determine term structure shape
        term_ivs = [(p.days_to_expiration, p.atm_iv) for p in term_points]
        structure_shape = self.term_calc.classify_term_structure(term_ivs)
        
        front_month_iv = term_points[0].atm_iv if term_points else 0.0
        back_month_iv = term_points[-1].atm_iv if term_points else 0.0
        
        # Calculate slope
        term_structure_slope = self.term_calc.calculate_term_structure_slope(term_ivs)
        
        return VolatilityTermStructure(
            symbol=symbol,
            timestamp=timestamp,
            current_price=current_price,
            term_points=term_points,
            structure_shape=structure_shape,
            front_month_iv=front_month_iv,
            back_month_iv=back_month_iv,
            term_structure_slope=term_structure_slope
        )
    
    def _analyze_skew(
        self,
        symbol: str,
        options_chain: Dict
    ) -> List[VolatilitySkew]:
        """Analyze volatility skew for multiple expirations."""
        
        skew_analyses = []
        expirations = options_chain.get('expirations', [])
        
        for exp_data in expirations[:3]:  # Analyze first 3 expirations
            exp_date = exp_data['expiration_date']
            days_to_exp = exp_data.get('days_to_expiration', 0)
            
            # Get ATM reference
            atm_strike = exp_data.get('atm_strike', 0.0)
            atm_iv = exp_data.get('atm_iv', 0.0)
            
            # Separate OTM calls and puts
            calls = exp_data.get('calls', [])
            puts = exp_data.get('puts', [])
            
            # OTM calls (strikes > ATM)
            otm_calls = [c for c in calls if c['strike'] > atm_strike]
            call_strikes = [c['strike'] for c in otm_calls]
            call_ivs = [c['iv'] for c in otm_calls]
            
            # OTM puts (strikes < ATM)
            otm_puts = [p for p in puts if p['strike'] < atm_strike]
            put_strikes = [p['strike'] for p in otm_puts]
            put_ivs = [p['iv'] for p in otm_puts]
            
            # Calculate skew slopes
            call_skew_slope = self.skew_calc.calculate_skew_slope(
                call_strikes, call_ivs
            )
            put_skew_slope = self.skew_calc.calculate_skew_slope(
                put_strikes, put_ivs
            )
            
            # Put/Call ratio
            put_call_ratio = self.skew_calc.calculate_put_call_skew_ratio(
                put_ivs, call_ivs
            )
            
            # Classify skew type
            skew_type = self.skew_calc.classify_skew_type(
                put_skew_slope, call_skew_slope, put_call_ratio
            )
            
            skew_analyses.append(VolatilitySkew(
                symbol=symbol,
                expiration_date=exp_date,
                days_to_expiration=days_to_exp,
                atm_strike=atm_strike,
                atm_iv=atm_iv,
                call_strikes=call_strikes,
                call_ivs=call_ivs,
                call_skew_slope=call_skew_slope,
                put_strikes=put_strikes,
                put_ivs=put_ivs,
                put_skew_slope=put_skew_slope,
                put_call_skew_ratio=put_call_ratio,
                skew_type=skew_type
            ))
        
        return skew_analyses
    
    def _build_volatility_surface(
        self,
        symbol: str,
        current_price: float,
        options_chain: Dict,
        timestamp: datetime
    ) -> VolatilitySurface:
        """Build 3D volatility surface data."""
        
        surface_points = []
        expirations_list = []
        
        expirations = options_chain.get('expirations', [])
        
        for exp_data in expirations:
            exp_date = exp_data['expiration_date']
            days_to_exp = exp_data.get('days_to_expiration', 0)
            expirations_list.append(exp_date)
            
            # Add all options to surface
            for call in exp_data.get('calls', []):
                surface_points.append(VolatilitySurfacePoint(
                    strike=call['strike'],
                    days_to_expiration=days_to_exp,
                    implied_volatility=call['iv'],
                    delta=call.get('delta'),
                    moneyness=call['strike'] / current_price
                ))
            
            for put in exp_data.get('puts', []):
                surface_points.append(VolatilitySurfacePoint(
                    strike=put['strike'],
                    days_to_expiration=days_to_exp,
                    implied_volatility=put['iv'],
                    delta=put.get('delta'),
                    moneyness=put['strike'] / current_price
                ))
        
        # Calculate surface characteristics
        surface_data = [(p.strike, p.days_to_expiration, p.implied_volatility) 
                       for p in surface_points]
        surface_curvature = self.surface_calc.calculate_surface_curvature(surface_data)
        
        # Determine strike range
        all_strikes = [p.strike for p in surface_points]
        min_strike = min(all_strikes) if all_strikes else 0.0
        max_strike = max(all_strikes) if all_strikes else 0.0
        
        return VolatilitySurface(
            symbol=symbol,
            timestamp=timestamp,
            current_price=current_price,
            surface_points=surface_points,
            expirations=expirations_list,
            min_strike=min_strike,
            max_strike=max_strike,
            surface_curvature=surface_curvature
        )
    
    def analyze_watchlist(
        self,
        watchlist_name: str,
        symbols_data: Dict[str, Dict]
    ) -> WatchlistVolatilityAnalysis:
        """
        Perform bulk volatility analysis for a watchlist.
        
        Args:
            watchlist_name: Name of the watchlist
            symbols_data: Dictionary mapping symbols to their data
            
        Returns:
            WatchlistVolatilityAnalysis with aggregated results
        """
        timestamp = datetime.now()
        symbols = list(symbols_data.keys())
        symbol_metrics = {}
        
        high_iv_symbols = []
        low_iv_symbols = []
        premium_selling = []
        premium_buying = []
        all_alerts = []
        
        # Analyze each symbol
        for symbol, data in symbols_data.items():
            metrics = self._calculate_metrics(
                symbol,
                data['current_iv'],
                data['iv_history'],
                data['price_history'],
                timestamp
            )
            
            symbol_metrics[symbol] = metrics
            
            # Categorize by IV rank
            if metrics.iv_rank >= 70:
                high_iv_symbols.append(symbol)
                premium_selling.append((symbol, metrics.iv_rank))
            elif metrics.iv_rank <= 30:
                low_iv_symbols.append(symbol)
                premium_buying.append((symbol, metrics.iv_rank))
            
            # Check alerts
            alerts = self.alert_engine.check_alerts(
                symbol, metrics, previous_iv=data.get('previous_iv')
            )
            all_alerts.extend(alerts)
        
        # Sort opportunities by IV rank
        premium_selling.sort(key=lambda x: x[1], reverse=True)
        premium_buying.sort(key=lambda x: x[1])
        
        # Calculate aggregate statistics
        all_iv_ranks = [m.iv_rank for m in symbol_metrics.values()]
        all_iv_percentiles = [m.iv_percentile for m in symbol_metrics.values()]
        
        avg_iv_rank = np.mean(all_iv_ranks) if all_iv_ranks else 0.0
        avg_iv_percentile = np.mean(all_iv_percentiles) if all_iv_percentiles else 0.0
        
        return WatchlistVolatilityAnalysis(
            watchlist_name=watchlist_name,
            timestamp=timestamp,
            symbols=symbols,
            symbol_metrics=symbol_metrics,
            average_iv_rank=round(avg_iv_rank, 2),
            average_iv_percentile=round(avg_iv_percentile, 2),
            high_iv_symbols=high_iv_symbols,
            low_iv_symbols=low_iv_symbols,
            premium_selling_candidates=premium_selling,
            premium_buying_candidates=premium_buying,
            active_alerts=all_alerts
        )
    
    def _find_atm_strike(self, current_price: float, strikes: List[float]) -> float:
        """Find the strike closest to current price."""
        if not strikes:
            return current_price
        return min(strikes, key=lambda x: abs(x - current_price))
    
    def _build_rank_history(
        self, 
        iv_history: List[float], 
        days: int = 30
    ) -> List[Tuple[datetime, float]]:
        """Build historical IV rank data for charting."""
        history = []
        current_date = datetime.now()
        
        for i in range(min(days, len(iv_history))):
            date = current_date - timedelta(days=i)
            # Calculate rolling IV rank
            lookback = iv_history[i:]
            if len(lookback) >= 2:
                current = iv_history[i]
                rank = self.iv_rank_calc.calculate_iv_rank(current, lookback)
                history.append((date, rank))
        
        return list(reversed(history))
    
    def _build_percentile_history(
        self,
        iv_history: List[float],
        days: int = 30
    ) -> List[Tuple[datetime, float]]:
        """Build historical IV percentile data for charting."""
        history = []
        current_date = datetime.now()
        
        for i in range(min(days, len(iv_history))):
            date = current_date - timedelta(days=i)
            # Calculate rolling IV percentile
            lookback = iv_history[i:]
            if len(lookback) >= 2:
                current = iv_history[i]
                percentile = self.iv_rank_calc.calculate_iv_percentile(current, lookback)
                history.append((date, percentile))
        
        return list(reversed(history))
