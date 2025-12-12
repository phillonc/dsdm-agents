"""
Alert Service Models
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from enum import Enum
import uuid


class AlertType(str, Enum):
    """Alert types"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    VOLUME_SPIKE = "volume_spike"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    DISABLED = "disabled"


class Alert(BaseModel):
    """Price alert"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    
    # Alert configuration
    symbol: str
    alert_type: AlertType
    threshold_value: Decimal
    
    # Optional message
    message: Optional[str] = None
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    triggered_at: Optional[datetime] = None
    triggered_price: Optional[Decimal] = None
    
    # Expiration
    expires_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class CreateAlertRequest(BaseModel):
    """Create alert request"""
    symbol: str
    alert_type: AlertType
    threshold_value: Decimal
    message: Optional[str] = None
    expires_at: Optional[datetime] = None


class AlertTriggered(BaseModel):
    """Alert triggered notification"""
    alert_id: uuid.UUID
    symbol: str
    alert_type: AlertType
    threshold_value: Decimal
    current_price: Decimal
    message: Optional[str] = None
    triggered_at: datetime
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
