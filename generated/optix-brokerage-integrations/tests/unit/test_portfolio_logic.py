"""
Unit tests for portfolio logic
Tests cash aggregation, realized P&L, and day P&L calculations
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from src.brokerage_service.sync_service import PortfolioSyncService
from src.brokerage_service.repository import BrokerageRepository
from src.brokerage_service.models import (
    BrokerageConnection,
    BrokerageProvider,
    Position,
    PositionType,
    Transaction,
    TransactionType,
    AccountBalance,
    PortfolioSnapshot,
)


@pytest.fixture
def repository():
    """Create test repository"""
    return BrokerageRepository()


@pytest.fixture
def sync_service(repository):
    """Create sync service"""
    return PortfolioSyncService(repository)


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


@pytest.fixture
def setup_test_data(repository, test_user_id):
    """Setup test connections, positions, and transactions"""
    # Create two connections
    conn1 = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.SCHWAB,
        account_id="schwab_account",
        _access_token_encrypted="token1",
    )
    conn2 = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.FIDELITY,
        account_id="fidelity_account",
        _access_token_encrypted="token2",
    )
    
    repository.create_connection(conn1)
    repository.create_connection(conn2)
    
    # Create positions
    positions1 = [
        Position(
            connection_id=conn1.id,
            symbol="AAPL",
            position_type=PositionType.STOCK,
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            cost_basis=Decimal("15000.00"),
            current_price=Decimal("175.00"),
            market_value=Decimal("17500.00"),
            unrealized_pl=Decimal("2500.00"),
            unrealized_pl_percent=Decimal("16.67"),
        )
    ]
    
    positions2 = [
        Position(
            connection_id=conn2.id,
            symbol="MSFT",
            position_type=PositionType.STOCK,
            quantity=Decimal("50"),
            average_price=Decimal("300.00"),
            cost_basis=Decimal("15000.00"),
            current_price=Decimal("350.00"),
            market_value=Decimal("17500.00"),
            unrealized_pl=Decimal("2500.00"),
            unrealized_pl_percent=Decimal("16.67"),
        )
    ]
    
    repository.save_positions(positions1)
    repository.save_positions(positions2)
    
    # Create account balances
    balance1 = AccountBalance(
        connection_id=conn1.id,
        cash=Decimal("5000.00"),
        equity=Decimal("17500.00"),
        buying_power=Decimal("10000.00"),
        margin_balance=Decimal("0"),
    )
    balance2 = AccountBalance(
        connection_id=conn2.id,
        cash=Decimal("3000.00"),
        equity=Decimal("17500.00"),
        buying_power=Decimal("6000.00"),
        margin_balance=Decimal("0"),
    )
    
    repository.save_account_balance(balance1)
    repository.save_account_balance(balance2)
    
    # Create some transactions for realized P&L
    transactions = [
        Transaction(
            connection_id=conn1.id,
            transaction_type=TransactionType.SELL,
            symbol="TSLA",
            quantity=Decimal("10"),
            price=Decimal("250.00"),
            amount=Decimal("2500.00"),
            fees=Decimal("5.00"),
            transaction_date=datetime.utcnow() - timedelta(days=5),
        ),
        Transaction(
            connection_id=conn1.id,
            transaction_type=TransactionType.DIVIDEND,
            symbol="AAPL",
            quantity=Decimal("0"),
            price=Decimal("0"),
            amount=Decimal("100.00"),
            fees=Decimal("0"),
            transaction_date=datetime.utcnow() - timedelta(days=3),
        ),
    ]
    
    repository.save_transactions(transactions)
    
    return conn1, conn2


@pytest.mark.asyncio
async def test_calculate_total_cash(sync_service, test_user_id, setup_test_data):
    """Test total cash calculation across accounts"""
    total_cash = await sync_service._calculate_total_cash(test_user_id)
    
    # Should aggregate from both accounts: 5000 + 3000 = 8000
    assert total_cash == Decimal("8000.00")


@pytest.mark.asyncio
async def test_calculate_realized_pl(sync_service, test_user_id, setup_test_data):
    """Test realized P&L calculation"""
    realized_pl = await sync_service._calculate_realized_pl(test_user_id)
    
    # Should include:
    # - SELL transaction: 2500 - 5 = 2495
    # - DIVIDEND: 100
    # Total: 2595
    assert realized_pl == Decimal("2595.00")


@pytest.mark.asyncio
async def test_get_unified_portfolio(sync_service, test_user_id, setup_test_data):
    """Test unified portfolio calculation"""
    portfolio = await sync_service.get_unified_portfolio(test_user_id)
    
    # Total equity: 17500 + 17500 = 35000
    assert portfolio.total_equity == Decimal("35000.00")
    
    # Total cash: 8000
    assert portfolio.total_cash == Decimal("8000.00")
    
    # Total value: 35000 + 8000 = 43000
    assert portfolio.total_value == Decimal("43000.00")
    
    # Unrealized P&L: 2500 + 2500 = 5000
    total_unrealized = sum(pos.unrealized_pl for pos in portfolio.positions)
    assert total_unrealized == Decimal("5000.00")
    
    # Realized P&L: 2595
    assert portfolio.realized_pl == Decimal("2595.00")
    
    # Total P&L: 5000 + 2595 = 7595
    assert portfolio.total_pl == Decimal("7595.00")
    
    # Number of positions
    assert len(portfolio.positions) == 2


@pytest.mark.asyncio
async def test_day_pl_without_snapshot(sync_service, test_user_id, setup_test_data):
    """Test day P&L returns zero when no snapshot exists"""
    day_pl, day_pl_percent = await sync_service._calculate_day_pl(test_user_id)
    
    # Should return zero when no snapshot
    assert day_pl == Decimal("0")
    assert day_pl_percent == Decimal("0")


@pytest.mark.asyncio
async def test_day_pl_with_snapshot(sync_service, repository, test_user_id, setup_test_data):
    """Test day P&L calculation with snapshot"""
    # Create a start of day snapshot
    snapshot = PortfolioSnapshot(
        user_id=test_user_id,
        snapshot_type="start_of_day",
        total_value=Decimal("40000.00"),  # Earlier value
        total_cash=Decimal("8000.00"),
        positions_snapshot={},
        captured_at=datetime.utcnow(),
    )
    repository.save_portfolio_snapshot(snapshot)
    
    # Calculate day P&L
    day_pl, day_pl_percent = await sync_service._calculate_day_pl(test_user_id)
    
    # Current value is 43000, start was 40000
    # Day P&L = 43000 - 40000 = 3000
    assert day_pl == Decimal("3000.00")
    
    # Day P&L % = 3000 / 40000 * 100 = 7.5%
    assert day_pl_percent == Decimal("7.5")


@pytest.mark.asyncio
async def test_portfolio_with_margin(repository, sync_service, test_user_id):
    """Test cash calculation with margin balance"""
    # Create connection with margin
    conn = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.SCHWAB,
        account_id="margin_account",
        _access_token_encrypted="token",
    )
    repository.create_connection(conn)
    
    # Create balance with margin debit
    balance = AccountBalance(
        connection_id=conn.id,
        cash=Decimal("10000.00"),
        equity=Decimal("50000.00"),
        buying_power=Decimal("100000.00"),
        margin_balance=Decimal("2000.00"),  # Margin debit
    )
    repository.save_account_balance(balance)
    
    # Calculate total cash
    total_cash = await sync_service._calculate_total_cash(test_user_id)
    
    # Should subtract margin: 10000 - 2000 = 8000
    assert total_cash == Decimal("8000.00")


@pytest.mark.asyncio
async def test_realized_pl_with_options(repository, sync_service, test_user_id):
    """Test realized P&L with option transactions"""
    conn = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.SCHWAB,
        account_id="options_account",
        _access_token_encrypted="token",
    )
    repository.create_connection(conn)
    
    # Option transactions
    transactions = [
        # Sell to open (collect premium)
        Transaction(
            connection_id=conn.id,
            transaction_type=TransactionType.SELL_TO_OPEN,
            symbol="AAPL 2024-01-01 C 150",
            quantity=Decimal("1"),
            price=Decimal("5.00"),
            amount=Decimal("500.00"),
            fees=Decimal("1.00"),
            transaction_date=datetime.utcnow() - timedelta(days=10),
        ),
        # Buy to close (close position)
        Transaction(
            connection_id=conn.id,
            transaction_type=TransactionType.BUY_TO_CLOSE,
            symbol="AAPL 2024-01-01 C 150",
            quantity=Decimal("1"),
            price=Decimal("2.00"),
            amount=Decimal("200.00"),
            fees=Decimal("1.00"),
            transaction_date=datetime.utcnow() - timedelta(days=5),
        ),
        # Expired option (worthless)
        Transaction(
            connection_id=conn.id,
            transaction_type=TransactionType.EXPIRED,
            symbol="SPY 2024-01-01 P 400",
            quantity=Decimal("1"),
            price=Decimal("0"),
            amount=Decimal("0"),
            fees=Decimal("0"),
            transaction_date=datetime.utcnow() - timedelta(days=2),
        ),
    ]
    repository.save_transactions(transactions)
    
    realized_pl = await sync_service._calculate_realized_pl(test_user_id)
    
    # Buy to close: -(200 + 1) = -201
    # Expired: 0
    # Total: -201
    assert realized_pl == Decimal("-201.00")


def test_closing_transaction_types(sync_service):
    """Test that closing transaction types are correctly defined"""
    closing_types = sync_service.CLOSING_TRANSACTION_TYPES
    
    assert TransactionType.SELL in closing_types
    assert TransactionType.BUY_TO_CLOSE in closing_types
    assert TransactionType.SELL_TO_CLOSE in closing_types
    assert TransactionType.EXPIRED in closing_types
    assert TransactionType.ASSIGNED in closing_types
    assert TransactionType.EXERCISED in closing_types
    assert TransactionType.DIVIDEND in closing_types
    
    # Non-closing types should not be in list
    assert TransactionType.BUY not in closing_types
    assert TransactionType.BUY_TO_OPEN not in closing_types
