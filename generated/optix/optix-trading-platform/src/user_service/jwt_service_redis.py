"""
Redis-Integrated JWT Service
JWT service with Redis-backed token blacklist and storage
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import jwt
import uuid
import structlog
from .jwt_service import (
    JWTService,
    TokenType,
    TokenStatus,
    TokenRecord,
    RefreshTokenFamily
)
from .redis_token_blacklist import RedisTokenBlacklist, get_token_blacklist
from .redis_client import RedisClient

logger = structlog.get_logger(__name__)


class RedisJWTService(JWTService):
    """
    JWT service with Redis integration for token blacklist and persistence
    Extends base JWTService with Redis-backed storage
    """
    
    def __init__(
        self,
        secret_key: str,
        redis_client: Optional[RedisClient] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
        mfa_challenge_expire_minutes: int = 5,
        password_reset_expire_hours: int = 1,
        use_redis_blacklist: bool = True
    ):
        """
        Initialize Redis-integrated JWT service
        
        Args:
            secret_key: JWT secret key
            redis_client: Optional RedisClient instance
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token expiration
            refresh_token_expire_days: Refresh token expiration
            mfa_challenge_expire_minutes: MFA challenge token expiration
            password_reset_expire_hours: Password reset token expiration
            use_redis_blacklist: Use Redis for token blacklist
        """
        super().__init__(
            secret_key=secret_key,
            algorithm=algorithm,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
            mfa_challenge_expire_minutes=mfa_challenge_expire_minutes,
            password_reset_expire_hours=password_reset_expire_hours
        )
        
        self.use_redis_blacklist = use_redis_blacklist
        if use_redis_blacklist:
            self.blacklist = get_token_blacklist(redis_client)
        else:
            self.blacklist = None
    
    async def verify_token_async(
        self,
        token: str,
        expected_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Async version of verify_token with Redis blacklist check
        
        Args:
            token: JWT token string
            expected_type: Expected token type
        
        Returns:
            Decoded token payload
        
        Raises:
            ValueError: If token is invalid, expired, or blacklisted
        """
        # First do standard JWT verification
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        
        # Verify token type
        token_type = payload.get("type")
        if expected_type and token_type != expected_type.value:
            raise ValueError(
                f"Invalid token type. Expected {expected_type.value}, got {token_type}"
            )
        
        # Check Redis blacklist
        jti = payload.get("jti")
        if jti and self.use_redis_blacklist and self.blacklist:
            is_blacklisted = await self.blacklist.is_blacklisted(jti)
            if is_blacklisted:
                logger.warning("blacklisted_token_used", jti=jti)
                raise ValueError("Token has been revoked")
            
            # Check family blacklist for refresh tokens
            if token_type == TokenType.REFRESH.value:
                family_id = payload.get("family_id")
                if family_id:
                    is_family_blacklisted = await self.blacklist.is_family_blacklisted(
                        family_id
                    )
                    if is_family_blacklisted:
                        logger.warning(
                            "blacklisted_family_token_used",
                            family_id=family_id,
                            jti=jti
                        )
                        raise ValueError("Token family has been revoked")
        
        return payload
    
    async def revoke_token_async(
        self,
        jti: str,
        ttl_seconds: int,
        user_id: Optional[uuid.UUID] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Async token revocation with Redis blacklist
        
        Args:
            jti: JWT ID
            ttl_seconds: Time until token expires
            user_id: Optional user ID
            reason: Optional revocation reason
        
        Returns:
            True if revoked
        """
        if self.use_redis_blacklist and self.blacklist:
            return await self.blacklist.blacklist_token(
                jti=jti,
                ttl_seconds=ttl_seconds,
                user_id=user_id,
                reason=reason
            )
        else:
            # Fall back to in-memory
            return self.revoke_token(jti)
    
    async def revoke_user_tokens_async(
        self,
        user_id: uuid.UUID,
        active_tokens: List[TokenRecord],
        reason: Optional[str] = None
    ) -> int:
        """
        Revoke all tokens for a user using Redis
        
        Args:
            user_id: User ID
            active_tokens: List of active token records
            reason: Revocation reason
        
        Returns:
            Number of tokens revoked
        """
        if self.use_redis_blacklist and self.blacklist:
            token_entries = []
            for token in active_tokens:
                delta = token.expires_at - datetime.utcnow()
                ttl_seconds = max(int(delta.total_seconds()), 1)
                
                token_entries.append({
                    "jti": token.jti,
                    "ttl_seconds": ttl_seconds,
                    "user_id": user_id,
                    "reason": reason or "user_logout"
                })
            
            return await self.blacklist.blacklist_tokens_batch(token_entries)
        else:
            # Fall back to in-memory
            return self.revoke_user_tokens(user_id)
    
    async def revoke_token_family_async(
        self,
        family_id: str,
        ttl_seconds: int = 2592000,
        reason: Optional[str] = None
    ) -> bool:
        """
        Revoke entire token family using Redis
        
        Args:
            family_id: Token family ID
            ttl_seconds: TTL for blacklist entry
            reason: Revocation reason
        
        Returns:
            True if successful
        """
        if self.use_redis_blacklist and self.blacklist:
            return await self.blacklist.blacklist_token_family(
                family_id=family_id,
                ttl_seconds=ttl_seconds,
                reason=reason
            )
        else:
            # Fall back to in-memory
            return self._revoke_token_family(family_id)
    
    async def rotate_refresh_token_async(
        self,
        old_token: str
    ) -> Tuple[str, TokenRecord, RefreshTokenFamily]:
        """
        Async refresh token rotation with Redis blacklist integration
        
        Args:
            old_token: Old refresh token
        
        Returns:
            Tuple of (new_token, new_record, family)
        
        Raises:
            ValueError: If token is invalid or reused
        """
        # Verify old token (checks Redis blacklist)
        try:
            payload = await self.verify_token_async(
                old_token,
                expected_type=TokenType.REFRESH
            )
        except ValueError as e:
            raise e
        
        old_jti = payload.get("jti")
        family_id = payload.get("family_id")
        user_id = uuid.UUID(payload["sub"])
        
        # Check if token was already used (in Redis or memory)
        if self.use_redis_blacklist and self.blacklist:
            # Check Redis first
            is_blacklisted = await self.blacklist.is_blacklisted(old_jti)
            if is_blacklisted:
                # Token reuse detected! Revoke entire family
                await self.revoke_token_family_async(
                    family_id=family_id,
                    reason="token_reuse_detected"
                )
                raise ValueError(
                    "Token reuse detected - all tokens in family revoked"
                )
        
        # Check in-memory storage
        if old_jti in self._token_records:
            old_record = self._token_records[old_jti]
            if old_record.status == TokenStatus.REPLACED:
                # Token reuse in memory
                if self.use_redis_blacklist and self.blacklist:
                    await self.revoke_token_family_async(
                        family_id=family_id,
                        reason="token_reuse_detected"
                    )
                raise ValueError(
                    "Token reuse detected - all tokens in family revoked"
                )
        
        # Create new refresh token (uses parent class method)
        new_token, new_record, family = self.create_refresh_token(
            user_id=user_id,
            family_id=family_id
        )
        
        # Blacklist old token in Redis
        if self.use_redis_blacklist and self.blacklist:
            # Calculate TTL from expiration
            delta = datetime.utcnow() + self.refresh_token_expire - datetime.utcnow()
            ttl_seconds = int(delta.total_seconds())
            
            await self.blacklist.blacklist_token(
                jti=old_jti,
                ttl_seconds=ttl_seconds,
                user_id=user_id,
                reason="token_rotated"
            )
        
        # Mark old token as replaced in memory
        if old_jti in self._token_records:
            self._token_records[old_jti].status = TokenStatus.REPLACED
            self._token_records[old_jti].replaced_by = new_record.jti
        
        logger.info(
            "refresh_token_rotated",
            old_jti=old_jti,
            new_jti=new_record.jti,
            family_id=family_id
        )
        
        return new_token, new_record, family
    
    async def cleanup_expired_tokens_async(self) -> dict:
        """
        Cleanup expired tokens in both Redis and memory
        
        Returns:
            Cleanup statistics
        """
        # Clean up in-memory tokens
        memory_cleaned = self.cleanup_expired_tokens()
        
        # Get Redis statistics
        redis_stats = {}
        if self.use_redis_blacklist and self.blacklist:
            redis_stats = await self.blacklist.get_stats()
        
        return {
            "memory_expired_tokens": memory_cleaned,
            "redis_stats": redis_stats,
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instance
_redis_jwt_service: Optional[RedisJWTService] = None


def get_redis_jwt_service(
    secret_key: Optional[str] = None,
    redis_client: Optional[RedisClient] = None,
    **kwargs
) -> RedisJWTService:
    """
    Get Redis JWT service singleton
    
    Args:
        secret_key: JWT secret key (required for first init)
        redis_client: Optional RedisClient instance
        **kwargs: Additional service arguments
    
    Returns:
        RedisJWTService instance
    """
    global _redis_jwt_service
    if _redis_jwt_service is None:
        if secret_key is None:
            raise ValueError("secret_key is required for first initialization")
        _redis_jwt_service = RedisJWTService(
            secret_key=secret_key,
            redis_client=redis_client,
            **kwargs
        )
    return _redis_jwt_service
