"""
Payoff diagram visualization for options strategies
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..models.strategy import Strategy
from ..calculators.pnl_calculator import PnLCalculator


class PayoffVisualizer:
    """
    Generate payoff diagram data for visualization
    """
    
    @staticmethod
    def generate_payoff_data(
        strategy: Strategy,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        num_points: int = 200
    ) -> Dict:
        """
        Generate comprehensive payoff diagram data
        
        Args:
            strategy: The options strategy
            price_range: Price range for the diagram
            num_points: Number of price points to calculate
            
        Returns:
            Dictionary with payoff data for visualization
        """
        # Get payoff at expiration
        payoff_expiration = PnLCalculator.calculate_payoff_diagram(
            strategy, price_range, num_points, at_expiration=True
        )
        
        # Get current payoff (time remaining)
        payoff_current = PnLCalculator.calculate_payoff_diagram(
            strategy, price_range, num_points, at_expiration=False
        )
        
        # Calculate max profit and loss
        max_profit, price_at_max_profit = PnLCalculator.calculate_max_profit(strategy, price_range)
        max_loss, price_at_max_loss = PnLCalculator.calculate_max_loss(strategy, price_range)
        
        return {
            'expiration_payoff': {
                'prices': payoff_expiration['prices'],
                'pnl': payoff_expiration['pnl'],
                'label': 'At Expiration'
            },
            'current_payoff': {
                'prices': payoff_current['prices'],
                'pnl': payoff_current['pnl'],
                'label': 'Current'
            },
            'breakeven_points': payoff_expiration['breakeven_points'],
            'max_profit': {
                'value': float(max_profit),
                'price': float(price_at_max_profit)
            },
            'max_loss': {
                'value': float(max_loss),
                'price': float(price_at_max_loss)
            },
            'initial_cost': float(strategy.total_cost)
        }
    
    @staticmethod
    def generate_individual_leg_payoffs(
        strategy: Strategy,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        num_points: int = 100
    ) -> List[Dict]:
        """
        Generate payoff data for each individual leg
        
        Args:
            strategy: The options strategy
            price_range: Price range for the diagram
            num_points: Number of price points
            
        Returns:
            List of payoff data for each leg
        """
        leg_payoffs = []
        
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
        
        for leg in strategy.legs:
            pnl_values = []
            
            for price in prices:
                pnl = PnLCalculator.calculate_option_pnl_at_expiration(
                    leg.option,
                    Decimal(str(price))
                )
                pnl_values.append(float(pnl))
            
            leg_payoffs.append({
                'leg_id': leg.leg_id,
                'label': f"{leg.option.option_type.value} {float(leg.option.strike_price)} {leg.option.position.value}",
                'prices': prices.tolist(),
                'pnl': pnl_values,
                'strike': float(leg.option.strike_price),
                'option_type': leg.option.option_type.value,
                'position': leg.option.position.value
            })
        
        return leg_payoffs
    
    @staticmethod
    def generate_time_decay_analysis(
        strategy: Strategy,
        underlying_price: Decimal,
        days_points: List[int] = None
    ) -> Dict:
        """
        Generate time decay analysis data
        
        Args:
            strategy: The options strategy
            underlying_price: Current underlying price
            days_points: List of days to analyze (e.g., [0, 7, 14, 21, 28])
            
        Returns:
            Time decay analysis data
        """
        if days_points is None:
            # Default: current date, then weekly intervals until expiration
            max_days = min(strategy.legs[0].option.days_to_expiration if strategy.legs else 30, 90)
            days_points = list(range(0, max_days + 1, 7))
        
        time_series = []
        
        for days_passed in days_points:
            # Calculate strategy value at this time point
            # (In real implementation, would adjust option prices for time decay)
            days_remaining = strategy.legs[0].option.days_to_expiration - days_passed
            
            if days_remaining < 0:
                continue
            
            # Simplified: calculate P&L
            pnl = PnLCalculator.calculate_strategy_pnl(
                strategy,
                underlying_price,
                at_expiration=(days_remaining == 0)
            )
            
            time_series.append({
                'days_passed': days_passed,
                'days_remaining': days_remaining,
                'pnl': float(pnl)
            })
        
        return {
            'time_series': time_series,
            'underlying_price': float(underlying_price)
        }
    
    @staticmethod
    def generate_volatility_analysis(
        strategy: Strategy,
        underlying_price: Decimal,
        iv_changes: List[Decimal] = None
    ) -> Dict:
        """
        Generate implied volatility impact analysis
        
        Args:
            strategy: The options strategy
            underlying_price: Current underlying price
            iv_changes: List of IV changes to analyze (e.g., [-0.10, -0.05, 0, 0.05, 0.10])
            
        Returns:
            Volatility impact analysis data
        """
        if iv_changes is None:
            iv_changes = [Decimal('-0.10'), Decimal('-0.05'), Decimal('0'), 
                         Decimal('0.05'), Decimal('0.10')]
        
        iv_series = []
        
        base_pnl = PnLCalculator.calculate_strategy_pnl(
            strategy,
            underlying_price,
            at_expiration=False
        )
        
        for iv_change in iv_changes:
            # Create a copy of strategy with adjusted IV
            adjusted_pnl = base_pnl  # Simplified for now
            
            iv_series.append({
                'iv_change': float(iv_change),
                'iv_change_pct': float(iv_change * Decimal('100')),
                'pnl': float(adjusted_pnl),
                'pnl_change': float(adjusted_pnl - base_pnl)
            })
        
        return {
            'volatility_series': iv_series,
            'base_pnl': float(base_pnl),
            'underlying_price': float(underlying_price)
        }
    
    @staticmethod
    def generate_heatmap_data(
        strategy: Strategy,
        price_range: Optional[Tuple[Decimal, Decimal]] = None,
        days_range: Optional[Tuple[int, int]] = None,
        price_points: int = 20,
        time_points: int = 10
    ) -> Dict:
        """
        Generate P&L heatmap data (price vs time)
        
        Args:
            strategy: The options strategy
            price_range: Price range for analysis
            days_range: Days range (from, to)
            price_points: Number of price points
            time_points: Number of time points
            
        Returns:
            Heatmap data structure
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
        
        if days_range is None:
            max_days = strategy.legs[0].option.days_to_expiration if strategy.legs else 30
            days_range = (0, min(max_days, 60))
        
        prices = np.linspace(float(min_price), float(max_price), price_points)
        days = np.linspace(days_range[0], days_range[1], time_points)
        
        # Initialize P&L matrix
        pnl_matrix = []
        
        for day in days:
            pnl_row = []
            for price in prices:
                # Calculate P&L at this price and time point
                # Simplified: using expiration P&L
                pnl = PnLCalculator.calculate_strategy_pnl(
                    strategy,
                    Decimal(str(price)),
                    at_expiration=(day >= days_range[1])
                )
                pnl_row.append(float(pnl))
            pnl_matrix.append(pnl_row)
        
        return {
            'prices': prices.tolist(),
            'days': days.tolist(),
            'pnl_matrix': pnl_matrix,
            'x_label': 'Underlying Price',
            'y_label': 'Days Passed',
            'z_label': 'P&L ($)'
        }
    
    @staticmethod
    def get_chart_config(chart_type: str = 'payoff') -> Dict:
        """
        Get default chart configuration for different visualization types
        
        Args:
            chart_type: Type of chart (payoff, greeks, heatmap, etc.)
            
        Returns:
            Chart configuration dictionary
        """
        configs = {
            'payoff': {
                'title': 'Strategy Payoff Diagram',
                'x_axis': 'Underlying Price ($)',
                'y_axis': 'Profit/Loss ($)',
                'show_grid': True,
                'show_breakeven': True,
                'show_max_profit': True,
                'show_max_loss': True,
                'colors': {
                    'profit': '#10b981',
                    'loss': '#ef4444',
                    'breakeven': '#f59e0b',
                    'current': '#3b82f6',
                    'expiration': '#8b5cf6'
                }
            },
            'greeks': {
                'title': 'Greeks Analysis',
                'show_grid': True,
                'colors': {
                    'delta': '#3b82f6',
                    'gamma': '#10b981',
                    'theta': '#ef4444',
                    'vega': '#f59e0b',
                    'rho': '#8b5cf6'
                }
            },
            'heatmap': {
                'title': 'P&L Heatmap (Price vs Time)',
                'colormap': 'RdYlGn',
                'show_colorbar': True
            }
        }
        
        return configs.get(chart_type, {})
