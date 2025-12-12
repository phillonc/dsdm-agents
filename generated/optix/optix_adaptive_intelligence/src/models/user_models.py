"""
User profile and personalization models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TradingStyle(str, Enum):
    """User trading style classification"""
    DAY_TRADER = "day_trader"
    SWING_TRADER = "swing_trader"
    POSITION_TRADER = "position_trader"
    SCALPER = "scalper"
    INVESTOR = "investor"


class RiskTolerance(str, Enum):
    """User risk tolerance level"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


class StrategyPreference(str, Enum):
    """Preferred trading strategies"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    VOLATILITY = "volatility"
    OPTIONS_SELLING = "options_selling"
    OPTIONS_BUYING = "options_buying"
    SPREADS = "spreads"


class UserProfile(BaseModel):
    """User trading profile and preferences"""
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    trading_style: TradingStyle
    risk_tolerance: RiskTolerance
    preferred_strategies: List[StrategyPreference] = Field(default_factory=list)
    preferred_timeframes: List[str] = Field(default_factory=list)
    preferred_symbols: List[str] = Field(default_factory=list)
    sectors_of_interest: List[str] = Field(default_factory=list)
    account_size: Optional[float] = None
    max_position_size: Optional[float] = None
    max_risk_per_trade: Optional[float] = None
    preferred_indicators: List[str] = Field(default_factory=list)
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    trading_hours: Dict[str, Any] = Field(default_factory=dict)
    experience_level: str = Field(default="intermediate")
    learning_preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TradingPattern(BaseModel):
    """Learned trading pattern from user behavior"""
    pattern_id: str
    user_id: str
    identified_at: datetime = Field(default_factory=datetime.utcnow)
    pattern_type: str = Field(..., description="Type of behavioral pattern")
    frequency: int = Field(..., description="How often pattern occurs")
    success_rate: float = Field(..., ge=0.0, le=1.0)
    average_return: float
    average_holding_period: float = Field(..., description="In hours")
    common_entry_conditions: List[str] = Field(default_factory=list)
    common_exit_conditions: List[str] = Field(default_factory=list)
    preferred_time_of_day: Optional[str] = None
    typical_position_size: Optional[float] = None
    risk_reward_preference: Optional[float] = None
    associated_symbols: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    sample_size: int = Field(..., description="Number of trades in pattern")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InsightType(str, Enum):
    """Types of personalized insights"""
    OPPORTUNITY = "opportunity"
    WARNING = "warning"
    EDUCATION = "education"
    PERFORMANCE = "performance"
    RECOMMENDATION = "recommendation"
    MARKET_UPDATE = "market_update"


class InsightPriority(str, Enum):
    """Insight priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class PersonalizedInsight(BaseModel):
    """Personalized insight for user"""
    insight_id: str
    user_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    insight_type: InsightType
    priority: InsightPriority
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    symbol: Optional[str] = None
    actionable: bool = Field(default=False)
    action_items: List[str] = Field(default_factory=list)
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance to user profile"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    expiry: Optional[datetime] = Field(None, description="When insight becomes stale")
    related_patterns: List[str] = Field(default_factory=list)
    related_signals: List[str] = Field(default_factory=list)
    performance_impact: Optional[Dict[str, float]] = None
    learning_content: Optional[Dict[str, Any]] = None
    read: bool = Field(default=False)
    read_at: Optional[datetime] = None
    dismissed: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "insight_id": "ins_789",
                "user_id": "user_123",
                "insight_type": "opportunity",
                "priority": "high",
                "title": "Strong Bullish Setup on AAPL",
                "description": "Based on your swing trading profile and preference for momentum strategies, AAPL shows strong bullish signals...",
                "symbol": "AAPL",
                "actionable": True,
                "action_items": [
                    "Consider entry near 178.50",
                    "Set stop loss at 175.00",
                    "Target price: 185.00"
                ],
                "relevance_score": 0.92,
                "confidence": 0.85
            }
        }


class UserStatistics(BaseModel):
    """User trading statistics"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float = Field(..., ge=0.0, le=1.0)
    average_return: float
    total_return: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float
    average_holding_period: float
    most_traded_symbols: List[Dict[str, Any]] = Field(default_factory=list)
    best_performing_strategy: Optional[str] = None
    worst_performing_strategy: Optional[str] = None
    risk_metrics: Dict[str, float] = Field(default_factory=dict)
    behavioral_insights: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
