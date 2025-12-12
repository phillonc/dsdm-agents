"""
Unit Tests for Enhanced Authentication
Integration tests for JWT, MFA, and RBAC
"""
import pytest
from datetime import datetime, timedelta
import uuid
from src.user_service.auth import AuthService
from src.user_service.models import User, MFAMethod
from src.user_service.rbac import Permission, Role, get_rbac_service
from src.user_service.mfa_manager import get_mfa_manager, MFAType


@pytest.fixture
def auth_service():
    """Create auth service instance for testing"""
    return AuthService(
        secret_key="test-secret-key-for-testing-only",
        access_token_expire_minutes=15,
        refresh_token_expire_days=30
    )


@pytest.fixture
def test_user():
    """Create test user"""
    return User(
        email="test@example.com",
        password_hash="hashed_password",
        first_name="Test",
        last_name="User",
        roles=["free_user"]
    )


@pytest.fixture
def premium_user():
    """Create premium test user"""
    return User(
        email="premium@example.com",
        password_hash="hashed_password",
        first_name="Premium",
        last_name="User",
        roles=["premium_user"],
        is_premium=True
    )


class TestPasswordManagement:
    """Test password hashing and verification"""
    
    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_success(self, auth_service):
        """Test successful password verification"""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        is_valid = auth_service.verify_password(password, hashed)
        assert is_valid is True
    
    def test_verify_password_failure(self, auth_service):
        """Test failed password verification"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = auth_service.hash_password(password)
        
        is_valid = auth_service.verify_password(wrong_password, hashed)
        assert is_valid is False
    
    def test_password_hashes_are_unique(self, auth_service):
        """Test that same password produces different hashes (salted)"""
        password = "SecurePassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        # Different hashes due to salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestMFAManagement:
    """Test MFA functionality"""
    
    def test_generate_mfa_secret(self, auth_service):
        """Test MFA secret generation"""
        secret1 = auth_service.generate_mfa_secret()
        secret2 = auth_service.generate_mfa_secret()
        
        assert secret1 is not None
        assert secret2 is not None
        assert secret1 != secret2
        assert len(secret1) == 32  # Base32 encoded
    
    def test_get_totp_uri(self, auth_service):
        """Test TOTP URI generation"""
        secret = auth_service.generate_mfa_secret()
        email = "test@example.com"
        
        uri = auth_service.get_totp_uri(secret, email)
        
        assert uri is not None
        assert "otpauth://totp/" in uri
        assert email in uri
        assert "OPTIX" in uri
    
    def test_verify_mfa_code(self, auth_service):
        """Test MFA code verification"""
        import pyotp
        
        secret = auth_service.generate_mfa_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Valid code should verify
        is_valid = auth_service.verify_mfa_code(secret, valid_code)
        assert is_valid is True
        
        # Invalid code should fail
        is_valid = auth_service.verify_mfa_code(secret, "000000")
        assert is_valid is False


class TestJWTTokenManagement:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self, auth_service, test_user):
        """Test access token creation"""
        token = auth_service.create_access_token(test_user)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self, auth_service, test_user):
        """Test refresh token creation"""
        token = auth_service.create_refresh_token(test_user.id)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_create_token_pair(self, auth_service, test_user):
        """Test token pair creation"""
        token_pair = auth_service.create_token_pair(test_user)
        
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in > 0
    
    def test_verify_token(self, auth_service, test_user):
        """Test token verification"""
        token = auth_service.create_access_token(test_user)
        payload = auth_service.verify_token(token, token_type="access")
        
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "access"
    
    def test_decode_token(self, auth_service, test_user):
        """Test token decoding into TokenPayload"""
        token = auth_service.create_access_token(test_user)
        token_payload = auth_service.decode_token(token)
        
        assert token_payload.sub == str(test_user.id)
        assert token_payload.email == test_user.email
        assert token_payload.type == "access"
        assert token_payload.roles == test_user.roles
    
    def test_refresh_access_token(self, auth_service, test_user):
        """Test refreshing access token"""
        refresh_token = auth_service.create_refresh_token(test_user.id)
        new_access_token = auth_service.refresh_access_token(refresh_token, test_user)
        
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        
        # New token should be valid
        payload = auth_service.verify_token(new_access_token, token_type="access")
        assert payload["sub"] == str(test_user.id)


class TestAccountSecurity:
    """Test account security features"""
    
    def test_handle_failed_login(self, auth_service, test_user):
        """Test failed login handling"""
        initial_attempts = test_user.failed_login_attempts
        
        auth_service.handle_failed_login(test_user)
        
        assert test_user.failed_login_attempts == initial_attempts + 1
    
    def test_account_lockout(self, auth_service, test_user):
        """Test account lockout after max failed attempts"""
        # Simulate multiple failed attempts
        for i in range(5):
            auth_service.handle_failed_login(test_user)
        
        assert test_user.is_locked is True
        assert test_user.locked_until is not None
        assert auth_service.check_account_lockout(test_user) is True
    
    def test_successful_login_resets_attempts(self, auth_service, test_user):
        """Test that successful login resets failed attempts"""
        # Add some failed attempts
        test_user.failed_login_attempts = 3
        
        auth_service.handle_successful_login(test_user)
        
        assert test_user.failed_login_attempts == 0
        assert test_user.is_locked is False
        assert test_user.last_login_at is not None
    
    def test_generate_password_reset_token(self, auth_service, test_user):
        """Test password reset token generation"""
        token = auth_service.generate_password_reset_token(test_user.id)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_password_reset_token(self, auth_service, test_user):
        """Test password reset token verification"""
        token = auth_service.generate_password_reset_token(test_user.id)
        user_id = auth_service.verify_password_reset_token(token)
        
        assert user_id == test_user.id


class TestRBACIntegration:
    """Test RBAC integration with auth service"""
    
    def test_check_permission(self, auth_service, test_user):
        """Test permission checking"""
        rbac = auth_service.rbac_service
        rbac.assign_role(test_user.id, Role.FREE_USER)
        
        # Free user should have watchlist read permission
        has_permission = auth_service.check_permission(
            test_user,
            Permission.WATCHLIST_READ
        )
        assert has_permission is True
        
        # Free user should not have admin permission
        has_permission = auth_service.check_permission(
            test_user,
            Permission.ADMIN_USERS
        )
        assert has_permission is False
    
    def test_check_multiple_permissions(self, auth_service, premium_user):
        """Test checking multiple permissions"""
        rbac = auth_service.rbac_service
        rbac.assign_role(premium_user.id, Role.PREMIUM_USER)
        
        permissions = [
            Permission.WATCHLIST_READ,
            Permission.MARKET_DATA_OPTIONS,
            Permission.AI_INSIGHTS
        ]
        
        # Should have all premium permissions
        has_all = auth_service.check_permissions(
            premium_user,
            permissions,
            require_all=True
        )
        assert has_all is True
    
    def test_require_permission_success(self, auth_service, test_user):
        """Test require_permission with valid permission"""
        rbac = auth_service.rbac_service
        rbac.assign_role(test_user.id, Role.FREE_USER)
        
        # Should not raise exception
        auth_service.require_permission(test_user, Permission.WATCHLIST_READ)
    
    def test_require_permission_failure(self, auth_service, test_user):
        """Test require_permission with invalid permission"""
        from fastapi import HTTPException
        
        rbac = auth_service.rbac_service
        rbac.assign_role(test_user.id, Role.FREE_USER)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.require_permission(test_user, Permission.ADMIN_USERS)
        
        assert exc_info.value.status_code == 403
    
    def test_assign_role(self, auth_service, test_user):
        """Test role assignment"""
        auth_service.assign_role(test_user, Role.PREMIUM_USER)
        
        assert Role.PREMIUM_USER.value in test_user.roles
    
    def test_revoke_role(self, auth_service, test_user):
        """Test role revocation"""
        # Assign role first
        auth_service.assign_role(test_user, Role.PREMIUM_USER)
        assert Role.PREMIUM_USER.value in test_user.roles
        
        # Revoke role
        auth_service.revoke_role(test_user, Role.PREMIUM_USER)
        assert Role.PREMIUM_USER.value not in test_user.roles
    
    def test_promote_to_premium(self, auth_service, test_user):
        """Test promoting user to premium"""
        auth_service.promote_to_premium(test_user)
        
        assert test_user.is_premium is True
        assert Role.PREMIUM_USER.value in test_user.roles
    
    def test_grant_trader_access(self, auth_service, test_user):
        """Test granting trader role"""
        auth_service.grant_trader_access(test_user)
        
        assert Role.TRADER.value in test_user.roles


class TestTrustedDevices:
    """Test trusted device management"""
    
    def test_generate_device_token(self, auth_service):
        """Test device token generation"""
        token1 = auth_service.generate_device_token()
        token2 = auth_service.generate_device_token()
        
        assert token1 is not None
        assert token2 is not None
        assert token1 != token2
    
    def test_add_trusted_device(self, auth_service, test_user):
        """Test adding trusted device"""
        device_token = auth_service.generate_device_token()
        
        auth_service.add_trusted_device(test_user, device_token)
        
        assert device_token in test_user.trusted_devices
    
    def test_verify_device_token(self, auth_service, test_user):
        """Test device token verification"""
        device_token = auth_service.generate_device_token()
        auth_service.add_trusted_device(test_user, device_token)
        
        # Valid token should verify
        is_valid = auth_service.verify_device_token(test_user, device_token)
        assert is_valid is True
        
        # Invalid token should fail
        is_valid = auth_service.verify_device_token(test_user, "invalid-token")
        assert is_valid is False
    
    def test_remove_trusted_device(self, auth_service, test_user):
        """Test removing trusted device"""
        device_token = auth_service.generate_device_token()
        auth_service.add_trusted_device(test_user, device_token)
        
        # Remove device
        removed = auth_service.remove_trusted_device(test_user, device_token)
        assert removed is True
        assert device_token not in test_user.trusted_devices


class TestMFAManagerIntegration:
    """Test MFA Manager integration"""
    
    def test_create_verification_challenge(self):
        """Test creating verification challenge"""
        mfa_manager = get_mfa_manager()
        user_id = uuid.uuid4()
        
        challenge = mfa_manager.create_verification_challenge(
            user_id=user_id,
            mfa_type=MFAType.TOTP
        )
        
        assert challenge is not None
        assert challenge.user_id == user_id
        assert challenge.mfa_type == MFAType.TOTP
    
    def test_generate_backup_codes(self):
        """Test backup code generation"""
        mfa_manager = get_mfa_manager()
        user_id = uuid.uuid4()
        
        codes = mfa_manager.generate_backup_codes(user_id)
        
        assert len(codes) == 10
        assert all(isinstance(code, str) for code in codes)
        assert len(set(codes)) == 10  # All unique
    
    def test_verify_backup_code(self):
        """Test backup code verification"""
        mfa_manager = get_mfa_manager()
        user_id = uuid.uuid4()
        
        # Generate codes
        codes = mfa_manager.generate_backup_codes(user_id)
        
        # Create challenge and verify with backup code
        challenge = mfa_manager.create_verification_challenge(
            user_id=user_id,
            mfa_type=MFAType.BACKUP_CODE
        )
        
        # Verify with first code
        success, message = mfa_manager.verify_challenge(
            challenge.challenge_id,
            codes[0]
        )
        
        assert success is True
        
        # Code should be marked as used
        remaining = mfa_manager.get_remaining_backup_codes(user_id)
        assert remaining == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
