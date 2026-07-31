"""
Data models for brokerage service
"""

from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class BrokerageProvider(str, Enum):
    """Supported brokerage providers"""
    SCHWAB = "schwab"
    FIDELITY = "fidelity"
    ROBINHOOD = "robinhood"
    IBKR = "ibkr"
    WEBULL = "webull"


class PositionType(str, Enum):
    """Types of positions"""
    STOCK = "stock"
    OPTION = "option"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    CRYPTO = "crypto"


class TransactionType(str, Enum):
    """Types of transactions"""
    BUY = "buy"
    SELL = "sell"
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    EXPIRED = "expired"
    ASSIGNED = "assigned"
    EXERCISED = "exercised"


class Position(BaseModel):
    """Position model"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    connection_id: Optional[uuid.UUID] = None
    symbol: str
    position_type: PositionType
    quantity: Decimal
    average_price: Decimal
    cost_basis: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal
    
    # Options specific fields
    strike_price: Optional[Decimal] = None
    expiration_date: Optional[datetime] = None
    option_type: Optional[str] = None  # 'CALL' or 'PUT'
    
    # Greeks for options
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class Transaction(BaseModel):
    """Transaction model"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    connection_id: Optional[uuid.UUID] = None
    transaction_type: TransactionType
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Decimal
    fees: Decimal = Decimal("0")
    transaction_date: datetime
    description: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class Portfolio(BaseModel):
    """Portfolio model representing aggregate user holdings"""
    user_id: uuid.UUID
    total_value: Decimal
    total_cash: Decimal = Decimal("0")
    total_equity: Decimal
    day_pl: Decimal = Decimal("0")
    day_pl_percent: Decimal = Decimal("0")
    total_pl: Decimal
    total_pl_percent: Decimal
    realized_pl: Decimal = Decimal("0")
    positions: List[Position] = []
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class BrokerageConnection(BaseModel):
    """Brokerage connection model"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    provider: BrokerageProvider
    account_id: str
    account_name: Optional[str] = None
    
    # Encrypted tokens (stored encrypted in DB)
    _access_token_encrypted: str
    _refresh_token_encrypted: Optional[str] = None
    
    token_expires_at: Optional[datetime] = None
    is_active: bool = True
    last_synced_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Properties for token access (will use encryption service)
    @property
    def access_token(self) -> str:
        """Get decrypted access token"""
        # Will be implemented with encryption service
        return self._access_token_encrypted
    
    @access_token.setter
    def access_token(self, value: str):
        """Set access token (will be encrypted)"""
        # Will be implemented with encryption service
        self._access_token_encrypted = value
    
    @property
    def refresh_token(self) -> Optional[str]:
        """Get decrypted refresh token"""
        if not self._refresh_token_encrypted:
            return None
        # Will be implemented with encryption service
        return self._refresh_token_encrypted
    
    @refresh_token.setter
    def refresh_token(self, value: Optional[str]):
        """Set refresh token (will be encrypted)"""
        # Will be implemented with encryption service
        self._refresh_token_encrypted = value
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AccountBalance(BaseModel):
    """Account balance model"""
    connection_id: uuid.UUID
    cash: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")
    margin_balance: Decimal = Decimal("0")
    currency: str = "USD"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class PortfolioSnapshot(BaseModel):
    """Portfolio snapshot for day P&L calculation"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    snapshot_type: str  # 'start_of_day', 'end_of_day'
    total_value: Decimal
    total_cash: Decimal
    positions_snapshot: Dict[str, Any]
    captured_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }
