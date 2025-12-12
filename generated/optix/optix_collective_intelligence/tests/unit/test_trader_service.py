"""
Unit tests for TraderService.
"""

import pytest
from datetime import datetime

from src.trader_service import TraderService
from src.models import Trader, FollowType
from src.exceptions import ValidationError, NotFoundError, DuplicateError


class TestTraderService:
    """Test suite for TraderService."""

    @pytest.fixture
    def service(self):
        """Create a TraderService instance."""
        return TraderService()

    @pytest.fixture
    def sample_trader(self, service):
        """Create a sample trader."""
        return service.create_trader(
            username="testuser",
            display_name="Test User",
            bio="Test bio"
        )

    def test_create_trader_success(self, service):
        """Test successful trader creation."""
        trader = service.create_trader(
            username="john_doe",
            display_name="John Doe",
            bio="Professional trader"
        )

        assert trader.trader_id is not None
        assert trader.username == "john_doe"
        assert trader.display_name == "John Doe"
        assert trader.bio == "Professional trader"
        assert trader.followers_count == 0
        assert trader.following_count == 0

    def test_create_trader_invalid_username(self, service):
        """Test trader creation with invalid username."""
        with pytest.raises(ValidationError):
            service.create_trader(username="ab", display_name="Test")

        with pytest.raises(ValidationError):
            service.create_trader(username="a" * 31, display_name="Test")

    def test_create_trader_duplicate_username(self, service, sample_trader):
        """Test trader creation with duplicate username."""
        with pytest.raises(DuplicateError):
            service.create_trader(username="testuser", display_name="Another User")

    def test_get_trader_success(self, service, sample_trader):
        """Test getting a trader by ID."""
        trader = service.get_trader(sample_trader.trader_id)
        assert trader.trader_id == sample_trader.trader_id
        assert trader.username == sample_trader.username

    def test_get_trader_not_found(self, service):
        """Test getting non-existent trader."""
        with pytest.raises(NotFoundError):
            service.get_trader("nonexistent_id")

    def test_get_trader_by_username_success(self, service, sample_trader):
        """Test getting trader by username."""
        trader = service.get_trader_by_username("testuser")
        assert trader.trader_id == sample_trader.trader_id

    def test_get_trader_by_username_not_found(self, service):
        """Test getting trader by non-existent username."""
        with pytest.raises(NotFoundError):
            service.get_trader_by_username("nonexistent")

    def test_update_trader_success(self, service, sample_trader):
        """Test updating trader profile."""
        updated = service.update_trader(
            sample_trader.trader_id,
            display_name="Updated Name",
            bio="Updated bio",
            verified=True
        )

        assert updated.display_name == "Updated Name"
        assert updated.bio == "Updated bio"
        assert updated.verified is True

    def test_update_trader_username(self, service, sample_trader):
        """Test updating trader username."""
        updated = service.update_trader(
            sample_trader.trader_id,
            username="newusername"
        )

        assert updated.username == "newusername"
        trader = service.get_trader_by_username("newusername")
        assert trader.trader_id == sample_trader.trader_id

    def test_follow_trader_success(self, service):
        """Test creating a follow relationship."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        relationship = service.follow_trader(trader1.trader_id, trader2.trader_id)

        assert relationship.follower_id == trader1.trader_id
        assert relationship.following_id == trader2.trader_id
        assert relationship.follow_type == FollowType.FOLLOW
        assert relationship.active is True

        # Check counts updated
        assert service.get_trader(trader1.trader_id).following_count == 1
        assert service.get_trader(trader2.trader_id).followers_count == 1

    def test_follow_self(self, service, sample_trader):
        """Test following yourself."""
        with pytest.raises(ValidationError):
            service.follow_trader(sample_trader.trader_id, sample_trader.trader_id)

    def test_follow_already_following(self, service):
        """Test following someone already followed."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        service.follow_trader(trader1.trader_id, trader2.trader_id)

        with pytest.raises(ValidationError):
            service.follow_trader(trader1.trader_id, trader2.trader_id)

    def test_unfollow_trader_success(self, service):
        """Test unfollowing a trader."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        service.follow_trader(trader1.trader_id, trader2.trader_id)
        result = service.unfollow_trader(trader1.trader_id, trader2.trader_id)

        assert result is True
        assert service.get_trader(trader1.trader_id).following_count == 0
        assert service.get_trader(trader2.trader_id).followers_count == 0

    def test_unfollow_not_following(self, service):
        """Test unfollowing someone not followed."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        result = service.unfollow_trader(trader1.trader_id, trader2.trader_id)
        assert result is False

    def test_get_following(self, service):
        """Test getting list of following."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")
        trader3 = service.create_trader(username="user3", display_name="User 3")

        service.follow_trader(trader1.trader_id, trader2.trader_id)
        service.follow_trader(trader1.trader_id, trader3.trader_id)

        following = service.get_following(trader1.trader_id)
        assert len(following) == 2
        following_ids = {t.trader_id for t in following}
        assert trader2.trader_id in following_ids
        assert trader3.trader_id in following_ids

    def test_get_followers(self, service):
        """Test getting list of followers."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")
        trader3 = service.create_trader(username="user3", display_name="User 3")

        service.follow_trader(trader2.trader_id, trader1.trader_id)
        service.follow_trader(trader3.trader_id, trader1.trader_id)

        followers = service.get_followers(trader1.trader_id)
        assert len(followers) == 2
        follower_ids = {t.trader_id for t in followers}
        assert trader2.trader_id in follower_ids
        assert trader3.trader_id in follower_ids

    def test_is_following(self, service):
        """Test checking if following."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        assert service.is_following(trader1.trader_id, trader2.trader_id) is False

        service.follow_trader(trader1.trader_id, trader2.trader_id)
        assert service.is_following(trader1.trader_id, trader2.trader_id) is True

    def test_search_traders_by_query(self, service):
        """Test searching traders by query."""
        service.create_trader(username="john_doe", display_name="John Doe")
        service.create_trader(username="jane_smith", display_name="Jane Smith")
        service.create_trader(username="bob_jones", display_name="Bob Jones")

        results = service.search_traders(query="john")
        assert len(results) == 1
        assert results[0].username == "john_doe"

    def test_search_traders_by_reputation(self, service):
        """Test searching traders by reputation."""
        t1 = service.create_trader(username="user1", display_name="User 1")
        t2 = service.create_trader(username="user2", display_name="User 2")

        service.update_trader(t1.trader_id, reputation_score=80.0)
        service.update_trader(t2.trader_id, reputation_score=60.0)

        results = service.search_traders(min_reputation=70.0)
        assert len(results) == 1
        assert results[0].trader_id == t1.trader_id

    def test_search_traders_verified_only(self, service):
        """Test searching for verified traders only."""
        t1 = service.create_trader(username="user1", display_name="User 1")
        service.create_trader(username="user2", display_name="User 2")

        service.update_trader(t1.trader_id, verified=True)

        results = service.search_traders(verified_only=True)
        assert len(results) == 1
        assert results[0].trader_id == t1.trader_id

    def test_get_follow_relationship(self, service):
        """Test getting follow relationship."""
        trader1 = service.create_trader(username="user1", display_name="User 1")
        trader2 = service.create_trader(username="user2", display_name="User 2")

        service.follow_trader(trader1.trader_id, trader2.trader_id, FollowType.COPY)

        relationship = service.get_follow_relationship(
            trader1.trader_id,
            trader2.trader_id
        )

        assert relationship is not None
        assert relationship.follower_id == trader1.trader_id
        assert relationship.following_id == trader2.trader_id
        assert relationship.follow_type == FollowType.COPY
