"""
Integration tests for brokerage connectors
Tests full flow with mocked external APIs
"""

import pytest
from decimal import Decimal
from datetime import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from src.brokerage_service.sync_service import PortfolioSyncService
from src.brokerage_service.repository import BrokerageRepository
from src.brokerage_service.models import (
    BrokerageConnection,
    BrokerageProvider,
    PositionType,
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


@pytest.mark.asyncio
async def test_full_fidelity_sync_flow(repository, sync_service, test_user_id):
    """Test complete Fidelity connection and sync flow"""
    # Create connection
    connection = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.FIDELITY,
        account_id="fidelity_test",
        _access_token_encrypted="mock_token",
    )
    repository.create_connection(connection)
    
    # Mock API responses
    mock_positions = {
        "positions": [
            {
                "symbol": "AAPL",
                "assetType": "EQUITY",
                "quantity": 100,
                "costBasis": 15000.00,
                "marketValue": 17500.00,
                "unrealizedGainLoss": 2500.00,
            }
        ]
    }
    
    mock_balance = {
        "balances": {
            "cashBalance": 5000.00,
            "accountValue": 22500.00,
            "buyingPower": 10000.00,
            "marginBalance": 0.00
        }
    }
    
    mock_transactions = {
        "transactions": [
            {
                "transactionType": "BUY",
                "symbol": "AAPL",
                "quantity": 100,
                "price": 150.00,
                "amount": -15000.00,
                "commission": 0,
                "transactionDate": datetime.utcnow().isoformat(),
            }
        ]
    }
    
    # Mock HTTP client
    with patch("httpx.AsyncClient") as mock_client:
        def get_response(url, **kwargs):
            if "positions" in url:
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value=mock_positions)
                )
            elif "balances" in url:
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value=mock_balance)
                )
            elif "transactions" in url:
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value=mock_transactions)
                )
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=get_response)
        
        # Perform sync
        result = await sync_service.sync_account(connection.id)
        
        assert result["positions"] == 1
        assert result["transactions"] == 1
        
        # Verify data was saved
        positions = repository.get_positions(connection.id)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == Decimal("100")
        
        balance = repository.get_account_balance(connection.id)
        assert balance.cash == Decimal("5000.00")


@pytest.mark.asyncio
async def test_multi_broker_portfolio_aggregation(repository, sync_service, test_user_id):
    """Test aggregating portfolio across multiple brokerages"""
    # Create two connections
    conn_schwab = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.SCHWAB,
        account_id="schwab_test",
        _access_token_encrypted="schwab_token",
    )
    conn_fidelity = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.FIDELITY,
        account_id="fidelity_test",
        _access_token_encrypted="fidelity_token",
    )
    
    repository.create_connection(conn_schwab)
    repository.create_connection(conn_fidelity)
    
    # Mock positions for both
    from src.brokerage_service.models import Position, AccountBalance
    
    positions_schwab = [
        Position(
            connection_id=conn_schwab.id,
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
    
    positions_fidelity = [
        Position(
            connection_id=conn_fidelity.id,
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
    
    repository.save_positions(positions_schwab)
    repository.save_positions(positions_fidelity)
    
    # Mock balances
    balance_schwab = AccountBalance(
        connection_id=conn_schwab.id,
        cash=Decimal("5000.00"),
        equity=Decimal("17500.00"),
    )
    balance_fidelity = AccountBalance(
        connection_id=conn_fidelity.id,
        cash=Decimal("3000.00"),
        equity=Decimal("17500.00"),
    )
    
    repository.save_account_balance(balance_schwab)
    repository.save_account_balance(balance_fidelity)
    
    # Get unified portfolio
    portfolio = await sync_service.get_unified_portfolio(test_user_id)
    
    # Verify aggregation
    assert len(portfolio.positions) == 2
    assert portfolio.total_equity == Decimal("35000.00")
    assert portfolio.total_cash == Decimal("8000.00")
    assert portfolio.total_value == Decimal("43000.00")
    
    # Verify both positions are present
    symbols = {pos.symbol for pos in portfolio.positions}
    assert "AAPL" in symbols
    assert "MSFT" in symbols


@pytest.mark.asyncio
async def test_sync_with_token_refresh(repository, sync_service, test_user_id):
    """Test that expired tokens are refreshed during sync"""
    # Create connection with expired token
    connection = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.FIDELITY,
        account_id="test",
        _access_token_encrypted="old_token",
        _refresh_token_encrypted="refresh_token",
        token_expires_at=datetime.utcnow() - timedelta(minutes=1),  # Expired
    )
    repository.create_connection(connection)
    
    # Mock refresh response
    mock_refresh_response = {
        "access_token": "new_token",
        "expires_in": 3600
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        # Mock all API calls
        async def mock_post(url, **kwargs):
            if "token" in url:
                return MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value=mock_refresh_response)
                )
        
        async def mock_get(url, **kwargs):
            return MagicMock(
                raise_for_status=MagicMock(),
                json=MagicMock(return_value={"positions": [], "balances": {}, "transactions": []})
            )
        
        mock_client.return_value.__aenter__.return_value.post = mock_post
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        # Sync should refresh token
        await sync_service.sync_account(connection.id)
        
        # Verify token was updated
        updated_conn = repository.get_connection(connection.id)
        assert updated_conn.token_expires_at > datetime.utcnow()


@pytest.mark.asyncio
async def test_concurrent_account_sync(repository, sync_service, test_user_id):
    """Test syncing multiple accounts concurrently"""
    # Create 3 connections
    connections = []
    for i in range(3):
        conn = BrokerageConnection(
            user_id=test_user_id,
            provider=BrokerageProvider.FIDELITY,
            account_id=f"account_{i}",
            _access_token_encrypted=f"token_{i}",
        )
        repository.create_connection(conn)
        connections.append(conn)
    
    # Mock API responses
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=MagicMock(
                raise_for_status=MagicMock(),
                json=MagicMock(return_value={"positions": [], "balances": {}, "transactions": []})
            )
        )
        
        # Sync all accounts
        result = await sync_service.sync_all_accounts(test_user_id)
        
        # Verify all were synced
        assert result["accounts"] == 3


@pytest.mark.asyncio
async def test_error_handling_in_sync(repository, sync_service, test_user_id):
    """Test error handling during sync"""
    connection = BrokerageConnection(
        user_id=test_user_id,
        provider=BrokerageProvider.FIDELITY,
        account_id="test",
        _access_token_encrypted="token",
    )
    repository.create_connection(connection)
    
    # Mock API failure
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        # Sync should raise exception
        with pytest.raises(Exception):
            await sync_service.sync_account(connection.id)
