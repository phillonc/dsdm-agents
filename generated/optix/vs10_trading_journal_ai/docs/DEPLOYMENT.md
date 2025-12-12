# VS-10 Trading Journal AI - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Production Configuration](#production-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB SSD
- Network: 100 Mbps

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 8+ GB
- Storage: 100+ GB SSD
- Network: 1 Gbps

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- Kubernetes 1.27+ (for K8s deployment)
- PostgreSQL 14+
- Redis 7+
- Python 3.10+ (for local development)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd vs10_trading_journal_ai
```

### 2. Environment Variables

Create `.env` file:

```bash
# Application
APP_NAME=trading-journal-ai
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_KEY=<generate-secure-key>
SECRET_KEY=<generate-secure-key>

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/trading_journal
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=<redis-password>

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# VS-7 Integration
VS7_API_URL=http://vs7-api:8001
VS7_API_KEY=<vs7-api-key>
VS7_SYNC_INTERVAL=3600

# Security
JWT_SECRET_KEY=<generate-secure-key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
CORS_ORIGINS=["https://optix-trading.com"]

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
PROMETHEUS_ENABLED=true
METRICS_PORT=9090

# S3/Storage (for exports and attachments)
AWS_ACCESS_KEY_ID=<aws-key>
AWS_SECRET_ACCESS_KEY=<aws-secret>
S3_BUCKET=trading-journal-exports
S3_REGION=us-east-1
```

### 3. Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

## Database Configuration

### PostgreSQL Setup

#### 1. Create Database

```sql
CREATE DATABASE trading_journal;
CREATE USER trading_journal_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_journal TO trading_journal_user;
```

#### 2. Run Migrations

```bash
# Install Alembic
pip install alembic

# Initialize migrations (if not exists)
alembic init alembic

# Run migrations
alembic upgrade head
```

#### 3. Create Indexes

```sql
-- Performance indexes
CREATE INDEX idx_trades_user_entry_date ON trades(user_id, entry_date);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_journal_user_entry_date ON journal_entries(user_id, entry_date);
CREATE INDEX idx_weekly_reviews_user_week ON weekly_reviews(user_id, week_start);
```

### Redis Setup

```bash
# Redis configuration in redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Docker Deployment

### 1. Build Image

```bash
docker build -t trading-journal-ai:1.0.0 .
```

### 2. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: trading_journal
      POSTGRES_USER: trading_journal_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trading_journal_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    image: trading-journal-ai:1.0.0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - VS7_API_URL=${VS7_API_URL}
      - VS7_API_KEY=${VS7_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - SENTRY_DSN=${SENTRY_DSN}
    ports:
      - "8000:8000"
    command: uvicorn src.api:app --host 0.0.0.0 --port 8000 --workers 4
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  celery-worker:
    image: trading-journal-ai:1.0.0
    depends_on:
      - redis
      - postgres
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    command: celery -A src.tasks worker --loglevel=info
    restart: unless-stopped

  celery-beat:
    image: trading-journal-ai:1.0.0
    depends_on:
      - redis
      - postgres
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    command: celery -A src.tasks beat --loglevel=info
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check services
docker-compose ps

# Check logs
docker-compose logs -f api

# Test API
curl http://localhost:8000/health
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace trading-journal
```

### 2. ConfigMap

`k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-journal-config
  namespace: trading-journal
data:
  APP_NAME: "trading-journal-ai"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_PORT: "8000"
  PROMETHEUS_ENABLED: "true"
```

### 3. Secrets

```bash
kubectl create secret generic trading-journal-secrets \
  --from-literal=database-url=<database-url> \
  --from-literal=redis-url=<redis-url> \
  --from-literal=api-key=<api-key> \
  --from-literal=secret-key=<secret-key> \
  --from-literal=vs7-api-key=<vs7-key> \
  -n trading-journal
```

### 4. Deployment

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-journal-api
  namespace: trading-journal
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-journal-api
  template:
    metadata:
      labels:
        app: trading-journal-api
    spec:
      containers:
      - name: api
        image: trading-journal-ai:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: trading-journal-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: trading-journal-secrets
              key: redis-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: trading-journal-secrets
              key: secret-key
        envFrom:
        - configMapRef:
            name: trading-journal-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
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

### 5. Service

`k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: trading-journal-api
  namespace: trading-journal
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: trading-journal-api
```

### 6. Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: trading-journal-api-hpa
  namespace: trading-journal
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: trading-journal-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 7. Deploy to Kubernetes

```bash
kubectl apply -f k8s/
kubectl get pods -n trading-journal
kubectl logs -f deployment/trading-journal-api -n trading-journal
```

## Production Configuration

### Nginx Reverse Proxy

```nginx
upstream trading_journal_api {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.optix-trading.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.optix-trading.com;

    ssl_certificate /etc/ssl/certs/optix-trading.crt;
    ssl_certificate_key /etc/ssl/private/optix-trading.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://trading_journal_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        access_log off;
        proxy_pass http://trading_journal_api/health;
    }
}
```

### Gunicorn Configuration

`gunicorn.conf.py`:

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
timeout = 60
graceful_timeout = 30
max_requests = 10000
max_requests_jitter = 1000
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

## Monitoring & Logging

### Prometheus Metrics

Exposed at `/metrics`:

- Request count and latency
- Active connections
- Database connection pool
- Trade sync statistics
- Error rates

### Grafana Dashboard

Import dashboard from `monitoring/grafana-dashboard.json`

**Key Metrics:**
- API request rate
- Response times (p50, p95, p99)
- Error rate
- Database query performance
- Cache hit rate
- Trade sync success rate

### Logging Configuration

```python
# logging_config.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/trading-journal/app.log',
            'maxBytes': 100_000_000,
            'backupCount': 10,
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}
```

### Sentry Error Tracking

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production")
)
```

## Backup & Recovery

### Database Backups

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="trading_journal"

pg_dump -U trading_journal_user $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Retain last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

### Automated Backups with Cron

```bash
# Add to crontab
0 2 * * * /usr/local/bin/backup-trading-journal.sh
```

### Restore from Backup

```bash
gunzip -c backup_20240115_020000.sql.gz | psql -U trading_journal_user trading_journal
```

### Redis Persistence

```bash
# Enable RDB snapshots
save 900 1
save 300 10
save 60 10000

# Enable AOF
appendonly yes
appendfsync everysec
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
psql -h postgres -U trading_journal_user -d trading_journal

# Check logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 2. Redis Connection Errors

```bash
# Check Redis status
redis-cli ping

# Check memory
redis-cli info memory

# Clear cache if needed
redis-cli FLUSHALL
```

#### 3. High Memory Usage

```bash
# Check memory
docker stats

# Reduce workers
API_WORKERS=2

# Increase database pool efficiency
DATABASE_POOL_SIZE=10
```

#### 4. Slow API Responses

```bash
# Enable query logging
DATABASE_ECHO=true

# Check slow queries
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

# Add missing indexes
CREATE INDEX idx_name ON table(column);
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
pg_isready -h postgres -U trading_journal_user

# Redis health
redis-cli ping

# Check logs
docker-compose logs -f --tail=100
kubectl logs -f deployment/trading-journal-api -n trading-journal
```

### Performance Tuning

```bash
# PostgreSQL
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1

# Application
API_WORKERS=8
DATABASE_POOL_SIZE=20
REDIS_MAX_CONNECTIONS=50
```

## Security Checklist

- [ ] All environment variables use secrets management
- [ ] API keys rotated regularly
- [ ] TLS 1.3 enabled for all connections
- [ ] Database credentials encrypted
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM)
- [ ] XSS protection headers set
- [ ] Regular security audits scheduled

## Maintenance Schedule

**Daily:**
- Monitor error rates
- Check disk space
- Review API metrics

**Weekly:**
- Review logs for anomalies
- Check backup success
- Database vacuum (automated)

**Monthly:**
- Security updates
- Dependency updates
- Performance review
- Capacity planning

---

For additional support, contact DevOps team or refer to the runbook.
