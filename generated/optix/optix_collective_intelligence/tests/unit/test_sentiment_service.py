"""
Unit tests for SentimentService.
"""

import pytest
from datetime import datetime, timedelta

from src.sentiment_service import SentimentService
from src.models import TradeIdea, SentimentType, IdeaStatus, TradeType


class TestSentimentService:
    """Test suite for SentimentService."""

    @pytest.fixture
    def service(self):
        """Create a SentimentService instance."""
        return SentimentService()

    @pytest.fixture
    def sample_ideas(self, service):
        """Create sample trade ideas with different sentiments."""
        ideas = []
        
        # Bullish ideas for BTC
        for i in range(6):
            idea = TradeIdea(
                trader_id=f"trader{i}",
                title=f"BTC Bullish {i}",
                description="Bullish setup",
                asset="BTC/USD",
                sentiment=SentimentType.BULLISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow() - timedelta(hours=i)
            )
            service.track_idea(idea)
            ideas.append(idea)

        # Bearish ideas for BTC
        for i in range(3):
            idea = TradeIdea(
                trader_id=f"trader{i+6}",
                title=f"BTC Bearish {i}",
                description="Bearish setup",
                asset="BTC/USD",
                sentiment=SentimentType.BEARISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow() - timedelta(hours=i)
            )
            service.track_idea(idea)
            ideas.append(idea)

        # Neutral idea for BTC
        idea = TradeIdea(
            trader_id="trader9",
            title="BTC Neutral",
            description="Neutral outlook",
            asset="BTC/USD",
            sentiment=SentimentType.NEUTRAL,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow()
        )
        service.track_idea(idea)
        ideas.append(idea)

        return ideas

    def test_track_idea(self, service):
        """Test tracking a trade idea."""
        idea = TradeIdea(
            trader_id="trader123",
            title="Test Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow()
        )

        service.track_idea(idea)

        assert idea.idea_id in service._ideas
        assert "BTC/USD" in service._asset_ideas
        assert idea.idea_id in service._asset_ideas["BTC/USD"]

    def test_track_draft_idea(self, service):
        """Test tracking a draft idea."""
        idea = TradeIdea(
            trader_id="trader123",
            title="Draft Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.DRAFT
        )

        service.track_idea(idea)

        # Draft ideas should not be added to asset_ideas
        assert "BTC/USD" not in service._asset_ideas

    def test_update_idea_sentiment(self, service):
        """Test updating idea sentiment."""
        idea = TradeIdea(
            trader_id="trader123",
            title="Test Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.NEUTRAL,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow()
        )
        service.track_idea(idea)

        service.update_idea_sentiment(idea.idea_id, SentimentType.BULLISH)

        assert service._ideas[idea.idea_id].sentiment == SentimentType.BULLISH

    def test_get_asset_sentiment(self, service, sample_ideas):
        """Test getting asset sentiment."""
        sentiment = service.get_asset_sentiment("BTC/USD")

        assert sentiment.asset == "BTC/USD"
        assert sentiment.bullish_count == 6
        assert sentiment.bearish_count == 3
        assert sentiment.neutral_count == 1
        assert sentiment.volume_24h == 10
        assert sentiment.overall_sentiment == SentimentType.BULLISH
        assert sentiment.sentiment_score > 0

    def test_get_asset_sentiment_bearish(self, service):
        """Test getting bearish asset sentiment."""
        # Create mostly bearish ideas
        for i in range(7):
            idea = TradeIdea(
                trader_id=f"trader{i}",
                title=f"ETH Bearish {i}",
                description="Bearish setup",
                asset="ETH/USD",
                sentiment=SentimentType.BEARISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow()
            )
            service.track_idea(idea)

        for i in range(2):
            idea = TradeIdea(
                trader_id=f"trader{i+7}",
                title=f"ETH Bullish {i}",
                description="Bullish setup",
                asset="ETH/USD",
                sentiment=SentimentType.BULLISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow()
            )
            service.track_idea(idea)

        sentiment = service.get_asset_sentiment("ETH/USD")

        assert sentiment.overall_sentiment == SentimentType.BEARISH
        assert sentiment.sentiment_score < 0

    def test_get_asset_sentiment_neutral(self, service):
        """Test getting neutral asset sentiment."""
        # Create balanced ideas
        for i in range(3):
            idea = TradeIdea(
                trader_id=f"trader{i}",
                title=f"XRP Bullish {i}",
                description="Bullish setup",
                asset="XRP/USD",
                sentiment=SentimentType.BULLISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow()
            )
            service.track_idea(idea)

        for i in range(3):
            idea = TradeIdea(
                trader_id=f"trader{i+3}",
                title=f"XRP Bearish {i}",
                description="Bearish setup",
                asset="XRP/USD",
                sentiment=SentimentType.BEARISH,
                status=IdeaStatus.PUBLISHED,
                published_at=datetime.utcnow()
            )
            service.track_idea(idea)

        sentiment = service.get_asset_sentiment("XRP/USD")

        assert sentiment.overall_sentiment == SentimentType.NEUTRAL
        assert abs(sentiment.sentiment_score) <= 20

    def test_get_asset_sentiment_no_data(self, service):
        """Test getting sentiment for asset with no data."""
        sentiment = service.get_asset_sentiment("UNKNOWN/USD")

        assert sentiment.volume_24h == 0
        assert sentiment.overall_sentiment == SentimentType.NEUTRAL
        assert sentiment.sentiment_score == 0.0

    def test_get_asset_sentiment_timeframe(self, service):
        """Test getting sentiment with custom timeframe."""
        # Old idea (beyond timeframe)
        old_idea = TradeIdea(
            trader_id="trader1",
            title="Old Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow() - timedelta(days=2)
        )
        service.track_idea(old_idea)

        # Recent idea
        recent_idea = TradeIdea(
            trader_id="trader2",
            title="Recent Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BEARISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow()
        )
        service.track_idea(recent_idea)

        # Get sentiment for last 24 hours
        sentiment = service.get_asset_sentiment("BTC/USD", timeframe=timedelta(hours=24))

        # Should only include recent idea
        assert sentiment.volume_24h == 1
        assert sentiment.bearish_count == 1

    def test_get_trending_assets(self, service):
        """Test getting trending assets."""
        # Create ideas for multiple assets with different engagement
        btc_idea = TradeIdea(
            trader_id="trader1",
            title="BTC Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            views_count=1000,
            likes_count=50,
            comments_count=20
        )
        service.track_idea(btc_idea)

        eth_idea = TradeIdea(
            trader_id="trader2",
            title="ETH Idea",
            description="Description",
            asset="ETH/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            views_count=500,
            likes_count=10
        )
        service.track_idea(eth_idea)

        trending = service.get_trending_assets(limit=10)

        assert len(trending) >= 1
        # BTC should be first due to higher engagement
        assert trending[0].asset == "BTC/USD"

    def test_get_bullish_assets(self, service):
        """Test getting bullish assets."""
        # Create bullish ideas for multiple assets
        for asset in ["BTC/USD", "ETH/USD", "XRP/USD"]:
            for i in range(7):
                idea = TradeIdea(
                    trader_id=f"trader{i}",
                    title=f"{asset} Idea",
                    description="Description",
                    asset=asset,
                    sentiment=SentimentType.BULLISH,
                    status=IdeaStatus.PUBLISHED,
                    published_at=datetime.utcnow()
                )
                service.track_idea(idea)

        bullish = service.get_bullish_assets(limit=10, min_volume=5)

        assert len(bullish) == 3
        assert all(s.overall_sentiment == SentimentType.BULLISH for s in bullish)
        assert all(s.volume_24h >= 5 for s in bullish)

    def test_get_bearish_assets(self, service):
        """Test getting bearish assets."""
        # Create bearish ideas
        for asset in ["BTC/USD", "ETH/USD"]:
            for i in range(7):
                idea = TradeIdea(
                    trader_id=f"trader{i}",
                    title=f"{asset} Idea",
                    description="Description",
                    asset=asset,
                    sentiment=SentimentType.BEARISH,
                    status=IdeaStatus.PUBLISHED,
                    published_at=datetime.utcnow()
                )
                service.track_idea(idea)

        bearish = service.get_bearish_assets(limit=10, min_volume=5)

        assert len(bearish) == 2
        assert all(s.overall_sentiment == SentimentType.BEARISH for s in bearish)

    def test_get_sentiment_distribution(self, service, sample_ideas):
        """Test getting sentiment distribution."""
        distribution = service.get_sentiment_distribution("BTC/USD")

        assert "bullish" in distribution
        assert "bearish" in distribution
        assert "neutral" in distribution

        # Check percentages add up to 100
        total = distribution["bullish"] + distribution["bearish"] + distribution["neutral"]
        assert abs(total - 100.0) < 0.01

        # Check values match counts
        assert distribution["bullish"] == 60.0  # 6 out of 10
        assert distribution["bearish"] == 30.0  # 3 out of 10
        assert distribution["neutral"] == 10.0  # 1 out of 10

    def test_get_sentiment_history(self, service):
        """Test getting sentiment history."""
        # Create ideas over multiple days
        for day in range(3):
            for i in range(5):
                idea = TradeIdea(
                    trader_id=f"trader{day}_{i}",
                    title=f"Idea {day}_{i}",
                    description="Description",
                    asset="BTC/USD",
                    sentiment=SentimentType.BULLISH if i < 3 else SentimentType.BEARISH,
                    status=IdeaStatus.PUBLISHED,
                    published_at=datetime.utcnow() - timedelta(days=day, hours=12)
                )
                service.track_idea(idea)

        history = service.get_sentiment_history("BTC/USD", days=7)

        assert len(history) == 7
        assert all("date" in entry for entry in history)
        assert all("bullish" in entry for entry in history)
        assert all("bearish" in entry for entry in history)
        assert all("score" in entry for entry in history)

    def test_calculate_trending_score(self, service):
        """Test trending score calculation."""
        # Recent idea with high engagement
        recent_idea = TradeIdea(
            trader_id="trader1",
            title="Recent Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            views_count=1000,
            likes_count=100,
            comments_count=50,
            shares_count=20
        )

        # Old idea with low engagement
        old_idea = TradeIdea(
            trader_id="trader2",
            title="Old Idea",
            description="Description",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH,
            status=IdeaStatus.PUBLISHED,
            published_at=datetime.utcnow() - timedelta(hours=23),
            views_count=100,
            likes_count=5
        )

        score = service._calculate_trending_score([recent_idea, old_idea])

        assert isinstance(score, float)
        assert score > 0

        # Recent idea should contribute more
        recent_score = service._calculate_trending_score([recent_idea])
        old_score = service._calculate_trending_score([old_idea])
        assert recent_score > old_score

    def test_sentiment_caching(self, service, sample_ideas):
        """Test that sentiment is cached."""
        # First call
        sentiment1 = service.get_asset_sentiment("BTC/USD")
        
        # Second call (should be cached)
        sentiment2 = service.get_asset_sentiment("BTC/USD")

        # Should return same calculated_at time within cache TTL
        assert sentiment1.calculated_at == sentiment2.calculated_at

    def test_clear_cache(self, service, sample_ideas):
        """Test clearing sentiment cache."""
        service.get_asset_sentiment("BTC/USD")
        assert len(service._sentiment_cache) > 0

        service.clear_cache()
        assert len(service._sentiment_cache) == 0
