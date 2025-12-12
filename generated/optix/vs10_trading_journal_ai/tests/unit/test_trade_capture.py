"""
Unit tests for trade capture functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Trade, TradeCreate, TradeDirection, TradeStatus
from src.trade_capture import TradeCapture, BrokerageIntegrationClient


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_vs7_client():
    """Create mock VS-7 client."""
    client = Mock(spec=BrokerageIntegrationClient)
    client.get_trades = AsyncMock(return_value=[])
    client.get_account_positions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def trade_capture(db_session, mock_vs7_client):
    """Create TradeCapture instance with mocked dependencies."""
    return TradeCapture(db_session, mock_vs7_client)


class TestTradeCapture:
    """Tests for TradeCapture service."""
    
    def test_create_trade(self, trade_capture):
        """Test creating a new trade."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=150.50,
            quantity=100,
            entry_commission=1.50
        )
        
        trade = trade_capture.create_trade(trade_data)
        
        assert trade.id is not None
        assert trade.user_id == "user123"
        assert trade.symbol == "AAPL"
        assert trade.direction == TradeDirection.LONG
        assert trade.status == TradeStatus.OPEN
        assert trade.entry_price == 150.50
        assert trade.quantity == 100
    
    def test_create_trade_with_stop_loss(self, trade_capture):
        """Test creating trade with stop loss."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="TSLA",
            direction=TradeDirection.SHORT,
            entry_date=datetime.utcnow(),
            entry_price=200.00,
            quantity=50,
            stop_loss=210.00,
            take_profit=180.00
        )
        
        trade = trade_capture.create_trade(trade_data)
        
        assert trade.stop_loss == 210.00
        assert trade.take_profit == 180.00
    
    def test_update_trade_exit_long(self, trade_capture):
        """Test updating trade with exit (long position)."""
        # Create trade
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=150.00,
            quantity=100,
            entry_commission=1.00
        )
        trade = trade_capture.create_trade(trade_data)
        
        # Close trade
        exit_date = datetime.utcnow()
        updated_trade = trade_capture.update_trade_exit(
            trade_id=trade.id,
            exit_price=155.00,
            exit_date=exit_date,
            exit_commission=1.00
        )
        
        assert updated_trade.status == TradeStatus.CLOSED
        assert updated_trade.exit_price == 155.00
        assert updated_trade.exit_date == exit_date
        
        # Check P&L calculation
        expected_gross_pnl = (155.00 - 150.00) * 100  # $500
        expected_net_pnl = expected_gross_pnl - 2.00  # $498
        
        assert updated_trade.gross_pnl == pytest.approx(expected_gross_pnl)
        assert updated_trade.net_pnl == pytest.approx(expected_net_pnl)
    
    def test_update_trade_exit_short(self, trade_capture):
        """Test updating trade with exit (short position)."""
        # Create short trade
        trade_data = TradeCreate(
            user_id="user123",
            symbol="TSLA",
            direction=TradeDirection.SHORT,
            entry_date=datetime.utcnow(),
            entry_price=200.00,
            quantity=50,
            entry_commission=1.50
        )
        trade = trade_capture.create_trade(trade_data)
        
        # Close trade at profit
        updated_trade = trade_capture.update_trade_exit(
            trade_id=trade.id,
            exit_price=190.00,  # Profit for short
            exit_date=datetime.utcnow(),
            exit_commission=1.50
        )
        
        # Check P&L calculation for short
        expected_gross_pnl = (200.00 - 190.00) * 50  # $500
        expected_net_pnl = expected_gross_pnl - 3.00  # $497
        
        assert updated_trade.gross_pnl == pytest.approx(expected_gross_pnl)
        assert updated_trade.net_pnl == pytest.approx(expected_net_pnl)
    
    def test_calculate_pnl_percentage(self, trade_capture):
        """Test P&L percentage calculation."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=100.00,
            quantity=100
        )
        trade = trade_capture.create_trade(trade_data)
        
        # Exit at 10% profit
        updated_trade = trade_capture.update_trade_exit(
            trade_id=trade.id,
            exit_price=110.00,
            exit_date=datetime.utcnow()
        )
        
        # P&L should be approximately 10%
        assert updated_trade.pnl_percent == pytest.approx(10.0, rel=0.1)
    
    def test_calculate_risk_reward_ratio(self, trade_capture):
        """Test risk/reward ratio calculation."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=100.00,
            quantity=100,
            stop_loss=95.00  # $5 risk per share
        )
        trade = trade_capture.create_trade(trade_data)
        
        # Exit at 2:1 R/R
        updated_trade = trade_capture.update_trade_exit(
            trade_id=trade.id,
            exit_price=110.00,  # $10 reward per share
            exit_date=datetime.utcnow()
        )
        
        # R/R should be 2:1
        assert updated_trade.risk_reward_ratio == pytest.approx(2.0, rel=0.1)
    
    def test_get_user_trades(self, trade_capture):
        """Test retrieving user trades."""
        # Create multiple trades
        for i in range(3):
            trade_data = TradeCreate(
                user_id="user123",
                symbol=f"STOCK{i}",
                direction=TradeDirection.LONG,
                entry_date=datetime.utcnow() - timedelta(days=i),
                entry_price=100.00 + i,
                quantity=100
            )
            trade_capture.create_trade(trade_data)
        
        # Get all trades
        trades = trade_capture.get_user_trades("user123")
        assert len(trades) == 3
    
    def test_get_user_trades_filtered_by_symbol(self, trade_capture):
        """Test filtering trades by symbol."""
        # Create trades with different symbols
        for symbol in ["AAPL", "TSLA", "AAPL"]:
            trade_data = TradeCreate(
                user_id="user123",
                symbol=symbol,
                direction=TradeDirection.LONG,
                entry_date=datetime.utcnow(),
                entry_price=150.00,
                quantity=100
            )
            trade_capture.create_trade(trade_data)
        
        # Filter by symbol
        aapl_trades = trade_capture.get_user_trades("user123", symbol="AAPL")
        assert len(aapl_trades) == 2
    
    def test_get_user_trades_filtered_by_status(self, trade_capture):
        """Test filtering trades by status."""
        # Create and close one trade
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=150.00,
            quantity=100
        )
        trade1 = trade_capture.create_trade(trade_data)
        trade_capture.update_trade_exit(
            trade_id=trade1.id,
            exit_price=155.00,
            exit_date=datetime.utcnow()
        )
        
        # Create open trade
        trade2 = trade_capture.create_trade(trade_data)
        
        # Filter by open status
        open_trades = trade_capture.get_user_trades("user123", status=TradeStatus.OPEN)
        assert len(open_trades) == 1
        
        # Filter by closed status
        closed_trades = trade_capture.get_user_trades("user123", status=TradeStatus.CLOSED)
        assert len(closed_trades) == 1
    
    def test_normalize_broker_trade(self, trade_capture):
        """Test normalizing broker trade data."""
        broker_trade = {
            'user_id': 'user123',
            'broker_id': 'alpaca',
            'trade_id': 'abc123',
            'symbol': 'AAPL',
            'side': 'BUY',
            'price': 150.50,
            'quantity': 100,
            'execution_time': '2024-01-15T10:30:00',
            'commission': 1.50
        }
        
        trade_data = trade_capture._normalize_broker_trade(broker_trade)
        
        assert trade_data.user_id == 'user123'
        assert trade_data.broker_id == 'alpaca'
        assert trade_data.symbol == 'AAPL'
        assert trade_data.direction == TradeDirection.LONG
        assert trade_data.entry_price == 150.50
        assert trade_data.quantity == 100
    
    @pytest.mark.asyncio
    async def test_sync_trades(self, trade_capture, mock_vs7_client):
        """Test syncing trades from brokerage."""
        # Mock broker response
        mock_vs7_client.get_trades.return_value = [
            {
                'user_id': 'user123',
                'broker_id': 'alpaca',
                'trade_id': 'abc123',
                'symbol': 'AAPL',
                'side': 'BUY',
                'price': 150.00,
                'quantity': 100,
                'execution_time': datetime.utcnow().isoformat(),
                'commission': 1.00,
                'status': 'OPEN'
            }
        ]
        
        stats = await trade_capture.sync_trades(
            user_id='user123',
            broker_id='alpaca',
            lookback_days=30
        )
        
        assert stats['total_fetched'] == 1
        assert stats['new_trades'] == 1
        assert stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_sync_open_positions(self, trade_capture, mock_vs7_client):
        """Test syncing open positions."""
        # Mock positions response
        mock_vs7_client.get_account_positions.return_value = [
            {
                'symbol': 'AAPL',
                'side': 'LONG',
                'average_price': 150.00,
                'quantity': 100,
                'opened_at': datetime.utcnow().isoformat()
            }
        ]
        
        stats = await trade_capture.sync_open_positions(
            user_id='user123',
            broker_id='alpaca'
        )
        
        assert stats['total_positions'] == 1
        assert stats['synced'] == 1


class TestBrokerageIntegrationClient:
    """Tests for BrokerageIntegrationClient."""
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client async context manager."""
        client = BrokerageIntegrationClient(
            base_url="https://api.example.com",
            api_key="test_key"
        )
        
        async with client as c:
            assert c.session is not None
        
        assert client.session is None or client.session.closed
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = BrokerageIntegrationClient(
            base_url="https://api.example.com/",
            api_key="test_key"
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test_key"
