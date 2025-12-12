# OPTIX Visual Strategy Builder - Deployment Guide

## Overview

This guide provides instructions for deploying the OPTIX Visual Strategy Builder in various environments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Production Deployment](#production-deployment)
6. [Integration](#integration)
7. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

- **Python**: 3.9 or higher
- **RAM**: 512 MB minimum, 2 GB recommended
- **Disk Space**: 100 MB
- **CPU**: Any modern processor

### Supported Operating Systems

- Linux (Ubuntu 20.04+, CentOS 7+, etc.)
- macOS 10.14+
- Windows 10+

### Python Dependencies

See `requirements.txt` for complete list:
- numpy >= 1.24.0
- scipy >= 1.10.0
- python-dateutil >= 2.8.2

---

## Installation

### Option 1: Install from Source

```bash
# Clone repository
git clone https://github.com/optix/visual-strategy-builder.git
cd visual-strategy-builder

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

### Option 2: Install from PyPI (when published)

```bash
pip install optix-visual-strategy-builder
```

### Option 3: Install with Poetry

```bash
poetry install
```

---

## Configuration

### Environment Variables

The system uses these optional environment variables:

```bash
# Risk-free rate (default: 0.05 or 5%)
export OPTIX_RISK_FREE_RATE=0.05

# Default dividend yield (default: 0.0)
export OPTIX_DEFAULT_DIVIDEND_YIELD=0.0

# Monte Carlo simulation count (default: 1000)
export OPTIX_MONTE_CARLO_SIMS=1000
```

### Configuration File (Optional)

Create `config/settings.py`:

```python
# Default settings
DEFAULT_RISK_FREE_RATE = 0.05
DEFAULT_DIVIDEND_YIELD = 0.0
MONTE_CARLO_SIMULATIONS = 1000

# Performance settings
MAX_STRATEGY_LEGS = 20
PAYOFF_DIAGRAM_POINTS = 200

# Calculation precision
DECIMAL_PRECISION = 4
```

---

## Testing

### Run All Tests

```bash
# Basic test run
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Verbose output
pytest -v

# Run specific test file
pytest tests/test_strategy.py

# Run tests matching pattern
pytest -k "test_iron_condor"
```

### Test Coverage

Verify test coverage meets requirements:

```bash
pytest --cov=src --cov-report=term-missing

# Expected output:
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# src/models/option.py                      120      8    93%   45-47
# src/calculators/black_scholes.py          95      10    89%   
# ...
# ---------------------------------------------------------------------
# TOTAL                                    1842    230    88%
```

### Integration Testing

Run integration tests:

```bash
pytest tests/ -m integration
```

### Example Validation

Validate examples run correctly:

```bash
python examples/usage_example.py
```

---

## Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY setup.py .

# Install package
RUN pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

CMD ["python"]
```

Build and run:

```bash
docker build -t optix-strategy-builder .
docker run -it optix-strategy-builder
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  strategy-builder:
    build: .
    volumes:
      - ./data:/app/data
    environment:
      - OPTIX_RISK_FREE_RATE=0.05
    restart: unless-stopped
```

### Kubernetes Deployment

Create `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: optix-strategy-builder
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
        image: optix/strategy-builder:latest
        resources:
          limits:
            memory: "2Gi"
            cpu: "1"
          requests:
            memory: "512Mi"
            cpu: "0.5"
        env:
        - name: OPTIX_RISK_FREE_RATE
          value: "0.05"
```

### AWS Lambda Deployment

Package for Lambda:

```bash
# Create deployment package
pip install -r requirements.txt -t package/
cp -r src/ package/
cd package
zip -r ../deployment-package.zip .
```

Lambda handler (`lambda_handler.py`):

```python
from src.api.strategy_api import StrategyAPI
import json

def lambda_handler(event, context):
    api = StrategyAPI()
    
    # Process event
    action = event.get('action')
    
    if action == 'create_strategy':
        result = api.create_from_template(**event['parameters'])
    elif action == 'analyze':
        result = api.get_strategy_analysis()
    
    return {
        'statusCode': 200,
        'body': json.dumps(result, default=str)
    }
```

---

## Integration

### REST API Integration

Example Flask wrapper:

```python
from flask import Flask, request, jsonify
from src.api.strategy_api import StrategyAPI

app = Flask(__name__)

@app.route('/api/strategy/create', methods=['POST'])
def create_strategy():
    data = request.json
    api = StrategyAPI()
    
    result = api.create_from_template(
        template_name=data['template'],
        underlying_symbol=data['symbol'],
        underlying_price=data['price'],
        expiration_date=data['expiration'],
        **data.get('parameters', {})
    )
    
    return jsonify(result)

@app.route('/api/strategy/analyze', methods=['POST'])
def analyze_strategy():
    # Implementation
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### WebSocket Integration

Example using Socket.IO:

```python
from flask import Flask
from flask_socketio import SocketIO, emit
from src.api.strategy_api import StrategyAPI

app = Flask(__name__)
socketio = SocketIO(app)
api = StrategyAPI()

@socketio.on('create_strategy')
def handle_create_strategy(data):
    result = api.create_from_template(**data)
    emit('strategy_created', result)

@socketio.on('update_price')
def handle_price_update(data):
    scenario = api.run_scenario_analysis(
        scenario_price=data['price']
    )
    emit('scenario_result', scenario)

if __name__ == '__main__':
    socketio.run(app, port=5000)
```

### Message Queue Integration

Example with Celery:

```python
from celery import Celery
from src.api.strategy_api import StrategyAPI

app = Celery('strategy_builder', broker='redis://localhost:6379/0')

@app.task
def analyze_strategy(strategy_data):
    api = StrategyAPI()
    api.import_strategy(strategy_data)
    
    return api.get_strategy_analysis()

@app.task
def batch_scenarios(strategy_data, prices):
    api = StrategyAPI()
    api.import_strategy(strategy_data)
    
    results = []
    for price in prices:
        scenario = api.run_scenario_analysis(scenario_price=price)
        results.append(scenario)
    
    return results
```

---

## Monitoring and Logging

### Application Logging

Configure logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strategy_builder.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('optix.strategy_builder')
```

### Performance Monitoring

Monitor key metrics:

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        logger.info(f"{func.__name__} took {duration:.3f}s")
        return result
    
    return wrapper

# Apply to API methods
api.get_strategy_analysis = monitor_performance(api.get_strategy_analysis)
```

### Health Checks

Implement health check endpoint:

```python
@app.route('/health')
def health_check():
    try:
        # Test basic functionality
        api = StrategyAPI()
        api.create_custom_strategy("Health Check")
        
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
```

---

## Troubleshooting

### Common Issues

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Install package in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
```

#### Calculation Errors

**Problem**: `ValueError: Expiration date must be in the future`

**Solution**: Ensure expiration dates are in the future:
```python
from datetime import datetime, timedelta
exp = (datetime.utcnow() + timedelta(days=30)).isoformat()
```

#### Memory Issues

**Problem**: High memory usage with large strategies

**Solution**: Reduce payoff diagram resolution:
```python
payoff = api.get_payoff_diagram(num_points=50)  # Instead of 200
```

#### Performance Issues

**Problem**: Slow calculations

**Solution**:
1. Reduce Monte Carlo simulations:
```python
# In risk_calculator.py
pop = RiskCalculator.calculate_probability_of_profit(
    strategy,
    num_simulations=100  # Instead of 1000
)
```

2. Use caching for repeated calculations

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with detailed output
api = StrategyAPI()
# ... operations will log debug information
```

### Support

For additional support:
- GitHub Issues: https://github.com/optix/visual-strategy-builder/issues
- Documentation: https://optix.readthedocs.io
- Email: support@optixtrading.com

---

## Security Considerations

### Input Validation

Always validate user inputs:

```python
def validate_price(price):
    if price <= 0:
        raise ValueError("Price must be positive")
    if price > 1000000:
        raise ValueError("Price exceeds maximum")
    return price
```

### Rate Limiting

Implement rate limiting for API endpoints:

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/strategy/create')
@limiter.limit("10 per minute")
def create_strategy():
    # ...
```

### API Authentication

Secure API endpoints:

```python
from functools import wraps
from flask import request

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != VALID_API_KEY:
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

---

## Performance Optimization

### Caching Results

Implement caching for expensive calculations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_greeks(option_hash):
    # Calculate Greeks
    pass
```

### Batch Processing

Process multiple strategies efficiently:

```python
def batch_analyze(strategies):
    results = []
    for strategy_data in strategies:
        api = StrategyAPI()
        api.import_strategy(strategy_data)
        results.append(api.get_strategy_analysis())
    return results
```

---

## Backup and Recovery

### Strategy Backup

Implement regular backups:

```bash
#!/bin/bash
# backup_strategies.sh

BACKUP_DIR="/backups/strategies"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/strategies_$DATE.tar.gz ./data/strategies/

# Keep only last 7 days
find $BACKUP_DIR -name "strategies_*.tar.gz" -mtime +7 -delete
```

### Disaster Recovery

Recovery procedure:

```bash
# Restore from backup
tar -xzf /backups/strategies/strategies_20240101_120000.tar.gz -C ./data/

# Verify integrity
python verify_strategies.py

# Restart service
systemctl restart strategy-builder
```

---

## Conclusion

This deployment guide provides comprehensive instructions for deploying the OPTIX Visual Strategy Builder in various environments. For additional assistance, consult the API documentation and examples.
