"""
User Service Data Models
Enhanced with RBAC and advanced MFA support
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, validator
import uuid


class MFAMethod(str, Enum):
    """Multi-factor authentication methods"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODE = "backup_code"


class NotificationPreference(str, Enum):
    """Notification delivery preferences"""
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


class User(BaseModel):
    """User model with RBAC integration"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr
    password_hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    
    # MFA settings
    mfa_enabled: bool = False
    mfa_method: Optional[MFAMethod] = None
    mfa_secret: Optional[str] = None
    backup_codes_generated: bool = False
    
    # RBAC - Role assignments
    roles: List[str] = Field(default_factory=lambda: ["free_user"])
    
    # Account status
    email_verified: bool = False
    is_active: bool = True
    is_premium: bool = False
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    failed_login_attempts: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    last_password_change: Optional[datetime] = None
    
    # Security
    requires_password_change: bool = False
    trusted_devices: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
    
    def is_locked_out(self) -> bool:
        """Check if account is locked"""
        if not self.is_locked:
            return False
        if self.locked_until and datetime.utcnow() > self.locked_until:
            return False
        return True


class UserProfile(BaseModel):
    """User profile and preferences"""
    user_id: uuid.UUID
    
    # Trading preferences
    default_watchlist_id: Optional[uuid.UUID] = None
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    trading_experience: str = "intermediate"  # beginner, intermediate, advanced
    
    # Notification preferences
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "price_alerts": True,
        "flow_alerts": True,
        "position_alerts": True,
        "news_alerts": False,
        "ai_insights": True,
        "security_alerts": True,
    })
    
    notification_channels: List[NotificationPreference] = [NotificationPreference.PUSH]
    
    # Display preferences
    theme: str = "dark"  # dark, light, auto
    chart_type: str = "candlestick"
    language: str = "en"
    timezone: str = "America/New_York"
    
    # Privacy settings
    anonymous_mode: bool = False
    share_track_record: bool = False
    data_retention_days: int = 365
    
    # Session preferences
    session_timeout_minutes: int = 30
    require_mfa_on_sensitive_ops: bool = True
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserRegistration(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    accepted_tos: bool
    referral_code: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        # Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError('Password must contain special character')
        return v
    
    @validator('accepted_tos')
    def tos_must_be_accepted(cls, v):
        if not v:
            raise ValueError('Terms of service must be accepted')
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    mfa_code: Optional[str] = None
    trusted_device_token: Optional[str] = None
    remember_device: bool = False


class TokenPair(BaseModel):
    """JWT token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    requires_mfa: bool = False
    mfa_challenge_id: Optional[str] = None


class TokenPayload(BaseModel):
    """JWT token payload structure"""
    sub: str  # user_id
    email: str
    roles: List[str]
    permissions: List[str]
    exp: datetime
    iat: datetime
    type: str  # access or refresh
    is_premium: bool = False


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v


class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v


class MFASetupResponse(BaseModel):
    """MFA setup response"""
    secret: str
    qr_code_uri: str
    backup_codes: Optional[List[str]] = None


class MFAVerifyRequest(BaseModel):
    """MFA verification request"""
    secret: str
    code: str
    generate_backup_codes: bool = True


class BrokerageConnectionRequest(BaseModel):
    """Brokerage connection request"""
    broker_name: str
    account_id: str
    credentials: Dict[str, str]
    mfa_code: Optional[str] = None


class BrokerageConnectionResponse(BaseModel):
    """Brokerage connection response"""
    connection_id: uuid.UUID
    broker_name: str
    account_id: str
    mfa_required: bool
    mfa_verified: bool
    status: str
    created_at: datetime


class SessionInfo(BaseModel):
    """User session information"""
    session_id: uuid.UUID
    user_id: uuid.UUID
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_trusted_device: bool = False


class AuditLog(BaseModel):
    """Security audit log entry"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    action: str
    resource: str
    result: str  # success, failure, error
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }
