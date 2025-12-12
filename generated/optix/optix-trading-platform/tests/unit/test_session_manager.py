"""
Unit Tests for Session Manager
Tests session creation, validation, trusted devices, and security monitoring
"""
import pytest
from datetime import datetime, timedelta
import uuid
from src.user_service.session_manager import (
    SessionManager, Session, SessionStatus, TrustedDevice,
    DeviceTrustLevel, SecurityEvent
)


@pytest.fixture
def session_manager():
    """Create session manager instance for testing"""
    return SessionManager(
        session_timeout_minutes=30,
        max_sessions_per_user=5,
        trust_device_days=30
    )


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


class TestSessionManager:
    """Test session manager functionality"""
    
    def test_create_session(self, session_manager, test_user_id):
        """Test session creation"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-device-fp",
            mfa_verified=True
        )
        
        assert session is not None
        assert session.user_id == test_user_id
        assert session.status == SessionStatus.ACTIVE
        assert session.mfa_verified is True
        assert session.is_trusted_device is False
    
    def test_create_session_with_trusted_device(self, session_manager, test_user_id):
        """Test session creation with trusted device"""
        # First trust the device
        trusted_device = session_manager.trust_device(
            user_id=test_user_id,
            device_fingerprint="test-device-fp",
            device_name="Test Device"
        )
        
        # Create session with trust token
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-device-fp",
            trust_token=trusted_device.trust_token,
            mfa_verified=False
        )
        
        assert session.is_trusted_device is True
        assert session.device_trust_level == DeviceTrustLevel.TRUSTED
    
    def test_get_session(self, session_manager, test_user_id):
        """Test retrieving session"""
        # Create session
        created_session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Retrieve session
        retrieved_session = session_manager.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.user_id == test_user_id
    
    def test_validate_session(self, session_manager, test_user_id):
        """Test session validation"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Validate session
        is_valid = session_manager.validate_session(session.session_id)
        assert is_valid is True
    
    def test_validate_expired_session(self, session_manager, test_user_id):
        """Test validation of expired session"""
        # Create session manager with very short timeout
        short_manager = SessionManager(session_timeout_minutes=0)
        
        session = short_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        # Validation should fail
        is_valid = short_manager.validate_session(session.session_id)
        assert is_valid is False
    
    def test_update_session_activity(self, session_manager, test_user_id):
        """Test updating session activity"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        initial_activity = session.last_activity_at
        initial_count = session.request_count
        
        # Wait a bit
        import time
        time.sleep(0.1)
        
        # Update activity
        session_manager.update_session_activity(
            session.session_id,
            endpoint="/api/v1/watchlists"
        )
        
        # Check updates
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.last_activity_at > initial_activity
        assert updated_session.request_count == initial_count + 1
        assert len(updated_session.last_requests) == 1
    
    def test_terminate_session(self, session_manager, test_user_id):
        """Test session termination"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Terminate session
        success = session_manager.terminate_session(session.session_id)
        assert success is True
        
        # Session should be terminated
        terminated_session = session_manager._sessions.get(session.session_id)
        assert terminated_session.status == SessionStatus.TERMINATED
    
    def test_terminate_user_sessions(self, session_manager, test_user_id):
        """Test terminating all user sessions"""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = session_manager.create_session(
                user_id=test_user_id,
                ip_address=f"127.0.0.{i+1}",
                user_agent="TestAgent/1.0",
                device_fingerprint=f"test-fp-{i}",
                mfa_verified=True
            )
            sessions.append(session)
        
        # Terminate all sessions except first one
        count = session_manager.terminate_user_sessions(
            test_user_id,
            except_session_id=sessions[0].session_id
        )
        
        assert count == 2
        
        # First session should still be active
        first_session = session_manager.get_session(sessions[0].session_id)
        assert first_session is not None
        assert first_session.status == SessionStatus.ACTIVE
    
    def test_get_user_sessions(self, session_manager, test_user_id):
        """Test getting all user sessions"""
        # Create multiple sessions
        for i in range(3):
            session_manager.create_session(
                user_id=test_user_id,
                ip_address=f"127.0.0.{i+1}",
                user_agent="TestAgent/1.0",
                device_fingerprint=f"test-fp-{i}",
                mfa_verified=True
            )
        
        # Get all sessions
        sessions = session_manager.get_user_sessions(test_user_id)
        assert len(sessions) == 3
        
        for session in sessions:
            assert session.user_id == test_user_id
            assert session.status == SessionStatus.ACTIVE
    
    def test_enforce_session_limit(self, session_manager, test_user_id):
        """Test enforcing maximum sessions per user"""
        # Create more sessions than allowed
        for i in range(7):  # Max is 5
            session_manager.create_session(
                user_id=test_user_id,
                ip_address=f"127.0.0.{i+1}",
                user_agent="TestAgent/1.0",
                device_fingerprint=f"test-fp-{i}",
                mfa_verified=True
            )
        
        # Should only have max_sessions
        sessions = session_manager.get_user_sessions(test_user_id)
        assert len(sessions) == 5
    
    def test_trust_device(self, session_manager, test_user_id):
        """Test trusting a device"""
        device = session_manager.trust_device(
            user_id=test_user_id,
            device_fingerprint="test-device-fp",
            device_name="My iPhone",
            device_type="mobile",
            duration_days=30
        )
        
        assert device is not None
        assert device.user_id == test_user_id
        assert device.device_name == "My iPhone"
        assert device.device_type == "mobile"
        assert device.trust_level == DeviceTrustLevel.TRUSTED
        assert device.is_valid() is True
        assert device.trust_token is not None
    
    def test_revoke_device_trust(self, session_manager, test_user_id):
        """Test revoking device trust"""
        # Trust device
        device = session_manager.trust_device(
            user_id=test_user_id,
            device_fingerprint="test-fp",
            device_name="Test Device"
        )
        
        # Revoke trust
        success = session_manager.revoke_device_trust(device.device_id)
        assert success is True
        
        # Device should be revoked
        assert device.revoked is True
        assert device.trust_level == DeviceTrustLevel.BLOCKED
        assert device.is_valid() is False
    
    def test_get_trusted_devices(self, session_manager, test_user_id):
        """Test getting trusted devices for user"""
        # Trust multiple devices
        for i in range(3):
            session_manager.trust_device(
                user_id=test_user_id,
                device_fingerprint=f"test-fp-{i}",
                device_name=f"Device {i}"
            )
        
        # Get trusted devices
        devices = session_manager.get_trusted_devices(test_user_id)
        assert len(devices) == 3
        
        for device in devices:
            assert device.user_id == test_user_id
            assert device.is_valid() is True
    
    def test_security_event_logging(self, session_manager, test_user_id):
        """Test security event logging"""
        # Create session (should log event)
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Get security events
        events = session_manager.get_security_events(user_id=test_user_id)
        
        assert len(events) > 0
        assert any(e.event_type == "session_created" for e in events)
    
    def test_flag_suspicious_activity(self, session_manager, test_user_id):
        """Test flagging suspicious activity"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Flag as suspicious
        session_manager._flag_suspicious_activity(
            session,
            reason="Unusual login location"
        )
        
        # Session should be flagged
        assert session.status == SessionStatus.SUSPICIOUS
        
        # Should have security event
        events = session_manager.get_security_events(
            user_id=test_user_id,
            severity="high"
        )
        assert len(events) > 0
        assert any(
            e.event_type == "suspicious_activity" and
            "Unusual login location" in e.description
            for e in events
        )
    
    def test_cleanup_expired_sessions(self, session_manager, test_user_id):
        """Test cleanup of expired sessions"""
        # Create session manager with short timeout
        short_manager = SessionManager(session_timeout_minutes=0)
        
        # Create sessions
        for i in range(3):
            short_manager.create_session(
                user_id=test_user_id,
                ip_address=f"127.0.0.{i+1}",
                user_agent="TestAgent/1.0",
                device_fingerprint=f"test-fp-{i}",
                mfa_verified=True
            )
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        # Cleanup
        count = short_manager.cleanup_expired_sessions()
        assert count == 3
    
    def test_device_id_generation(self, session_manager):
        """Test device ID generation"""
        device_fp1 = "fingerprint-123"
        device_fp2 = "fingerprint-456"
        user_agent = "TestAgent/1.0"
        
        id1 = session_manager._generate_device_id(device_fp1, user_agent)
        id2 = session_manager._generate_device_id(device_fp1, user_agent)
        id3 = session_manager._generate_device_id(device_fp2, user_agent)
        
        # Same inputs should produce same ID
        assert id1 == id2
        
        # Different inputs should produce different ID
        assert id1 != id3
        
        # ID should be consistent length
        assert len(id1) == 16
    
    def test_session_activity_tracking(self, session_manager, test_user_id):
        """Test session activity tracking"""
        session = session_manager.create_session(
            user_id=test_user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="test-fp",
            mfa_verified=True
        )
        
        # Make multiple requests
        endpoints = [
            "/api/v1/watchlists",
            "/api/v1/alerts",
            "/api/v1/positions"
        ]
        
        for endpoint in endpoints:
            session_manager.update_session_activity(session.session_id, endpoint)
        
        # Check activity
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.request_count == 3
        assert len(updated_session.last_requests) == 3
        
        # Verify endpoints are tracked
        tracked_endpoints = [r["endpoint"] for r in updated_session.last_requests]
        assert tracked_endpoints == endpoints


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
