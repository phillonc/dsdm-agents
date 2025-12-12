"""
Trade Idea Service for managing trade ideas and discussions.

This service handles creation, sharing, and interaction with trade ideas.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import TradeIdea, Comment, IdeaStatus, SentimentType
from .exceptions import ValidationError, NotFoundError, PermissionError


class TradeIdeaService:
    """Service for managing trade ideas."""

    def __init__(self):
        """Initialize the trade idea service."""
        self._ideas: Dict[str, TradeIdea] = {}
        self._comments: Dict[str, Comment] = {}
        self._likes: Dict[str, set] = {}  # idea_id -> set of trader_ids
        self._comment_likes: Dict[str, set] = {}  # comment_id -> set of trader_ids

    def create_idea(
        self,
        trader_id: str,
        title: str,
        description: str,
        asset: str,
        **kwargs
    ) -> TradeIdea:
        """
        Create a new trade idea.

        Args:
            trader_id: ID of the trader creating the idea
            title: Title of the trade idea
            description: Detailed description
            asset: Asset symbol
            **kwargs: Additional idea parameters

        Returns:
            Created TradeIdea object

        Raises:
            ValidationError: If required fields are invalid
        """
        if not trader_id or not title or not description or not asset:
            raise ValidationError("Trader ID, title, description, and asset are required")

        if len(title) < 5 or len(title) > 200:
            raise ValidationError("Title must be between 5 and 200 characters")

        if len(description) < 10:
            raise ValidationError("Description must be at least 10 characters")

        idea = TradeIdea(
            trader_id=trader_id,
            title=title,
            description=description,
            asset=asset,
            **kwargs
        )

        self._ideas[idea.idea_id] = idea
        self._likes[idea.idea_id] = set()
        return idea

    def publish_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """
        Publish a draft trade idea.

        Args:
            idea_id: ID of the idea to publish
            trader_id: ID of the trader (must be the owner)

        Returns:
            Updated TradeIdea object

        Raises:
            NotFoundError: If idea doesn't exist
            PermissionError: If trader is not the owner
            ValidationError: If idea is not in draft status
        """
        idea = self.get_idea(idea_id)

        if idea.trader_id != trader_id:
            raise PermissionError("Only the owner can publish this idea")

        if idea.status != IdeaStatus.DRAFT:
            raise ValidationError("Only draft ideas can be published")

        idea.status = IdeaStatus.PUBLISHED
        idea.published_at = datetime.utcnow()
        idea.updated_at = datetime.utcnow()

        return idea

    def update_idea(
        self,
        idea_id: str,
        trader_id: str,
        **updates
    ) -> TradeIdea:
        """
        Update a trade idea.

        Args:
            idea_id: ID of the idea to update
            trader_id: ID of the trader (must be the owner)
            **updates: Fields to update

        Returns:
            Updated TradeIdea object

        Raises:
            NotFoundError: If idea doesn't exist
            PermissionError: If trader is not the owner
        """
        idea = self.get_idea(idea_id)

        if idea.trader_id != trader_id:
            raise PermissionError("Only the owner can update this idea")

        for key, value in updates.items():
            if hasattr(idea, key):
                setattr(idea, key, value)

        idea.updated_at = datetime.utcnow()
        return idea

    def get_idea(self, idea_id: str) -> TradeIdea:
        """
        Get a trade idea by ID.

        Args:
            idea_id: ID of the idea

        Returns:
            TradeIdea object

        Raises:
            NotFoundError: If idea doesn't exist
        """
        if idea_id not in self._ideas:
            raise NotFoundError(f"Trade idea {idea_id} not found")
        return self._ideas[idea_id]

    def get_ideas_by_trader(
        self,
        trader_id: str,
        include_drafts: bool = False
    ) -> List[TradeIdea]:
        """
        Get all ideas by a specific trader.

        Args:
            trader_id: ID of the trader
            include_drafts: Whether to include draft ideas

        Returns:
            List of TradeIdea objects
        """
        ideas = [
            idea for idea in self._ideas.values()
            if idea.trader_id == trader_id
        ]

        if not include_drafts:
            ideas = [
                idea for idea in ideas
                if idea.status != IdeaStatus.DRAFT
            ]

        return sorted(ideas, key=lambda x: x.created_at, reverse=True)

    def get_ideas_by_asset(self, asset: str) -> List[TradeIdea]:
        """
        Get all published ideas for a specific asset.

        Args:
            asset: Asset symbol

        Returns:
            List of TradeIdea objects
        """
        ideas = [
            idea for idea in self._ideas.values()
            if idea.asset == asset and idea.status == IdeaStatus.PUBLISHED
        ]
        return sorted(ideas, key=lambda x: x.created_at, reverse=True)

    def search_ideas(
        self,
        query: Optional[str] = None,
        asset: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sentiment: Optional[SentimentType] = None,
        limit: int = 50
    ) -> List[TradeIdea]:
        """
        Search for trade ideas.

        Args:
            query: Text search query
            asset: Filter by asset
            tags: Filter by tags
            sentiment: Filter by sentiment
            limit: Maximum number of results

        Returns:
            List of matching TradeIdea objects
        """
        results = [
            idea for idea in self._ideas.values()
            if idea.status == IdeaStatus.PUBLISHED
        ]

        if asset:
            results = [idea for idea in results if idea.asset == asset]

        if sentiment:
            results = [idea for idea in results if idea.sentiment == sentiment]

        if tags:
            results = [
                idea for idea in results
                if any(tag in idea.tags for tag in tags)
            ]

        if query:
            query_lower = query.lower()
            results = [
                idea for idea in results
                if query_lower in idea.title.lower()
                or query_lower in idea.description.lower()
            ]

        results = sorted(results, key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def like_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """
        Like a trade idea.

        Args:
            idea_id: ID of the idea
            trader_id: ID of the trader liking the idea

        Returns:
            Updated TradeIdea object

        Raises:
            NotFoundError: If idea doesn't exist
        """
        idea = self.get_idea(idea_id)

        if trader_id not in self._likes[idea_id]:
            self._likes[idea_id].add(trader_id)
            idea.likes_count += 1

        return idea

    def unlike_idea(self, idea_id: str, trader_id: str) -> TradeIdea:
        """
        Unlike a trade idea.

        Args:
            idea_id: ID of the idea
            trader_id: ID of the trader unliking the idea

        Returns:
            Updated TradeIdea object

        Raises:
            NotFoundError: If idea doesn't exist
        """
        idea = self.get_idea(idea_id)

        if trader_id in self._likes[idea_id]:
            self._likes[idea_id].remove(trader_id)
            idea.likes_count = max(0, idea.likes_count - 1)

        return idea

    def add_comment(
        self,
        idea_id: str,
        trader_id: str,
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> Comment:
        """
        Add a comment to a trade idea.

        Args:
            idea_id: ID of the idea
            trader_id: ID of the commenting trader
            content: Comment content
            parent_comment_id: Optional parent comment for threading

        Returns:
            Created Comment object

        Raises:
            NotFoundError: If idea doesn't exist
            ValidationError: If content is invalid
        """
        idea = self.get_idea(idea_id)

        if not content or len(content.strip()) < 1:
            raise ValidationError("Comment content cannot be empty")

        if len(content) > 1000:
            raise ValidationError("Comment content cannot exceed 1000 characters")

        if parent_comment_id and parent_comment_id not in self._comments:
            raise NotFoundError(f"Parent comment {parent_comment_id} not found")

        comment = Comment(
            idea_id=idea_id,
            trader_id=trader_id,
            content=content,
            parent_comment_id=parent_comment_id
        )

        self._comments[comment.comment_id] = comment
        self._comment_likes[comment.comment_id] = set()
        idea.comments_count += 1

        return comment

    def get_comments(
        self,
        idea_id: str,
        parent_comment_id: Optional[str] = None
    ) -> List[Comment]:
        """
        Get comments for a trade idea.

        Args:
            idea_id: ID of the idea
            parent_comment_id: Optional parent comment to filter by

        Returns:
            List of Comment objects
        """
        comments = [
            comment for comment in self._comments.values()
            if comment.idea_id == idea_id
            and comment.parent_comment_id == parent_comment_id
        ]
        return sorted(comments, key=lambda x: x.created_at)

    def get_trending_ideas(self, limit: int = 10) -> List[TradeIdea]:
        """
        Get trending trade ideas based on engagement.

        Args:
            limit: Maximum number of results

        Returns:
            List of trending TradeIdea objects
        """
        published_ideas = [
            idea for idea in self._ideas.values()
            if idea.status == IdeaStatus.PUBLISHED
        ]

        # Calculate engagement score
        def engagement_score(idea: TradeIdea) -> float:
            age_hours = (datetime.utcnow() - idea.published_at).total_seconds() / 3600
            age_factor = 1 / (age_hours + 2)  # Decay factor
            return (
                idea.likes_count * 2 +
                idea.comments_count * 3 +
                idea.shares_count * 5 +
                idea.views_count * 0.1
            ) * age_factor

        trending = sorted(
            published_ideas,
            key=engagement_score,
            reverse=True
        )
        return trending[:limit]

    def increment_views(self, idea_id: str) -> TradeIdea:
        """
        Increment view count for an idea.

        Args:
            idea_id: ID of the idea

        Returns:
            Updated TradeIdea object
        """
        idea = self.get_idea(idea_id)
        idea.views_count += 1
        return idea

    def share_idea(self, idea_id: str) -> TradeIdea:
        """
        Increment share count for an idea.

        Args:
            idea_id: ID of the idea

        Returns:
            Updated TradeIdea object
        """
        idea = self.get_idea(idea_id)
        idea.shares_count += 1
        return idea
