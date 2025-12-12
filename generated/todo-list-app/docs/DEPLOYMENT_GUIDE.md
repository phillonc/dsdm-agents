# Deployment Guide

This guide covers deploying the Todo List application to production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Application Server](#application-server)
5. [Web Server Configuration](#web-server-configuration)
6. [SSL/HTTPS Setup](#sslhttps-setup)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Backup Strategy](#backup-strategy)

## Prerequisites

### System Requirements
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- PostgreSQL 12+
- Nginx or Apache
- 2GB+ RAM
- 10GB+ disk space

### Required Software
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
sudo apt-get install -y postgresql postgresql-contrib
sudo apt-get install -y nginx
sudo apt-get install -y supervisor  # For process management
```

## Environment Setup

### 1. Create Application User
```bash
sudo useradd -m -s /bin/bash todoapp
sudo su - todoapp
```

### 2. Clone and Setup Application
```bash
cd /home/todoapp
git clone <repository-url> todo-list-app
cd todo-list-app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 3. Create Production Environment File
```bash
nano .env
```

```env
# Production Environment Configuration
FLASK_APP=src.app
FLASK_ENV=production
SECRET_KEY=<generate-strong-random-key>

# Database (PostgreSQL)
DATABASE_URL=postgresql://todoapp:password@localhost/todoapp

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Reminders
ENABLE_REMINDERS=True
REMINDER_CHECK_INTERVAL=3600
```

**Generate Strong Secret Key**:
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Database Configuration

### 1. Create PostgreSQL Database
```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE todoapp;
CREATE USER todoapp WITH PASSWORD 'strong-password-here';
GRANT ALL PRIVILEGES ON DATABASE todoapp TO todoapp;
\q
```

### 2. Update PostgreSQL Authentication
```bash
sudo nano /etc/postgresql/12/main/pg_hba.conf
```

Add:
```
local   todoapp         todoapp                                 md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 3. Initialize Database
```bash
cd /home/todoapp/todo-list-app
source venv/bin/activate
python -c "from src.app import create_app; from src.models import db; app = create_app('production'); app.app_context().push(); db.create_all()"
```

## Application Server

### Option 1: Supervisor + Gunicorn (Recommended)

#### 1. Create Gunicorn Configuration
```bash
nano /home/todoapp/todo-list-app/gunicorn_config.py
```

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/home/todoapp/todo-list-app/logs/access.log"
errorlog = "/home/todoapp/todo-list-app/logs/error.log"
loglevel = "info"

# Process naming
proc_name = "todoapp"

# Server mechanics
daemon = False
pidfile = "/home/todoapp/todo-list-app/gunicorn.pid"
```

#### 2. Create Log Directory
```bash
mkdir -p /home/todoapp/todo-list-app/logs
```

#### 3. Create Supervisor Configuration
```bash
sudo nano /etc/supervisor/conf.d/todoapp.conf
```

```ini
[program:todoapp]
command=/home/todoapp/todo-list-app/venv/bin/gunicorn -c /home/todoapp/todo-list-app/gunicorn_config.py "src.app:create_app('production')"
directory=/home/todoapp/todo-list-app
user=todoapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/todoapp/todo-list-app/logs/supervisor.log
environment=PATH="/home/todoapp/todo-list-app/venv/bin"
```

#### 4. Start Application
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start todoapp
sudo supervisorctl status
```

### Option 2: Systemd Service

```bash
sudo nano /etc/systemd/system/todoapp.service
```

```ini
[Unit]
Description=Todo List Application
After=network.target postgresql.service

[Service]
Type=notify
User=todoapp
Group=todoapp
WorkingDirectory=/home/todoapp/todo-list-app
Environment="PATH=/home/todoapp/todo-list-app/venv/bin"
ExecStart=/home/todoapp/todo-list-app/venv/bin/gunicorn -c /home/todoapp/todo-list-app/gunicorn_config.py "src.app:create_app('production')"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl start todoapp
sudo systemctl enable todoapp
sudo systemctl status todoapp
```

## Web Server Configuration

### Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/todoapp
```

```nginx
upstream todoapp {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration (will be set up with Certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/todoapp_access.log;
    error_log /var/log/nginx/todoapp_error.log;

    # Max upload size
    client_max_body_size 10M;

    location / {
        proxy_pass http://todoapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files (if you add any)
    location /static {
        alias /home/todoapp/todo-list-app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/todoapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Free SSL)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

Certbot will automatically:
- Obtain SSL certificates
- Configure Nginx
- Set up auto-renewal (cron job)

## Monitoring and Logging

### 1. Application Logs
```bash
# View application logs
tail -f /home/todoapp/todo-list-app/logs/error.log
tail -f /home/todoapp/todo-list-app/logs/access.log

# View Nginx logs
sudo tail -f /var/log/nginx/todoapp_access.log
sudo tail -f /var/log/nginx/todoapp_error.log

# View Supervisor logs
sudo tail -f /home/todoapp/todo-list-app/logs/supervisor.log
```

### 2. Log Rotation
```bash
sudo nano /etc/logrotate.d/todoapp
```

```
/home/todoapp/todo-list-app/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 todoapp todoapp
    sharedscripts
    postrotate
        supervisorctl restart todoapp
    endscript
}
```

### 3. Monitoring Script
```bash
nano /home/todoapp/check_app.sh
```

```bash
#!/bin/bash
if ! curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "Application is down! Restarting..."
    sudo supervisorctl restart todoapp
fi
```

Add to crontab:
```bash
crontab -e
*/5 * * * * /home/todoapp/check_app.sh
```

## Backup Strategy

### 1. Database Backup Script
```bash
nano /home/todoapp/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/todoapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump -U todoapp todoapp | gzip > $BACKUP_DIR/todoapp_$DATE.sql.gz

# Keep only last 30 days of backups
find $BACKUP_DIR -name "todoapp_*.sql.gz" -mtime +30 -delete
```

Make executable and add to crontab:
```bash
chmod +x /home/todoapp/backup_db.sh
crontab -e
0 2 * * * /home/todoapp/backup_db.sh
```

### 2. Application Files Backup
```bash
nano /home/todoapp/backup_files.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/todoapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf $BACKUP_DIR/app_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    /home/todoapp/todo-list-app/
```

## Post-Deployment Checklist

- [ ] Database created and initialized
- [ ] All environment variables set correctly
- [ ] Gunicorn running and responding
- [ ] Nginx configured and running
- [ ] SSL certificate installed and working
- [ ] Application accessible via HTTPS
- [ ] Logs being written correctly
- [ ] Log rotation configured
- [ ] Backup scripts scheduled
- [ ] Monitoring in place
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] SSH key-based authentication enabled
- [ ] Database credentials secure
- [ ] Regular security updates scheduled

## Maintenance Commands

```bash
# Restart application
sudo supervisorctl restart todoapp

# View logs
sudo supervisorctl tail -f todoapp

# Check status
sudo supervisorctl status

# Restart Nginx
sudo systemctl restart nginx

# Database backup
pg_dump -U todoapp todoapp > backup.sql

# View running processes
ps aux | grep gunicorn

# Check disk space
df -h

# Check memory usage
free -h
```

## Scaling Considerations

### Horizontal Scaling
1. Set up load balancer (HAProxy/Nginx)
2. Deploy multiple application servers
3. Use shared PostgreSQL instance
4. Implement Redis for session storage

### Vertical Scaling
1. Increase Gunicorn workers
2. Upgrade server resources
3. Optimize database queries
4. Add database connection pooling

## Troubleshooting

### Application Won't Start
```bash
# Check logs
sudo supervisorctl tail -f todoapp stderr

# Test manually
cd /home/todoapp/todo-list-app
source venv/bin/activate
gunicorn "src.app:create_app('production')"
```

### Database Connection Issues
```bash
# Test connection
psql -U todoapp -d todoapp -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R todoapp:todoapp /home/todoapp/todo-list-app
sudo chmod -R 755 /home/todoapp/todo-list-app
```

---

For additional support, consult the main README.md or open an issue.
