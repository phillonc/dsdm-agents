"""
Unit Tests for JWT Service
Tests token generation, validation, rotation, and revocation
"""
import pytest
from datetime import datetime, timedelta
import uuid
from src.user_service.jwt_service import (
    JWTService, TokenType, TokenStatus, RefreshTokenFamily, TokenRecord
)


@pytest.fixture
def jwt_service():
    """Create JWT service instance for testing"""
    return JWTService(
        secret_key="test-secret-key-for-testing-only",
        access_token_expire_minutes=15,
        refresh_token_expire_days=30
    )


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


class TestJWTService:
    """Test JWT service functionality"""
    
    def test_generate_jti(self, jwt_service):
        """Test JTI generation"""
        jti1 = jwt_service.generate_jti()
        jti2 = jwt_service.generate_jti()
        
        assert jti1 != jti2
        assert len(jti1) > 0
        assert len(jti2) > 0
    
    def test_create_access_token(self, jwt_service, test_user_id):
        """Test access token creation"""
        email = "test@example.com"
        roles = ["free_user"]
        permissions = ["watchlist:read", "alert:write"]
        
        token, record = jwt_service.create_access_token(
            user_id=test_user_id,
            email=email,
            roles=roles,
            permissions=permissions,
            is_premium=False
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert record.token_type == TokenType.ACCESS
        assert record.user_id == test_user_id
        assert record.status == TokenStatus.ACTIVE
    
    def test_create_refresh_token(self, jwt_service, test_user_id):
        """Test refresh token creation"""
        token, record, family = jwt_service.create_refresh_token(
            user_id=test_user_id,
            device_fingerprint="test-device-fp",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert token is not None
        assert record.token_type == TokenType.REFRESH
        assert record.user_id == test_user_id
        assert record.family_id == family.family_id
        assert family.user_id == test_user_id
    
    def test_verify_access_token(self, jwt_service, test_user_id):
        """Test access token verification"""
        email = "test@example.com"
        roles = ["free_user"]
        permissions = ["watchlist:read"]
        
        token, _ = jwt_service.create_access_token(
            user_id=test_user_id,
            email=email,
            roles=roles,
            permissions=permissions
        )
        
        # Verify token
        payload = jwt_service.verify_token(token, expected_type=TokenType.ACCESS)
        
        assert payload["sub"] == str(test_user_id)
        assert payload["email"] == email
        assert payload["roles"] == roles
        assert payload["permissions"] == permissions
        assert payload["type"] == TokenType.ACCESS.value
    
    def test_verify_invalid_token(self, jwt_service):
        """Test verification of invalid token"""
        with pytest.raises(ValueError, match="Invalid token"):
            jwt_service.verify_token("invalid-token")
    
    def test_verify_wrong_token_type(self, jwt_service, test_user_id):
        """Test verification with wrong expected type"""
        token, _ = jwt_service.create_access_token(
            user_id=test_user_id,
            email="test@example.com",
            roles=["free_user"],
            permissions=[]
        )
        
        with pytest.raises(ValueError, match="Invalid token type"):
            jwt_service.verify_token(token, expected_type=TokenType.REFRESH)
    
    def test_rotate_refresh_token(self, jwt_service, test_user_id):
        """Test refresh token rotation"""
        # Create initial refresh token
        old_token, old_record, family = jwt_service.create_refresh_token(
            user_id=test_user_id
        )
        
        # Rotate token
        new_token, new_record, new_family = jwt_service.rotate_refresh_token(old_token)
        
        assert new_token != old_token
        assert new_record.jti != old_record.jti
        assert new_family.family_id == family.family_id
        assert old_record.status == TokenStatus.REPLACED
        assert old_record.replaced_by == new_record.jti
    
    def test_token_reuse_detection(self, jwt_service, test_user_id):
        """Test detection of token reuse (theft detection)"""
        # Create and rotate token
        old_token, _, _ = jwt_service.create_refresh_token(user_id=test_user_id)
        new_token, _, _ = jwt_service.rotate_refresh_token(old_token)
        
        # Try to reuse old token (simulating theft)
        with pytest.raises(ValueError, match="Token reuse detected"):
            jwt_service.rotate_refresh_token(old_token)
    
    def test_revoke_token(self, jwt_service, test_user_id):
        """Test token revocation"""
        token, record = jwt_service.create_access_token(
            user_id=test_user_id,
            email="test@example.com",
            roles=["free_user"],
            permissions=[]
        )
        
        # Revoke token
        success = jwt_service.revoke_token(record.jti)
        assert success is True
        assert record.status == TokenStatus.REVOKED
        
        # Try to verify revoked token
        with pytest.raises(ValueError, match="Token has been revoked"):
            jwt_service.verify_token(token)
    
    def test_revoke_user_tokens(self, jwt_service, test_user_id):
        """Test revoking all tokens for a user"""
        # Create multiple tokens
        tokens = []
        for i in range(3):
            token, record = jwt_service.create_access_token(
                user_id=test_user_id,
                email=f"test{i}@example.com",
                roles=["free_user"],
                permissions=[]
            )
            tokens.append((token, record))
        
        # Revoke all user tokens
        count = jwt_service.revoke_user_tokens(test_user_id)
        assert count == 3
        
        # Verify all tokens are revoked
        for token, record in tokens:
            assert record.status == TokenStatus.REVOKED
            with pytest.raises(ValueError):
                jwt_service.verify_token(token)
    
    def test_create_mfa_challenge_token(self, jwt_service, test_user_id):
        """Test MFA challenge token creation"""
        challenge_id = str(uuid.uuid4())
        mfa_methods = ["totp", "sms"]
        
        token, record = jwt_service.create_mfa_challenge_token(
            user_id=test_user_id,
            challenge_id=challenge_id,
            mfa_methods=mfa_methods
        )
        
        assert token is not None
        assert record.token_type == TokenType.MFA_CHALLENGE
        
        # Verify token
        payload = jwt_service.verify_token(token, expected_type=TokenType.MFA_CHALLENGE)
        assert payload["challenge_id"] == challenge_id
        assert payload["mfa_methods"] == mfa_methods
    
    def test_create_password_reset_token(self, jwt_service, test_user_id):
        """Test password reset token creation"""
        email = "test@example.com"
        
        token, record = jwt_service.create_password_reset_token(
            user_id=test_user_id,
            email=email
        )
        
        assert token is not None
        assert record.token_type == TokenType.PASSWORD_RESET
        
        # Verify token
        payload = jwt_service.verify_token(token, expected_type=TokenType.PASSWORD_RESET)
        assert payload["email"] == email
    
    def test_create_email_verification_token(self, jwt_service, test_user_id):
        """Test email verification token creation"""
        email = "test@example.com"
        
        token, record = jwt_service.create_email_verification_token(
            user_id=test_user_id,
            email=email
        )
        
        assert token is not None
        assert record.token_type == TokenType.EMAIL_VERIFICATION
        
        # Verify token
        payload = jwt_service.verify_token(
            token,
            expected_type=TokenType.EMAIL_VERIFICATION
        )
        assert payload["email"] == email
    
    def test_get_user_active_tokens(self, jwt_service, test_user_id):
        """Test getting active tokens for user"""
        # Create multiple tokens
        for i in range(3):
            jwt_service.create_access_token(
                user_id=test_user_id,
                email=f"test{i}@example.com",
                roles=["free_user"],
                permissions=[]
            )
        
        # Get active tokens
        active_tokens = jwt_service.get_user_active_tokens(test_user_id)
        assert len(active_tokens) == 3
        
        for token in active_tokens:
            assert token.status == TokenStatus.ACTIVE
            assert token.user_id == test_user_id
    
    def test_cleanup_expired_tokens(self, jwt_service, test_user_id):
        """Test cleanup of expired tokens"""
        # Create service with short expiration
        short_service = JWTService(
            secret_key="test-secret",
            access_token_expire_minutes=0  # Immediate expiration
        )
        
        # Create token that expires immediately
        token, record = short_service.create_access_token(
            user_id=test_user_id,
            email="test@example.com",
            roles=["free_user"],
            permissions=[]
        )
        
        # Wait a bit for expiration
        import time
        time.sleep(0.1)
        
        # Cleanup expired tokens
        count = short_service.cleanup_expired_tokens()
        assert count > 0
    
    def test_device_fingerprint_creation(self, jwt_service):
        """Test device fingerprint generation"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        ip_address = "192.168.1.1"
        
        fp1 = jwt_service.create_device_fingerprint(user_agent, ip_address)
        fp2 = jwt_service.create_device_fingerprint(user_agent, ip_address)
        fp3 = jwt_service.create_device_fingerprint(user_agent, "192.168.1.2")
        
        # Same inputs should produce same fingerprint
        assert fp1 == fp2
        
        # Different inputs should produce different fingerprint
        assert fp1 != fp3
        
        # Fingerprint should be a hash
        assert len(fp1) == 64  # SHA256 hex digest length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
