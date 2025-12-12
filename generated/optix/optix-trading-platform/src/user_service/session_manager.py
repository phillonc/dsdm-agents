"""
Session Management Module
Manages user sessions, trusted devices, and security monitoring
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from enum import Enum
import uuid
import secrets
from pydantic import BaseModel, Field
import hashlib


class SessionStatus(str, Enum):
    """Session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"


class DeviceTrustLevel(str, Enum):
    """Device trust levels"""
    TRUSTED = "trusted"
    RECOGNIZED = "recognized"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class Session(BaseModel):
    """User session"""
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    device_id: str
    device_fingerprint: str
    ip_address: str
    user_agent: str
    location: Optional[Dict[str, str]] = None
    
    # Session timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    
    # Status
    status: SessionStatus = SessionStatus.ACTIVE
    terminated_at: Optional[datetime] = None
    
    # Security flags
    is_trusted_device: bool = False
    device_trust_level: DeviceTrustLevel = DeviceTrustLevel.UNKNOWN
    mfa_verified: bool = False
    
    # Activity tracking
    request_count: int = 0
    last_requests: List[Dict] = Field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at or self.status != SessionStatus.ACTIVE
    
    def update_activity(self, endpoint: Optional[str] = None) -> None:
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
        self.request_count += 1
        
        if endpoint:
            # Keep last 10 requests
            self.last_requests.append({
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat()
            })
            if len(self.last_requests) > 10:
                self.last_requests.pop(0)


class TrustedDevice(BaseModel):
    """Trusted device record"""
    device_id: str
    user_id: uuid.UUID
    device_fingerprint: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None  # mobile, desktop, tablet
    
    # Trust information
    trust_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    trust_level: DeviceTrustLevel = DeviceTrustLevel.TRUSTED
    
    # Usage tracking
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_ip_address: Optional[str] = None
    usage_count: int = 0
    
    # Security
    trusted_at: datetime = Field(default_factory=datetime.utcnow)
    trusted_until: Optional[datetime] = None  # Optional expiration
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if trust is still valid"""
        if self.revoked:
            return False
        if self.trusted_until and datetime.utcnow() > self.trusted_until:
            return False
        return True


class SecurityEvent(BaseModel):
    """Security event log"""
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    
    # Context
    session_id: Optional[uuid.UUID] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Additional data
    metadata: Dict = Field(default_factory=dict)
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Response
    action_taken: Optional[str] = None
    resolved: bool = False


class SessionManager:
    """
    Manages user sessions, trusted devices, and security monitoring
    Implements session security best practices
    """
    
    def __init__(
        self,
        session_timeout_minutes: int = 30,
        max_sessions_per_user: int = 5,
        trust_device_days: int = 30,
        suspicious_activity_threshold: int = 100
    ):
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_sessions_per_user = max_sessions_per_user
        self.trust_device_duration = timedelta(days=trust_device_days)
        self.suspicious_activity_threshold = suspicious_activity_threshold
        
        # Storage (use Redis in production)
        self._sessions: Dict[uuid.UUID, Session] = {}
        self._user_sessions: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        self._trusted_devices: Dict[str, TrustedDevice] = {}
        self._security_events: List[SecurityEvent] = []
        
        # Session tracking by device
        self._device_sessions: Dict[str, Set[uuid.UUID]] = {}
    
    def create_session(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        user_agent: str,
        device_fingerprint: str,
        trust_token: Optional[str] = None,
        mfa_verified: bool = False
    ) -> Session:
        """
        Create new user session
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            device_fingerprint: Device fingerprint hash
            trust_token: Optional trusted device token
            mfa_verified: Whether MFA was verified
        
        Returns:
            New session object
        """
        # Generate device ID
        device_id = self._generate_device_id(device_fingerprint, user_agent)
        
        # Check if device is trusted
        is_trusted = False
        trust_level = DeviceTrustLevel.UNKNOWN
        
        if trust_token:
            trusted_device = self._get_trusted_device_by_token(trust_token)
            if trusted_device and trusted_device.user_id == user_id:
                is_trusted = True
                trust_level = DeviceTrustLevel.TRUSTED
                trusted_device.last_seen_at = datetime.utcnow()
                trusted_device.last_ip_address = ip_address
                trusted_device.usage_count += 1
        
        # Check for recognized device
        if device_id in self._device_sessions and not is_trusted:
            trust_level = DeviceTrustLevel.RECOGNIZED
        
        # Create session
        session = Session(
            user_id=user_id,
            device_id=device_id,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + self.session_timeout,
            is_trusted_device=is_trusted,
            device_trust_level=trust_level,
            mfa_verified=mfa_verified
        )
        
        # Store session
        self._sessions[session.session_id] = session
        
        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session.session_id)
        
        # Track device sessions
        if device_id not in self._device_sessions:
            self._device_sessions[device_id] = set()
        self._device_sessions[device_id].add(session.session_id)
        
        # Enforce max sessions per user
        self._enforce_session_limit(user_id)
        
        # Log security event
        self._log_security_event(
            user_id=user_id,
            event_type="session_created",
            severity="low",
            description=f"New session created from {ip_address}",
            session_id=session.session_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return session
    
    def get_session(self, session_id: uuid.UUID) -> Optional[Session]:
        """Get session by ID"""
        session = self._sessions.get(session_id)
        
        if session and session.is_expired():
            session.status = SessionStatus.EXPIRED
            return None
        
        return session
    
    def validate_session(
        self,
        session_id: uuid.UUID,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Validate session
        
        Args:
            session_id: Session ID
            ip_address: Client IP (optional, for additional validation)
        
        Returns:
            True if session is valid
        """
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        # Check IP address if provided (optional strict mode)
        # if ip_address and session.ip_address != ip_address:
        #     self._flag_suspicious_activity(session, "IP address mismatch")
        #     return False
        
        # Update activity
        session.update_activity()
        
        return True
    
    def update_session_activity(
        self,
        session_id: uuid.UUID,
        endpoint: Optional[str] = None
    ) -> bool:
        """Update session last activity"""
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        session.update_activity(endpoint)
        return True
    
    def terminate_session(self, session_id: uuid.UUID) -> bool:
        """Terminate specific session"""
        session = self._sessions.get(session_id)
        
        if not session:
            return False
        
        session.status = SessionStatus.TERMINATED
        session.terminated_at = datetime.utcnow()
        
        # Remove from tracking
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id].discard(session_id)
        
        if session.device_id in self._device_sessions:
            self._device_sessions[session.device_id].discard(session_id)
        
        return True
    
    def terminate_user_sessions(
        self,
        user_id: uuid.UUID,
        except_session_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Terminate all sessions for a user
        
        Args:
            user_id: User ID
            except_session_id: Optional session to keep active
        
        Returns:
            Number of sessions terminated
        """
        if user_id not in self._user_sessions:
            return 0
        
        session_ids = list(self._user_sessions[user_id])
        count = 0
        
        for session_id in session_ids:
            if except_session_id and session_id == except_session_id:
                continue
            
            if self.terminate_session(session_id):
                count += 1
        
        return count
    
    def get_user_sessions(self, user_id: uuid.UUID) -> List[Session]:
        """Get all active sessions for user"""
        if user_id not in self._user_sessions:
            return []
        
        sessions = []
        for session_id in self._user_sessions[user_id]:
            session = self.get_session(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _enforce_session_limit(self, user_id: uuid.UUID) -> None:
        """Enforce maximum sessions per user"""
        sessions = self.get_user_sessions(user_id)
        
        if len(sessions) > self.max_sessions_per_user:
            # Terminate oldest sessions
            sessions.sort(key=lambda s: s.created_at)
            excess = len(sessions) - self.max_sessions_per_user
            
            for i in range(excess):
                self.terminate_session(sessions[i].session_id)
    
    # Trusted Device Management
    
    def trust_device(
        self,
        user_id: uuid.UUID,
        device_fingerprint: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        duration_days: Optional[int] = None
    ) -> TrustedDevice:
        """
        Mark device as trusted
        
        Args:
            user_id: User ID
            device_fingerprint: Device fingerprint
            device_name: Human-readable device name
            device_type: Device type (mobile, desktop, etc.)
            duration_days: Trust duration (None for permanent)
        
        Returns:
            TrustedDevice object
        """
        device_id = self._generate_device_id(device_fingerprint, "")
        
        # Check if already trusted
        if device_id in self._trusted_devices:
            device = self._trusted_devices[device_id]
            device.last_seen_at = datetime.utcnow()
            return device
        
        # Create trusted device
        trusted_until = None
        if duration_days:
            trusted_until = datetime.utcnow() + timedelta(days=duration_days)
        
        trusted_device = TrustedDevice(
            device_id=device_id,
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            device_type=device_type,
            trusted_until=trusted_until
        )
        
        self._trusted_devices[device_id] = trusted_device
        
        # Log security event
        self._log_security_event(
            user_id=user_id,
            event_type="device_trusted",
            severity="low",
            description=f"Device {device_name or device_id} marked as trusted",
            device_id=device_id
        )
        
        return trusted_device
    
    def revoke_device_trust(self, device_id: str) -> bool:
        """Revoke trust for a device"""
        if device_id not in self._trusted_devices:
            return False
        
        device = self._trusted_devices[device_id]
        device.revoked = True
        device.revoked_at = datetime.utcnow()
        device.trust_level = DeviceTrustLevel.BLOCKED
        
        # Log security event
        self._log_security_event(
            user_id=device.user_id,
            event_type="device_trust_revoked",
            severity="medium",
            description=f"Trust revoked for device {device_id}",
            device_id=device_id
        )
        
        return True
    
    def get_trusted_devices(self, user_id: uuid.UUID) -> List[TrustedDevice]:
        """Get all trusted devices for user"""
        return [
            device for device in self._trusted_devices.values()
            if device.user_id == user_id and device.is_valid()
        ]
    
    def _get_trusted_device_by_token(self, trust_token: str) -> Optional[TrustedDevice]:
        """Get trusted device by trust token"""
        for device in self._trusted_devices.values():
            if device.trust_token == trust_token and device.is_valid():
                return device
        return None
    
    # Security Monitoring
    
    def _flag_suspicious_activity(
        self,
        session: Session,
        reason: str
    ) -> None:
        """Flag suspicious activity"""
        session.status = SessionStatus.SUSPICIOUS
        
        self._log_security_event(
            user_id=session.user_id,
            event_type="suspicious_activity",
            severity="high",
            description=f"Suspicious activity detected: {reason}",
            session_id=session.session_id,
            device_id=session.device_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            metadata={"reason": reason}
        )
    
    def _log_security_event(
        self,
        user_id: uuid.UUID,
        event_type: str,
        severity: str,
        description: str,
        **kwargs
    ) -> SecurityEvent:
        """Log security event"""
        event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            **kwargs
        )
        
        self._security_events.append(event)
        
        # In production, also log to database and monitoring system
        
        return event
    
    def get_security_events(
        self,
        user_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events with optional filters"""
        events = self._security_events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        # Sort by timestamp, newest first
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]
    
    # Utility Methods
    
    def _generate_device_id(self, device_fingerprint: str, user_agent: str) -> str:
        """Generate stable device ID"""
        data = f"{device_fingerprint}:{user_agent}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < now or session.status != SessionStatus.ACTIVE
        ]
        
        for sid in expired_ids:
            self.terminate_session(sid)
        
        return len(expired_ids)


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(**kwargs) -> SessionManager:
    """Get session manager singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(**kwargs)
    return _session_manager
