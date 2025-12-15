"""
User Service REST API
Implements authentication and profile management endpoints

Uses sync PostgreSQL database repository for persistence.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
import uuid
import os
from sqlalchemy.orm import Session

from .models import (
    User, UserProfile, UserRegistration, UserLogin,
    TokenPair, PasswordReset, PasswordResetConfirm
)
from .auth import AuthService
from .db_repository import UserRepository
from .database import get_db_session


router = APIRouter(prefix="/api/v1", tags=["user-service"])


# Dependency injection
def get_auth_service() -> AuthService:
    """Get authentication service instance"""
    secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    return AuthService(secret_key=secret_key)


def get_user_repository(db: Session = Depends(get_db_session)) -> UserRepository:
    """Get user repository instance with database session"""
    return UserRepository(db)


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

        user_model = user_repo.get_by_id(user_id)
        if not user_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Convert database model to Pydantic model
        return _db_user_to_model(user_model)

    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )


def _db_user_to_model(user_model) -> User:
    """Convert database UserModel to Pydantic User model"""
    # Map database role (singular) to roles list for Pydantic model
    roles = [user_model.role] if user_model.role else ["free_user"]

    return User(
        id=user_model.id,
        email=user_model.email,
        password_hash=user_model.password_hash,
        first_name=user_model.first_name,
        last_name=user_model.last_name,
        phone=user_model.phone_number,
        mfa_enabled=user_model.mfa_enabled,
        mfa_secret=user_model.mfa_secret,
        email_verified=user_model.email_verified,
        is_active=user_model.status == "active",
        is_premium=user_model.is_premium,
        roles=roles,
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        last_login_at=user_model.last_login_at,
    )


@router.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(
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
    existing_user = user_repo.get_by_email(registration.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    password_hash = auth_service.hash_password(registration.password)
    try:
        created_user_model = user_repo.create(
            email=registration.email,
            password_hash=password_hash,
            first_name=registration.first_name,
            last_name=registration.last_name
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Convert to Pydantic model for token generation
    created_user = _db_user_to_model(created_user_model)

    # Generate token pair
    tokens = auth_service.create_token_pair(created_user)

    # TODO: Send verification email

    return tokens


@router.post("/auth/login", response_model=TokenPair)
def login(
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
    # Get user from database
    user_model = user_repo.get_by_email(credentials.email)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not auth_service.verify_password(credentials.password, user_model.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check if account is active
    if user_model.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Verify MFA if enabled
    if user_model.mfa_enabled:
        if not credentials.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required"
            )

        if not auth_service.verify_mfa_code(user_model.mfa_secret, credentials.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )

    # Update last login
    user_repo.update_last_login(user_model.id)

    # Convert to Pydantic model and generate tokens
    user = _db_user_to_model(user_model)
    return auth_service.create_token_pair(user)


@router.post("/auth/refresh", response_model=TokenPair)
def refresh_token(
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

    # Get user from database
    user_model = user_repo.get_by_id(user_id)
    if not user_model or user_model.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Convert to Pydantic model and generate new token pair
    user = _db_user_to_model(user_model)
    return auth_service.create_token_pair(user)


@router.get("/users/me", response_model=User)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user profile
    """
    return current_user


@router.patch("/users/me", response_model=User)
def update_current_user(
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
        updates["phone_number"] = phone  # DB column is phone_number

    updated_user_model = user_repo.update(current_user.id, **updates)
    if not updated_user_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return _db_user_to_model(updated_user_model)


@router.post("/auth/mfa/setup")
def setup_mfa(
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
def verify_and_enable_mfa(
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

    # Enable MFA in database
    user_repo.update(
        current_user.id,
        mfa_enabled=True,
        mfa_secret=secret
    )

    return {"message": "MFA enabled successfully"}


@router.post("/auth/password-reset")
def request_password_reset(
    request: PasswordReset,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Request password reset email
    """
    # Check if user exists (but don't reveal this to prevent enumeration)
    _user = user_repo.get_by_email(request.email)

    # Always return success to prevent email enumeration
    # TODO: Send password reset email if user exists

    return {"message": "If email exists, reset link has been sent"}


import pyotp
