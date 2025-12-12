"""
Unit Tests for Redis Integration
Tests for Redis client, token blacklist, and session storage
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

# Import components to test
from src.user_service.redis_client import RedisClient, get_redis_client
from src.user_service.redis_token_blacklist import (
    RedisTokenBlacklist,
    get_token_blacklist
)
from src.user_service.redis_session_store import (
    RedisSessionStore,
    get_session_store
)
from src.user_service.session_manager import Session, TrustedDevice, SecurityEvent
from src.user_service.jwt_service_redis import RedisJWTService
from src.user_service.session_manager_redis import RedisSessionManager


class TestRedisClient:
    """Test Redis client functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis connection"""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.get = AsyncMock(return_value="test_value")
        redis_mock.delete = AsyncMock(return_value=1)
        redis_mock.exists = AsyncMock(return_value=1)
        redis_mock.sadd = AsyncMock(return_value=1)
        redis_mock.smembers = AsyncMock(return_value={"member1", "member2"})
        redis_mock.sismember = AsyncMock(return_value=True)
        return redis_mock
    
    @pytest.fixture
    def redis_client(self, mock_redis):
        """Create Redis client with mocked connection"""
        client = RedisClient(redis_url="redis://localhost:6379/0")
        client._redis = mock_redis
        return client
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_client):
        """Test basic set and get operations"""
        key = "test_key"
        value = "test_value"
        
        # Test set
        result = await redis_client.set(key, value, ttl=60)
        assert result is True
        
        # Test get
        result = await redis_client.get(key)
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_set_with_serialization(self, redis_client, mock_redis):
        """Test set with JSON serialization"""
        key = "test_key"
        value = {"foo": "bar", "count": 42}
        
        mock_redis.get = AsyncMock(return_value=json.dumps(value))
        
        await redis_client.set(key, value, serialize=True)
        result = await redis_client.get(key, deserialize=True)
        
        assert result == value
    
    @pytest.mark.asyncio
    async def test_set_operations(self, redis_client):
        """Test Redis set operations"""
        key = "test_set"
        
        # Add members
        await redis_client.sadd(key, "member1", "member2")
        
        # Check membership
        is_member = await redis_client.sismember(key, "member1")
        assert is_member is True
        
        # Get all members
        members = await redis_client.smembers(key)
        assert "member1" in members
    
    @pytest.mark.asyncio
    async def test_delete(self, redis_client):
        """Test delete operation"""
        key = "test_key"
        
        deleted = await redis_client.delete(key)
        assert deleted == 1
    
    @pytest.mark.asyncio
    async def test_ping(self, redis_client):
        """Test Redis ping"""
        result = await redis_client.ping()
        assert result is True


class TestRedisTokenBlacklist:
    """Test Redis token blacklist functionality"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        client = Mock(spec=RedisClient)
        client.set = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.exists = AsyncMock(return_value=0)
        client.delete = AsyncMock(return_value=1)
        client.sadd = AsyncMock(return_value=1)
        client.smembers = AsyncMock(return_value=set())
        client.sismember = AsyncMock(return_value=False)
        client.srem = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.scan = AsyncMock(return_value=(0, []))
        return client
    
    @pytest.fixture
    def blacklist(self, mock_redis_client):
        """Create token blacklist with mocked Redis"""
        return RedisTokenBlacklist(redis_client=mock_redis_client)
    
    @pytest.mark.asyncio
    async def test_blacklist_token(self, blacklist, mock_redis_client):
        """Test blacklisting a token"""
        jti = "test_jti_123"
        user_id = uuid.uuid4()
        ttl = 3600
        
        result = await blacklist.blacklist_token(
            jti=jti,
            ttl_seconds=ttl,
            user_id=user_id,
            reason="test_revocation"
        )
        
        assert result is True
        mock_redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_blacklisted(self, blacklist, mock_redis_client):
        """Test checking if token is blacklisted"""
        jti = "test_jti_123"
        
        # Not blacklisted
        mock_redis_client.exists.return_value = 0
        result = await blacklist.is_blacklisted(jti)
        assert result is False
        
        # Blacklisted
        mock_redis_client.exists.return_value = 1
        result = await blacklist.is_blacklisted(jti)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_blacklist_token_family(self, blacklist, mock_redis_client):
        """Test blacklisting entire token family"""
        family_id = "family_123"
        
        result = await blacklist.blacklist_token_family(
            family_id=family_id,
            reason="token_reuse_detected"
        )
        
        assert result is True
        mock_redis_client.sadd.assert_called()
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_is_family_blacklisted(self, blacklist, mock_redis_client):
        """Test checking if family is blacklisted"""
        family_id = "family_123"
        
        # Not blacklisted
        mock_redis_client.sismember.return_value = False
        result = await blacklist.is_family_blacklisted(family_id)
        assert result is False
        
        # Blacklisted
        mock_redis_client.sismember.return_value = True
        result = await blacklist.is_family_blacklisted(family_id)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_blacklist_all_user_tokens(self, blacklist, mock_redis_client):
        """Test blacklisting all user tokens"""
        user_id = uuid.uuid4()
        token_jtis = ["jti1", "jti2", "jti3"]
        
        result = await blacklist.blacklist_all_user_tokens(
            user_id=user_id,
            token_jtis=token_jtis,
            reason="user_logout"
        )
        
        assert result == 3
        assert mock_redis_client.set.call_count == 3


class TestRedisSessionStore:
    """Test Redis session storage functionality"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        client = Mock(spec=RedisClient)
        client.set = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.delete = AsyncMock(return_value=1)
        client.sadd = AsyncMock(return_value=1)
        client.smembers = AsyncMock(return_value=set())
        client.srem = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.zadd = AsyncMock(return_value=1)
        client.zrange = AsyncMock(return_value=[])
        client.scan = AsyncMock(return_value=(0, []))
        return client
    
    @pytest.fixture
    def session_store(self, mock_redis_client):
        """Create session store with mocked Redis"""
        return RedisSessionStore(redis_client=mock_redis_client)
    
    @pytest.fixture
    def sample_session(self):
        """Create sample session"""
        user_id = uuid.uuid4()
        return Session(
            session_id=uuid.uuid4(),
            user_id=user_id,
            device_id="device123",
            device_fingerprint="fingerprint123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_store, sample_session, mock_redis_client):
        """Test creating session in Redis"""
        result = await session_store.create_session(sample_session)
        
        assert result is True
        mock_redis_client.set.assert_called_once()
        mock_redis_client.sadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_store, sample_session, mock_redis_client):
        """Test retrieving session from Redis"""
        # Mock Redis to return session data
        session_data = sample_session.model_dump(mode='json')
        mock_redis_client.get = AsyncMock(return_value=session_data)
        
        result = await session_store.get_session(sample_session.session_id)
        
        assert result is not None
        assert result.session_id == sample_session.session_id
    
    @pytest.mark.asyncio
    async def test_update_session(self, session_store, sample_session):
        """Test updating session in Redis"""
        sample_session.last_activity_at = datetime.utcnow()
        
        result = await session_store.update_session(sample_session)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_store, sample_session, mock_redis_client):
        """Test deleting session from Redis"""
        # Mock get_session to return the session
        session_data = sample_session.model_dump(mode='json')
        mock_redis_client.get = AsyncMock(return_value=session_data)
        
        result = await session_store.delete_session(sample_session.session_id)
        
        assert result is True
        mock_redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_store, sample_session, mock_redis_client):
        """Test getting all user sessions"""
        # Mock smembers to return session IDs
        mock_redis_client.smembers = AsyncMock(
            return_value={str(sample_session.session_id)}
        )
        
        # Mock get to return session data
        session_data = sample_session.model_dump(mode='json')
        mock_redis_client.get = AsyncMock(return_value=session_data)
        
        sessions = await session_store.get_user_sessions(sample_session.user_id)
        
        assert len(sessions) == 1
        assert sessions[0].session_id == sample_session.session_id
    
    @pytest.mark.asyncio
    async def test_save_trusted_device(self, session_store, mock_redis_client):
        """Test saving trusted device"""
        device = TrustedDevice(
            device_id="device123",
            user_id=uuid.uuid4(),
            device_fingerprint="fingerprint123",
            device_name="Test Device"
        )
        
        result = await session_store.save_trusted_device(device)
        
        assert result is True
        mock_redis_client.set.assert_called_once()
        mock_redis_client.sadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, session_store, mock_redis_client):
        """Test logging security event"""
        event = SecurityEvent(
            user_id=uuid.uuid4(),
            event_type="login_success",
            severity="low",
            description="User logged in"
        )
        
        result = await session_store.log_security_event(event)
        
        assert result is True
        mock_redis_client.set.assert_called_once()
        mock_redis_client.zadd.assert_called_once()


class TestRedisJWTService:
    """Test Redis-integrated JWT service"""
    
    @pytest.fixture
    def mock_blacklist(self):
        """Mock token blacklist"""
        blacklist = Mock(spec=RedisTokenBlacklist)
        blacklist.is_blacklisted = AsyncMock(return_value=False)
        blacklist.is_family_blacklisted = AsyncMock(return_value=False)
        blacklist.blacklist_token = AsyncMock(return_value=True)
        blacklist.blacklist_token_family = AsyncMock(return_value=True)
        return blacklist
    
    @pytest.fixture
    def jwt_service(self, mock_blacklist):
        """Create JWT service with mocked blacklist"""
        service = RedisJWTService(
            secret_key="test_secret_key",
            use_redis_blacklist=True
        )
        service.blacklist = mock_blacklist
        return service
    
    def test_create_access_token(self, jwt_service):
        """Test creating access token"""
        user_id = uuid.uuid4()
        token, record = jwt_service.create_access_token(
            user_id=user_id,
            email="test@example.com",
            roles=["user"],
            permissions=["read"]
        )
        
        assert token is not None
        assert record.user_id == user_id
        assert record.token_type.value == "access"
    
    @pytest.mark.asyncio
    async def test_verify_token_not_blacklisted(self, jwt_service):
        """Test verifying non-blacklisted token"""
        user_id = uuid.uuid4()
        token, _ = jwt_service.create_access_token(
            user_id=user_id,
            email="test@example.com",
            roles=["user"],
            permissions=["read"]
        )
        
        # Should not raise exception
        payload = await jwt_service.verify_token_async(token)
        assert payload["sub"] == str(user_id)
    
    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, jwt_service, mock_blacklist):
        """Test verifying blacklisted token"""
        user_id = uuid.uuid4()
        token, _ = jwt_service.create_access_token(
            user_id=user_id,
            email="test@example.com",
            roles=["user"],
            permissions=["read"]
        )
        
        # Mock blacklist to return True
        mock_blacklist.is_blacklisted = AsyncMock(return_value=True)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Token has been revoked"):
            await jwt_service.verify_token_async(token)
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, jwt_service, mock_blacklist):
        """Test revoking token"""
        jti = "test_jti"
        ttl = 3600
        user_id = uuid.uuid4()
        
        result = await jwt_service.revoke_token_async(
            jti=jti,
            ttl_seconds=ttl,
            user_id=user_id
        )
        
        assert result is True
        mock_blacklist.blacklist_token.assert_called_once()


class TestRedisSessionManager:
    """Test Redis-integrated session manager"""
    
    @pytest.fixture
    def mock_store(self):
        """Mock session store"""
        store = Mock(spec=RedisSessionStore)
        store.create_session = AsyncMock(return_value=True)
        store.get_session = AsyncMock(return_value=None)
        store.update_session = AsyncMock(return_value=True)
        store.delete_session = AsyncMock(return_value=True)
        store.get_user_sessions = AsyncMock(return_value=[])
        store.get_user_trusted_devices = AsyncMock(return_value=[])
        store.save_trusted_device = AsyncMock(return_value=True)
        store.log_security_event = AsyncMock(return_value=True)
        return store
    
    @pytest.fixture
    def session_manager(self, mock_store):
        """Create session manager with mocked store"""
        manager = RedisSessionManager(use_redis_storage=True)
        manager.store = mock_store
        return manager
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_store):
        """Test creating session"""
        user_id = uuid.uuid4()
        
        session = await session_manager.create_session_async(
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            device_fingerprint="fingerprint123"
        )
        
        assert session is not None
        assert session.user_id == user_id
        mock_store.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_terminate_session(self, session_manager, mock_store):
        """Test terminating session"""
        session_id = uuid.uuid4()
        
        # Mock get_session to return a session
        mock_session = Mock()
        mock_session.status = "active"
        mock_session.terminated_at = None
        mock_store.get_session = AsyncMock(return_value=mock_session)
        
        result = await session_manager.terminate_session_async(session_id)
        
        assert result is True
        mock_store.delete_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trust_device(self, session_manager, mock_store):
        """Test trusting a device"""
        user_id = uuid.uuid4()
        
        # Mock get_trusted_device to return None (device not yet trusted)
        mock_store.get_trusted_device = AsyncMock(return_value=None)
        
        device = await session_manager.trust_device_async(
            user_id=user_id,
            device_fingerprint="fingerprint123",
            device_name="Test Device"
        )
        
        assert device is not None
        assert device.user_id == user_id
        mock_store.save_trusted_device.assert_called_once()


@pytest.mark.asyncio
async def test_integration_flow():
    """Test complete integration flow"""
    # This would be an integration test with real Redis
    # Skipped in unit tests
    pytest.skip("Integration test - requires Redis")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
