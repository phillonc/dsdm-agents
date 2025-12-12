"""
Watchlist Service Models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import uuid


class WatchlistItem(BaseModel):
    """Individual watchlist item"""
    symbol: str
    added_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper()


class Watchlist(BaseModel):
    """User watchlist"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    
    symbols: List[WatchlistItem] = []
    
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('symbols')
    def max_symbols(cls, v):
        """Enforce 50 symbol limit per watchlist"""
        if len(v) > 50:
            raise ValueError('Maximum 50 symbols allowed per watchlist')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class WatchlistCreate(BaseModel):
    """Create watchlist request"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    is_default: bool = False


class WatchlistUpdate(BaseModel):
    """Update watchlist request"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    is_default: Optional[bool] = None


class AddSymbolRequest(BaseModel):
    """Add symbol to watchlist request"""
    symbol: str
    notes: Optional[str] = None
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper()


class RemoveSymbolRequest(BaseModel):
    """Remove symbol from watchlist request"""
    symbol: str
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper()
