# OPTIX Trading Platform - User Service

## Overview

The User Service is the authentication and authorization backbone of the OPTIX Trading Platform, providing enterprise-grade security for trading operations. It implements comprehensive JWT-based authentication, multi-factor authentication (MFA), role-based access control (RBAC), and session management.

## Features

### 🔐 Authentication
- **JWT Token Authentication** - Stateless, scalable authentication
- **Token Rotation** - Automatic refresh token rotation with theft detection
- **Token Families** - Track token lineage to detect reuse
- **Multiple Token Types** - Access, refresh, MFA challenge, password reset, email verification

### 🛡️ Multi-Factor Authentication
- **TOTP** - Time-based One-Time Passwords (Google Authenticator, Authy)
- **SMS Verification** - Text message codes
- **Email Verification** - Email-based codes
- **Backup Codes** - 10 single-use recovery codes
- **Brokerage MFA** - Support for broker-specific MFA flows

### 👥 Role-Based Access Control
- **5 User Roles** - Guest, Free User, Premium User, Trader, Admin
- **40+ Permissions** - Granular resource-based access control
- **Custom Permissions** - Grant specific permissions beyond role
- **Role Hierarchy** - Priority-based permission inheritance

### 📱 Session Management
- **Device Fingerprinting** - Unique device identification
- **Trusted Devices** - Skip MFA on trusted devices
- **Session Tracking** - Monitor active sessions
- **Activity Logging** - Track user actions and endpoints
- **Session Limits** - Maximum 5 concurrent sessions

### 🔒 Security Features
- **Password Hashing** - bcrypt with 12-round salt
- **Account Lockout** - Protection against brute force (5 attempts)
- **Token Theft Detection** - Automatic family revocation
- **Security Monitoring** - Real-time event logging
- **Audit Trail** - Comprehensive security audit logs

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Service                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  JWT Service │  │ Auth Service │  │ MFA Manager  │  │
│  │              │  │              │  │              │  │
│  │ • Token Gen  │  │ • Password   │  │ • TOTP       │  │
│  │ • Validation │  │ • Hashing    │  │ • SMS/Email  │  │
│  │ • Rotation   │  │ • Lockout    │  │ • Backup     │  │
│  │ • Revocation │  │ • Reset      │  │ • Challenge  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Session Mgr   │  │ RBAC Service │  │  Repository  │  │
│  │              │  │              │  │              │  │
│  │ • Lifecycle  │  │ • Roles      │  │ • User CRUD  │  │
│  │ • Trusted    │  │ • Permissions│  │ • Profile    │  │
│  │ • Security   │  │ • Checks     │  │ • Storage    │  │
│  │ • Monitoring │  │ • Custom     │  │ • Queries    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET_KEY="your-secret-key-here"
export DATABASE_URL="postgresql://user:pass@localhost/optix"
export REDIS_URL="redis://localhost:6379"
```

### Basic Usage

```python
from src.user_service.auth import AuthService
from src.user_service.models import User, UserLogin

# Initialize auth service
auth_service = AuthService(secret_key="your-secret-key")

# Register user
user = User(
    email="user@example.com",
    password_hash=auth_service.hash_password("SecurePass123!")
)

# Create tokens
token_pair = auth_service.create_token_pair(user)

# Validate token
payload = auth_service.verify_token(token_pair.access_token)
```

## API Endpoints

### Authentication

#### Register User
```http
POST /api/v1/users/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@",
  "first_name": "John",
  "last_name": "Doe",
  "accepted_tos": true
}

Response: 201 Created
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900,
  "requires_mfa": false
}
```

#### Login
```http
POST /api/v1/users/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@",
  "mfa_code": "123456",
  "remember_device": true
}

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

#### Refresh Token
```http
POST /api/v1/users/auth/refresh?refresh_token=eyJhbGc...

Response: 200 OK
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### MFA

#### Setup MFA
```http
POST /api/v1/users/auth/mfa/setup
Authorization: Bearer eyJhbGc...

Response: 200 OK
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_uri": "otpauth://totp/OPTIX:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=OPTIX"
}
```

#### Verify and Enable MFA
```http
POST /api/v1/users/auth/mfa/verify
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "secret": "JBSWY3DPEHPK3PXP",
  "code": "123456",
  "generate_backup_codes": true
}

Response: 200 OK
{
  "message": "MFA enabled successfully",
  "backup_codes": ["abcd1234", "efgh5678", ...]
}
```

### User Profile

#### Get Current User
```http
GET /api/v1/users/me
Authorization: Bearer eyJhbGc...

Response: 200 OK
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "roles": ["free_user"],
  "is_premium": false,
  "mfa_enabled": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Session Management

#### Get Active Sessions
```http
GET /api/v1/users/me/sessions
Authorization: Bearer eyJhbGc...

Response: 200 OK
[
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2024-01-15T10:00:00Z",
    "last_activity": "2024-01-15T10:30:00Z",
    "is_trusted_device": true
  }
]
```

## Module Documentation

### JWT Service (`jwt_service.py`)

Advanced JWT token management with rotation and theft detection.

**Key Features:**
- Multiple token types (access, refresh, MFA challenge, etc.)
- Token family tracking for refresh tokens
- Automatic token rotation on use
- Token reuse detection (theft prevention)
- Device fingerprinting

**Example:**
```python
from src.user_service.jwt_service import get_jwt_service

jwt_service = get_jwt_service(secret_key="secret")

# Create access token
token, record = jwt_service.create_access_token(
    user_id=user_id,
    email=email,
    roles=["free_user"],
    permissions=["watchlist:read", "alert:write"]
)

# Rotate refresh token
new_token, new_record, family = jwt_service.rotate_refresh_token(old_token)
```

### Auth Service (`auth.py`)

Core authentication service with password management and MFA.

**Key Features:**
- Password hashing with bcrypt
- Password verification
- MFA integration
- Account lockout protection
- RBAC integration

**Example:**
```python
from src.user_service.auth import AuthService

auth_service = AuthService(secret_key="secret")

# Hash password
password_hash = auth_service.hash_password("SecurePass123!")

# Verify password
is_valid = auth_service.verify_password(password, password_hash)

# Check permission
auth_service.require_permission(user, Permission.WATCHLIST_WRITE)
```

### MFA Manager (`mfa_manager.py`)

Multi-factor authentication management.

**Key Features:**
- TOTP generation and verification
- SMS/Email verification codes
- Backup code management
- Brokerage MFA support

**Example:**
```python
from src.user_service.mfa_manager import get_mfa_manager

mfa_manager = get_mfa_manager()

# Generate TOTP secret
secret = mfa_manager.generate_totp_secret()

# Verify TOTP code
is_valid = mfa_manager.verify_totp_code(secret, code)

# Generate backup codes
codes = mfa_manager.generate_backup_codes(user_id)
```

### Session Manager (`session_manager.py`)

Session lifecycle and trusted device management.

**Key Features:**
- Session creation and validation
- Device fingerprinting
- Trusted device tracking
- Security event logging
- Activity monitoring

**Example:**
```python
from src.user_service.session_manager import get_session_manager

session_manager = get_session_manager()

# Create session
session = session_manager.create_session(
    user_id=user_id,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    device_fingerprint="abc123",
    mfa_verified=True
)

# Trust device
device = session_manager.trust_device(
    user_id=user_id,
    device_fingerprint="abc123",
    device_name="My iPhone"
)
```

### RBAC Service (`rbac.py`)

Role-based access control and permission management.

**Key Features:**
- 5 user roles with priority hierarchy
- 40+ granular permissions
- Custom permission grants
- Resource-based access control

**Example:**
```python
from src.user_service.rbac import get_rbac_service, Role, Permission

rbac_service = get_rbac_service()

# Assign role
rbac_service.assign_role(user_id, Role.PREMIUM_USER)

# Check permission
has_perm = rbac_service.has_permission(user_id, Permission.MARKET_DATA_OPTIONS)

# Get user permissions
permissions = rbac_service.get_user_permissions(user_id)
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Session Configuration  
SESSION_TIMEOUT_MINUTES=30
MAX_SESSIONS_PER_USER=5
TRUST_DEVICE_DAYS=30

# Security Configuration
MAX_FAILED_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
PASSWORD_RESET_EXPIRE_HOURS=1

# MFA Configuration
MFA_CHALLENGE_EXPIRE_MINUTES=5
MFA_CODE_LENGTH=6
BACKUP_CODE_COUNT=10

# Database
DATABASE_URL=postgresql://user:pass@localhost/optix

# Cache
REDIS_URL=redis://localhost:6379
```

## Testing

### Run Unit Tests

```bash
# All tests
pytest tests/unit/

# Specific module
pytest tests/unit/test_jwt_service.py -v

# With coverage
pytest tests/unit/ --cov=src/user_service --cov-report=html
```

### Run Integration Tests

```bash
pytest tests/integration/test_auth_flow.py -v
```

### Test Coverage

Current test coverage: **85%**

Key test suites:
- ✅ JWT Service (token generation, validation, rotation)
- ✅ Auth Service (password management, MFA, RBAC)
- ✅ Session Manager (session lifecycle, trusted devices)
- ✅ MFA Manager (TOTP, backup codes, challenges)
- ✅ RBAC Service (roles, permissions, access control)

## Security Best Practices

### For Developers

1. **Never commit secrets** - Use environment variables
2. **Always use HTTPS** in production
3. **Implement rate limiting** on auth endpoints
4. **Use Redis** for token blacklist in production
5. **Rotate JWT secrets** regularly
6. **Monitor security events** continuously
7. **Keep dependencies updated** for security patches

### For Deployment

1. **Enable TLS 1.3** for all connections
2. **Use strong JWT secrets** (32+ random characters)
3. **Configure proper CORS** policies
4. **Enable security headers** (HSTS, CSP, etc.)
5. **Set up monitoring** for failed logins
6. **Implement backup** for user data
7. **Test disaster recovery** procedures

## Performance Considerations

### Optimization Tips

- **Cache RBAC permissions** to reduce database queries
- **Use Redis** for session storage and token blacklist
- **Index database** on user_id, email, session_id
- **Implement connection pooling** for database
- **Use async operations** where possible
- **Monitor token generation** performance

### Scalability

- Stateless JWT tokens support horizontal scaling
- Redis cluster for distributed cache
- Database read replicas for high traffic
- Load balancer compatible
- No single point of failure

## Troubleshooting

### Common Issues

**"Token has expired"**
- Access tokens expire after 15 minutes
- Use refresh token to get new access token
- Check system time synchronization

**"Token reuse detected"**
- Indicates potential token theft
- All tokens in family are revoked
- User must re-authenticate

**"Account is locked"**
- Too many failed login attempts
- Wait 30 minutes or use password reset
- Check failed_login_attempts counter

**"Invalid MFA code"**
- Ensure device time is synchronized
- TOTP codes are time-sensitive (30 seconds)
- Use backup codes if authenticator unavailable

**"Permission denied"**
- User doesn't have required role/permission
- Check user roles with GET /api/v1/users/me
- Contact admin to upgrade account

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Use type hints throughout
- Write comprehensive docstrings
- Add unit tests for new features
- Update documentation

### Pull Request Process

1. Create feature branch from `main`
2. Implement feature with tests
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

## License

Copyright © 2024 OPTIX Trading Platform. All rights reserved.

## Support

For authentication-related issues:
- 📧 Email: support@optixtrading.com
- 📖 Documentation: `/docs/USER_AUTHENTICATION.md`
- 🐛 Bug Reports: GitHub Issues
- 💬 Discord: OPTIX Community Server

## Changelog

### v1.0.0 (2024-01-15)
- ✨ Initial release
- 🔐 JWT authentication with token rotation
- 🛡️ Multi-factor authentication (TOTP, SMS, Email)
- 👥 Role-based access control (5 roles, 40+ permissions)
- 📱 Session management with trusted devices
- 🔒 Security monitoring and audit logging
- ✅ 85% test coverage
