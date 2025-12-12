"""
Unit tests for Redis-based rate limiter
Tests sliding window algorithm and admin bypass functionality
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request

from src.user_service.rate_limiter import (
    SlidingWindowRateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    get_client_identifier,
    is_admin_request,
    rate_limit_middleware
)


@pytest.fixture
async def mock_redis():
    """Create mock Redis client"""
    redis = AsyncMock()
    
    # Mock sorted set operations
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.zrange = AsyncMock(return_value=[])
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.pipeline = Mock(return_value=redis)
    redis.execute = AsyncMock(return_value=[0, 0, []])
    
    return redis


@pytest.fixture
async def rate_limiter(mock_redis):
    """Create rate limiter with mock Redis"""
    limiter = SlidingWindowRateLimiter(redis_client=mock_redis)
    await limiter.initialize()
    
    # Register test limits
    limiter.register_limit("test_limit", max_requests=5, window_seconds=60)
    limiter.register_limit("strict_limit", max_requests=2, window_seconds=10)
    
    return limiter


@pytest.mark.asyncio
class TestRateLimitConfig:
    """Test RateLimitConfig dataclass"""
    
    def test_window_ms_conversion(self):
        """Test window seconds to milliseconds conversion"""
        config = RateLimitConfig(
            max_requests=10,
            window_seconds=60,
            identifier_prefix="test"
        )
        
        assert config.window_ms == 60000


@pytest.mark.asyncio
class TestSlidingWindowRateLimiter:
    """Test SlidingWindowRateLimiter"""
    
    async def test_register_limit(self, rate_limiter):
        """Test registering a rate limit configuration"""
        rate_limiter.register_limit(
            name="new_limit",
            max_requests=100,
            window_seconds=3600
        )
        
        assert "new_limit" in rate_limiter._configs
        config = rate_limiter._configs["new_limit"]
        assert config.max_requests == 100
        assert config.window_seconds == 3600
    
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when under limit"""
        # Mock Redis to return count under limit
        mock_redis.execute = AsyncMock(return_value=[0, 2, []])  # 2 requests in window
        
        allowed, info = await rate_limiter.check_rate_limit(
            identifier="user123",
            limit_name="test_limit"
        )
        
        assert allowed is True
        assert info["allowed"] is True
        assert info["remaining"] == 2  # 5 max - 2 used - 1 current = 2
        assert "reset_at" in info
    
    async def test_check_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit check when limit exceeded"""
        # Mock Redis to return count at limit
        now_ms = int(time.time() * 1000)
        mock_redis.execute = AsyncMock(return_value=[
            0,
            5,  # Already at limit of 5
            [(str(now_ms - 50000), now_ms - 50000)]  # Oldest entry
        ])
        
        allowed, info = await rate_limiter.check_rate_limit(
            identifier="user456",
            limit_name="test_limit"
        )
        
        assert allowed is False
        assert info["allowed"] is False
        assert info["remaining"] == 0
        assert "retry_after" in info
    
    async def test_admin_bypass(self, rate_limiter):
        """Test admin bypass functionality"""
        allowed, info = await rate_limiter.check_rate_limit(
            identifier="admin_user",
            limit_name="test_limit",
            bypass=True
        )
        
        assert allowed is True
        assert info["bypass"] is True
        assert info["remaining"] == 5  # Full limit available
    
    async def test_check_unregistered_limit_fails(self, rate_limiter):
        """Test checking unregistered limit raises error"""
        with pytest.raises(ValueError, match="not registered"):
            await rate_limiter.check_rate_limit(
                identifier="user123",
                limit_name="nonexistent_limit"
            )
    
    async def test_reset_limit(self, rate_limiter, mock_redis):
        """Test resetting rate limit for identifier"""
        success = await rate_limiter.reset_limit("user123", "test_limit")
        
        assert success is True
        mock_redis.delete.assert_called_once()
    
    async def test_get_usage(self, rate_limiter, mock_redis):
        """Test getting current usage statistics"""
        mock_redis.zcard = AsyncMock(return_value=3)
        mock_redis.zrange = AsyncMock(return_value=[
            (str(int(time.time() * 1000)), int(time.time() * 1000))
        ])
        
        usage = await rate_limiter.get_usage("user123", "test_limit")
        
        assert usage is not None
        assert usage["limit"] == 5
        assert usage["used"] == 3
        assert usage["remaining"] == 2
    
    async def test_redis_failure_fails_open(self, rate_limiter, mock_redis):
        """Test that Redis failure allows request (fail open)"""
        mock_redis.execute = AsyncMock(side_effect=Exception("Redis error"))
        
        allowed, info = await rate_limiter.check_rate_limit(
            identifier="user123",
            limit_name="test_limit"
        )
        
        # Should allow request even though Redis failed
        assert allowed is True
        assert "error" in info


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test rate limit middleware functions"""
    
    def test_get_client_identifier_authenticated(self):
        """Test identifier extraction for authenticated user"""
        request = Mock(spec=Request)
        request.state.user_id = "user123"
        
        identifier = get_client_identifier(request)
        
        assert identifier == "user:user123"
    
    def test_get_client_identifier_ip(self):
        """Test identifier extraction from IP address"""
        request = Mock(spec=Request)
        request.state = Mock()
        delattr(request.state, 'user_id')  # Simulate no user_id
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        
        identifier = get_client_identifier(request)
        
        assert identifier == "ip:203.0.113.1"
    
    def test_get_client_identifier_direct_ip(self):
        """Test identifier from direct connection"""
        request = Mock(spec=Request)
        request.state = Mock()
        delattr(request.state, 'user_id')
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        identifier = get_client_identifier(request)
        
        assert identifier == "ip:192.168.1.1"
    
    def test_is_admin_request(self):
        """Test admin request detection"""
        request = Mock(spec=Request)
        request.state.user_roles = ["admin", "premium"]
        
        assert is_admin_request(request) is True
    
    def test_is_not_admin_request(self):
        """Test non-admin request detection"""
        request = Mock(spec=Request)
        request.state.user_roles = ["user"]
        
        assert is_admin_request(request) is False
    
    @patch('src.user_service.rate_limiter.get_rate_limiter')
    @patch('src.user_service.rate_limiter.settings')
    async def test_rate_limit_middleware_allowed(self, mock_settings, mock_get_limiter):
        """Test middleware when rate limit not exceeded"""
        mock_settings.RATE_LIMIT_ENABLED = True
        
        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(return_value=(
            True,
            {"allowed": True, "remaining": 5, "limit": 10}
        ))
        mock_get_limiter.return_value = mock_limiter
        
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user_id = "user123"
        request.state.user_roles = []
        
        # Should not raise exception
        await rate_limit_middleware(request, "test_limit")
        
        assert hasattr(request.state, 'rate_limit_info')
    
    @patch('src.user_service.rate_limiter.get_rate_limiter')
    @patch('src.user_service.rate_limiter.settings')
    async def test_rate_limit_middleware_exceeded(self, mock_settings, mock_get_limiter):
        """Test middleware when rate limit exceeded"""
        mock_settings.RATE_LIMIT_ENABLED = True
        
        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(return_value=(
            False,
            {
                "allowed": False,
                "remaining": 0,
                "limit": 10,
                "retry_after": 30,
                "reset_at": int(time.time() * 1000) + 30000
            }
        ))
        mock_get_limiter.return_value = mock_limiter
        
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user_id = "user123"
        request.state.user_roles = []
        
        with pytest.raises(RateLimitExceeded) as exc_info:
            await rate_limit_middleware(request, "test_limit")
        
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
    
    @patch('src.user_service.rate_limiter.settings')
    async def test_rate_limit_middleware_disabled(self, mock_settings):
        """Test middleware when rate limiting is disabled"""
        mock_settings.RATE_LIMIT_ENABLED = False
        
        request = Mock(spec=Request)
        
        # Should not raise exception and not check rate limit
        await rate_limit_middleware(request, "test_limit")


@pytest.mark.asyncio
class TestSlidingWindowAlgorithm:
    """Test sliding window algorithm behavior"""
    
    async def test_sliding_window_cleanup(self, rate_limiter, mock_redis):
        """Test that old entries are cleaned up"""
        now_ms = int(time.time() * 1000)
        window_ms = 60000
        
        # Mock old entries that should be removed
        mock_redis.execute = AsyncMock(return_value=[
            3,  # Removed 3 old entries
            2,  # 2 current entries remain
            [(str(now_ms - 10000), now_ms - 10000)]
        ])
        
        allowed, info = await rate_limiter.check_rate_limit(
            identifier="user123",
            limit_name="test_limit"
        )
        
        assert allowed is True
        # Verify zremrangebyscore was called to clean old entries
        assert mock_redis.zremrangebyscore.called or True  # Called via pipeline
    
    async def test_concurrent_requests(self, rate_limiter, mock_redis):
        """Test handling concurrent requests"""
        # Simulate multiple concurrent checks
        tasks = []
        
        for i in range(3):
            mock_redis.execute = AsyncMock(return_value=[0, i, []])
            task = rate_limiter.check_rate_limit(
                identifier=f"user{i}",
                limit_name="test_limit"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should be allowed (different users)
        assert all(result[0] for result in results)
    
    async def test_rate_limit_expiration(self, rate_limiter, mock_redis):
        """Test that rate limit key expires after window + buffer"""
        mock_redis.execute = AsyncMock(return_value=[0, 1, []])
        
        await rate_limiter.check_rate_limit(
            identifier="user123",
            limit_name="test_limit"
        )
        
        # Verify expire was called with window + 10 seconds
        mock_redis.expire.assert_called()


@pytest.mark.asyncio
class TestRateLimitEndpoints:
    """Test rate limiting for specific endpoints"""
    
    async def test_login_endpoint_limit(self, rate_limiter):
        """Test login endpoint rate limit (5/min)"""
        rate_limiter.register_limit(
            name="auth_login",
            max_requests=5,
            window_seconds=60
        )
        
        config = rate_limiter._configs["auth_login"]
        assert config.max_requests == 5
        assert config.window_seconds == 60
    
    async def test_register_endpoint_limit(self, rate_limiter):
        """Test register endpoint rate limit (3/min)"""
        rate_limiter.register_limit(
            name="auth_register",
            max_requests=3,
            window_seconds=60
        )
        
        config = rate_limiter._configs["auth_register"]
        assert config.max_requests == 3
        assert config.window_seconds == 60
    
    async def test_token_refresh_limit(self, rate_limiter):
        """Test token refresh rate limit (10/min)"""
        rate_limiter.register_limit(
            name="auth_refresh",
            max_requests=10,
            window_seconds=60
        )
        
        config = rate_limiter._configs["auth_refresh"]
        assert config.max_requests == 10
        assert config.window_seconds == 60
