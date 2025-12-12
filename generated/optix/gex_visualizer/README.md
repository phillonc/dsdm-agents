## # GEX Visualizer for OPTIX Trading Platform

[![Test Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](./htmlcov/index.html)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**VS-5: Gamma Exposure (GEX) Visualizer** - Professional-grade gamma exposure analytics and visualization platform for options trading.

## 🎯 Overview

The GEX Visualizer provides comprehensive gamma exposure analysis for options markets, helping traders understand market maker positioning, gamma flip levels, and pin risk dynamics. This tool is essential for understanding how dealer hedging impacts market volatility and price action.

## ✨ Key Features

### 1. **Gamma Exposure Calculations**
- Real-time GEX calculation across all strikes
- Separate tracking of call and put gamma exposure
- Net dealer gamma exposure computation
- Strike-by-strike gamma analysis

### 2. **Heatmap Visualization**
- Color-coded strike display (green = positive, red = negative)
- Visual identification of high gamma concentration zones
- Interactive heatmap data for charting
- Spot price overlay on gamma distribution

### 3. **Gamma Flip Level Detection**
- Automatic identification of gamma flip strikes
- Distance-to-flip calculations (absolute and percentage)
- Market regime classification (positive/negative/near-flip)
- Real-time flip level tracking

### 4. **Pin Risk Analysis**
- High open interest strike identification
- Max pain level calculations
- Pin risk scoring (0-1 scale)
- Days-to-expiration risk assessment
- Proximity-based pin risk alerts

### 5. **Market Maker Positioning**
- Dealer gamma exposure metrics
- Long/short gamma position identification
- Hedging pressure indicators (buy/sell/neutral)
- Vanna and charm exposure calculations
- Destabilizing position alerts

### 6. **Alert System**
- Gamma flip proximity alerts (critical/high/medium/low)
- High GEX concentration warnings
- Pin risk warnings near expiration
- Market regime change notifications
- Configurable severity thresholds

### 7. **Historical Data Storage**
- Daily GEX snapshots
- Historical trend analysis
- Statistical summaries (mean, median, percentiles)
- Regime distribution tracking
- Configurable retention period (default: 365 days)

### 8. **FastAPI REST Endpoints**
- RESTful API architecture
- Comprehensive endpoint documentation (OpenAPI/Swagger)
- Real-time GEX calculations
- Historical data retrieval
- Alert management
- Prometheus metrics integration

## 🏗️ Architecture

```
gex_visualizer/
├── src/
│   ├── core/              # Core calculation engines
│   │   ├── gex_calculator.py
│   │   ├── gamma_flip_detector.py
│   │   ├── pin_risk_analyzer.py
│   │   ├── market_maker_analyzer.py
│   │   └── alert_engine.py
│   ├── models/            # Data models
│   │   ├── schemas.py     # Pydantic schemas
│   │   └── database.py    # SQLAlchemy models
│   ├── services/          # Business logic
│   │   ├── gex_service.py
│   │   ├── storage_service.py
│   │   └── options_data_service.py
│   └── api/               # FastAPI application
│       ├── app.py
│       └── routers/
├── tests/
│   ├── unit/
│   └── integration/
├── config/
│   └── settings.py
└── docs/
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+ (for caching)

### Installation

```bash
# Clone the repository
cd generated/gex_visualizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql://gex_user:gex_pass@localhost:5432/gex_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# GEX Settings
RISK_FREE_RATE=0.05
GAMMA_FLIP_THRESHOLD_PCT=5.0
PIN_RISK_DAYS_TO_EXPIRY=5
HIGH_GEX_THRESHOLD=1000000000  # $1B

# Options Data API (optional)
OPTIONS_CHAIN_API_URL=https://api.example.com
OPTIONS_CHAIN_API_KEY=your_api_key_here
```

### Database Setup

```bash
# Create database
createdb gex_db

# Run migrations (if using Alembic)
alembic upgrade head
```

### Running the Application

```bash
# Development mode
python -m src.main

# Production mode with Uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- API Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Metrics: http://localhost:8000/metrics

## 📚 API Usage Examples

### Calculate GEX

```python
import httpx

# With provided options chain
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/gex/calculate",
        json={
            "symbol": "SPY",
            "spot_price": "450.00",
            "options_chain": [...],  # Your options data
            "calculate_pin_risk": True,
            "include_historical": True
        }
    )
    data = response.json()
```

### Get GEX for Symbol

```python
# Automatic options chain fetch
response = await client.get(
    "http://localhost:8000/api/v1/gex/calculate/SPY",
    params={"spot_price": "450.00"}
)
```

### Get Gamma Flip Level

```python
response = await client.get(
    "http://localhost:8000/api/v1/gex/gamma-flip/SPY"
)
```

### Get Active Alerts

```python
response = await client.get(
    "http://localhost:8000/api/v1/alerts/active"
)
```

### Get Historical Data

```python
response = await client.get(
    "http://localhost:8000/api/v1/historical/SPY",
    params={"days": 30}
)
```

## 🧪 Testing

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_gex_calculator.py -v
```

Current test coverage: **85%+**

## 📊 Key Concepts

### Gamma Exposure (GEX)

GEX represents the dollar amount market makers must hedge for a 1% move in the underlying. Formula:

```
GEX = Gamma × Open Interest × Spot² × 0.01
```

- **Positive GEX**: Market makers are long gamma → stabilizing (sell rallies, buy dips)
- **Negative GEX**: Market makers are short gamma → destabilizing (buy rallies, sell dips)

### Gamma Flip Level

The price level where net GEX crosses from negative to positive (or vice versa). This is a critical inflection point for market dynamics.

### Pin Risk

The tendency for the underlying price to gravitate toward strikes with high open interest near expiration, as market makers hedge their positions.

### Max Pain

The strike price where option holders (collectively) experience maximum loss at expiration.

## 🔧 Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `RISK_FREE_RATE` | 0.05 | Annual risk-free rate for calculations |
| `TRADING_DAYS_PER_YEAR` | 252 | Trading days for time decay |
| `GAMMA_FLIP_THRESHOLD_PCT` | 5.0 | Alert threshold for flip proximity |
| `PIN_RISK_DAYS_TO_EXPIRY` | 5 | Days threshold for pin risk analysis |
| `HIGH_GEX_THRESHOLD` | 1e9 | Dollar threshold for high GEX alerts |
| `HISTORICAL_DATA_DAYS` | 365 | Days of historical data to retain |

## 🐳 Docker Deployment

```bash
# Build image
docker build -t gex-visualizer:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  --name gex-visualizer \
  gex-visualizer:latest
```

## 📈 Monitoring

The application exposes Prometheus metrics at `/metrics`:

- Request counts and latencies
- GEX calculation times
- Alert generation rates
- Database query performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure test coverage remains above 85%
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Related Documentation

- [API Reference](./docs/api/README.md)
- [Architecture Guide](./docs/architecture/README.md)
- [User Guide](./docs/user-guides/README.md)
- [Deployment Guide](./docs/deployment.md)

## 📞 Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Email: dev@optix.trading
- Documentation: [docs-url]

---

**Built with ❤️ for the OPTIX Trading Platform**
