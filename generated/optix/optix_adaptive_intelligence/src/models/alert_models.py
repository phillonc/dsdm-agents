"""
Alert and notification models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AlertType(str, Enum):
    """Types of alerts"""
    PATTERN_DETECTED = "pattern_detected"
    PRICE_TARGET = "price_target"
    SUPPORT_RESISTANCE = "support_resistance"
    UNUSUAL_OPTIONS = "unusual_options"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_CHANGE = "volatility_change"
    SENTIMENT_SHIFT = "sentiment_shift"
    PREDICTION_SIGNAL = "prediction_signal"
    RISK_WARNING = "risk_warning"
    OPPORTUNITY = "opportunity"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Delivery channels for alerts"""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push"
    WEBHOOK = "webhook"


class AlertStatus(str, Enum):
    """Alert status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    FAILED = "failed"


class Alert(BaseModel):
    """Real-time alert"""
    alert_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus = Field(default=AlertStatus.PENDING)
    symbol: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    channels: List[AlertChannel] = Field(default_factory=list)
    actionable: bool = Field(default=False)
    action_url: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    expiry: Optional[datetime] = Field(None, description="Alert expiration time")
    triggered_by: Optional[str] = Field(None, description="Pattern/signal ID that triggered alert")
    related_entities: Dict[str, str] = Field(
        default_factory=dict,
        description="Related patterns, signals, insights"
    )
    priority_score: float = Field(..., ge=0.0, le=1.0)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    retry_count: int = Field(default=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "alert_123",
                "user_id": "user_456",
                "alert_type": "pattern_detected",
                "severity": "high",
                "symbol": "AAPL",
                "title": "Head & Shoulders Pattern Detected",
                "message": "A bearish head & shoulders pattern has been detected on AAPL with 87% confidence. Consider taking profits or tightening stops.",
                "channels": ["in_app", "push"],
                "actionable": True,
                "priority_score": 0.87
            }
        }


class AlertCondition(BaseModel):
    """Condition for triggering an alert"""
    condition_id: str
    condition_type: str = Field(..., description="Type of condition")
    operator: str = Field(..., description="Comparison operator: >, <, ==, >=, <=")
    threshold: float = Field(..., description="Threshold value")
    current_value: Optional[float] = None
    met: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertConfig(BaseModel):
    """User alert configuration"""
    config_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = Field(default=True)
    alert_type: AlertType
    symbol: Optional[str] = Field(None, description="Specific symbol or None for all")
    conditions: List[AlertCondition] = Field(default_factory=list)
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    min_severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM)
    preferred_channels: List[AlertChannel] = Field(default_factory=list)
    quiet_hours: Optional[Dict[str, Any]] = Field(
        None,
        description="Time periods to suppress alerts"
    )
    max_alerts_per_day: Optional[int] = None
    deduplication_window: int = Field(
        default=3600,
        description="Seconds to deduplicate similar alerts"
    )
    custom_filters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "config_id": "cfg_789",
                "user_id": "user_456",
                "enabled": True,
                "alert_type": "pattern_detected",
                "symbol": "AAPL",
                "min_confidence": 0.8,
                "min_severity": "medium",
                "preferred_channels": ["in_app", "push"],
                "max_alerts_per_day": 20
            }
        }


class AlertDeliveryLog(BaseModel):
    """Log of alert delivery attempts"""
    log_id: str
    alert_id: str
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
    channel: AlertChannel
    status: str = Field(..., description="success, failed, pending")
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    delivery_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertStatistics(BaseModel):
    """Alert statistics for monitoring"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_alerts: int
    alerts_by_type: Dict[AlertType, int] = Field(default_factory=dict)
    alerts_by_severity: Dict[AlertSeverity, int] = Field(default_factory=dict)
    delivery_success_rate: float = Field(..., ge=0.0, le=1.0)
    average_delivery_time_ms: float
    read_rate: float = Field(..., ge=0.0, le=1.0)
    action_taken_rate: float = Field(..., ge=0.0, le=1.0)
    dismissed_rate: float = Field(..., ge=0.0, le=1.0)
    false_positive_rate: Optional[float] = None
    user_satisfaction_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
