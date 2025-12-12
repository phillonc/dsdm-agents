"""
Unit tests for TradeIdeaService.
"""

import pytest
from datetime import datetime

from src.trade_idea_service import TradeIdeaService
from src.models import TradeIdea, TradeType, IdeaStatus, SentimentType
from src.exceptions import ValidationError, NotFoundError, PermissionError


class TestTradeIdeaService:
    """Test suite for TradeIdeaService."""

    @pytest.fixture
    def service(self):
        """Create a TradeIdeaService instance."""
        return TradeIdeaService()

    @pytest.fixture
    def sample_idea(self, service):
        """Create a sample trade idea."""
        return service.create_idea(
            trader_id="trader123",
            title="BTC Long Setup",
            description="Bitcoin showing bullish patterns on the 4H chart",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            entry_price=50000.0,
            target_price=55000.0,
            stop_loss=48000.0
        )

    def test_create_idea_success(self, service):
        """Test successful idea creation."""
        idea = service.create_idea(
            trader_id="trader123",
            title="Test Trade Idea",
            description="This is a test trade idea description",
            asset="ETH/USD",
            trade_type=TradeType.BUY,
            entry_price=3000.0
        )

        assert idea.idea_id is not None
        assert idea.trader_id == "trader123"
        assert idea.title == "Test Trade Idea"
        assert idea.status == IdeaStatus.DRAFT
        assert idea.likes_count == 0
        assert idea.comments_count == 0

    def test_create_idea_validation_errors(self, service):
        """Test idea creation validation."""
        with pytest.raises(ValidationError):
            service.create_idea(
                trader_id="",
                title="Test",
                description="Description",
                asset="BTC"
            )

        with pytest.raises(ValidationError):
            service.create_idea(
                trader_id="trader123",
                title="abc",  # Too short
                description="Description",
                asset="BTC"
            )

        with pytest.raises(ValidationError):
            service.create_idea(
                trader_id="trader123",
                title="Good Title",
                description="Short",  # Too short
                asset="BTC"
            )

    def test_publish_idea_success(self, service, sample_idea):
        """Test publishing a draft idea."""
        published = service.publish_idea(sample_idea.idea_id, "trader123")

        assert published.status == IdeaStatus.PUBLISHED
        assert published.published_at is not None
        assert isinstance(published.published_at, datetime)

    def test_publish_idea_permission_error(self, service, sample_idea):
        """Test publishing idea by non-owner."""
        with pytest.raises(PermissionError):
            service.publish_idea(sample_idea.idea_id, "different_trader")

    def test_publish_already_published(self, service, sample_idea):
        """Test publishing already published idea."""
        service.publish_idea(sample_idea.idea_id, "trader123")

        with pytest.raises(ValidationError):
            service.publish_idea(sample_idea.idea_id, "trader123")

    def test_update_idea_success(self, service, sample_idea):
        """Test updating an idea."""
        updated = service.update_idea(
            sample_idea.idea_id,
            "trader123",
            title="Updated Title",
            target_price=56000.0
        )

        assert updated.title == "Updated Title"
        assert updated.target_price == 56000.0
        assert updated.updated_at > sample_idea.updated_at

    def test_update_idea_permission_error(self, service, sample_idea):
        """Test updating idea by non-owner."""
        with pytest.raises(PermissionError):
            service.update_idea(
                sample_idea.idea_id,
                "different_trader",
                title="Hacked"
            )

    def test_get_idea_success(self, service, sample_idea):
        """Test getting an idea by ID."""
        idea = service.get_idea(sample_idea.idea_id)
        assert idea.idea_id == sample_idea.idea_id

    def test_get_idea_not_found(self, service):
        """Test getting non-existent idea."""
        with pytest.raises(NotFoundError):
            service.get_idea("nonexistent_id")

    def test_get_ideas_by_trader(self, service):
        """Test getting ideas by trader."""
        idea1 = service.create_idea(
            trader_id="trader123",
            title="Idea 1",
            description="Description 1",
            asset="BTC"
        )
        idea2 = service.create_idea(
            trader_id="trader123",
            title="Idea 2",
            description="Description 2",
            asset="ETH"
        )
        service.create_idea(
            trader_id="trader456",
            title="Idea 3",
            description="Description 3",
            asset="BTC"
        )

        ideas = service.get_ideas_by_trader("trader123")
        assert len(ideas) == 0  # Drafts excluded by default

        ideas = service.get_ideas_by_trader("trader123", include_drafts=True)
        assert len(ideas) == 2
        idea_ids = {i.idea_id for i in ideas}
        assert idea1.idea_id in idea_ids
        assert idea2.idea_id in idea_ids

    def test_get_ideas_by_asset(self, service):
        """Test getting ideas by asset."""
        idea1 = service.create_idea(
            trader_id="trader123",
            title="BTC Idea 1",
            description="Description",
            asset="BTC/USD"
        )
        service.publish_idea(idea1.idea_id, "trader123")

        idea2 = service.create_idea(
            trader_id="trader456",
            title="BTC Idea 2",
            description="Description",
            asset="BTC/USD"
        )
        service.publish_idea(idea2.idea_id, "trader456")

        service.create_idea(
            trader_id="trader789",
            title="ETH Idea",
            description="Description",
            asset="ETH/USD"
        )

        ideas = service.get_ideas_by_asset("BTC/USD")
        assert len(ideas) == 2

    def test_search_ideas(self, service):
        """Test searching ideas."""
        idea1 = service.create_idea(
            trader_id="trader123",
            title="Bitcoin Long Setup",
            description="Bullish pattern",
            asset="BTC/USD",
            tags=["bitcoin", "long"]
        )
        service.publish_idea(idea1.idea_id, "trader123")

        idea2 = service.create_idea(
            trader_id="trader456",
            title="Ethereum Analysis",
            description="Bearish setup",
            asset="ETH/USD",
            tags=["ethereum", "short"]
        )
        service.publish_idea(idea2.idea_id, "trader456")

        # Search by query
        results = service.search_ideas(query="bitcoin")
        assert len(results) == 1
        assert results[0].idea_id == idea1.idea_id

        # Search by asset
        results = service.search_ideas(asset="ETH/USD")
        assert len(results) == 1
        assert results[0].idea_id == idea2.idea_id

        # Search by tags
        results = service.search_ideas(tags=["long"])
        assert len(results) == 1
        assert results[0].idea_id == idea1.idea_id

    def test_like_idea(self, service, sample_idea):
        """Test liking an idea."""
        service.publish_idea(sample_idea.idea_id, "trader123")

        liked = service.like_idea(sample_idea.idea_id, "trader456")
        assert liked.likes_count == 1

        # Like again (should not increase)
        liked = service.like_idea(sample_idea.idea_id, "trader456")
        assert liked.likes_count == 1

    def test_unlike_idea(self, service, sample_idea):
        """Test unliking an idea."""
        service.publish_idea(sample_idea.idea_id, "trader123")
        service.like_idea(sample_idea.idea_id, "trader456")

        unliked = service.unlike_idea(sample_idea.idea_id, "trader456")
        assert unliked.likes_count == 0

        # Unlike again (should stay at 0)
        unliked = service.unlike_idea(sample_idea.idea_id, "trader456")
        assert unliked.likes_count == 0

    def test_add_comment_success(self, service, sample_idea):
        """Test adding a comment."""
        comment = service.add_comment(
            sample_idea.idea_id,
            "trader456",
            "Great analysis!"
        )

        assert comment.comment_id is not None
        assert comment.idea_id == sample_idea.idea_id
        assert comment.trader_id == "trader456"
        assert comment.content == "Great analysis!"

        idea = service.get_idea(sample_idea.idea_id)
        assert idea.comments_count == 1

    def test_add_comment_validation(self, service, sample_idea):
        """Test comment validation."""
        with pytest.raises(ValidationError):
            service.add_comment(sample_idea.idea_id, "trader456", "")

        with pytest.raises(ValidationError):
            service.add_comment(sample_idea.idea_id, "trader456", "x" * 1001)

    def test_add_comment_with_parent(self, service, sample_idea):
        """Test adding a reply comment."""
        parent = service.add_comment(
            sample_idea.idea_id,
            "trader456",
            "Great analysis!"
        )

        reply = service.add_comment(
            sample_idea.idea_id,
            "trader789",
            "I agree!",
            parent_comment_id=parent.comment_id
        )

        assert reply.parent_comment_id == parent.comment_id

    def test_get_comments(self, service, sample_idea):
        """Test getting comments."""
        comment1 = service.add_comment(
            sample_idea.idea_id,
            "trader456",
            "Comment 1"
        )
        comment2 = service.add_comment(
            sample_idea.idea_id,
            "trader789",
            "Comment 2"
        )

        comments = service.get_comments(sample_idea.idea_id)
        assert len(comments) == 2

    def test_get_trending_ideas(self, service):
        """Test getting trending ideas."""
        # Create and publish multiple ideas with different engagement
        idea1 = service.create_idea(
            trader_id="trader123",
            title="Trending Idea",
            description="Description",
            asset="BTC"
        )
        service.publish_idea(idea1.idea_id, "trader123")
        service.like_idea(idea1.idea_id, "trader1")
        service.like_idea(idea1.idea_id, "trader2")
        service.add_comment(idea1.idea_id, "trader3", "Great!")

        idea2 = service.create_idea(
            trader_id="trader456",
            title="Another Idea",
            description="Description",
            asset="ETH"
        )
        service.publish_idea(idea2.idea_id, "trader456")

        trending = service.get_trending_ideas(limit=10)
        assert len(trending) >= 1
        assert trending[0].idea_id == idea1.idea_id  # Most engaged

    def test_increment_views(self, service, sample_idea):
        """Test incrementing view count."""
        initial_views = sample_idea.views_count
        service.increment_views(sample_idea.idea_id)
        assert sample_idea.views_count == initial_views + 1

    def test_share_idea(self, service, sample_idea):
        """Test sharing an idea."""
        initial_shares = sample_idea.shares_count
        service.share_idea(sample_idea.idea_id)
        assert sample_idea.shares_count == initial_shares + 1
