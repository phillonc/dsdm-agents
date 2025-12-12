"""
Copy Trading Service for managing copy trading functionality.

This service handles automatic trade replication from followed traders.
"""

from datetime import datetime
from typing import List, Dict, Optional, Callable, Any
from .models import Trade, TradeType, TradeStatus, FollowRelationship, FollowType
from .trader_service import TraderService
from .exceptions import ValidationError, NotFoundError, PermissionError


class CopyTradingService:
    """Service for managing copy trading."""

    def __init__(self, trader_service: TraderService):
        """
        Initialize the copy trading service.

        Args:
            trader_service: TraderService instance
        """
        self.trader_service = trader_service
        self._copy_trades: Dict[str, List[str]] = {}  # source_trade_id -> [copy_trade_ids]
        self._execution_callback: Optional[Callable] = None

    def set_execution_callback(self, callback: Callable[[Trade], Trade]):
        """
        Set callback function for executing trades.

        Args:
            callback: Function that executes a trade and returns the result
        """
        self._execution_callback = callback

    def enable_copy_trading(
        self,
        follower_id: str,
        following_id: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> FollowRelationship:
        """
        Enable copy trading for a follow relationship.

        Args:
            follower_id: ID of the follower (copier)
            following_id: ID of the trader being copied
            settings: Copy trading settings

        Returns:
            Updated FollowRelationship object

        Raises:
            NotFoundError: If relationship doesn't exist
            ValidationError: If settings are invalid
        """
        # Get or create follow relationship
        relationship = self.trader_service.get_follow_relationship(
            follower_id,
            following_id
        )

        if not relationship:
            relationship = self.trader_service.follow_trader(
                follower_id,
                following_id,
                follow_type=FollowType.COPY
            )
        else:
            relationship.follow_type = FollowType.COPY

        # Validate and set copy settings
        default_settings = {
            "enabled": True,
            "copy_percentage": 100.0,  # Percentage of capital to allocate
            "max_position_size": None,  # Maximum position size
            "min_position_size": None,  # Minimum position size
            "copy_stop_loss": True,
            "copy_take_profit": True,
            "slippage_tolerance": 0.5,  # Max slippage percentage
            "asset_whitelist": None,  # List of assets to copy (None = all)
            "asset_blacklist": None,  # List of assets to exclude
            "max_concurrent_positions": None,
            "reverse_trades": False,  # Reverse trade direction
        }

        if settings:
            default_settings.update(settings)

        self._validate_copy_settings(default_settings)
        relationship.copy_settings = default_settings

        return relationship

    def disable_copy_trading(
        self,
        follower_id: str,
        following_id: str,
        close_positions: bool = False
    ) -> bool:
        """
        Disable copy trading for a follow relationship.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being copied
            close_positions: Whether to close existing copy positions

        Returns:
            True if disabled successfully

        Raises:
            NotFoundError: If relationship doesn't exist
        """
        relationship = self.trader_service.get_follow_relationship(
            follower_id,
            following_id
        )

        if not relationship:
            raise NotFoundError("Follow relationship not found")

        if relationship.copy_settings:
            relationship.copy_settings["enabled"] = False

        # TODO: Implement position closing if close_positions is True

        return True

    def process_trade(self, source_trade: Trade) -> List[Trade]:
        """
        Process a trade and create copy trades for followers.

        Args:
            source_trade: Original trade from the leader

        Returns:
            List of created copy Trade objects
        """
        if not self._execution_callback:
            raise ValidationError("Execution callback not set")

        # Get followers who are copying this trader
        followers = self.trader_service.get_followers(source_trade.trader_id)

        copy_trades = []

        for follower in followers:
            relationship = self.trader_service.get_follow_relationship(
                follower.trader_id,
                source_trade.trader_id
            )

            if not relationship or relationship.follow_type != FollowType.COPY:
                continue

            settings = relationship.copy_settings
            if not settings or not settings.get("enabled", False):
                continue

            # Check if trade should be copied based on settings
            if not self._should_copy_trade(source_trade, settings):
                continue

            # Create copy trade
            copy_trade = self._create_copy_trade(
                source_trade,
                follower.trader_id,
                settings
            )

            if copy_trade:
                # Execute the copy trade
                executed_trade = self._execution_callback(copy_trade)
                copy_trades.append(executed_trade)

                # Track the copy relationship
                if source_trade.trade_id not in self._copy_trades:
                    self._copy_trades[source_trade.trade_id] = []
                self._copy_trades[source_trade.trade_id].append(executed_trade.trade_id)

        return copy_trades

    def get_copy_trades(self, source_trade_id: str) -> List[str]:
        """
        Get copy trade IDs for a source trade.

        Args:
            source_trade_id: ID of the source trade

        Returns:
            List of copy trade IDs
        """
        return self._copy_trades.get(source_trade_id, [])

    def update_copy_settings(
        self,
        follower_id: str,
        following_id: str,
        settings: Dict[str, Any]
    ) -> FollowRelationship:
        """
        Update copy trading settings.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being copied
            settings: New settings

        Returns:
            Updated FollowRelationship object

        Raises:
            NotFoundError: If relationship doesn't exist
            ValidationError: If settings are invalid
        """
        self._validate_copy_settings(settings)
        return self.trader_service.update_copy_settings(
            follower_id,
            following_id,
            settings
        )

    def get_copy_statistics(
        self,
        follower_id: str,
        following_id: str
    ) -> Dict[str, Any]:
        """
        Get copy trading statistics for a relationship.

        Args:
            follower_id: ID of the follower
            following_id: ID of the trader being copied

        Returns:
            Dictionary with statistics
        """
        # TODO: Implement statistics calculation
        return {
            "total_copied_trades": 0,
            "successful_copies": 0,
            "failed_copies": 0,
            "total_profit_loss": 0.0,
            "average_slippage": 0.0
        }

    def _should_copy_trade(
        self,
        trade: Trade,
        settings: Dict[str, Any]
    ) -> bool:
        """
        Determine if a trade should be copied based on settings.

        Args:
            trade: Trade to evaluate
            settings: Copy trading settings

        Returns:
            True if trade should be copied
        """
        # Check whitelist
        if settings.get("asset_whitelist"):
            if trade.asset not in settings["asset_whitelist"]:
                return False

        # Check blacklist
        if settings.get("asset_blacklist"):
            if trade.asset in settings["asset_blacklist"]:
                return False

        # Check position size limits
        if settings.get("max_position_size"):
            if trade.quantity > settings["max_position_size"]:
                return False

        if settings.get("min_position_size"):
            if trade.quantity < settings["min_position_size"]:
                return False

        # TODO: Check max concurrent positions

        return True

    def _create_copy_trade(
        self,
        source_trade: Trade,
        follower_id: str,
        settings: Dict[str, Any]
    ) -> Optional[Trade]:
        """
        Create a copy trade based on source trade and settings.

        Args:
            source_trade: Original trade
            follower_id: ID of the follower
            settings: Copy trading settings

        Returns:
            Copy Trade object or None
        """
        # Calculate position size based on copy percentage
        copy_percentage = settings.get("copy_percentage", 100.0) / 100.0
        quantity = source_trade.quantity * copy_percentage

        # Apply position size limits
        if settings.get("max_position_size"):
            quantity = min(quantity, settings["max_position_size"])

        if settings.get("min_position_size"):
            if quantity < settings["min_position_size"]:
                return None  # Don't copy if below minimum

        # Determine trade type (reverse if enabled)
        trade_type = source_trade.trade_type
        if settings.get("reverse_trades", False):
            trade_type = self._reverse_trade_type(trade_type)

        # Create copy trade
        copy_trade = Trade(
            trader_id=follower_id,
            idea_id=source_trade.idea_id,
            asset=source_trade.asset,
            trade_type=trade_type,
            entry_price=source_trade.entry_price,
            quantity=quantity,
            status=TradeStatus.PENDING,
            notes=f"Copy of trade {source_trade.trade_id}"
        )

        copy_trade.metadata = {
            "copy_trade": True,
            "source_trade_id": source_trade.trade_id,
            "source_trader_id": source_trade.trader_id,
            "copy_settings": settings
        }

        return copy_trade

    def _reverse_trade_type(self, trade_type: TradeType) -> TradeType:
        """Reverse a trade type."""
        reverse_map = {
            TradeType.BUY: TradeType.SELL,
            TradeType.SELL: TradeType.BUY,
            TradeType.SHORT: TradeType.COVER,
            TradeType.COVER: TradeType.SHORT
        }
        return reverse_map.get(trade_type, trade_type)

    def _validate_copy_settings(self, settings: Dict[str, Any]):
        """
        Validate copy trading settings.

        Args:
            settings: Settings to validate

        Raises:
            ValidationError: If settings are invalid
        """
        if "copy_percentage" in settings:
            if not 0 < settings["copy_percentage"] <= 100:
                raise ValidationError("Copy percentage must be between 0 and 100")

        if "slippage_tolerance" in settings:
            if settings["slippage_tolerance"] < 0:
                raise ValidationError("Slippage tolerance cannot be negative")

        if settings.get("max_position_size") and settings.get("min_position_size"):
            if settings["max_position_size"] < settings["min_position_size"]:
                raise ValidationError(
                    "Maximum position size cannot be less than minimum"
                )
