"""
Redis-backed Session Storage
Persistent session management with Redis for scalability
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import structlog
from pydantic import BaseModel
from .session_manager import Session, TrustedDevice, SecurityEvent, SessionStatus
from .redis_client import RedisClient, get_redis_client

logger = structlog.get_logger(__name__)


class RedisSessionStore:
    """
    Redis-backed session store for distributed session management
    Supports session persistence, device tracking, and security monitoring
    """
    
    # Redis key prefixes
    KEY_PREFIX_SESSION = "session:"
    KEY_PREFIX_USER_SESSIONS = "user:sessions:"
    KEY_PREFIX_DEVICE_SESSIONS = "device:sessions:"
    KEY_PREFIX_TRUSTED_DEVICE = "trusted:device:"
    KEY_PREFIX_USER_DEVICES = "user:devices:"
    KEY_PREFIX_SECURITY_EVENT = "security:event:"
    KEY_PREFIX_USER_SECURITY = "user:security:"
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Initialize session store
        
        Args:
            redis_client: RedisClient instance (uses singleton if not provided)
        """
        self.redis = redis_client or get_redis_client()
    
    # Session Operations
    
    async def create_session(
        self,
        session: Session,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store session in Redis
        
        Args:
            session: Session object
            ttl_seconds: Optional TTL override (uses session expiration by default)
        
        Returns:
            True if successful
        """
        try:
            session_id = str(session.session_id)
            user_id = str(session.user_id)
            
            # Calculate TTL
            if ttl_seconds is None:
                delta = session.expires_at - datetime.utcnow()
                ttl_seconds = int(delta.total_seconds())
            
            # Store session data
            session_key = f"{self.KEY_PREFIX_SESSION}{session_id}"
            session_data = session.model_dump(mode='json')
            
            await self.redis.set(
                session_key,
                session_data,
                ttl=ttl_seconds,
                serialize=True
            )
            
            # Track user's sessions
            user_sessions_key = f"{self.KEY_PREFIX_USER_SESSIONS}{user_id}"
            await self.redis.sadd(user_sessions_key, session_id)
            await self.redis.expire(user_sessions_key, ttl_seconds)
            
            # Track device's sessions
            device_sessions_key = f"{self.KEY_PREFIX_DEVICE_SESSIONS}{session.device_id}"
            await self.redis.sadd(device_sessions_key, session_id)
            await self.redis.expire(device_sessions_key, ttl_seconds)
            
            logger.info(
                "session_created",
                session_id=session_id,
                user_id=user_id,
                device_id=session.device_id,
                ttl=ttl_seconds
            )
            
            return True
        except Exception as e:
            logger.error(
                "session_create_error",
                session_id=str(session.session_id),
                error=str(e)
            )
            raise
    
    async def get_session(self, session_id: uuid.UUID) -> Optional[Session]:
        """
        Retrieve session from Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            Session object or None if not found
        """
        try:
            session_key = f"{self.KEY_PREFIX_SESSION}{session_id}"
            session_data = await self.redis.get(session_key, deserialize=True)
            
            if not session_data:
                return None
            
            # Convert back to Session object
            session = Session(**session_data)
            
            # Check if expired
            if session.is_expired():
                await self.delete_session(session_id)
                return None
            
            return session
        except Exception as e:
            logger.error(
                "session_get_error",
                session_id=str(session_id),
                error=str(e)
            )
            return None
    
    async def update_session(
        self,
        session: Session,
        extend_ttl: bool = False
    ) -> bool:
        """
        Update session in Redis
        
        Args:
            session: Updated session object
            extend_ttl: Whether to extend TTL based on new expiration
        
        Returns:
            True if successful
        """
        try:
            session_key = f"{self.KEY_PREFIX_SESSION}{session.session_id}"
            session_data = session.model_dump(mode='json')
            
            if extend_ttl:
                delta = session.expires_at - datetime.utcnow()
                ttl_seconds = int(delta.total_seconds())
                await self.redis.set(
                    session_key,
                    session_data,
                    ttl=ttl_seconds,
                    serialize=True
                )
            else:
                # Update without changing TTL
                await self.redis.set(
                    session_key,
                    session_data,
                    serialize=True
                )
            
            return True
        except Exception as e:
            logger.error(
                "session_update_error",
                session_id=str(session.session_id),
                error=str(e)
            )
            raise
    
    async def delete_session(self, session_id: uuid.UUID) -> bool:
        """
        Delete session from Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted
        """
        try:
            # Get session first to clean up related keys
            session = await self.get_session(session_id)
            
            session_key = f"{self.KEY_PREFIX_SESSION}{session_id}"
            deleted = await self.redis.delete(session_key)
            
            if session:
                # Remove from user sessions
                user_sessions_key = f"{self.KEY_PREFIX_USER_SESSIONS}{session.user_id}"
                await self.redis.srem(user_sessions_key, str(session_id))
                
                # Remove from device sessions
                device_sessions_key = f"{self.KEY_PREFIX_DEVICE_SESSIONS}{session.device_id}"
                await self.redis.srem(device_sessions_key, str(session_id))
            
            if deleted:
                logger.info("session_deleted", session_id=str(session_id))
            
            return bool(deleted)
        except Exception as e:
            logger.error(
                "session_delete_error",
                session_id=str(session_id),
                error=str(e)
            )
            raise
    
    async def get_user_sessions(
        self,
        user_id: uuid.UUID,
        active_only: bool = True
    ) -> List[Session]:
        """
        Get all sessions for a user
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
        
        Returns:
            List of Session objects
        """
        try:
            user_sessions_key = f"{self.KEY_PREFIX_USER_SESSIONS}{user_id}"
            session_ids = await self.redis.smembers(user_sessions_key)
            
            sessions = []
            for session_id_str in session_ids:
                try:
                    session_id = uuid.UUID(session_id_str)
                    session = await self.get_session(session_id)
                    
                    if session:
                        if not active_only or session.status == SessionStatus.ACTIVE:
                            sessions.append(session)
                except Exception as e:
                    logger.warning(
                        "invalid_session_in_user_list",
                        session_id=session_id_str,
                        error=str(e)
                    )
            
            return sessions
        except Exception as e:
            logger.error(
                "get_user_sessions_error",
                user_id=str(user_id),
                error=str(e)
            )
            return []
    
    async def delete_user_sessions(
        self,
        user_id: uuid.UUID,
        except_session_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Delete all sessions for a user
        
        Args:
            user_id: User ID
            except_session_id: Optional session to keep
        
        Returns:
            Number of sessions deleted
        """
        try:
            sessions = await self.get_user_sessions(user_id, active_only=False)
            count = 0
            
            for session in sessions:
                if except_session_id and session.session_id == except_session_id:
                    continue
                
                if await self.delete_session(session.session_id):
                    count += 1
            
            logger.info(
                "user_sessions_deleted",
                user_id=str(user_id),
                count=count
            )
            
            return count
        except Exception as e:
            logger.error(
                "delete_user_sessions_error",
                user_id=str(user_id),
                error=str(e)
            )
            raise
    
    async def get_device_sessions(self, device_id: str) -> List[Session]:
        """
        Get all sessions for a device
        
        Args:
            device_id: Device ID
        
        Returns:
            List of Session objects
        """
        try:
            device_sessions_key = f"{self.KEY_PREFIX_DEVICE_SESSIONS}{device_id}"
            session_ids = await self.redis.smembers(device_sessions_key)
            
            sessions = []
            for session_id_str in session_ids:
                try:
                    session_id = uuid.UUID(session_id_str)
                    session = await self.get_session(session_id)
                    if session:
                        sessions.append(session)
                except Exception:
                    pass
            
            return sessions
        except Exception as e:
            logger.error(
                "get_device_sessions_error",
                device_id=device_id,
                error=str(e)
            )
            return []
    
    # Trusted Device Operations
    
    async def save_trusted_device(
        self,
        device: TrustedDevice,
        ttl_days: Optional[int] = None
    ) -> bool:
        """
        Save trusted device to Redis
        
        Args:
            device: TrustedDevice object
            ttl_days: Optional TTL in days
        
        Returns:
            True if successful
        """
        try:
            device_key = f"{self.KEY_PREFIX_TRUSTED_DEVICE}{device.device_id}"
            device_data = device.model_dump(mode='json')
            
            # Calculate TTL
            ttl_seconds = None
            if device.trusted_until:
                delta = device.trusted_until - datetime.utcnow()
                ttl_seconds = int(delta.total_seconds())
            elif ttl_days:
                ttl_seconds = ttl_days * 86400
            
            await self.redis.set(
                device_key,
                device_data,
                ttl=ttl_seconds,
                serialize=True
            )
            
            # Track user's trusted devices
            user_devices_key = f"{self.KEY_PREFIX_USER_DEVICES}{device.user_id}"
            await self.redis.sadd(user_devices_key, device.device_id)
            
            if ttl_seconds:
                await self.redis.expire(user_devices_key, ttl_seconds)
            
            logger.info(
                "trusted_device_saved",
                device_id=device.device_id,
                user_id=str(device.user_id)
            )
            
            return True
        except Exception as e:
            logger.error(
                "save_trusted_device_error",
                device_id=device.device_id,
                error=str(e)
            )
            raise
    
    async def get_trusted_device(self, device_id: str) -> Optional[TrustedDevice]:
        """
        Get trusted device from Redis
        
        Args:
            device_id: Device ID
        
        Returns:
            TrustedDevice object or None
        """
        try:
            device_key = f"{self.KEY_PREFIX_TRUSTED_DEVICE}{device_id}"
            device_data = await self.redis.get(device_key, deserialize=True)
            
            if not device_data:
                return None
            
            device = TrustedDevice(**device_data)
            
            # Check if still valid
            if not device.is_valid():
                await self.delete_trusted_device(device_id)
                return None
            
            return device
        except Exception as e:
            logger.error(
                "get_trusted_device_error",
                device_id=device_id,
                error=str(e)
            )
            return None
    
    async def get_user_trusted_devices(
        self,
        user_id: uuid.UUID
    ) -> List[TrustedDevice]:
        """
        Get all trusted devices for a user
        
        Args:
            user_id: User ID
        
        Returns:
            List of TrustedDevice objects
        """
        try:
            user_devices_key = f"{self.KEY_PREFIX_USER_DEVICES}{user_id}"
            device_ids = await self.redis.smembers(user_devices_key)
            
            devices = []
            for device_id in device_ids:
                device = await self.get_trusted_device(device_id)
                if device and device.is_valid():
                    devices.append(device)
            
            return devices
        except Exception as e:
            logger.error(
                "get_user_devices_error",
                user_id=str(user_id),
                error=str(e)
            )
            return []
    
    async def delete_trusted_device(self, device_id: str) -> bool:
        """
        Delete trusted device
        
        Args:
            device_id: Device ID
        
        Returns:
            True if deleted
        """
        try:
            # Get device first to clean up user's device list
            device = await self.get_trusted_device(device_id)
            
            device_key = f"{self.KEY_PREFIX_TRUSTED_DEVICE}{device_id}"
            deleted = await self.redis.delete(device_key)
            
            if device:
                user_devices_key = f"{self.KEY_PREFIX_USER_DEVICES}{device.user_id}"
                await self.redis.srem(user_devices_key, device_id)
            
            if deleted:
                logger.info("trusted_device_deleted", device_id=device_id)
            
            return bool(deleted)
        except Exception as e:
            logger.error(
                "delete_trusted_device_error",
                device_id=device_id,
                error=str(e)
            )
            raise
    
    # Security Event Operations
    
    async def log_security_event(
        self,
        event: SecurityEvent,
        ttl_days: int = 90
    ) -> bool:
        """
        Log security event to Redis
        
        Args:
            event: SecurityEvent object
            ttl_days: Days to retain event
        
        Returns:
            True if successful
        """
        try:
            event_key = f"{self.KEY_PREFIX_SECURITY_EVENT}{event.event_id}"
            event_data = event.model_dump(mode='json')
            
            ttl_seconds = ttl_days * 86400
            await self.redis.set(
                event_key,
                event_data,
                ttl=ttl_seconds,
                serialize=True
            )
            
            # Add to user's security events (sorted set by timestamp)
            user_security_key = f"{self.KEY_PREFIX_USER_SECURITY}{event.user_id}"
            score = event.timestamp.timestamp()
            await self.redis.zadd(
                user_security_key,
                {str(event.event_id): score}
            )
            
            # Keep only recent events in sorted set
            max_events = 1000
            await self.redis.zremrangebyrank(user_security_key, 0, -max_events - 1)
            
            logger.debug(
                "security_event_logged",
                event_type=event.event_type,
                severity=event.severity,
                user_id=str(event.user_id)
            )
            
            return True
        except Exception as e:
            logger.error(
                "log_security_event_error",
                event_id=str(event.event_id),
                error=str(e)
            )
            return False
    
    async def get_user_security_events(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        severity: Optional[str] = None
    ) -> List[SecurityEvent]:
        """
        Get security events for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of events
            severity: Optional severity filter
        
        Returns:
            List of SecurityEvent objects
        """
        try:
            user_security_key = f"{self.KEY_PREFIX_USER_SECURITY}{user_id}"
            
            # Get recent event IDs (newest first)
            event_ids = await self.redis.zrange(
                user_security_key,
                -limit,
                -1,
                withscores=False
            )
            
            events = []
            for event_id_str in reversed(event_ids):  # Reverse for newest first
                event_key = f"{self.KEY_PREFIX_SECURITY_EVENT}{event_id_str}"
                event_data = await self.redis.get(event_key, deserialize=True)
                
                if event_data:
                    event = SecurityEvent(**event_data)
                    
                    if severity and event.severity != severity:
                        continue
                    
                    events.append(event)
            
            return events
        except Exception as e:
            logger.error(
                "get_user_security_events_error",
                user_id=str(user_id),
                error=str(e)
            )
            return []
    
    # Utility and Monitoring
    
    async def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions (approximate)
        
        Returns:
            Number of active sessions
        """
        try:
            count = 0
            cursor = 0
            pattern = f"{self.KEY_PREFIX_SESSION}*"
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                count += len(keys)
                if cursor == 0:
                    break
            
            return count
        except Exception as e:
            logger.error("get_sessions_count_error", error=str(e))
            return 0
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (Redis handles this automatically)
        This provides statistics for monitoring
        
        Returns:
            Number of sessions checked
        """
        # Redis automatically removes expired keys
        # This is for monitoring purposes
        try:
            return await self.get_active_sessions_count()
        except Exception as e:
            logger.error("cleanup_error", error=str(e))
            return 0


# Singleton instance
_session_store: Optional[RedisSessionStore] = None


def get_session_store(
    redis_client: Optional[RedisClient] = None
) -> RedisSessionStore:
    """
    Get session store singleton
    
    Args:
        redis_client: Optional RedisClient instance
    
    Returns:
        RedisSessionStore instance
    """
    global _session_store
    if _session_store is None:
        _session_store = RedisSessionStore(redis_client=redis_client)
    return _session_store
