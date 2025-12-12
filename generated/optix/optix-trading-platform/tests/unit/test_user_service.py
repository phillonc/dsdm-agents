"""
Unit Tests for User Service
Tests authentication, registration, and profile management
"""
import pytest
from datetime import datetime, timedelta
import uuid
from src.user_service.models import User, UserRegistration, UserLogin
from src.user_service.auth import AuthService
from src.user_service.repository import UserRepository


class TestAuthService:
    """Test authentication service"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService(secret_key="test-secret-key")
    
    @pytest.fixture
    def test_user(self):
        return User(
            id=uuid.uuid4(),
            email="test@optix.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User"
        )
    
    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "SecurePass123"
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert auth_service.verify_password(password, hashed)
    
    def test_verify_password_invalid(self, auth_service):
        """Test password verification with wrong password"""
        password = "SecurePass123"
        hashed = auth_service.hash_password(password)
        
        assert not auth_service.verify_password("WrongPass123", hashed)
    
    def test_create_access_token(self, auth_service, test_user):
        """Test JWT access token creation"""
        token = auth_service.create_access_token(test_user.id)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = auth_service.verify_token(token, token_type="access")
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self, auth_service, test_user):
        """Test JWT refresh token creation"""
        token = auth_service.create_refresh_token(test_user.id)
        
        assert token is not None
        
        # Verify token
        payload = auth_service.verify_token(token, token_type="refresh")
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "refresh"
    
    def test_token_pair(self, auth_service, test_user):
        """Test token pair creation"""
        token_pair = auth_service.create_token_pair(test_user)
        
        assert token_pair.access_token
        assert token_pair.refresh_token
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in == 900  # 15 minutes
    
    def test_generate_mfa_secret(self, auth_service):
        """Test MFA secret generation"""
        secret = auth_service.generate_mfa_secret()
        
        assert secret is not None
        assert len(secret) == 32  # Base32 encoded
    
    def test_verify_mfa_code(self, auth_service):
        """Test MFA code verification"""
        import pyotp
        
        secret = auth_service.generate_mfa_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        assert auth_service.verify_mfa_code(secret, code)


class TestUserRepository:
    """Test user repository"""
    
    @pytest.fixture
    def repo(self):
        return UserRepository()
    
    @pytest.fixture
    def test_user(self):
        return User(
            email="test@optix.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User"
        )
    
    def test_create_user(self, repo, test_user):
        """Test user creation"""
        created = repo.create_user(test_user)
        
        assert created.id == test_user.id
        assert created.email == test_user.email
    
    def test_get_user_by_id(self, repo, test_user):
        """Test get user by ID"""
        created = repo.create_user(test_user)
        retrieved = repo.get_user_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_user_by_email(self, repo, test_user):
        """Test get user by email"""
        created = repo.create_user(test_user)
        retrieved = repo.get_user_by_email(test_user.email)
        
        assert retrieved is not None
        assert retrieved.email == test_user.email
    
    def test_update_user(self, repo, test_user):
        """Test user update"""
        created = repo.create_user(test_user)
        
        updates = {"first_name": "Updated", "phone": "+1234567890"}
        updated = repo.update_user(created.id, updates)
        
        assert updated.first_name == "Updated"
        assert updated.phone == "+1234567890"
    
    def test_delete_user(self, repo, test_user):
        """Test user soft delete"""
        created = repo.create_user(test_user)
        
        result = repo.delete_user(created.id)
        assert result is True
        
        user = repo.get_user_by_id(created.id)
        assert user.is_active is False


class TestUserModels:
    """Test user models and validation"""
    
    def test_user_registration_valid(self):
        """Test valid user registration"""
        registration = UserRegistration(
            email="test@optix.com",
            password="SecurePass123",
            first_name="Test",
            last_name="User",
            accepted_tos=True
        )
        
        assert registration.email == "test@optix.com"
        assert registration.password == "SecurePass123"
        assert registration.accepted_tos is True
    
    def test_user_registration_weak_password(self):
        """Test password strength validation"""
        with pytest.raises(ValueError, match="Password must contain uppercase"):
            UserRegistration(
                email="test@optix.com",
                password="weak",
                accepted_tos=True
            )
    
    def test_user_registration_tos_not_accepted(self):
        """Test TOS acceptance validation"""
        with pytest.raises(ValueError, match="Terms of service must be accepted"):
            UserRegistration(
                email="test@optix.com",
                password="SecurePass123",
                accepted_tos=False
            )
    
    def test_user_login(self):
        """Test user login model"""
        login = UserLogin(
            email="test@optix.com",
            password="SecurePass123"
        )
        
        assert login.email == "test@optix.com"
        assert login.mfa_code is None
    
    def test_user_login_with_mfa(self):
        """Test user login with MFA"""
        login = UserLogin(
            email="test@optix.com",
            password="SecurePass123",
            mfa_code="123456"
        )
        
        assert login.mfa_code == "123456"
