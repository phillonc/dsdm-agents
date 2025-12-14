# Quick Start: PostgreSQL & Rate Limiting

## 5-Minute Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL client (optional, for verification)

### 1. Clone and Setup

```bash
cd optix-trading-platform
pip install -r requirements.txt
```

### 2. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

### 3. Run Migrations

```bash
# Apply database schema
alembic upgrade head

# Verify current revision
alembic current
# Expected: 001 (head) (initial_schema)
```

### 4. Verify Database

```bash
# Connect to database
docker-compose exec postgres psql -U postgres -d optix

# Check tables
\dt user_service.*

# Should see:
# - users
# - sessions_history  
# - security_events
# - trusted_devices
# - refresh_token_families

# Check sample users
SELECT email, role FROM user_service.users;

# Should see:
# admin@optix.io | admin
# test@optix.io  | user

# Exit
\q
```

### 5. Test Database Integration

```python
# test_db.py
import asyncio
from src.user_service.database import init_db, db_manager, close_db
from src.user_service.db_repository import UserRepository
from src.user_service.db_models import UserRole

async def test_database():
    # Initialize
    await init_db()
    
    # Create user
    async with db_manager.get_session() as session:
        user_repo = UserRepository(session)
        
        user = await user_repo.create(
            email="quickstart@example.com",
            password_hash="test_hash",
            first_name="Quick",
            last_name="Start",
            role=UserRole.USER
        )
        
        print(f"✅ Created user: {user.id}")
        
        # Retrieve user
        found_user = await user_repo.get_by_email("quickstart@example.com")
        print(f"✅ Found user: {found_user.email}")
        
        # Update user
        await user_repo.update(user.id, first_name="Updated")
        print(f"✅ Updated user")
        
    # Cleanup
    await close_db()
    print("✅ Database test complete!")

if __name__ == "__main__":
    asyncio.run(test_database())
```

Run it:
```bash
python test_db.py
```

### 6. Test Rate Limiting

```python
# test_rate_limit.py
import asyncio
from src.user_service.rate_limiter import get_rate_limiter

async def test_rate_limiting():
    # Initialize rate limiter
    limiter = await get_rate_limiter()
    
    print("Testing rate limiting (5 requests allowed)...")
    
    # Test 7 requests (should block after 5)
    for i in range(7):
        allowed, info = await limiter.check_rate_limit(
            identifier="test_user",
            limit_name="auth_login",
            bypass=False
        )
        
        if allowed:
            print(f"✅ Request {i+1}: Allowed (remaining: {info['remaining']})")
        else:
            print(f"❌ Request {i+1}: BLOCKED (retry in {info['retry_after']}s)")
    
    # Test admin bypass
    allowed, info = await limiter.check_rate_limit(
        identifier="admin_user",
        limit_name="auth_login",
        bypass=True  # Admin bypass
    )
    print(f"✅ Admin request: {'Bypassed' if info.get('bypass') else 'Limited'}")
    
    print("\n✅ Rate limiting test complete!")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
```

Run it:
```bash
python test_rate_limit.py
```

## Using in Your Code

### Database Operations

```python
from src.user_service.database import db_manager
from src.user_service.db_repository import (
    UserRepository, 
    SessionRepository,
    SecurityEventRepository
)
from src.user_service.db_models import UserRole, EventSeverity

async def example_usage():
    async with db_manager.get_session() as session:
        # User operations
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="user@example.com",
            password_hash="hashed_password"
        )
        
        # Session operations
        session_repo = SessionRepository(session)
        session_record = await session_repo.create(
            session_id=uuid4(),
            user_id=user.id,
            device_id="device123",
            ip_address="192.168.1.1"
        )
        
        # Security event logging
        event_repo = SecurityEventRepository(session)
        await event_repo.create(
            user_id=user.id,
            event_type="login_success",
            severity=EventSeverity.LOW,
            description="User logged in successfully",
            ip_address="192.168.1.1"
        )
```

### Rate Limiting in API Endpoints

```python
from fastapi import APIRouter, Request
from src.user_service.rate_limiter import rate_limit_middleware

router = APIRouter()

@router.post("/login")
async def login(request: Request, credentials: dict):
    # Apply rate limiting (5 req/min)
    await rate_limit_middleware(request, "auth_login")
    
    # Your login logic here
    return {"message": "Login successful"}

@router.post("/register")
async def register(request: Request, user_data: dict):
    # Apply rate limiting (3 req/min)
    await rate_limit_middleware(request, "auth_register")
    
    # Your registration logic here
    return {"message": "Registration successful"}
```

## Common Tasks

### Create Migration

```bash
# Make changes to models in src/user_service/db_models.py
# Then generate migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head
```

### Rollback Migration

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123
```

### Reset Rate Limit

```python
from src.user_service.rate_limiter import get_rate_limiter

limiter = await get_rate_limiter()
await limiter.reset_limit("user123", "auth_login")
```

### Check Rate Limit Usage

```python
from src.user_service.rate_limiter import get_rate_limiter

limiter = await get_rate_limiter()
usage = await limiter.get_usage("user123", "auth_login")

print(f"Used: {usage['used']}/{usage['limit']}")
print(f"Remaining: {usage['remaining']}")
```

## Running Tests

```bash
# Database repository tests
pytest tests/unit/test_db_repository.py -v

# Rate limiter tests
pytest tests/unit/test_rate_limiter.py -v

# All tests with coverage
pytest tests/unit/ --cov=src.user_service --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Troubleshooting

### Database connection failed

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

### Redis connection failed

```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Restart
docker-compose restart redis
```

### Migration failed

```bash
# Check current state
alembic current

# Show history
alembic history

# If stuck, downgrade and retry
alembic downgrade -1
alembic upgrade head
```

## Next Steps

1. **Read Documentation**
   - [PostgreSQL Integration Guide](./docs/POSTGRESQL_INTEGRATION.md)
   - [Rate Limiting Guide](./docs/RATE_LIMITING.md)

2. **Review Examples**
   - Check test files for usage examples
   - Review repository implementations

3. **Configure Production**
   - Set up production database credentials
   - Configure SSL/TLS for PostgreSQL
   - Set up Redis authentication
   - Configure rate limits for your use case

4. **Monitor**
   - Add database health checks to monitoring
   - Track rate limit hit rates
   - Monitor connection pool usage

## Support

For detailed documentation, see:
- `docs/POSTGRESQL_INTEGRATION.md`
- `docs/RATE_LIMITING.md`
- `POSTGRESQL_RATE_LIMITING_BUILD.md`

For issues:
1. Check Docker Compose logs
2. Verify environment variables
3. Review test cases for examples
