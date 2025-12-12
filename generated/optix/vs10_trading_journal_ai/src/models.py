"""
Data models for Trading Journal AI system.

This module defines all database models and schemas for the trading journal,
including trades, journal entries, tags, and analytics records.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, 
    ForeignKey, Table, Boolean, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# Association tables for many-to-many relationships
trade_tags = Table(
    'trade_tags',
    Base.metadata,
    Column('trade_id', Integer, ForeignKey('trades.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class TradeDirection(str, Enum):
    """Trade direction enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, Enum):
    """Trade status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


class SetupType(str, Enum):
    """Trading setup type enumeration."""
    BREAKOUT = "BREAKOUT"
    PULLBACK = "PULLBACK"
    REVERSAL = "REVERSAL"
    MOMENTUM = "MOMENTUM"
    RANGE_BOUND = "RANGE_BOUND"
    GAP_TRADE = "GAP_TRADE"
    NEWS_TRADE = "NEWS_TRADE"
    SCALP = "SCALP"
    SWING = "SWING"
    OTHER = "OTHER"


class MarketCondition(str, Enum):
    """Market condition enumeration."""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    LOW_VOLUME = "LOW_VOLUME"
    HIGH_VOLUME = "HIGH_VOLUME"
    PRE_MARKET = "PRE_MARKET"
    POST_MARKET = "POST_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"


class Sentiment(str, Enum):
    """Trader sentiment enumeration."""
    CONFIDENT = "CONFIDENT"
    UNCERTAIN = "UNCERTAIN"
    FOMO = "FOMO"
    REVENGE = "REVENGE"
    DISCIPLINED = "DISCIPLINED"
    IMPULSIVE = "IMPULSIVE"
    CALM = "CALM"
    ANXIOUS = "ANXIOUS"


class Trade(Base):
    """Trade database model."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    broker_id = Column(String(50), index=True)
    broker_trade_id = Column(String(100), unique=True, index=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    status = Column(SQLEnum(TradeStatus), nullable=False, default=TradeStatus.OPEN)
    
    # Entry details
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_commission = Column(Float, default=0.0)
    
    # Exit details
    exit_date = Column(DateTime, index=True)
    exit_price = Column(Float)
    exit_commission = Column(Float, default=0.0)
    
    # P&L
    gross_pnl = Column(Float)
    net_pnl = Column(Float)
    pnl_percent = Column(Float)
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    
    # AI-detected patterns
    setup_type = Column(SQLEnum(SetupType))
    market_condition = Column(SQLEnum(MarketCondition))
    sentiment = Column(SQLEnum(Sentiment))
    
    # AI flags
    is_fomo = Column(Boolean, default=False)
    is_revenge = Column(Boolean, default=False)
    is_overtraded = Column(Boolean, default=False)
    
    # Additional data
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tags = relationship('Tag', secondary=trade_tags, back_populates='trades')
    journal_entries = relationship('JournalEntry', back_populates='trade', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.direction} {self.status}>"


class Tag(Base):
    """Tag database model for categorizing trades."""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    category = Column(String(50))  # setup, market, sentiment, custom
    color = Column(String(7))  # Hex color code
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trades = relationship('Trade', secondary=trade_tags, back_populates='tags')
    
    def __repr__(self):
        return f"<Tag {self.name}>"


class JournalEntry(Base):
    """Journal entry database model."""
    __tablename__ = 'journal_entries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    trade_id = Column(Integer, ForeignKey('trades.id'))
    
    # Entry content
    title = Column(String(200))
    content = Column(Text)
    notes = Column(Text)
    
    # Mood tracking
    mood_rating = Column(Integer)  # 1-10 scale
    confidence_level = Column(Integer)  # 1-10 scale
    discipline_rating = Column(Integer)  # 1-10 scale
    
    # Attachments
    screenshots = Column(JSON)  # List of screenshot URLs
    chart_images = Column(JSON)  # List of chart image URLs
    
    # AI analysis
    ai_insights = Column(JSON)
    ai_suggestions = Column(Text)
    
    # Timestamps
    entry_date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trade = relationship('Trade', back_populates='journal_entries')
    
    def __repr__(self):
        return f"<JournalEntry {self.title} {self.entry_date}>"


class WeeklyReview(Base):
    """Weekly AI review database model."""
    __tablename__ = 'weekly_reviews'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Review period
    week_start = Column(DateTime, nullable=False, index=True)
    week_end = Column(DateTime, nullable=False)
    
    # Performance metrics
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    
    gross_pnl = Column(Float)
    net_pnl = Column(Float)
    average_win = Column(Float)
    average_loss = Column(Float)
    profit_factor = Column(Float)
    
    largest_win = Column(Float)
    largest_loss = Column(Float)
    
    # AI analysis
    top_performing_setups = Column(JSON)
    worst_performing_setups = Column(JSON)
    best_trading_hours = Column(JSON)
    market_condition_performance = Column(JSON)
    
    # AI insights and tips
    key_insights = Column(JSON)
    improvement_tips = Column(JSON)
    pattern_discoveries = Column(JSON)
    behavioral_analysis = Column(JSON)
    
    # Summary
    summary_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WeeklyReview {self.week_start} to {self.week_end}>"


class PerformanceMetric(Base):
    """Performance metrics database model."""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Metric details
    metric_type = Column(String(50), nullable=False)  # by_symbol, by_setup, by_hour, etc.
    metric_key = Column(String(100), nullable=False)  # The specific symbol, setup, hour, etc.
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Performance data
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    
    total_pnl = Column(Float)
    average_pnl = Column(Float)
    max_win = Column(Float)
    max_loss = Column(Float)
    
    profit_factor = Column(Float)
    expectancy = Column(Float)
    
    # Additional metrics
    metrics_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PerformanceMetric {self.metric_type}:{self.metric_key}>"


# Pydantic schemas for API
class TradeCreate(BaseModel):
    """Schema for creating a trade."""
    user_id: str
    broker_id: Optional[str] = None
    broker_trade_id: Optional[str] = None
    symbol: str
    direction: TradeDirection
    entry_date: datetime
    entry_price: float
    quantity: float
    entry_commission: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: Optional[SetupType] = None
    market_condition: Optional[MarketCondition] = None
    sentiment: Optional[Sentiment] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('entry_price', 'quantity')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v


class TradeUpdate(BaseModel):
    """Schema for updating a trade."""
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_commission: Optional[float] = 0.0
    status: Optional[TradeStatus] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: Optional[SetupType] = None
    market_condition: Optional[MarketCondition] = None
    sentiment: Optional[Sentiment] = None
    metadata: Optional[Dict[str, Any]] = None


class TradeResponse(BaseModel):
    """Schema for trade response."""
    id: int
    user_id: str
    broker_id: Optional[str]
    broker_trade_id: Optional[str]
    symbol: str
    direction: TradeDirection
    status: TradeStatus
    entry_date: datetime
    entry_price: float
    quantity: float
    entry_commission: float
    exit_date: Optional[datetime]
    exit_price: Optional[float]
    exit_commission: Optional[float]
    gross_pnl: Optional[float]
    net_pnl: Optional[float]
    pnl_percent: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: Optional[float]
    setup_type: Optional[SetupType]
    market_condition: Optional[MarketCondition]
    sentiment: Optional[Sentiment]
    is_fomo: bool
    is_revenge: bool
    is_overtraded: bool
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class JournalEntryCreate(BaseModel):
    """Schema for creating a journal entry."""
    user_id: str
    trade_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    notes: Optional[str] = None
    mood_rating: Optional[int] = Field(None, ge=1, le=10)
    confidence_level: Optional[int] = Field(None, ge=1, le=10)
    discipline_rating: Optional[int] = Field(None, ge=1, le=10)
    screenshots: Optional[List[str]] = None
    chart_images: Optional[List[str]] = None
    entry_date: datetime = Field(default_factory=datetime.utcnow)


class JournalEntryResponse(BaseModel):
    """Schema for journal entry response."""
    id: int
    user_id: str
    trade_id: Optional[int]
    title: Optional[str]
    content: Optional[str]
    notes: Optional[str]
    mood_rating: Optional[int]
    confidence_level: Optional[int]
    discipline_rating: Optional[int]
    screenshots: Optional[List[str]]
    chart_images: Optional[List[str]]
    ai_insights: Optional[Dict[str, Any]]
    ai_suggestions: Optional[str]
    entry_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    """Schema for creating a tag."""
    user_id: str
    name: str
    category: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


class TagResponse(BaseModel):
    """Schema for tag response."""
    id: int
    user_id: str
    name: str
    category: Optional[str]
    color: Optional[str]
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WeeklyReviewResponse(BaseModel):
    """Schema for weekly review response."""
    id: int
    user_id: str
    week_start: datetime
    week_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_pnl: float
    net_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    largest_win: float
    largest_loss: float
    top_performing_setups: Dict[str, Any]
    worst_performing_setups: Dict[str, Any]
    best_trading_hours: Dict[str, Any]
    market_condition_performance: Dict[str, Any]
    key_insights: List[str]
    improvement_tips: List[str]
    pattern_discoveries: List[str]
    behavioral_analysis: Dict[str, Any]
    summary_text: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PerformanceAnalyticsRequest(BaseModel):
    """Schema for performance analytics request."""
    user_id: str
    start_date: datetime
    end_date: datetime
    group_by: Optional[str] = None  # symbol, setup, hour, day_of_week
    filters: Optional[Dict[str, Any]] = None


class PerformanceAnalyticsResponse(BaseModel):
    """Schema for performance analytics response."""
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_pnl: float
    max_win: float
    max_loss: float
    profit_factor: float
    expectancy: float
    breakdown: Dict[str, Any]
    
    class Config:
        from_attributes = True
