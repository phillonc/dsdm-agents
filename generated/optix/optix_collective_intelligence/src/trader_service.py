"""
Trader Service for managing trader profiles and relationships.

This service handles trader management, following, and social connections.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import Trader, FollowRelationship, FollowType
from .exceptions import ValidationError, NotFoundError, DuplicateError


class TraderService:
    """Service for managing traders and relationships."""

    def __init__(self):
        """Initialize the trader service."""
        self._traders: Dict[str, Trader] = {}
        self._username_index: Dict[str, str] = {}  # username -> trader_id
        self._relationships: Dict[str, FollowRelationship] = {}
        self._following_index: Dict[str, set] = {}  # follower_id -> set of following_ids
        self._followers_index: Dict[str, set] = {}  # following_id -> set of follower_ids

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

        Raises:
            ValidationError: If username is invalid
            DuplicateError: If username already exists
        """
        if not username or len(username) < 3 or len(username) > 30:
            raise ValidationError("Username must be between 3 and 30 characters")

        if not username.isalnum() and '_' not in username:
            raise ValidationError("Username can only contain letters, numbers, and underscores")

        if username.lower() in self._username_index:
            raise DuplicateError(f"Username {username} already exists")

        trader = Trader(
            username=username,
            display_name=display_name or username,
            **kwargs
        )

        self._traders[trader.trader_id] = trader
        self._username_index[username.lower()] = trader.trader_id
        self._following_index[trader.trader_id] = set()
        self._followers_index[trader.trader_id] = set()

        return trader

    def get_trader(self, trader_id: str) -> Trader:
        """
        Get a trader by ID.

        Args:
            trader_id: ID of the trader

        Returns:
            Trader object

        Raises:
            NotFoundError: If trader doesn't exist
        """
        if trader_id not in self._traders:
            raise NotFoundError(f"Trader {trader_id} not found")
        return self._traders[trader_id]

    def get_trader_by_username(self, username: str) -> Trader:
        """
        Get a trader by username.

        Args:
            username: Username of the trader

        Returns:
            Trader object

        Raises:
            NotFoundError: If trader doesn't exist
        """
        trader_id = self._username_index.get(username.lower())
        if not trader_id:
            raise NotFoundError(f"Trader with username {username} not found")
        return self._traders[trader_id]

    def update_trader(
        self,
        trader_id: str,
        **updates
    ) -> Trader:
        """
        Update a trader profile.

        Args:
            trader_id: ID of the trader
            **updates: Fields to update

        Returns:
            Updated Trader object

        Raises:
            NotFoundError: If trader doesn't exist
            ValidationError: If updates are invalid
        """
        trader = self.get_trader(trader_id)

        if 'username' in updates and updates['username'] != trader.username:
            new_username = updates['username']
            if new_username.lower() in self._username_index:
                raise ValidationError("Username already taken")
            del self._username_index[trader.username.lower()]
            self._username_index[new_username.lower()] = trader_id

        for key, value in updates.items():
            if hasattr(trader, key):
                setattr(trader, key, value)

        return trader

    def follow_trader(
        self,
        follower_id: str,
        following_id: str,
        follow_type: FollowType = FollowType.FOLLOW,
        copy_settings: Optional[Dict[str, Any]] = None
    ) -> FollowRelationship:
        """
        Create a follow relationship.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being followed
            follow_type: Type of follow (FOLLOW or COPY)
            copy_settings: Optional copy trading settings

        Returns:
            Created FollowRelationship object

        Raises:
            NotFoundError: If either trader doesn't exist
            ValidationError: If trying to follow self or already following
        """
        if follower_id == following_id:
            raise ValidationError("Cannot follow yourself")

        # Verify both traders exist
        self.get_trader(follower_id)
        self.get_trader(following_id)

        # Check if already following
        if following_id in self._following_index.get(follower_id, set()):
            raise ValidationError("Already following this trader")

        relationship = FollowRelationship(
            follower_id=follower_id,
            following_id=following_id,
            follow_type=follow_type,
            copy_settings=copy_settings
        )

        self._relationships[relationship.relationship_id] = relationship
        self._following_index[follower_id].add(following_id)
        self._followers_index[following_id].add(follower_id)

        # Update counts
        follower = self._traders[follower_id]
        following = self._traders[following_id]
        follower.following_count += 1
        following.followers_count += 1

        return relationship

    def unfollow_trader(
        self,
        follower_id: str,
        following_id: str
    ) -> bool:
        """
        Remove a follow relationship.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being unfollowed

        Returns:
            True if unfollowed, False if wasn't following

        Raises:
            NotFoundError: If either trader doesn't exist
        """
        self.get_trader(follower_id)
        self.get_trader(following_id)

        if following_id not in self._following_index.get(follower_id, set()):
            return False

        # Find and deactivate relationship
        for rel in self._relationships.values():
            if (rel.follower_id == follower_id and
                rel.following_id == following_id and
                rel.active):
                rel.active = False
                break

        self._following_index[follower_id].discard(following_id)
        self._followers_index[following_id].discard(follower_id)

        # Update counts
        follower = self._traders[follower_id]
        following = self._traders[following_id]
        follower.following_count = max(0, follower.following_count - 1)
        following.followers_count = max(0, following.followers_count - 1)

        return True

    def get_following(self, trader_id: str) -> List[Trader]:
        """
        Get list of traders that a trader is following.

        Args:
            trader_id: ID of the trader

        Returns:
            List of Trader objects
        """
        self.get_trader(trader_id)
        following_ids = self._following_index.get(trader_id, set())
        return [self._traders[fid] for fid in following_ids if fid in self._traders]

    def get_followers(self, trader_id: str) -> List[Trader]:
        """
        Get list of traders following a trader.

        Args:
            trader_id: ID of the trader

        Returns:
            List of Trader objects
        """
        self.get_trader(trader_id)
        follower_ids = self._followers_index.get(trader_id, set())
        return [self._traders[fid] for fid in follower_ids if fid in self._traders]

    def is_following(self, follower_id: str, following_id: str) -> bool:
        """
        Check if a trader is following another trader.

        Args:
            follower_id: ID of the potential follower
            following_id: ID of the trader being checked

        Returns:
            True if following, False otherwise
        """
        return following_id in self._following_index.get(follower_id, set())

    def get_follow_relationship(
        self,
        follower_id: str,
        following_id: str
    ) -> Optional[FollowRelationship]:
        """
        Get the follow relationship between two traders.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being followed

        Returns:
            FollowRelationship object or None
        """
        for rel in self._relationships.values():
            if (rel.follower_id == follower_id and
                rel.following_id == following_id and
                rel.active):
                return rel
        return None

    def update_copy_settings(
        self,
        follower_id: str,
        following_id: str,
        copy_settings: Dict[str, Any]
    ) -> FollowRelationship:
        """
        Update copy trading settings for a follow relationship.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being followed
            copy_settings: New copy settings

        Returns:
            Updated FollowRelationship object

        Raises:
            NotFoundError: If relationship doesn't exist
        """
        relationship = self.get_follow_relationship(follower_id, following_id)
        if not relationship:
            raise NotFoundError("Follow relationship not found")

        relationship.copy_settings = copy_settings
        return relationship

    def search_traders(
        self,
        query: Optional[str] = None,
        min_reputation: Optional[float] = None,
        verified_only: bool = False,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Trader]:
        """
        Search for traders.

        Args:
            query: Text search query
            min_reputation: Minimum reputation score
            verified_only: Only return verified traders
            tags: Filter by tags
            limit: Maximum number of results

        Returns:
            List of matching Trader objects
        """
        results = list(self._traders.values())

        if verified_only:
            results = [t for t in results if t.verified]

        if min_reputation is not None:
            results = [t for t in results if t.reputation_score >= min_reputation]

        if tags:
            results = [
                t for t in results
                if any(tag in t.tags for tag in tags)
            ]

        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.username.lower()
                or query_lower in t.display_name.lower()
                or query_lower in t.bio.lower()
            ]

        results = sorted(results, key=lambda x: x.reputation_score, reverse=True)
        return results[:limit]

    def get_all_traders(self) -> List[Trader]:
        """
        Get all traders.

        Returns:
            List of all Trader objects
        """
        return list(self._traders.values())
