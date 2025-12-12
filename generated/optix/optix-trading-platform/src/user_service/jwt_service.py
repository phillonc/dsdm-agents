"""
Advanced JWT Service
Comprehensive token management with refresh tokens, token families, and revocation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import jwt
import secrets
import hashlib
from enum import Enum
import uuid
from pydantic import BaseModel, Field


class TokenType(str, Enum):
    """JWT token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    MFA_CHALLENGE = "mfa_challenge"


class TokenStatus(str, Enum):
    """Token status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    REPLACED = "replaced"


class RefreshTokenFamily(BaseModel):
    """Refresh token family for rotation tracking"""
    family_id: str = Field(default_factory=lambda: secrets.token_urlsafe(16))
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class TokenRecord(BaseModel):
    """Token record for tracking and revocation"""
    jti: str  # JWT ID
    token_type: TokenType
    user_id: uuid.UUID
    family_id: Optional[str] = None  # For refresh token rotation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    status: TokenStatus = TokenStatus.ACTIVE
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None  # JTI of replacement token


class JWTService:
    """
    Advanced JWT service with comprehensive token management
    Implements token rotation, families, and revocation
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
        mfa_challenge_expire_minutes: int = 5,
        password_reset_expire_hours: int = 1
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        self.mfa_challenge_expire = timedelta(minutes=mfa_challenge_expire_minutes)
        self.password_reset_expire = timedelta(hours=password_reset_expire_hours)
        
        # Token storage (use Redis in production)
        self._token_records: Dict[str, TokenRecord] = {}
        self._token_families: Dict[str, RefreshTokenFamily] = {}
        self._revoked_tokens: set = set()
        self._blacklisted_families: set = set()
    
    def generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return secrets.token_urlsafe(32)
    
    def create_access_token(
        self,
        user_id: uuid.UUID,
        email: str,
        roles: List[str],
        permissions: List[str],
        additional_claims: Optional[Dict[str, Any]] = None,
        is_premium: bool = False
    ) -> Tuple[str, TokenRecord]:
        """
        Create JWT access token
        
        Returns:
            Tuple of (token_string, token_record)
        """
        now = datetime.utcnow()
        expire = now + self.access_token_expire
        jti = self.generate_jti()
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "exp": expire,
            "iat": now,
            "nbf": now,  # Not valid before
            "jti": jti,
            "type": TokenType.ACCESS.value,
            "is_premium": is_premium,
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token record
        record = TokenRecord(
            jti=jti,
            token_type=TokenType.ACCESS,
            user_id=user_id,
            expires_at=expire
        )
        self._token_records[jti] = record
        
        return token, record
    
    def create_refresh_token(
        self,
        user_id: uuid.UUID,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        family_id: Optional[str] = None
    ) -> Tuple[str, TokenRecord, RefreshTokenFamily]:
        """
        Create JWT refresh token with token family for rotation
        
        Returns:
            Tuple of (token_string, token_record, token_family)
        """
        now = datetime.utcnow()
        expire = now + self.refresh_token_expire
        jti = self.generate_jti()
        
        # Create or use existing token family
        if family_id and family_id in self._token_families:
            family = self._token_families[family_id]
            family.last_used_at = now
        else:
            family = RefreshTokenFamily(
                user_id=user_id,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self._token_families[family.family_id] = family
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": jti,
            "type": TokenType.REFRESH.value,
            "family_id": family.family_id
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token record
        record = TokenRecord(
            jti=jti,
            token_type=TokenType.REFRESH,
            user_id=user_id,
            family_id=family.family_id,
            expires_at=expire
        )
        self._token_records[jti] = record
        
        return token, record, family
    
    def rotate_refresh_token(
        self,
        old_token: str
    ) -> Tuple[str, TokenRecord, RefreshTokenFamily]:
        """
        Rotate refresh token (invalidate old, create new in same family)
        Implements automatic detection of token theft via token reuse
        
        Returns:
            Tuple of (new_token_string, new_token_record, token_family)
        """
        # Verify and decode old token
        try:
            payload = jwt.decode(
                old_token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.JWTError as e:
            raise ValueError(f"Invalid refresh token: {str(e)}")
        
        old_jti = payload.get("jti")
        family_id = payload.get("family_id")
        user_id = uuid.UUID(payload["sub"])
        
        # Check if token was already used (potential theft)
        if old_jti in self._token_records:
            old_record = self._token_records[old_jti]
            if old_record.status == TokenStatus.REPLACED:
                # Token reuse detected! Revoke entire family
                self._revoke_token_family(family_id)
                raise ValueError("Token reuse detected - all tokens in family revoked")
        
        # Check if family is blacklisted
        if family_id in self._blacklisted_families:
            raise ValueError("Token family has been revoked")
        
        # Mark old token as replaced
        if old_jti in self._token_records:
            old_record = self._token_records[old_jti]
            old_record.status = TokenStatus.REPLACED
        
        # Create new refresh token in same family
        new_token, new_record, family = self.create_refresh_token(
            user_id=user_id,
            family_id=family_id
        )
        
        # Link old token to new token
        if old_jti in self._token_records:
            self._token_records[old_jti].replaced_by = new_record.jti
        
        return new_token, new_record, family
    
    def create_mfa_challenge_token(
        self,
        user_id: uuid.UUID,
        challenge_id: str,
        mfa_methods: List[str]
    ) -> Tuple[str, TokenRecord]:
        """
        Create temporary MFA challenge token
        Used during MFA verification flow
        """
        now = datetime.utcnow()
        expire = now + self.mfa_challenge_expire
        jti = self.generate_jti()
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": TokenType.MFA_CHALLENGE.value,
            "challenge_id": challenge_id,
            "mfa_methods": mfa_methods
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        record = TokenRecord(
            jti=jti,
            token_type=TokenType.MFA_CHALLENGE,
            user_id=user_id,
            expires_at=expire
        )
        self._token_records[jti] = record
        
        return token, record
    
    def create_password_reset_token(
        self,
        user_id: uuid.UUID,
        email: str
    ) -> Tuple[str, TokenRecord]:
        """Create password reset token"""
        now = datetime.utcnow()
        expire = now + self.password_reset_expire
        jti = self.generate_jti()
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": TokenType.PASSWORD_RESET.value
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        record = TokenRecord(
            jti=jti,
            token_type=TokenType.PASSWORD_RESET,
            user_id=user_id,
            expires_at=expire
        )
        self._token_records[jti] = record
        
        return token, record
    
    def create_email_verification_token(
        self,
        user_id: uuid.UUID,
        email: str
    ) -> Tuple[str, TokenRecord]:
        """Create email verification token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=7)  # 7 days to verify
        jti = self.generate_jti()
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "type": TokenType.EMAIL_VERIFICATION.value
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        record = TokenRecord(
            jti=jti,
            token_type=TokenType.EMAIL_VERIFICATION,
            user_id=user_id,
            expires_at=expire
        )
        self._token_records[jti] = record
        
        return token, record
    
    def verify_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            expected_type: Expected token type (optional)
        
        Returns:
            Decoded token payload
        
        Raises:
            ValueError: If token is invalid, expired, or revoked
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        
        # Verify token type
        token_type = payload.get("type")
        if expected_type and token_type != expected_type.value:
            raise ValueError(f"Invalid token type. Expected {expected_type.value}, got {token_type}")
        
        # Check if token is revoked
        jti = payload.get("jti")
        if jti:
            if jti in self._revoked_tokens:
                raise ValueError("Token has been revoked")
            
            # Check token record
            if jti in self._token_records:
                record = self._token_records[jti]
                if record.status == TokenStatus.REVOKED:
                    raise ValueError("Token has been revoked")
                if record.status == TokenStatus.REPLACED:
                    raise ValueError("Token has been replaced")
            
            # Check family blacklist for refresh tokens
            if token_type == TokenType.REFRESH.value:
                family_id = payload.get("family_id")
                if family_id in self._blacklisted_families:
                    raise ValueError("Token family has been revoked")
        
        return payload
    
    def revoke_token(self, jti: str) -> bool:
        """Revoke specific token by JTI"""
        if jti in self._token_records:
            record = self._token_records[jti]
            record.status = TokenStatus.REVOKED
            record.revoked_at = datetime.utcnow()
            self._revoked_tokens.add(jti)
            return True
        return False
    
    def revoke_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all tokens for a user"""
        count = 0
        for jti, record in self._token_records.items():
            if record.user_id == user_id and record.status == TokenStatus.ACTIVE:
                self.revoke_token(jti)
                count += 1
        return count
    
    def _revoke_token_family(self, family_id: str) -> bool:
        """Revoke all tokens in a refresh token family"""
        if family_id not in self._token_families:
            return False
        
        # Mark family as blacklisted
        self._blacklisted_families.add(family_id)
        
        # Revoke family
        family = self._token_families[family_id]
        family.revoked = True
        family.revoked_at = datetime.utcnow()
        
        # Revoke all tokens in family
        for jti, record in self._token_records.items():
            if record.family_id == family_id and record.status == TokenStatus.ACTIVE:
                self.revoke_token(jti)
        
        return True
    
    def get_token_record(self, jti: str) -> Optional[TokenRecord]:
        """Get token record by JTI"""
        return self._token_records.get(jti)
    
    def get_user_active_tokens(self, user_id: uuid.UUID) -> List[TokenRecord]:
        """Get all active tokens for a user"""
        return [
            record for record in self._token_records.values()
            if record.user_id == user_id and record.status == TokenStatus.ACTIVE
        ]
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens and records"""
        now = datetime.utcnow()
        expired_jtis = [
            jti for jti, record in self._token_records.items()
            if record.expires_at < now and record.status != TokenStatus.REVOKED
        ]
        
        for jti in expired_jtis:
            if jti in self._token_records:
                self._token_records[jti].status = TokenStatus.EXPIRED
        
        return len(expired_jtis)
    
    def create_device_fingerprint(
        self,
        user_agent: str,
        ip_address: str,
        additional_info: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create device fingerprint for tracking
        Used for trusted device detection and security monitoring
        """
        fingerprint_data = f"{user_agent}:{ip_address}"
        if additional_info:
            for key, value in sorted(additional_info.items()):
                fingerprint_data += f":{key}={value}"
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


# Singleton instance
_jwt_service: Optional[JWTService] = None


def get_jwt_service(
    secret_key: Optional[str] = None,
    **kwargs
) -> JWTService:
    """Get JWT service singleton"""
    global _jwt_service
    if _jwt_service is None:
        if secret_key is None:
            raise ValueError("secret_key is required for first initialization")
        _jwt_service = JWTService(secret_key=secret_key, **kwargs)
    return _jwt_service
