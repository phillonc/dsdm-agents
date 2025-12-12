"""
Unit tests for PerformanceService.
"""

import pytest
from datetime import datetime, timedelta

from src.performance_service import PerformanceService
from src.models import Trade, TradeType, TradeStatus


class TestPerformanceService:
    """Test suite for PerformanceService."""

    @pytest.fixture
    def service(self):
        """Create a PerformanceService instance."""
        return PerformanceService()

    @pytest.fixture
    def sample_trade(self):
        """Create a sample closed trade."""
        trade = Trade(
            trader_id="trader123",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            entry_price=50000.0,
            exit_price=52000.0,
            quantity=1.0,
            status=TradeStatus.CLOSED,
            opened_at=datetime.utcnow() - timedelta(days=1),
            closed_at=datetime.utcnow(),
            profit_loss=2000.0,
            profit_loss_percentage=4.0
        )
        return trade

    def test_add_trade(self, service, sample_trade):
        """Test adding a trade."""
        result = service.add_trade(sample_trade)

        assert result.trade_id == sample_trade.trade_id
        assert sample_trade.trade_id in service._trades
        assert sample_trade.trader_id in service._trader_trades_index

    def test_get_trader_trades(self, service):
        """Test getting trades for a trader."""
        trade1 = Trade(
            trader_id="trader123",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            status=TradeStatus.CLOSED,
            profit_loss=1000.0,
            profit_loss_percentage=2.0
        )
        trade2 = Trade(
            trader_id="trader123",
            asset="ETH/USD",
            trade_type=TradeType.SELL,
            status=TradeStatus.OPEN,
            profit_loss=0.0,
            profit_loss_percentage=0.0
        )

        service.add_trade(trade1)
        service.add_trade(trade2)

        # Get all trades
        trades = service.get_trader_trades("trader123")
        assert len(trades) == 2

        # Filter by status
        closed_trades = service.get_trader_trades("trader123", status=TradeStatus.CLOSED)
        assert len(closed_trades) == 1
        assert closed_trades[0].trade_id == trade1.trade_id

    def test_calculate_metrics_no_trades(self, service):
        """Test metrics calculation with no trades."""
        metrics = service.calculate_metrics("trader123")

        assert metrics.trader_id == "trader123"
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0

    def test_calculate_metrics_basic(self, service):
        """Test basic metrics calculation."""
        # Create winning trades
        for i in range(6):
            trade = Trade(
                trader_id="trader123",
                asset="BTC/USD",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                opened_at=datetime.utcnow() - timedelta(days=i),
                closed_at=datetime.utcnow() - timedelta(days=i, hours=12),
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            )
            service.add_trade(trade)

        # Create losing trades
        for i in range(4):
            trade = Trade(
                trader_id="trader123",
                asset="BTC/USD",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                opened_at=datetime.utcnow() - timedelta(days=i+6),
                closed_at=datetime.utcnow() - timedelta(days=i+6, hours=12),
                profit_loss=-500.0,
                profit_loss_percentage=-2.5
            )
            service.add_trade(trade)

        metrics = service.calculate_metrics("trader123")

        assert metrics.total_trades == 10
        assert metrics.winning_trades == 6
        assert metrics.losing_trades == 4
        assert metrics.win_rate == 60.0
        assert metrics.total_return == 30.0 - 10.0  # 6*5% - 4*2.5%
        assert metrics.best_trade == 5.0
        assert metrics.worst_trade == -2.5

    def test_calculate_metrics_periods(self, service):
        """Test metrics calculation for different periods."""
        # Old trade (beyond 1 month)
        old_trade = Trade(
            trader_id="trader123",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            status=TradeStatus.CLOSED,
            opened_at=datetime.utcnow() - timedelta(days=60),
            closed_at=datetime.utcnow() - timedelta(days=59),
            profit_loss=1000.0,
            profit_loss_percentage=5.0
        )
        service.add_trade(old_trade)

        # Recent trade
        recent_trade = Trade(
            trader_id="trader123",
            asset="BTC/USD",
            trade_type=TradeType.BUY,
            status=TradeStatus.CLOSED,
            opened_at=datetime.utcnow() - timedelta(days=5),
            closed_at=datetime.utcnow() - timedelta(days=4),
            profit_loss=2000.0,
            profit_loss_percentage=10.0
        )
        service.add_trade(recent_trade)

        # All time
        metrics_all = service.calculate_metrics("trader123", period="all_time")
        assert metrics_all.total_trades == 2

        # 1 month
        metrics_1m = service.calculate_metrics("trader123", period="1m")
        assert metrics_1m.total_trades == 1
        assert metrics_1m.total_return == 10.0

    def test_calculate_sharpe_ratio(self, service):
        """Test Sharpe ratio calculation."""
        returns = [5.0, 3.0, -2.0, 4.0, 6.0]
        sharpe = service._calculate_sharpe_ratio(returns)
        assert isinstance(sharpe, float)

        # Test with no variance
        returns_flat = [5.0, 5.0, 5.0]
        sharpe_flat = service._calculate_sharpe_ratio(returns_flat)
        assert sharpe_flat == 0.0

    def test_calculate_sortino_ratio(self, service):
        """Test Sortino ratio calculation."""
        returns = [5.0, 3.0, -2.0, 4.0, 6.0]
        sortino = service._calculate_sortino_ratio(returns)
        assert isinstance(sortino, float)

        # Test with no downside
        returns_positive = [5.0, 3.0, 4.0, 6.0]
        sortino_positive = service._calculate_sortino_ratio(returns_positive)
        assert sortino_positive == 0.0

    def test_calculate_max_drawdown(self, service):
        """Test maximum drawdown calculation."""
        trades = [
            Trade(
                trader_id="trader123",
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                opened_at=datetime.utcnow() - timedelta(days=i),
                profit_loss_percentage=pct
            )
            for i, pct in enumerate([10.0, -5.0, -8.0, 15.0, -3.0])
        ]

        max_dd = service._calculate_max_drawdown(trades)
        assert isinstance(max_dd, float)
        assert max_dd >= 0.0

    def test_calculate_profit_factor(self, service):
        """Test profit factor calculation."""
        trades = [
            Trade(
                trader_id="trader123",
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=profit
            )
            for profit in [1000.0, 1500.0, -500.0, -300.0]
        ]

        profit_factor = service._calculate_profit_factor(trades)
        expected = 2500.0 / 800.0
        assert abs(profit_factor - expected) < 0.01

        # Test with no losses
        winning_trades = [t for t in trades if t.profit_loss > 0]
        pf_no_loss = service._calculate_profit_factor(winning_trades)
        assert pf_no_loss == float('inf')

    def test_calculate_consistency_score(self, service):
        """Test consistency score calculation."""
        returns = [5.0, 5.1, 4.9, 5.2, 4.8]  # Consistent
        score = service._calculate_consistency_score(returns)
        assert score > 80.0  # Should be high

        returns_volatile = [10.0, -5.0, 15.0, -8.0, 12.0]  # Volatile
        score_volatile = service._calculate_consistency_score(returns_volatile)
        assert score_volatile < score  # Should be lower

    def test_calculate_risk_adjusted_return(self, service):
        """Test risk-adjusted return calculation."""
        returns = [5.0, 3.0, -2.0, 4.0, 6.0]
        avg_return = sum(returns) / len(returns)
        rar = service._calculate_risk_adjusted_return(avg_return, returns)
        assert isinstance(rar, float)

    def test_compare_traders(self, service):
        """Test comparing multiple traders."""
        # Add trades for trader1
        for i in range(3):
            service.add_trade(Trade(
                trader_id="trader1",
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=1000.0,
                profit_loss_percentage=5.0
            ))

        # Add trades for trader2
        for i in range(2):
            service.add_trade(Trade(
                trader_id="trader2",
                asset="BTC",
                trade_type=TradeType.BUY,
                status=TradeStatus.CLOSED,
                profit_loss=2000.0,
                profit_loss_percentage=10.0
            ))

        comparison = service.compare_traders(["trader1", "trader2"])

        assert "trader1" in comparison
        assert "trader2" in comparison
        assert comparison["trader1"].total_trades == 3
        assert comparison["trader2"].total_trades == 2

    def test_metrics_caching(self, service):
        """Test that metrics are cached."""
        service.add_trade(Trade(
            trader_id="trader123",
            asset="BTC",
            trade_type=TradeType.BUY,
            status=TradeStatus.CLOSED,
            profit_loss=1000.0,
            profit_loss_percentage=5.0
        ))

        # First call
        metrics1 = service.calculate_metrics("trader123")
        
        # Second call (should be cached)
        metrics2 = service.calculate_metrics("trader123")

        assert metrics1.calculated_at == metrics2.calculated_at
