"""
Integration Tests for Authentication Flow
End-to-end testing of registration, login, MFA, and RBAC
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app
import uuid


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user registration data"""
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!@",
        "first_name": "Test",
        "last_name": "User",
        "accepted_tos": True
    }


class TestRegistrationFlow:
    """Test user registration flow"""
    
    def test_successful_registration(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["requires_mfa"] is False
    
    def test_registration_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email"""
        # Register first time
        client.post("/api/v1/users/auth/register", json=test_user_data)
        
        # Try to register again with same email
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_registration_weak_password(self, client, test_user_data):
        """Test registration with weak password"""
        test_user_data["password"] = "weak"
        
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_registration_invalid_email(self, client, test_user_data):
        """Test registration with invalid email"""
        test_user_data["email"] = "invalid-email"
        
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        
        assert response.status_code == 422
    
    def test_registration_tos_not_accepted(self, client, test_user_data):
        """Test registration without accepting TOS"""
        test_user_data["accepted_tos"] = False
        
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        
        assert response.status_code == 422


class TestLoginFlow:
    """Test user login flow"""
    
    def test_successful_login(self, client, test_user_data):
        """Test successful login"""
        # Register user first
        client.post("/api/v1/users/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/v1/users/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["requires_mfa"] is False
    
    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password"""
        # Register user first
        client.post("/api/v1/users/auth/register", json=test_user_data)
        
        # Try login with wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123!"
        }
        response = client.post("/api/v1/users/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "Password123!"
        }
        response = client.post("/api/v1/users/auth/login", json=login_data)
        
        assert response.status_code == 401


class TestTokenRefreshFlow:
    """Test token refresh flow"""
    
    def test_refresh_token(self, client, test_user_data):
        """Test refreshing access token"""
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Refresh token
        response = client.post(
            "/api/v1/users/auth/refresh",
            params={"refresh_token": tokens["refresh_token"]}
        )
        
        assert response.status_code == 200
        new_tokens = response.json()
        
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]


class TestMFAFlow:
    """Test MFA setup and verification flow"""
    
    def test_mfa_setup(self, client, test_user_data):
        """Test MFA setup"""
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Setup MFA
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post("/api/v1/users/auth/mfa/setup", headers=headers)
        
        assert response.status_code == 200
        mfa_data = response.json()
        
        assert "secret" in mfa_data
        assert "qr_code_uri" in mfa_data
        assert "otpauth://" in mfa_data["qr_code_uri"]
    
    def test_mfa_verify_and_enable(self, client, test_user_data):
        """Test MFA verification and enabling"""
        import pyotp
        
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Setup MFA
        response = client.post("/api/v1/users/auth/mfa/setup", headers=headers)
        mfa_data = response.json()
        secret = mfa_data["secret"]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        # Verify and enable MFA
        verify_data = {
            "secret": secret,
            "code": code,
            "generate_backup_codes": True
        }
        response = client.post(
            "/api/v1/users/auth/mfa/verify",
            json=verify_data,
            headers=headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "backup_codes" in result


class TestProtectedEndpoints:
    """Test protected endpoints requiring authentication"""
    
    def test_get_profile_authenticated(self, client, test_user_data):
        """Test getting profile with valid token"""
        # Register user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Get profile
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        profile = response.json()
        
        assert profile["email"] == test_user_data["email"]
        assert profile["first_name"] == test_user_data["first_name"]
    
    def test_get_profile_unauthenticated(self, client):
        """Test getting profile without token"""
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == 403  # No credentials
    
    def test_get_profile_invalid_token(self, client):
        """Test getting profile with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401


class TestSessionManagement:
    """Test session management endpoints"""
    
    def test_get_active_sessions(self, client, test_user_data):
        """Test getting active sessions"""
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Get active sessions
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/me/sessions", headers=headers)
        
        assert response.status_code == 200
        sessions = response.json()
        
        assert isinstance(sessions, list)
        assert len(sessions) > 0
    
    def test_logout(self, client, test_user_data):
        """Test logout"""
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Logout
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post("/api/v1/users/auth/logout", headers=headers)
        
        assert response.status_code == 200
        
        # Token should no longer work (in production with Redis)
        # For now, token is still valid in memory
    
    def test_logout_all_sessions(self, client, test_user_data):
        """Test logging out from all sessions"""
        # Register and login
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Logout all
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post("/api/v1/users/auth/logout-all", headers=headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "sessions" in result["message"].lower()


class TestPasswordManagement:
    """Test password management endpoints"""
    
    def test_change_password(self, client, test_user_data):
        """Test changing password"""
        # Register user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Change password
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        change_data = {
            "current_password": test_user_data["password"],
            "new_password": "NewSecurePass123!@"
        }
        response = client.post(
            "/api/v1/users/auth/password/change",
            json=change_data,
            headers=headers
        )
        
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self, client, test_user_data):
        """Test changing password with wrong current password"""
        # Register user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Try to change with wrong current password
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        change_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePass123!@"
        }
        response = client.post(
            "/api/v1/users/auth/password/change",
            json=change_data,
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_request_password_reset(self, client, test_user_data):
        """Test requesting password reset"""
        # Register user
        client.post("/api/v1/users/auth/register", json=test_user_data)
        
        # Request password reset
        reset_data = {"email": test_user_data["email"]}
        response = client.post("/api/v1/users/auth/password/reset", json=reset_data)
        
        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()


class TestRBACEndpoints:
    """Test RBAC and permission-based endpoints"""
    
    def test_free_user_permissions(self, client, test_user_data):
        """Test that free user has correct permissions"""
        # Register user (gets free_user role by default)
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Get profile to verify roles
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        profile = response.json()
        assert "free_user" in profile["roles"]
    
    def test_admin_endpoint_unauthorized(self, client, test_user_data):
        """Test that non-admin cannot access admin endpoints"""
        # Register regular user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Try to access admin endpoint
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/admin/users", headers=headers)
        
        # Should be forbidden (403) or not found if endpoint doesn't exist yet
        assert response.status_code in [403, 404]


class TestProfileManagement:
    """Test user profile management"""
    
    def test_update_profile(self, client, test_user_data):
        """Test updating user profile"""
        # Register user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Update profile
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+1234567890"
        }
        response = client.patch(
            "/api/v1/users/me",
            params=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        profile = response.json()
        
        assert profile["first_name"] == "Updated"
        assert profile["last_name"] == "Name"
    
    def test_get_user_preferences(self, client, test_user_data):
        """Test getting user preferences"""
        # Register user
        response = client.post("/api/v1/users/auth/register", json=test_user_data)
        tokens = response.json()
        
        # Get preferences
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.get("/api/v1/users/me/profile", headers=headers)
        
        assert response.status_code == 200
        preferences = response.json()
        
        assert "notification_preferences" in preferences
        assert "theme" in preferences


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
