"""
User Service REST API
Implements authentication and profile management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
import uuid
from .models import (
    User, UserProfile, UserRegistration, UserLogin,
    TokenPair, PasswordReset, PasswordResetConfirm
)
from .auth import AuthService
from .repository import UserRepository


router = APIRouter(prefix="/api/v1", tags=["user-service"])


# Dependency injection
def get_auth_service() -> AuthService:
    """Get authentication service instance"""
    # In production, load from config/environment
    return AuthService(secret_key="your-secret-key-change-in-production")


def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    # In production, inject database connection
    return UserRepository()


def get_current_user(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """Get current authenticated user from JWT token"""
    try:
        # Extract token from "Bearer <token>"
        token = authorization.split(" ")[1]
        payload = auth_service.verify_token(token)
        user_id = uuid.UUID(payload["sub"])
        
        user = user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )


@router.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    registration: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Register new user account
    
    - **email**: Valid email address
    - **password**: Minimum 8 characters with mixed case and number
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
        last_name=registration.last_name
    )
    
    created_user = user_repo.create_user(user)
    
    # Create default profile
    profile = UserProfile(user_id=created_user.id)
    user_repo.create_profile(profile)
    
    # Generate token pair
    tokens = auth_service.create_token_pair(created_user)
    
    # TODO: Send verification email
    
    return tokens


@router.post("/auth/login", response_model=TokenPair)
async def login(
    credentials: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Authenticate user and return JWT tokens
    
    - **email**: User email
    - **password**: User password
    - **mfa_code**: Optional MFA code if enabled
    """
    # Get user
    user = user_repo.get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not auth_service.verify_password(credentials.password, user.password_hash):
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
    
    # Verify MFA if enabled
    if user.mfa_enabled:
        if not credentials.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required"
            )
        
        if not auth_service.verify_mfa_code(user.mfa_secret, credentials.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
    
    # Update last login
    user_repo.update_last_login(user.id)
    
    # Generate tokens
    return auth_service.create_token_pair(user)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    payload = auth_service.verify_token(refresh_token, token_type="refresh")
    user_id = uuid.UUID(payload["sub"])
    
    # Get user
    user = user_repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Generate new token pair
    return auth_service.create_token_pair(user)


@router.get("/users/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user profile
    """
    return current_user


@router.patch("/users/me", response_model=User)
async def update_current_user(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Update current user profile
    """
    updates = {}
    if first_name is not None:
        updates["first_name"] = first_name
    if last_name is not None:
        updates["last_name"] = last_name
    if phone is not None:
        updates["phone"] = phone
    
    updated_user = user_repo.update_user(current_user.id, updates)
    return updated_user


@router.post("/auth/mfa/setup")
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Generate MFA secret for TOTP setup
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA already enabled"
        )
    
    secret = auth_service.generate_mfa_secret()
    
    # Generate QR code data
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="OPTIX"
    )
    
    return {
        "secret": secret,
        "qr_code_uri": totp_uri
    }


@router.post("/auth/mfa/verify")
async def verify_and_enable_mfa(
    secret: str,
    code: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Verify MFA code and enable MFA
    """
    if not auth_service.verify_mfa_code(secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    
    # Enable MFA
    user_repo.update_user(current_user.id, {
        "mfa_enabled": True,
        "mfa_method": "totp",
        "mfa_secret": secret
    })
    
    return {"message": "MFA enabled successfully"}


@router.post("/auth/password-reset")
async def request_password_reset(
    request: PasswordReset,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Request password reset email
    """
    user = user_repo.get_user_by_email(request.email)
    
    # Always return success to prevent email enumeration
    # TODO: Send password reset email if user exists
    
    return {"message": "If email exists, reset link has been sent"}


import pyotp
