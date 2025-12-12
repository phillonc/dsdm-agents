"""
Sentiment Service for aggregating and analyzing community sentiment.

This service tracks and aggregates sentiment from trade ideas and community activity.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
from .models import CommunitySentiment, SentimentType, TradeIdea, IdeaStatus
from .exceptions import NotFoundError


class SentimentService:
    """Service for managing community sentiment."""

    def __init__(self):
        """Initialize the sentiment service."""
        self._sentiment_cache: Dict[str, CommunitySentiment] = {}
        self._asset_ideas: Dict[str, List[str]] = defaultdict(list)  # asset -> idea_ids
        self._ideas: Dict[str, TradeIdea] = {}

    def track_idea(self, idea: TradeIdea):
        """
        Track a trade idea for sentiment analysis.

        Args:
            idea: TradeIdea object to track
        """
        self._ideas[idea.idea_id] = idea
        if idea.status == IdeaStatus.PUBLISHED:
            self._asset_ideas[idea.asset].append(idea.idea_id)
            # Invalidate cache for this asset
            if idea.asset in self._sentiment_cache:
                del self._sentiment_cache[idea.asset]

    def update_idea_sentiment(self, idea_id: str, sentiment: SentimentType):
        """
        Update sentiment for a trade idea.

        Args:
            idea_id: ID of the idea
            sentiment: New sentiment value

        Raises:
            NotFoundError: If idea doesn't exist
        """
        if idea_id not in self._ideas:
            raise NotFoundError(f"Trade idea {idea_id} not found")

        idea = self._ideas[idea_id]
        old_sentiment = idea.sentiment
        idea.sentiment = sentiment

        # Invalidate cache if sentiment changed
        if old_sentiment != sentiment:
            if idea.asset in self._sentiment_cache:
                del self._sentiment_cache[idea.asset]

    def get_asset_sentiment(
        self,
        asset: str,
        timeframe: Optional[timedelta] = None
    ) -> CommunitySentiment:
        """
        Get aggregated sentiment for an asset.

        Args:
            asset: Asset symbol
            timeframe: Optional timeframe for recent sentiment (default: 24h)

        Returns:
            CommunitySentiment object
        """
        if not timeframe:
            timeframe = timedelta(hours=24)

        # Check cache (5 minute TTL)
        cache_key = f"{asset}:{timeframe.total_seconds()}"
        if asset in self._sentiment_cache:
            cached = self._sentiment_cache[asset]
            if (datetime.utcnow() - cached.calculated_at).seconds < 300:
                return cached

        # Get recent ideas for this asset
        cutoff_time = datetime.utcnow() - timeframe
        idea_ids = self._asset_ideas.get(asset, [])
        recent_ideas = [
            self._ideas[iid] for iid in idea_ids
            if iid in self._ideas
            and self._ideas[iid].published_at
            and self._ideas[iid].published_at >= cutoff_time
        ]

        # Count sentiments
        bullish_count = sum(1 for i in recent_ideas if i.sentiment == SentimentType.BULLISH)
        bearish_count = sum(1 for i in recent_ideas if i.sentiment == SentimentType.BEARISH)
        neutral_count = sum(1 for i in recent_ideas if i.sentiment == SentimentType.NEUTRAL)

        total = bullish_count + bearish_count + neutral_count

        # Calculate overall sentiment
        if total == 0:
            overall_sentiment = SentimentType.NEUTRAL
            sentiment_score = 0.0
        else:
            # Calculate weighted sentiment score (-100 to 100)
            sentiment_score = ((bullish_count - bearish_count) / total) * 100

            if sentiment_score > 20:
                overall_sentiment = SentimentType.BULLISH
            elif sentiment_score < -20:
                overall_sentiment = SentimentType.BEARISH
            else:
                overall_sentiment = SentimentType.NEUTRAL

        # Calculate trending score based on volume and recency
        trending_score = self._calculate_trending_score(recent_ideas)

        sentiment = CommunitySentiment(
            asset=asset,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            overall_sentiment=overall_sentiment,
            sentiment_score=sentiment_score,
            volume_24h=total,
            trending_score=trending_score
        )

        self._sentiment_cache[asset] = sentiment
        return sentiment

    def get_trending_assets(
        self,
        limit: int = 10,
        timeframe: timedelta = timedelta(hours=24)
    ) -> List[CommunitySentiment]:
        """
        Get trending assets based on community activity.

        Args:
            limit: Maximum number of assets
            timeframe: Timeframe for trending calculation

        Returns:
            List of CommunitySentiment objects
        """
        assets = list(self._asset_ideas.keys())
        sentiments = [
            self.get_asset_sentiment(asset, timeframe)
            for asset in assets
        ]

        # Sort by trending score
        sentiments = sorted(
            sentiments,
            key=lambda x: x.trending_score,
            reverse=True
        )

        return sentiments[:limit]

    def get_bullish_assets(
        self,
        limit: int = 10,
        min_volume: int = 5
    ) -> List[CommunitySentiment]:
        """
        Get assets with most bullish sentiment.

        Args:
            limit: Maximum number of assets
            min_volume: Minimum volume threshold

        Returns:
            List of CommunitySentiment objects
        """
        assets = list(self._asset_ideas.keys())
        sentiments = [
            self.get_asset_sentiment(asset)
            for asset in assets
        ]

        # Filter by volume and bullish sentiment
        sentiments = [
            s for s in sentiments
            if s.volume_24h >= min_volume
            and s.overall_sentiment == SentimentType.BULLISH
        ]

        # Sort by sentiment score
        sentiments = sorted(
            sentiments,
            key=lambda x: x.sentiment_score,
            reverse=True
        )

        return sentiments[:limit]

    def get_bearish_assets(
        self,
        limit: int = 10,
        min_volume: int = 5
    ) -> List[CommunitySentiment]:
        """
        Get assets with most bearish sentiment.

        Args:
            limit: Maximum number of assets
            min_volume: Minimum volume threshold

        Returns:
            List of CommunitySentiment objects
        """
        assets = list(self._asset_ideas.keys())
        sentiments = [
            self.get_asset_sentiment(asset)
            for asset in assets
        ]

        # Filter by volume and bearish sentiment
        sentiments = [
            s for s in sentiments
            if s.volume_24h >= min_volume
            and s.overall_sentiment == SentimentType.BEARISH
        ]

        # Sort by sentiment score (most negative)
        sentiments = sorted(
            sentiments,
            key=lambda x: x.sentiment_score
        )

        return sentiments[:limit]

    def get_sentiment_distribution(
        self,
        asset: str
    ) -> Dict[str, float]:
        """
        Get sentiment distribution percentages for an asset.

        Args:
            asset: Asset symbol

        Returns:
            Dictionary with bullish, bearish, neutral percentages
        """
        sentiment = self.get_asset_sentiment(asset)
        total = sentiment.volume_24h

        if total == 0:
            return {
                "bullish": 0.0,
                "bearish": 0.0,
                "neutral": 0.0
            }

        return {
            "bullish": (sentiment.bullish_count / total) * 100,
            "bearish": (sentiment.bearish_count / total) * 100,
            "neutral": (sentiment.neutral_count / total) * 100
        }

    def get_sentiment_history(
        self,
        asset: str,
        days: int = 7
    ) -> List[Dict]:
        """
        Get historical sentiment data for an asset.

        Args:
            asset: Asset symbol
            days: Number of days of history

        Returns:
            List of daily sentiment snapshots
        """
        history = []
        for i in range(days):
            start_time = datetime.utcnow() - timedelta(days=i+1)
            end_time = datetime.utcnow() - timedelta(days=i)

            # Get ideas for this day
            idea_ids = self._asset_ideas.get(asset, [])
            day_ideas = [
                self._ideas[iid] for iid in idea_ids
                if iid in self._ideas
                and self._ideas[iid].published_at
                and start_time <= self._ideas[iid].published_at < end_time
            ]

            bullish = sum(1 for i in day_ideas if i.sentiment == SentimentType.BULLISH)
            bearish = sum(1 for i in day_ideas if i.sentiment == SentimentType.BEARISH)
            neutral = sum(1 for i in day_ideas if i.sentiment == SentimentType.NEUTRAL)

            total = bullish + bearish + neutral
            score = ((bullish - bearish) / total * 100) if total > 0 else 0.0

            history.append({
                "date": start_time.strftime("%Y-%m-%d"),
                "bullish": bullish,
                "bearish": bearish,
                "neutral": neutral,
                "score": score
            })

        return list(reversed(history))

    def _calculate_trending_score(self, ideas: List[TradeIdea]) -> float:
        """
        Calculate trending score based on idea engagement and recency.

        Args:
            ideas: List of TradeIdea objects

        Returns:
            Trending score
        """
        if not ideas:
            return 0.0

        score = 0.0
        now = datetime.utcnow()

        for idea in ideas:
            # Engagement score
            engagement = (
                idea.views_count * 0.1 +
                idea.likes_count * 2 +
                idea.comments_count * 3 +
                idea.shares_count * 5
            )

            # Recency factor (decay over 24 hours)
            hours_old = (now - idea.published_at).total_seconds() / 3600
            recency_factor = 1 / (1 + hours_old / 24)

            score += engagement * recency_factor

        return score

    def clear_cache(self):
        """Clear the sentiment cache."""
        self._sentiment_cache.clear()
