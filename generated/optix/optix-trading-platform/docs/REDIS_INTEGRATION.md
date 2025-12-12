# Redis Integration Guide

## Overview

The OPTIX Trading Platform uses Redis for high-performance, distributed session management and token blacklisting. This guide covers the Redis integration architecture, setup, and usage.

## Architecture

### Components

1. **RedisClient** - Core Redis connection management
2. **RedisTokenBlacklist** - Token revocation and blacklist management
3. **RedisSessionStore** - Session persistence and management
4. **RedisJWTService** - JWT service with Redis-backed blacklist
5. **RedisSessionManager** - Session manager with Redis persistence

### Data Storage Patterns

#### Token Blacklist
- **Keys**: `token:blacklist:{jti}`
- **Type**: String (JSON metadata)
- **TTL**: Token expiration time
- **Purpose**: Track revoked tokens with automatic expiration

#### Token Families
- **Keys**: `token:family:{family_id}`
- **Type**: String (JSON metadata)
- **Set**: `token:revoked_families`
- **Purpose**: Detect token reuse and revoke token families

#### Sessions
- **Keys**: `session:{session_id}`
- **Type**: String (JSON session data)
- **TTL**: Session timeout
- **Purpose**: Store active user sessions

#### User Sessions Index
- **Keys**: `user:sessions:{user_id}`
- **Type**: Set (session IDs)
- **Purpose**: Track all sessions for a user

#### Device Sessions Index
- **Keys**: `device:sessions:{device_id}`
- **Type**: Set (session IDs)
- **Purpose**: Track sessions by device

#### Trusted Devices
- **Keys**: `trusted:device:{device_id}`
- **Type**: String (JSON device data)
- **TTL**: Trust duration
- **Purpose**: Store trusted device information

#### Security Events
- **Keys**: `security:event:{event_id}`
- **Type**: String (JSON event data)
- **TTL**: 90 days default
- **Purpose**: Audit trail for security events

#### User Security Events Index
- **Keys**: `user:security:{user_id}`
- **Type**: Sorted Set (event IDs by timestamp)
- **Purpose**: Fast retrieval of user's security history

## Setup

### 1. Install Redis

#### Using Docker (Recommended for Development)

```bash
# Pull Redis image
docker pull redis:7-alpine

# Run Redis container
docker run -d \
  --name optix-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes

# Verify Redis is running
docker exec -it optix-redis redis-cli ping
# Should return: PONG
```

#### Using Docker Compose

Add to your `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: optix-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis-data:
```

#### Native Installation

**macOS (Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**CentOS/RHEL:**
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. Configure Redis URL

Add to your `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# For production with password
# REDIS_URL=redis://:password@localhost:6379/0

# For Redis Cluster
# REDIS_URL=redis://node1:6379,node2:6379,node3:6379/0
```

### 3. Initialize Redis Client

```python
from src.user_service.redis_client import init_redis

# Initialize on application startup
redis_client = await init_redis()

# Or use the singleton
from src.user_service.redis_client import get_redis_client
redis_client = get_redis_client()
await redis_client.connect()
```

## Usage

### Token Blacklist

#### Blacklist a Token

```python
from src.user_service.redis_token_blacklist import get_token_blacklist

blacklist = get_token_blacklist()

# Blacklist token with automatic expiration
await blacklist.blacklist_token(
    jti="token_jti_123",
    ttl_seconds=3600,  # Token expires in 1 hour
    user_id=user_id,
    reason="user_logout"
)
```

#### Check if Token is Blacklisted

```python
is_revoked = await blacklist.is_blacklisted("token_jti_123")
if is_revoked:
    raise ValueError("Token has been revoked")
```

#### Revoke All User Tokens

```python
# Get list of active token JTIs for user
active_tokens = ["jti1", "jti2", "jti3"]

count = await blacklist.blacklist_all_user_tokens(
    user_id=user_id,
    token_jtis=active_tokens,
    ttl_seconds=3600,
    reason="user_logout_all"
)
print(f"Revoked {count} tokens")
```

#### Revoke Token Family (Refresh Token Rotation)

```python
# When token reuse is detected
await blacklist.blacklist_token_family(
    family_id="family_123",
    ttl_seconds=2592000,  # 30 days
    reason="token_reuse_detected"
)
```

### Session Management

#### Create Session

```python
from src.user_service.redis_session_store import get_session_store
from src.user_service.session_manager import Session

store = get_session_store()

session = Session(
    user_id=user_id,
    device_id="device_123",
    device_fingerprint="fingerprint_hash",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    expires_at=datetime.utcnow() + timedelta(hours=1)
)

await store.create_session(session)
```

#### Retrieve Session

```python
session = await store.get_session(session_id)
if session and not session.is_expired():
    # Session is valid
    pass
```

#### Update Session Activity

```python
session.update_activity(endpoint="/api/trades")
await store.update_session(session, extend_ttl=True)
```

#### Terminate Session

```python
await store.delete_session(session_id)
```

#### Get All User Sessions

```python
sessions = await store.get_user_sessions(user_id, active_only=True)
print(f"User has {len(sessions)} active sessions")
```

### Using Redis-Integrated Services

#### JWT Service

```python
from src.user_service.jwt_service_redis import get_redis_jwt_service

jwt_service = get_redis_jwt_service(
    secret_key="your_secret_key",
    use_redis_blacklist=True
)

# Create token
token, record = jwt_service.create_access_token(
    user_id=user_id,
    email="user@example.com",
    roles=["user"],
    permissions=["read", "write"]
)

# Verify token (checks Redis blacklist)
try:
    payload = await jwt_service.verify_token_async(token)
except ValueError as e:
    print(f"Token invalid: {e}")

# Revoke token
await jwt_service.revoke_token_async(
    jti=record.jti,
    ttl_seconds=3600,
    user_id=user_id,
    reason="security_concern"
)
```

#### Session Manager

```python
from src.user_service.session_manager_redis import get_redis_session_manager

session_manager = get_redis_session_manager(
    session_timeout_minutes=30,
    max_sessions_per_user=5,
    use_redis_storage=True
)

# Create session
session = await session_manager.create_session_async(
    user_id=user_id,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    device_fingerprint="fingerprint_hash",
    mfa_verified=True
)

# Validate session
is_valid = await session_manager.validate_session_async(session.session_id)

# Trust device
device = await session_manager.trust_device_async(
    user_id=user_id,
    device_fingerprint="fingerprint_hash",
    device_name="iPhone 13",
    device_type="mobile",
    duration_days=30
)

# Terminate all user sessions except current
await session_manager.terminate_user_sessions_async(
    user_id=user_id,
    except_session_id=current_session_id
)
```

## Production Considerations

### High Availability

#### Redis Sentinel

For automatic failover:

```env
REDIS_URL=redis://sentinel1:26379,sentinel2:26379/0?sentinel=mymaster
```

#### Redis Cluster

For horizontal scaling:

```env
REDIS_URL=redis://node1:6379,node2:6379,node3:6379/0
```

### Security

#### Enable Authentication

In `redis.conf`:
```conf
requirepass your_strong_password
```

In `.env`:
```env
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

#### Enable TLS/SSL

```env
REDIS_URL=rediss://localhost:6379/0  # Note: rediss:// for SSL
```

#### Network Security

- Use firewall rules to restrict Redis access
- Bind Redis to localhost in development
- Use VPC/private networks in production

### Performance Tuning

#### Connection Pooling

```python
redis_client = RedisClient(
    redis_url=redis_url,
    max_connections=100,  # Increase for high traffic
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)
```

#### Memory Management

In `redis.conf`:
```conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

#### Persistence

For session durability:
```conf
# RDB snapshots
save 900 1
save 300 10
save 60 10000

# AOF for better durability
appendonly yes
appendfsync everysec
```

### Monitoring

#### Key Metrics to Monitor

1. **Memory Usage**: `INFO memory`
2. **Connected Clients**: `INFO clients`
3. **Operations/sec**: `INFO stats`
4. **Hit Rate**: Cache hit ratio
5. **Slow Queries**: `SLOWLOG GET 10`

#### Health Checks

```python
# In your application
async def redis_health_check():
    try:
        await redis_client.ping()
        info = await redis_client.info("stats")
        return {
            "status": "healthy",
            "connected_clients": info.get("connected_clients"),
            "ops_per_sec": info.get("instantaneous_ops_per_sec")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Cleanup and Maintenance

#### Automatic Cleanup

Redis automatically removes expired keys. Monitor with:

```bash
redis-cli INFO keyspace
```

#### Manual Cleanup (if needed)

```python
# Cleanup expired sessions
from src.user_service.redis_session_store import get_session_store
store = get_session_store()
count = await store.cleanup_expired_sessions()

# Cleanup expired blacklist entries
from src.user_service.redis_token_blacklist import get_token_blacklist
blacklist = get_token_blacklist()
count = await blacklist.cleanup_expired()
```

#### Background Cleanup Job

```python
# Run periodically (e.g., via Celery or cron)
async def cleanup_job():
    jwt_service = get_redis_jwt_service()
    session_manager = get_redis_session_manager()
    
    # Cleanup expired tokens and sessions
    jwt_stats = await jwt_service.cleanup_expired_tokens_async()
    session_stats = await session_manager.cleanup_expired_sessions_async()
    
    logger.info("cleanup_completed", jwt_stats=jwt_stats, session_stats=session_stats)
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Redis

**Solutions**:
1. Check Redis is running: `redis-cli ping`
2. Verify connection URL in `.env`
3. Check firewall rules
4. Verify Redis is listening on correct port: `netstat -an | grep 6379`

### Performance Issues

**Problem**: Slow operations

**Solutions**:
1. Check connection pool size
2. Monitor slow queries: `redis-cli SLOWLOG GET 10`
3. Review memory usage: `redis-cli INFO memory`
4. Consider using Redis Cluster for horizontal scaling

### Memory Issues

**Problem**: Redis running out of memory

**Solutions**:
1. Set `maxmemory` limit
2. Configure eviction policy (e.g., `allkeys-lru`)
3. Reduce TTLs for non-critical data
4. Monitor key count and sizes

### Data Loss

**Problem**: Sessions/tokens lost after restart

**Solutions**:
1. Enable AOF persistence
2. Configure RDB snapshots
3. Use Redis Sentinel or Cluster for HA
4. Implement session recreation logic

## Testing

### Unit Tests

```bash
# Run Redis integration tests
pytest tests/unit/test_redis_integration.py -v
```

### Integration Tests

Requires running Redis instance:

```bash
# Start test Redis container
docker run -d --name test-redis -p 6380:6379 redis:7-alpine

# Run integration tests
REDIS_URL=redis://localhost:6380/0 pytest tests/integration/test_redis_flow.py -v

# Cleanup
docker stop test-redis && docker rm test-redis
```

### Load Testing

```python
# Example load test
import asyncio
from src.user_service.redis_client import get_redis_client

async def load_test():
    client = get_redis_client()
    await client.connect()
    
    # Perform 10000 operations
    for i in range(10000):
        await client.set(f"test_key_{i}", f"value_{i}", ttl=60)
    
    print("Load test completed")
```

## Best Practices

1. **Always use TTL**: Set expiration on all keys to prevent memory leaks
2. **Use connection pooling**: Reuse connections for better performance
3. **Monitor memory usage**: Set up alerts for high memory usage
4. **Enable persistence**: Use AOF or RDB for data durability
5. **Implement graceful degradation**: Handle Redis unavailability
6. **Use namespaces**: Prefix keys for organization (already implemented)
7. **Batch operations**: Use pipelines for multiple operations
8. **Regular backups**: Backup Redis data in production
9. **Test failover**: Regularly test Redis failover scenarios
10. **Version control**: Keep Redis configuration in version control

## Migration from In-Memory

To migrate from in-memory storage to Redis:

1. **Update imports**:
   ```python
   # Before
   from src.user_service.jwt_service import get_jwt_service
   from src.user_service.session_manager import get_session_manager
   
   # After
   from src.user_service.jwt_service_redis import get_redis_jwt_service
   from src.user_service.session_manager_redis import get_redis_session_manager
   ```

2. **Initialize Redis**: Add Redis initialization to startup
3. **Update configuration**: Set Redis URL in environment
4. **Test thoroughly**: Verify all authentication flows work
5. **Monitor**: Watch for connection/performance issues
6. **Rollback plan**: Keep in-memory as fallback option

## Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [Redis Best Practices](https://redis.io/topics/best-practices)
- [Redis Security](https://redis.io/topics/security)
- [Redis Persistence](https://redis.io/topics/persistence)
- [Redis Sentinel](https://redis.io/topics/sentinel)
- [Redis Cluster](https://redis.io/topics/cluster-tutorial)
