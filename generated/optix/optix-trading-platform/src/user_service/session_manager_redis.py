"""
Redis-Integrated Session Manager
Session manager with Redis-backed persistent storage
"""
from typing import Optional, List, Set
from datetime import datetime, timedelta
import uuid
import structlog
from .session_manager import (
    SessionManager,
    Session,
    TrustedDevice,
    SecurityEvent,
    SessionStatus,
    DeviceTrustLevel
)
from .redis_session_store import RedisSessionStore, get_session_store
from .redis_client import RedisClient

logger = structlog.get_logger(__name__)


class RedisSessionManager(SessionManager):
    """
    Session manager with Redis persistence for scalability
    Extends base SessionManager with Redis-backed storage
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        session_timeout_minutes: int = 30,
        max_sessions_per_user: int = 5,
        trust_device_days: int = 30,
        suspicious_activity_threshold: int = 100,
        use_redis_storage: bool = True
    ):
        """
        Initialize Redis session manager
        
        Args:
            redis_client: Optional RedisClient instance
            session_timeout_minutes: Session timeout
            max_sessions_per_user: Max concurrent sessions
            trust_device_days: Device trust duration
            suspicious_activity_threshold: Threshold for suspicious activity
            use_redis_storage: Use Redis for session storage
        """
        super().__init__(
            session_timeout_minutes=session_timeout_minutes,
            max_sessions_per_user=max_sessions_per_user,
            trust_device_days=trust_device_days,
            suspicious_activity_threshold=suspicious_activity_threshold
        )
        
        self.use_redis_storage = use_redis_storage
        if use_redis_storage:
            self.store = get_session_store(redis_client)
        else:
            self.store = None
    
    async def create_session_async(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        user_agent: str,
        device_fingerprint: str,
        trust_token: Optional[str] = None,
        mfa_verified: bool = False
    ) -> Session:
        """
        Create new user session with Redis storage
        
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
        
        # Check if device is trusted (check Redis if enabled)
        is_trusted = False
        trust_level = DeviceTrustLevel.UNKNOWN
        
        if trust_token and self.use_redis_storage and self.store:
            # Look up trusted device in Redis
            trusted_devices = await self.store.get_user_trusted_devices(user_id)
            for device in trusted_devices:
                if device.trust_token == trust_token and device.is_valid():
                    is_trusted = True
                    trust_level = DeviceTrustLevel.TRUSTED
                    device.last_seen_at = datetime.utcnow()
                    device.last_ip_address = ip_address
                    device.usage_count += 1
                    await self.store.save_trusted_device(device)
                    break
        
        # Check for recognized device in Redis
        if self.use_redis_storage and self.store and not is_trusted:
            device_sessions = await self.store.get_device_sessions(device_id)
            if device_sessions:
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
        
        # Store in Redis
        if self.use_redis_storage and self.store:
            await self.store.create_session(session)
        else:
            # Fall back to in-memory
            self._sessions[session.session_id] = session
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session.session_id)
            if device_id not in self._device_sessions:
                self._device_sessions[device_id] = set()
            self._device_sessions[device_id].add(session.session_id)
        
        # Enforce max sessions per user
        await self._enforce_session_limit_async(user_id)
        
        # Log security event
        await self._log_security_event_async(
            user_id=user_id,
            event_type="session_created",
            severity="low",
            description=f"New session created from {ip_address}",
            session_id=session.session_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(
            "session_created",
            session_id=str(session.session_id),
            user_id=str(user_id),
            device_trust_level=trust_level.value
        )
        
        return session
    
    async def get_session_async(
        self,
        session_id: uuid.UUID
    ) -> Optional[Session]:
        """
        Get session by ID from Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            Session object or None
        """
        if self.use_redis_storage and self.store:
            return await self.store.get_session(session_id)
        else:
            return self.get_session(session_id)
    
    async def validate_session_async(
        self,
        session_id: uuid.UUID,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Validate session from Redis
        
        Args:
            session_id: Session ID
            ip_address: Client IP (optional)
        
        Returns:
            True if session is valid
        """
        session = await self.get_session_async(session_id)
        
        if not session:
            return False
        
        # Update activity
        session.update_activity()
        
        # Update in Redis
        if self.use_redis_storage and self.store:
            await self.store.update_session(session)
        
        return True
    
    async def update_session_activity_async(
        self,
        session_id: uuid.UUID,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Update session last activity in Redis
        
        Args:
            session_id: Session ID
            endpoint: Optional endpoint being accessed
        
        Returns:
            True if updated
        """
        session = await self.get_session_async(session_id)
        
        if not session:
            return False
        
        session.update_activity(endpoint)
        
        # Update in Redis
        if self.use_redis_storage and self.store:
            await self.store.update_session(session)
        
        return True
    
    async def terminate_session_async(
        self,
        session_id: uuid.UUID
    ) -> bool:
        """
        Terminate session in Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            True if terminated
        """
        if self.use_redis_storage and self.store:
            session = await self.store.get_session(session_id)
            if session:
                session.status = SessionStatus.TERMINATED
                session.terminated_at = datetime.utcnow()
                await self.store.update_session(session)
                # Delete from Redis after marking as terminated
                return await self.store.delete_session(session_id)
            return False
        else:
            return self.terminate_session(session_id)
    
    async def terminate_user_sessions_async(
        self,
        user_id: uuid.UUID,
        except_session_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Terminate all sessions for a user in Redis
        
        Args:
            user_id: User ID
            except_session_id: Optional session to keep
        
        Returns:
            Number of sessions terminated
        """
        if self.use_redis_storage and self.store:
            return await self.store.delete_user_sessions(user_id, except_session_id)
        else:
            return self.terminate_user_sessions(user_id, except_session_id)
    
    async def get_user_sessions_async(
        self,
        user_id: uuid.UUID
    ) -> List[Session]:
        """
        Get all active sessions for user from Redis
        
        Args:
            user_id: User ID
        
        Returns:
            List of Session objects
        """
        if self.use_redis_storage and self.store:
            return await self.store.get_user_sessions(user_id, active_only=True)
        else:
            return self.get_user_sessions(user_id)
    
    async def _enforce_session_limit_async(self, user_id: uuid.UUID) -> None:
        """
        Enforce maximum sessions per user in Redis
        
        Args:
            user_id: User ID
        """
        sessions = await self.get_user_sessions_async(user_id)
        
        if len(sessions) > self.max_sessions_per_user:
            # Terminate oldest sessions
            sessions.sort(key=lambda s: s.created_at)
            excess = len(sessions) - self.max_sessions_per_user
            
            for i in range(excess):
                await self.terminate_session_async(sessions[i].session_id)
            
            logger.info(
                "session_limit_enforced",
                user_id=str(user_id),
                terminated_count=excess
            )
    
    # Trusted Device Management with Redis
    
    async def trust_device_async(
        self,
        user_id: uuid.UUID,
        device_fingerprint: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        duration_days: Optional[int] = None
    ) -> TrustedDevice:
        """
        Mark device as trusted in Redis
        
        Args:
            user_id: User ID
            device_fingerprint: Device fingerprint
            device_name: Human-readable device name
            device_type: Device type
            duration_days: Trust duration
        
        Returns:
            TrustedDevice object
        """
        device_id = self._generate_device_id(device_fingerprint, "")
        
        # Check if already trusted in Redis
        if self.use_redis_storage and self.store:
            existing = await self.store.get_trusted_device(device_id)
            if existing:
                existing.last_seen_at = datetime.utcnow()
                await self.store.save_trusted_device(existing)
                return existing
        
        # Create trusted device
        trusted_until = None
        if duration_days:
            trusted_until = datetime.utcnow() + timedelta(days=duration_days)
        elif self.trust_device_duration:
            trusted_until = datetime.utcnow() + self.trust_device_duration
        
        trusted_device = TrustedDevice(
            device_id=device_id,
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            device_type=device_type,
            trusted_until=trusted_until
        )
        
        # Save to Redis
        if self.use_redis_storage and self.store:
            await self.store.save_trusted_device(
                trusted_device,
                ttl_days=duration_days or 30
            )
        else:
            # Fall back to in-memory
            self._trusted_devices[device_id] = trusted_device
        
        # Log security event
        await self._log_security_event_async(
            user_id=user_id,
            event_type="device_trusted",
            severity="low",
            description=f"Device {device_name or device_id} marked as trusted",
            device_id=device_id
        )
        
        logger.info(
            "device_trusted",
            device_id=device_id,
            user_id=str(user_id)
        )
        
        return trusted_device
    
    async def revoke_device_trust_async(self, device_id: str) -> bool:
        """
        Revoke trust for a device in Redis
        
        Args:
            device_id: Device ID
        
        Returns:
            True if revoked
        """
        if self.use_redis_storage and self.store:
            device = await self.store.get_trusted_device(device_id)
            if device:
                device.revoked = True
                device.revoked_at = datetime.utcnow()
                device.trust_level = DeviceTrustLevel.BLOCKED
                await self.store.save_trusted_device(device)
                
                # Log security event
                await self._log_security_event_async(
                    user_id=device.user_id,
                    event_type="device_trust_revoked",
                    severity="medium",
                    description=f"Trust revoked for device {device_id}",
                    device_id=device_id
                )
                
                return True
            return False
        else:
            return self.revoke_device_trust(device_id)
    
    async def get_trusted_devices_async(
        self,
        user_id: uuid.UUID
    ) -> List[TrustedDevice]:
        """
        Get all trusted devices for user from Redis
        
        Args:
            user_id: User ID
        
        Returns:
            List of TrustedDevice objects
        """
        if self.use_redis_storage and self.store:
            return await self.store.get_user_trusted_devices(user_id)
        else:
            return self.get_trusted_devices(user_id)
    
    # Security Monitoring with Redis
    
    async def _log_security_event_async(
        self,
        user_id: uuid.UUID,
        event_type: str,
        severity: str,
        description: str,
        **kwargs
    ) -> SecurityEvent:
        """
        Log security event to Redis
        
        Args:
            user_id: User ID
            event_type: Event type
            severity: Severity level
            description: Event description
            **kwargs: Additional event data
        
        Returns:
            SecurityEvent object
        """
        event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            **kwargs
        )
        
        # Log to Redis
        if self.use_redis_storage and self.store:
            await self.store.log_security_event(event)
        else:
            # Fall back to in-memory
            self._security_events.append(event)
        
        return event
    
    async def get_security_events_async(
        self,
        user_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """
        Get security events from Redis
        
        Args:
            user_id: Optional user ID filter
            severity: Optional severity filter
            limit: Maximum number of events
        
        Returns:
            List of SecurityEvent objects
        """
        if self.use_redis_storage and self.store and user_id:
            return await self.store.get_user_security_events(
                user_id=user_id,
                limit=limit,
                severity=severity
            )
        else:
            return self.get_security_events(user_id, severity, limit)
    
    # Cleanup and Maintenance
    
    async def cleanup_expired_sessions_async(self) -> dict:
        """
        Clean up expired sessions in Redis
        
        Returns:
            Cleanup statistics
        """
        if self.use_redis_storage and self.store:
            sessions_checked = await self.store.cleanup_expired_sessions()
            return {
                "sessions_checked": sessions_checked,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            expired = self.cleanup_expired_sessions()
            return {
                "expired_sessions": expired,
                "timestamp": datetime.utcnow().isoformat()
            }


# Singleton instance
_redis_session_manager: Optional[RedisSessionManager] = None


def get_redis_session_manager(
    redis_client: Optional[RedisClient] = None,
    **kwargs
) -> RedisSessionManager:
    """
    Get Redis session manager singleton
    
    Args:
        redis_client: Optional RedisClient instance
        **kwargs: Additional manager arguments
    
    Returns:
        RedisSessionManager instance
    """
    global _redis_session_manager
    if _redis_session_manager is None:
        _redis_session_manager = RedisSessionManager(
            redis_client=redis_client,
            **kwargs
        )
    return _redis_session_manager
