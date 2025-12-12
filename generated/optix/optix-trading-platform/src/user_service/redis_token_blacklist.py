"""
Redis-backed Token Blacklist Service
Implements token revocation and blacklisting with Redis for high performance
"""
from typing import Optional, List, Set
from datetime import datetime, timedelta
import uuid
import structlog
from .redis_client import RedisClient, get_redis_client

logger = structlog.get_logger(__name__)


class RedisTokenBlacklist:
    """
    Redis-backed token blacklist for JWT revocation
    Uses Redis sets and key expiration for efficient token revocation
    """
    
    # Redis key prefixes
    KEY_PREFIX_BLACKLIST = "token:blacklist:"
    KEY_PREFIX_USER_TOKENS = "token:user:"
    KEY_PREFIX_FAMILY = "token:family:"
    KEY_PREFIX_REVOKED_FAMILIES = "token:revoked_families"
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize token blacklist
        
        Args:
            redis_client: RedisClient instance (uses singleton if not provided)
        """
        self.redis = redis_client or get_redis_client()
    
    # Token Blacklisting
    
    async def blacklist_token(
        self,
        jti: str,
        ttl_seconds: int,
        user_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Add token to blacklist with automatic expiration
        
        Args:
            jti: JWT ID (unique token identifier)
            ttl_seconds: Time until token naturally expires
            user_id: Optional user ID for tracking
            reason: Optional reason for blacklisting
        
        Returns:
            True if successfully blacklisted
        """
        try:
            key = f"{self.KEY_PREFIX_BLACKLIST}{jti}"
            
            # Store blacklist entry with metadata
            metadata = {
                "blacklisted_at": datetime.utcnow().isoformat(),
                "reason": reason or "manual_revocation"
            }
            
            if user_id:
                metadata["user_id"] = str(user_id)
            
            # Set with TTL matching token expiration
            success = await self.redis.set(
                key,
                metadata,
                ttl=ttl_seconds,
                serialize=True
            )
            
            # Track user's blacklisted tokens
            if user_id:
                await self._add_to_user_blacklist(user_id, jti, ttl_seconds)
            
            if success:
                logger.info(
                    "token_blacklisted",
                    jti=jti,
                    user_id=str(user_id) if user_id else None,
                    ttl=ttl_seconds,
                    reason=reason
                )
            
            return success
        except Exception as e:
            logger.error("token_blacklist_error", jti=jti, error=str(e))
            raise
    
    async def is_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            jti: JWT ID to check
        
        Returns:
            True if token is blacklisted
        """
        try:
            key = f"{self.KEY_PREFIX_BLACKLIST}{jti}"
            exists = await self.redis.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error("token_blacklist_check_error", jti=jti, error=str(e))
            # Fail closed - assume blacklisted on error
            return True
    
    async def remove_from_blacklist(self, jti: str) -> bool:
        """
        Remove token from blacklist (rare operation)
        
        Args:
            jti: JWT ID to remove
        
        Returns:
            True if removed
        """
        try:
            key = f"{self.KEY_PREFIX_BLACKLIST}{jti}"
            deleted = await self.redis.delete(key)
            
            if deleted:
                logger.info("token_unblacklisted", jti=jti)
            
            return bool(deleted)
        except Exception as e:
            logger.error("token_unblacklist_error", jti=jti, error=str(e))
            raise
    
    async def get_blacklist_info(self, jti: str) -> Optional[dict]:
        """
        Get blacklist entry metadata
        
        Args:
            jti: JWT ID
        
        Returns:
            Metadata dict or None if not blacklisted
        """
        try:
            key = f"{self.KEY_PREFIX_BLACKLIST}{jti}"
            return await self.redis.get(key, deserialize=True)
        except Exception as e:
            logger.error("get_blacklist_info_error", jti=jti, error=str(e))
            return None
    
    # User Token Management
    
    async def _add_to_user_blacklist(
        self,
        user_id: uuid.UUID,
        jti: str,
        ttl_seconds: int
    ) -> bool:
        """
        Track blacklisted token for user
        
        Args:
            user_id: User ID
            jti: JWT ID
            ttl_seconds: TTL for the set entry
        
        Returns:
            True if added
        """
        try:
            key = f"{self.KEY_PREFIX_USER_TOKENS}{user_id}"
            await self.redis.sadd(key, jti)
            
            # Set expiration on the entire set (refreshed on each add)
            await self.redis.expire(key, ttl_seconds)
            
            return True
        except Exception as e:
            logger.error(
                "user_blacklist_add_error",
                user_id=str(user_id),
                jti=jti,
                error=str(e)
            )
            return False
    
    async def get_user_blacklisted_tokens(
        self,
        user_id: uuid.UUID
    ) -> Set[str]:
        """
        Get all blacklisted tokens for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Set of JTIs
        """
        try:
            key = f"{self.KEY_PREFIX_USER_TOKENS}{user_id}"
            return await self.redis.smembers(key)
        except Exception as e:
            logger.error(
                "get_user_blacklisted_tokens_error",
                user_id=str(user_id),
                error=str(e)
            )
            return set()
    
    async def blacklist_all_user_tokens(
        self,
        user_id: uuid.UUID,
        token_jtis: List[str],
        ttl_seconds: int = 3600,
        reason: Optional[str] = None
    ) -> int:
        """
        Blacklist all tokens for a user
        
        Args:
            user_id: User ID
            token_jtis: List of JTIs to blacklist
            ttl_seconds: TTL for blacklist entries
            reason: Reason for mass blacklist
        
        Returns:
            Number of tokens blacklisted
        """
        try:
            count = 0
            for jti in token_jtis:
                success = await self.blacklist_token(
                    jti=jti,
                    ttl_seconds=ttl_seconds,
                    user_id=user_id,
                    reason=reason or "user_logout_all"
                )
                if success:
                    count += 1
            
            logger.info(
                "user_tokens_blacklisted",
                user_id=str(user_id),
                count=count,
                reason=reason
            )
            
            return count
        except Exception as e:
            logger.error(
                "blacklist_user_tokens_error",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    # Token Family Management (for refresh token rotation)
    
    async def blacklist_token_family(
        self,
        family_id: str,
        ttl_seconds: int = 2592000,  # 30 days default
        reason: Optional[str] = None
    ) -> bool:
        """
        Blacklist an entire token family (e.g., after token reuse detected)
        
        Args:
            family_id: Token family ID
            ttl_seconds: TTL for blacklist entry
            reason: Reason for blacklisting
        
        Returns:
            True if successful
        """
        try:
            # Add to revoked families set
            await self.redis.sadd(self.KEY_PREFIX_REVOKED_FAMILIES, family_id)
            
            # Store family blacklist metadata
            key = f"{self.KEY_PREFIX_FAMILY}{family_id}"
            metadata = {
                "revoked_at": datetime.utcnow().isoformat(),
                "reason": reason or "token_reuse_detected",
                "family_id": family_id
            }
            
            await self.redis.set(
                key,
                metadata,
                ttl=ttl_seconds,
                serialize=True
            )
            
            logger.warning(
                "token_family_blacklisted",
                family_id=family_id,
                reason=reason
            )
            
            return True
        except Exception as e:
            logger.error(
                "blacklist_family_error",
                family_id=family_id,
                error=str(e)
            )
            raise
    
    async def is_family_blacklisted(self, family_id: str) -> bool:
        """
        Check if token family is blacklisted
        
        Args:
            family_id: Token family ID
        
        Returns:
            True if family is blacklisted
        """
        try:
            return await self.redis.sismember(
                self.KEY_PREFIX_REVOKED_FAMILIES,
                family_id
            )
        except Exception as e:
            logger.error(
                "check_family_blacklist_error",
                family_id=family_id,
                error=str(e)
            )
            # Fail closed
            return True
    
    async def remove_family_from_blacklist(self, family_id: str) -> bool:
        """
        Remove token family from blacklist
        
        Args:
            family_id: Token family ID
        
        Returns:
            True if removed
        """
        try:
            removed = await self.redis.srem(
                self.KEY_PREFIX_REVOKED_FAMILIES,
                family_id
            )
            
            # Also remove metadata
            key = f"{self.KEY_PREFIX_FAMILY}{family_id}"
            await self.redis.delete(key)
            
            if removed:
                logger.info("token_family_unblacklisted", family_id=family_id)
            
            return bool(removed)
        except Exception as e:
            logger.error(
                "remove_family_blacklist_error",
                family_id=family_id,
                error=str(e)
            )
            raise
    
    # Batch Operations
    
    async def blacklist_tokens_batch(
        self,
        token_entries: List[dict]
    ) -> int:
        """
        Blacklist multiple tokens in batch
        
        Args:
            token_entries: List of dicts with 'jti', 'ttl_seconds', 'user_id', 'reason'
        
        Returns:
            Number of tokens blacklisted
        """
        try:
            count = 0
            for entry in token_entries:
                success = await self.blacklist_token(
                    jti=entry["jti"],
                    ttl_seconds=entry.get("ttl_seconds", 3600),
                    user_id=entry.get("user_id"),
                    reason=entry.get("reason")
                )
                if success:
                    count += 1
            
            logger.info("tokens_blacklisted_batch", count=count)
            return count
        except Exception as e:
            logger.error("blacklist_batch_error", error=str(e))
            raise
    
    async def check_tokens_batch(self, jtis: List[str]) -> dict:
        """
        Check multiple tokens for blacklist status
        
        Args:
            jtis: List of JWT IDs
        
        Returns:
            Dict mapping JTI to blacklist status
        """
        try:
            results = {}
            for jti in jtis:
                results[jti] = await self.is_blacklisted(jti)
            return results
        except Exception as e:
            logger.error("check_batch_error", error=str(e))
            raise
    
    # Statistics and Monitoring
    
    async def get_stats(self) -> dict:
        """
        Get blacklist statistics
        
        Returns:
            Statistics dict
        """
        try:
            # Count blacklisted tokens (approximate)
            cursor = 0
            blacklist_count = 0
            pattern = f"{self.KEY_PREFIX_BLACKLIST}*"
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                blacklist_count += len(keys)
                if cursor == 0:
                    break
            
            # Count blacklisted families
            family_count = len(
                await self.redis.smembers(self.KEY_PREFIX_REVOKED_FAMILIES)
            )
            
            return {
                "blacklisted_tokens": blacklist_count,
                "blacklisted_families": family_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("get_blacklist_stats_error", error=str(e))
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Cleanup and Maintenance
    
    async def cleanup_expired(self) -> int:
        """
        Manual cleanup of expired entries (Redis handles this automatically)
        This is mainly for monitoring and statistics
        
        Returns:
            Number of keys checked
        """
        # Redis automatically removes expired keys, but we can scan for reporting
        try:
            count = 0
            cursor = 0
            pattern = f"{self.KEY_PREFIX_BLACKLIST}*"
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                count += len(keys)
                if cursor == 0:
                    break
            
            logger.info("blacklist_cleanup_checked", keys_checked=count)
            return count
        except Exception as e:
            logger.error("cleanup_error", error=str(e))
            return 0


# Singleton instance
_token_blacklist: Optional[RedisTokenBlacklist] = None


def get_token_blacklist(
    redis_client: Optional[RedisClient] = None
) -> RedisTokenBlacklist:
    """
    Get token blacklist singleton
    
    Args:
        redis_client: Optional RedisClient instance
    
    Returns:
        RedisTokenBlacklist instance
    """
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = RedisTokenBlacklist(redis_client=redis_client)
    return _token_blacklist
