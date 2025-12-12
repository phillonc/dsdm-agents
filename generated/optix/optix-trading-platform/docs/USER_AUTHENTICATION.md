# User Authentication System Documentation

## Overview

The OPTIX Trading Platform implements a comprehensive authentication and authorization system featuring:

- **JWT Token Authentication** with token rotation and family tracking
- **Multi-Factor Authentication (MFA)** with TOTP, SMS, and backup codes
- **Role-Based Access Control (RBAC)** with granular permissions
- **Session Management** with trusted device support
- **Security Monitoring** with audit logging and threat detection

## Architecture

### Components

1. **JWT Service** (`jwt_service.py`)
   - Token generation and validation
   - Token rotation and family tracking
   - Automatic token theft detection
   - Multiple token types (access, refresh, MFA challenge, etc.)

2. **Auth Service** (`auth.py`)
   - Password hashing with bcrypt
   - MFA integration
   - RBAC integration
   - Account security (lockout, password reset)

3. **MFA Manager** (`mfa_manager.py`)
   - TOTP (Time-based One-Time Password) support
   - SMS/Email verification codes
   - Backup codes for account recovery
   - Brokerage-specific MFA support

4. **Session Manager** (`session_manager.py`)
   - Session lifecycle management
   - Trusted device tracking
   - Security event logging
   - Suspicious activity detection

5. **RBAC Service** (`rbac.py`)
   - Role and permission management
   - Resource-based access control
   - Custom permission grants

## Authentication Flow

### Registration

```
1. User submits registration form
   - Email (validated)
   - Password (must meet strength requirements)
   - Personal information
   - Accept terms of service

2. System creates user account
   - Hashes password with bcrypt
   - Assigns default "free_user" role
   - Creates user profile
   - Generates JWT tokens

3. System returns token pair
   - Access token (15 min expiry)
   - Refresh token (30 day expiry)
```

### Login

```
1. User submits credentials
   - Email
   - Password
   - Optional: MFA code
   - Optional: Trusted device token

2. System validates credentials
   - Verifies password
   - Checks account status (active, locked)
   - Validates MFA if enabled

3. System creates session
   - Generates device fingerprint
   - Creates session record
   - Checks for trusted device

4. System returns tokens
   - Access token with user info and permissions
   - Refresh token for token rotation
   - Optional: Trusted device token
```

### Token Refresh

```
1. Client sends refresh token

2. System validates and rotates token
   - Verifies refresh token
   - Detects token reuse (theft detection)
   - Invalidates old token
   - Creates new token in same family

3. System returns new token pair
   - New access token
   - New refresh token
```

## Multi-Factor Authentication

### Supported MFA Methods

1. **TOTP (Time-based One-Time Password)**
   - Compatible with Google Authenticator, Authy, etc.
   - QR code provisioning
   - 6-digit codes with 30-second validity window

2. **SMS Verification**
   - 6-digit codes sent via SMS
   - 5-minute validity

3. **Email Verification**
   - 6-digit codes sent via email
   - 5-minute validity

4. **Backup Codes**
   - 10 single-use codes
   - For account recovery
   - Generated during MFA setup

### MFA Setup Flow

```
1. User requests MFA setup
   GET /api/v1/users/auth/mfa/setup
   
2. System generates TOTP secret
   Returns:
   - Secret key
   - QR code URI
   
3. User scans QR code with authenticator app

4. User verifies setup with code
   POST /api/v1/users/auth/mfa/verify
   Body: { secret, code, generate_backup_codes }
   
5. System enables MFA
   - Saves secret
   - Generates backup codes
   - Requires MFA for future logins
```

### MFA Login Flow

```
1. User submits credentials (without MFA code)

2. System validates credentials
   - Returns MFA challenge token
   - Indicates required MFA methods

3. User submits MFA code
   POST /api/v1/users/auth/login
   Body: { email, password, mfa_code }

4. System verifies MFA code
   - Returns full access token
   - Creates authenticated session
```

## Role-Based Access Control

### Roles

| Role | Description | Priority |
|------|-------------|----------|
| `guest` | Limited read-only access | 0 |
| `free_user` | Basic platform features | 10 |
| `premium_user` | Premium features (AI, options flow) | 20 |
| `trader` | Full trading with brokerage integration | 30 |
| `admin` | User management and analytics | 90 |
| `super_admin` | Full system access | 100 |

### Key Permissions

**User Management**
- `user:read` - View user profile
- `user:write` - Update user profile
- `user:delete` - Delete user account

**Watchlist Operations**
- `watchlist:read` - View watchlists
- `watchlist:write` - Create/update watchlists
- `watchlist:delete` - Delete watchlists

**Alert Operations**
- `alert:read` - View alerts
- `alert:write` - Create/update alerts
- `alert:delete` - Delete alerts

**Brokerage Operations**
- `brokerage:connect` - Connect brokerage accounts
- `brokerage:read` - View positions/orders
- `brokerage:trade` - Execute trades
- `brokerage:disconnect` - Disconnect accounts

**Market Data Access**
- `market_data:realtime` - Real-time quotes
- `market_data:historical` - Historical data
- `market_data:options` - Options data (premium)
- `market_data:flow` - Options flow data (premium)

**AI Features**
- `ai:insights` - AI-powered insights (premium)
- `ai:predictions` - Price predictions (premium)

**Premium Features**
- `premium:advanced_charts` - Advanced charting
- `premium:unlimited_alerts` - Unlimited alerts
- `premium:priority_support` - Priority support

**Admin Operations**
- `admin:users` - User administration
- `admin:system` - System configuration
- `admin:analytics` - Platform analytics

### Permission Checking

```python
# Check single permission
if auth_service.check_permission(user, Permission.WATCHLIST_WRITE):
    # Allow watchlist creation
    pass

# Check multiple permissions (require all)
if auth_service.check_permissions(
    user,
    [Permission.BROKERAGE_CONNECT, Permission.BROKERAGE_TRADE],
    require_all=True
):
    # Allow trading
    pass

# Require permission (raises 403 if missing)
auth_service.require_permission(user, Permission.ADMIN_USERS)
```

## Session Management

### Session Creation

Sessions are created on successful login and include:

- **Session ID** - Unique identifier
- **User ID** - Associated user
- **Device Information**
  - Device fingerprint
  - IP address
  - User agent
- **Security Flags**
  - MFA verified
  - Trusted device
  - Trust level
- **Activity Tracking**
  - Last activity timestamp
  - Request count
  - Recent endpoints

### Trusted Devices

Users can mark devices as trusted to skip MFA:

```
1. User logs in with MFA
2. User selects "Remember this device"
3. System generates trust token
4. Token stored on device
5. Future logins from device skip MFA
```

**Trust Properties**
- Optional expiration (e.g., 30 days)
- Can be revoked by user
- Tracked with device fingerprint
- Usage monitoring

### Session Limits

- Maximum 5 active sessions per user
- Oldest sessions automatically terminated when limit exceeded
- Users can view and terminate sessions manually

## Security Features

### Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Password Hashing

- Algorithm: bcrypt
- Cost factor: 12 rounds
- Automatic salt generation
- Unique hash per password instance

### Account Lockout

Protects against brute force attacks:

- **Max Failed Attempts**: 5
- **Lockout Duration**: 30 minutes
- **Automatic Reset**: On lockout expiration
- **Manual Reset**: Via password reset

### Token Security

**Access Tokens**
- Short-lived (15 minutes)
- Contains user ID, roles, and permissions
- Stateless validation
- Revocable via blacklist (Redis in production)

**Refresh Tokens**
- Long-lived (30 days)
- Token family tracking
- Automatic rotation on use
- Token reuse detection (theft prevention)

**Token Theft Detection**

When a refresh token is reused:
1. System detects token was already replaced
2. Entire token family is revoked
3. User is forced to re-authenticate
4. Security event is logged

### Security Monitoring

The system logs security events including:

- **Session Events**
  - Session creation
  - Session termination
  - Suspicious activity

- **Authentication Events**
  - Login attempts (success/failure)
  - Password changes
  - Password reset requests

- **MFA Events**
  - MFA setup
  - MFA verification
  - Backup code usage

- **Device Events**
  - Device trusted
  - Device trust revoked
  - New device detection

- **Permission Events**
  - Permission denied
  - Role assignments
  - Privilege escalation attempts

## API Endpoints

### Authentication

```http
POST /api/v1/users/auth/register
POST /api/v1/users/auth/login
POST /api/v1/users/auth/refresh
POST /api/v1/users/auth/logout
POST /api/v1/users/auth/logout-all
```

### MFA

```http
POST /api/v1/users/auth/mfa/setup
POST /api/v1/users/auth/mfa/verify
POST /api/v1/users/auth/mfa/disable
```

### Password Management

```http
POST /api/v1/users/auth/password/change
POST /api/v1/users/auth/password/reset
POST /api/v1/users/auth/password/reset/confirm
```

### User Profile

```http
GET  /api/v1/users/me
PATCH /api/v1/users/me
GET  /api/v1/users/me/profile
```

### Session Management

```http
GET    /api/v1/users/me/sessions
DELETE /api/v1/users/me/sessions/{session_id}
```

### Admin (Requires admin permission)

```http
GET  /api/v1/users/admin/users
POST /api/v1/users/admin/users/{user_id}/roles
```

## Best Practices

### For Developers

1. **Always use HTTPS** in production
2. **Store secrets securely** (environment variables, secrets manager)
3. **Implement rate limiting** on authentication endpoints
4. **Use Redis** for token blacklist in production
5. **Log security events** to centralized logging system
6. **Monitor for suspicious activity** patterns
7. **Regularly rotate JWT secret keys**
8. **Implement CSRF protection** for state-changing operations

### For Users

1. **Use strong, unique passwords**
2. **Enable MFA** for additional security
3. **Save backup codes** securely
4. **Review active sessions** regularly
5. **Use trusted devices** only on personal devices
6. **Report suspicious activity** immediately
7. **Keep authenticator apps** up to date

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
```

## Troubleshooting

### Common Issues

**"Token has expired"**
- Use refresh token to get new access token
- Access tokens expire after 15 minutes

**"Token reuse detected"**
- Indicates potential token theft
- All tokens in family are revoked
- User must re-authenticate

**"Account is locked"**
- Too many failed login attempts
- Wait 30 minutes or use password reset

**"Invalid MFA code"**
- Ensure device time is synchronized
- TOTP codes are time-sensitive
- Use backup codes if needed

**"Permission denied"**
- User doesn't have required role/permission
- Contact admin to upgrade account

## Migration from Legacy Auth

If migrating from a legacy authentication system:

1. **Hash existing passwords** with bcrypt
2. **Map old roles** to new RBAC roles
3. **Invalidate old tokens** (different format)
4. **Require password reset** for enhanced security
5. **Encourage MFA setup** for all users
6. **Audit permissions** after migration

## Performance Considerations

### Optimization Tips

1. **Cache RBAC permissions** per user
2. **Use Redis** for token blacklist
3. **Implement token rotation** efficiently
4. **Limit session storage** to essential data
5. **Index database** on user_id, email, session_id
6. **Use connection pooling** for database
7. **Implement rate limiting** on auth endpoints

### Scalability

- JWT tokens are stateless (no server-side storage)
- Sessions can be stored in distributed cache (Redis)
- RBAC permissions can be cached
- Horizontal scaling supported
- Load balancer compatible

## Security Audit Checklist

- [ ] JWT secrets are properly secured
- [ ] HTTPS enforced in production
- [ ] Rate limiting configured
- [ ] Account lockout implemented
- [ ] MFA available and encouraged
- [ ] Password requirements enforced
- [ ] Token rotation working
- [ ] Token theft detection active
- [ ] Security events logged
- [ ] Audit logs retained
- [ ] Backup codes stored securely
- [ ] Admin access restricted
- [ ] SQL injection prevented
- [ ] XSS protection enabled
- [ ] CSRF tokens implemented

## Support

For authentication-related issues:
- Review security logs
- Check session status
- Verify token validity
- Confirm RBAC permissions
- Test MFA setup

For security incidents:
- Immediately revoke compromised tokens
- Force password reset
- Review audit logs
- Notify affected users
- Document incident
