# OPTIX Trading Platform - Redis Integration Quick Start

Get the Redis integration up and running in 5 minutes! 🚀

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+
- Git

## Step 1: Start Redis and Services

```bash
# Clone the repository (if not already cloned)
cd optix-trading-platform

# Start Redis, PostgreSQL, and API services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f redis
```

Expected output:
```
optix-redis       | Ready to accept connections
optix-postgres    | database system is ready to accept connections
optix-api         | Application startup complete
```

## Step 2: Verify Redis Connection

```bash
# Connect to Redis CLI
docker exec -it optix-redis redis-cli

# Test connection (should return PONG)
127.0.0.1:6379> PING
PONG

# Exit Redis CLI
127.0.0.1:6379> exit
```

## Step 3: Test the API

```bash
# Check health endpoint (includes Redis status)
curl http://localhost:8000/health | jq

# Expected output:
{
  "status": "healthy",
  "version": "1.0.0",
  "infrastructure": {
    "redis": {
      "status": "healthy",
      "connected_clients": 1,
      "ops_per_sec": 0
    }
  }
}
```

## Step 4: Run Tests

```bash
# Install dependencies (if not in Docker)
pip install -r requirements.txt

# Run Redis integration tests
pytest tests/unit/test_redis_integration.py -v

# Run with coverage
pytest tests/unit/test_redis_integration.py --cov=src/user_service
```

Expected output:
```
tests/unit/test_redis_integration.py::TestRedisClient::test_set_and_get PASSED
tests/unit/test_redis_integration.py::TestRedisTokenBlacklist::test_blacklist_token PASSED
...
======================== 30 passed in 2.5s ========================
```

## Step 5: Quick Usage Examples

### Example 1: Token Blacklist

```python
from src.user_service.redis_token_blacklist import get_token_blacklist
import asyncio

async def blacklist_example():
    blacklist = get_token_blacklist()
    
    # Blacklist a token
    await blacklist.blacklist_token(
        jti="token_123",
        ttl_seconds=3600,
        reason="user_logout"
    )
    
    # Check if blacklisted
    is_revoked = await blacklist.is_blacklisted("token_123")
    print(f"Token blacklisted: {is_revoked}")  # True

asyncio.run(blacklist_example())
```

### Example 2: Session Management

```python
from src.user_service.session_manager_redis import get_redis_session_manager
import uuid
import asyncio

async def session_example():
    manager = get_redis_session_manager(use_redis_storage=True)
    
    # Create session
    session = await manager.create_session_async(
        user_id=uuid.uuid4(),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0...",
        device_fingerprint="fingerprint_hash"
    )
    
    print(f"Session created: {session.session_id}")
    
    # Retrieve session
    retrieved = await manager.get_session_async(session.session_id)
    print(f"Session valid: {retrieved is not None}")

asyncio.run(session_example())
```

### Example 3: JWT with Redis

```python
from src.user_service.jwt_service_redis import get_redis_jwt_service
import uuid
import asyncio

async def jwt_example():
    jwt_service = get_redis_jwt_service(
        secret_key="your_secret_key",
        use_redis_blacklist=True
    )
    
    # Create token
    user_id = uuid.uuid4()
    token, record = jwt_service.create_access_token(
        user_id=user_id,
        email="user@example.com",
        roles=["user"],
        permissions=["read"]
    )
    
    print(f"Token created: {token[:50]}...")
    
    # Verify token (checks Redis blacklist)
    payload = await jwt_service.verify_token_async(token)
    print(f"Token valid for user: {payload['email']}")
    
    # Revoke token
    await jwt_service.revoke_token_async(
        jti=record.jti,
        ttl_seconds=3600,
        user_id=user_id
    )
    
    # Try to verify again (should fail)
    try:
        await jwt_service.verify_token_async(token)
    except ValueError as e:
        print(f"Token revoked: {e}")

asyncio.run(jwt_example())
```

## Step 6: Monitor Redis

### Option A: Redis Commander (GUI)

```bash
# Start Redis Commander (included in docker-compose)
docker-compose --profile dev up -d

# Open in browser
open http://localhost:8081
```

### Option B: Redis CLI

```bash
# Connect to Redis
docker exec -it optix-redis redis-cli

# View all keys (use with caution in production!)
KEYS *

# Get session data
GET session:your-session-id-here

# View blacklisted tokens
SMEMBERS token:revoked_families

# Check memory usage
INFO memory

# Monitor operations in real-time
MONITOR
```

## Step 7: View Logs

```bash
# All services
docker-compose logs -f

# Redis only
docker-compose logs -f redis

# API only
docker-compose logs -f api

# Follow last 100 lines
docker-compose logs --tail=100 -f
```

## Troubleshooting

### Redis Not Starting

```bash
# Check logs
docker-compose logs redis

# Common issue: Port already in use
sudo lsof -i :6379

# Kill existing Redis
docker stop optix-redis
docker rm optix-redis

# Restart
docker-compose up -d redis
```

### Connection Refused

```bash
# Check if Redis is listening
docker exec optix-redis redis-cli ping

# Check Redis configuration
docker exec optix-redis redis-cli CONFIG GET port

# Verify network
docker network inspect optix-trading-platform_optix-network
```

### Application Can't Connect to Redis

```bash
# Check environment variables
docker-compose exec api env | grep REDIS

# Test connection from API container
docker-compose exec api python -c "
from src.user_service.redis_client import get_redis_client
import asyncio
async def test():
    redis = get_redis_client('redis://redis:6379/0')
    await redis.connect()
    print(await redis.ping())
asyncio.run(test())
"
```

### Out of Memory

```bash
# Check memory usage
docker exec optix-redis redis-cli INFO memory

# Clear all data (CAUTION: Development only!)
docker exec optix-redis redis-cli FLUSHALL

# Set memory limit
docker exec optix-redis redis-cli CONFIG SET maxmemory 512mb
docker exec optix-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Configuration

### Environment Variables

Create `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# For Docker
REDIS_URL=redis://redis:6379/0

# With password (production)
REDIS_URL=redis://:your_password@redis:6379/0

# With SSL (production)
REDIS_URL=rediss://redis:6379/0
```

### Docker Compose Override

Create `docker-compose.override.yml` for local customization:

```yaml
version: '3.8'

services:
  redis:
    ports:
      - "6380:6379"  # Change port
    command: redis-server --maxmemory 1gb
```

## Development Workflow

### 1. Make Code Changes

```bash
# Edit Redis integration files
vim src/user_service/redis_token_blacklist.py

# Run tests
pytest tests/unit/test_redis_integration.py -v -k blacklist
```

### 2. Test Changes

```bash
# Run all tests
pytest tests/unit/test_redis_integration.py

# Run specific test class
pytest tests/unit/test_redis_integration.py::TestRedisTokenBlacklist -v

# Run with print output
pytest tests/unit/test_redis_integration.py -v -s
```

### 3. Restart Services

```bash
# Rebuild and restart API
docker-compose up -d --build api

# Or restart all services
docker-compose restart
```

### 4. Check Logs

```bash
# Watch API logs for Redis operations
docker-compose logs -f api | grep redis
```

## Production Checklist

Before deploying to production:

- [ ] Enable Redis authentication (`requirepass` in redis.conf)
- [ ] Enable TLS/SSL (use `rediss://` URL)
- [ ] Set up Redis Sentinel or Cluster for HA
- [ ] Configure persistence (AOF + RDB)
- [ ] Set memory limits and eviction policy
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure alerts for Redis availability
- [ ] Test failover scenarios
- [ ] Document backup/restore procedures
- [ ] Review security best practices

## Next Steps

1. **Read Full Documentation**: See `docs/REDIS_INTEGRATION.md`
2. **PostgreSQL Integration**: Next phase for persistent storage
3. **Rate Limiting**: Implement using Redis counters
4. **AI Integration (VS-1)**: Adaptive Intelligence Engine

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (CAUTION: Data loss!)
docker-compose down -v

# View service status
docker-compose ps

# Execute command in container
docker-compose exec api python -c "import sys; print(sys.version)"

# Scale API instances
docker-compose up -d --scale api=3

# View resource usage
docker stats

# Clean up everything
docker-compose down -v --rmi all
```

## Support

- **Documentation**: `docs/REDIS_INTEGRATION.md`
- **Build Summary**: `REDIS_INTEGRATION_BUILD_SUMMARY.md`
- **Technical Requirements**: `docs/TECHNICAL_REQUIREMENTS_REDIS.md`
- **Issues**: Check application logs and Redis logs

Happy coding! 🎉
