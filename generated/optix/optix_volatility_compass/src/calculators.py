"""
Core calculation engines for volatility metrics.
"""
import numpy as np
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats
from scipy.interpolate import griddata


class IVRankCalculator:
    """Calculator for IV Rank and IV Percentile metrics."""
    
    @staticmethod
    def calculate_iv_rank(current_iv: float, iv_history: List[float], 
                          lookback_days: int = 252) -> float:
        """
        Calculate IV Rank: (Current IV - Min IV) / (Max IV - Min IV) * 100
        
        Args:
            current_iv: Current implied volatility
            iv_history: Historical IV values (most recent first)
            lookback_days: Number of days to look back (default 252 = 1 year)
            
        Returns:
            IV Rank value between 0 and 100
        """
        if not iv_history or len(iv_history) < 2:
            return 50.0  # Default to middle if insufficient data
            
        # Use specified lookback period
        history_subset = iv_history[:lookback_days]
        
        min_iv = min(history_subset)
        max_iv = max(history_subset)
        
        if max_iv == min_iv:
            return 50.0  # If no variation, return middle value
            
        iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
        return max(0.0, min(100.0, iv_rank))
    
    @staticmethod
    def calculate_iv_percentile(current_iv: float, iv_history: List[float],
                                lookback_days: int = 252) -> float:
        """
        Calculate IV Percentile: Percentage of days where IV was below current level
        
        Args:
            current_iv: Current implied volatility
            iv_history: Historical IV values
            lookback_days: Number of days to look back
            
        Returns:
            IV Percentile value between 0 and 100
        """
        if not iv_history or len(iv_history) < 2:
            return 50.0
            
        history_subset = iv_history[:lookback_days]
        
        days_below = sum(1 for iv in history_subset if iv < current_iv)
        percentile = (days_below / len(history_subset)) * 100
        
        return round(percentile, 2)
    
    @staticmethod
    def get_52_week_extremes(iv_history: List[float]) -> Tuple[float, float]:
        """Get 52-week min and max IV values."""
        if not iv_history:
            return 0.0, 0.0
            
        history_52w = iv_history[:252]  # 252 trading days ≈ 1 year
        return min(history_52w), max(history_52w)


class HistoricalVolatilityCalculator:
    """Calculator for historical volatility (realized volatility)."""
    
    @staticmethod
    def calculate_hv(price_history: List[float], window_days: int = 30) -> float:
        """
        Calculate historical volatility using close-to-close method.
        
        Args:
            price_history: List of historical prices (most recent first)
            window_days: Number of days for HV calculation
            
        Returns:
            Annualized historical volatility as percentage
        """
        if len(price_history) < window_days + 1:
            return 0.0
            
        # Use specified window
        prices = price_history[:window_days + 1]
        
        # Calculate log returns
        log_returns = []
        for i in range(len(prices) - 1):
            log_return = np.log(prices[i] / prices[i + 1])
            log_returns.append(log_return)
        
        if not log_returns:
            return 0.0
            
        # Calculate standard deviation of returns
        std_dev = np.std(log_returns, ddof=1)
        
        # Annualize (252 trading days per year)
        annual_volatility = std_dev * np.sqrt(252)
        
        return round(annual_volatility * 100, 2)  # Return as percentage
    
    @staticmethod
    def calculate_parkinson_hv(high_low_data: List[Tuple[float, float]], 
                               window_days: int = 30) -> float:
        """
        Calculate Parkinson historical volatility using high-low range.
        More efficient estimator than close-to-close.
        
        Args:
            high_low_data: List of (high, low) tuples
            window_days: Number of days for calculation
            
        Returns:
            Annualized Parkinson HV as percentage
        """
        if len(high_low_data) < window_days:
            return 0.0
            
        data_subset = high_low_data[:window_days]
        
        # Calculate squared log ratio of high to low
        sum_squared = 0.0
        for high, low in data_subset:
            if low > 0:
                sum_squared += (np.log(high / low)) ** 2
        
        # Parkinson's constant
        parkinson_constant = 1 / (4 * np.log(2))
        
        # Calculate variance and annualize
        variance = parkinson_constant * (sum_squared / window_days)
        annual_volatility = np.sqrt(variance * 252)
        
        return round(annual_volatility * 100, 2)


class SkewCalculator:
    """Calculator for volatility skew analysis."""
    
    @staticmethod
    def calculate_skew_slope(strikes: List[float], ivs: List[float]) -> float:
        """
        Calculate the slope of volatility skew using linear regression.
        
        Args:
            strikes: Strike prices
            ivs: Implied volatilities at each strike
            
        Returns:
            Slope of the skew line
        """
        if len(strikes) < 2 or len(strikes) != len(ivs):
            return 0.0
            
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(strikes, ivs)
        return round(slope, 6)
    
    @staticmethod
    def classify_skew_type(put_skew_slope: float, call_skew_slope: float,
                          put_call_ratio: float) -> str:
        """
        Classify the type of volatility skew.
        
        Args:
            put_skew_slope: Slope of put side skew
            call_skew_slope: Slope of call side skew
            put_call_ratio: Ratio of put IV to call IV
            
        Returns:
            Skew type: "normal", "reverse", "flat", "smile"
        """
        # Normal skew: OTM puts have higher IV than OTM calls
        if put_call_ratio > 1.05 and put_skew_slope < -0.001:
            return "normal"
        
        # Reverse skew: OTM calls have higher IV than OTM puts
        if put_call_ratio < 0.95 and call_skew_slope > 0.001:
            return "reverse"
        
        # Smile: Both OTM puts and calls have elevated IV
        if abs(put_skew_slope) > 0.001 and abs(call_skew_slope) > 0.001:
            if put_skew_slope < 0 and call_skew_slope > 0:
                return "smile"
        
        # Flat skew: Relatively uniform IV across strikes
        return "flat"
    
    @staticmethod
    def calculate_put_call_skew_ratio(put_ivs: List[float], 
                                     call_ivs: List[float]) -> float:
        """
        Calculate the ratio of average put IV to average call IV.
        
        Args:
            put_ivs: List of put implied volatilities
            call_ivs: List of call implied volatilities
            
        Returns:
            Put/Call IV ratio
        """
        if not put_ivs or not call_ivs:
            return 1.0
            
        avg_put_iv = np.mean(put_ivs)
        avg_call_iv = np.mean(call_ivs)
        
        if avg_call_iv == 0:
            return 1.0
            
        return round(avg_put_iv / avg_call_iv, 4)


class TermStructureCalculator:
    """Calculator for volatility term structure analysis."""
    
    @staticmethod
    def classify_term_structure(term_ivs: List[Tuple[int, float]]) -> str:
        """
        Classify term structure shape based on near-term vs far-term IV.
        
        Args:
            term_ivs: List of (days_to_expiration, iv) tuples, sorted by DTE
            
        Returns:
            Structure type: "contango", "backwardation", "flat"
        """
        if len(term_ivs) < 2:
            return "flat"
        
        # Get front month (shortest DTE) and back month (longest DTE)
        front_dte, front_iv = term_ivs[0]
        back_dte, back_iv = term_ivs[-1]
        
        # Calculate percentage difference
        iv_diff_pct = ((back_iv - front_iv) / front_iv) * 100
        
        # Contango: IV increases with time (normal)
        if iv_diff_pct > 5:
            return "contango"
        
        # Backwardation: IV decreases with time (elevated near-term)
        elif iv_diff_pct < -5:
            return "backwardation"
        
        # Flat: Relatively uniform across expirations
        else:
            return "flat"
    
    @staticmethod
    def calculate_term_structure_slope(term_ivs: List[Tuple[int, float]]) -> float:
        """
        Calculate the slope of term structure using linear regression.
        
        Args:
            term_ivs: List of (days_to_expiration, iv) tuples
            
        Returns:
            Slope of term structure
        """
        if len(term_ivs) < 2:
            return 0.0
        
        dtes = [dte for dte, _ in term_ivs]
        ivs = [iv for _, iv in term_ivs]
        
        slope, intercept, r_value, p_value, std_err = stats.linregregress(dtes, ivs)
        return round(slope, 6)


class VolatilitySurfaceCalculator:
    """Calculator for 3D volatility surface construction."""
    
    @staticmethod
    def calculate_surface_curvature(surface_points: List[Tuple[float, int, float]]) -> float:
        """
        Calculate overall curvature of the volatility surface.
        Higher values indicate more convex surface (smile/smirk).
        
        Args:
            surface_points: List of (strike, dte, iv) tuples
            
        Returns:
            Surface curvature measure
        """
        if len(surface_points) < 3:
            return 0.0
        
        # Extract IV values
        ivs = [iv for _, _, iv in surface_points]
        
        # Calculate second derivative approximation
        if len(ivs) < 3:
            return 0.0
        
        second_derivatives = []
        for i in range(1, len(ivs) - 1):
            second_deriv = ivs[i-1] - 2*ivs[i] + ivs[i+1]
            second_derivatives.append(abs(second_deriv))
        
        # Average absolute curvature
        avg_curvature = np.mean(second_derivatives) if second_derivatives else 0.0
        return round(avg_curvature, 6)
    
    @staticmethod
    def interpolate_surface(known_points: List[Tuple[float, int, float]],
                           grid_strikes: np.ndarray,
                           grid_dtes: np.ndarray) -> np.ndarray:
        """
        Interpolate volatility surface for visualization.
        
        Args:
            known_points: List of (strike, dte, iv) tuples
            grid_strikes: Strike grid for interpolation
            grid_dtes: DTE grid for interpolation
            
        Returns:
            2D array of interpolated IV values
        """
        if len(known_points) < 3:
            return np.zeros((len(grid_dtes), len(grid_strikes)))
        
        # Prepare data for interpolation
        strikes = np.array([s for s, _, _ in known_points])
        dtes = np.array([d for _, d, _ in known_points])
        ivs = np.array([iv for _, _, iv in known_points])
        
        # Create meshgrid
        strike_grid, dte_grid = np.meshgrid(grid_strikes, grid_dtes)
        
        # Interpolate using cubic method
        iv_surface = griddata(
            (strikes, dtes), 
            ivs, 
            (strike_grid, dte_grid),
            method='cubic',
            fill_value=np.nan
        )
        
        return iv_surface


class IVConditionClassifier:
    """Classifier for volatility conditions and regime detection."""
    
    @staticmethod
    def classify_condition(iv_rank: float, iv_percentile: float) -> str:
        """
        Classify current volatility condition based on IV Rank and Percentile.
        
        Args:
            iv_rank: Current IV Rank (0-100)
            iv_percentile: Current IV Percentile (0-100)
            
        Returns:
            Volatility condition classification
        """
        # Use average of rank and percentile for robust classification
        avg_metric = (iv_rank + iv_percentile) / 2
        
        if avg_metric >= 80:
            return "extremely_high"
        elif avg_metric >= 60:
            return "high"
        elif avg_metric >= 40:
            return "normal"
        elif avg_metric >= 20:
            return "low"
        else:
            return "extremely_low"
    
    @staticmethod
    def calculate_iv_hv_ratio(current_iv: float, historical_vol: float) -> float:
        """
        Calculate ratio of implied volatility to historical volatility.
        
        Args:
            current_iv: Current implied volatility
            historical_vol: Historical volatility
            
        Returns:
            IV/HV ratio
        """
        if historical_vol == 0:
            return 1.0
            
        return round(current_iv / historical_vol, 2)
