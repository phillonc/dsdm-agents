"""
Options data models
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, validator
import numpy as np


class OptionType(str, Enum):
    """Option type enumeration"""
    CALL = "call"
    PUT = "put"


class OptionSide(str, Enum):
    """Option side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OptionContract(BaseModel):
    """Option contract specification"""
    symbol: str = Field(..., description="Underlying symbol")
    expiration: date = Field(..., description="Expiration date")
    strike: float = Field(..., gt=0, description="Strike price")
    option_type: OptionType = Field(..., description="Call or Put")
    contract_symbol: Optional[str] = Field(None, description="Full option symbol")
    
    class Config:
        use_enum_values = True
        
    @validator('contract_symbol', always=True)
    def generate_contract_symbol(cls, v: Optional[str], values: dict) -> str:
        """Generate standard option symbol if not provided"""
        if v:
            return v
        symbol = values.get('symbol', '')
        exp = values.get('expiration')
        strike = values.get('strike', 0)
        opt_type = values.get('option_type', '')
        
        if exp and symbol and strike and opt_type:
            exp_str = exp.strftime('%y%m%d')
            strike_str = f"{int(strike * 1000):08d}"
            type_code = 'C' if opt_type == OptionType.CALL else 'P'
            return f"{symbol}{exp_str}{type_code}{strike_str}"
        return ""


class OptionQuote(BaseModel):
    """Option market quote data"""
    contract: OptionContract
    timestamp: datetime
    bid: float = Field(..., ge=0)
    ask: float = Field(..., ge=0)
    last: Optional[float] = Field(None, ge=0)
    volume: int = Field(default=0, ge=0)
    open_interest: int = Field(default=0, ge=0)
    implied_volatility: Optional[float] = Field(None, ge=0, le=5)
    delta: Optional[float] = Field(None, ge=-1, le=1)
    gamma: Optional[float] = Field(None, ge=0)
    theta: Optional[float] = Field(None)
    vega: Optional[float] = Field(None, ge=0)
    rho: Optional[float] = Field(None)
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        return (self.bid + self.ask) / 2
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        return self.ask - self.bid
    
    @property
    def spread_percent(self) -> float:
        """Calculate spread as percentage of mid"""
        mid = self.mid_price
        return (self.spread / mid * 100) if mid > 0 else 0


class OptionLeg(BaseModel):
    """Single leg of an options strategy"""
    contract: OptionContract
    side: OptionSide
    quantity: int = Field(..., gt=0)
    entry_price: Optional[float] = Field(None, ge=0)
    exit_price: Optional[float] = Field(None, ge=0)
    
    class Config:
        use_enum_values = True
    
    @property
    def position_multiplier(self) -> int:
        """Get position multiplier (+1 for buy, -1 for sell)"""
        return 1 if self.side == OptionSide.BUY else -1
    
    def calculate_pnl(self, exit_price: Optional[float] = None) -> float:
        """Calculate P&L for this leg"""
        if self.entry_price is None:
            return 0.0
        
        exit = exit_price if exit_price is not None else self.exit_price
        if exit is None:
            return 0.0
        
        # Buy: profit when price increases, Sell: profit when price decreases
        price_diff = (exit - self.entry_price) * self.position_multiplier
        return price_diff * self.quantity * 100  # 100 shares per contract


class OptionStrategy(BaseModel):
    """Multi-leg options strategy"""
    strategy_id: str
    name: str
    description: Optional[str] = None
    legs: list[OptionLeg]
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    max_loss: Optional[float] = None
    max_profit: Optional[float] = None
    breakeven_points: list[float] = Field(default_factory=list)
    
    @property
    def is_open(self) -> bool:
        """Check if strategy is still open"""
        return self.exit_time is None
    
    @property
    def total_contracts(self) -> int:
        """Total number of contracts"""
        return sum(leg.quantity for leg in self.legs)
    
    @property
    def net_delta(self) -> float:
        """Calculate net delta exposure"""
        # This would need quotes with Greeks
        return 0.0
    
    def calculate_total_pnl(self) -> float:
        """Calculate total strategy P&L"""
        return sum(leg.calculate_pnl() for leg in self.legs)
    
    def calculate_cost_basis(self) -> float:
        """Calculate initial cost/credit of strategy"""
        total = 0.0
        for leg in self.legs:
            if leg.entry_price is not None:
                total += leg.entry_price * leg.quantity * leg.position_multiplier * 100
        return total


class MarketConditions(BaseModel):
    """Market conditions snapshot"""
    timestamp: datetime
    underlying_price: float = Field(..., gt=0)
    underlying_symbol: str
    implied_volatility: Optional[float] = Field(None, ge=0)
    historical_volatility: Optional[float] = Field(None, ge=0)
    vix_level: Optional[float] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=0)
    
    # Volatility regime classification
    volatility_regime: Optional[str] = Field(None, description="low, medium, high")
    
    @validator('volatility_regime', always=True)
    def classify_regime(cls, v: Optional[str], values: dict) -> str:
        """Classify volatility regime"""
        if v:
            return v
        
        iv = values.get('implied_volatility')
        if iv is None:
            return "unknown"
        
        if iv < 0.15:
            return "low"
        elif iv < 0.30:
            return "medium"
        else:
            return "high"
