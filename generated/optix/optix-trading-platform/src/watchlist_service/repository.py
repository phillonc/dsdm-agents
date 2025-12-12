"""
Watchlist Repository
Data access layer for watchlist operations
"""
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import Watchlist


class WatchlistRepository:
    """
    Watchlist repository for database operations
    In production, use PostgreSQL with proper indexing
    """
    
    def __init__(self):
        # In-memory storage for demonstration
        self._watchlists: Dict[uuid.UUID, Watchlist] = {}
        self._user_index: Dict[uuid.UUID, List[uuid.UUID]] = {}
    
    def create_watchlist(self, watchlist: Watchlist) -> Watchlist:
        """Create new watchlist"""
        self._watchlists[watchlist.id] = watchlist
        
        # Update user index
        if watchlist.user_id not in self._user_index:
            self._user_index[watchlist.user_id] = []
        self._user_index[watchlist.user_id].append(watchlist.id)
        
        return watchlist
    
    def get_watchlist(self, watchlist_id: uuid.UUID) -> Optional[Watchlist]:
        """Get watchlist by ID"""
        return self._watchlists.get(watchlist_id)
    
    def get_user_watchlists(self, user_id: uuid.UUID) -> List[Watchlist]:
        """Get all watchlists for a user"""
        watchlist_ids = self._user_index.get(user_id, [])
        watchlists = [
            self._watchlists[wid]
            for wid in watchlist_ids
            if wid in self._watchlists
        ]
        return sorted(watchlists, key=lambda w: w.created_at)
    
    def update_watchlist(
        self,
        watchlist_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Watchlist:
        """Update watchlist"""
        watchlist = self._watchlists.get(watchlist_id)
        if not watchlist:
            raise ValueError("Watchlist not found")
        
        for key, value in updates.items():
            if hasattr(watchlist, key):
                setattr(watchlist, key, value)
        
        watchlist.updated_at = datetime.utcnow()
        return watchlist
    
    def delete_watchlist(self, watchlist_id: uuid.UUID) -> bool:
        """Delete watchlist"""
        watchlist = self._watchlists.get(watchlist_id)
        if not watchlist:
            return False
        
        # Remove from storage
        del self._watchlists[watchlist_id]
        
        # Update user index
        if watchlist.user_id in self._user_index:
            self._user_index[watchlist.user_id].remove(watchlist_id)
        
        return True
    
    def unset_default_watchlists(self, user_id: uuid.UUID):
        """Unset default flag for all user watchlists"""
        for watchlist in self.get_user_watchlists(user_id):
            watchlist.is_default = False
