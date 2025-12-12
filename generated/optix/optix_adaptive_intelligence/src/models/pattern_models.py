"""
Pattern recognition data models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class PatternType(str, Enum):
    """Types of chart patterns"""
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    CUP_AND_HANDLE = "cup_and_handle"
    ROUNDING_BOTTOM = "rounding_bottom"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"


class TrendDirection(str, Enum):
    """Trend direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ChartPattern(BaseModel):
    """Chart pattern detection result"""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    symbol: str = Field(..., description="Trading symbol")
    pattern_type: PatternType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    start_time: datetime = Field(..., description="Pattern start timestamp")
    end_time: Optional[datetime] = Field(None, description="Pattern end timestamp")
    trend_direction: TrendDirection
    price_target: Optional[float] = Field(None, description="Projected price target")
    stop_loss: Optional[float] = Field(None, description="Suggested stop loss")
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    volume_confirmation: bool = Field(default=False, description="Volume confirms pattern")
    key_levels: List[Dict[str, float]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "pattern_id": "pat_123456",
                "symbol": "AAPL",
                "pattern_type": "head_shoulders",
                "confidence": 0.87,
                "trend_direction": "bearish",
                "price_target": 175.50,
                "stop_loss": 182.00,
                "support_level": 175.00,
                "resistance_level": 180.00,
                "volume_confirmation": True
            }
        }


class OptionsActivityType(str, Enum):
    """Types of unusual options activity"""
    UNUSUAL_VOLUME = "unusual_volume"
    LARGE_BLOCK_TRADE = "large_block_trade"
    SWEEP = "sweep"
    GOLDEN_SWEEP = "golden_sweep"
    UNUSUAL_OI_CHANGE = "unusual_oi_change"
    HIGH_IV_RANK = "high_iv_rank"
    SKEW_ANOMALY = "skew_anomaly"


class OptionsActivity(BaseModel):
    """Unusual options activity detection"""
    activity_id: str = Field(..., description="Unique activity identifier")
    symbol: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    activity_type: OptionsActivityType
    strike: float
    expiration: datetime
    option_type: str = Field(..., pattern="^(call|put)$")
    volume: int
    open_interest: int
    volume_oi_ratio: float
    avg_volume: float
    volume_multiple: float = Field(..., description="Volume / Average Volume")
    premium: float
    implied_volatility: float
    delta: Optional[float] = None
    sentiment: TrendDirection
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('volume_multiple')
    def validate_volume_multiple(cls, v):
        if v < 0:
            raise ValueError("Volume multiple must be positive")
        return v


class VolumeAnomalyType(str, Enum):
    """Types of volume anomalies"""
    SPIKE = "spike"
    DIVERGENCE = "divergence"
    CLIMAX = "climax"
    DRY_UP = "dry_up"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


class VolumeAnomaly(BaseModel):
    """Volume anomaly detection"""
    anomaly_id: str
    symbol: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    anomaly_type: VolumeAnomalyType
    current_volume: int
    average_volume: float
    volume_ratio: float = Field(..., description="Current / Average")
    price_change: float
    price_volume_correlation: float = Field(..., ge=-1.0, le=1.0)
    significance: float = Field(..., ge=0.0, le=1.0)
    timeframe: str = Field(..., description="e.g., '1D', '1H', '5m'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupportResistanceLevel(BaseModel):
    """Support and resistance level identification"""
    level_id: str
    symbol: str
    price_level: float
    level_type: str = Field(..., pattern="^(support|resistance)$")
    strength: float = Field(..., ge=0.0, le=1.0, description="Level strength")
    touches: int = Field(..., ge=1, description="Number of times price touched level")
    first_touch: datetime
    last_touch: datetime
    time_relevance: float = Field(..., ge=0.0, le=1.0, description="How recent/relevant")
    volume_at_level: float
    broken: bool = Field(default=False)
    break_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "level_id": "level_789",
                "symbol": "AAPL",
                "price_level": 175.50,
                "level_type": "support",
                "strength": 0.85,
                "touches": 5,
                "time_relevance": 0.90,
                "broken": False
            }
        }
