"""
P&L calculation and payoff diagram generation.

This module provides utilities for calculating profit/loss and generating
visualization data for options strategies.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from .models import OptionsStrategy, OptionLeg


class PayoffCalculator:
    """Calculate payoffs and generate payoff diagram data."""
    
    @staticmethod
    def generate_price_range(
        current_price: float,
        range_percentage: float = 0.30,
        num_points: int = 100
    ) -> List[float]:
        """
        Generate a price range for payoff calculations.
        
        Args:
            current_price: Current price of underlying
            range_percentage: Percentage range around current price (e.g., 0.30 = ±30%)
            num_points: Number of price points to generate
            
        Returns:
            List of price points
        """
        lower_bound = current_price * (1 - range_percentage)
        upper_bound = current_price * (1 + range_percentage)
        return np.linspace(lower_bound, upper_bound, num_points).tolist()
    
    @staticmethod
    def calculate_payoff_diagram(
        strategy: OptionsStrategy,
        price_range: Optional[List[float]] = None,
        current_price: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Calculate complete payoff diagram data.
        
        Args:
            strategy: The options strategy
            price_range: Custom price range (optional)
            current_price: Current price for default range calculation
            
        Returns:
            Dictionary with payoff data including prices, P&L values, and key metrics
        """
        # Determine price range
        if price_range is None:
            if current_price is None:
                # Try to infer from strategy legs
                if strategy.legs:
                    strikes = [leg.strike for leg in strategy.legs]
                    current_price = sum(strikes) / len(strikes)
                else:
                    raise ValueError("Either price_range or current_price must be provided")
            
            price_range = PayoffCalculator.generate_price_range(current_price)
        
        # Calculate P&L for each price point
        pnl_data = strategy.calculate_pnl_range(price_range)
        
        # Extract key metrics
        max_profit = strategy.get_max_profit(price_range)
        max_loss = strategy.get_max_loss(price_range)
        breakeven_points = strategy.get_breakeven_points(price_range)
        
        # Calculate current P&L if current price is known
        current_pnl = None
        if current_price:
            current_pnl = strategy.calculate_pnl(current_price)
        
        return {
            'price_range': price_range,
            'pnl_data': pnl_data,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'breakeven_points': breakeven_points,
            'current_price': current_price,
            'current_pnl': current_pnl,
            'total_cost': strategy.get_total_cost(),
            'num_legs': len(strategy.legs)
        }
    
    @staticmethod
    def calculate_probability_of_profit(
        strategy: OptionsStrategy,
        current_price: float,
        expected_volatility: float,
        days_to_expiration: int,
        num_simulations: int = 10000
    ) -> Dict[str, float]:
        """
        Monte Carlo simulation to estimate probability of profit.
        
        Args:
            strategy: The options strategy
            current_price: Current underlying price
            expected_volatility: Expected volatility (annual)
            days_to_expiration: Days until expiration
            num_simulations: Number of Monte Carlo simulations
            
        Returns:
            Dictionary with probability metrics
        """
        # Convert annual volatility to daily
        daily_vol = expected_volatility / np.sqrt(252)
        
        # Generate random price movements
        np.random.seed(42)  # For reproducibility
        random_returns = np.random.normal(0, daily_vol, (num_simulations, days_to_expiration))
        
        # Calculate cumulative returns
        cumulative_returns = np.exp(np.sum(random_returns, axis=1))
        final_prices = current_price * cumulative_returns
        
        # Calculate P&L for each simulated price
        profitable_simulations = 0
        total_profit = 0.0
        total_loss = 0.0
        
        for final_price in final_prices:
            pnl = strategy.calculate_pnl(final_price)
            if pnl > 0:
                profitable_simulations += 1
                total_profit += pnl
            else:
                total_loss += pnl
        
        prob_of_profit = profitable_simulations / num_simulations
        avg_profit = total_profit / profitable_simulations if profitable_simulations > 0 else 0
        avg_loss = total_loss / (num_simulations - profitable_simulations) if (num_simulations - profitable_simulations) > 0 else 0
        
        expected_value = (avg_profit * prob_of_profit) + (avg_loss * (1 - prob_of_profit))
        
        return {
            'probability_of_profit': round(prob_of_profit * 100, 2),
            'average_profit': round(avg_profit, 2),
            'average_loss': round(avg_loss, 2),
            'expected_value': round(expected_value, 2),
            'simulations': num_simulations
        }
    
    @staticmethod
    def calculate_risk_reward_ratio(
        strategy: OptionsStrategy,
        price_range: List[float]
    ) -> Dict[str, float]:
        """
        Calculate risk/reward metrics.
        
        Args:
            strategy: The options strategy
            price_range: Price range for calculations
            
        Returns:
            Dictionary with risk/reward metrics
        """
        max_profit = strategy.get_max_profit(price_range)
        max_loss = strategy.get_max_loss(price_range)
        
        # Calculate risk/reward ratio
        risk_reward_ratio = None
        if max_loss and max_loss != 0:
            risk_reward_ratio = abs(max_profit / max_loss)
        
        # Return on risk
        return_on_risk = None
        if max_loss and max_loss != 0:
            return_on_risk = (max_profit / abs(max_loss)) * 100
        
        return {
            'max_profit': round(max_profit, 2) if max_profit else None,
            'max_loss': round(max_loss, 2) if max_loss else None,
            'risk_reward_ratio': round(risk_reward_ratio, 2) if risk_reward_ratio else None,
            'return_on_risk_percent': round(return_on_risk, 2) if return_on_risk else None,
            'total_capital_at_risk': round(abs(max_loss), 2) if max_loss else None
        }


class RealTimePnLTracker:
    """Track real-time P&L changes for a strategy."""
    
    def __init__(self, strategy: OptionsStrategy):
        """Initialize tracker with a strategy."""
        self.strategy = strategy
        self.pnl_history: List[Dict[str, any]] = []
    
    def update_pnl(self, current_price: float, timestamp: str = None) -> Dict[str, any]:
        """
        Update P&L calculation with current price.
        
        Args:
            current_price: Current underlying price
            timestamp: Optional timestamp for the update
            
        Returns:
            Current P&L snapshot
        """
        from datetime import datetime
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        current_pnl = self.strategy.calculate_pnl(current_price)
        greeks = self.strategy.get_aggregated_greeks()
        
        snapshot = {
            'timestamp': timestamp,
            'underlying_price': current_price,
            'pnl': round(current_pnl, 2),
            'total_cost': round(self.strategy.get_total_cost(), 2),
            'greeks': greeks.to_dict()
        }
        
        self.pnl_history.append(snapshot)
        return snapshot
    
    def get_pnl_change(self) -> Optional[float]:
        """Get P&L change since last update."""
        if len(self.pnl_history) < 2:
            return None
        
        return self.pnl_history[-1]['pnl'] - self.pnl_history[-2]['pnl']
    
    def get_pnl_history(self) -> List[Dict[str, any]]:
        """Get complete P&L history."""
        return self.pnl_history
    
    def reset_history(self) -> None:
        """Reset P&L history."""
        self.pnl_history = []
