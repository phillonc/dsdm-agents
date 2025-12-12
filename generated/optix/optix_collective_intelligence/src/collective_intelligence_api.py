"""
Main API for the Collective Intelligence Network.

This module provides a unified interface for all social trading functionality.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from .models import (
    Trader, TradeIdea, Trade, Comment, FollowRelationship,
    PerformanceMetrics, CommunitySentiment, LeaderboardEntry,
    TradeType, IdeaStatus, SentimentType, FollowType
)
from .trader_service import TraderService
from .trade_idea_service import TradeIdeaService
from .performance_service import PerformanceService
from .leaderboard_service import LeaderboardService
from .sentiment_service import SentimentService
from .copy_trading_service import CopyTradingService


class CollectiveIntelligenceAPI:
    """
    Main API for the Collective Intelligence Network.

    This class provides a unified interface for all social trading features
    including trade ideas, trader profiles, performance metrics, leaderboards,
    sentiment analysis, and copy trading.
    """

    def __init__(self):
        """Initialize the Collective Intelligence API."""
        self.trader_service = TraderService()
        self.trade_idea_service = TradeIdeaService()
        self.performance_service = PerformanceService()
        self.leaderboard_service = LeaderboardService(
            self.trader_service,
            self.performance_service
        )
        self.sentiment_service = SentimentService()
        self.copy_trading_service = CopyTradingService(self.trader_service)

    # ==================== Trader Management ====================

    def create_trader(
        self,
        username: str,
        display_name: str,
        **kwargs
    ) -> Trader:
        """
        Create a new trader profile.

        Args:
            username: Unique username
            display_name: Display name
            **kwargs: Additional trader parameters

        Returns:
            Created Trader object
        """
        return self.trader_service.create_trader(username, display_name, **kwargs)

    def get_trader(self, trader_id: str) -> Trader:
        """Get a trader by ID."""
        return self.trader_service.get_trader(trader_id)

    def get_trader_by_username(self, username: str) -> Trader:
        """Get a trader by username."""
        return self.trader_service.get_trader_by_username(username)

    def update_trader(self, trader_id: str, **updates) -> Trader:
        """Update a trader profile."""
        return self.trader_service.update_trader(trader_id, **updates)

    def search_traders(
        self,
        query: Optional[str] = None,
        min_reputation: Optional[float] = None,
        verified_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Trader]:
        """Search for traders."""
        return self.trader_service.search_traders(
            query, min_reputation, verified_only, tags, limit
        )

    # ==================== Social Connections ====================

    def follow_trader(
        self,
        follower_id: str,
        following_id: str
    ) -> FollowRelationship:
        """Create a follow relationship."""
        return self.trader_service.follow_trader(follower_id, following_id)

    def unfollow_trader(self, follower_id: str, following_id: str) -> bool:
        """Remove a follow relationship."""
        return self.trader_service.unfollow_trader(follower_id, following_id)

    def get_following(self, trader_id: str) -> List[Trader]:
        """Get traders that a trader is following."""
        return self.trader_service.get_following(trader_id)

    def get_followers(self, trader_id: str) -> List[Trader]:
        """Get traders following a trader."""
        return self.trader_service.get_followers(trader_id)

    def is_following(self, follower_id: str, following_id: str) -> bool:
        """Check if a trader is following another."""
        return self.trader_service.is_following(follower_id, following_id)

    # ==================== Trade Ideas ====================

    def create_trade_idea(
        self,
        trader_id: str,
        title: str,
        description: str,
        asset: str,
        **kwargs
    ) -> TradeIdea:
        """Create a new trade idea."""
        idea = self.trade_idea_service.create_idea(
            trader_id, title, description, asset, **kwargs
        )
        # Track for sentiment analysis
        self.sentiment_service.track_idea(idea)
        return idea

    def publish_trade_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """Publish a draft trade idea."""
        idea = self.trade_idea_service.publish_idea(idea_id, trader_id)
        self.sentiment_service.track_idea(idea)
        return idea

    def update_trade_idea(
        self,
        idea_id: str,
        trader_id: str,
        **updates
    ) -> TradeIdea:
        """Update a trade idea."""
        return self.trade_idea_service.update_idea(idea_id, trader_id, **updates)

    def get_trade_idea(self, idea_id: str) -> TradeIdea:
        """Get a trade idea by ID."""
        idea = self.trade_idea_service.get_idea(idea_id)
        self.trade_idea_service.increment_views(idea_id)
        return idea

    def get_trader_ideas(
        self,
        trader_id: str,
        include_drafts: bool = False
    ) -> List[TradeIdea]:
        """Get all ideas by a trader."""
        return self.trade_idea_service.get_ideas_by_trader(trader_id, include_drafts)

    def search_trade_ideas(
        self,
        query: Optional[str] = None,
        asset: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sentiment: Optional[SentimentType] = None,
        limit: int = 50
    ) -> List[TradeIdea]:
        """Search for trade ideas."""
        return self.trade_idea_service.search_ideas(query, asset, tags, sentiment, limit)

    def get_trending_ideas(self, limit: int = 10) -> List[TradeIdea]:
        """Get trending trade ideas."""
        return self.trade_idea_service.get_trending_ideas(limit)

    def like_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """Like a trade idea."""
        return self.trade_idea_service.like_idea(idea_id, trader_id)

    def unlike_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """Unlike a trade idea."""
        return self.trade_idea_service.unlike_idea(idea_id, trader_id)

    def add_comment(
        self,
        idea_id: str,
        trader_id: str,
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> Comment:
        """Add a comment to a trade idea."""
        return self.trade_idea_service.add_comment(
            idea_id, trader_id, content, parent_comment_id
        )

    def get_comments(
        self,
        idea_id: str,
        parent_comment_id: Optional[str] = None
    ) -> List[Comment]:
        """Get comments for a trade idea."""
        return self.trade_idea_service.get_comments(idea_id, parent_comment_id)

    def share_idea(self, idea_id: str) -> TradeIdea:
        """Share a trade idea."""
        return self.trade_idea_service.share_idea(idea_id)

    # ==================== Performance Metrics ====================

    def record_trade(self, trade: Trade) -> Trade:
        """Record a trade for performance tracking."""
        return self.performance_service.add_trade(trade)

    def get_trader_trades(
        self,
        trader_id: str,
        status: Optional[Any] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """Get trades for a trader."""
        return self.performance_service.get_trader_trades(
            trader_id, status, start_date, end_date
        )

    def get_performance_metrics(
        self,
        trader_id: str,
        period: str = "all_time"
    ) -> PerformanceMetrics:
        """Get performance metrics for a trader."""
        return self.performance_service.calculate_metrics(trader_id, period)

    def compare_trader_performance(
        self,
        trader_ids: List[str],
        period: str = "all_time"
    ) -> Dict[str, PerformanceMetrics]:
        """Compare performance of multiple traders."""
        return self.performance_service.compare_traders(trader_ids, period)

    # ==================== Leaderboards ====================

    def get_leaderboard(
        self,
        metric: str = "total_return",
        period: str = "all_time",
        limit: int = 100,
        min_trades: int = 10
    ) -> List[LeaderboardEntry]:
        """Get leaderboard rankings."""
        return self.leaderboard_service.get_leaderboard(
            metric, period, limit, min_trades
        )

    def get_top_performers(
        self,
        period: str = "1m",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get top performing traders."""
        return self.leaderboard_service.get_top_performers(period, limit)

    def get_most_consistent_traders(
        self,
        period: str = "3m",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get most consistent traders."""
        return self.leaderboard_service.get_most_consistent(period, limit)

    def get_rising_stars(self, limit: int = 10) -> List[LeaderboardEntry]:
        """Get rising star traders."""
        return self.leaderboard_service.get_rising_stars(limit)

    def get_trader_rank(
        self,
        trader_id: str,
        metric: str = "total_return",
        period: str = "all_time"
    ) -> Optional[int]:
        """Get a trader's rank."""
        return self.leaderboard_service.get_trader_rank(trader_id, metric, period)

    def get_all_leaderboards(
        self,
        period: str = "1m"
    ) -> Dict[str, List[LeaderboardEntry]]:
        """Get all category leaderboards."""
        return self.leaderboard_service.get_category_leaderboards(period)

    # ==================== Sentiment Analysis ====================

    def get_asset_sentiment(
        self,
        asset: str,
        timeframe: Optional[timedelta] = None
    ) -> CommunitySentiment:
        """Get aggregated sentiment for an asset."""
        return self.sentiment_service.get_asset_sentiment(asset, timeframe)

    def get_trending_assets(
        self,
        limit: int = 10,
        timeframe: timedelta = timedelta(hours=24)
    ) -> List[CommunitySentiment]:
        """Get trending assets."""
        return self.sentiment_service.get_trending_assets(limit, timeframe)

    def get_bullish_assets(
        self,
        limit: int = 10,
        min_volume: int = 5
    ) -> List[CommunitySentiment]:
        """Get assets with bullish sentiment."""
        return self.sentiment_service.get_bullish_assets(limit, min_volume)

    def get_bearish_assets(
        self,
        limit: int = 10,
        min_volume: int = 5
    ) -> List[CommunitySentiment]:
        """Get assets with bearish sentiment."""
        return self.sentiment_service.get_bearish_assets(limit, min_volume)

    def get_sentiment_distribution(self, asset: str) -> Dict[str, float]:
        """Get sentiment distribution for an asset."""
        return self.sentiment_service.get_sentiment_distribution(asset)

    def get_sentiment_history(
        self,
        asset: str,
        days: int = 7
    ) -> List[Dict]:
        """Get historical sentiment data."""
        return self.sentiment_service.get_sentiment_history(asset, days)

    # ==================== Copy Trading ====================

    def enable_copy_trading(
        self,
        follower_id: str,
        following_id: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> FollowRelationship:
        """Enable copy trading."""
        return self.copy_trading_service.enable_copy_trading(
            follower_id, following_id, settings
        )

    def disable_copy_trading(
        self,
        follower_id: str,
        following_id: str,
        close_positions: bool = False
    ) -> bool:
        """Disable copy trading."""
        return self.copy_trading_service.disable_copy_trading(
            follower_id, following_id, close_positions
        )

    def update_copy_settings(
        self,
        follower_id: str,
        following_id: str,
        settings: Dict[str, Any]
    ) -> FollowRelationship:
        """Update copy trading settings."""
        return self.copy_trading_service.update_copy_settings(
            follower_id, following_id, settings
        )

    def get_copy_statistics(
        self,
        follower_id: str,
        following_id: str
    ) -> Dict[str, Any]:
        """Get copy trading statistics."""
        return self.copy_trading_service.get_copy_statistics(
            follower_id, following_id
        )

    # ==================== Utility Methods ====================

    def clear_caches(self):
        """Clear all service caches."""
        self.leaderboard_service.clear_cache()
        self.sentiment_service.clear_cache()

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        traders = self.trader_service.get_all_traders()

        return {
            "total_traders": len(traders),
            "total_verified_traders": sum(1 for t in traders if t.verified),
            "total_ideas": len(self.trade_idea_service._ideas),
            "total_comments": len(self.trade_idea_service._comments),
            "total_trades": len(self.performance_service._trades),
            "active_copy_relationships": sum(
                1 for r in self.trader_service._relationships.values()
                if r.active and r.follow_type == FollowType.COPY
            )
        }
