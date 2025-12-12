"""
AI Analysis data models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class PredictionSignal(BaseModel):
    """Price prediction signal from ML models"""
    signal_id: str
    symbol: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    signal_type: SignalType
    signal_strength: SignalStrength
    confidence: float = Field(..., ge=0.0, le=1.0)
    current_price: float
    predicted_price: float
    price_target: Optional[float] = None
    time_horizon: str = Field(..., description="e.g., '1D', '1W', '1M'")
    prediction_range: Dict[str, float] = Field(
        ..., 
        description="min, max, std_dev of prediction"
    )
    model_name: str = Field(..., description="ML model used")
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    contributing_factors: List[str] = Field(default_factory=list)
    risk_reward_ratio: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "sig_12345",
                "symbol": "AAPL",
                "signal_type": "buy",
                "signal_strength": "strong",
                "confidence": 0.82,
                "current_price": 178.50,
                "predicted_price": 185.00,
                "time_horizon": "1W",
                "prediction_range": {
                    "min": 182.00,
                    "max": 188.00,
                    "std_dev": 2.5
                }
            }
        }


class VolatilityRegime(str, Enum):
    """Volatility regime classification"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class VolatilityForecast(BaseModel):
    """Volatility forecasting result"""
    forecast_id: str
    symbol: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    current_volatility: float = Field(..., description="Current realized volatility")
    implied_volatility: float = Field(..., description="Current IV")
    forecasted_volatility: float
    forecast_horizon: str = Field(..., description="e.g., '1D', '1W', '1M'")
    volatility_regime: VolatilityRegime
    regime_change_probability: float = Field(..., ge=0.0, le=1.0)
    confidence_interval: Dict[str, float] = Field(
        ...,
        description="lower, upper bounds"
    )
    garch_forecast: Optional[float] = None
    ewma_forecast: Optional[float] = None
    historical_percentile: float = Field(
        ..., 
        ge=0.0, 
        le=100.0,
        description="Current vol percentile vs history"
    )
    mean_reversion_signal: bool = Field(default=False)
    model_metrics: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SentimentScore(str, Enum):
    """Overall sentiment classification"""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class SentimentSource(str, Enum):
    """Sources of sentiment data"""
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    OPTIONS_FLOW = "options_flow"
    ANALYST_RATINGS = "analyst_ratings"
    INSIDER_TRADING = "insider_trading"
    MARKET_BREADTH = "market_breadth"


class SentimentAnalysis(BaseModel):
    """Market sentiment analysis"""
    analysis_id: str
    symbol: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    overall_sentiment: SentimentScore
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Normalized score")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_sentiments: Dict[SentimentSource, float] = Field(default_factory=dict)
    sentiment_shift: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Change from previous period"
    )
    sentiment_momentum: float = Field(
        ...,
        description="Rate of sentiment change"
    )
    volume_weighted_sentiment: Optional[float] = None
    key_drivers: List[str] = Field(default_factory=list)
    sentiment_breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed breakdown by category"
    )
    contrarian_indicator: bool = Field(
        default=False,
        description="Extreme sentiment suggesting reversal"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "sent_456",
                "symbol": "AAPL",
                "overall_sentiment": "bullish",
                "sentiment_score": 0.65,
                "confidence": 0.78,
                "sentiment_shift": 0.15,
                "key_drivers": [
                    "Strong earnings report",
                    "Positive analyst upgrades",
                    "Bullish options flow"
                ]
            }
        }


class MarketRegime(str, Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    BREAKOUT = "breakout"


class MarketContext(BaseModel):
    """Overall market context and regime"""
    context_id: str
    symbol: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    market_regime: MarketRegime
    regime_confidence: float = Field(..., ge=0.0, le=1.0)
    trend_strength: float = Field(..., ge=0.0, le=1.0)
    correlation_to_spy: float = Field(..., ge=-1.0, le=1.0)
    beta: float
    sector_performance: Dict[str, float] = Field(default_factory=dict)
    market_breadth: Dict[str, Any] = Field(default_factory=dict)
    risk_indicators: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
