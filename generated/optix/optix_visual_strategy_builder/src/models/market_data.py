"""
Market data models for pricing and analysis
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PricePoint:
    """
    Represents a price point in time
    """
    price: Decimal
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class MarketData:
    """
    Market data for option pricing
    """
    underlying_symbol: str
    underlying_price: Decimal
    timestamp: datetime
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: Optional[int] = None
    implied_volatility: Optional[Decimal] = None
    historical_volatility: Optional[Decimal] = None
    interest_rate: Decimal = Decimal('0.05')
    dividend_yield: Decimal = Decimal('0.0')
    
    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price from bid/ask"""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / Decimal('2')
        return self.underlying_price
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread"""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'underlying_symbol': self.underlying_symbol,
            'underlying_price': float(self.underlying_price),
            'timestamp': self.timestamp.isoformat(),
            'bid': float(self.bid) if self.bid else None,
            'ask': float(self.ask) if self.ask else None,
            'mid_price': float(self.mid_price),
            'spread': float(self.spread) if self.spread else None,
            'volume': self.volume,
            'implied_volatility': float(self.implied_volatility) if self.implied_volatility else None,
            'historical_volatility': float(self.historical_volatility) if self.historical_volatility else None,
            'interest_rate': float(self.interest_rate),
            'dividend_yield': float(self.dividend_yield)
        }
