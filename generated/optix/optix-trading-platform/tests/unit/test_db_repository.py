"""
Unit tests for database repositories
Tests async SQLAlchemy 2.0 repository pattern implementations
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.user_service.database import Base
from src.user_service.db_models import (
    UserModel, SessionModel, SecurityEventModel,
    TrustedDeviceModel, RefreshTokenFamilyModel,
    UserStatus, UserRole, EventSeverity
)
from src.user_service.db_repository import (
    UserRepository, SessionRepository, SecurityEventRepository,
    TrustedDeviceRepository, RefreshTokenFamilyRepository
)


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
    
    # Create all tables
    async with engine.begin() as conn:
        # SQLite doesn't support schemas, so we need to adjust
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    """Create test database session"""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
class TestUserRepository:
    """Test UserRepository"""
    
    async def test_create_user(self, session: AsyncSession):
        """Test creating a new user"""
        repo = UserRepository(session)
        
        user = await repo.create(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            role=UserRole.USER
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.status == UserStatus.ACTIVE
        assert user.role == UserRole.USER
    
    async def test_create_duplicate_user_fails(self, session: AsyncSession):
        """Test that creating duplicate email fails"""
        repo = UserRepository(session)
        
        await repo.create(
            email="duplicate@example.com",
            password_hash="hash1"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await repo.create(
                email="duplicate@example.com",
                password_hash="hash2"
            )
    
    async def test_get_by_id(self, session: AsyncSession):
        """Test retrieving user by ID"""
        repo = UserRepository(session)
        
        created_user = await repo.create(
            email="getbyid@example.com",
            password_hash="hash"
        )
        
        retrieved_user = await repo.get_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
    
    async def test_get_by_email(self, session: AsyncSession):
        """Test retrieving user by email"""
        repo = UserRepository(session)
        
        await repo.create(
            email="getbyemail@example.com",
            password_hash="hash"
        )
        
        user = await repo.get_by_email("getbyemail@example.com")
        
        assert user is not None
        assert user.email == "getbyemail@example.com"
    
    async def test_get_by_email_case_insensitive(self, session: AsyncSession):
        """Test email lookup is case insensitive"""
        repo = UserRepository(session)
        
        await repo.create(
            email="CaseSensitive@Example.COM",
            password_hash="hash"
        )
        
        user = await repo.get_by_email("casesensitive@example.com")
        
        assert user is not None
    
    async def test_update_user(self, session: AsyncSession):
        """Test updating user fields"""
        repo = UserRepository(session)
        
        user = await repo.create(
            email="update@example.com",
            password_hash="hash"
        )
        
        updated_user = await repo.update(
            user.id,
            first_name="Updated",
            phone_number="+1234567890"
        )
        
        assert updated_user.first_name == "Updated"
        assert updated_user.phone_number == "+1234567890"
    
    async def test_update_last_login(self, session: AsyncSession):
        """Test updating last login timestamp"""
        repo = UserRepository(session)
        
        user = await repo.create(
            email="lastlogin@example.com",
            password_hash="hash"
        )
        
        assert user.last_login_at is None
        
        await repo.update_last_login(user.id)
        
        updated_user = await repo.get_by_id(user.id)
        assert updated_user.last_login_at is not None
    
    async def test_verify_email(self, session: AsyncSession):
        """Test email verification"""
        repo = UserRepository(session)
        
        user = await repo.create(
            email="verify@example.com",
            password_hash="hash"
        )
        
        assert user.email_verified is False
        
        success = await repo.verify_email(user.id)
        assert success is True
        
        verified_user = await repo.get_by_id(user.id)
        assert verified_user.email_verified is True
        assert verified_user.email_verified_at is not None
    
    async def test_soft_delete(self, session: AsyncSession):
        """Test soft deleting a user"""
        repo = UserRepository(session)
        
        user = await repo.create(
            email="delete@example.com",
            password_hash="hash"
        )
        
        success = await repo.soft_delete(user.id)
        assert success is True
        
        # User should not be retrievable after soft delete
        deleted_user = await repo.get_by_id(user.id)
        assert deleted_user is None


@pytest.mark.asyncio
class TestSessionRepository:
    """Test SessionRepository"""
    
    async def test_create_session(self, session: AsyncSession):
        """Test creating a session"""
        user_repo = UserRepository(session)
        session_repo = SessionRepository(session)
        
        user = await user_repo.create(
            email="session@example.com",
            password_hash="hash"
        )
        
        session_id = uuid.uuid4()
        session_record = await session_repo.create(
            session_id=session_id,
            user_id=user.id,
            device_id="device123",
            ip_address="192.168.1.1",
            mfa_verified=True
        )
        
        assert session_record.session_id == session_id
        assert session_record.user_id == user.id
        assert session_record.mfa_verified is True
    
    async def test_get_by_session_id(self, session: AsyncSession):
        """Test retrieving session by ID"""
        user_repo = UserRepository(session)
        session_repo = SessionRepository(session)
        
        user = await user_repo.create(
            email="getsession@example.com",
            password_hash="hash"
        )
        
        session_id = uuid.uuid4()
        await session_repo.create(
            session_id=session_id,
            user_id=user.id,
            device_id="device123"
        )
        
        retrieved = await session_repo.get_by_session_id(session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session_id
    
    async def test_update_activity(self, session: AsyncSession):
        """Test updating session activity"""
        user_repo = UserRepository(session)
        session_repo = SessionRepository(session)
        
        user = await user_repo.create(
            email="activity@example.com",
            password_hash="hash"
        )
        
        session_id = uuid.uuid4()
        await session_repo.create(
            session_id=session_id,
            user_id=user.id,
            device_id="device123"
        )
        
        # Wait a bit and update
        import asyncio
        await asyncio.sleep(0.1)
        
        success = await session_repo.update_activity(session_id)
        assert success is True
    
    async def test_terminate_session(self, session: AsyncSession):
        """Test terminating a session"""
        user_repo = UserRepository(session)
        session_repo = SessionRepository(session)
        
        user = await user_repo.create(
            email="terminate@example.com",
            password_hash="hash"
        )
        
        session_id = uuid.uuid4()
        await session_repo.create(
            session_id=session_id,
            user_id=user.id,
            device_id="device123"
        )
        
        success = await session_repo.terminate(session_id)
        assert success is True
        
        terminated = await session_repo.get_by_session_id(session_id)
        assert terminated.terminated_at is not None


@pytest.mark.asyncio
class TestSecurityEventRepository:
    """Test SecurityEventRepository"""
    
    async def test_create_event(self, session: AsyncSession):
        """Test creating a security event"""
        user_repo = UserRepository(session)
        event_repo = SecurityEventRepository(session)
        
        user = await user_repo.create(
            email="event@example.com",
            password_hash="hash"
        )
        
        event = await event_repo.create(
            user_id=user.id,
            event_type="login_failed",
            severity=EventSeverity.MEDIUM,
            description="Failed login attempt",
            ip_address="192.168.1.1",
            metadata={"attempts": 3}
        )
        
        assert event.id is not None
        assert event.event_type == "login_failed"
        assert event.severity == EventSeverity.MEDIUM
        assert event.metadata["attempts"] == 3
    
    async def test_get_user_events(self, session: AsyncSession):
        """Test retrieving user's security events"""
        user_repo = UserRepository(session)
        event_repo = SecurityEventRepository(session)
        
        user = await user_repo.create(
            email="userevents@example.com",
            password_hash="hash"
        )
        
        # Create multiple events
        for i in range(3):
            await event_repo.create(
                user_id=user.id,
                event_type=f"event_{i}",
                severity=EventSeverity.LOW,
                description=f"Test event {i}"
            )
        
        events = await event_repo.get_user_events(user.id)
        
        assert len(events) == 3
    
    async def test_mark_resolved(self, session: AsyncSession):
        """Test marking event as resolved"""
        user_repo = UserRepository(session)
        event_repo = SecurityEventRepository(session)
        
        user = await user_repo.create(
            email="resolved@example.com",
            password_hash="hash"
        )
        
        event = await event_repo.create(
            user_id=user.id,
            event_type="suspicious_activity",
            severity=EventSeverity.HIGH,
            description="Suspicious login"
        )
        
        assert event.resolved is False
        
        success = await event_repo.mark_resolved(event.id)
        assert success is True


@pytest.mark.asyncio
class TestTrustedDeviceRepository:
    """Test TrustedDeviceRepository"""
    
    async def test_create_trusted_device(self, session: AsyncSession):
        """Test creating a trusted device"""
        user_repo = UserRepository(session)
        device_repo = TrustedDeviceRepository(session)
        
        user = await user_repo.create(
            email="device@example.com",
            password_hash="hash"
        )
        
        device = await device_repo.create(
            user_id=user.id,
            device_id="device123",
            device_fingerprint="fingerprint123",
            trust_token="token123",
            device_name="iPhone 15"
        )
        
        assert device.id is not None
        assert device.device_id == "device123"
        assert device.trust_token == "token123"
        assert device.revoked is False
    
    async def test_get_by_token(self, session: AsyncSession):
        """Test retrieving device by trust token"""
        user_repo = UserRepository(session)
        device_repo = TrustedDeviceRepository(session)
        
        user = await user_repo.create(
            email="gettoken@example.com",
            password_hash="hash"
        )
        
        await device_repo.create(
            user_id=user.id,
            device_id="device123",
            device_fingerprint="fingerprint123",
            trust_token="unique_token_123"
        )
        
        device = await device_repo.get_by_token("unique_token_123")
        
        assert device is not None
        assert device.trust_token == "unique_token_123"
    
    async def test_revoke_device(self, session: AsyncSession):
        """Test revoking a trusted device"""
        user_repo = UserRepository(session)
        device_repo = TrustedDeviceRepository(session)
        
        user = await user_repo.create(
            email="revoke@example.com",
            password_hash="hash"
        )
        
        await device_repo.create(
            user_id=user.id,
            device_id="device123",
            device_fingerprint="fingerprint123",
            trust_token="token123"
        )
        
        success = await device_repo.revoke("device123", user.id)
        assert success is True
        
        # Should not be retrievable after revocation
        device = await device_repo.get_by_token("token123")
        assert device is None


@pytest.mark.asyncio
class TestRefreshTokenFamilyRepository:
    """Test RefreshTokenFamilyRepository"""
    
    async def test_create_token_family(self, session: AsyncSession):
        """Test creating a token family"""
        user_repo = UserRepository(session)
        family_repo = RefreshTokenFamilyRepository(session)
        
        user = await user_repo.create(
            email="family@example.com",
            password_hash="hash"
        )
        
        family = await family_repo.create(
            family_id="family123",
            user_id=user.id,
            device_fingerprint="fingerprint123"
        )
        
        assert family.id is not None
        assert family.family_id == "family123"
        assert family.revoked is False
    
    async def test_revoke_family(self, session: AsyncSession):
        """Test revoking a token family"""
        user_repo = UserRepository(session)
        family_repo = RefreshTokenFamilyRepository(session)
        
        user = await user_repo.create(
            email="revokefamily@example.com",
            password_hash="hash"
        )
        
        await family_repo.create(
            family_id="family123",
            user_id=user.id
        )
        
        success = await family_repo.revoke("family123", "security_breach")
        assert success is True
        
        family = await family_repo.get_by_family_id("family123")
        assert family.revoked is True
        assert family.revoke_reason == "security_breach"
