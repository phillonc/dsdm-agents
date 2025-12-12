# OPTIX Adaptive Intelligence Engine

AI-powered pattern recognition and analysis system for options trading, providing real-time insights, personalized recommendations, and intelligent alerts.

## Overview

The Adaptive Intelligence Engine is the core AI component of the OPTIX Trading Platform, designed to:

- **Detect Chart Patterns**: Identify technical patterns like head & shoulders, double tops/bottoms, triangles, flags, and breakouts
- **Analyze Options Activity**: Detect unusual options volume, sweeps, and golden sweeps
- **Forecast Volatility**: Predict volatility changes using EWMA and GARCH models
- **Analyze Sentiment**: Aggregate sentiment from multiple sources (options flow, news, market breadth)
- **Generate Personalized Insights**: Learn user trading patterns and provide customized recommendations
- **Deliver Real-time Alerts**: Trigger intelligent alerts across multiple channels

## Features

### 1. Pattern Recognition Service

- **Chart Patterns**: Head & Shoulders, Double Top/Bottom, Triangles, Flags, Wedges, Breakouts
- **Support/Resistance Levels**: Automatic identification of key price levels
- **Unusual Options Activity**: Volume spikes, sweeps, golden sweeps, OI changes
- **Volume Anomalies**: Spikes, divergence, climax, accumulation/distribution

### 2. AI Analysis Service

- **Price Prediction**: ML-based price forecasting with confidence intervals
- **Volatility Forecasting**: EWMA and GARCH models for volatility prediction
- **Sentiment Analysis**: Multi-source sentiment aggregation and analysis
- **Market Context**: Overall market regime and trend analysis

### 3. Personalization Service

- **Pattern Learning**: Automatically learn from user's trading history
- **Custom Insights**: Generate personalized trading opportunities and warnings
- **Performance Tracking**: Track and analyze user's trading performance
- **Educational Content**: Provide context-aware learning materials

### 4. Alert Service

- **Multi-Channel Delivery**: In-app, email, SMS, push notifications, webhooks
- **Smart Prioritization**: Priority-based alert delivery
- **Deduplication**: Prevent alert fatigue with intelligent deduplication
- **Custom Filters**: User-configurable alert conditions and thresholds

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│  Patterns API  │ Analysis API │ Personalization │ Alerts   │
├─────────────────────────────────────────────────────────────┤
│                     Service Layer                            │
├──────────────────┬──────────────┬──────────────┬───────────┤
│ Pattern          │ AI Analysis  │Personalization│  Alert   │
│ Recognition      │   Service    │   Service     │ Service  │
├──────────────────┴──────────────┴──────────────┴───────────┤
│                      Data Models                             │
├─────────────────────────────────────────────────────────────┤
│  Pattern Models  │Analysis Models│User Models │Alert Models│
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.9+
- Redis (for caching)
- MongoDB (for data persistence)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd optix_adaptive_intelligence
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
```bash
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

4. Run the application:
```bash
python -m src.main
```

Or using uvicorn directly:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

### API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Pattern Detection

```python
import requests

# Detect chart patterns
response = requests.post(
    "http://localhost:8000/api/v1/patterns/detect/chart",
    params={"symbol": "AAPL"}
)
patterns = response.json()
```

### Price Prediction

```python
# Generate price predictions
response = requests.post(
    "http://localhost:8000/api/v1/analysis/predict",
    params={
        "symbol": "AAPL",
        "time_horizon": "1W"
    }
)
signals = response.json()
```

### Personalized Insights

```python
# Get personalized insights
response = requests.post(
    "http://localhost:8000/api/v1/personalization/insights/user_123/generate",
    params={"max_insights": 10}
)
insights = response.json()
```

### Alert Configuration

```python
# Create alert configuration
response = requests.post(
    "http://localhost:8000/api/v1/alerts/config/user_123",
    json={
        "enabled": True,
        "alert_type": "pattern_detected",
        "min_confidence": 0.8,
        "preferred_channels": ["in_app", "push"]
    }
)
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_pattern_recognition.py

# Run integration tests only
pytest tests/integration/
```

## Configuration

Key configuration options in `config/config.yaml`:

### Pattern Recognition
- `min_confidence`: Minimum confidence threshold (0.0-1.0)
- `lookback_periods`: Historical periods to analyze
- `volume_threshold_multiplier`: Volume spike detection threshold

### AI Analysis
- `model_type`: ML model type (random_forest, xgboost, etc.)
- `n_estimators`: Number of trees for ensemble models
- `min_samples`: Minimum samples required for training

### Personalization
- `min_sample_size`: Minimum trades to learn patterns
- `learning_window_days`: Days of history to analyze
- `relevance_threshold`: Minimum relevance score for insights

### Alerts
- `max_retries`: Maximum delivery retry attempts
- `deduplication_window`: Time window for deduplication (seconds)
- `default_max_per_day`: Default daily alert limit

## API Endpoints

### Pattern Recognition
- `POST /api/v1/patterns/detect/chart` - Detect chart patterns
- `POST /api/v1/patterns/detect/support-resistance` - Find support/resistance levels
- `POST /api/v1/patterns/detect/unusual-options` - Detect unusual options activity
- `POST /api/v1/patterns/detect/volume-anomalies` - Detect volume anomalies

### AI Analysis
- `POST /api/v1/analysis/predict` - Generate price predictions
- `POST /api/v1/analysis/volatility/forecast` - Forecast volatility
- `POST /api/v1/analysis/sentiment` - Analyze sentiment
- `POST /api/v1/analysis/market-context` - Analyze market context

### Personalization
- `GET /api/v1/personalization/profile/{user_id}` - Get user profile
- `POST /api/v1/personalization/patterns/{user_id}/learn` - Learn trading patterns
- `POST /api/v1/personalization/insights/{user_id}/generate` - Generate insights
- `GET /api/v1/personalization/statistics/{user_id}` - Get user statistics

### Alerts
- `GET /api/v1/alerts/user/{user_id}` - Get user alerts
- `POST /api/v1/alerts/config/{user_id}` - Create alert configuration
- `POST /api/v1/alerts/test/{user_id}` - Send test alert

## Performance

The system is designed for high performance:

- **Pattern Detection**: < 500ms for 100 periods of data
- **Price Prediction**: < 1s for ML-based forecasts
- **Alert Delivery**: < 200ms average delivery time
- **Concurrent Requests**: Supports 100+ req/s with 4 workers

## Monitoring

### Metrics

Key metrics exposed via Prometheus:
- Pattern detection count and latency
- Prediction accuracy over time
- Alert delivery success rate
- API request count and latency

### Logging

Structured JSON logging includes:
- Request/response details
- Service operation timing
- Error tracking and stack traces
- User action audit trail

## Security

- **API Key Authentication**: Required for all endpoints
- **Rate Limiting**: 100 requests per minute per API key
- **Data Encryption**: AES-256-GCM for sensitive data
- **Input Validation**: Comprehensive validation using Pydantic

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Copyright © 2024 OPTIX Trading Platform. All rights reserved.

## Support

For support and questions:
- Documentation: `/docs` endpoint
- Issues: GitHub Issues
- Email: support@optix-trading.com

## Roadmap

### Q1 2024
- [x] Core pattern recognition
- [x] Basic ML predictions
- [x] Personalization engine
- [x] Multi-channel alerts

### Q2 2024
- [ ] Deep learning models (LSTM, Transformer)
- [ ] Real-time streaming analysis
- [ ] Advanced sentiment (NLP with FinBERT)
- [ ] Backtesting framework

### Q3 2024
- [ ] Reinforcement learning for strategy optimization
- [ ] Multi-asset correlation analysis
- [ ] Advanced risk modeling
- [ ] Mobile app integration

## Acknowledgments

Built with:
- FastAPI - Modern web framework
- scikit-learn - ML algorithms
- pandas/numpy - Data processing
- scipy - Statistical analysis
- pytest - Testing framework
