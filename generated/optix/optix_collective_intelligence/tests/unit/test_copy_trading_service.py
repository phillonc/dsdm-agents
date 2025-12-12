"""
Unit tests for CopyTradingService.
"""

import pytest

from src.copy_trading_service import CopyTradingService
from src.trader_service import TraderService
from src.models import Trade, TradeType, TradeStatus, FollowType
from src.exceptions import ValidationError, NotFoundError


class TestCopyTradingService:
    """Test suite for CopyTradingService."""

    @pytest.fixture
    def trader_service(self):
        """Create TraderService instance."""
        return TraderService()

    @pytest.fixture
    def service(self, trader_service):
        """Create CopyTradingService instance."""
        return CopyTradingService(trader_service)

    @pytest.fixture
    def traders(self, trader_service):
        """Create sample traders."""
        leader = trader_service.create_trader(
            username="leader",
            display_name="Leader Trader"
        )
        follower = trader_service.create_trader(
            username="follower",
            display_name="Follower Trader"
        )
        return {"leader": leader, "follower": follower}

    def test_enable_copy_trading(self, service, traders):
        """Test enabling copy trading."""
        settings = {
            "enabled": True,
            "copy_percentage": 50.0,
            "max_position_size": 1000.0
        }

        relationship = service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id,
            settings
        )

        assert relationship is not None
        assert relationship.follow_type == FollowType.COPY
        assert relationship.copy_settings["enabled"] is True
        assert relationship.copy_settings["copy_percentage"] == 50.0

    def test_enable_copy_trading_defaults(self, service, traders):
        """Test enabling copy trading with default settings."""
        relationship = service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        assert relationship.copy_settings["enabled"] is True
        assert relationship.copy_settings["copy_percentage"] == 100.0
        assert relationship.copy_settings["copy_stop_loss"] is True

    def test_enable_copy_trading_validation(self, service, traders):
        """Test copy trading settings validation."""
        invalid_settings = {
            "copy_percentage": 150.0  # Invalid: > 100
        }

        with pytest.raises(ValidationError):
            service.enable_copy_trading(
                traders["follower"].trader_id,
                traders["leader"].trader_id,
                invalid_settings
            )

    def test_disable_copy_trading(self, service, traders):
        """Test disabling copy trading."""
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        result = service.disable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        assert result is True

        relationship = service.trader_service.get_follow_relationship(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )
        assert relationship.copy_settings["enabled"] is False

    def test_should_copy_trade_whitelist(self, service, traders):
        """Test trade copying with asset whitelist."""
        settings = {
            "asset_whitelist": ["BTC/USD", "ETH/USD"]
        }

        trade_btc = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        trade_xrp = Trade(
            trader_id=traders["leader"].trader_id,
            asset="XRP/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        assert service._should_copy_trade(trade_btc, settings) is True
        assert service._should_copy_trade(trade_xrp, settings) is False

    def test_should_copy_trade_blacklist(self, service, traders):
        """Test trade copying with asset blacklist."""
        settings = {
            "asset_blacklist": ["DOGE/USD"]
        }

        trade_btc = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        trade_doge = Trade(
            trader_id=traders["leader"].trader_id,
            asset="DOGE/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        assert service._should_copy_trade(trade_btc, settings) is True
        assert service._should_copy_trade(trade_doge, settings) is False

    def test_should_copy_trade_position_limits(self, service, traders):
        """Test trade copying with position size limits."""
        settings = {
            "max_position_size": 10.0,
            "min_position_size": 1.0
        }

        trade_valid = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=5.0
        )

        trade_too_large = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=15.0
        )

        trade_too_small = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=0.5
        )

        assert service._should_copy_trade(trade_valid, settings) is True
        assert service._should_copy_trade(trade_too_large, settings) is False
        assert service._should_copy_trade(trade_too_small, settings) is False

    def test_create_copy_trade(self, service, traders):
        """Test creating a copy trade."""
        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            entry_price=50000.0,
            quantity=2.0
        )

        settings = {
            "copy_percentage": 50.0
        }

        copy_trade = service._create_copy_trade(
            source_trade,
            traders["follower"].trader_id,
            settings
        )

        assert copy_trade is not None
        assert copy_trade.trader_id == traders["follower"].trader_id
        assert copy_trade.asset == source_trade.asset
        assert copy_trade.trade_type == source_trade.trade_type
        assert copy_trade.quantity == 1.0  # 50% of 2.0
        assert copy_trade.metadata["copy_trade"] is True
        assert copy_trade.metadata["source_trade_id"] == source_trade.trade_id

    def test_create_copy_trade_with_limits(self, service, traders):
        """Test creating copy trade with position limits."""
        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=10.0
        )

        settings = {
            "copy_percentage": 100.0,
            "max_position_size": 5.0
        }

        copy_trade = service._create_copy_trade(
            source_trade,
            traders["follower"].trader_id,
            settings
        )

        assert copy_trade.quantity == 5.0  # Capped at max

    def test_create_copy_trade_below_minimum(self, service, traders):
        """Test that trades below minimum are not copied."""
        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        settings = {
            "copy_percentage": 10.0,  # Results in 0.1
            "min_position_size": 0.5
        }

        copy_trade = service._create_copy_trade(
            source_trade,
            traders["follower"].trader_id,
            settings
        )

        assert copy_trade is None  # Below minimum

    def test_create_copy_trade_reverse(self, service, traders):
        """Test creating reversed copy trade."""
        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        settings = {
            "reverse_trades": True
        }

        copy_trade = service._create_copy_trade(
            source_trade,
            traders["follower"].trader_id,
            settings
        )

        assert copy_trade.trade_type == TradeType.SELL  # Reversed

    def test_reverse_trade_type(self, service):
        """Test trade type reversal."""
        assert service._reverse_trade_type(TradeType.BUY) == TradeType.SELL
        assert service._reverse_trade_type(TradeType.SELL) == TradeType.BUY
        assert service._reverse_trade_type(TradeType.SHORT) == TradeType.COVER
        assert service._reverse_trade_type(TradeType.COVER) == TradeType.SHORT

    def test_process_trade(self, service, traders):
        """Test processing a trade for copy trading."""
        # Enable copy trading
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        # Set execution callback
        executed_trades = []
        def mock_execution(trade):
            executed_trades.append(trade)
            return trade

        service.set_execution_callback(mock_execution)

        # Create source trade
        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        # Process trade
        copy_trades = service.process_trade(source_trade)

        assert len(copy_trades) == 1
        assert copy_trades[0].trader_id == traders["follower"].trader_id
        assert source_trade.trade_id in service._copy_trades

    def test_process_trade_no_callback(self, service, traders):
        """Test processing trade without execution callback."""
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        with pytest.raises(ValidationError):
            service.process_trade(source_trade)

    def test_process_trade_disabled(self, service, traders):
        """Test processing trade when copy trading is disabled."""
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )
        service.disable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        service.set_execution_callback(lambda t: t)

        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        copy_trades = service.process_trade(source_trade)
        assert len(copy_trades) == 0

    def test_get_copy_trades(self, service, traders):
        """Test getting copy trades for a source trade."""
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        service.set_execution_callback(lambda t: t)

        source_trade = Trade(
            trader_id=traders["leader"].trader_id,
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            quantity=1.0
        )

        service.process_trade(source_trade)

        copy_trade_ids = service.get_copy_trades(source_trade.trade_id)
        assert len(copy_trade_ids) == 1

    def test_update_copy_settings(self, service, traders):
        """Test updating copy settings."""
        service.enable_copy_trading(
            traders["follower"].trader_id,
            traders["leader"].trader_id
        )

        new_settings = {
            "copy_percentage": 75.0,
            "max_position_size": 500.0
        }

        relationship = service.update_copy_settings(
            traders["follower"].trader_id,
            traders["leader"].trader_id,
            new_settings
        )

        assert relationship.copy_settings["copy_percentage"] == 75.0
        assert relationship.copy_settings["max_position_size"] == 500.0

    def test_validate_copy_settings(self, service):
        """Test copy settings validation."""
        # Valid settings
        valid_settings = {
            "copy_percentage": 50.0,
            "slippage_tolerance": 1.0,
            "max_position_size": 100.0,
            "min_position_size": 10.0
        }
        service._validate_copy_settings(valid_settings)  # Should not raise

        # Invalid copy percentage
        with pytest.raises(ValidationError):
            service._validate_copy_settings({"copy_percentage": 150.0})

        with pytest.raises(ValidationError):
            service._validate_copy_settings({"copy_percentage": 0.0})

        # Invalid slippage
        with pytest.raises(ValidationError):
            service._validate_copy_settings({"slippage_tolerance": -1.0})

        # Invalid position sizes
        with pytest.raises(ValidationError):
            service._validate_copy_settings({
                "max_position_size": 10.0,
                "min_position_size": 20.0
            })
