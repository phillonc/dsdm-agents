"""Options trade data model."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from decimal import Decimal


class TradeType(Enum):
    """Type of options trade."""
    SWEEP = "sweep"
    BLOCK = "block"
    DARK_POOL = "dark_pool"
    REGULAR = "regular"
    SPLIT = "split"


class OrderType(Enum):
    """Order type for options trade."""
    CALL = "call"
    PUT = "put"


@dataclass
class OptionsTrade:
    """Represents a single options trade."""
    
    trade_id: str
    symbol: str
    underlying_symbol: str
    order_type: OrderType
    strike: Decimal
    expiration: datetime
    premium: Decimal
    size: int
    price: Decimal
    timestamp: datetime
    trade_type: TradeType
    
    # Exchange and execution details
    exchange: str
    execution_side: str  # "bid", "ask", "mid"
    
    # Flow analysis fields
    is_aggressive: bool = False
    is_opening: bool = True
    sentiment: str = "neutral"  # "bullish", "bearish", "neutral"
    
    # Smart money indicators
    unusual_size: bool = False
    above_ask: bool = False
    below_bid: bool = False
    implied_volatility: Optional[Decimal] = None
    
    # Market context
    underlying_price: Optional[Decimal] = None
    open_interest: Optional[int] = None
    volume_oi_ratio: Optional[Decimal] = None
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    @property
    def notional_value(self) -> Decimal:
        """Calculate notional value of the trade."""
        return self.premium * Decimal(self.size) * Decimal(100)
    
    @property
    def is_itm(self) -> bool:
        """Check if option is in-the-money."""
        if not self.underlying_price:
            return False
        
        if self.order_type == OrderType.CALL:
            return self.underlying_price > self.strike
        else:
            return self.underlying_price < self.strike
    
    @property
    def moneyness(self) -> Optional[Decimal]:
        """Calculate option moneyness (S/K for calls, K/S for puts)."""
        if not self.underlying_price:
            return None
        
        if self.order_type == OrderType.CALL:
            return self.underlying_price / self.strike
        else:
            return self.strike / self.underlying_price
    
    def days_to_expiration(self, reference_time: Optional[datetime] = None) -> int:
        """Calculate days to expiration."""
        ref = reference_time or datetime.now()
        delta = self.expiration - ref
        return max(0, delta.days)
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary."""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'underlying_symbol': self.underlying_symbol,
            'order_type': self.order_type.value,
            'strike': str(self.strike),
            'expiration': self.expiration.isoformat(),
            'premium': str(self.premium),
            'size': self.size,
            'price': str(self.price),
            'timestamp': self.timestamp.isoformat(),
            'trade_type': self.trade_type.value,
            'exchange': self.exchange,
            'execution_side': self.execution_side,
            'is_aggressive': self.is_aggressive,
            'is_opening': self.is_opening,
            'sentiment': self.sentiment,
            'unusual_size': self.unusual_size,
            'notional_value': str(self.notional_value),
            'metadata': self.metadata,
        }
