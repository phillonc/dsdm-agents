"""
Greeks visualization for options strategies
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..models.strategy import Strategy
from ..calculators.greeks_calculator import GreeksCalculator


class GreeksVisualizer:
    """
    Visualize Greeks across different price ranges and time periods
    """
    
    @staticmethod
    def generate_greeks_profile(
        strategy: Strategy,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        num_points: int = 100
    ) -> Dict:
        """
        Generate Greeks profile across a price range
        
        Args:
            strategy: The options strategy
            price_range: Price range to analyze
            num_points: Number of price points
            
        Returns:
            Greeks profile data
        """
        # Determine price range
        if price_range is None:
            strikes = [leg.option.strike_price for leg in strategy.legs]
            min_strike = min(strikes)
            max_strike = max(strikes)
            min_price = min_strike * Decimal('0.8')
            max_price = max_strike * Decimal('1.2')
        else:
            min_price, max_price = price_range
        
        prices = np.linspace(float(min_price), float(max_price), num_points)
        
        delta_values = []
        gamma_values = []
        theta_values = []
        vega_values = []
        rho_values = []
        
        for price in prices:
            # Update underlying price for all legs
            for leg in strategy.legs:
                leg.option.underlying_price = Decimal(str(price))
            
            # Calculate Greeks
            greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
            
            delta_values.append(float(greeks.total_delta))
            gamma_values.append(float(greeks.total_gamma))
            theta_values.append(float(greeks.total_theta))
            vega_values.append(float(greeks.total_vega))
            rho_values.append(float(greeks.total_rho))
        
        return {
            'prices': prices.tolist(),
            'delta': delta_values,
            'gamma': gamma_values,
            'theta': theta_values,
            'vega': vega_values,
            'rho': rho_values
        }
    
    @staticmethod
    def generate_greeks_summary(strategy: Strategy) -> Dict:
        """
        Generate current Greeks summary with interpretations
        
        Args:
            strategy: The options strategy
            
        Returns:
            Greeks summary with interpretations
        """
        greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
        risk_profile = greeks.get_risk_profile()
        
        return {
            'current_greeks': greeks.to_dict(),
            'risk_profile': risk_profile,
            'interpretations': {
                'delta': GreeksVisualizer._interpret_delta(greeks.total_delta),
                'gamma': GreeksVisualizer._interpret_gamma(greeks.total_gamma),
                'theta': GreeksVisualizer._interpret_theta(greeks.total_theta),
                'vega': GreeksVisualizer._interpret_vega(greeks.total_vega),
                'rho': GreeksVisualizer._interpret_rho(greeks.total_rho)
            }
        }
    
    @staticmethod
    def _interpret_delta(delta: Decimal) -> Dict:
        """Interpret delta value"""
        abs_delta = abs(delta)
        
        if abs_delta < Decimal('10'):
            exposure = "Low"
            description = "Position is relatively neutral to price movements"
        elif abs_delta < Decimal('50'):
            exposure = "Moderate"
            description = "Position has moderate directional exposure"
        else:
            exposure = "High"
            description = "Position has significant directional exposure"
        
        direction = "Bullish" if delta > 0 else "Bearish" if delta < 0 else "Neutral"
        
        return {
            'value': float(delta),
            'exposure': exposure,
            'direction': direction,
            'description': description,
            'meaning': f"For every $1 move in underlying, position changes by ~${float(delta):.2f}"
        }
    
    @staticmethod
    def _interpret_gamma(gamma: Decimal) -> Dict:
        """Interpret gamma value"""
        abs_gamma = abs(gamma)
        
        if abs_gamma < Decimal('0.05'):
            exposure = "Low"
            risk = "Stable"
        elif abs_gamma < Decimal('0.15'):
            exposure = "Moderate"
            risk = "Moderate"
        else:
            exposure = "High"
            risk = "High"
        
        position_type = "Long" if gamma > 0 else "Short"
        
        return {
            'value': float(gamma),
            'exposure': exposure,
            'risk': risk,
            'position_type': position_type,
            'description': f"{position_type} gamma position with {exposure.lower()} exposure",
            'meaning': "Rate of change of delta. Higher gamma means delta changes faster."
        }
    
    @staticmethod
    def _interpret_theta(theta: Decimal) -> Dict:
        """Interpret theta value"""
        abs_theta = abs(theta)
        
        if abs_theta < Decimal('5'):
            impact = "Low"
        elif abs_theta < Decimal('20'):
            impact = "Moderate"
        else:
            impact = "High"
        
        effect = "Losing value" if theta < 0 else "Gaining value"
        
        return {
            'value': float(theta),
            'daily_decay': float(theta),
            'impact': impact,
            'effect': effect,
            'description': f"{effect} {impact.lower()} amount each day due to time decay",
            'meaning': f"Position loses/gains ~${abs(float(theta)):.2f} per day from time decay"
        }
    
    @staticmethod
    def _interpret_vega(vega: Decimal) -> Dict:
        """Interpret vega value"""
        abs_vega = abs(vega)
        
        if abs_vega < Decimal('5'):
            sensitivity = "Low"
        elif abs_vega < Decimal('20'):
            sensitivity = "Moderate"
        else:
            sensitivity = "High"
        
        position_type = "Long volatility" if vega > 0 else "Short volatility"
        
        return {
            'value': float(vega),
            'sensitivity': sensitivity,
            'position_type': position_type,
            'description': f"{position_type} position with {sensitivity.lower()} volatility sensitivity",
            'meaning': f"For every 1% change in IV, position changes by ~${float(vega):.2f}"
        }
    
    @staticmethod
    def _interpret_rho(rho: Decimal) -> Dict:
        """Interpret rho value"""
        abs_rho = abs(rho)
        
        if abs_rho < Decimal('2'):
            sensitivity = "Low"
        elif abs_rho < Decimal('10'):
            sensitivity = "Moderate"
        else:
            sensitivity = "High"
        
        return {
            'value': float(rho),
            'sensitivity': sensitivity,
            'description': f"{sensitivity} sensitivity to interest rate changes",
            'meaning': f"For every 1% change in rates, position changes by ~${float(rho):.2f}"
        }
    
    @staticmethod
    def generate_greek_heatmap(
        strategy: Strategy,
        greek_name: str,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        time_range: Optional[Tuple[int, int]] = None,
        price_points: int = 20,
        time_points: int = 10
    ) -> Dict:
        """
        Generate heatmap data for a specific Greek
        
        Args:
            strategy: The options strategy
            greek_name: Name of Greek (delta, gamma, theta, vega, rho)
            price_range: Price range for analysis
            time_range: Time range in days
            price_points: Number of price points
            time_points: Number of time points
            
        Returns:
            Heatmap data for the Greek
        """
        # Determine ranges
        if price_range is None:
            strikes = [leg.option.strike_price for leg in strategy.legs]
            min_strike = min(strikes)
            max_strike = max(strikes)
            min_price = min_strike * Decimal('0.9')
            max_price = max_strike * Decimal('1.1')
        else:
            min_price, max_price = price_range
        
        if time_range is None:
            max_days = strategy.legs[0].option.days_to_expiration if strategy.legs else 30
            time_range = (0, min(max_days, 60))
        
        prices = np.linspace(float(min_price), float(max_price), price_points)
        days = np.linspace(time_range[0], time_range[1], time_points)
        
        greek_matrix = []
        
        greek_attr_map = {
            'delta': 'total_delta',
            'gamma': 'total_gamma',
            'theta': 'total_theta',
            'vega': 'total_vega',
            'rho': 'total_rho'
        }
        
        greek_attr = greek_attr_map.get(greek_name.lower(), 'total_delta')
        
        for day in days:
            greek_row = []
            for price in prices:
                # Update prices
                for leg in strategy.legs:
                    leg.option.underlying_price = Decimal(str(price))
                
                # Calculate Greeks
                greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
                greek_value = getattr(greeks, greek_attr)
                greek_row.append(float(greek_value))
            
            greek_matrix.append(greek_row)
        
        return {
            'prices': prices.tolist(),
            'days': days.tolist(),
            'greek_matrix': greek_matrix,
            'greek_name': greek_name,
            'x_label': 'Underlying Price',
            'y_label': 'Days Passed',
            'z_label': f'{greek_name.capitalize()}'
        }
    
    @staticmethod
    def compare_strategies_greeks(strategies: List[Strategy]) -> Dict:
        """
        Compare Greeks across multiple strategies
        
        Args:
            strategies: List of strategies to compare
            
        Returns:
            Comparison data
        """
        comparison = []
        
        for strategy in strategies:
            greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
            
            comparison.append({
                'strategy_name': strategy.name,
                'strategy_id': strategy.strategy_id,
                'greeks': greeks.to_dict(),
                'risk_profile': greeks.get_risk_profile()
            })
        
        return {
            'strategies': comparison,
            'comparison_summary': GreeksVisualizer._generate_comparison_summary(comparison)
        }
    
    @staticmethod
    def _generate_comparison_summary(comparison: List[Dict]) -> Dict:
        """Generate summary of strategy comparison"""
        if not comparison:
            return {}
        
        # Find strategy with highest/lowest Greeks
        max_delta = max(comparison, key=lambda x: x['greeks']['total_delta'])
        min_delta = min(comparison, key=lambda x: x['greeks']['total_delta'])
        max_theta_decay = min(comparison, key=lambda x: x['greeks']['total_theta'])
        max_vega = max(comparison, key=lambda x: abs(x['greeks']['total_vega']))
        
        return {
            'most_bullish': max_delta['strategy_name'],
            'most_bearish': min_delta['strategy_name'],
            'highest_time_decay': max_theta_decay['strategy_name'],
            'most_volatility_sensitive': max_vega['strategy_name']
        }
