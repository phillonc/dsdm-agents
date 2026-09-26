# OPTIX Brokerage Integrations

Universal brokerage integration service for the OPTIX trading platform. Supports connecting to multiple brokerages with OAuth 2.0 authentication and provides unified portfolio management.

## Features

### Supported Brokerages

- ✅ **Charles Schwab / TD Ameritrade** - OAuth 2.0
- ✅ **Fidelity** - OAuth 2.0
- ✅ **Robinhood** - Plaid Integration
- ✅ **Interactive Brokers (IBKR)** - OAuth 2.0 / Client Portal API
- ✅ **Webull** - OAuth 2.0

### Core Capabilities

- **Universal Portfolio Sync** - Aggregate positions across all connected brokerages
- **Complete Cash Tracking** - Total cash calculation with margin adjustments
- **Realized P&L Calculation** - Track profits from closed positions, dividends, and interest
- **Day P&L Calculation** - Real-time day change with start-of-day snapshots
- **Transaction History** - Comprehensive transaction tracking across all accounts
- **Security Hardening** - CSRF protection, token encryption, and secure token revocation

## Architecture

```
┌─────────────────────────────────────────────────┐
│           FastAPI REST API                      │
│         /api/v1/brokerages/*                    │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│         PortfolioSyncService                    │
│  • sync_account()                               │
│  • sync_all_accounts()                          │
│  • get_unified_portfolio()                      │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│        BrokerageConnector (Abstract)            │
└─────────────────────────────────────────────────┘
        │       │       │       │       │
        ▼       ▼       ▼       ▼       ▼
    Schwab  Fidelity Robinhood IBKR  Webull
```

## Installation

```bash
# Clone repository
git clone https://github.com/phillonc/dsdm-agents.git
cd dsdm-agents/generated/optix-brokerage-integrations

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```bash
# Schwab/TD Ameritrade
SCHWAB_CLIENT_ID=your_client_id
SCHWAB_CLIENT_SECRET=your_client_secret
SCHWAB_REDIRECT_URI=https://yourdomain.com/oauth/callback/schwab

# Fidelity
FIDELITY_CLIENT_ID=your_client_id
FIDELITY_CLIENT_SECRET=your_client_secret
FIDELITY_REDIRECT_URI=https://yourdomain.com/oauth/callback/fidelity

# Plaid (for Robinhood)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=production

# Interactive Brokers
IBKR_CLIENT_ID=your_client_id
IBKR_CLIENT_SECRET=your_client_secret
IBKR_USE_GATEWAY=false

# Webull
WEBULL_CLIENT_ID=your_client_id
WEBULL_CLIENT_SECRET=your_client_secret

# Security
TOKEN_ENCRYPTION_KEY=your_32_byte_base64_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql://localhost/optix
```

## Usage

### Start the API Server

```bash
python -m src.brokerage_service.api
```

API will be available at `http://localhost:8000`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### Key Endpoints

#### List Supported Brokerages
```
GET /api/v1/brokerages
```

#### Connect a Brokerage
```
POST /api/v1/brokerages/{provider}/connect?user_id={uuid}
```

#### OAuth Callback
```
GET /api/v1/brokerages/{provider}/callback?code={code}&state={state}
```

#### Get Unified Portfolio
```
GET /api/v1/portfolio?user_id={uuid}
```

#### Sync Portfolio
```
POST /api/v1/portfolio/sync?user_id={uuid}
```

#### Disconnect Brokerage
```
DELETE /api/v1/brokerages/{connection_id}/disconnect?user_id={uuid}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_fidelity_connector.py

# Run integration tests only
pytest tests/integration/
```

## Security Features

### CSRF Protection
- OAuth state parameter generated as UUID
- State stored in Redis with 10-minute TTL
- State validated and deleted on callback (one-time use)

### Token Encryption
- All OAuth tokens encrypted at rest using Fernet (AES-128)
- Encryption key derived using PBKDF2
- Tokens only decrypted in memory when needed

### Token Revocation
- Tokens revoked with brokerage on disconnect
- All associated data deleted on disconnection
- Graceful handling of revocation failures

## Portfolio Logic

### Total Cash Calculation
```python
total_cash = sum(account.cash - account.margin_balance for account in accounts)
```

### Realized P&L Calculation
Includes:
- Sale proceeds minus cost basis for closed positions
- Dividends and interest
- Option premiums for expired/assigned/exercised options
- Trading fees subtracted

### Day P&L Calculation
```python
day_pl = current_value - start_of_day_value + withdrawals - deposits
day_pl_percent = (day_pl / start_of_day_value) * 100
```

Start-of-day snapshots captured at 9:30 AM ET (market open).

## Development

### Project Structure
```
src/brokerage_service/
├── __init__.py
├── api.py                  # FastAPI REST API
├── models.py               # Pydantic data models
├── repository.py           # Data access layer
├── sync_service.py         # Portfolio sync logic
├── settings.py             # Configuration
├── encryption.py           # Token encryption
└── connectors/
    ├── base.py            # Abstract base class
    ├── schwab.py          # Schwab connector
    ├── fidelity.py        # Fidelity connector
    ├── robinhood.py       # Robinhood/Plaid connector
    ├── ibkr.py            # Interactive Brokers connector
    └── webull.py          # Webull connector

tests/
├── unit/
│   ├── test_fidelity_connector.py
│   ├── test_portfolio_logic.py
│   └── test_security.py
└── integration/
    └── test_brokerage_integration.py
```

### Adding a New Brokerage

1. Create connector class inheriting from `BrokerageConnector`
2. Implement all abstract methods
3. Add to connector map in `sync_service.py`
4. Update settings with API credentials
5. Write unit and integration tests

Example:
```python
from .base import BrokerageConnector

class NewBrokerConnector(BrokerageConnector):
    async def authenticate(self, authorization_code: str):
        # Implement OAuth flow
        pass
    
    async def get_positions(self):
        # Fetch positions
        pass
    
    # ... implement other methods
```

## Performance

- Position sync: < 30 seconds per account
- Portfolio calculation: < 2 seconds
- OAuth connection: < 60 seconds
- Concurrent syncs supported for multiple accounts

## Monitoring

Key metrics to monitor:
- Connection success rate
- Sync reliability
- Portfolio calculation accuracy
- API response times
- Token refresh success rate

## License

Copyright © 2025 OPTIX Trading Platform

## Support

For issues and questions:
- GitHub Issues: https://github.com/phillonc/dsdm-agents/issues
- Email: support@optix.app

## Version

Current Version: 1.0.0

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

## Changelog

### v1.0.0 (2025-12-16)
- Initial release
- Support for 5 major brokerages
- Complete portfolio logic implementation
- Security hardening (CSRF, encryption, token revocation)
- Comprehensive test suite
