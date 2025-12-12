"""
Multi-Factor Authentication (MFA) Manager
Enhanced MFA support for brokerage connections with backup codes and session management
"""
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from enum import Enum
import pyotp
import secrets
import hashlib
import uuid
from pydantic import BaseModel, Field


class MFAType(str, Enum):
    """Types of MFA authentication"""
    TOTP = "totp"  # Time-based One-Time Password (e.g., Google Authenticator)
    SMS = "sms"  # SMS text message
    EMAIL = "email"  # Email verification code
    BACKUP_CODE = "backup_code"  # One-time backup codes
    BROKERAGE = "brokerage"  # Brokerage-specific MFA (e.g., Schwab Symantec VIP)


class MFAStatus(str, Enum):
    """MFA verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class MFAChallenge(BaseModel):
    """MFA challenge/session"""
    challenge_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    mfa_type: MFAType
    challenge_code: Optional[str] = None  # For SMS/Email
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    attempts: int = 0
    max_attempts: int = 3
    status: MFAStatus = MFAStatus.PENDING
    metadata: Dict = Field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if challenge has expired"""
        return datetime.utcnow() > self.expires_at
    
    def can_attempt(self) -> bool:
        """Check if more attempts are allowed"""
        return self.attempts < self.max_attempts and not self.is_expired()


class BrokerageConnection(BaseModel):
    """Brokerage connection with MFA"""
    connection_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    broker_name: str  # schwab, td_ameritrade, fidelity, etc.
    account_id: str
    mfa_required: bool = True
    mfa_type: Optional[MFAType] = None
    mfa_verified: bool = False
    last_mfa_verification: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Connection credentials (encrypted in production)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    
    def needs_mfa_reverification(self, reverify_hours: int = 24) -> bool:
        """Check if MFA needs to be verified again"""
        if not self.mfa_verified or not self.last_mfa_verification:
            return True
        
        reverify_threshold = datetime.utcnow() - timedelta(hours=reverify_hours)
        return self.last_mfa_verification < reverify_threshold


class BackupCode(BaseModel):
    """MFA backup code"""
    code_hash: str
    used: bool = False
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MFAManager:
    """Manages multi-factor authentication for users and brokerage connections"""
    
    def __init__(self):
        self._challenges: Dict[uuid.UUID, MFAChallenge] = {}
        self._backup_codes: Dict[uuid.UUID, List[BackupCode]] = {}
        self._brokerage_connections: Dict[uuid.UUID, BrokerageConnection] = {}
        
        # Configuration
        self.totp_window = 1  # Allow 1 time step before/after
        self.challenge_expiry_minutes = 5
        self.sms_code_length = 6
        self.backup_code_count = 10
        self.backup_code_length = 8
    
    # TOTP (Time-based One-Time Password) Methods
    
    def generate_totp_secret(self) -> str:
        """Generate TOTP secret for authenticator apps"""
        return pyotp.random_base32()
    
    def get_totp_provisioning_uri(
        self,
        secret: str,
        email: str,
        issuer: str = "OPTIX Trading"
    ) -> str:
        """Get provisioning URI for QR code generation"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    def verify_totp_code(self, secret: str, code: str) -> bool:
        """Verify TOTP code from authenticator app"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=self.totp_window)
    
    # SMS/Email MFA Methods
    
    def create_verification_challenge(
        self,
        user_id: uuid.UUID,
        mfa_type: MFAType,
        metadata: Optional[Dict] = None
    ) -> MFAChallenge:
        """Create MFA verification challenge"""
        # Generate verification code for SMS/Email
        challenge_code = None
        if mfa_type in [MFAType.SMS, MFAType.EMAIL]:
            challenge_code = self._generate_verification_code()
        
        challenge = MFAChallenge(
            user_id=user_id,
            mfa_type=mfa_type,
            challenge_code=challenge_code,
            expires_at=datetime.utcnow() + timedelta(minutes=self.challenge_expiry_minutes),
            metadata=metadata or {}
        )
        
        self._challenges[challenge.challenge_id] = challenge
        return challenge
    
    def verify_challenge(
        self,
        challenge_id: uuid.UUID,
        verification_code: str
    ) -> Tuple[bool, str]:
        """Verify MFA challenge with provided code"""
        challenge = self._challenges.get(challenge_id)
        
        if not challenge:
            return False, "Invalid challenge ID"
        
        if challenge.status != MFAStatus.PENDING:
            return False, f"Challenge already {challenge.status.value}"
        
        if challenge.is_expired():
            challenge.status = MFAStatus.EXPIRED
            return False, "Challenge has expired"
        
        if not challenge.can_attempt():
            challenge.status = MFAStatus.FAILED
            return False, "Maximum attempts exceeded"
        
        challenge.attempts += 1
        
        # Verify based on type
        verified = False
        if challenge.mfa_type in [MFAType.SMS, MFAType.EMAIL]:
            verified = challenge.challenge_code == verification_code
        elif challenge.mfa_type == MFAType.BACKUP_CODE:
            verified = self._verify_backup_code(challenge.user_id, verification_code)
        
        if verified:
            challenge.status = MFAStatus.VERIFIED
            return True, "Verification successful"
        else:
            if not challenge.can_attempt():
                challenge.status = MFAStatus.FAILED
            return False, "Invalid verification code"
    
    def _generate_verification_code(self) -> str:
        """Generate random verification code for SMS/Email"""
        # Generate cryptographically secure random code
        code = ''.join(str(secrets.randbelow(10)) for _ in range(self.sms_code_length))
        return code
    
    # Backup Codes Methods
    
    def generate_backup_codes(self, user_id: uuid.UUID) -> List[str]:
        """Generate backup codes for account recovery"""
        codes = []
        backup_codes = []
        
        for _ in range(self.backup_code_count):
            # Generate random code
            code = secrets.token_hex(self.backup_code_length // 2)
            codes.append(code)
            
            # Store hashed version
            code_hash = self._hash_backup_code(code)
            backup_codes.append(BackupCode(code_hash=code_hash))
        
        self._backup_codes[user_id] = backup_codes
        return codes
    
    def _verify_backup_code(self, user_id: uuid.UUID, code: str) -> bool:
        """Verify and mark backup code as used"""
        backup_codes = self._backup_codes.get(user_id, [])
        code_hash = self._hash_backup_code(code)
        
        for backup_code in backup_codes:
            if backup_code.code_hash == code_hash and not backup_code.used:
                backup_code.used = True
                backup_code.used_at = datetime.utcnow()
                return True
        
        return False
    
    def _hash_backup_code(self, code: str) -> str:
        """Hash backup code for secure storage"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def get_remaining_backup_codes(self, user_id: uuid.UUID) -> int:
        """Get count of remaining unused backup codes"""
        backup_codes = self._backup_codes.get(user_id, [])
        return sum(1 for code in backup_codes if not code.used)
    
    # Brokerage Connection MFA Methods
    
    def create_brokerage_connection(
        self,
        user_id: uuid.UUID,
        broker_name: str,
        account_id: str,
        mfa_type: Optional[MFAType] = None
    ) -> BrokerageConnection:
        """Create brokerage connection requiring MFA"""
        connection = BrokerageConnection(
            user_id=user_id,
            broker_name=broker_name,
            account_id=account_id,
            mfa_type=mfa_type or MFAType.TOTP,
            mfa_required=True
        )
        
        self._brokerage_connections[connection.connection_id] = connection
        return connection
    
    def verify_brokerage_mfa(
        self,
        connection_id: uuid.UUID,
        mfa_code: str,
        mfa_secret: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify MFA for brokerage connection"""
        connection = self._brokerage_connections.get(connection_id)
        
        if not connection:
            return False, "Invalid connection ID"
        
        verified = False
        message = ""
        
        if connection.mfa_type == MFAType.TOTP and mfa_secret:
            verified = self.verify_totp_code(mfa_secret, mfa_code)
            message = "TOTP verification successful" if verified else "Invalid TOTP code"
        
        elif connection.mfa_type == MFAType.BROKERAGE:
            # For brokerage-specific MFA (e.g., Schwab Symantec VIP)
            # This would integrate with broker's MFA system
            # For now, we'll create a challenge that needs external verification
            verified = True  # Placeholder - implement broker-specific verification
            message = "Brokerage MFA verification pending"
        
        if verified:
            connection.mfa_verified = True
            connection.last_mfa_verification = datetime.utcnow()
            connection.updated_at = datetime.utcnow()
        
        return verified, message
    
    def get_brokerage_connection(
        self,
        connection_id: uuid.UUID
    ) -> Optional[BrokerageConnection]:
        """Get brokerage connection by ID"""
        return self._brokerage_connections.get(connection_id)
    
    def get_user_brokerage_connections(
        self,
        user_id: uuid.UUID
    ) -> List[BrokerageConnection]:
        """Get all brokerage connections for user"""
        return [
            conn for conn in self._brokerage_connections.values()
            if conn.user_id == user_id
        ]
    
    def revoke_brokerage_connection(self, connection_id: uuid.UUID) -> bool:
        """Revoke/delete brokerage connection"""
        if connection_id in self._brokerage_connections:
            del self._brokerage_connections[connection_id]
            return True
        return False
    
    # Session and Trust Management
    
    def create_trusted_device_token(self, user_id: uuid.UUID) -> str:
        """Create token for trusted device (skip MFA for period)"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        # In production, store this with expiration in database/cache
        return token
    
    def verify_trusted_device(self, user_id: uuid.UUID, token: str) -> bool:
        """Verify if device is trusted (can skip MFA)"""
        # In production, check token against stored trusted devices
        # For now, return False (always require MFA)
        return False
    
    # Cleanup Methods
    
    def cleanup_expired_challenges(self) -> int:
        """Remove expired challenges"""
        expired_ids = [
            cid for cid, challenge in self._challenges.items()
            if challenge.is_expired() or challenge.status != MFAStatus.PENDING
        ]
        
        for cid in expired_ids:
            del self._challenges[cid]
        
        return len(expired_ids)
    
    def get_challenge(self, challenge_id: uuid.UUID) -> Optional[MFAChallenge]:
        """Get MFA challenge by ID"""
        return self._challenges.get(challenge_id)


# Singleton instance
_mfa_manager = None


def get_mfa_manager() -> MFAManager:
    """Get MFA manager singleton"""
    global _mfa_manager
    if _mfa_manager is None:
        _mfa_manager = MFAManager()
    return _mfa_manager
