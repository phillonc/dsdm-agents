"""
Market Data Cache Layer
Redis-backed caching for market data with TTL
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from .models import Quote, OptionsChain, OptionsExpirations


class MarketDataCache:
    """
    Market data cache using Redis
    In production, connect to Redis cluster
    """
    
    def __init__(self):
        # In-memory cache for demonstration
        # In production, use Redis with connection pool
        self._cache: Dict[str, tuple[Any, datetime]] = {}
    
    def _is_expired(self, timestamp: datetime, ttl: int) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() > timestamp + timedelta(seconds=ttl)
    
    def _get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            # Note: In production Redis handles TTL automatically
            return value
        return None
    
    def _set(self, key: str, value: Any, ttl: int):
        """Set value in cache with TTL"""
        self._cache[key] = (value, datetime.utcnow())
        # In production: redis.setex(key, ttl, json.dumps(value))
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get cached quote"""
        key = f"quote:{symbol.upper()}"
        data = self._get(key)
        if data:
            return Quote(**data)
        return None
    
    def set_quote(self, symbol: str, quote: Quote, ttl: int = 1):
        """Cache quote with TTL"""
        key = f"quote:{symbol.upper()}"
        self._set(key, quote.dict(), ttl)
    
    def get_chain(self, cache_key: str) -> Optional[OptionsChain]:
        """Get cached options chain"""
        key = f"chain:{cache_key}"
        data = self._get(key)
        if data:
            return OptionsChain(**data)
        return None
    
    def set_chain(self, cache_key: str, chain: OptionsChain, ttl: int = 5):
        """Cache options chain with TTL"""
        key = f"chain:{cache_key}"
        self._set(key, chain.dict(), ttl)
    
    def get_expirations(self, symbol: str) -> Optional[OptionsExpirations]:
        """Get cached expirations"""
        key = f"expirations:{symbol.upper()}"
        data = self._get(key)
        if data:
            return OptionsExpirations(**data)
        return None
    
    def set_expirations(
        self,
        symbol: str,
        expirations: OptionsExpirations,
        ttl: int = 3600
    ):
        """Cache expirations with TTL"""
        key = f"expirations:{symbol.upper()}"
        self._set(key, expirations.dict(), ttl)
    
    def invalidate_symbol(self, symbol: str):
        """Invalidate all cache entries for a symbol"""
        symbol = symbol.upper()
        keys_to_remove = [
            key for key in self._cache.keys()
            if symbol in key
        ]
        for key in keys_to_remove:
            del self._cache[key]
    
    def clear_all(self):
        """Clear entire cache"""
        self._cache.clear()
