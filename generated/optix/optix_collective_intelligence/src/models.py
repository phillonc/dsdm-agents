"""
Data models for the Collective Intelligence Network.

This module defines all core data structures for social trading functionality.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from uuid import uuid4


class TradeType(Enum):
    """Types of trades."""
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"


class TradeStatus(Enum):
    """Status of a trade."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class IdeaStatus(Enum):
    """Status of a trade idea."""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class SentimentType(Enum):
    """Sentiment types."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class FollowType(Enum):
    """Types of following relationships."""
    FOLLOW = "follow"
    COPY = "copy"


@dataclass
class Trader:
    """Represents a trader in the network."""
    trader_id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    display_name: str = ""
    bio: str = ""
    avatar_url: str = ""
    joined_date: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False
    total_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    followers_count: int = 0
    following_count: int = 0
    reputation_score: float = 0.0
    risk_score: float = 0.0
    average_trade_duration: float = 0.0
    favorite_assets: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trader_id': self.trader_id,
            'username': self.username,
            'display_name': self.display_name,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'joined_date': self.joined_date.isoformat(),
            'verified': self.verified,
            'total_trades': self.total_trades,
            'win_rate': self.win_rate,
            'total_return': self.total_return,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'reputation_score': self.reputation_score,
            'risk_score': self.risk_score,
            'average_trade_duration': self.average_trade_duration,
            'favorite_assets': self.favorite_assets,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class TradeIdea:
    """Represents a trade idea shared in the community."""
    idea_id: str = field(default_factory=lambda: str(uuid4()))
    trader_id: str = ""
    title: str = ""
    description: str = ""
    asset: str = ""
    trade_type: TradeType = TradeType.BUY
    entry_price: float = 0.0
    target_price: float = 0.0
    stop_loss: float = 0.0
    timeframe: str = ""
    confidence: float = 0.0
    status: IdeaStatus = IdeaStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    tags: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    sentiment: SentimentType = SentimentType.NEUTRAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'idea_id': self.idea_id,
            'trader_id': self.trader_id,
            'title': self.title,
            'description': self.description,
            'asset': self.asset,
            'trade_type': self.trade_type.value,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'timeframe': self.timeframe,
            'confidence': self.confidence,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'shares_count': self.shares_count,
            'views_count': self.views_count,
            'tags': self.tags,
            'attachments': self.attachments,
            'sentiment': self.sentiment.value,
            'metadata': self.metadata
        }


@dataclass
class Trade:
    """Represents an actual trade execution."""
    trade_id: str = field(default_factory=lambda: str(uuid4()))
    trader_id: str = ""
    idea_id: Optional[str] = None
    asset: str = ""
    trade_type: TradeType = TradeType.BUY
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    profit_loss: float = 0.0
    profit_loss_percentage: float = 0.0
    fees: float = 0.0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trade_id': self.trade_id,
            'trader_id': self.trader_id,
            'idea_id': self.idea_id,
            'asset': self.asset,
            'trade_type': self.trade_type.value,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'status': self.status.value,
            'opened_at': self.opened_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'profit_loss': self.profit_loss,
            'profit_loss_percentage': self.profit_loss_percentage,
            'fees': self.fees,
            'notes': self.notes,
            'metadata': self.metadata
        }


@dataclass
class Comment:
    """Represents a comment on a trade idea."""
    comment_id: str = field(default_factory=lambda: str(uuid4()))
    idea_id: str = ""
    trader_id: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    likes_count: int = 0
    parent_comment_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'comment_id': self.comment_id,
            'idea_id': self.idea_id,
            'trader_id': self.trader_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'likes_count': self.likes_count,
            'parent_comment_id': self.parent_comment_id,
            'metadata': self.metadata
        }


@dataclass
class FollowRelationship:
    """Represents a follow/copy relationship between traders."""
    relationship_id: str = field(default_factory=lambda: str(uuid4()))
    follower_id: str = ""
    following_id: str = ""
    follow_type: FollowType = FollowType.FOLLOW
    created_at: datetime = field(default_factory=datetime.utcnow)
    copy_settings: Optional[Dict[str, Any]] = None
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'relationship_id': self.relationship_id,
            'follower_id': self.follower_id,
            'following_id': self.following_id,
            'follow_type': self.follow_type.value,
            'created_at': self.created_at.isoformat(),
            'copy_settings': self.copy_settings,
            'active': self.active,
            'metadata': self.metadata
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for a trader."""
    trader_id: str = ""
    period: str = "all_time"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    average_return: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    average_trade_duration: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    consistency_score: float = 0.0
    risk_adjusted_return: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trader_id': self.trader_id,
            'period': self.period,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_return': self.total_return,
            'average_return': self.average_return,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'average_trade_duration': self.average_trade_duration,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'profit_factor': self.profit_factor,
            'consistency_score': self.consistency_score,
            'risk_adjusted_return': self.risk_adjusted_return,
            'calculated_at': self.calculated_at.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class CommunitySentiment:
    """Aggregated sentiment for an asset."""
    asset: str = ""
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    overall_sentiment: SentimentType = SentimentType.NEUTRAL
    sentiment_score: float = 0.0
    volume_24h: int = 0
    trending_score: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'asset': self.asset,
            'bullish_count': self.bullish_count,
            'bearish_count': self.bearish_count,
            'neutral_count': self.neutral_count,
            'overall_sentiment': self.overall_sentiment.value,
            'sentiment_score': self.sentiment_score,
            'volume_24h': self.volume_24h,
            'trending_score': self.trending_score,
            'calculated_at': self.calculated_at.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class LeaderboardEntry:
    """Entry in a leaderboard ranking."""
    rank: int = 0
    trader_id: str = ""
    username: str = ""
    display_name: str = ""
    avatar_url: str = ""
    score: float = 0.0
    metric_value: float = 0.0
    change_from_previous: int = 0
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'rank': self.rank,
            'trader_id': self.trader_id,
            'username': self.username,
            'display_name': self.display_name,
            'avatar_url': self.avatar_url,
            'score': self.score,
            'metric_value': self.metric_value,
            'change_from_previous': self.change_from_previous,
            'verified': self.verified,
            'metadata': self.metadata
        }
