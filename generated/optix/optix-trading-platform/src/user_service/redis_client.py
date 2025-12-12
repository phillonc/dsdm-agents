"""
Redis Client for OPTIX Trading Platform
Provides Redis connection management and utilities
"""
from typing import Optional, Any, Dict, List
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
import json
import pickle
from datetime import timedelta
from contextlib import asynccontextmanager
import structlog

logger = structlog.get_logger(__name__)


class RedisClient:
    """
    Async Redis client wrapper with connection pooling and utilities
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_connections: int = 50,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True
    ):
        self.redis_url = redis_url
        self.decode_responses = decode_responses
        
        # Create connection pool
        self.pool = ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=decode_responses,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout
        )
        
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            self._redis = redis.Redis(connection_pool=self.pool)
            await self._redis.ping()
            logger.info("redis_connected", url=self.redis_url)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.aclose()
            await self.pool.aclose()
            logger.info("redis_disconnected")
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis client instance"""
        if not self._redis:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._redis
    
    # Key-Value Operations
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = False
    ) -> bool:
        """
        Set a key-value pair
        
        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds
            serialize: Whether to JSON serialize the value
        
        Returns:
            True if successful
        """
        try:
            if serialize:
                value = json.dumps(value)
            
            if ttl:
                return await self.redis.setex(key, ttl, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error("redis_set_error", key=key, error=str(e))
            raise
    
    async def get(
        self,
        key: str,
        deserialize: bool = False
    ) -> Optional[Any]:
        """
        Get value by key
        
        Args:
            key: Redis key
            deserialize: Whether to JSON deserialize the value
        
        Returns:
            Value or None if not found
        """
        try:
            value = await self.redis.get(key)
            
            if value and deserialize:
                return json.loads(value)
            
            return value
        except Exception as e:
            logger.error("redis_get_error", key=key, error=str(e))
            raise
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys
        
        Returns:
            Number of keys deleted
        """
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error("redis_delete_error", keys=keys, error=str(e))
            raise
    
    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist
        
        Returns:
            Number of existing keys
        """
        try:
            return await self.redis.exists(*keys)
        except Exception as e:
            logger.error("redis_exists_error", keys=keys, error=str(e))
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error("redis_expire_error", key=key, error=str(e))
            raise
    
    async def ttl(self, key: str) -> int:
        """
        Get time to live for a key
        
        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error("redis_ttl_error", key=key, error=str(e))
            raise
    
    # Hash Operations
    
    async def hset(
        self,
        key: str,
        field: str,
        value: Any,
        serialize: bool = False
    ) -> int:
        """Set hash field"""
        try:
            if serialize:
                value = json.dumps(value)
            return await self.redis.hset(key, field, value)
        except Exception as e:
            logger.error("redis_hset_error", key=key, field=field, error=str(e))
            raise
    
    async def hget(
        self,
        key: str,
        field: str,
        deserialize: bool = False
    ) -> Optional[Any]:
        """Get hash field"""
        try:
            value = await self.redis.hget(key, field)
            
            if value and deserialize:
                return json.loads(value)
            
            return value
        except Exception as e:
            logger.error("redis_hget_error", key=key, field=field, error=str(e))
            raise
    
    async def hgetall(
        self,
        key: str,
        deserialize: bool = False
    ) -> Dict:
        """Get all hash fields"""
        try:
            data = await self.redis.hgetall(key)
            
            if deserialize and data:
                return {k: json.loads(v) for k, v in data.items()}
            
            return data
        except Exception as e:
            logger.error("redis_hgetall_error", key=key, error=str(e))
            raise
    
    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields"""
        try:
            return await self.redis.hdel(key, *fields)
        except Exception as e:
            logger.error("redis_hdel_error", key=key, fields=fields, error=str(e))
            raise
    
    async def hexists(self, key: str, field: str) -> bool:
        """Check if hash field exists"""
        try:
            return await self.redis.hexists(key, field)
        except Exception as e:
            logger.error("redis_hexists_error", key=key, field=field, error=str(e))
            raise
    
    # Set Operations
    
    async def sadd(self, key: str, *members: Any) -> int:
        """Add members to a set"""
        try:
            return await self.redis.sadd(key, *members)
        except Exception as e:
            logger.error("redis_sadd_error", key=key, error=str(e))
            raise
    
    async def srem(self, key: str, *members: Any) -> int:
        """Remove members from a set"""
        try:
            return await self.redis.srem(key, *members)
        except Exception as e:
            logger.error("redis_srem_error", key=key, error=str(e))
            raise
    
    async def smembers(self, key: str) -> set:
        """Get all set members"""
        try:
            return await self.redis.smembers(key)
        except Exception as e:
            logger.error("redis_smembers_error", key=key, error=str(e))
            raise
    
    async def sismember(self, key: str, member: Any) -> bool:
        """Check if member is in set"""
        try:
            return await self.redis.sismember(key, member)
        except Exception as e:
            logger.error("redis_sismember_error", key=key, member=member, error=str(e))
            raise
    
    # List Operations
    
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list"""
        try:
            return await self.redis.lpush(key, *values)
        except Exception as e:
            logger.error("redis_lpush_error", key=key, error=str(e))
            raise
    
    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to the right of a list"""
        try:
            return await self.redis.rpush(key, *values)
        except Exception as e:
            logger.error("redis_rpush_error", key=key, error=str(e))
            raise
    
    async def lrange(self, key: str, start: int, end: int) -> List:
        """Get list range"""
        try:
            return await self.redis.lrange(key, start, end)
        except Exception as e:
            logger.error("redis_lrange_error", key=key, error=str(e))
            raise
    
    async def lpop(self, key: str) -> Optional[Any]:
        """Pop value from the left of a list"""
        try:
            return await self.redis.lpop(key)
        except Exception as e:
            logger.error("redis_lpop_error", key=key, error=str(e))
            raise
    
    async def rpop(self, key: str) -> Optional[Any]:
        """Pop value from the right of a list"""
        try:
            return await self.redis.rpop(key)
        except Exception as e:
            logger.error("redis_rpop_error", key=key, error=str(e))
            raise
    
    # Sorted Set Operations
    
    async def zadd(
        self,
        key: str,
        mapping: Dict[Any, float],
        nx: bool = False,
        xx: bool = False
    ) -> int:
        """Add members to sorted set"""
        try:
            return await self.redis.zadd(key, mapping, nx=nx, xx=xx)
        except Exception as e:
            logger.error("redis_zadd_error", key=key, error=str(e))
            raise
    
    async def zrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False
    ) -> List:
        """Get sorted set range"""
        try:
            return await self.redis.zrange(key, start, end, withscores=withscores)
        except Exception as e:
            logger.error("redis_zrange_error", key=key, error=str(e))
            raise
    
    async def zrem(self, key: str, *members: Any) -> int:
        """Remove members from sorted set"""
        try:
            return await self.redis.zrem(key, *members)
        except Exception as e:
            logger.error("redis_zrem_error", key=key, error=str(e))
            raise
    
    async def zscore(self, key: str, member: Any) -> Optional[float]:
        """Get score of member in sorted set"""
        try:
            return await self.redis.zscore(key, member)
        except Exception as e:
            logger.error("redis_zscore_error", key=key, member=member, error=str(e))
            raise
    
    # Pattern Operations
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (use with caution in production)"""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.error("redis_keys_error", pattern=pattern, error=str(e))
            raise
    
    async def scan(
        self,
        cursor: int = 0,
        match: Optional[str] = None,
        count: Optional[int] = None
    ):
        """Scan keys (recommended over KEYS in production)"""
        try:
            return await self.redis.scan(cursor=cursor, match=match, count=count)
        except Exception as e:
            logger.error("redis_scan_error", error=str(e))
            raise
    
    # Pub/Sub Operations
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            return await self.redis.publish(channel, message)
        except Exception as e:
            logger.error("redis_publish_error", channel=channel, error=str(e))
            raise
    
    # Utility Methods
    
    async def ping(self) -> bool:
        """Check if Redis is available"""
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error("redis_ping_error", error=str(e))
            return False
    
    async def flushdb(self) -> bool:
        """Flush current database (use with extreme caution!)"""
        try:
            return await self.redis.flushdb()
        except Exception as e:
            logger.error("redis_flushdb_error", error=str(e))
            raise
    
    async def info(self, section: Optional[str] = None) -> Dict:
        """Get Redis server information"""
        try:
            return await self.redis.info(section)
        except Exception as e:
            logger.error("redis_info_error", error=str(e))
            raise
    
    # Context Manager Support
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Singleton instance
_redis_client: Optional[RedisClient] = None


def get_redis_client(redis_url: Optional[str] = None, **kwargs) -> RedisClient:
    """
    Get Redis client singleton
    
    Args:
        redis_url: Redis connection URL
        **kwargs: Additional RedisClient arguments
    
    Returns:
        RedisClient instance
    """
    global _redis_client
    if _redis_client is None:
        if redis_url is None:
            from config.settings import settings
            redis_url = settings.REDIS_URL
        _redis_client = RedisClient(redis_url=redis_url, **kwargs)
    return _redis_client


async def init_redis(redis_url: Optional[str] = None, **kwargs) -> RedisClient:
    """
    Initialize and connect Redis client
    
    Args:
        redis_url: Redis connection URL
        **kwargs: Additional RedisClient arguments
    
    Returns:
        Connected RedisClient instance
    """
    client = get_redis_client(redis_url, **kwargs)
    await client.connect()
    return client
