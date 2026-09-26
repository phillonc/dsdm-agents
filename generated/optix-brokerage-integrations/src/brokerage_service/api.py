"""
FastAPI REST API for brokerage service
Includes CSRF protection and token revocation
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import json
import logging

# Redis for OAuth state management
try:
    import redis.asyncio as redis
except ImportError:
    import redis

from .models import (
    BrokerageProvider,
    BrokerageConnection,
    Portfolio,
    Position,
    Transaction,
)
from .repository import BrokerageRepository
from .sync_service import PortfolioSyncService
from .settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OPTIX Brokerage API",
    description="Universal brokerage integration API",
    version="1.0.0"
)

# Dependency injection
def get_repository() -> BrokerageRepository:
    """Get repository instance"""
    # In production, this would inject database session
    return BrokerageRepository()

def get_sync_service(repo: BrokerageRepository = Depends(get_repository)) -> PortfolioSyncService:
    """Get sync service instance"""
    return PortfolioSyncService(repo)

async def get_redis() -> redis.Redis:
    """Get Redis client for OAuth state management"""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


# Request/Response Models

class ConnectRequest(BaseModel):
    """Request to initiate brokerage connection"""
    provider: BrokerageProvider
    user_id: uuid.UUID

class ConnectResponse(BaseModel):
    """Response with OAuth authorization URL"""
    authorization_url: str
    state: str
    provider: BrokerageProvider

class OAuthCallbackRequest(BaseModel):
    """OAuth callback data"""
    code: str
    state: str

class ConnectionResponse(BaseModel):
    """Brokerage connection response"""
    id: uuid.UUID
    provider: BrokerageProvider
    account_id: str
    account_name: Optional[str]
    is_active: bool
    last_synced_at: Optional[datetime]
    created_at: datetime

class SyncResponse(BaseModel):
    """Sync operation response"""
    success: bool
    accounts_synced: int
    positions_synced: int
    transactions_synced: int
    synced_at: datetime

class DayChangeResponse(BaseModel):
    """Day P&L response"""
    day_pl: str
    day_pl_percent: str
    total_value: str
    start_of_day_value: str


# API Endpoints

@app.get("/api/v1/brokerages")
async def list_supported_brokerages():
    """
    List all supported brokerage providers
    """
    return {
        "brokerages": [
            {
                "id": "schwab",
                "name": "Charles Schwab",
                "status": "active",
                "oauth_type": "OAuth 2.0"
            },
            {
                "id": "fidelity",
                "name": "Fidelity",
                "status": "active",
                "oauth_type": "OAuth 2.0"
            },
            {
                "id": "robinhood",
                "name": "Robinhood",
                "status": "active",
                "oauth_type": "Plaid"
            },
            {
                "id": "ibkr",
                "name": "Interactive Brokers",
                "status": "active",
                "oauth_type": "OAuth 2.0"
            },
            {
                "id": "webull",
                "name": "Webull",
                "status": "active",
                "oauth_type": "OAuth 2.0"
            }
        ]
    }

@app.post("/api/v1/brokerages/{provider}/connect", response_model=ConnectResponse)
async def initiate_brokerage_connection(
    provider: BrokerageProvider,
    user_id: uuid.UUID = Query(...),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Initiate OAuth connection to brokerage
    Includes CSRF protection via state parameter
    
    Args:
        provider: Brokerage provider
        user_id: User ID
        redis_client: Redis client for state storage
        
    Returns:
        Authorization URL and state for OAuth flow
    """
    # Generate CSRF state token
    state = str(uuid.uuid4())
    
    # Store state in Redis with expiry
    state_data = {
        "user_id": str(user_id),
        "provider": provider,
        "created_at": datetime.utcnow().isoformat()
    }
    
    await redis_client.setex(
        f"oauth_state:{state}",
        timedelta(minutes=settings.oauth_state_ttl_minutes),
        json.dumps(state_data)
    )
    
    # Build authorization URL based on provider
    auth_urls = {
        BrokerageProvider.SCHWAB: "https://api.schwabapi.com/v1/oauth/authorize",
        BrokerageProvider.FIDELITY: "https://api.fidelity.com/oauth2/authorize",
        BrokerageProvider.ROBINHOOD: "https://plaid.com/link",  # Plaid Link URL
        BrokerageProvider.IBKR: "https://www.interactivebrokers.com/authorize",
        BrokerageProvider.WEBULL: "https://www.webull.com/oauth2/authorize",
    }
    
    base_url = auth_urls.get(provider)
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider {provider} not supported"
        )
    
    # Build full authorization URL with parameters
    auth_url = f"{base_url}?client_id=CLIENT_ID&response_type=code&state={state}&redirect_uri=REDIRECT_URI"
    
    logger.info(f"Initiated connection for user {user_id} to {provider}")
    
    return ConnectResponse(
        authorization_url=auth_url,
        state=state,
        provider=provider
    )

@app.get("/api/v1/brokerages/{provider}/callback")
async def oauth_callback(
    provider: BrokerageProvider,
    code: str = Query(...),
    state: str = Query(...),
    redis_client: redis.Redis = Depends(get_redis),
    repo: BrokerageRepository = Depends(get_repository),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    OAuth callback endpoint
    Validates CSRF state and exchanges code for tokens
    
    Args:
        provider: Brokerage provider
        code: OAuth authorization code
        state: CSRF state token
        redis_client: Redis client
        repo: Repository
        sync_service: Sync service
        
    Returns:
        Connection confirmation
    """
    # Verify CSRF state
    state_data_json = await redis_client.get(f"oauth_state:{state}")
    
    if not state_data_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state"
        )
    
    state_data = json.loads(state_data_json)
    
    # Verify provider matches
    if state_data["provider"] != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch"
        )
    
    # Delete state (one-time use)
    await redis_client.delete(f"oauth_state:{state}")
    
    user_id = uuid.UUID(state_data["user_id"])
    
    # Create connection record
    connection = BrokerageConnection(
        user_id=user_id,
        provider=provider,
        account_id="temporary",  # Will be updated after authentication
        _access_token_encrypted="",  # Will be set after authentication
    )
    
    # Get connector and authenticate
    connector = sync_service.get_connector(connection)
    
    try:
        auth_data = await connector.authenticate(code)
        
        # Update connection with real data
        connection.access_token = auth_data["access_token"]
        if auth_data.get("refresh_token"):
            connection.refresh_token = auth_data["refresh_token"]
        connection.token_expires_at = auth_data.get("expires_at")
        connection.account_id = auth_data["account_id"]
        connection.account_name = auth_data.get("account_name")
        
        # Save connection
        connection = repo.create_connection(connection)
        
        # Trigger initial sync (async)
        await sync_service.sync_account(connection.id)
        
        logger.info(f"Successfully connected {provider} for user {user_id}")
        
        return {
            "success": True,
            "connection_id": str(connection.id),
            "message": f"{provider} account connected successfully"
        }
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect account: {str(e)}"
        )

@app.delete("/api/v1/brokerages/{connection_id}/disconnect")
async def disconnect_brokerage(
    connection_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
    repo: BrokerageRepository = Depends(get_repository),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Disconnect brokerage and revoke tokens
    
    Args:
        connection_id: Connection ID to disconnect
        user_id: User ID for authorization
        repo: Repository
        sync_service: Sync service
        
    Returns:
        Confirmation of disconnection
    """
    connection = repo.get_connection(connection_id)
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Verify ownership
    if connection.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Revoke tokens with brokerage
    connector = sync_service.get_connector(connection)
    
    try:
        await connector.disconnect()
        logger.info(f"Successfully revoked tokens for connection {connection_id}")
    except Exception as e:
        # Log but don't fail - we still want to remove local connection
        logger.warning(f"Token revocation failed: {e}")
    
    # Delete all associated data
    repo.delete_positions_for_connection(connection_id)
    repo.delete_transactions_for_connection(connection_id)
    repo.delete_connection(connection_id)
    
    logger.info(f"Disconnected and cleaned up connection {connection_id}")
    
    return {
        "success": True,
        "message": "Brokerage disconnected successfully"
    }

@app.get("/api/v1/portfolio", response_model=Portfolio)
async def get_portfolio(
    user_id: uuid.UUID = Query(...),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Get unified portfolio across all connected brokerages
    Includes complete cash, realized P&L, and day P&L calculations
    
    Args:
        user_id: User ID
        sync_service: Sync service
        
    Returns:
        Complete portfolio data
    """
    try:
        portfolio = await sync_service.get_unified_portfolio(user_id)
        return portfolio
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio: {str(e)}"
        )

@app.get("/api/v1/portfolio/positions", response_model=List[Position])
async def get_positions(
    user_id: uuid.UUID = Query(...),
    repo: BrokerageRepository = Depends(get_repository)
):
    """
    Get all positions for user
    
    Args:
        user_id: User ID
        repo: Repository
        
    Returns:
        List of positions
    """
    positions = repo.get_user_positions(user_id)
    return positions

@app.get("/api/v1/portfolio/day-change", response_model=DayChangeResponse)
async def get_day_change(
    user_id: uuid.UUID = Query(...),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Get day P&L details
    
    Args:
        user_id: User ID
        sync_service: Sync service
        
    Returns:
        Day P&L information
    """
    day_pl, day_pl_percent = await sync_service._calculate_day_pl(user_id)
    portfolio = await sync_service.get_unified_portfolio(user_id)
    
    # Calculate start of day value
    start_of_day_value = portfolio.total_value - day_pl
    
    return DayChangeResponse(
        day_pl=str(day_pl),
        day_pl_percent=str(day_pl_percent),
        total_value=str(portfolio.total_value),
        start_of_day_value=str(start_of_day_value)
    )

@app.post("/api/v1/portfolio/sync", response_model=SyncResponse)
async def sync_portfolio(
    user_id: uuid.UUID = Query(...),
    sync_service: PortfolioSyncService = Depends(get_sync_service)
):
    """
    Trigger portfolio sync for all connected accounts
    
    Args:
        user_id: User ID
        sync_service: Sync service
        
    Returns:
        Sync statistics
    """
    try:
        result = await sync_service.sync_all_accounts(user_id)
        
        return SyncResponse(
            success=True,
            accounts_synced=result["accounts"],
            positions_synced=result["positions"],
            transactions_synced=result["transactions"],
            synced_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Portfolio sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )

@app.get("/api/v1/transactions", response_model=List[Transaction])
async def get_transactions(
    user_id: uuid.UUID = Query(...),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    repo: BrokerageRepository = Depends(get_repository)
):
    """
    Get transaction history
    
    Args:
        user_id: User ID
        start_date: Start date filter
        end_date: End date filter
        limit: Max number of transactions
        repo: Repository
        
    Returns:
        List of transactions
    """
    transactions = repo.get_user_transactions(
        user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return transactions

@app.get("/api/v1/brokerages/connections", response_model=List[ConnectionResponse])
async def list_connections(
    user_id: uuid.UUID = Query(...),
    repo: BrokerageRepository = Depends(get_repository)
):
    """
    List all connected brokerages for user
    
    Args:
        user_id: User ID
        repo: Repository
        
    Returns:
        List of connections
    """
    connections = repo.get_user_connections(user_id)
    
    return [
        ConnectionResponse(
            id=conn.id,
            provider=conn.provider,
            account_id=conn.account_id,
            account_name=conn.account_name,
            is_active=conn.is_active,
            last_synced_at=conn.last_synced_at,
            created_at=conn.created_at
        )
        for conn in connections
    ]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "brokerage-api", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
