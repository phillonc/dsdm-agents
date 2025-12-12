"""
Watchlist Service API
CRUD operations for user watchlists
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
from .models import (
    Watchlist, WatchlistCreate, WatchlistUpdate,
    AddSymbolRequest, RemoveSymbolRequest, WatchlistItem
)
from .repository import WatchlistRepository


router = APIRouter(prefix="/api/v1/watchlists", tags=["watchlists"])


def get_watchlist_repository() -> WatchlistRepository:
    """Get watchlist repository instance"""
    return WatchlistRepository()


def get_current_user_id() -> uuid.UUID:
    """
    Get current user ID from auth context
    In production, extract from JWT token
    """
    # Mock user ID for development
    return uuid.uuid4()


@router.get("", response_model=List[Watchlist])
async def list_watchlists(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    List all watchlists for current user
    
    Returns list of watchlists ordered by creation date
    """
    watchlists = repo.get_user_watchlists(user_id)
    return watchlists


@router.post("", response_model=Watchlist, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Create new watchlist
    
    - **name**: Watchlist name (1-50 characters)
    - **description**: Optional description
    - **is_default**: Set as default watchlist
    """
    # Check watchlist limit (10 per user)
    existing = repo.get_user_watchlists(user_id)
    if len(existing) >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 watchlists allowed per user"
        )
    
    # If setting as default, unset other defaults
    if watchlist_data.is_default:
        repo.unset_default_watchlists(user_id)
    
    watchlist = Watchlist(
        user_id=user_id,
        name=watchlist_data.name,
        description=watchlist_data.description,
        is_default=watchlist_data.is_default
    )
    
    created = repo.create_watchlist(watchlist)
    return created


@router.get("/{watchlist_id}", response_model=Watchlist)
async def get_watchlist(
    watchlist_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Get watchlist by ID
    """
    watchlist = repo.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    # Verify ownership
    if watchlist.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return watchlist


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: uuid.UUID,
    updates: WatchlistUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Update watchlist metadata
    
    - **name**: New watchlist name
    - **description**: New description
    - **is_default**: Update default status
    """
    watchlist = repo.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    if watchlist.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # If setting as default, unset others
    if updates.is_default:
        repo.unset_default_watchlists(user_id)
    
    updated = repo.update_watchlist(watchlist_id, updates.dict(exclude_unset=True))
    return updated


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Delete watchlist
    """
    watchlist = repo.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    if watchlist.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    repo.delete_watchlist(watchlist_id)


@router.post("/{watchlist_id}/symbols", response_model=Watchlist)
async def add_symbol(
    watchlist_id: uuid.UUID,
    symbol_data: AddSymbolRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Add symbol to watchlist
    
    - Maximum 50 symbols per watchlist
    - Duplicate symbols are ignored
    """
    watchlist = repo.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    if watchlist.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check symbol limit
    if len(watchlist.symbols) >= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 symbols reached"
        )
    
    # Check for duplicate
    if any(item.symbol == symbol_data.symbol for item in watchlist.symbols):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol_data.symbol} already in watchlist"
        )
    
    # Add symbol
    item = WatchlistItem(
        symbol=symbol_data.symbol,
        notes=symbol_data.notes
    )
    watchlist.symbols.append(item)
    
    updated = repo.update_watchlist(watchlist_id, {"symbols": watchlist.symbols})
    return updated


@router.delete("/{watchlist_id}/symbols", response_model=Watchlist)
async def remove_symbol(
    watchlist_id: uuid.UUID,
    symbol_data: RemoveSymbolRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: WatchlistRepository = Depends(get_watchlist_repository)
):
    """
    Remove symbol from watchlist
    """
    watchlist = repo.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    if watchlist.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Remove symbol
    watchlist.symbols = [
        item for item in watchlist.symbols
        if item.symbol != symbol_data.symbol
    ]
    
    updated = repo.update_watchlist(watchlist_id, {"symbols": watchlist.symbols})
    return updated
