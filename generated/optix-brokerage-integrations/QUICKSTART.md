# Quick Start Guide

Get the OPTIX Brokerage Integrations service running in under 5 minutes.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+ (or Docker)
- Redis 7+ (or Docker)
- Git

## Step 1: Clone and Navigate

```bash
cd generated/optix-brokerage-integrations
```

## Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
# or: pip install -r requirements.txt
```

## Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Generate encryption key
make generate-key

# Edit .env and add:
# - Your brokerage API credentials
# - The generated encryption key
# - Database and Redis URLs
nano .env  # or use your preferred editor
```

## Step 4: Start Infrastructure (Docker)

If you don't have PostgreSQL and Redis installed:

```bash
# Create docker-compose.yml (minimal version)
cat > docker-compose.yml << EOF
version: '3.8'
services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: optix
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
EOF

# Start services
docker-compose up -d
```

## Step 5: Run the API Server

```bash
make run
# or: python -m uvicorn src.brokerage_service.api:app --reload
```

The API will be available at: **http://localhost:8000**

## Step 6: Test the API

Open your browser to:
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

Or use curl:

```bash
# Check health
curl http://localhost:8000/health

# List supported brokerages
curl http://localhost:8000/api/v1/brokerages
```

## Step 7: Run Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test suite
make test-unit
make test-security
```

## Quick Usage Example

### Connect a Brokerage (Python)

```python
import httpx
import asyncio

async def connect_fidelity():
    async with httpx.AsyncClient() as client:
        # Generate test user ID
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Initiate connection
        response = await client.post(
            "http://localhost:8000/api/v1/brokerages/fidelity/connect",
            params={"user_id": user_id}
        )
        data = response.json()
        print(f"Authorization URL: {data['authorization_url']}")
        
        # After OAuth completes, get portfolio
        portfolio = await client.get(
            "http://localhost:8000/api/v1/portfolio",
            params={"user_id": user_id}
        )
        print(f"Portfolio: {portfolio.json()}")

asyncio.run(connect_fidelity())
```

### Using the Makefile

```bash
# See all available commands
make help

# Development workflow
make install      # Install dependencies
make format       # Format code
make lint         # Check code quality
make test         # Run tests
make run          # Start server

# Docker workflow
make docker-build # Build image
make docker-up    # Start containers
make docker-logs  # View logs
make docker-down  # Stop containers

# Database
make db-migrate   # Run migrations
make db-rollback  # Rollback migration

# Utilities
make clean        # Clean up files
make docs         # List documentation
```

## Common Issues

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection
psql postgresql://postgres:password@localhost:5432/optix -c "SELECT 1"
```

### Redis Connection Error

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
```

### Import Errors

```bash
# Make sure you're in the virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt
```

## Project Structure

```
optix-brokerage-integrations/
├── src/
│   └── brokerage_service/
│       ├── api.py              # REST API endpoints
│       ├── models.py           # Data models
│       ├── sync_service.py     # Core sync logic
│       ├── repository.py       # Data access
│       ├── encryption.py       # Token encryption
│       ├── settings.py         # Configuration
│       └── connectors/         # Brokerage connectors
│           ├── base.py         # Abstract base
│           ├── fidelity.py     # Fidelity
│           ├── robinhood.py    # Robinhood
│           ├── ibkr.py         # Interactive Brokers
│           └── webull.py       # Webull
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── docs/                       # Documentation
├── .env.example               # Environment template
├── requirements.txt           # Dependencies
├── Makefile                   # Common commands
└── README.md                  # Main readme
```

## Next Steps

1. **Read the Documentation**
   - [README.md](README.md) - Overview and features
   - [docs/API_GUIDE.md](docs/API_GUIDE.md) - API reference
   - [docs/TECHNICAL_REQUIREMENTS.md](docs/TECHNICAL_REQUIREMENTS.md) - Full requirements
   - [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment

2. **Explore the API**
   - Visit http://localhost:8000/docs for interactive documentation
   - Try the example requests
   - Test OAuth flows with your brokerage credentials

3. **Review the Code**
   - Start with `src/brokerage_service/api.py` to understand endpoints
   - Look at `src/brokerage_service/connectors/fidelity.py` as an example connector
   - Review `src/brokerage_service/sync_service.py` for portfolio logic

4. **Run the Tests**
   - Execute `make test` to see all tests pass
   - Check coverage with `make coverage`
   - Review test files in `tests/` to understand usage

5. **Deploy**
   - Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production setup
   - Use Docker or Kubernetes
   - Configure monitoring and backups

## Getting Help

- **Documentation:** Check the `docs/` directory
- **Examples:** See code examples in API_GUIDE.md
- **Issues:** Report bugs or request features on GitHub
- **Tests:** Look at test files for usage examples

## Development Tips

1. **Use the Makefile** - It has shortcuts for common tasks
2. **Keep tests running** - Run `make test` frequently
3. **Format your code** - Run `make format` before committing
4. **Check coverage** - Maintain 85%+ coverage
5. **Read the TRD** - Technical Requirements Document has all specs

## Production Checklist

Before deploying to production:

- [ ] All API credentials configured
- [ ] Encryption key generated and secured
- [ ] Database migrations run
- [ ] Redis configured
- [ ] Environment variables set
- [ ] HTTPS configured
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] Health checks working
- [ ] Rate limiting enabled

## Resources

- **API Docs:** http://localhost:8000/docs
- **GitHub:** https://github.com/phillonc/dsdm-agents
- **Support:** support@optix.app

---

**You're all set!** The API is running and ready for development. 🚀
