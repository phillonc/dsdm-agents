"""
Repository pattern implementations for User Service
Provides clean abstraction over database operations with async SQLAlchemy 2.0
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import uuid
import structlog

from .db_models import (
    UserModel,
    SessionModel,
    SecurityEventModel,
    TrustedDeviceModel,
    RefreshTokenFamilyModel,
    UserStatus,
    UserRole,
    EventSeverity
)

logger = structlog.get_logger()


class UserRepository:
    """Repository for User operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        email: str,
        password_hash: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.USER
    ) -> UserModel:
        """Create a new user"""
        try:
            user = UserModel(
                email=email.lower(),
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role,
                status=UserStatus.ACTIVE
            )
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)
            
            logger.info("User created", user_id=str(user.id), email=email)
            return user
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error("User creation failed - duplicate email", email=email)
            raise ValueError(f"User with email {email} already exists")
    
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserModel]:
        """Get user by ID"""
        stmt = select(UserModel).where(
            and_(
                UserModel.id == user_id,
                UserModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email"""
        stmt = select(UserModel).where(
            and_(
                UserModel.email == email.lower(),
                UserModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[UserModel]:
        """Update user fields"""
        # Filter out None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            return await self.get_by_id(user_id)
        
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**update_data)
            .returning(UserModel)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        user = result.scalar_one_or_none()
        if user:
            logger.info("User updated", user_id=str(user_id), fields=list(update_data.keys()))
        return user
    
    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp"""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_password(self, user_id: uuid.UUID, password_hash: str) -> bool:
        """Update user password"""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(password_hash=password_hash)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        success = result.rowcount > 0
        if success:
            logger.info("Password updated", user_id=str(user_id))
        return success
    
    async def verify_email(self, user_id: uuid.UUID) -> bool:
        """Mark user email as verified"""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                email_verified=True,
                email_verified_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def soft_delete(self, user_id: uuid.UUID) -> bool:
        """Soft delete a user"""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                deleted_at=datetime.utcnow(),
                status=UserStatus.DELETED
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        if result.rowcount > 0:
            logger.info("User soft deleted", user_id=str(user_id))
            return True
        return False
    
    async def list_users(
        self,
        status: Optional[UserStatus] = None,
        role: Optional[UserRole] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserModel]:
        """List users with optional filters"""
        stmt = select(UserModel).where(UserModel.deleted_at.is_(None))
        
        if status:
            stmt = stmt.where(UserModel.status == status)
        if role:
            stmt = stmt.where(UserModel.role == role)
        
        stmt = stmt.limit(limit).offset(offset).order_by(UserModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_users(
        self,
        status: Optional[UserStatus] = None,
        role: Optional[UserRole] = None
    ) -> int:
        """Count users with optional filters"""
        stmt = select(func.count(UserModel.id)).where(UserModel.deleted_at.is_(None))
        
        if status:
            stmt = stmt.where(UserModel.status == status)
        if role:
            stmt = stmt.where(UserModel.role == role)
        
        result = await self.session.execute(stmt)
        return result.scalar_one()


class SessionRepository:
    """Repository for Session operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        device_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        mfa_verified: bool = False,
        is_trusted_device: bool = False,
        device_fingerprint: Optional[str] = None,
        device_name: Optional[str] = None
    ) -> SessionModel:
        """Create a new session record"""
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=30)
        
        session_record = SessionModel(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            mfa_verified=mfa_verified,
            is_trusted_device=is_trusted_device,
            last_activity_at=datetime.utcnow()
        )
        
        self.session.add(session_record)
        await self.session.flush()
        await self.session.refresh(session_record)
        
        logger.info("Session created", session_id=str(session_id), user_id=str(user_id))
        return session_record
    
    async def get_by_session_id(self, session_id: uuid.UUID) -> Optional[SessionModel]:
        """Get session by session ID"""
        stmt = select(SessionModel).where(SessionModel.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_activity(self, session_id: uuid.UUID) -> bool:
        """Update session last activity timestamp"""
        stmt = (
            update(SessionModel)
            .where(SessionModel.session_id == session_id)
            .values(last_activity_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def terminate(self, session_id: uuid.UUID) -> bool:
        """Terminate a session"""
        stmt = (
            update(SessionModel)
            .where(SessionModel.session_id == session_id)
            .values(terminated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        if result.rowcount > 0:
            logger.info("Session terminated", session_id=str(session_id))
            return True
        return False
    
    async def get_user_sessions(
        self,
        user_id: uuid.UUID,
        active_only: bool = True
    ) -> List[SessionModel]:
        """Get all sessions for a user"""
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)
        
        if active_only:
            stmt = stmt.where(
                and_(
                    SessionModel.terminated_at.is_(None),
                    SessionModel.expires_at > datetime.utcnow()
                )
            )
        
        stmt = stmt.order_by(SessionModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def terminate_user_sessions(self, user_id: uuid.UUID) -> int:
        """Terminate all active sessions for a user"""
        stmt = (
            update(SessionModel)
            .where(
                and_(
                    SessionModel.user_id == user_id,
                    SessionModel.terminated_at.is_(None)
                )
            )
            .values(terminated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info("User sessions terminated", user_id=str(user_id), count=count)
        return count
    
    async def cleanup_expired(self, before_date: Optional[datetime] = None) -> int:
        """Delete expired session records"""
        if not before_date:
            before_date = datetime.utcnow() - timedelta(days=90)
        
        stmt = delete(SessionModel).where(
            or_(
                SessionModel.expires_at < datetime.utcnow(),
                SessionModel.terminated_at < before_date
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info("Expired sessions cleaned up", count=count)
        return count


class SecurityEventRepository:
    """Repository for Security Event operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: uuid.UUID,
        event_type: str,
        severity: EventSeverity,
        description: str,
        session_id: Optional[uuid.UUID] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        action_taken: Optional[str] = None
    ) -> SecurityEventModel:
        """Create a security event"""
        event = SecurityEventModel(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            description=description,
            session_id=session_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            action_taken=action_taken
        )
        
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        
        logger.info(
            "Security event created",
            event_id=str(event.id),
            user_id=str(user_id),
            event_type=event_type,
            severity=severity
        )
        return event
    
    async def get_by_id(self, event_id: uuid.UUID) -> Optional[SecurityEventModel]:
        """Get security event by ID"""
        stmt = select(SecurityEventModel).where(SecurityEventModel.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_events(
        self,
        user_id: uuid.UUID,
        event_type: Optional[str] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecurityEventModel]:
        """Get security events for a user"""
        stmt = select(SecurityEventModel).where(SecurityEventModel.user_id == user_id)
        
        if event_type:
            stmt = stmt.where(SecurityEventModel.event_type == event_type)
        if severity:
            stmt = stmt.where(SecurityEventModel.severity == severity)
        
        stmt = stmt.limit(limit).offset(offset).order_by(SecurityEventModel.timestamp.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_recent_events(
        self,
        hours: int = 24,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[SecurityEventModel]:
        """Get recent security events"""
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(SecurityEventModel).where(SecurityEventModel.timestamp >= since)
        
        if severity:
            stmt = stmt.where(SecurityEventModel.severity == severity)
        
        stmt = stmt.limit(limit).order_by(SecurityEventModel.timestamp.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def mark_resolved(self, event_id: uuid.UUID) -> bool:
        """Mark security event as resolved"""
        stmt = (
            update(SecurityEventModel)
            .where(SecurityEventModel.id == event_id)
            .values(resolved=True)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class TrustedDeviceRepository:
    """Repository for Trusted Device operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: uuid.UUID,
        device_id: str,
        device_fingerprint: str,
        trust_token: str,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        trusted_until: Optional[datetime] = None,
        ip_address: Optional[str] = None
    ) -> TrustedDeviceModel:
        """Create a trusted device"""
        device = TrustedDeviceModel(
            user_id=user_id,
            device_id=device_id,
            device_fingerprint=device_fingerprint,
            trust_token=trust_token,
            device_name=device_name,
            device_type=device_type,
            trusted_until=trusted_until,
            last_ip_address=ip_address,
            usage_count=0
        )
        
        self.session.add(device)
        await self.session.flush()
        await self.session.refresh(device)
        
        logger.info("Trusted device created", device_id=device_id, user_id=str(user_id))
        return device
    
    async def get_by_token(self, trust_token: str) -> Optional[TrustedDeviceModel]:
        """Get trusted device by token"""
        stmt = select(TrustedDeviceModel).where(
            and_(
                TrustedDeviceModel.trust_token == trust_token,
                TrustedDeviceModel.revoked == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_devices(self, user_id: uuid.UUID) -> List[TrustedDeviceModel]:
        """Get all trusted devices for a user"""
        stmt = select(TrustedDeviceModel).where(
            and_(
                TrustedDeviceModel.user_id == user_id,
                TrustedDeviceModel.revoked == False
            )
        ).order_by(TrustedDeviceModel.last_seen_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_usage(
        self,
        device_id: str,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None
    ) -> bool:
        """Update device usage statistics"""
        update_data = {
            "last_seen_at": datetime.utcnow(),
            "usage_count": TrustedDeviceModel.usage_count + 1
        }
        if ip_address:
            update_data["last_ip_address"] = ip_address
        
        stmt = (
            update(TrustedDeviceModel)
            .where(
                and_(
                    TrustedDeviceModel.device_id == device_id,
                    TrustedDeviceModel.user_id == user_id
                )
            )
            .values(**update_data)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def revoke(self, device_id: str, user_id: uuid.UUID) -> bool:
        """Revoke trust for a device"""
        stmt = (
            update(TrustedDeviceModel)
            .where(
                and_(
                    TrustedDeviceModel.device_id == device_id,
                    TrustedDeviceModel.user_id == user_id
                )
            )
            .values(
                revoked=True,
                revoked_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        if result.rowcount > 0:
            logger.info("Trusted device revoked", device_id=device_id, user_id=str(user_id))
            return True
        return False
    
    async def revoke_all(self, user_id: uuid.UUID) -> int:
        """Revoke all trusted devices for a user"""
        stmt = (
            update(TrustedDeviceModel)
            .where(TrustedDeviceModel.user_id == user_id)
            .values(
                revoked=True,
                revoked_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info("All trusted devices revoked", user_id=str(user_id), count=count)
        return count


class RefreshTokenFamilyRepository:
    """Repository for Refresh Token Family operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        family_id: str,
        user_id: uuid.UUID,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RefreshTokenFamilyModel:
        """Create a token family"""
        family = RefreshTokenFamilyModel(
            family_id=family_id,
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.session.add(family)
        await self.session.flush()
        await self.session.refresh(family)
        
        logger.info("Token family created", family_id=family_id, user_id=str(user_id))
        return family
    
    async def get_by_family_id(self, family_id: str) -> Optional[RefreshTokenFamilyModel]:
        """Get token family by ID"""
        stmt = select(RefreshTokenFamilyModel).where(
            RefreshTokenFamilyModel.family_id == family_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_last_used(self, family_id: str) -> bool:
        """Update token family last used timestamp"""
        stmt = (
            update(RefreshTokenFamilyModel)
            .where(RefreshTokenFamilyModel.family_id == family_id)
            .values(last_used_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def revoke(self, family_id: str, reason: str) -> bool:
        """Revoke a token family"""
        stmt = (
            update(RefreshTokenFamilyModel)
            .where(RefreshTokenFamilyModel.family_id == family_id)
            .values(
                revoked=True,
                revoked_at=datetime.utcnow(),
                revoke_reason=reason
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        if result.rowcount > 0:
            logger.info("Token family revoked", family_id=family_id, reason=reason)
            return True
        return False
    
    async def revoke_user_families(self, user_id: uuid.UUID, reason: str) -> int:
        """Revoke all token families for a user"""
        stmt = (
            update(RefreshTokenFamilyModel)
            .where(RefreshTokenFamilyModel.user_id == user_id)
            .values(
                revoked=True,
                revoked_at=datetime.utcnow(),
                revoke_reason=reason
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info("User token families revoked", user_id=str(user_id), count=count)
        return count
