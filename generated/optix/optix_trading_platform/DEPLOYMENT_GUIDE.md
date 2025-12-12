# Deployment Guide - Options Flow Intelligence

## Pre-Deployment Checklist

### System Requirements
- [ ] Python 3.9 or higher installed
- [ ] pip package manager available
- [ ] 2GB+ available memory
- [ ] Network access for webhook alerts (if used)

### Environment Setup
- [ ] Create Python virtual environment
- [ ] Install dependencies from requirements.txt
- [ ] Configure alert channels
- [ ] Set environment variables (if needed)

## Installation Steps

### 1. Environment Setup

```bash
# Create virtual environment
python3.9 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies

```bash
# Navigate to project directory
cd optix_trading_platform

# Install required packages
pip install -r requirements.txt

# Verify installation
python -c "from src.options_flow_intelligence import OptionsFlowIntelligence; print('Installation successful!')"
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

## Configuration

### Basic Configuration

```python
# config.py
from src.options_flow_intelligence import OptionsFlowIntelligence

# Initialize engine with default settings
engine = OptionsFlowIntelligence(
    enable_alerts=True,
    alert_dispatch_channels=['console']
)
```

### Advanced Configuration

```python
# Configure detectors with custom thresholds
from src.detectors import SweepDetector, BlockDetector, DarkPoolDetector
from decimal import Decimal

# Custom sweep detector
sweep_detector = SweepDetector(
    min_legs=4,
    max_time_window_seconds=2.0,
    min_premium_per_leg=Decimal('10000')
)

# Custom block detector
block_detector = BlockDetector(
    min_contracts=100,
    min_premium=Decimal('100000')
)

# Replace default detectors
engine.sweep_detector = sweep_detector
engine.block_detector = block_detector
```

### Alert Configuration

#### Console Alerts (Default)
```python
engine = OptionsFlowIntelligence(
    enable_alerts=True,
    alert_dispatch_channels=['console']
)
```

#### Webhook Alerts
```python
engine = OptionsFlowIntelligence(
    enable_alerts=True,
    alert_dispatch_channels=['console', 'webhook']
)

# Add webhook URL
engine.add_alert_webhook("https://your-server.com/webhook")
```

#### Custom Alert Handler
```python
def custom_alert_handler(alert):
    # Send to your system
    print(f"Custom handler: {alert.title}")
    # Add your logic here
    
engine.alert_dispatcher.add_custom_handler('custom', custom_alert_handler)
```

## Deployment Scenarios

### Scenario 1: Single Server Deployment

**Use Case:** Development, testing, small-scale production

**Setup:**
```bash
# Install as service
sudo systemctl enable optix-flow-intelligence.service
sudo systemctl start optix-flow-intelligence.service
```

**Service File Example:**
```ini
[Unit]
Description=OPTIX Options Flow Intelligence
After=network.target

[Service]
Type=simple
User=optix
WorkingDirectory=/opt/optix_trading_platform
ExecStart=/opt/optix_trading_platform/venv/bin/python -m src.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Scenario 2: Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

CMD ["python", "-m", "src.main"]
```

**Build and Run:**
```bash
# Build image
docker build -t optix-flow-intelligence:1.0.0 .

# Run container
docker run -d \
  --name optix-flow \
  -p 8080:8080 \
  -v /data/optix:/app/data \
  optix-flow-intelligence:1.0.0
```

### Scenario 3: Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: optix-flow-intelligence
spec:
  replicas: 3
  selector:
    matchLabels:
      app: optix-flow
  template:
    metadata:
      labels:
        app: optix-flow
    spec:
      containers:
      - name: optix-flow
        image: optix-flow-intelligence:1.0.0
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: ALERT_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: optix-secrets
              key: webhook-url
```

## Integration Examples

### Example 1: Real-Time Trade Feed

```python
import asyncio
from src.options_flow_intelligence import OptionsFlowIntelligence
from src.models import OptionsTrade

engine = OptionsFlowIntelligence(enable_alerts=True)

async def process_trade_feed():
    """Process incoming trade feed."""
    async for trade_data in your_trade_feed():
        # Convert to OptionsTrade
        trade = OptionsTrade(**trade_data)
        
        # Process trade
        result = engine.process_trade(trade)
        
        # Log significant detections
        if result['detections']:
            print(f"Detections: {result['detections']}")

asyncio.run(process_trade_feed())
```

### Example 2: REST API Integration

```python
from flask import Flask, request, jsonify
from src.options_flow_intelligence import OptionsFlowIntelligence

app = Flask(__name__)
engine = OptionsFlowIntelligence(enable_alerts=True)

@app.route('/api/v1/trade', methods=['POST'])
def process_trade():
    """Process incoming trade."""
    trade_data = request.json
    trade = OptionsTrade(**trade_data)
    result = engine.process_trade(trade)
    return jsonify(result)

@app.route('/api/v1/flow/<symbol>', methods=['GET'])
def get_flow(symbol):
    """Get order flow for symbol."""
    flow = engine.get_order_flow_summary(symbol)
    return jsonify(flow)

@app.route('/api/v1/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts."""
    min_severity = request.args.get('min_severity')
    alerts = engine.get_active_alerts(min_severity=min_severity)
    return jsonify(alerts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Example 3: Database Persistence

```python
import sqlite3
from datetime import datetime

class TradeStorage:
    """Store trades and detections in database."""
    
    def __init__(self, db_path='optix.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT,
                underlying_symbol TEXT,
                timestamp TEXT,
                premium REAL,
                size INTEGER,
                trade_type TEXT
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT,
                detection_type TEXT,
                confidence REAL,
                timestamp TEXT
            )
        ''')
    
    def store_trade_result(self, trade, result):
        """Store trade and detections."""
        # Store trade
        self.conn.execute('''
            INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.trade_id,
            trade.symbol,
            trade.underlying_symbol,
            trade.timestamp.isoformat(),
            float(trade.premium),
            trade.size,
            trade.trade_type.value
        ))
        
        # Store detections
        for detection in result['detections']:
            self.conn.execute('''
                INSERT INTO detections (trade_id, detection_type, confidence, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                trade.trade_id,
                detection['type'],
                detection['confidence'],
                datetime.now().isoformat()
            ))
        
        self.conn.commit()

# Usage
storage = TradeStorage()
result = engine.process_trade(trade)
storage.store_trade_result(trade, result)
```

## Monitoring

### Application Metrics

```python
from src.options_flow_intelligence import OptionsFlowIntelligence
import time

engine = OptionsFlowIntelligence(enable_alerts=True)

def log_metrics():
    """Log engine metrics."""
    stats = engine.get_statistics()
    
    print(f"Trades Processed: {stats['engine']['trades_processed']}")
    print(f"Sweeps Detected: {stats['engine']['sweeps_detected']}")
    print(f"Alerts Created: {stats['engine']['alerts_created']}")
    
    # Log to monitoring system
    # your_monitoring_system.log(stats)

# Run periodically
while True:
    log_metrics()
    time.sleep(60)  # Every minute
```

### Health Check Endpoint

```python
from flask import Flask, jsonify

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        stats = engine.get_statistics()
        return jsonify({
            'status': 'healthy',
            'trades_processed': stats['engine']['trades_processed'],
            'uptime': get_uptime()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
```

## Performance Tuning

### Memory Optimization

```python
# Reduce buffer sizes for memory-constrained environments
from datetime import timedelta

engine = OptionsFlowIntelligence(enable_alerts=True)

# Reduce analysis windows
engine.flow_analyzer.analysis_window = timedelta(minutes=10)  # Down from 15
engine.flow_aggregator.aggregation_window = timedelta(minutes=30)  # Down from 60

# Reduce alert retention
engine.alert_manager.alert_retention = timedelta(hours=12)  # Down from 24
```

### Throughput Optimization

```python
# Process trades in batches
def process_batch(trades):
    results = []
    for trade in trades:
        result = engine.process_trade(trade)
        results.append(result)
    return results

# Use multiprocessing for parallel symbol processing
from multiprocessing import Pool

def process_symbol_batch(symbol_trades):
    local_engine = OptionsFlowIntelligence(enable_alerts=False)
    return [local_engine.process_trade(t) for t in symbol_trades]

with Pool(processes=4) as pool:
    results = pool.map(process_symbol_batch, symbol_batches)
```

## Troubleshooting

### Issue: High Memory Usage

**Symptoms:** Memory grows over time

**Solutions:**
1. Reduce buffer windows
2. Clear old data more frequently
3. Limit number of tracked symbols
4. Use external cache (Redis)

### Issue: Slow Processing

**Symptoms:** Trades taking > 1ms to process

**Solutions:**
1. Profile code to find bottlenecks
2. Reduce detection complexity
3. Use caching for repeated calculations
4. Consider horizontal scaling

### Issue: Missed Detections

**Symptoms:** Known sweeps/blocks not detected

**Solutions:**
1. Review detection thresholds
2. Verify trade data quality
3. Check time synchronization
4. Enable debug logging

## Security Considerations

### API Security

```python
# Add authentication
from functools import wraps
from flask import request

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or not validate_api_key(api_key):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/v1/trade', methods=['POST'])
@require_api_key
def process_trade():
    # Protected endpoint
    pass
```

### Data Encryption

```python
# Encrypt sensitive data
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt trade data before storage
encrypted_data = cipher.encrypt(trade_data.encode())

# Decrypt when needed
decrypted_data = cipher.decrypt(encrypted_data).decode()
```

## Backup and Recovery

### Data Backup

```bash
# Backup configuration
tar -czf optix_config_backup_$(date +%Y%m%d).tar.gz config/

# Backup database (if used)
sqlite3 optix.db ".backup optix_backup_$(date +%Y%m%d).db"
```

### Disaster Recovery

```bash
# Restore from backup
tar -xzf optix_config_backup_20250112.tar.gz

# Restore database
sqlite3 optix.db ".restore optix_backup_20250112.db"

# Restart service
sudo systemctl restart optix-flow-intelligence
```

## Production Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Alert channels configured
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Backup strategy in place
- [ ] Security measures implemented
- [ ] Performance tuned
- [ ] Documentation reviewed
- [ ] Rollback plan prepared
- [ ] Team trained on system

## Support

For issues or questions:
- Review documentation in `docs/`
- Check examples in `examples/`
- Run diagnostic: `python -m src.diagnostics`
- Contact: support@optix.trading
