# GEX Visualizer Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring Setup](#monitoring-setup)
- [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements
- CPU: 2+ cores
- RAM: 4GB minimum, 8GB recommended
- Disk: 20GB minimum for database
- OS: Linux (Ubuntu 20.04+), macOS, Windows with WSL2

### Software Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker 20.10+ (for containerized deployment)
- Docker Compose 2.0+ (for local development)

## Local Development

### 1. Clone Repository

```bash
cd generated/gex_visualizer
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Setup Database

```bash
# Create database
createdb gex_db

# Run migrations (if using Alembic)
alembic upgrade head

# Or initialize via Python
python -c "
from src.services.storage_service import StorageService
import asyncio
async def init():
    storage = StorageService()
    await storage.init_db()
asyncio.run(init())
"
```

### 6. Start Redis

```bash
redis-server
```

### 7. Run Application

```bash
# Development mode with auto-reload
python -m src.main

# Or with Uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Access API:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Metrics: http://localhost:8000/metrics

## Docker Deployment

### Using Docker Compose (Recommended for Local/Dev)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f gex-visualizer

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

Services Started:
- GEX Visualizer API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Using Docker Only

```bash
# Build image
docker build -t gex-visualizer:latest .

# Run container (requires external PostgreSQL and Redis)
docker run -d \
  --name gex-visualizer \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  gex-visualizer:latest

# View logs
docker logs -f gex-visualizer

# Stop container
docker stop gex-visualizer
docker rm gex-visualizer
```

## Production Deployment

### 1. Environment Configuration

Create production `.env`:

```bash
# Application
DEBUG=False
LOG_LEVEL=INFO

# Database with SSL
DATABASE_URL=postgresql://gex_user:secure_password@prod-db:5432/gex_db?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://prod-redis:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000

# Monitoring
ENABLE_METRICS=True
```

### 2. Security Checklist

- [ ] Change default passwords
- [ ] Enable SSL/TLS for database
- [ ] Use environment variables for secrets
- [ ] Enable firewall rules
- [ ] Set up API authentication
- [ ] Configure rate limiting
- [ ] Enable HTTPS (use reverse proxy)
- [ ] Regular security updates

### 3. Run with Gunicorn/Uvicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### 4. Systemd Service (Linux)

Create `/etc/systemd/system/gex-visualizer.service`:

```ini
[Unit]
Description=GEX Visualizer API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=gex
Group=gex
WorkingDirectory=/opt/gex-visualizer
Environment="PATH=/opt/gex-visualizer/venv/bin"
EnvironmentFile=/opt/gex-visualizer/.env
ExecStart=/opt/gex-visualizer/venv/bin/gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gex-visualizer
sudo systemctl start gex-visualizer
sudo systemctl status gex-visualizer
```

### 5. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/gex-visualizer`:

```nginx
upstream gex_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name gex.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gex.example.com;

    ssl_certificate /etc/letsencrypt/live/gex.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gex.example.com/privkey.pem;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://gex_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /metrics {
        # Restrict metrics endpoint
        allow 10.0.0.0/8;
        deny all;
        proxy_pass http://gex_backend;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/gex-visualizer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Kubernetes Deployment

### 1. Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gex-visualizer
```

### 2. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: gex-secrets
  namespace: gex-visualizer
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/gex_db"
  REDIS_URL: "redis://redis:6379/0"
```

### 3. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gex-config
  namespace: gex-visualizer
data:
  DEBUG: "False"
  LOG_LEVEL: "INFO"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
```

### 4. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gex-visualizer
  namespace: gex-visualizer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gex-visualizer
  template:
    metadata:
      labels:
        app: gex-visualizer
    spec:
      containers:
      - name: gex-visualizer
        image: gex-visualizer:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: gex-config
        - secretRef:
            name: gex-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
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
          initialDelaySeconds: 10
          periodSeconds: 5
```

### 5. Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: gex-visualizer
  namespace: gex-visualizer
spec:
  type: LoadBalancer
  selector:
    app: gex-visualizer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

### 6. Apply Manifests

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods -n gex-visualizer
kubectl get svc -n gex-visualizer

# View logs
kubectl logs -f deployment/gex-visualizer -n gex-visualizer
```

## Monitoring Setup

### Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'gex-visualizer'
    static_configs:
      - targets: ['gex-visualizer:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import dashboard JSON or create panels:

1. **GEX Calculations**: `rate(gex_calculations_total[5m])`
2. **API Latency**: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
3. **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
4. **Database Connections**: `database_connections_active`

### Health Check Monitoring

```bash
# Simple uptime monitor
watch -n 30 'curl -f http://localhost:8000/health || echo "Service Down!"'

# Or use monitoring tools
# - Datadog
# - New Relic
# - Prometheus Alertmanager
```

## Backup and Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
pg_dump -h localhost -U gex_user gex_db > /backups/gex_db_$DATE.sql

# Compress
gzip /backups/gex_db_$DATE.sql

# Remove old backups (keep 30 days)
find /backups -name "gex_db_*.sql.gz" -mtime +30 -delete
```

### Database Restore

```bash
# Restore from backup
gunzip < /backups/gex_db_20240115.sql.gz | psql -h localhost -U gex_user gex_db
```

### Redis Backup

```bash
# Redis saves automatically to /data/dump.rdb
# Copy backup
cp /var/lib/redis/dump.rdb /backups/redis_backup_$(date +%Y%m%d).rdb
```

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose logs gex-visualizer

# Verify database connection
psql -h localhost -U gex_user -d gex_db -c "SELECT 1;"

# Verify Redis connection
redis-cli ping
```

### High CPU Usage

```bash
# Check worker count
ps aux | grep uvicorn

# Reduce workers if needed
# Adjust --workers parameter
```

### Database Connection Errors

```bash
# Check connection pool settings
# Increase DATABASE_POOL_SIZE and DATABASE_MAX_OVERFLOW

# Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'gex_db';
```

### Memory Issues

```bash
# Monitor memory usage
docker stats gex-visualizer

# Increase memory limit in docker-compose.yml:
mem_limit: 4g
```

## Performance Tuning

### PostgreSQL

```sql
-- Increase shared_buffers
ALTER SYSTEM SET shared_buffers = '2GB';

-- Increase effective_cache_size
ALTER SYSTEM SET effective_cache_size = '6GB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis

```conf
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Application

```python
# Increase connection pool
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Adjust worker count based on CPU cores
workers = (2 * cpu_cores) + 1
```

## Maintenance Tasks

### Daily
- Monitor logs for errors
- Check system resources
- Verify backups completed

### Weekly
- Review application metrics
- Check for security updates
- Analyze slow queries

### Monthly
- Database vacuum and analyze
- Cleanup old historical data
- Review and optimize indexes
- Update dependencies

---

For support: dev@optix.trading
