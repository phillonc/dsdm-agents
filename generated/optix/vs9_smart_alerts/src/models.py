"""
VS-9 Smart Alerts Ecosystem - Data Models
OPTIX Trading Platform

Comprehensive data models for the smart alerts system including alert definitions,
conditions, user preferences, delivery settings, and analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AlertStatus(Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    SNOOZED = "snoozed"
    EXPIRED = "expired"
    DELETED = "deleted"


class ConditionType(Enum):
    """Types of alert conditions"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE = "price_change"
    IV_ABOVE = "iv_above"
    IV_BELOW = "iv_below"
    IV_CHANGE = "iv_change"
    VOLUME_ABOVE = "volume_above"
    FLOW_BULLISH = "flow_bullish"
    FLOW_BEARISH = "flow_bearish"
    UNUSUAL_ACTIVITY = "unusual_activity"
    SPREAD_WIDTH = "spread_width"
    DELTA_CHANGE = "delta_change"
    GAMMA_EXPOSURE = "gamma_exposure"
    POSITION_PNL = "position_pnl"
    EXPIRATION_APPROACHING = "expiration_approaching"


class DeliveryChannel(Enum):
    """Alert delivery channels"""
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class MarketSession(Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


@dataclass
class AlertCondition:
    """Individual condition for an alert"""
    condition_id: str = field(default_factory=lambda: str(uuid4()))
    condition_type: ConditionType = ConditionType.PRICE_ABOVE
    symbol: str = ""
    threshold: float = 0.0
    comparison_value: Optional[float] = None
    timeframe: Optional[str] = None  # e.g., "5m", "1h", "1d"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.condition_type, str):
            self.condition_type = ConditionType(self.condition_type)


@dataclass
class AlertRule:
    """Complete alert rule with multiple conditions"""
    rule_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    name: str = ""
    description: str = ""
    conditions: List[AlertCondition] = field(default_factory=list)
    logic: str = "AND"  # AND or OR for combining conditions
    priority: AlertPriority = AlertPriority.MEDIUM
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Timing and expiration
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    cooldown_minutes: int = 5  # Minimum time between triggers
    last_triggered_at: Optional[datetime] = None
    
    # Market hours awareness
    market_hours_only: bool = True
    allowed_sessions: List[MarketSession] = field(
        default_factory=lambda: [MarketSession.REGULAR]
    )
    
    # Position awareness
    position_aware: bool = False
    relevant_positions: List[str] = field(default_factory=list)  # Position IDs
    
    # Template and categorization
    template_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: str = "custom"
    
    # Analytics
    trigger_count: int = 0
    action_count: int = 0  # Times user acted on this alert
    snooze_count: int = 0
    relevance_score: float = 0.5  # Learned from user behavior
    
    # Consolidation
    consolidation_group: Optional[str] = None
    allow_consolidation: bool = True
    
    def __post_init__(self):
        if isinstance(self.priority, str):
            self.priority = AlertPriority(self.priority)
        if isinstance(self.status, str):
            self.status = AlertStatus(self.status)
        if isinstance(self.allowed_sessions[0], str):
            self.allowed_sessions = [MarketSession(s) for s in self.allowed_sessions]


@dataclass
class TriggeredAlert:
    """An alert that has been triggered"""
    alert_id: str = field(default_factory=lambda: str(uuid4()))
    rule_id: str = ""
    user_id: str = ""
    
    # Trigger details
    triggered_at: datetime = field(default_factory=datetime.utcnow)
    trigger_values: Dict[str, Any] = field(default_factory=dict)
    matched_conditions: List[str] = field(default_factory=list)
    
    # Alert content
    title: str = ""
    message: str = ""
    priority: AlertPriority = AlertPriority.MEDIUM
    
    # Status and tracking
    status: AlertStatus = AlertStatus.TRIGGERED
    acknowledged_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    
    # User action tracking
    user_acted: bool = False
    action_type: Optional[str] = None  # e.g., "opened_position", "closed_position"
    action_timestamp: Optional[datetime] = None
    
    # Consolidation
    consolidated_alert_id: Optional[str] = None
    is_consolidated: bool = False
    related_alert_ids: List[str] = field(default_factory=list)
    
    # Delivery tracking
    delivered_channels: List[DeliveryChannel] = field(default_factory=list)
    delivery_attempts: Dict[str, int] = field(default_factory=dict)
    
    # Context
    market_session: MarketSession = MarketSession.REGULAR
    related_positions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.priority, str):
            self.priority = AlertPriority(self.priority)
        if isinstance(self.status, str):
            self.status = AlertStatus(self.status)
        if isinstance(self.market_session, str):
            self.market_session = MarketSession(self.market_session)


@dataclass
class ConsolidatedAlert:
    """Multiple related alerts grouped together"""
    consolidated_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    
    # Grouped alerts
    alert_ids: List[str] = field(default_factory=list)
    alerts: List[TriggeredAlert] = field(default_factory=list)
    
    # Consolidation details
    created_at: datetime = field(default_factory=datetime.utcnow)
    consolidation_reason: str = ""
    consolidation_group: str = ""
    
    # Summary
    title: str = ""
    summary: str = ""
    priority: AlertPriority = AlertPriority.MEDIUM
    alert_count: int = 0
    
    # Status
    status: AlertStatus = AlertStatus.TRIGGERED
    acknowledged_at: Optional[datetime] = None


@dataclass
class DeliveryPreference:
    """User's alert delivery preferences"""
    user_id: str = ""
    
    # Channel settings
    enabled_channels: List[DeliveryChannel] = field(
        default_factory=lambda: [DeliveryChannel.IN_APP, DeliveryChannel.PUSH]
    )
    
    # Priority-based routing
    priority_channel_map: Dict[AlertPriority, List[DeliveryChannel]] = field(
        default_factory=lambda: {
            AlertPriority.LOW: [DeliveryChannel.IN_APP],
            AlertPriority.MEDIUM: [DeliveryChannel.IN_APP, DeliveryChannel.PUSH],
            AlertPriority.HIGH: [DeliveryChannel.IN_APP, DeliveryChannel.PUSH, DeliveryChannel.EMAIL],
            AlertPriority.URGENT: [DeliveryChannel.IN_APP, DeliveryChannel.PUSH, DeliveryChannel.EMAIL, DeliveryChannel.SMS],
        }
    )
    
    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    push_tokens: List[str] = field(default_factory=list)
    webhook_url: Optional[str] = None
    
    # Timing preferences
    quiet_hours_start: Optional[str] = None  # e.g., "22:00"
    quiet_hours_end: Optional[str] = None  # e.g., "07:00"
    quiet_hours_priority_override: AlertPriority = AlertPriority.URGENT
    
    # Consolidation preferences
    enable_consolidation: bool = True
    consolidation_window_minutes: int = 5
    
    # Rate limiting
    max_alerts_per_hour: int = 50
    max_sms_per_day: int = 10
    
    # Updated timestamp
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AlertTemplate:
    """Pre-defined alert template for common scenarios"""
    template_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    category: str = "general"
    
    # Template conditions
    condition_templates: List[Dict[str, Any]] = field(default_factory=list)
    logic: str = "AND"
    
    # Default settings
    default_priority: AlertPriority = AlertPriority.MEDIUM
    recommended_cooldown: int = 5
    
    # Usage tracking
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Tags and search
    tags: List[str] = field(default_factory=list)
    is_public: bool = True


@dataclass
class AlertAnalytics:
    """Analytics for alert performance and user behavior"""
    user_id: str = ""
    rule_id: Optional[str] = None
    
    # Time period
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    
    # Trigger metrics
    total_triggers: int = 0
    triggers_by_condition: Dict[str, int] = field(default_factory=dict)
    triggers_by_priority: Dict[str, int] = field(default_factory=dict)
    triggers_by_time: Dict[str, int] = field(default_factory=dict)
    
    # User engagement metrics
    acknowledged_count: int = 0
    snoozed_count: int = 0
    dismissed_count: int = 0
    acted_upon_count: int = 0
    
    # Timing metrics
    avg_acknowledgment_time_seconds: float = 0.0
    avg_time_to_action_seconds: float = 0.0
    
    # Relevance metrics
    relevance_score: float = 0.5
    false_positive_rate: float = 0.0
    action_rate: float = 0.0  # acted_upon / total_triggers
    
    # Delivery metrics
    delivery_success_rate: Dict[str, float] = field(default_factory=dict)
    avg_delivery_time_ms: Dict[str, float] = field(default_factory=dict)
    
    # Consolidation metrics
    consolidation_rate: float = 0.0
    avg_alerts_per_consolidation: float = 0.0


@dataclass
class UserAlertProfile:
    """User's learned alert preferences and behavior"""
    user_id: str = ""
    
    # Behavior patterns
    most_acted_conditions: List[ConditionType] = field(default_factory=list)
    preferred_priorities: List[AlertPriority] = field(default_factory=list)
    active_trading_hours: List[str] = field(default_factory=list)
    
    # Learned preferences
    symbol_interests: Dict[str, float] = field(default_factory=dict)  # symbol -> interest score
    condition_relevance: Dict[str, float] = field(default_factory=dict)  # condition_type -> relevance
    
    # Engagement metrics
    avg_response_time_seconds: float = 0.0
    action_rate: float = 0.0
    snooze_rate: float = 0.0
    
    # Model features for ML
    features: Dict[str, Any] = field(default_factory=dict)
    
    # Last updated
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_learning_cycle: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    """User's trading position for position-aware alerts"""
    position_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    symbol: str = ""
    
    # Position details
    quantity: int = 0
    entry_price: float = 0.0
    current_price: float = 0.0
    position_type: str = "long"  # long, short, option
    
    # Options specific
    option_type: Optional[str] = None  # call, put
    strike: Optional[float] = None
    expiration: Optional[datetime] = None
    
    # P&L
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    # Greeks (for options)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Timestamps
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketData:
    """Current market data for alert evaluation"""
    symbol: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Price data
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: int = 0
    
    # Change metrics
    price_change: float = 0.0
    price_change_percent: float = 0.0
    volume_ratio: float = 1.0  # vs average volume
    
    # Options data
    implied_volatility: Optional[float] = None
    iv_rank: Optional[float] = None
    iv_percentile: Optional[float] = None
    
    # Flow data
    call_volume: Optional[int] = None
    put_volume: Optional[int] = None
    put_call_ratio: Optional[float] = None
    unusual_activity_score: Optional[float] = None
    
    # Greeks aggregates
    total_gamma: Optional[float] = None
    total_delta: Optional[float] = None
    
    # Market state
    session: MarketSession = MarketSession.REGULAR
    is_trading_hours: bool = True
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


def create_alert_from_template(
    template: AlertTemplate,
    user_id: str,
    symbol: str,
    overrides: Optional[Dict[str, Any]] = None
) -> AlertRule:
    """Create an AlertRule from a template"""
    overrides = overrides or {}
    
    # Create conditions from template
    conditions = []
    for cond_template in template.condition_templates:
        condition = AlertCondition(
            condition_type=ConditionType(cond_template.get("condition_type")),
            symbol=symbol,
            threshold=cond_template.get("threshold", 0.0),
            timeframe=cond_template.get("timeframe"),
            parameters=cond_template.get("parameters", {})
        )
        conditions.append(condition)
    
    # Create alert rule
    alert_rule = AlertRule(
        user_id=user_id,
        name=overrides.get("name", f"{template.name} - {symbol}"),
        description=overrides.get("description", template.description),
        conditions=conditions,
        logic=template.logic,
        priority=overrides.get("priority", template.default_priority),
        template_id=template.template_id,
        tags=template.tags.copy(),
        category=template.category,
        cooldown_minutes=overrides.get("cooldown_minutes", template.recommended_cooldown)
    )
    
    return alert_rule
