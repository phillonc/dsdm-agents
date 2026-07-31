# Deployment Guide

Guide for deploying the OPTIX Brokerage Integrations service to production.

## Prerequisites

- Docker and Docker Compose
- PostgreSQL 14+
- Redis 7+
- Python 3.11+
- Access to brokerage API credentials

## Environment Setup

### 1. Environment Variables

Create a `.env` file with all required configuration:

```bash
# Application
APP_ENV=production
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/optix
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Brokerage API Credentials
SCHWAB_CLIENT_ID=your_schwab_client_id
SCHWAB_CLIENT_SECRET=your_schwab_client_secret
SCHWAB_REDIRECT_URI=https://yourdomain.com/oauth/callback/schwab

FIDELITY_CLIENT_ID=your_fidelity_client_id
FIDELITY_CLIENT_SECRET=your_fidelity_client_secret
FIDELITY_REDIRECT_URI=https://yourdomain.com/oauth/callback/fidelity

PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=production

IBKR_CLIENT_ID=your_ibkr_client_id
IBKR_CLIENT_SECRET=your_ibkr_client_secret
IBKR_USE_GATEWAY=false

WEBULL_CLIENT_ID=your_webull_client_id
WEBULL_CLIENT_SECRET=your_webull_client_secret

# Security
TOKEN_ENCRYPTION_KEY=your_32_byte_base64_key
SECRET_KEY=your_api_secret_key

# OAuth
OAUTH_STATE_TTL_MINUTES=10
TOKEN_REFRESH_BUFFER_MINUTES=5

# Performance
SYNC_INTERVAL_MINUTES=15
POSITION_SYNC_TIMEOUT_SECONDS=30
MAX_WORKERS=4
```

### 2. Generate Encryption Key

```bash
python -c "from src.brokerage_service.encryption import TokenEncryption; print(TokenEncryption.generate_key())"
```

## Docker Deployment

### 1. Build Docker Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.brokerage_service.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Build:
```bash
docker build -t optix-brokerage:latest .
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    image: optix-brokerage:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/optix
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=optix
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  scheduler:
    image: optix-brokerage:latest
    command: python -m src.scheduler
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

Start services:
```bash
docker-compose up -d
```

## Database Migration

### 1. Run Alembic Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### 2. Database Schema

Ensure these tables exist:

```sql
-- brokerage_connections
CREATE TABLE brokerage_connections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- positions
CREATE TABLE positions (
    id UUID PRIMARY KEY,
    connection_id UUID REFERENCES brokerage_connections(id),
    symbol VARCHAR(50) NOT NULL,
    position_type VARCHAR(50) NOT NULL,
    quantity DECIMAL(15, 8) NOT NULL,
    average_price DECIMAL(15, 2) NOT NULL,
    cost_basis DECIMAL(15, 2) NOT NULL,
    current_price DECIMAL(15, 2) NOT NULL,
    market_value DECIMAL(15, 2) NOT NULL,
    unrealized_pl DECIMAL(15, 2) NOT NULL,
    unrealized_pl_percent DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    connection_id UUID REFERENCES brokerage_connections(id),
    transaction_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(50),
    quantity DECIMAL(15, 8),
    price DECIMAL(15, 2),
    amount DECIMAL(15, 2) NOT NULL,
    fees DECIMAL(15, 2) DEFAULT 0,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- portfolio_snapshots
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    snapshot_type VARCHAR(20) NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL,
    total_cash DECIMAL(15, 2) NOT NULL,
    positions_snapshot JSONB,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, snapshot_type, DATE(captured_at))
);

-- account_balances
CREATE TABLE account_balances (
    id UUID PRIMARY KEY,
    connection_id UUID REFERENCES brokerage_connections(id),
    cash DECIMAL(15, 2) DEFAULT 0,
    equity DECIMAL(15, 2) DEFAULT 0,
    buying_power DECIMAL(15, 2) DEFAULT 0,
    margin_balance DECIMAL(15, 2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Kubernetes Deployment

### 1. Deployment YAML

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: optix-brokerage-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: optix-brokerage-api
  template:
    metadata:
      labels:
        app: optix-brokerage-api
    spec:
      containers:
      - name: api
        image: optix-brokerage:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: optix-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: optix-config
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 2. Service YAML

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: optix-brokerage-api
spec:
  selector:
    app: optix-brokerage-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply:
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Monitoring

### 1. Prometheus Metrics

Add to `api.py`:

```python
from prometheus_client import Counter, Histogram, make_asgi_app

# Metrics
sync_counter = Counter('optix_syncs_total', 'Total syncs', ['provider', 'status'])
sync_duration = Histogram('optix_sync_duration_seconds', 'Sync duration', ['provider'])

# Add metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### 2. Grafana Dashboard

Import dashboard JSON from `monitoring/grafana-dashboard.json`

### 3. Sentry Error Tracking

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

## Scheduled Tasks

### Start-of-Day Snapshots

Schedule to run at 9:30 AM ET daily:

```python
# scheduler.py
import schedule
import time
from src.brokerage_service.sync_service import PortfolioSyncService

def capture_snapshots():
    service = PortfolioSyncService(repository)
    asyncio.run(service.capture_all_user_snapshots())

schedule.every().day.at("09:30").do(capture_snapshots)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Health Checks

Endpoint: `GET /health`

Response:
```json
{
  "status": "healthy",
  "service": "brokerage-api",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

## Scaling

### Horizontal Scaling

- Add more API replicas: `docker-compose up --scale api=3`
- Load balancer distributes requests
- Redis handles distributed state

### Database Optimization

- Add indexes on frequently queried columns
- Use connection pooling
- Implement read replicas for queries

## Backup

### Database Backup

```bash
# Daily backup
pg_dump -h localhost -U postgres optix > backup-$(date +%Y%m%d).sql

# Restore
psql -h localhost -U postgres optix < backup-20251216.sql
```

### Redis Backup

```bash
# Save snapshot
redis-cli SAVE

# Copy dump.rdb
cp /var/lib/redis/dump.rdb /backups/
```

## Security Checklist

- [ ] All secrets in environment variables or secrets manager
- [ ] HTTPS enabled with valid SSL certificate
- [ ] CORS configured properly
- [ ] Rate limiting enabled
- [ ] Database connections encrypted
- [ ] Token encryption key rotated regularly
- [ ] Security headers configured
- [ ] Firewall rules configured

## Troubleshooting

### High Memory Usage

Check for connection leaks:
```bash
docker stats
```

### Slow Sync Performance

Check logs:
```bash
docker-compose logs -f api
```

### Database Connection Issues

Test connection:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

## Rollback

```bash
# Rollback to previous version
docker-compose down
docker pull optix-brokerage:previous-tag
docker-compose up -d

# Rollback database
alembic downgrade -1
```
