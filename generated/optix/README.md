# OPTIX Trading Platform

**Version:** 1.0.0 | **Updated:** December 2025

A comprehensive options trading intelligence platform providing institutional-grade tools for retail traders. Built with modern microservices architecture and AI-powered analytics.

---

## Platform Overview

OPTIX (Options Trading Intelligence eXchange) is a mobile-first platform that democratizes professional options trading tools. The platform consists of multiple specialized services that work together to provide real-time market data, advanced analytics, and intelligent trading assistance.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (Port 3000)                            │
│                    Static HTML/CSS/JS + GenUI Components                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   OPTIX Main    │   │  GEX Visualizer │   │  Generative UI  │
│   API (8000)    │   │     (8001)      │   │     (8004)      │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                   ┌───────────┴───────────┐
                   │                       │
                   ▼                       ▼
           ┌──────────────┐       ┌──────────────┐
           │  PostgreSQL  │       │    Redis     │
           │   (5432)     │       │   (6379)     │
           └──────────────┘       └──────────────┘
```

---

## Services & Components

### Running Services

| Service | Port | Description | Status |
|---------|------|-------------|--------|
| **Frontend** | 3000 | Web interface with 11 pages | Active |
| **OPTIX Main API** | 8000 | Core platform API (auth, quotes, portfolio) | Active |
| **GEX Visualizer** | 8001 | Gamma exposure analytics | Active |
| **Generative UI** | 8004 | AI-powered dynamic UI generation | Active |
| **PostgreSQL** | 5432 | Primary database | Active |
| **Redis** | 6379 | Caching and sessions | Active |

### Component Modules

| Module | Description | Key Features |
|--------|-------------|--------------|
| [optix-trading-platform](./optix-trading-platform/) | Core platform foundation | Auth, market data, portfolio sync |
| [gex_visualizer](./gex_visualizer/) | Gamma exposure analytics | GEX calculations, heatmaps, alerts |
| [genui_service](./genui_service/) | AI UI generation | Natural language to UI, 15+ components |
| [frontend](./frontend/) | Web application | 11 trading pages, real-time updates |
| [optix_backtester](./optix_backtester/) | Strategy backtesting | Monte Carlo, walk-forward optimization |
| [optix_visual_strategy_builder](./optix_visual_strategy_builder/) | Options strategy builder | Payoff diagrams, Greeks analysis |
| [optix_volatility_compass](./optix_volatility_compass/) | IV analytics | IV rank, skew analysis, term structure |
| [vs9_smart_alerts](./vs9_smart_alerts/) | Intelligent alerts | Multi-condition triggers, ML relevance |
| [vs10_trading_journal_ai](./vs10_trading_journal_ai/) | AI trading journal | Auto trade capture, pattern discovery |
| [optix_adaptive_intelligence](./optix_adaptive_intelligence/) | AI pattern recognition | Market prediction, anomaly detection |
| [optix_collective_intelligence](./optix_collective_intelligence/) | Social trading | Sentiment aggregation, community signals |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (via Docker or Homebrew)
- Redis 7.0+ (via Docker or Homebrew)
- Docker Desktop (recommended for infrastructure)

### Start All Services (One Command)

```bash
# From dsdm-agents root directory
cd /Users/phillonmorris/dsdm-agents

# Start everything: PostgreSQL, Redis, Frontend, OPTIX API, GEX
./scripts/start_servers.sh

# Check status of all services
./scripts/start_servers.sh status

# Stop all services
./scripts/start_servers.sh stop
```

The script automatically:
- Starts PostgreSQL (Docker or Homebrew)
- Starts Redis (Docker or Homebrew)
- Installs missing dependencies (e.g., `psycopg2-binary`)
- Kills conflicting processes on ports
- Starts all API servers in the background
- Logs output to `logs/` directory

### Server Management Commands

| Command | Description |
|---------|-------------|
| `./scripts/start_servers.sh` | Start all services |
| `./scripts/start_servers.sh status` | Check service status |
| `./scripts/start_servers.sh stop` | Stop all services |
| `./scripts/start_servers.sh frontend` | Start only Frontend (port 3000) |
| `./scripts/start_servers.sh optix` | Start only OPTIX API (port 8000) |
| `./scripts/start_servers.sh gex` | Start only GEX Visualizer (port 8001) |
| `./scripts/start_servers.sh infra` | Start only PostgreSQL + Redis |
| `./scripts/start_servers.sh logs optix` | View OPTIX API logs |
| `./scripts/start_servers.sh logs frontend` | View Frontend logs |
| `./scripts/start_servers.sh help` | Show all commands |

### Start Individual Services (Manual)

```bash
# Start frontend only (Port 3000)
cd /Users/phillonmorris/dsdm-agents/generated/optix/frontend
python3 -m http.server 3000

# Start main API only (Port 8000)
cd /Users/phillonmorris/dsdm-agents/generated/optix/optix-trading-platform
pip install psycopg2-binary  # Required for PostgreSQL
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Start GEX service only (Port 8001)
cd /Users/phillonmorris/dsdm-agents/generated/optix/gex_visualizer
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8001

# Start Generative UI only (Port 8004)
cd /Users/phillonmorris/dsdm-agents/generated/optix/genui_service
source venv/bin/activate
GENUI_DEFAULT_LLM_PROVIDER=mock python -m uvicorn genui_service.api.app:app --port 8004
```

### Default Credentials

After starting the services, use these test accounts:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@optix.io` | `Admin123!` |
| User | `test@optix.io` | `Test123!` |

**Note:** The API uses PostgreSQL for persistent storage. Users and data persist across server restarts. Seeded users (`admin@optix.io`, `test@optix.io`) are available after database initialization.

---

## Frontend Pages

### Public Pages
| Page | URL |
|------|-----|
| Landing Page | http://localhost:3000/ |
| Login | http://localhost:3000/pages/auth/login.html |
| Register | http://localhost:3000/pages/auth/register.html |

### Protected Pages
| Page | URL | Description |
|------|-----|-------------|
| Dashboard | http://localhost:3000/pages/dashboard.html | Portfolio overview |
| Watchlist | http://localhost:3000/pages/watchlist.html | Symbol management |
| Options Chain | http://localhost:3000/pages/options.html | Options viewer |
| GEX Analysis | http://localhost:3000/pages/gex.html | Gamma exposure |
| Strategies | http://localhost:3000/pages/strategies.html | Strategy builder |
| Options Flow | http://localhost:3000/pages/flow.html | Order flow feed |
| Positions | http://localhost:3000/pages/positions.html | Open positions |
| Performance | http://localhost:3000/pages/performance.html | Analytics |
| Alerts | http://localhost:3000/pages/alerts.html | Alert management |

### Test Accounts

| Email | Password | Description |
|-------|----------|-------------|
| `demo@optix.com` | `DemoPass123#` | Standard demo |
| `trader@optix.com` | `Trader123#` | Active trader |
| `admin@optix.com` | `Admin123#` | Admin access |

---

## API Documentation

### Health Checks

```bash
# Main API
curl http://localhost:8000/health

# GEX Visualizer
curl http://localhost:8001/health

# Generative UI
curl http://localhost:8004/health
```

### Interactive API Docs

| Service | Swagger UI | ReDoc |
|---------|------------|-------|
| Main API | http://localhost:8000/docs | http://localhost:8000/redoc |
| GEX | http://localhost:8001/api/docs | http://localhost:8001/api/redoc |
| GenUI | http://localhost:8004/docs | http://localhost:8004/redoc |

### Key Endpoints

**Authentication**
```bash
POST http://localhost:8000/api/v1/auth/register
POST http://localhost:8000/api/v1/auth/login
POST http://localhost:8000/api/v1/auth/refresh
```

**Market Data**
```bash
GET http://localhost:8000/api/v1/quotes/{symbol}
GET http://localhost:8000/api/v1/options/chain/{symbol}
```

**GEX Analysis**
```bash
GET http://localhost:8001/api/v1/gex/calculate/{symbol}
GET http://localhost:8001/api/v1/gex/gamma-flip/{symbol}
GET http://localhost:8001/api/v1/gex/heatmap/{symbol}
```

**Generative UI**
```bash
POST http://localhost:8004/api/v1/genui/generate
GET http://localhost:8004/api/v1/genui/components
```

---

## Development

### Project Structure

```
generated/optix/
├── README.md                          # This file
├── frontend/                          # Web application (11 pages)
│   ├── index.html                     # Landing page
│   ├── assets/                        # CSS, JS
│   ├── pages/                         # Application pages
│   └── components/                    # Reusable components
├── optix-trading-platform/            # Core API (VS-0, VS-7)
├── gex_visualizer/                    # GEX analytics (VS-5)
├── genui_service/                     # AI UI generation (VS-11)
├── optix_backtester/                  # Backtesting (VS-6)
├── optix_visual_strategy_builder/     # Strategy builder (VS-3)
├── optix_volatility_compass/          # IV analytics (VS-8)
├── vs9_smart_alerts/                  # Smart alerts (VS-9)
├── vs10_trading_journal_ai/           # Trading journal (VS-10)
├── optix_adaptive_intelligence/       # AI engine (VS-1)
├── optix_collective_intelligence/     # Social trading (VS-4)
└── genui_output.html                  # Sample GenUI output
```

### Running Tests

```bash
# Run tests for individual services
cd generated/optix/gex_visualizer
pytest --cov=src --cov-report=html

cd generated/optix/optix_backtester
pytest --cov=src --cov-report=term

cd generated/optix/genui_service
pytest tests/ -v
```

### Environment Configuration

Create `.env` files in each service directory:

```bash
# Common settings
DATABASE_URL=postgresql://optix:optix@localhost:5432/optix_db
REDIS_URL=redis://localhost:6379/0

# Main API
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# GEX Visualizer
RISK_FREE_RATE=0.05
GAMMA_FLIP_THRESHOLD_PCT=5.0

# Generative UI
GENUI_DEFAULT_LLM_PROVIDER=mock  # or anthropic, openai, google
GENUI_ANTHROPIC_API_KEY=your-key
```

---

## Feature Modules (Vertical Slices)

| VS | Module | Status | Description |
|----|--------|--------|-------------|
| VS-0 | Core Foundation | Production | Auth, quotes, watchlists |
| VS-1 | Adaptive Intelligence | Active | AI pattern recognition |
| VS-3 | Visual Strategy Builder | Active | Options strategy builder |
| VS-4 | Collective Intelligence | Active | Social trading signals |
| VS-5 | GEX Visualizer | Production | Gamma exposure analytics |
| VS-6 | Time Machine Backtester | Active | Strategy backtesting |
| VS-7 | Brokerage Sync | Production | Multi-broker integration |
| VS-8 | Volatility Compass | Active | IV analytics |
| VS-9 | Smart Alerts | Active | Intelligent alerting |
| VS-10 | Trading Journal AI | Active | AI-powered journal |
| VS-11 | Generative UI | Production | Dynamic UI generation |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, Pydantic |
| **Database** | PostgreSQL 15, SQLAlchemy |
| **Cache** | Redis 7.0 |
| **Frontend** | HTML5, CSS3, JavaScript |
| **AI/ML** | Anthropic Claude, OpenAI, Google Gemini |
| **Testing** | pytest, 85%+ coverage |
| **Container** | Docker, Kubernetes (EKS) |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| API Response (p95) | < 200ms reads, < 500ms writes |
| Real-time Data Latency | < 500ms |
| Options Chain Load | < 2 seconds |
| GenUI Generation | < 30 seconds |
| Concurrent Users | 100K supported |
| Uptime (Market Hours) | 99.9% |

---

## Security

- JWT authentication with 15-minute token expiry
- MFA support via TOTP
- AES-256 encryption at rest
- TLS 1.3 in transit
- CSP headers for XSS prevention
- Rate limiting (20 requests/min for GenUI)

---

## Documentation

- [Service Endpoints](../../docs/OPTIX_Service_Endpoints.md) - Complete API reference
- [Frontend README](./frontend/README.md) - Frontend documentation
- [GEX Visualizer](./gex_visualizer/README.md) - GEX service details
- [Generative UI](./genui_service/README.md) - GenUI service details
- [Backtester](./optix_backtester/README.md) - Backtesting documentation

---

## Support

- **Issues:** https://github.com/optix/trading-platform/issues
- **Documentation:** https://docs.optix.com
- **Email:** support@optix.com

---

**Built with DSDM Atern methodology by the OPTIX Engineering Team**

*Copyright 2025 OPTIX Trading Platform. All rights reserved.*
