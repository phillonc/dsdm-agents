"""
Authentication and Authorization Module
Enhanced JWT-based auth with MFA and RBAC support
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
import bcrypt
import pyotp
import secrets
from fastapi import HTTPException, status
from .models import User, TokenPair, TokenPayload, MFAMethod
from .rbac import get_rbac_service, Permission, Role
import uuid


class AuthService:
    """Enhanced authentication service with RBAC and advanced MFA"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        self.rbac_service = get_rbac_service()
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
        self.password_reset_expire_minutes = 60
    
    # Password Management
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with salt"""
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds for good security/performance balance
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    def generate_password_reset_token(self, user_id: uuid.UUID) -> str:
        """Generate password reset token"""
        expire = datetime.utcnow() + timedelta(minutes=self.password_reset_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "password_reset",
            "iat": datetime.utcnow(),
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_password_reset_token(self, token: str) -> Optional[uuid.UUID]:
        """Verify password reset token and return user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "password_reset":
                return None
            
            return uuid.UUID(payload["sub"])
        except (jwt.ExpiredSignatureError, jwt.JWTError):
            return None
    
    # MFA Management
    
    def generate_mfa_secret(self) -> str:
        """Generate TOTP secret for MFA"""
        return pyotp.random_base32()
    
    def verify_mfa_code(self, secret: str, code: str, method: MFAMethod = MFAMethod.TOTP) -> bool:
        """Verify MFA code"""
        if method == MFAMethod.TOTP:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        
        # For SMS/Email, verification happens through MFAManager
        return False
    
    def get_totp_uri(self, secret: str, email: str, issuer: str = "OPTIX") -> str:
        """Get TOTP provisioning URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    # JWT Token Management
    
    def create_access_token(
        self,
        user: User,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token with RBAC permissions"""
        expire = datetime.utcnow() + self.access_token_expire

        # Derive permissions from user's roles using RBAC service's role mappings
        # Import here to avoid circular imports
        from .rbac import Role, ROLE_PERMISSIONS_MAP

        # Map database roles to RBAC Role enum values
        db_role_to_rbac = {
            "user": Role.FREE_USER,
            "premium": Role.PREMIUM_USER,
            "admin": Role.ADMIN,
            "trial": Role.FREE_USER,  # Trial users get free user permissions
        }

        permissions = set()
        for role_str in user.roles:
            try:
                # First try direct Role enum match
                role = Role(role_str)
                if role in ROLE_PERMISSIONS_MAP:
                    permissions.update(ROLE_PERMISSIONS_MAP[role].permissions)
            except ValueError:
                # Try mapping database role to RBAC role
                mapped_role = db_role_to_rbac.get(role_str)
                if mapped_role and mapped_role in ROLE_PERMISSIONS_MAP:
                    permissions.update(ROLE_PERMISSIONS_MAP[mapped_role].permissions)

        permission_strings = [perm.value for perm in permissions]

        to_encode = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "permissions": permission_strings,
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow(),
            "is_premium": user.is_premium,
        }

        if additional_claims:
            to_encode.update(additional_claims)

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + self.refresh_token_expire
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),  # JWT ID for token revocation
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_token_pair(self, user: User, requires_mfa: bool = False) -> TokenPair:
        """Create access and refresh token pair"""
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user.id)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expire.total_seconds()),
            requires_mfa=requires_mfa
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def refresh_access_token(self, refresh_token: str, user: User) -> str:
        """Create new access token from refresh token"""
        payload = self.verify_token(refresh_token, token_type="refresh")
        user_id = uuid.UUID(payload["sub"])
        
        if user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return self.create_access_token(user)
    
    def decode_token(self, token: str) -> TokenPayload:
        """Decode token into TokenPayload model"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            return TokenPayload(
                sub=payload["sub"],
                email=payload.get("email", ""),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                type=payload["type"],
                is_premium=payload.get("is_premium", False)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    # Account Security
    
    def handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt and implement account lockout"""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= self.max_failed_attempts:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=self.lockout_duration_minutes
            )
    
    def handle_successful_login(self, user: User) -> None:
        """Reset failed login attempts on successful login"""
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
    
    def check_account_lockout(self, user: User) -> bool:
        """Check if account is locked out"""
        if not user.is_locked:
            return False
        
        # Check if lockout has expired
        if user.locked_until and datetime.utcnow() > user.locked_until:
            user.is_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
            return False
        
        return True
    
    # Authorization with RBAC
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return self.rbac_service.has_permission(user.id, permission)
    
    def check_permissions(self, user: User, permissions: List[Permission], require_all: bool = True) -> bool:
        """Check if user has permissions (all or any)"""
        if require_all:
            return self.rbac_service.has_all_permissions(user.id, permissions)
        else:
            return self.rbac_service.has_any_permission(user.id, permissions)
    
    def require_permission(self, user: User, permission: Permission) -> None:
        """Raise exception if user doesn't have permission"""
        if not self.check_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
    
    def assign_role(self, user: User, role: Role, granted_by: Optional[uuid.UUID] = None) -> None:
        """Assign role to user"""
        self.rbac_service.assign_role(user.id, role, granted_by)
        if role.value not in user.roles:
            user.roles.append(role.value)
    
    def revoke_role(self, user: User, role: Role) -> None:
        """Revoke role from user"""
        self.rbac_service.revoke_role(user.id, role)
        if role.value in user.roles:
            user.roles.remove(role.value)
    
    def promote_to_premium(self, user: User) -> None:
        """Promote user to premium"""
        user.is_premium = True
        self.assign_role(user, Role.PREMIUM_USER)
    
    def grant_trader_access(self, user: User) -> None:
        """Grant trader role (brokerage access)"""
        self.assign_role(user, Role.TRADER)
    
    # Token Blacklist (for logout/revocation)
    
    def revoke_token(self, token: str) -> None:
        """Add token to blacklist (implement with Redis in production)"""
        # In production, store token JTI in Redis with TTL
        pass
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if token is blacklisted"""
        # In production, check Redis for token JTI
        return False
    
    # Trusted Devices
    
    def generate_device_token(self) -> str:
        """Generate token for trusted device"""
        return secrets.token_urlsafe(32)
    
    def verify_device_token(self, user: User, token: str) -> bool:
        """Verify trusted device token"""
        return token in user.trusted_devices
    
    def add_trusted_device(self, user: User, device_token: str) -> None:
        """Add device to trusted list"""
        if device_token not in user.trusted_devices:
            user.trusted_devices.append(device_token)
    
    def remove_trusted_device(self, user: User, device_token: str) -> bool:
        """Remove device from trusted list"""
        if device_token in user.trusted_devices:
            user.trusted_devices.remove(device_token)
            return True
        return False
