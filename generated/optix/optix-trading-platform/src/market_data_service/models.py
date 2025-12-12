"""
Market Data Models
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum


class OptionType(str, Enum):
    """Option contract type"""
    CALL = "call"
    PUT = "put"


class QuoteStatus(str, Enum):
    """Quote data status"""
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    CLOSED = "closed"


class Quote(BaseModel):
    """Real-time stock/ETF quote"""
    symbol: str
    last_price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    
    # Price changes
    change: Decimal = Decimal("0")
    change_percent: Decimal = Decimal("0")
    
    # Volume and trades
    volume: int = 0
    avg_volume: Optional[int] = None
    
    # Daily range
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    
    # Market status
    status: QuoteStatus = QuoteStatus.REAL_TIME
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class Greeks(BaseModel):
    """Option Greeks"""
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    rho: Optional[Decimal] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class OptionContract(BaseModel):
    """Individual option contract"""
    symbol: str  # Underlying symbol
    option_symbol: str  # Full option symbol
    strike: Decimal
    expiration_date: date
    option_type: OptionType
    
    # Pricing
    last_price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    
    # Greeks
    greeks: Greeks
    
    # Volatility and probabilities
    implied_volatility: Decimal
    
    # Volume and open interest
    volume: int = 0
    open_interest: int = 0
    
    # Contract details
    in_the_money: bool = False
    intrinsic_value: Decimal = Decimal("0")
    extrinsic_value: Decimal = Decimal("0")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class OptionsChain(BaseModel):
    """Complete options chain for an expiration"""
    symbol: str
    expiration_date: date
    underlying_price: Decimal
    
    calls: List[OptionContract]
    puts: List[OptionContract]
    
    # Chain-level statistics
    total_call_volume: int = 0
    total_put_volume: int = 0
    total_call_open_interest: int = 0
    total_put_open_interest: int = 0
    put_call_ratio: Optional[Decimal] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class OptionsExpirations(BaseModel):
    """Available option expiration dates"""
    symbol: str
    expirations: List[date]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class MarketHours(BaseModel):
    """Market hours information"""
    is_open: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    session_type: str = "regular"  # pre_market, regular, after_hours, closed
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HistoricalBar(BaseModel):
    """Historical OHLCV bar"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
