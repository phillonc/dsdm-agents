"""
Redis-based Rate Limiting with Sliding Window Algorithm
Provides flexible rate limiting for API endpoints with admin bypass support
"""
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import time
import structlog
from redis.asyncio import Redis
from fastapi import Request, HTTPException, status

from .redis_client import get_redis_client
from config.settings import settings

logger = structlog.get_logger()


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    identifier_prefix: str
    
    @property
    def window_ms(self) -> int:
        """Window size in milliseconds"""
        return self.window_seconds * 1000


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded"""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        if headers is None:
            headers = {}
        
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers
        )


class SlidingWindowRateLimiter:
    """
    Redis-based sliding window rate limiter
    
    Uses sorted sets to track requests in a time window.
    More accurate than fixed window and more memory efficient than token bucket.
    
    Algorithm:
    1. Remove entries older than the window
    2. Count remaining entries
    3. If under limit, add new entry
    4. Return result with remaining quota
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self._configs: Dict[str, RateLimitConfig] = {}
    
    async def initialize(self) -> None:
        """Initialize rate limiter with Redis connection"""
        if self.redis is None:
            self.redis = await get_redis_client()
        logger.info("Rate limiter initialized")
    
    def register_limit(
        self,
        name: str,
        max_requests: int,
        window_seconds: int,
        identifier_prefix: Optional[str] = None
    ) -> None:
        """
        Register a rate limit configuration
        
        Args:
            name: Unique name for this rate limit
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            identifier_prefix: Optional prefix for Redis keys
        """
        if identifier_prefix is None:
            identifier_prefix = f"ratelimit:{name}"
        
        self._configs[name] = RateLimitConfig(
            max_requests=max_requests,
            window_seconds=window_seconds,
            identifier_prefix=identifier_prefix
        )
        
        logger.info(
            "Rate limit registered",
            name=name,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_name: str,
        bypass: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request should be rate limited
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            limit_name: Name of rate limit config to use
            bypass: If True, skip rate limiting (for admins)
        
        Returns:
            Tuple of (allowed, info_dict)
            info_dict contains: remaining, reset_at, limit, used
        
        Raises:
            ValueError: If limit_name not registered
        """
        if limit_name not in self._configs:
            raise ValueError(f"Rate limit '{limit_name}' not registered")
        
        config = self._configs[limit_name]
        
        # Admin bypass
        if bypass:
            return True, {
                "allowed": True,
                "bypass": True,
                "limit": config.max_requests,
                "remaining": config.max_requests,
                "reset_at": None,
                "used": 0
            }
        
        # Generate Redis key
        key = f"{config.identifier_prefix}:{identifier}"
        
        # Current timestamp in milliseconds
        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - config.window_ms
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # 1. Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start_ms)
            
            # 2. Count current entries in window
            pipe.zcard(key)
            
            # 3. Get oldest entry for reset time calculation
            pipe.zrange(key, 0, 0, withscores=True)
            
            results = await pipe.execute()
            current_count = results[1]
            oldest_entries = results[2]
            
            # Calculate reset time
            if oldest_entries:
                oldest_timestamp = int(oldest_entries[0][1])
                reset_at = oldest_timestamp + config.window_ms
            else:
                reset_at = now_ms + config.window_ms
            
            # Check if under limit
            if current_count < config.max_requests:
                # Add current request
                await self.redis.zadd(
                    key,
                    {str(now_ms): now_ms}
                )
                
                # Set expiration (cleanup)
                await self.redis.expire(key, config.window_seconds + 10)
                
                remaining = config.max_requests - (current_count + 1)
                
                return True, {
                    "allowed": True,
                    "limit": config.max_requests,
                    "remaining": remaining,
                    "reset_at": reset_at,
                    "used": current_count + 1
                }
            else:
                # Rate limit exceeded
                retry_after_ms = reset_at - now_ms
                retry_after_sec = max(1, int(retry_after_ms / 1000))
                
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    limit_name=limit_name,
                    count=current_count,
                    limit=config.max_requests
                )
                
                return False, {
                    "allowed": False,
                    "limit": config.max_requests,
                    "remaining": 0,
                    "reset_at": reset_at,
                    "used": current_count,
                    "retry_after": retry_after_sec
                }
                
        except Exception as e:
            logger.error(
                "Rate limit check failed",
                error=str(e),
                identifier=identifier,
                limit_name=limit_name
            )
            # Fail open - allow request if Redis fails
            return True, {
                "allowed": True,
                "error": str(e),
                "limit": config.max_requests,
                "remaining": config.max_requests
            }
    
    async def reset_limit(self, identifier: str, limit_name: str) -> bool:
        """
        Reset rate limit for an identifier
        
        Useful for admin operations or testing
        """
        if limit_name not in self._configs:
            return False
        
        config = self._configs[limit_name]
        key = f"{config.identifier_prefix}:{identifier}"
        
        try:
            await self.redis.delete(key)
            logger.info("Rate limit reset", identifier=identifier, limit_name=limit_name)
            return True
        except Exception as e:
            logger.error("Rate limit reset failed", error=str(e))
            return False
    
    async def get_usage(
        self,
        identifier: str,
        limit_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current usage for an identifier
        
        Returns dict with usage stats or None if error
        """
        if limit_name not in self._configs:
            return None
        
        config = self._configs[limit_name]
        key = f"{config.identifier_prefix}:{identifier}"
        
        try:
            now_ms = int(time.time() * 1000)
            window_start_ms = now_ms - config.window_ms
            
            # Clean old entries and count
            await self.redis.zremrangebyscore(key, 0, window_start_ms)
            count = await self.redis.zcard(key)
            
            # Get oldest entry
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            
            if oldest:
                reset_at = int(oldest[0][1]) + config.window_ms
            else:
                reset_at = now_ms + config.window_ms
            
            return {
                "limit": config.max_requests,
                "used": count,
                "remaining": max(0, config.max_requests - count),
                "reset_at": reset_at,
                "window_seconds": config.window_seconds
            }
            
        except Exception as e:
            logger.error("Get usage failed", error=str(e))
            return None


# Global rate limiter instance
_rate_limiter: Optional[SlidingWindowRateLimiter] = None


async def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter()
        await _rate_limiter.initialize()
        
        # Register default rate limits
        _rate_limiter.register_limit(
            name="auth_login",
            max_requests=5,
            window_seconds=60  # 5 requests per minute
        )
        
        _rate_limiter.register_limit(
            name="auth_register",
            max_requests=3,
            window_seconds=60  # 3 requests per minute
        )
        
        _rate_limiter.register_limit(
            name="auth_refresh",
            max_requests=10,
            window_seconds=60  # 10 requests per minute
        )
        
        _rate_limiter.register_limit(
            name="auth_mfa",
            max_requests=5,
            window_seconds=60  # 5 requests per minute
        )
        
        _rate_limiter.register_limit(
            name="api_default",
            max_requests=100,
            window_seconds=60  # 100 requests per minute
        )
        
        logger.info("Default rate limits configured")
    
    return _rate_limiter


def get_client_identifier(request: Request) -> str:
    """
    Extract client identifier from request
    
    Uses user_id if authenticated, otherwise IP address
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP from X-Forwarded-For
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    return f"ip:{ip}"


def is_admin_request(request: Request) -> bool:
    """Check if request is from admin user"""
    user_roles = getattr(request.state, "user_roles", [])
    return "admin" in user_roles


async def rate_limit_middleware(
    request: Request,
    limit_name: str = "api_default"
) -> None:
    """
    Rate limit middleware for FastAPI
    
    Usage:
        @router.post("/login")
        async def login(request: Request):
            await rate_limit_middleware(request, "auth_login")
            # ... rest of handler
    """
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    rate_limiter = await get_rate_limiter()
    identifier = get_client_identifier(request)
    bypass = is_admin_request(request)
    
    allowed, info = await rate_limiter.check_rate_limit(
        identifier=identifier,
        limit_name=limit_name,
        bypass=bypass
    )
    
    # Add rate limit headers to response
    request.state.rate_limit_info = info
    
    if not allowed:
        raise RateLimitExceeded(
            detail=f"Rate limit exceeded. Try again in {info.get('retry_after', 60)} seconds.",
            retry_after=info.get('retry_after'),
            headers={
                "X-RateLimit-Limit": str(info['limit']),
                "X-RateLimit-Remaining": str(info['remaining']),
                "X-RateLimit-Reset": str(info['reset_at'])
            }
        )


def add_rate_limit_headers(response, rate_limit_info: Optional[Dict[str, Any]]) -> None:
    """Add rate limit headers to response"""
    if not rate_limit_info:
        return
    
    if "limit" in rate_limit_info:
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
    
    if "remaining" in rate_limit_info:
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
    
    if "reset_at" in rate_limit_info:
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_at"])
    
    if rate_limit_info.get("bypass"):
        response.headers["X-RateLimit-Bypass"] = "true"
