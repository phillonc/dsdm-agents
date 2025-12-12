"""
Order execution simulation with realistic fills
"""
from datetime import datetime
from typing import Optional, Tuple
import numpy as np
from enum import Enum

from ..models.option import OptionQuote, OptionLeg, OptionSide
from ..models.backtest import TransactionCostModel


class FillType(str, Enum):
    """Order fill type"""
    MARKET = "market"
    LIMIT = "limit"
    MID = "mid"


class OrderExecutor:
    """Simulates realistic order execution"""
    
    def __init__(self, transaction_costs: TransactionCostModel):
        self.transaction_costs = transaction_costs
        
    def execute_market_order(
        self,
        quote: OptionQuote,
        side: OptionSide,
        quantity: int
    ) -> Tuple[float, float, float]:
        """
        Execute market order
        
        Args:
            quote: Current option quote
            side: Buy or sell
            quantity: Number of contracts
            
        Returns:
            Tuple of (fill_price, commission, slippage_cost)
        """
        # Market orders get filled at ask (buy) or bid (sell)
        if side == OptionSide.BUY:
            base_price = quote.ask
        else:
            base_price = quote.bid
        
        # Calculate slippage based on order size and liquidity
        slippage = self._calculate_slippage(
            base_price=base_price,
            quantity=quantity,
            quote=quote
        )
        
        fill_price = base_price + slippage if side == OptionSide.BUY else base_price - slippage
        
        # Calculate commission
        commission = self.transaction_costs.commission_per_contract * quantity
        
        slippage_cost = abs(slippage) * quantity * 100  # 100 shares per contract
        
        return fill_price, commission, slippage_cost
    
    def execute_limit_order(
        self,
        quote: OptionQuote,
        side: OptionSide,
        quantity: int,
        limit_price: float
    ) -> Optional[Tuple[float, float, float]]:
        """
        Execute limit order (may not fill)
        
        Args:
            quote: Current option quote
            side: Buy or sell
            quantity: Number of contracts
            limit_price: Limit price
            
        Returns:
            Tuple of (fill_price, commission, slippage_cost) or None if not filled
        """
        # Check if limit order would be filled
        if side == OptionSide.BUY and limit_price < quote.ask:
            return None  # Buy limit below ask won't fill immediately
        if side == OptionSide.SELL and limit_price > quote.bid:
            return None  # Sell limit above bid won't fill immediately
        
        # Limit order fills at limit price
        fill_price = limit_price
        
        # Still pay commission
        commission = self.transaction_costs.commission_per_contract * quantity
        
        # Minimal slippage for limit orders
        slippage_cost = 0.0
        
        return fill_price, commission, slippage_cost
    
    def execute_at_mid(
        self,
        quote: OptionQuote,
        side: OptionSide,
        quantity: int
    ) -> Tuple[float, float, float]:
        """
        Execute at mid price (optimistic execution)
        
        Args:
            quote: Current option quote
            side: Buy or sell
            quantity: Number of contracts
            
        Returns:
            Tuple of (fill_price, commission, slippage_cost)
        """
        fill_price = quote.mid_price
        
        # Calculate spread cost
        spread_cost = self._calculate_spread_cost(quote, quantity)
        
        # Commission
        commission = self.transaction_costs.commission_per_contract * quantity
        
        return fill_price, commission, spread_cost
    
    def _calculate_slippage(
        self,
        base_price: float,
        quantity: int,
        quote: OptionQuote
    ) -> float:
        """
        Calculate price slippage based on market conditions
        
        Args:
            base_price: Base price before slippage
            quantity: Order quantity
            quote: Current quote
            
        Returns:
            Slippage amount
        """
        # Base slippage from config
        base_slippage = base_price * (self.transaction_costs.slippage_percent / 100)
        
        # Adjust for liquidity (volume and open interest)
        liquidity_factor = self._calculate_liquidity_factor(quantity, quote)
        
        # Adjust for spread width
        spread_factor = quote.spread / quote.mid_price if quote.mid_price > 0 else 0
        
        # Combined slippage
        total_slippage = base_slippage * (1 + liquidity_factor + spread_factor)
        
        return total_slippage
    
    def _calculate_liquidity_factor(
        self,
        quantity: int,
        quote: OptionQuote
    ) -> float:
        """
        Calculate liquidity impact factor
        
        Args:
            quantity: Order size
            quote: Current quote
            
        Returns:
            Liquidity factor (0 = high liquidity, higher = low liquidity)
        """
        # Use open interest as liquidity proxy
        if quote.open_interest == 0:
            return 1.0  # High impact if no open interest
        
        # Calculate order size relative to open interest
        size_ratio = quantity / quote.open_interest
        
        # Square root model for market impact
        liquidity_factor = np.sqrt(size_ratio) * 0.5
        
        return min(liquidity_factor, 2.0)  # Cap at 2x
    
    def _calculate_spread_cost(
        self,
        quote: OptionQuote,
        quantity: int
    ) -> float:
        """
        Calculate cost of crossing the spread
        
        Args:
            quote: Current quote
            quantity: Order quantity
            
        Returns:
            Spread cost in dollars
        """
        # Pay percentage of spread based on config
        spread_to_pay = quote.spread * (
            self.transaction_costs.spread_cost_percent / 100
        )
        
        return spread_to_pay * quantity * 100  # 100 shares per contract
    
    def simulate_fill_probability(
        self,
        quote: OptionQuote,
        side: OptionSide,
        limit_price: float,
        time_seconds: int = 60
    ) -> float:
        """
        Simulate probability of limit order fill
        
        Args:
            quote: Current quote
            side: Buy or sell
            limit_price: Limit price
            time_seconds: Time to wait for fill
            
        Returns:
            Fill probability (0-1)
        """
        if side == OptionSide.BUY:
            # Buy limit above ask has high probability
            if limit_price >= quote.ask:
                return 0.95
            # Buy limit at mid has medium probability
            elif limit_price >= quote.mid_price:
                return 0.5
            # Buy limit near bid has low probability
            else:
                distance_factor = (limit_price - quote.bid) / quote.spread
                return max(0.1, distance_factor * 0.3)
        else:  # SELL
            # Sell limit below bid has high probability
            if limit_price <= quote.bid:
                return 0.95
            # Sell limit at mid has medium probability
            elif limit_price <= quote.mid_price:
                return 0.5
            # Sell limit near ask has low probability
            else:
                distance_factor = (quote.ask - limit_price) / quote.spread
                return max(0.1, distance_factor * 0.3)
    
    def apply_transaction_costs(
        self,
        pnl: float,
        commission: float,
        slippage: float
    ) -> float:
        """
        Apply transaction costs to P&L
        
        Args:
            pnl: Gross P&L
            commission: Commission paid
            slippage: Slippage cost
            
        Returns:
            Net P&L after costs
        """
        return pnl - commission - slippage


class PositionSizer:
    """Calculate position sizes based on various methods"""
    
    @staticmethod
    def fixed_quantity(quantity: int) -> int:
        """Fixed quantity position sizing"""
        return quantity
    
    @staticmethod
    def percent_of_capital(
        capital: float,
        percent: float,
        option_price: float
    ) -> int:
        """
        Position size as percentage of capital
        
        Args:
            capital: Available capital
            percent: Percentage to risk (0-100)
            option_price: Price per contract
            
        Returns:
            Number of contracts
        """
        risk_amount = capital * (percent / 100)
        contracts = int(risk_amount / (option_price * 100))
        return max(1, contracts)
    
    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital: float,
        option_price: float
    ) -> int:
        """
        Kelly criterion position sizing
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount
            capital: Available capital
            option_price: Price per contract
            
        Returns:
            Number of contracts
        """
        if avg_loss == 0 or win_rate == 0:
            return 1
        
        # Kelly formula: f = (p * b - q) / b
        # where p = win rate, q = loss rate, b = win/loss ratio
        b = abs(avg_win / avg_loss)
        q = 1 - win_rate
        
        kelly_fraction = (win_rate * b - q) / b
        
        # Use fractional Kelly (1/4) for safety
        kelly_fraction = max(0.0, min(kelly_fraction * 0.25, 0.25))
        
        risk_amount = capital * kelly_fraction
        contracts = int(risk_amount / (option_price * 100))
        
        return max(1, contracts)
