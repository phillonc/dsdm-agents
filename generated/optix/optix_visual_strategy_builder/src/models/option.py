"""
Option data models for the Visual Strategy Builder
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from decimal import Decimal


class OptionType(Enum):
    """Option type enumeration"""
    CALL = "CALL"
    PUT = "PUT"


class OptionPosition(Enum):
    """Position type enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Option:
    """
    Represents an options contract with all relevant attributes
    """
    symbol: str
    underlying_symbol: str
    option_type: OptionType
    strike_price: Decimal
    expiration_date: datetime
    quantity: int
    position: OptionPosition
    premium: Decimal
    underlying_price: Optional[Decimal] = None
    implied_volatility: Optional[Decimal] = None
    interest_rate: Decimal = Decimal('0.05')
    dividend_yield: Decimal = Decimal('0.0')
    
    # Greeks (will be calculated)
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    rho: Optional[Decimal] = None
    
    # Metadata
    id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate and initialize option"""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.strike_price <= 0:
            raise ValueError("Strike price must be positive")
        if self.premium < 0:
            raise ValueError("Premium cannot be negative")
        if self.expiration_date <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
    
    @property
    def days_to_expiration(self) -> int:
        """Calculate days until expiration"""
        delta = self.expiration_date - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def time_to_expiration(self) -> Decimal:
        """Calculate time to expiration in years"""
        return Decimal(str(self.days_to_expiration / 365.0))
    
    @property
    def total_premium(self) -> Decimal:
        """Calculate total premium (premium * quantity * 100 shares per contract)"""
        multiplier = Decimal('100')
        if self.position == OptionPosition.LONG:
            return -self.premium * self.quantity * multiplier
        else:
            return self.premium * self.quantity * multiplier
    
    def intrinsic_value(self) -> Decimal:
        """Calculate intrinsic value of the option"""
        if self.underlying_price is None:
            return Decimal('0')
        
        if self.option_type == OptionType.CALL:
            return max(Decimal('0'), self.underlying_price - self.strike_price)
        else:
            return max(Decimal('0'), self.strike_price - self.underlying_price)
    
    def time_value(self) -> Decimal:
        """Calculate time value of the option"""
        return self.premium - self.intrinsic_value()
    
    def is_in_the_money(self) -> bool:
        """Check if option is in the money"""
        if self.underlying_price is None:
            return False
        return self.intrinsic_value() > Decimal('0')
    
    def is_at_the_money(self, threshold: Decimal = Decimal('0.01')) -> bool:
        """Check if option is at the money"""
        if self.underlying_price is None:
            return False
        diff = abs(self.underlying_price - self.strike_price)
        return diff <= threshold * self.strike_price
    
    def to_dict(self) -> dict:
        """Convert option to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'underlying_symbol': self.underlying_symbol,
            'option_type': self.option_type.value,
            'strike_price': float(self.strike_price),
            'expiration_date': self.expiration_date.isoformat(),
            'quantity': self.quantity,
            'position': self.position.value,
            'premium': float(self.premium),
            'underlying_price': float(self.underlying_price) if self.underlying_price else None,
            'implied_volatility': float(self.implied_volatility) if self.implied_volatility else None,
            'delta': float(self.delta) if self.delta else None,
            'gamma': float(self.gamma) if self.gamma else None,
            'theta': float(self.theta) if self.theta else None,
            'vega': float(self.vega) if self.vega else None,
            'rho': float(self.rho) if self.rho else None,
            'days_to_expiration': self.days_to_expiration,
            'intrinsic_value': float(self.intrinsic_value()),
            'time_value': float(self.time_value()),
            'total_premium': float(self.total_premium)
        }
