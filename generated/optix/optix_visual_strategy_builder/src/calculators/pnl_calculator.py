"""
P&L (Profit and Loss) calculator for options strategies
"""
from decimal import Decimal
from typing import List, Dict, Tuple
import numpy as np

from ..models.option import Option, OptionType, OptionPosition
from ..models.strategy import Strategy
from .black_scholes import BlackScholesCalculator


class PnLCalculator:
    """
    Calculate profit/loss for options and strategies
    """
    
    @staticmethod
    def calculate_option_pnl(
        option: Option,
        current_price: Decimal,
        underlying_price: Decimal
    ) -> Decimal:
        """
        Calculate current P&L for a single option
        
        Args:
            option: The option contract
            current_price: Current option price
            underlying_price: Current underlying price
            
        Returns:
            Profit or loss
        """
        initial_cost = option.total_premium
        current_value = current_price * option.quantity * Decimal('100')
        
        if option.position == OptionPosition.LONG:
            # Long position: paid premium initially, receive value on close
            pnl = current_value + initial_cost  # initial_cost is negative for long
        else:
            # Short position: received premium initially, pay value on close
            pnl = initial_cost - current_value  # initial_cost is positive for short
        
        return pnl
    
    @staticmethod
    def calculate_option_pnl_at_expiration(
        option: Option,
        underlying_price: Decimal
    ) -> Decimal:
        """
        Calculate P&L for an option at expiration
        
        Args:
            option: The option contract
            underlying_price: Underlying price at expiration
            
        Returns:
            Profit or loss at expiration
        """
        # Calculate intrinsic value
        if option.option_type == OptionType.CALL:
            intrinsic_value = max(Decimal('0'), underlying_price - option.strike_price)
        else:  # PUT
            intrinsic_value = max(Decimal('0'), option.strike_price - underlying_price)
        
        # Calculate P&L
        contract_value = intrinsic_value * option.quantity * Decimal('100')
        
        if option.position == OptionPosition.LONG:
            pnl = contract_value + option.total_premium
        else:
            pnl = option.total_premium - contract_value
        
        return pnl
    
    @staticmethod
    def calculate_strategy_pnl(
        strategy: Strategy,
        underlying_price: Decimal,
        at_expiration: bool = False
    ) -> Decimal:
        """
        Calculate total P&L for a strategy
        
        Args:
            strategy: The options strategy
            underlying_price: Current or expiration underlying price
            at_expiration: If True, calculate P&L at expiration
            
        Returns:
            Total profit or loss
        """
        total_pnl = Decimal('0')
        
        for leg in strategy.legs:
            option = leg.option
            
            if at_expiration:
                pnl = PnLCalculator.calculate_option_pnl_at_expiration(
                    option, underlying_price
                )
            else:
                # Calculate current option price
                if option.underlying_price is None:
                    option.underlying_price = underlying_price
                
                current_price = BlackScholesCalculator.price_option(option)
                pnl = PnLCalculator.calculate_option_pnl(
                    option, current_price, underlying_price
                )
            
            total_pnl += pnl
        
        return total_pnl
    
    @staticmethod
    def calculate_payoff_diagram(
        strategy: Strategy,
        price_range: Tuple[Decimal, Decimal] = None,
        num_points: int = 100,
        at_expiration: bool = True
    ) -> Dict[str, List]:
        """
        Calculate payoff diagram data for visualization
        
        Args:
            strategy: The options strategy
            price_range: (min_price, max_price) tuple. If None, auto-calculate
            num_points: Number of points to calculate
            at_expiration: If True, calculate at expiration
            
        Returns:
            Dictionary with 'prices' and 'pnl' lists
        """
        # Determine price range
        if price_range is None:
            strikes = [leg.option.strike_price for leg in strategy.legs]
            min_strike = min(strikes)
            max_strike = max(strikes)
            
            # Create range 20% below min and 20% above max
            min_price = min_strike * Decimal('0.8')
            max_price = max_strike * Decimal('1.2')
        else:
            min_price, max_price = price_range
        
        # Generate price points
        prices = np.linspace(float(min_price), float(max_price), num_points)
        pnl_values = []
        
        for price in prices:
            underlying_price = Decimal(str(price))
            pnl = PnLCalculator.calculate_strategy_pnl(
                strategy, underlying_price, at_expiration
            )
            pnl_values.append(float(pnl))
        
        return {
            'prices': prices.tolist(),
            'pnl': pnl_values,
            'breakeven_points': PnLCalculator._find_breakeven_points(prices, pnl_values)
        }
    
    @staticmethod
    def _find_breakeven_points(prices: np.ndarray, pnl_values: List[float]) -> List[float]:
        """
        Find breakeven points where P&L crosses zero
        """
        breakevens = []
        pnl_array = np.array(pnl_values)
        
        # Find zero crossings
        for i in range(len(pnl_array) - 1):
            if (pnl_array[i] <= 0 and pnl_array[i + 1] > 0) or \
               (pnl_array[i] >= 0 and pnl_array[i + 1] < 0):
                # Linear interpolation to find exact breakeven
                x1, x2 = prices[i], prices[i + 1]
                y1, y2 = pnl_array[i], pnl_array[i + 1]
                
                if y2 != y1:
                    breakeven = x1 - y1 * (x2 - x1) / (y2 - y1)
                    breakevens.append(float(breakeven))
        
        return breakevens
    
    @staticmethod
    def calculate_max_profit(
        strategy: Strategy,
        price_range: Tuple[Decimal, Decimal] = None,
        num_points: int = 200
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate maximum profit and the price at which it occurs
        
        Returns:
            (max_profit, price_at_max)
        """
        payoff_data = PnLCalculator.calculate_payoff_diagram(
            strategy, price_range, num_points, at_expiration=True
        )
        
        pnl_values = payoff_data['pnl']
        prices = payoff_data['prices']
        
        max_idx = np.argmax(pnl_values)
        max_profit = Decimal(str(pnl_values[max_idx]))
        price_at_max = Decimal(str(prices[max_idx]))
        
        return max_profit, price_at_max
    
    @staticmethod
    def calculate_max_loss(
        strategy: Strategy,
        price_range: Tuple[Decimal, Decimal] = None,
        num_points: int = 200
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate maximum loss and the price at which it occurs
        
        Returns:
            (max_loss, price_at_max_loss)
        """
        payoff_data = PnLCalculator.calculate_payoff_diagram(
            strategy, price_range, num_points, at_expiration=True
        )
        
        pnl_values = payoff_data['pnl']
        prices = payoff_data['prices']
        
        min_idx = np.argmin(pnl_values)
        max_loss = Decimal(str(pnl_values[min_idx]))
        price_at_max_loss = Decimal(str(prices[min_idx]))
        
        return max_loss, price_at_max_loss
    
    @staticmethod
    def calculate_risk_reward_ratio(strategy: Strategy) -> Dict[str, Decimal]:
        """
        Calculate risk/reward metrics for the strategy
        
        Returns:
            Dictionary with risk/reward metrics
        """
        max_profit, _ = PnLCalculator.calculate_max_profit(strategy)
        max_loss, _ = PnLCalculator.calculate_max_loss(strategy)
        
        # Calculate ratio (avoid division by zero)
        if max_loss != 0:
            risk_reward_ratio = abs(max_profit / max_loss)
        else:
            risk_reward_ratio = Decimal('999.99')  # Effectively unlimited
        
        return {
            'max_profit': max_profit,
            'max_loss': max_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'initial_cost': strategy.total_cost,
            'return_on_risk': (max_profit / abs(max_loss) * Decimal('100')) if max_loss != 0 else Decimal('999.99')
        }
