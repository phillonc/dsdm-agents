"""
Unit tests for Fidelity connector
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from src.brokerage_service.connectors.fidelity import FidelityConnector
from src.brokerage_service.models import BrokerageConnection, BrokerageProvider, PositionType


@pytest.fixture
def mock_connection():
    """Create a mock Fidelity connection"""
    return BrokerageConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider=BrokerageProvider.FIDELITY,
        account_id="test_account",
        _access_token_encrypted="mock_access_token",
        _refresh_token_encrypted="mock_refresh_token",
    )


@pytest.fixture
def fidelity_connector(mock_connection):
    """Create Fidelity connector instance"""
    return FidelityConnector(
        mock_connection,
        client_id="test_client_id",
        client_secret="test_client_secret"
    )


@pytest.mark.asyncio
async def test_authenticate_success(fidelity_connector):
    """Test successful authentication"""
    mock_token_response = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    }
    
    mock_accounts_response = {
        "accounts": [
            {
                "accountId": "12345",
                "accountName": "Test Account",
            }
        ]
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_token_response)
        ))
        mock_get = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_accounts_response)
        ))
        
        mock_client.return_value.__aenter__.return_value.post = mock_post
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        result = await fidelity_connector.authenticate("auth_code_123")
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["account_id"] == "12345"
        assert result["account_name"] == "Test Account"
        assert "expires_at" in result


@pytest.mark.asyncio
async def test_get_positions(fidelity_connector):
    """Test fetching positions"""
    mock_response = {
        "positions": [
            {
                "symbol": "AAPL",
                "assetType": "EQUITY",
                "quantity": 100,
                "costBasis": 15000.00,
                "marketValue": 17500.00,
                "unrealizedGainLoss": 2500.00,
            },
            {
                "symbol": "SPY",
                "assetType": "ETF",
                "quantity": 50,
                "costBasis": 20000.00,
                "marketValue": 21000.00,
                "unrealizedGainLoss": 1000.00,
            }
        ]
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        positions = await fidelity_connector.get_positions()
        
        assert len(positions) == 2
        assert positions[0].symbol == "AAPL"
        assert positions[0].position_type == PositionType.STOCK
        assert positions[0].quantity == Decimal("100")
        assert positions[1].symbol == "SPY"
        assert positions[1].position_type == PositionType.ETF


@pytest.mark.asyncio
async def test_get_account_balance(fidelity_connector):
    """Test fetching account balance"""
    mock_response = {
        "balances": {
            "cashBalance": 5000.00,
            "accountValue": 50000.00,
            "buyingPower": 10000.00,
            "marginBalance": 0.00
        }
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        balance = await fidelity_connector.get_account_balance()
        
        assert balance["cash"] == 5000.00
        assert balance["equity"] == 50000.00
        assert balance["buying_power"] == 10000.00
        assert balance["margin_balance"] == 0.00


@pytest.mark.asyncio
async def test_disconnect(fidelity_connector):
    """Test token revocation on disconnect"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock()
        ))
        mock_client.return_value.__aenter__.return_value.post = mock_post
        
        await fidelity_connector.disconnect()
        
        # Verify revoke endpoint was called
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token(fidelity_connector):
    """Test token refresh"""
    mock_response = {
        "access_token": "refreshed_token",
        "expires_in": 3600
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=mock_response)
        ))
        mock_client.return_value.__aenter__.return_value.post = mock_post
        
        result = await fidelity_connector.refresh_token()
        
        assert result["access_token"] == "refreshed_token"
        assert "expires_at" in result


def test_position_type_mapping(fidelity_connector):
    """Test asset type to position type mapping"""
    assert fidelity_connector._map_position_type("EQUITY") == PositionType.STOCK
    assert fidelity_connector._map_position_type("OPTION") == PositionType.OPTION
    assert fidelity_connector._map_position_type("ETF") == PositionType.ETF
    assert fidelity_connector._map_position_type("MUTUAL_FUND") == PositionType.MUTUAL_FUND
