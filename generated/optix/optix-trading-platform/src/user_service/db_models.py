"""
SQLAlchemy ORM Models for User Service
Async SQLAlchemy 2.0 implementation with proper type hints
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Boolean, DateTime, Integer, Text, Enum as SQLEnum,
    ARRAY, JSON, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid
import enum

from .database import Base


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(str, enum.Enum):
    """User role types"""
    ADMIN = "admin"
    PREMIUM = "premium"
    USER = "user"
    TRIAL = "trial"


class MFAType(str, enum.Enum):
    """MFA method types"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    HARDWARE = "hardware"


class EventSeverity(str, enum.Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserModel(Base):
    """
    User account model with enhanced security features
    Maps to user_service.users table
    """
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_users_email', 'email', postgresql_where='deleted_at IS NULL'),
        Index('idx_users_status', 'status', postgresql_where='deleted_at IS NULL'),
        Index('idx_users_role', 'role'),
        Index('idx_users_created_at', 'created_at'),
        {'schema': 'user_service'}
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # Status and Role
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, name='user_status', schema='user_service'),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default='active'
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name='user_role', schema='user_service'),
        nullable=False,
        default=UserRole.USER,
        server_default='user'
    )
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # MFA Settings
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    mfa_type: Mapped[Optional[MFAType]] = mapped_column(
        SQLEnum(MFAType, name='mfa_type', schema='user_service'),
        nullable=True
    )
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    sessions: Mapped[List["SessionModel"]] = relationship(
        "SessionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    security_events: Mapped[List["SecurityEventModel"]] = relationship(
        "SecurityEventModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    trusted_devices: Mapped[List["TrustedDeviceModel"]] = relationship(
        "TrustedDeviceModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE and self.deleted_at is None
    
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN


class SessionModel(Base):
    """
    Session history model - stores historical session data
    Active sessions are primarily in Redis, this is for audit/history
    Maps to user_service.sessions_history table
    """
    __tablename__ = "sessions_history"
    __table_args__ = (
        Index('idx_sessions_user_id', 'user_id'),
        Index('idx_sessions_device_id', 'device_id'),
        Index('idx_sessions_created_at', 'created_at'),
        UniqueConstraint('session_id', name='unique_session_id'),
        {'schema': 'user_service'}
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Session identification
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Device information
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    terminated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Security
    mfa_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    is_trusted_device: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<Session(id={self.session_id}, user_id={self.user_id})>"
    
    def is_active(self) -> bool:
        """Check if session is still active"""
        now = datetime.utcnow()
        return (
            self.terminated_at is None and
            self.expires_at > now
        )


class SecurityEventModel(Base):
    """
    Security event audit log
    Maps to user_service.security_events table
    """
    __tablename__ = "security_events"
    __table_args__ = (
        Index('idx_security_events_user_id', 'user_id'),
        Index('idx_security_events_timestamp', 'timestamp'),
        Index('idx_security_events_severity', 'severity'),
        Index('idx_security_events_event_type', 'event_type'),
        {'schema': 'user_service'}
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # User reference
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[EventSeverity] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Additional data
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Response
    action_taken: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="security_events")
    
    def __repr__(self) -> str:
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, severity={self.severity})>"


class TrustedDeviceModel(Base):
    """
    Trusted device model for MFA bypass
    Maps to user_service.trusted_devices table
    """
    __tablename__ = "trusted_devices"
    __table_args__ = (
        Index('idx_trusted_devices_user_id', 'user_id'),
        Index('idx_trusted_devices_device_id', 'device_id'),
        Index('idx_trusted_devices_trust_token', 'trust_token'),
        UniqueConstraint('device_id', 'user_id', name='unique_device_per_user'),
        {'schema': 'user_service'}
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Device and user identification
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Device information
    device_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Trust information
    trust_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    trusted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    trusted_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Usage tracking
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    last_ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    
    # Status
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="trusted_devices")
    
    def __repr__(self) -> str:
        return f"<TrustedDevice(id={self.id}, device_id={self.device_id}, user_id={self.user_id})>"
    
    def is_valid(self) -> bool:
        """Check if trust is still valid"""
        if self.revoked:
            return False
        if self.trusted_until:
            return datetime.utcnow() < self.trusted_until
        return True


class RefreshTokenFamilyModel(Base):
    """
    Refresh token family for token rotation detection
    Maps to user_service.refresh_token_families table
    """
    __tablename__ = "refresh_token_families"
    __table_args__ = (
        Index('idx_token_families_user_id', 'user_id'),
        Index('idx_token_families_family_id', 'family_id'),
        UniqueConstraint('family_id', name='unique_family_id'),
        {'schema': 'user_service'}
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Family identification
    family_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Device context
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Security
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    def __repr__(self) -> str:
        return f"<RefreshTokenFamily(id={self.family_id}, user_id={self.user_id})>"
    
    def is_valid(self) -> bool:
        """Check if token family is still valid"""
        return not self.revoked
