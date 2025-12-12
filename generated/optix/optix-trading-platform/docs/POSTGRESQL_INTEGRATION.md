# PostgreSQL Integration Guide

## Overview

The OPTIX Trading Platform uses **PostgreSQL 15+** with **SQLAlchemy 2.0** async patterns for persistent data storage. This guide covers database setup, migrations, and repository usage.

## Architecture

### Database Stack

- **Database**: PostgreSQL 15+ with asyncpg driver
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Connection Pool**: Managed by SQLAlchemy AsyncEngine
- **Schema Organization**: Multi-schema design for microservices

### Key Features

- ✅ **Async/Await**: Full async support using asyncpg
- ✅ **Type Safety**: SQLAlchemy 2.0 Mapped columns with Python type hints
- ✅ **Repository Pattern**: Clean abstraction over database operations
- ✅ **Connection Pooling**: Efficient connection management
- ✅ **Health Checks**: Automatic connection validation
- ✅ **Migrations**: Version-controlled schema changes with Alembic
- ✅ **Soft Deletes**: Preserve data integrity with logical deletion

## Database Schema

### User Service Schema

The `user_service` schema contains all authentication and user management tables:

```sql
user_service.users                  -- User accounts
user_service.sessions_history       -- Session audit trail
user_service.security_events        -- Security audit log
user_service.trusted_devices        -- Trusted device management
user_service.refresh_token_families -- Token rotation tracking
```

### Models

#### UserModel
- Primary user account information
- Authentication credentials (password hash)
- Profile data (name, phone, email)
- Status and role management
- MFA configuration
- Timestamps and soft delete support

#### SessionModel
- Historical session records
- Device identification and fingerprinting
- IP address and user agent tracking
- MFA verification status
- Session lifecycle timestamps

#### SecurityEventModel
- Audit log for security events
- Severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Event metadata (JSON)
- Resolution tracking

#### TrustedDeviceModel
- Trusted device registry for MFA bypass
- Device fingerprinting
- Trust expiration
- Usage statistics
- Revocation support

#### RefreshTokenFamilyModel
- Token rotation detection
- Token family lineage tracking
- Revocation with reason

## Configuration

### Environment Variables

```bash
# PostgreSQL Connection
DATABASE_URL="postgresql://user:password@localhost:5432/optix"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Application
DEBUG=false
ENVIRONMENT=production
```

### Connection String Format

```
postgresql+asyncpg://username:password@host:port/database
```

The async driver (`asyncpg`) is automatically added by the database manager.

## Database Manager

### Initialization

```python
from src.user_service.database import db_manager, init_db

# Initialize on startup
await init_db()

# Close on shutdown
from src.user_service.database import close_db
await close_db()
```

### Usage with Context Manager

```python
from src.user_service.database import db_manager

async with db_manager.get_session() as session:
    # Perform database operations
    user = await session.execute(select(UserModel).where(...))
    # Automatic commit on success, rollback on exception
```

### FastAPI Dependency

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.user_service.database import get_db_session

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(UserModel))
    return result.scalars().all()
```

## Repository Pattern

### Using Repositories

```python
from src.user_service.db_repository import UserRepository
from src.user_service.database import get_db_session

async def create_user_example():
    async with db_manager.get_session() as session:
        user_repo = UserRepository(session)
        
        user = await user_repo.create(
            email="user@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role=UserRole.USER
        )
        
        return user
```

### Available Repositories

#### UserRepository
```python
# Create user
user = await user_repo.create(email, password_hash, ...)

# Get by ID or email
user = await user_repo.get_by_id(user_id)
user = await user_repo.get_by_email(email)

# Update user
user = await user_repo.update(user_id, first_name="New Name")

# Update last login
await user_repo.update_last_login(user_id)

# Update password
await user_repo.update_password(user_id, new_hash)

# Verify email
await user_repo.verify_email(user_id)

# Soft delete
await user_repo.soft_delete(user_id)

# List users
users = await user_repo.list_users(status=UserStatus.ACTIVE, limit=100)

# Count users
count = await user_repo.count_users(role=UserRole.PREMIUM)
```

#### SessionRepository
```python
# Create session
session = await session_repo.create(
    session_id=uuid4(),
    user_id=user_id,
    device_id="device123",
    ip_address="192.168.1.1",
    mfa_verified=True
)

# Get session
session = await session_repo.get_by_session_id(session_id)

# Update activity
await session_repo.update_activity(session_id)

# Terminate session
await session_repo.terminate(session_id)

# Get user sessions
sessions = await session_repo.get_user_sessions(user_id)

# Terminate all user sessions
count = await session_repo.terminate_user_sessions(user_id)

# Cleanup expired sessions
count = await session_repo.cleanup_expired()
```

#### SecurityEventRepository
```python
# Create event
event = await event_repo.create(
    user_id=user_id,
    event_type="login_failed",
    severity=EventSeverity.MEDIUM,
    description="Failed login attempt",
    ip_address="192.168.1.1",
    metadata={"attempts": 3}
)

# Get user events
events = await event_repo.get_user_events(
    user_id,
    event_type="login_failed",
    severity=EventSeverity.HIGH
)

# Get recent events
events = await event_repo.get_recent_events(hours=24)

# Mark resolved
await event_repo.mark_resolved(event_id)
```

#### TrustedDeviceRepository
```python
# Create trusted device
device = await device_repo.create(
    user_id=user_id,
    device_id="device123",
    device_fingerprint="fingerprint",
    trust_token="secure_token",
    device_name="iPhone 15"
)

# Get by token
device = await device_repo.get_by_token(trust_token)

# Get user devices
devices = await device_repo.get_user_devices(user_id)

# Update usage
await device_repo.update_usage(device_id, user_id, ip_address)

# Revoke device
await device_repo.revoke(device_id, user_id)

# Revoke all devices
count = await device_repo.revoke_all(user_id)
```

#### RefreshTokenFamilyRepository
```python
# Create token family
family = await family_repo.create(
    family_id="family123",
    user_id=user_id,
    device_fingerprint="fingerprint"
)

# Get by family ID
family = await family_repo.get_by_family_id(family_id)

# Update last used
await family_repo.update_last_used(family_id)

# Revoke family
await family_repo.revoke(family_id, "security_breach")

# Revoke all user families
count = await family_repo.revoke_user_families(user_id, "logout_all")
```

## Database Migrations

### Alembic Setup

Alembic is configured for async SQLAlchemy 2.0 with automatic migration generation.

### Create Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new field to users"

# Create empty migration
alembic revision -m "Custom migration"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration Structure

```python
"""Migration description

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade() -> None:
    # Upgrade operations
    op.create_table(...)

def downgrade() -> None:
    # Downgrade operations
    op.drop_table(...)
```

## Connection Pool Management

### Pool Configuration

```python
# In database.py
engine = create_async_engine(
    database_url,
    pool_size=20,           # Regular connections
    max_overflow=10,        # Additional connections under load
    pool_pre_ping=True,     # Verify connection before use
    pool_recycle=3600,      # Recycle after 1 hour
)
```

### Pool Monitoring

The database manager includes event listeners for connection monitoring:

- `connect`: Fired when new connection is created
- `checkout`: Fired when connection is checked out from pool
- `checkin`: Fired when connection is returned to pool

## Health Checks

### Database Health Check

```python
from src.user_service.database import db_manager

# Check database connectivity
is_healthy = await db_manager.health_check()
```

### In Endpoints

```python
@router.get("/health/database")
async def database_health():
    is_healthy = await db_manager.health_check()
    return {"status": "healthy" if is_healthy else "unhealthy"}
```

## Best Practices

### 1. Always Use Context Managers

```python
# ✅ Good
async with db_manager.get_session() as session:
    result = await session.execute(query)

# ❌ Bad - manual session management
session = await db_manager.get_raw_session()
# ... operations
await session.close()  # Easy to forget!
```

### 2. Use Repositories

```python
# ✅ Good - repository pattern
user = await user_repo.get_by_email(email)

# ❌ Bad - raw queries
result = await session.execute(
    select(UserModel).where(UserModel.email == email)
)
```

### 3. Batch Operations

```python
# ✅ Good - batch operations
async with db_manager.get_session() as session:
    user_repo = UserRepository(session)
    
    for user_data in batch:
        await user_repo.create(**user_data)
    # Single commit for all

# ❌ Bad - individual commits
for user_data in batch:
    async with db_manager.get_session() as session:
        await user_repo.create(**user_data)
    # Commit per user!
```

### 4. Index Usage

Ensure queries use indexes:

```python
# ✅ Good - uses index
user = await user_repo.get_by_email(email)  # email is indexed

# ⚠️ Careful - may need index
users = await session.execute(
    select(UserModel).where(UserModel.phone_number == phone)
)
```

### 5. Soft Deletes

Always use soft delete for user data:

```python
# ✅ Good
await user_repo.soft_delete(user_id)

# ❌ Bad - hard delete loses data
await session.delete(user)
```

## Troubleshooting

### Connection Issues

```python
# Check pool status
pool = db_manager.engine.pool
print(f"Size: {pool.size()}")
print(f"Checked out: {pool.checkedin()}")
```

### Query Performance

Enable SQL echo for debugging:

```python
# In settings.py
DEBUG = True  # Enables SQL logging
```

### Migration Conflicts

```bash
# Reset to specific revision
alembic downgrade abc123

# Stamp without running migration
alembic stamp head
```

## Security Considerations

1. **Connection Strings**: Never commit database credentials
2. **SQL Injection**: Use parameterized queries (automatic with ORM)
3. **Encryption**: Use SSL/TLS for production connections
4. **Least Privilege**: Database user should have minimum required permissions
5. **Audit Logs**: Use SecurityEventModel for all sensitive operations

## Performance Optimization

1. **Indexes**: Ensure appropriate indexes on filtered columns
2. **Connection Pool**: Tune pool size based on load
3. **Query Optimization**: Use `select()` with specific columns
4. **Eager Loading**: Use `selectinload()` for relationships
5. **Batch Operations**: Minimize round trips to database

## Monitoring

Key metrics to monitor:

- Connection pool size and usage
- Query execution time
- Database CPU and memory usage
- Slow query log
- Connection errors and timeouts
- Migration status

## Next Steps

- Review [Rate Limiting Guide](./RATE_LIMITING.md)
- See [API Reference](./API_REFERENCE.md)
- Check [Security Audit Checklist](./SECURITY_AUDIT_CHECKLIST.md)
