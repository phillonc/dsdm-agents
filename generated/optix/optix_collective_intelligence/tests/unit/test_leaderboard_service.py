"""
Unit tests for LeaderboardService.
"""

import pytest
from datetime import datetime, timedelta

from src.leaderboard_service import LeaderboardService
from src.trader_service import TraderService
from src.performance_service import PerformanceService
from src.models import Trade, TradeStatus, TradeType


class TestLeaderboardService:
    """Test suite for LeaderboardService."""

    @pytest.fixture
    def trader_service(self):
        """Create TraderService instance."""
        return TraderService()

    @pytest.fixture
    def performance_service(self):
        """Create PerformanceService instance."""
        return PerformanceService()

    @pytest.fixture
    def service(self, trader_service, performance_service):
        """Create LeaderboardService instance."""
        return LeaderboardService(trader_service, performance_service)

    @pytest.fixture
    def setup_traders(self, trader_service, performance_service):
        """Setup sample traders with performance."""
        traders = []
        
        # Create 5 traders with different performance
        for i in range(5):
            trader = trader_service.create_trader(
                username=f"trader{i}",
                display_name=f"Trader {i}"
            )
            traders.append(trader)

            # Add trades with varying performance
            num_trades = 10 + i * 5
            win_rate = 0.5 + (i * 0.1)

            for j in range(num_trades):
                is_win = j < int(num_trades * win_rate)
                trade = Trade(
                    trader_id=trader.trader_id,
                    asset="BTC/USD",
                    trade_type=TradeType.BUY,
                    status=TradeStatus.CLOSED,
                    opened_at=datetime.utcnow() - timedelta(days=j),
                    closed_at=datetime.utcnow() - timedelta(days=j, hours=12),
                    profit_loss=1000.0 if is_win else -500.0,
                    profit_loss_percentage=5.0 if is_win else -2.5
                )
                performance_service.add_trade(trade)

        return traders

    def test_get_leaderboard_basic(self, service, setup_traders):
        """Test basic leaderboard generation."""
        leaderboard = service.get_leaderboard(
            metric="total_return",
            limit=10,
            min_trades=5
        )

        assert len(leaderboard) <= 10
        assert len(leaderboard) > 0

        # Check ranks are sequential
        for i, entry in enumerate(leaderboard, 1):
            assert entry.rank == i

        # Check sorted by metric value
        for i in range(len(leaderboard) - 1):
            assert leaderboard[i].metric_value >= leaderboard[i + 1].metric_value

    def test_get_leaderboard_min_trades_filter(self, service, trader_service, performance_service):
        """Test minimum trades filter."""
        # Create trader with few trades
        trader = trader_service.create_trader(
            username="newtrader",
            display_name="New Trader"
        )
        for i in range(3):
            performance_service.add_trade(Trade(
                trader_id=trader.trader_id,
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            ))

        # Should not appear with min_trades=10
        leaderboard = service.get_leaderboard(min_trades=10)
        trader_ids = [e.trader_id for e in leaderboard]
        assert trader.trader_id not in trader_ids

        # Should appear with min_trades=3
        leaderboard = service.get_leaderboard(min_trades=3)
        trader_ids = [e.trader_id for e in leaderboard]
        assert trader.trader_id in trader_ids

    def test_get_top_performers(self, service, setup_traders):
        """Test getting top performers."""
        top = service.get_top_performers(period="1m", limit=3)

        assert len(top) <= 3
        assert all(entry.rank <= 3 for entry in top)

    def test_get_most_consistent(self, service, setup_traders):
        """Test getting most consistent traders."""
        consistent = service.get_most_consistent(period="3m", limit=5)

        assert len(consistent) <= 5
        # Check that consistency scores are used
        for entry in consistent:
            assert hasattr(entry, 'metric_value')

    def test_get_best_risk_adjusted(self, service, setup_traders):
        """Test getting best risk-adjusted returns."""
        best_ra = service.get_best_risk_adjusted(period="6m", limit=5)

        assert len(best_ra) <= 5

    def test_get_rising_stars(self, service, trader_service, performance_service):
        """Test getting rising star traders."""
        # Create recent trader with good performance
        recent_trader = trader_service.create_trader(
            username="rising_star",
            display_name="Rising Star"
        )

        for i in range(10):
            performance_service.add_trade(Trade(
                trader_id=recent_trader.trader_id,
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            ))

        rising = service.get_rising_stars(limit=10)

        # Recent trader should be in rising stars
        trader_ids = [e.trader_id for e in rising]
        assert recent_trader.trader_id in trader_ids

    def test_get_trader_rank(self, service, setup_traders):
        """Test getting a specific trader's rank."""
        trader_id = setup_traders[0].trader_id

        rank = service.get_trader_rank(
            trader_id,
            metric="total_return",
            period="all_time"
        )

        assert rank is not None
        assert isinstance(rank, int)
        assert rank >= 1

    def test_get_trader_rank_not_in_leaderboard(self, service, trader_service):
        """Test getting rank for trader not in leaderboard."""
        # Create trader with no trades
        trader = trader_service.create_trader(
            username="notrader",
            display_name="No Trader"
        )

        rank = service.get_trader_rank(trader.trader_id)
        assert rank is None

    def test_get_category_leaderboards(self, service, setup_traders):
        """Test getting all category leaderboards."""
        categories = service.get_category_leaderboards(period="1m")

        assert "top_performers" in categories
        assert "most_consistent" in categories
        assert "best_risk_adjusted" in categories
        assert "rising_stars" in categories

        assert isinstance(categories["top_performers"], list)
        assert isinstance(categories["most_consistent"], list)

    def test_calculate_score(self, service):
        """Test composite score calculation."""
        from src.models import PerformanceMetrics

        metrics = PerformanceMetrics(
            trader_id="trader123",
            total_return=100.0,
            win_rate=70.0,
            sharpe_ratio=2.0,
            consistency_score=85.0,
            risk_adjusted_return=1.5
        )

        score = service._calculate_score(metrics)

        assert isinstance(score, float)
        assert score > 0

    def test_leaderboard_caching(self, service, setup_traders):
        """Test that leaderboards are cached."""
        # First call
        lb1 = service.get_leaderboard()
        
        # Second call (should be cached)
        lb2 = service.get_leaderboard()

        # Should return same results within cache TTL
        assert len(lb1) == len(lb2)

    def test_clear_cache(self, service, setup_traders):
        """Test clearing leaderboard cache."""
        service.get_leaderboard()
        assert len(service._leaderboard_cache) > 0

        service.clear_cache()
        assert len(service._leaderboard_cache) == 0
