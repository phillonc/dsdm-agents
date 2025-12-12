# Deployment Guide

## Overview

This guide covers deploying the OPTIX Visual Strategy Builder from development to production environments.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Git
- (Production) Docker (recommended)
- (Production) PostgreSQL database (future version)
- (Production) Redis (future version)

## Development Deployment

### Local Setup

1. **Clone Repository**
```bash
git clone <repository-url>
cd optix_visual_strategy_builder
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Run Tests**
```bash
pytest --cov=src
```

5. **Start Development Server**
```bash
python -m src.api
```

Server runs on `http://localhost:5000`

### Development Configuration

Create `.env` file:
```bash
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
```

## Testing Environment

### Continuous Integration

**GitHub Actions** (`.github/workflows/test.yml`):

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

## Production Deployment

### Option 1: Docker Deployment (Recommended)

#### 1. Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Expose port
EXPOSE 5000

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "src.api:app"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  # Future: Add PostgreSQL
  # db:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: optix_strategies
  #     POSTGRES_USER: optix
  #     POSTGRES_PASSWORD: ${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  
  # Future: Add Redis
  # redis:
  #   image: redis:7-alpine
  #   ports:
  #     - "6379:6379"

# volumes:
#   postgres_data:
```

#### 3. Build and Run

```bash
# Build image
docker build -t optix-strategy-builder:latest .

# Run container
docker run -d -p 5000:5000 --name strategy-builder optix-strategy-builder:latest

# Or use docker-compose
docker-compose up -d
```

### Option 2: Manual Deployment

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.10 python3-pip python3-venv nginx -y
```

#### 2. Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/optix-strategy-builder
cd /opt/optix-strategy-builder

# Clone repository
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### 3. Configure Gunicorn

Create `/opt/optix-strategy-builder/gunicorn_config.py`:

```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/optix/access.log"
errorlog = "/var/log/optix/error.log"
loglevel = "info"

# Process naming
proc_name = "optix-strategy-builder"

# Server mechanics
daemon = False
pidfile = "/var/run/optix/strategy-builder.pid"
user = "optix"
group = "optix"
```

#### 4. Create Systemd Service

Create `/etc/systemd/system/optix-strategy-builder.service`:

```ini
[Unit]
Description=OPTIX Visual Strategy Builder
After=network.target

[Service]
Type=notify
User=optix
Group=optix
WorkingDirectory=/opt/optix-strategy-builder
Environment="PATH=/opt/optix-strategy-builder/venv/bin"
ExecStart=/opt/optix-strategy-builder/venv/bin/gunicorn \
    --config /opt/optix-strategy-builder/gunicorn_config.py \
    src.api:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable optix-strategy-builder
sudo systemctl start optix-strategy-builder
sudo systemctl status optix-strategy-builder
```

#### 5. Configure Nginx

Create `/etc/nginx/sites-available/optix-strategy-builder`:

```nginx
upstream strategy_builder {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name api.optix-trading.com;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://strategy_builder;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /health {
        proxy_pass http://strategy_builder/health;
        access_log off;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/optix-strategy-builder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.optix-trading.com
```

### Option 3: Cloud Platform Deployment

#### AWS Elastic Beanstalk

1. Install EB CLI:
```bash
pip install awsebcli
```

2. Initialize:
```bash
eb init -p python-3.10 optix-strategy-builder
```

3. Create environment:
```bash
eb create production-env
```

4. Deploy:
```bash
eb deploy
```

#### Google Cloud Run

1. Build container:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/strategy-builder
```

2. Deploy:
```bash
gcloud run deploy strategy-builder \
    --image gcr.io/PROJECT_ID/strategy-builder \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

#### Azure App Service

1. Create resource:
```bash
az webapp create \
    --resource-group optix-rg \
    --plan optix-plan \
    --name strategy-builder \
    --runtime "PYTHON:3.10"
```

2. Deploy:
```bash
az webapp up --name strategy-builder
```

## Environment Variables

### Production Environment

```bash
# Application
FLASK_ENV=production
LOG_LEVEL=INFO
WORKERS=4

# Future: Database
# DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Future: Redis
# REDIS_URL=redis://localhost:6379/0

# Future: Security
# SECRET_KEY=your-secret-key
# JWT_SECRET=your-jwt-secret

# Monitoring
# SENTRY_DSN=https://...
# DATADOG_API_KEY=...
```

## Monitoring

### Health Check Endpoint

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Visual Strategy Builder",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Logging

**Application Logs**:
```bash
# View logs
tail -f /var/log/optix/error.log
tail -f /var/log/optix/access.log

# Docker logs
docker logs -f strategy-builder
```

**Log Format**:
```
[2024-01-15 10:30:00] INFO: Strategy created: Iron Condor - SPY
[2024-01-15 10:30:01] INFO: Payoff diagram calculated for strategy abc123
[2024-01-15 10:30:02] ERROR: Invalid strategy ID: xyz789
```

### Metrics (Future)

Recommended tools:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Datadog**: APM and monitoring
- **Sentry**: Error tracking

## Performance Tuning

### Gunicorn Workers

Calculate workers:
```
workers = (2 × CPU cores) + 1
```

For 4-core system:
```python
workers = 9
```

### System Resources

**Minimum Requirements**:
- CPU: 2 cores
- RAM: 2 GB
- Disk: 10 GB

**Recommended for Production**:
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD

## Security Checklist

- [ ] Use environment variables for secrets
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Implement rate limiting
- [ ] Add authentication (JWT)
- [ ] Enable CORS properly
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Implement input validation
- [ ] Set up intrusion detection

## Backup and Recovery

### Application Backup

```bash
# Backup application
tar -czf backup-$(date +%Y%m%d).tar.gz /opt/optix-strategy-builder

# Backup to S3 (AWS)
aws s3 cp backup-*.tar.gz s3://optix-backups/
```

### Future: Database Backup

```bash
# PostgreSQL backup
pg_dump -U optix optix_strategies > backup.sql

# Restore
psql -U optix optix_strategies < backup.sql
```

## Scaling

### Horizontal Scaling

**Load Balancer** (Nginx):

```nginx
upstream strategy_builder {
    least_conn;
    server app1.internal:5000;
    server app2.internal:5000;
    server app3.internal:5000;
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: strategy-builder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: strategy-builder
  template:
    metadata:
      labels:
        app: strategy-builder
    spec:
      containers:
      - name: strategy-builder
        image: optix-strategy-builder:latest
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: strategy-builder-service
spec:
  selector:
    app: strategy-builder
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

## Troubleshooting

### Common Issues

**Port Already in Use**:
```bash
# Find process
lsof -i :5000
# Kill process
kill -9 <PID>
```

**Permission Denied**:
```bash
# Fix permissions
sudo chown -R optix:optix /opt/optix-strategy-builder
```

**Import Errors**:
```bash
# Check Python path
export PYTHONPATH="${PYTHONPATH}:/opt/optix-strategy-builder"
```

## Rollback Procedure

```bash
# Stop service
sudo systemctl stop optix-strategy-builder

# Restore previous version
cd /opt/optix-strategy-builder
git checkout <previous-commit>

# Reinstall dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start optix-strategy-builder
```

## Maintenance

### Updates

```bash
# Pull latest code
cd /opt/optix-strategy-builder
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart optix-strategy-builder
```

### Log Rotation

Create `/etc/logrotate.d/optix`:

```
/var/log/optix/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 optix optix
    sharedscripts
    postrotate
        systemctl reload optix-strategy-builder > /dev/null 2>&1 || true
    endscript
}
```

## Support

For deployment issues:
- Check logs: `/var/log/optix/`
- Review documentation
- Contact DevOps team

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
