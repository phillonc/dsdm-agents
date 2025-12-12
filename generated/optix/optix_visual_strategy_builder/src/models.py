"""
Data models for the Visual Strategy Builder.

This module defines core data structures for options, legs, strategies, and Greeks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid


class OptionType(Enum):
    """Option type enumeration."""
    CALL = "CALL"
    PUT = "PUT"


class PositionType(Enum):
    """Position type enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"


class StrategyType(Enum):
    """Pre-defined strategy types."""
    CUSTOM = "CUSTOM"
    IRON_CONDOR = "IRON_CONDOR"
    BUTTERFLY = "BUTTERFLY"
    STRADDLE = "STRADDLE"
    STRANGLE = "STRANGLE"
    VERTICAL_SPREAD = "VERTICAL_SPREAD"
    CALENDAR_SPREAD = "CALENDAR_SPREAD"
    DIAGONAL_SPREAD = "DIAGONAL_SPREAD"
    COVERED_CALL = "COVERED_CALL"
    PROTECTIVE_PUT = "PROTECTIVE_PUT"


@dataclass
class Greeks:
    """Greek values for options positions."""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    def __add__(self, other: 'Greeks') -> 'Greeks':
        """Add two Greeks objects."""
        return Greeks(
            delta=self.delta + other.delta,
            gamma=self.gamma + other.gamma,
            theta=self.theta + other.theta,
            vega=self.vega + other.vega,
            rho=self.rho + other.rho
        )
    
    def __mul__(self, scalar: float) -> 'Greeks':
        """Multiply Greeks by a scalar."""
        return Greeks(
            delta=self.delta * scalar,
            gamma=self.gamma * scalar,
            theta=self.theta * scalar,
            vega=self.vega * scalar,
            rho=self.rho * scalar
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'delta': round(self.delta, 4),
            'gamma': round(self.gamma, 4),
            'theta': round(self.theta, 4),
            'vega': round(self.vega, 4),
            'rho': round(self.rho, 4)
        }


@dataclass
class OptionLeg:
    """Represents a single option leg in a strategy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    option_type: OptionType = OptionType.CALL
    position_type: PositionType = PositionType.LONG
    strike: float = 0.0
    expiration: date = field(default_factory=date.today)
    quantity: int = 1
    premium: float = 0.0
    underlying_symbol: str = ""
    implied_volatility: float = 0.0
    greeks: Greeks = field(default_factory=Greeks)
    
    def get_cost(self) -> float:
        """Calculate the cost/credit of this leg."""
        multiplier = 100  # Standard option contract multiplier
        cost = self.premium * self.quantity * multiplier
        # Long positions are debits (negative), short positions are credits (positive)
        return -cost if self.position_type == PositionType.LONG else cost
    
    def get_position_greeks(self) -> Greeks:
        """Get Greeks adjusted for position type and quantity."""
        multiplier = self.quantity
        if self.position_type == PositionType.SHORT:
            multiplier *= -1
        return self.greeks * multiplier
    
    def calculate_pnl(self, underlying_price: float) -> float:
        """Calculate P&L at a given underlying price."""
        intrinsic_value = 0.0
        
        if self.option_type == OptionType.CALL:
            intrinsic_value = max(0, underlying_price - self.strike)
        else:  # PUT
            intrinsic_value = max(0, self.strike - underlying_price)
        
        multiplier = 100 * self.quantity
        
        if self.position_type == PositionType.LONG:
            return (intrinsic_value * multiplier) - abs(self.get_cost())
        else:  # SHORT
            return abs(self.get_cost()) - (intrinsic_value * multiplier)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'option_type': self.option_type.value,
            'position_type': self.position_type.value,
            'strike': self.strike,
            'expiration': self.expiration.isoformat(),
            'quantity': self.quantity,
            'premium': self.premium,
            'underlying_symbol': self.underlying_symbol,
            'implied_volatility': self.implied_volatility,
            'greeks': self.greeks.to_dict(),
            'cost': self.get_cost()
        }


@dataclass
class OptionsStrategy:
    """Represents a complete options strategy with multiple legs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Strategy"
    strategy_type: StrategyType = StrategyType.CUSTOM
    underlying_symbol: str = ""
    legs: List[OptionLeg] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    def add_leg(self, leg: OptionLeg) -> None:
        """Add a leg to the strategy."""
        self.legs.append(leg)
        self.updated_at = datetime.now()
    
    def remove_leg(self, leg_id: str) -> bool:
        """Remove a leg from the strategy by ID."""
        initial_length = len(self.legs)
        self.legs = [leg for leg in self.legs if leg.id != leg_id]
        if len(self.legs) < initial_length:
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_total_cost(self) -> float:
        """Calculate total cost/credit of the strategy."""
        return sum(leg.get_cost() for leg in self.legs)
    
    def get_aggregated_greeks(self) -> Greeks:
        """Calculate aggregated Greeks for the entire strategy."""
        total_greeks = Greeks()
        for leg in self.legs:
            total_greeks = total_greeks + leg.get_position_greeks()
        return total_greeks
    
    def calculate_pnl(self, underlying_price: float) -> float:
        """Calculate total P&L at a given underlying price."""
        return sum(leg.calculate_pnl(underlying_price) for leg in self.legs)
    
    def calculate_pnl_range(self, price_range: List[float]) -> List[Dict[str, float]]:
        """Calculate P&L across a range of prices."""
        return [
            {'price': price, 'pnl': self.calculate_pnl(price)}
            for price in price_range
        ]
    
    def get_max_profit(self, price_range: List[float]) -> Optional[float]:
        """Calculate maximum profit in the given price range."""
        if not price_range:
            return None
        pnls = [self.calculate_pnl(price) for price in price_range]
        return max(pnls)
    
    def get_max_loss(self, price_range: List[float]) -> Optional[float]:
        """Calculate maximum loss in the given price range."""
        if not price_range:
            return None
        pnls = [self.calculate_pnl(price) for price in price_range]
        return min(pnls)
    
    def get_breakeven_points(self, price_range: List[float], tolerance: float = 0.5) -> List[float]:
        """Find approximate breakeven points."""
        breakeven_points = []
        pnl_data = self.calculate_pnl_range(price_range)
        
        for i in range(len(pnl_data) - 1):
            current_pnl = pnl_data[i]['pnl']
            next_pnl = pnl_data[i + 1]['pnl']
            
            # Check if P&L crosses zero
            if (current_pnl <= tolerance and next_pnl >= -tolerance) or \
               (current_pnl >= -tolerance and next_pnl <= tolerance):
                # Linear interpolation for more accurate breakeven
                if abs(next_pnl - current_pnl) > 0.001:
                    ratio = abs(current_pnl) / abs(next_pnl - current_pnl)
                    breakeven = pnl_data[i]['price'] + ratio * (pnl_data[i + 1]['price'] - pnl_data[i]['price'])
                    breakeven_points.append(round(breakeven, 2))
        
        return breakeven_points
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'strategy_type': self.strategy_type.value,
            'underlying_symbol': self.underlying_symbol,
            'legs': [leg.to_dict() for leg in self.legs],
            'total_cost': self.get_total_cost(),
            'aggregated_greeks': self.get_aggregated_greeks().to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'notes': self.notes
        }


@dataclass
class ScenarioAnalysis:
    """Represents a what-if scenario analysis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Scenario"
    underlying_price_change: float = 0.0  # Percentage change
    volatility_change: float = 0.0  # Percentage change
    days_to_expiration_change: int = 0  # Days forward
    results: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'underlying_price_change': self.underlying_price_change,
            'volatility_change': self.volatility_change,
            'days_to_expiration_change': self.days_to_expiration_change,
            'results': self.results
        }
