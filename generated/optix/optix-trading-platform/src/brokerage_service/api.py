"""
Brokerage Service REST API
Multi-broker integration and portfolio sync endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict
import uuid
from .models import (
    BrokerageConnection, Portfolio, Position, Transaction,
    BrokerageProvider, ConnectBrokerageRequest, OAuthCallback,
    ConnectionStatus
)
from .repository import BrokerageRepository
from .sync_service import PortfolioSyncService


router = APIRouter(prefix="/api/v1", tags=["brokerage"])


def get_brokerage_repository() -> BrokerageRepository:
    """Get brokerage repository instance"""
    return BrokerageRepository()


def get_sync_service() -> PortfolioSyncService:
    """Get portfolio sync service instance"""
    return PortfolioSyncService()


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context"""
    # Mock user ID for development
    return uuid.uuid4()


@router.get("/brokerages", response_model=List[Dict])
async def list_available_brokerages():
    """
    List available brokerage providers
    
    Returns list of supported brokerages with connection instructions
    """
    return [
        {
            "provider": BrokerageProvider.SCHWAB,
            "name": "Charles Schwab",
            "method": "OAuth 2.0",
            "phase": "Month 2",
            "priority": "Must Have",
            "features": ["positions", "transactions", "real_time_sync"]
        },
        {
            "provider": BrokerageProvider.TD_AMERITRADE,
            "name": "TD Ameritrade",
            "method": "OAuth 2.0",
            "phase": "Month 2",
            "priority": "Must Have",
            "features": ["positions", "transactions", "real_time_sync"]
        },
        {
            "provider": BrokerageProvider.FIDELITY,
            "name": "Fidelity",
            "method": "OAuth 2.0",
            "phase": "Month 2",
            "priority": "Must Have",
            "features": ["positions", "transactions"]
        },
        {
            "provider": BrokerageProvider.ROBINHOOD,
            "name": "Robinhood",
            "method": "Plaid Integration",
            "phase": "Month 3",
            "priority": "Must Have",
            "features": ["positions", "transactions"]
        },
        {
            "provider": BrokerageProvider.INTERACTIVE_BROKERS,
            "name": "Interactive Brokers",
            "method": "Client Portal API",
            "phase": "Month 4",
            "priority": "Should Have",
            "features": ["positions", "transactions", "real_time_sync"]
        },
        {
            "provider": BrokerageProvider.WEBULL,
            "name": "Webull",
            "method": "Official API",
            "phase": "Month 4",
            "priority": "Should Have",
            "features": ["positions", "transactions"]
        }
    ]


@router.post("/brokerages/{provider}/connect")
async def initiate_brokerage_connection(
    provider: BrokerageProvider,
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Initiate OAuth flow for brokerage connection
    
    - **provider**: Brokerage provider to connect
    - Returns OAuth authorization URL
    
    **Performance**: Connection completes in < 60 seconds (AC)
    """
    # Generate OAuth state for CSRF protection
    state = str(uuid.uuid4())
    
    # Build OAuth URL based on provider
    oauth_urls = {
        BrokerageProvider.SCHWAB: f"https://api.schwabapi.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https://optix.app/oauth/callback/schwab&state={state}",
        BrokerageProvider.TD_AMERITRADE: f"https://auth.tdameritrade.com/auth?client_id=YOUR_CLIENT_ID&redirect_uri=https://optix.app/oauth/callback/tda&state={state}",
        BrokerageProvider.FIDELITY: f"https://api.fidelity.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https://optix.app/oauth/callback/fidelity&state={state}"
    }
    
    if provider not in oauth_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider {provider} not yet supported"
        )
    
    return {
        "authorization_url": oauth_urls[provider],
        "state": state,
        "provider": provider
    }


@router.get("/brokerages/{provider}/callback")
async def oauth_callback(
    provider: BrokerageProvider,
    code: str,
    state: str,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: BrokerageRepository = Depends(get_brokerage_repository),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Handle OAuth callback from brokerage
    
    - Exchanges authorization code for access token
    - Creates connection record
    - Triggers initial portfolio sync
    """
    # TODO: Verify state matches to prevent CSRF
    
    # Create connection with connecting status
    connection = BrokerageConnection(
        user_id=user_id,
        provider=provider,
        access_token="",  # Will be set by connector
        account_id="",
        status=ConnectionStatus.CONNECTING
    )
    
    # Save initial connection
    connection = repo.create_connection(connection)
    
    # Background task: Complete OAuth and sync
    background_tasks.add_task(
        complete_connection,
        connection.id,
        code,
        sync_service,
        repo
    )
    
    return {
        "message": "Connection initiated",
        "connection_id": str(connection.id),
        "status": "connecting"
    }


@router.delete("/brokerages/{connection_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_brokerage(
    connection_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: BrokerageRepository = Depends(get_brokerage_repository)
):
    """
    Disconnect and unlink brokerage account
    
    - Revokes access tokens
    - Deletes connection and associated data
    """
    connection = repo.get_connection(connection_id)
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    if connection.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # TODO: Revoke tokens with brokerage
    
    # Delete connection
    repo.delete_connection(connection_id)


@router.get("/portfolio", response_model=Portfolio)
async def get_unified_portfolio(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: BrokerageRepository = Depends(get_brokerage_repository),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Get unified portfolio view across all connected brokerages
    
    - Combines positions from all linked accounts
    - Calculates total portfolio value and P&L
    - Aggregates Greeks across all options positions
    
    **Performance**: < 2 seconds response time
    """
    portfolio = await sync_service.get_unified_portfolio(user_id)
    return portfolio


@router.get("/portfolio/positions", response_model=List[Position])
async def get_all_positions(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: BrokerageRepository = Depends(get_brokerage_repository)
):
    """
    Get all positions across all connected accounts
    
    Returns detailed position list with current P&L
    """
    positions = repo.get_user_positions(user_id)
    return positions


@router.get("/portfolio/performance")
async def get_portfolio_performance(
    user_id: uuid.UUID = Depends(get_current_user_id),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Get portfolio performance analytics
    
    - Total P&L (realized and unrealized)
    - Day change
    - Win rate
    - Risk metrics
    """
    performance = await sync_service.calculate_performance(user_id)
    return performance


@router.get("/transactions", response_model=List[Transaction])
async def get_transaction_history(
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = 100,
    repo: BrokerageRepository = Depends(get_brokerage_repository)
):
    """
    Get trade transaction history across all accounts
    
    - **limit**: Maximum number of transactions (default 100, max 500)
    """
    if limit > 500:
        limit = 500
    
    transactions = repo.get_user_transactions(user_id, limit)
    return transactions


@router.post("/portfolio/sync")
async def trigger_portfolio_sync(
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Manually trigger portfolio sync for all connected accounts
    
    - Sync completes in background
    - Returns immediately with status
    
    **Performance**: Sync completes within 30 seconds (AC)
    """
    # Trigger background sync
    background_tasks.add_task(sync_service.sync_all_accounts, user_id)
    
    return {
        "message": "Sync initiated",
        "status": "syncing"
    }


async def complete_connection(
    connection_id: uuid.UUID,
    authorization_code: str,
    sync_service: PortfolioSyncService,
    repo: BrokerageRepository
):
    """
    Complete OAuth flow and perform initial sync
    Background task
    """
    try:
        connection = repo.get_connection(connection_id)
        
        # Get appropriate connector
        connector = sync_service.get_connector(connection)
        
        # Exchange code for tokens
        token_data = await connector.authenticate(authorization_code)
        
        # Update connection with tokens
        repo.update_connection(connection_id, {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": token_data.get("expires_at"),
            "status": ConnectionStatus.CONNECTED
        })
        
        # Get account info
        account_info = await connector.get_account_info()
        repo.update_connection(connection_id, {
            "account_id": account_info.get("accountId"),
            "account_name": account_info.get("accountName"),
            "account_type": account_info.get("type", "individual")
        })
        
        # Perform initial sync
        await sync_service.sync_account(connection_id)
        
    except Exception as e:
        # Update connection with error
        repo.update_connection(connection_id, {
            "status": ConnectionStatus.ERROR,
            "sync_error": str(e)
        })


from typing import Dict
