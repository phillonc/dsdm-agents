"""
Enhanced User Service REST API
Comprehensive authentication endpoints with JWT, MFA, and RBAC
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import uuid
from datetime import datetime

from .models import (
    User, UserProfile, UserRegistration, UserLogin,
    TokenPair, PasswordReset, PasswordResetConfirm, PasswordChange,
    MFASetupResponse, MFAVerifyRequest, SessionInfo, AuditLog,
    MFAMethod
)
from .auth import AuthService
from .repository import UserRepository
from .jwt_service import JWTService, TokenType, get_jwt_service
from .mfa_manager import MFAManager, get_mfa_manager, MFAType
from .session_manager import SessionManager, get_session_manager
from .rbac import Permission, Role, get_rbac_service


router = APIRouter(prefix="/api/v1/users", tags=["user-service"])
security = HTTPBearer()


# Dependency injection
def get_auth_service() -> AuthService:
    """Get authentication service instance"""
    # In production, load from config/environment
    import os
    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    return AuthService(secret_key=secret_key)


def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    return UserRepository()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    session_manager: SessionManager = Depends(get_session_manager),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    Get current authenticated user from JWT token
    Also validates session
    """
    try:
        token = credentials.credentials
        
        # Verify JWT token
        payload = jwt_service.verify_token(token, expected_type=TokenType.ACCESS)
        user_id = uuid.UUID(payload["sub"])
        
        # Get user
        user = user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Check account lockout
        if user.is_locked_out():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked"
            )
        
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def require_permission(
    permission: Permission,
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Dependency to require specific permission"""
    auth_service.require_permission(user, permission)
    return user


# Authentication Endpoints

@router.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    registration: UserRegistration,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    session_manager: SessionManager = Depends(get_session_manager),
    rbac_service = Depends(get_rbac_service)
):
    """
    Register new user account
    
    - **email**: Valid email address
    - **password**: Minimum 8 characters with mixed case, number, and special character
    - **accepted_tos**: Must be true
    """
    # Check if user already exists
    existing_user = user_repo.get_user_by_email(registration.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    password_hash = auth_service.hash_password(registration.password)
    user = User(
        email=registration.email,
        password_hash=password_hash,
        first_name=registration.first_name,
        last_name=registration.last_name,
        phone=registration.phone
    )
    
    created_user = user_repo.create_user(user)
    
    # Assign default role
    rbac_service.assign_role(created_user.id, Role.FREE_USER)
    created_user.roles = [Role.FREE_USER.value]
    
    # Create default profile
    profile = UserProfile(user_id=created_user.id)
    user_repo.create_profile(profile)
    
    # Create session
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    device_fingerprint = jwt_service.create_device_fingerprint(user_agent, client_ip)
    
    session = session_manager.create_session(
        user_id=created_user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        device_fingerprint=device_fingerprint,
        mfa_verified=False
    )
    
    # Generate JWT tokens
    access_token, _ = jwt_service.create_access_token(
        user_id=created_user.id,
        email=created_user.email,
        roles=created_user.roles,
        permissions=[p.value for p in rbac_service.get_user_permissions(created_user.id)],
        is_premium=created_user.is_premium
    )
    
    refresh_token, _, _ = jwt_service.create_refresh_token(
        user_id=created_user.id,
        device_fingerprint=device_fingerprint,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # TODO: Send verification email
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_mfa=False
    )


@router.post("/auth/login", response_model=TokenPair)
async def login(
    credentials: UserLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    mfa_manager: MFAManager = Depends(get_mfa_manager),
    session_manager: SessionManager = Depends(get_session_manager),
    rbac_service = Depends(get_rbac_service)
):
    """
    Authenticate user and return JWT tokens
    
    - **email**: User email
    - **password**: User password
    - **mfa_code**: Optional MFA code if enabled
    - **trusted_device_token**: Optional token for trusted device
    """
    # Get user
    user = user_repo.get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check account lockout
    if auth_service.check_account_lockout(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {user.locked_until}"
        )
    
    # Verify password
    if not auth_service.verify_password(credentials.password, user.password_hash):
        auth_service.handle_failed_login(user)
        user_repo.update_user(user.id, {
            "failed_login_attempts": user.failed_login_attempts,
            "is_locked": user.is_locked,
            "locked_until": user.locked_until
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    device_fingerprint = jwt_service.create_device_fingerprint(user_agent, client_ip)
    
    # Check if device is trusted
    is_trusted_device = False
    if credentials.trusted_device_token:
        is_trusted_device = session_manager._get_trusted_device_by_token(
            credentials.trusted_device_token
        ) is not None
    
    # Handle MFA if enabled
    mfa_verified = False
    if user.mfa_enabled and not is_trusted_device:
        if not credentials.mfa_code:
            # Return challenge token
            challenge = mfa_manager.create_verification_challenge(
                user_id=user.id,
                mfa_type=user.mfa_method or MFAType.TOTP
            )
            
            challenge_token, _ = jwt_service.create_mfa_challenge_token(
                user_id=user.id,
                challenge_id=str(challenge.challenge_id),
                mfa_methods=[user.mfa_method.value] if user.mfa_method else []
            )
            
            return TokenPair(
                access_token=challenge_token,
                refresh_token="",
                requires_mfa=True,
                mfa_challenge_id=str(challenge.challenge_id)
            )
        
        # Verify MFA code
        if user.mfa_method == MFAMethod.TOTP:
            if not auth_service.verify_mfa_code(user.mfa_secret, credentials.mfa_code, user.mfa_method):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )
        
        mfa_verified = True
    
    # Successful login - reset failed attempts
    auth_service.handle_successful_login(user)
    user_repo.update_user(user.id, {
        "failed_login_attempts": 0,
        "is_locked": False,
        "locked_until": None,
        "last_login_at": datetime.utcnow()
    })
    
    # Create session
    trust_token = credentials.trusted_device_token if is_trusted_device else None
    session = session_manager.create_session(
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        device_fingerprint=device_fingerprint,
        trust_token=trust_token,
        mfa_verified=mfa_verified
    )
    
    # Generate JWT tokens
    access_token, _ = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=user.roles,
        permissions=[p.value for p in rbac_service.get_user_permissions(user.id)],
        additional_claims={"session_id": str(session.session_id)},
        is_premium=user.is_premium
    )
    
    refresh_token, _, _ = jwt_service.create_refresh_token(
        user_id=user.id,
        device_fingerprint=device_fingerprint,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Handle remember device
    trust_device_token = None
    if credentials.remember_device and mfa_verified:
        trusted_device = session_manager.trust_device(
            user_id=user.id,
            device_fingerprint=device_fingerprint,
            device_type="web"
        )
        trust_device_token = trusted_device.trust_token
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        requires_mfa=False
    )


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str,
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    user_repo: UserRepository = Depends(get_user_repository),
    rbac_service = Depends(get_rbac_service)
):
    """
    Refresh access token using refresh token
    Implements token rotation for enhanced security
    """
    try:
        # Rotate refresh token (invalidates old, creates new)
        new_refresh_token, _, _ = jwt_service.rotate_refresh_token(refresh_token)
        
        # Verify token and get user
        payload = jwt_service.verify_token(refresh_token, expected_type=TokenType.REFRESH)
        user_id = uuid.UUID(payload["sub"])
        
        user = user_repo.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Generate new access token
        new_access_token, _ = jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
            roles=user.roles,
            permissions=[p.value for p in rbac_service.get_user_permissions(user.id)],
            is_premium=user.is_premium
        )
        
        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Logout user and revoke tokens
    """
    token = credentials.credentials
    
    # Revoke access token
    payload = jwt_service.verify_token(token)
    jti = payload.get("jti")
    if jti:
        jwt_service.revoke_token(jti)
    
    # Terminate active sessions
    session_manager.terminate_user_sessions(current_user.id)
    
    return {"message": "Logged out successfully"}


@router.post("/auth/logout-all")
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Logout from all sessions and revoke all tokens
    """
    # Revoke all user tokens
    jwt_service.revoke_user_tokens(current_user.id)
    
    # Terminate all sessions
    count = session_manager.terminate_user_sessions(current_user.id)
    
    return {"message": f"Logged out from {count} sessions"}


# MFA Endpoints

@router.post("/auth/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    mfa_manager: MFAManager = Depends(get_mfa_manager)
):
    """
    Generate MFA secret for TOTP setup
    Returns QR code URI for authenticator apps
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA already enabled"
        )
    
    # Generate TOTP secret
    secret = mfa_manager.generate_totp_secret()
    
    # Generate QR code URI
    qr_code_uri = mfa_manager.get_totp_provisioning_uri(
        secret=secret,
        email=current_user.email
    )
    
    return MFASetupResponse(
        secret=secret,
        qr_code_uri=qr_code_uri
    )


@router.post("/auth/mfa/verify")
async def verify_and_enable_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    mfa_manager: MFAManager = Depends(get_mfa_manager),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Verify MFA code and enable MFA
    Optionally generates backup codes
    """
    # Verify MFA code
    if not mfa_manager.verify_totp_code(request.secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    
    # Generate backup codes if requested
    backup_codes = None
    if request.generate_backup_codes:
        backup_codes = mfa_manager.generate_backup_codes(current_user.id)
    
    # Enable MFA
    user_repo.update_user(current_user.id, {
        "mfa_enabled": True,
        "mfa_method": MFAMethod.TOTP,
        "mfa_secret": request.secret,
        "backup_codes_generated": request.generate_backup_codes
    })
    
    return {
        "message": "MFA enabled successfully",
        "backup_codes": backup_codes
    }


@router.post("/auth/mfa/disable")
async def disable_mfa(
    password: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Disable MFA (requires password confirmation)
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )
    
    # Verify password
    if not auth_service.verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Disable MFA
    user_repo.update_user(current_user.id, {
        "mfa_enabled": False,
        "mfa_method": None,
        "mfa_secret": None
    })
    
    return {"message": "MFA disabled successfully"}


# User Profile Endpoints

@router.get("/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user profile"""
    return current_user


@router.patch("/me", response_model=User)
async def update_current_user(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Update current user profile"""
    updates = {}
    if first_name is not None:
        updates["first_name"] = first_name
    if last_name is not None:
        updates["last_name"] = last_name
    if phone is not None:
        updates["phone"] = phone
    
    updated_user = user_repo.update_user(current_user.id, updates)
    return updated_user


@router.get("/me/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user preferences and settings"""
    profile = user_repo.get_profile(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


# Session Management Endpoints

@router.get("/me/sessions", response_model=List[SessionInfo])
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get all active sessions for current user"""
    sessions = session_manager.get_user_sessions(current_user.id)
    
    return [
        SessionInfo(
            session_id=s.session_id,
            user_id=s.user_id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            last_activity=s.last_activity_at,
            expires_at=s.expires_at,
            is_trusted_device=s.is_trusted_device
        )
        for s in sessions
    ]


@router.delete("/me/sessions/{session_id}")
async def terminate_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Terminate a specific session"""
    # Verify session belongs to user
    session = session_manager.get_session(session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session_manager.terminate_session(session_id)
    return {"message": "Session terminated"}


# Password Management

@router.post("/auth/password/change")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Change user password"""
    # Verify current password
    if not auth_service.verify_password(
        password_change.current_password,
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_hash = auth_service.hash_password(password_change.new_password)
    
    # Update password
    user_repo.update_user(current_user.id, {
        "password_hash": new_hash,
        "last_password_change": datetime.utcnow(),
        "requires_password_change": False
    })
    
    return {"message": "Password changed successfully"}


@router.post("/auth/password/reset")
async def request_password_reset(
    request: PasswordReset,
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Request password reset email"""
    user = user_repo.get_user_by_email(request.email)
    
    # Always return success to prevent email enumeration
    if user:
        # Generate reset token
        reset_token, _ = jwt_service.create_password_reset_token(
            user_id=user.id,
            email=user.email
        )
        
        # TODO: Send password reset email with token
    
    return {"message": "If email exists, reset link has been sent"}


@router.post("/auth/password/reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    jwt_service: JWTService = Depends(lambda: get_jwt_service("secret-key")),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Confirm password reset with token"""
    try:
        # Verify reset token
        payload = jwt_service.verify_token(
            reset_data.token,
            expected_type=TokenType.PASSWORD_RESET
        )
        user_id = uuid.UUID(payload["sub"])
        
        # Get user
        user = user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash new password
        new_hash = auth_service.hash_password(reset_data.new_password)
        
        # Update password
        user_repo.update_user(user.id, {
            "password_hash": new_hash,
            "last_password_change": datetime.utcnow(),
            "requires_password_change": False,
            "failed_login_attempts": 0,
            "is_locked": False,
            "locked_until": None
        })
        
        # Revoke reset token
        jti = payload.get("jti")
        if jti:
            jwt_service.revoke_token(jti)
        
        return {"message": "Password reset successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Admin Endpoints (require admin permission)

@router.get("/admin/users", dependencies=[Depends(lambda u=Depends(get_current_user), a=Depends(get_auth_service): require_permission(Permission.ADMIN_USERS, u, a))])
async def list_users():
    """List all users (admin only)"""
    # Implementation would list users from database
    return {"message": "Admin endpoint - list users"}


@router.post("/admin/users/{user_id}/roles")
async def assign_user_role(
    user_id: uuid.UUID,
    role: Role,
    current_user: User = Depends(lambda u=Depends(get_current_user), a=Depends(get_auth_service): require_permission(Permission.ADMIN_USERS, u, a)),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Assign role to user (admin only)"""
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    auth_service.assign_role(user, role, granted_by=current_user.id)
    user_repo.update_user(user.id, {"roles": user.roles})
    
    return {"message": f"Role {role.value} assigned to user"}
