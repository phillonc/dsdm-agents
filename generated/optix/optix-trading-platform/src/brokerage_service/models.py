"""
Brokerage Service Models
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum
import uuid


class BrokerageProvider(str, Enum):
    """Supported brokerage providers"""
    SCHWAB = "schwab"
    TD_AMERITRADE = "td_ameritrade"
    FIDELITY = "fidelity"
    ROBINHOOD = "robinhood"
    INTERACTIVE_BROKERS = "ibkr"
    WEBULL = "webull"


class AccountType(str, Enum):
    """Brokerage account types"""
    INDIVIDUAL = "individual"
    JOINT = "joint"
    IRA = "ira"
    ROTH_IRA = "roth_ira"
    MARGIN = "margin"


class PositionType(str, Enum):
    """Position types"""
    STOCK = "stock"
    OPTION = "option"
    ETF = "etf"
    CRYPTO = "crypto"


class ConnectionStatus(str, Enum):
    """Connection status"""
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


class BrokerageConnection(BaseModel):
    """Brokerage account connection"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    provider: BrokerageProvider
    
    # OAuth tokens (encrypted in production)
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    # Account details
    account_id: str
    account_name: Optional[str] = None
    account_type: AccountType = AccountType.INDIVIDUAL
    
    # Status
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    
    # Timestamps
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class Position(BaseModel):
    """Portfolio position"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    connection_id: uuid.UUID
    user_id: uuid.UUID
    
    # Symbol and type
    symbol: str
    position_type: PositionType
    
    # Quantity and cost basis
    quantity: Decimal
    average_price: Decimal
    cost_basis: Decimal
    
    # Current market value
    current_price: Decimal
    market_value: Decimal
    
    # P&L
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal
    realized_pl: Decimal = Decimal("0")
    
    # Options-specific fields
    option_symbol: Optional[str] = None
    strike: Optional[Decimal] = None
    expiration_date: Optional[date] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    
    # Greeks (for options)
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None
    
    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class Transaction(BaseModel):
    """Trade transaction history"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    connection_id: uuid.UUID
    user_id: uuid.UUID
    
    # Transaction details
    symbol: str
    transaction_type: str  # buy, sell, option_assignment, dividend, etc.
    quantity: Decimal
    price: Decimal
    amount: Decimal
    fees: Decimal = Decimal("0")
    
    # Options details
    option_symbol: Optional[str] = None
    strike: Optional[Decimal] = None
    expiration_date: Optional[date] = None
    option_type: Optional[str] = None
    
    # Timestamps
    transaction_date: datetime
    settled_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class Portfolio(BaseModel):
    """Unified portfolio view"""
    user_id: uuid.UUID
    
    # Account summaries
    total_value: Decimal
    total_cash: Decimal
    total_stocks_value: Decimal
    total_options_value: Decimal
    
    # Performance
    total_unrealized_pl: Decimal
    total_unrealized_pl_percent: Decimal
    total_realized_pl: Decimal
    day_pl: Decimal
    day_pl_percent: Decimal
    
    # Portfolio Greeks (sum across all options)
    total_delta: Decimal = Decimal("0")
    total_gamma: Decimal = Decimal("0")
    total_theta: Decimal = Decimal("0")
    total_vega: Decimal = Decimal("0")
    
    # Positions by connection
    positions: List[Position] = []
    connections: List[BrokerageConnection] = []
    
    # Analytics
    diversification_score: Optional[Decimal] = None
    risk_level: str = "moderate"  # low, moderate, high
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class ConnectBrokerageRequest(BaseModel):
    """Request to connect a brokerage"""
    provider: BrokerageProvider
    account_id: Optional[str] = None


class OAuthCallback(BaseModel):
    """OAuth callback data"""
    code: str
    state: str
