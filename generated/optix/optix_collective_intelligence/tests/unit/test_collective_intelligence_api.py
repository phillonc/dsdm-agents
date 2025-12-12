"""
Unit tests for CollectiveIntelligenceAPI.
"""

import pytest
from datetime import datetime, timedelta

from src.collective_intelligence_api import CollectiveIntelligenceAPI
from src.models import TradeType, Trade, TradeStatus, SentimentType


class TestCollectiveIntelligenceAPI:
    """Test suite for CollectiveIntelligenceAPI."""

    @pytest.fixture
    def api(self):
        """Create API instance."""
        return CollectiveIntelligenceAPI()

    def test_create_trader(self, api):
        """Test creating a trader through the API."""
        trader = api.create_trader(
            username="apiuser",
            display_name="API User",
            bio="Test bio"
        )

        assert trader.username == "apiuser"
        assert trader.display_name == "API User"

    def test_get_trader(self, api):
        """Test getting a trader."""
        trader = api.create_trader(username="testuser", display_name="Test User")
        fetched = api.get_trader(trader.trader_id)

        assert fetched.trader_id == trader.trader_id

    def test_follow_and_unfollow(self, api):
        """Test following and unfollowing."""
        trader1 = api.create_trader(username="user1", display_name="User 1")
        trader2 = api.create_trader(username="user2", display_name="User 2")

        # Follow
        relationship = api.follow_trader(trader1.trader_id, trader2.trader_id)
        assert relationship is not None

        # Check following
        assert api.is_following(trader1.trader_id, trader2.trader_id)

        # Get lists
        following = api.get_following(trader1.trader_id)
        assert len(following) == 1

        followers = api.get_followers(trader2.trader_id)
        assert len(followers) == 1

        # Unfollow
        api.unfollow_trader(trader1.trader_id, trader2.trader_id)
        assert not api.is_following(trader1.trader_id, trader2.trader_id)

    def test_create_and_publish_trade_idea(self, api):
        """Test creating and publishing a trade idea."""
        trader = api.create_trader(username="trader", display_name="Trader")

        # Create idea
        idea = api.create_trade_idea(
            trader_id=trader.trader_id,
            title="BTC Long Setup",
            description="Bullish pattern forming",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            entry_price=50000.0,
            sentiment=SentimentType.BULLISH
        )

        assert idea.title == "BTC Long Setup"
        assert idea.status.value == "draft"

        # Publish
        published = api.publish_trade_idea(idea.idea_id, trader.trader_id)
        assert published.status.value == "published"
        assert published.published_at is not None

    def test_trade_idea_interactions(self, api):
        """Test trade idea interactions."""
        trader1 = api.create_trader(username="trader1", display_name="Trader 1")
        trader2 = api.create_trader(username="trader2", display_name="Trader 2")

        idea = api.create_trade_idea(
            trader_id=trader1.trader_id,
            title="Test Idea",
            description="Test description",
            asset="BTC/USD"
        )
        api.publish_trade_idea(idea.idea_id, trader1.trader_id)

        # Like
        liked = api.like_idea(idea.idea_id, trader2.trader_id)
        assert liked.likes_count == 1

        # Comment
        comment = api.add_comment(
            idea.idea_id,
            trader2.trader_id,
            "Great analysis!"
        )
        assert comment.content == "Great analysis!"

        # Get comments
        comments = api.get_comments(idea.idea_id)
        assert len(comments) == 1

        # Share
        shared = api.share_idea(idea.idea_id)
        assert shared.shares_count == 1

    def test_search_trade_ideas(self, api):
        """Test searching trade ideas."""
        trader = api.create_trader(username="trader", display_name="Trader")

        idea1 = api.create_trade_idea(
            trader_id=trader.trader_id,
            title="Bitcoin Analysis",
            description="BTC going up",
            asset="BTC/USD",
            tags=["bitcoin", "long"]
        )
        api.publish_trade_idea(idea1.idea_id, trader.trader_id)

        idea2 = api.create_trade_idea(
            trader_id=trader.trader_id,
            title="Ethereum Setup",
            description="ETH breakout",
            asset="ETH/USD",
            tags=["ethereum"]
        )
        api.publish_trade_idea(idea2.idea_id, trader.trader_id)

        # Search by query
        results = api.search_trade_ideas(query="bitcoin")
        assert len(results) == 1

        # Search by asset
        results = api.search_trade_ideas(asset="ETH/USD")
        assert len(results) == 1

        # Search by tags
        results = api.search_trade_ideas(tags=["long"])
        assert len(results) == 1

    def test_record_trade_and_get_performance(self, api):
        """Test recording trades and getting performance."""
        trader = api.create_trader(username="trader", display_name="Trader")

        # Record winning trades
        for i in range(6):
            trade = Trade(
                trader_id=trader.trader_id,
                asset="BTC/USD",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            )
            api.record_trade(trade)

        # Record losing trades
        for i in range(4):
            trade = Trade(
                trader_id=trader.trader_id,
                asset="BTC/USD",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=-500.0,
                profit_loss_percentage=-2.5
            )
            api.record_trade(trade)

        # Get performance
        metrics = api.get_performance_metrics(trader.trader_id)

        assert metrics.total_trades == 10
        assert metrics.winning_trades == 6
        assert metrics.win_rate == 60.0

    def test_get_leaderboards(self, api):
        """Test getting leaderboards."""
        # Create traders with performance
        for i in range(3):
            trader = api.create_trader(
                username=f"trader{i}",
                display_name=f"Trader {i}"
            )

            for j in range(15):
                trade = Trade(
                    trader_id=trader.trader_id,
                    asset="BTC/USD",
                    trade_type=TradeType.BUY,
                    status=TradeStatus.CLOSED,
                    profit_loss=1000.0 * (i + 1),
                    profit_loss_percentage=5.0 * (i + 1)
                )
                api.record_trade(trade)

        # Get leaderboard
        leaderboard = api.get_leaderboard(limit=10)
        assert len(leaderboard) == 3

        # Get top performers
        top = api.get_top_performers(limit=2)
        assert len(top) <= 2

        # Get all leaderboards
        all_leaderboards = api.get_all_leaderboards()
        assert "top_performers" in all_leaderboards
        assert "most_consistent" in all_leaderboards

    def test_sentiment_analysis(self, api):
        """Test sentiment analysis features."""
        trader = api.create_trader(username="trader", display_name="Trader")

        # Create ideas with different sentiments
        for i in range(6):
            idea = api.create_trade_idea(
                trader_id=trader.trader_id,
                title=f"BTC Bullish {i}",
                description="Bullish setup",
                asset="BTC/USD",
                sentiment=SentimentType.BULLISH
            )
            api.publish_trade_idea(idea.idea_id, trader.trader_id)

        for i in range(3):
            idea = api.create_trade_idea(
                trader_id=trader.trader_id,
                title=f"BTC Bearish {i}",
                description="Bearish setup",
                asset="BTC/USD",
                sentiment=SentimentType.BEARISH
            )
            api.publish_trade_idea(idea.idea_id, trader.trader_id)

        # Get sentiment
        sentiment = api.get_asset_sentiment("BTC/USD")
        assert sentiment.bullish_count == 6
        assert sentiment.bearish_count == 3
        assert sentiment.overall_sentiment == SentimentType.BULLISH

        # Get distribution
        distribution = api.get_sentiment_distribution("BTC/USD")
        assert distribution["bullish"] > distribution["bearish"]

        # Get trending assets
        trending = api.get_trending_assets()
        assert len(trending) >= 1

    def test_copy_trading(self, api):
        """Test copy trading features."""
        leader = api.create_trader(username="leader", display_name="Leader")
        follower = api.create_trader(username="follower", display_name="Follower")

        # Enable copy trading
        settings = {
            "copy_percentage": 50.0,
            "max_position_size": 100.0
        }
        relationship = api.enable_copy_trading(
            follower.trader_id,
            leader.trader_id,
            settings
        )

        assert relationship.copy_settings["copy_percentage"] == 50.0

        # Update settings
        new_settings = {"copy_percentage": 75.0}
        updated = api.update_copy_settings(
            follower.trader_id,
            leader.trader_id,
            new_settings
        )
        assert updated.copy_settings["copy_percentage"] == 75.0

        # Disable copy trading
        result = api.disable_copy_trading(follower.trader_id, leader.trader_id)
        assert result is True

    def test_get_system_stats(self, api):
        """Test getting system statistics."""
        # Create some data
        trader1 = api.create_trader(username="trader1", display_name="Trader 1")
        trader2 = api.create_trader(username="trader2", display_name="Trader 2")

        api.create_trade_idea(
            trader_id=trader1.trader_id,
            title="Idea 1",
            description="Description",
            asset="BTC"
        )

        api.follow_trader(trader1.trader_id, trader2.trader_id)

        stats = api.get_system_stats()

        assert stats["total_traders"] == 2
        assert stats["total_ideas"] >= 1
        assert "total_trades" in stats

    def test_clear_caches(self, api):
        """Test clearing caches."""
        trader = api.create_trader(username="trader", display_name="Trader")

        for i in range(15):
            trade = Trade(
                trader_id=trader.trader_id,
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            )
            api.record_trade(trade)

        # Generate cached data
        api.get_leaderboard()
        api.create_trade_idea(
            trader_id=trader.trader_id,
            title="Test",
            description="Description",
            asset="BTC",
            sentiment=SentimentType.BULLISH
        )

        # Clear caches
        api.clear_caches()

        # Should work fine after clearing
        leaderboard = api.get_leaderboard()
        assert len(leaderboard) >= 0

    def test_compare_trader_performance(self, api):
        """Test comparing trader performance."""
        trader1 = api.create_trader(username="trader1", display_name="Trader 1")
        trader2 = api.create_trader(username="trader2", display_name="Trader 2")

        # Add trades for both
        for trader in [trader1, trader2]:
            for i in range(10):
                trade = Trade(
                    trader_id=trader.trader_id,
                    asset="BTC",
                    trade_type=TradeType.BUY,
                    status=TradeStatus.CLOSED,
                    profit_loss=1000.0,
                    profit_loss_percentage=5.0
                )
                api.record_trade(trade)

        comparison = api.compare_trader_performance([trader1.trader_id, trader2.trader_id])

        assert trader1.trader_id in comparison
        assert trader2.trader_id in comparison
        assert comparison[trader1.trader_id].total_trades == 10

    def test_get_trader_rank(self, api):
        """Test getting trader rank."""
        traders = []
        for i in range(3):
            trader = api.create_trader(
                username=f"trader{i}",
                display_name=f"Trader {i}"
            )
            traders.append(trader)

            for j in range(15):
                trade = Trade(
                    trader_id=trader.trader_id,
                    asset="BTC",
                    trade_type=TradeType.BUY,
                    status=TradeStatus.CLOSED,
                    profit_loss=1000.0 * (i + 1),
                    profit_loss_percentage=5.0 * (i + 1)
                )
                api.record_trade(trade)

        rank = api.get_trader_rank(traders[2].trader_id)
        assert rank == 1  # Best performer should be rank 1

    def test_get_trending_ideas(self, api):
        """Test getting trending ideas."""
        trader = api.create_trader(username="trader", display_name="Trader")

        # Create ideas with engagement
        idea1 = api.create_trade_idea(
            trader_id=trader.trader_id,
            title="Trending Idea",
            description="Description",
            asset="BTC"
        )
        api.publish_trade_idea(idea1.idea_id, trader.trader_id)
        api.like_idea(idea1.idea_id, trader.trader_id)
        api.add_comment(idea1.idea_id, trader.trader_id, "Comment")

        trending = api.get_trending_ideas(limit=10)
        assert len(trending) >= 1

    def test_end_to_end_workflow(self, api):
        """Test complete workflow."""
        # Create traders
        leader = api.create_trader(username="leader", display_name="Leader")
        follower = api.create_trader(username="follower", display_name="Follower")

        # Follow
        api.follow_trader(follower.trader_id, leader.trader_id)

        # Create trade idea
        idea = api.create_trade_idea(
            trader_id=leader.trader_id,
            title="BTC Long",
            description="Going up",
            asset="BTC/USD",
            sentiment=SentimentType.BULLISH
        )
        api.publish_trade_idea(idea.idea_id, leader.trader_id)

        # Interact with idea
        api.like_idea(idea.idea_id, follower.trader_id)
        api.add_comment(idea.idea_id, follower.trader_id, "Good idea!")

        # Record trades
        for i in range(20):
            trade = Trade(
                trader_id=leader.trader_id,
                asset="BTC/USD",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            )
            api.record_trade(trade)

        # Check everything
        assert api.is_following(follower.trader_id, leader.trader_id)
        
        sentiment = api.get_asset_sentiment("BTC/USD")
        assert sentiment.bullish_count >= 1

        metrics = api.get_performance_metrics(leader.trader_id)
        assert metrics.total_trades == 20

        leaderboard = api.get_leaderboard()
        assert len(leaderboard) >= 1
