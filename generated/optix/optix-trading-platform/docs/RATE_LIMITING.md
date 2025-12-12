# Rate Limiting Guide

## Overview

The OPTIX Trading Platform implements **Redis-based rate limiting** using a **sliding window algorithm** to protect API endpoints from abuse while maintaining fair access for legitimate users.

## Architecture

### Rate Limiting Stack

- **Storage**: Redis sorted sets
- **Algorithm**: Sliding window counter
- **Granularity**: Per-endpoint configuration
- **Identification**: User ID or IP address
- **Admin Bypass**: Role-based exemptions

### Key Features

- ✅ **Sliding Window**: More accurate than fixed window
- ✅ **Memory Efficient**: Automatic cleanup of old entries
- ✅ **Distributed**: Works across multiple server instances
- ✅ **Admin Bypass**: Administrators exempt from limits
- ✅ **Custom Limits**: Per-endpoint rate limit configuration
- ✅ **Graceful Degradation**: Fails open if Redis unavailable
- ✅ **Rate Limit Headers**: Standard HTTP rate limit headers

## Sliding Window Algorithm

### How It Works

The sliding window algorithm provides accurate rate limiting by:

1. **Storing Timestamps**: Each request is recorded with its timestamp in a Redis sorted set
2. **Window Calculation**: Only requests within the time window are counted
3. **Automatic Cleanup**: Old entries outside the window are removed
4. **Accurate Counting**: Provides true per-second rate limiting

### Advantages Over Fixed Window

| Feature | Fixed Window | Sliding Window |
|---------|-------------|----------------|
| Accuracy | Approximate | Precise |
| Burst Protection | Weak | Strong |
| Edge Cases | Allows 2x limit | True limit |
| Memory | Lower | Moderate |

### Example

With a limit of 5 requests per minute:

```
Time:       0:00  0:30  1:00  1:30  2:00
Fixed:      [---5 req---][---5 req---]
Sliding:        [---5 requests in any 60s---]
```

## Configuration

### Default Rate Limits

```python
# Authentication endpoints
auth_login:    5 requests / minute
auth_register: 3 requests / minute  
auth_refresh:  10 requests / minute
auth_mfa:      5 requests / minute

# General API
api_default:   100 requests / minute
```

### Custom Rate Limits

Register custom limits at startup:

```python
from src.user_service.rate_limiter import get_rate_limiter

rate_limiter = await get_rate_limiter()

rate_limiter.register_limit(
    name="custom_endpoint",
    max_requests=50,
    window_seconds=60
)
```

### Environment Configuration

```bash
# Enable/disable rate limiting
RATE_LIMIT_ENABLED=true

# Redis connection (shared with session management)
REDIS_URL="redis://localhost:6379/0"
REDIS_MAX_CONNECTIONS=50
```

## Usage

### Middleware Integration

#### Option 1: Manual Middleware

```python
from fastapi import APIRouter, Request
from src.user_service.rate_limiter import rate_limit_middleware

router = APIRouter()

@router.post("/login")
async def login(request: Request, credentials: LoginRequest):
    # Apply rate limiting
    await rate_limit_middleware(request, "auth_login")
    
    # Process login
    return await process_login(credentials)
```

#### Option 2: Dependency Injection

```python
from fastapi import Depends
from src.user_service.rate_limiter import rate_limit_middleware

async def rate_limit_login(request: Request):
    await rate_limit_middleware(request, "auth_login")

@router.post("/login")
async def login(
    credentials: LoginRequest,
    _: None = Depends(rate_limit_login)
):
    return await process_login(credentials)
```

#### Option 3: Response Middleware

```python
from fastapi import FastAPI
from src.user_service.rate_limiter import add_rate_limit_headers

@app.middleware("http")
async def rate_limit_response_middleware(request, call_next):
    response = await call_next(request)
    
    # Add rate limit headers if available
    rate_limit_info = getattr(request.state, "rate_limit_info", None)
    if rate_limit_info:
        add_rate_limit_headers(response, rate_limit_info)
    
    return response
```

## Client Identification

### User-Based Limiting

For authenticated requests:

```python
# Identifier: user:{user_id}
identifier = f"user:{request.state.user_id}"
```

### IP-Based Limiting

For anonymous requests:

```python
# Identifier: ip:{ip_address}
# Respects X-Forwarded-For header
identifier = f"ip:{request.client.host}"
```

### Custom Identification

```python
def get_custom_identifier(request: Request) -> str:
    # Use API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api:{api_key}"
    
    # Fallback to IP
    return f"ip:{request.client.host}"
```

## Admin Bypass

### Automatic Bypass

Administrators are automatically exempt from rate limits:

```python
# User with 'admin' role bypasses all rate limits
request.state.user_roles = ["admin", "premium"]

# Rate limiting is skipped
await rate_limit_middleware(request, "auth_login")
```

### Manual Bypass

```python
rate_limiter = await get_rate_limiter()

# Bypass for specific check
allowed, info = await rate_limiter.check_rate_limit(
    identifier="user123",
    limit_name="auth_login",
    bypass=True  # Skip rate limiting
)
```

## Rate Limit Headers

### Standard Headers

All rate-limited responses include:

```http
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1640000000000
```

### 429 Response Headers

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640000000000

{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

### Bypass Header

For admin requests:

```http
X-RateLimit-Bypass: true
```

## Response Handling

### Client Implementation

```typescript
async function makeRequest(url: string) {
  const response = await fetch(url);
  
  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    console.log(`Rate limited. Retry in ${retryAfter} seconds`);
    
    // Wait and retry
    await new Promise(resolve => 
      setTimeout(resolve, parseInt(retryAfter) * 1000)
    );
    return makeRequest(url);
  }
  
  return response;
}
```

### Error Handling

```python
from src.user_service.rate_limiter import RateLimitExceeded

try:
    await rate_limit_middleware(request, "auth_login")
except RateLimitExceeded as e:
    # Handle rate limit exceeded
    logger.warning(
        "Rate limit exceeded",
        user_id=user_id,
        endpoint="login"
    )
    raise  # Re-raise to return 429 response
```

## Monitoring and Analytics

### Check Current Usage

```python
rate_limiter = await get_rate_limiter()

usage = await rate_limiter.get_usage(
    identifier="user:123",
    limit_name="auth_login"
)

print(f"Used: {usage['used']}/{usage['limit']}")
print(f"Remaining: {usage['remaining']}")
print(f"Resets at: {usage['reset_at']}")
```

### Reset Rate Limit

For admin operations or testing:

```python
# Reset specific user's rate limit
success = await rate_limiter.reset_limit(
    identifier="user:123",
    limit_name="auth_login"
)
```

### Monitoring Dashboard

Track these metrics:

- **Rate Limit Hits**: Number of 429 responses
- **Top Limited Users**: Users hitting limits most often
- **Endpoint Usage**: Request counts per endpoint
- **Bypass Usage**: Admin bypass frequency
- **Redis Performance**: Rate limiter operation latency

## Security Considerations

### DDoS Protection

Rate limiting provides first-line defense:

```python
# Aggressive limits for public endpoints
rate_limiter.register_limit(
    name="public_api",
    max_requests=10,
    window_seconds=60
)

# More relaxed for authenticated users
rate_limiter.register_limit(
    name="authenticated_api",
    max_requests=100,
    window_seconds=60
)
```

### Distributed Attacks

IP-based limiting protects against distributed attacks:

```python
# Per-IP limit for login attempts
rate_limiter.register_limit(
    name="login_by_ip",
    max_requests=10,
    window_seconds=300  # 5 minutes
)
```

### Account Enumeration

Prevent account enumeration attacks:

```python
# Same limit for successful and failed logins
await rate_limit_middleware(request, "auth_login")

# Don't reveal if account exists
return generic_error_message()
```

## Best Practices

### 1. Appropriate Limits

```python
# ✅ Good - reasonable limits
login: 5/min          # Prevents brute force
register: 3/min       # Prevents spam
token_refresh: 10/min # Normal usage pattern

# ❌ Bad - too restrictive
login: 1/min          # Frustrates users
api: 10/hour          # Limits normal usage
```

### 2. User Communication

```python
# ✅ Good - clear error message
raise RateLimitExceeded(
    detail=f"Too many login attempts. Try again in {retry_after} seconds.",
    retry_after=retry_after
)

# ❌ Bad - vague message
raise RateLimitExceeded(detail="Rate limit exceeded")
```

### 3. Graceful Degradation

```python
# ✅ Good - fail open on Redis error
try:
    await rate_limit_middleware(request, limit_name)
except Exception as e:
    logger.error("Rate limiting failed", error=str(e))
    # Allow request to proceed

# ❌ Bad - fail closed
await rate_limit_middleware(request, limit_name)
# Hard failure if Redis is down
```

### 4. Monitor and Adjust

```python
# Track rate limit effectiveness
@app.middleware("http")
async def track_rate_limits(request, call_next):
    try:
        response = await call_next(request)
        if response.status_code == 429:
            metrics.increment("rate_limit.exceeded", tags={
                "endpoint": request.url.path
            })
        return response
    except Exception:
        raise
```

## Testing

### Unit Tests

```python
@pytest.mark.asyncio
async def test_rate_limit():
    limiter = SlidingWindowRateLimiter(mock_redis)
    limiter.register_limit("test", max_requests=5, window_seconds=60)
    
    # First 5 requests allowed
    for i in range(5):
        allowed, _ = await limiter.check_rate_limit("user1", "test")
        assert allowed
    
    # 6th request blocked
    allowed, info = await limiter.check_rate_limit("user1", "test")
    assert not allowed
    assert info["retry_after"] > 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_login_rate_limit(client):
    # Attempt 6 logins (limit is 5)
    for i in range(6):
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })
        
        if i < 5:
            assert response.status_code in [200, 401]
        else:
            assert response.status_code == 429
            assert "Retry-After" in response.headers
```

### Load Tests

```bash
# Test rate limiting under load
k6 run --vus 100 --duration 60s rate-limit-test.js
```

## Troubleshooting

### Rate Limit Not Working

1. Check Redis connection:
   ```python
   redis_client = await get_redis_client()
   await redis_client.ping()
   ```

2. Verify rate limiter initialization:
   ```python
   rate_limiter = await get_rate_limiter()
   print(rate_limiter._configs)
   ```

3. Check if bypass is enabled:
   ```python
   bypass = is_admin_request(request)
   print(f"Bypass: {bypass}")
   ```

### False Positives

Check identifier extraction:

```python
identifier = get_client_identifier(request)
print(f"Identifier: {identifier}")

# User ID should be used when authenticated
# IP address should be used for anonymous
```

### Redis Memory Usage

Monitor Redis memory:

```bash
redis-cli INFO memory
```

Cleanup old entries:

```python
# Entries automatically expire after window + 10 seconds
# Manual cleanup if needed:
await redis.delete(f"ratelimit:*")
```

## Performance

### Benchmarks

Typical latency for rate limit check:

- **Redis Available**: 1-3ms
- **Redis Unavailable**: <1ms (fail open)

### Optimization

1. **Pipeline Operations**: Use Redis pipeline for atomic operations
2. **Expiration**: Automatic key expiration prevents memory bloat
3. **Batch Cleanup**: Remove old entries in batch during check
4. **Connection Pooling**: Reuse Redis connections

## Next Steps

- Review [PostgreSQL Integration](./POSTGRESQL_INTEGRATION.md)
- See [Redis Integration](./REDIS_INTEGRATION.md)
- Check [API Reference](./API_REFERENCE.md)
- Review [Security Audit Checklist](./SECURITY_AUDIT_CHECKLIST.md)
