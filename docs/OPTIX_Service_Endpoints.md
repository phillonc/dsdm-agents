# OPTIX Platform - Service Endpoints & Components

**Version:** 1.1 | **Date:** December 12, 2024

---

## Running Services

| Service | Port | Health Check | API Docs |
|---------|------|--------------|----------|
| **Frontend** | 3000 | http://localhost:3000/ | - |
| OPTIX Main API | 8000 | http://localhost:8000/health | http://localhost:8000/docs |
| GEX Visualizer | 8001 | http://localhost:8001/health | http://localhost:8001/api/docs |
| Generative UI | 8004 | http://localhost:8004/health | http://localhost:8004/docs |
| PostgreSQL | 5432 | - | - |
| Redis | 6379 | - | - |

---

## Frontend Pages (Port 3000)

### Start Frontend Server

```bash
cd /Users/phillonmorris/dsdm-agents/generated/optix/frontend
python3 -m http.server 3000
```

### Public Pages

| Page | URL | Description |
|------|-----|-------------|
| Landing Page | http://localhost:3000/ | Marketing landing page |
| Login | http://localhost:3000/pages/auth/login.html | User authentication |
| Register | http://localhost:3000/pages/auth/register.html | New user registration |

### Protected Pages (require authentication)

#### Main
| Page | URL | Description |
|------|-----|-------------|
| Dashboard | http://localhost:3000/pages/dashboard.html | Portfolio overview & market insights |
| Watchlist | http://localhost:3000/pages/watchlist.html | Symbol watchlist management |

#### Trading
| Page | URL | Description |
|------|-----|-------------|
| Options Chain | http://localhost:3000/pages/options.html | Options chain viewer |
| Options (with symbol) | http://localhost:3000/pages/options.html?symbol=AAPL | Pre-loaded symbol |
| GEX Analysis | http://localhost:3000/pages/gex.html | Gamma Exposure analysis |
| Strategies | http://localhost:3000/pages/strategies.html | Options strategy builder |
| Options Flow | http://localhost:3000/pages/flow.html | Real-time options order flow |

#### Portfolio
| Page | URL | Description |
|------|-----|-------------|
| Positions | http://localhost:3000/pages/positions.html | Open positions management |
| Performance | http://localhost:3000/pages/performance.html | Portfolio analytics & returns |
| Alerts | http://localhost:3000/pages/alerts.html | Price & activity alerts |

### Test User Accounts

| Email | Password | Description |
|-------|----------|-------------|
| `demo@optix.com` | `DemoPass123#` | Standard demo account |
| `trader@optix.com` | `Trader123#` | Active trader with positions |
| `admin@optix.com` | `Admin123#` | Admin account with full access |
| `test@example.com` | `Test1234#` | Basic test account |

**Password Requirements:** 8+ chars, uppercase, lowercase, number, special char (`#`, `@`, `$`)

### Development Bypass (No Backend Required)

Run in browser console to simulate authentication:
```javascript
localStorage.setItem('optix_access_token', 'dev-token-12345');
localStorage.setItem('optix_user', JSON.stringify({
  id: 'dev-user',
  email: 'dev@optix.com',
  name: 'Dev User'
}));
location.reload();
```

---

## OPTIX Main API (Port 8000)

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | http://localhost:8000/api/v1/auth/register | User registration |
| POST | http://localhost:8000/api/v1/auth/login | User login |
| POST | http://localhost:8000/api/v1/auth/refresh | Refresh access token |
| POST | http://localhost:8000/api/v1/auth/logout | User logout |
| POST | http://localhost:8000/api/v1/auth/mfa/setup | Setup MFA |
| POST | http://localhost:8000/api/v1/auth/mfa/verify | Verify MFA code |
| POST | http://localhost:8000/api/v1/auth/password-reset | Request password reset |

### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8000/api/v1/users/me | Get current user profile |
| PATCH | http://localhost:8000/api/v1/users/me | Update user profile |

### Watchlist Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8000/api/v1/watchlists | List all watchlists |
| POST | http://localhost:8000/api/v1/watchlists | Create watchlist |
| GET | http://localhost:8000/api/v1/watchlists/{id} | Get watchlist by ID |
| PATCH | http://localhost:8000/api/v1/watchlists/{id} | Update watchlist |
| DELETE | http://localhost:8000/api/v1/watchlists/{id} | Delete watchlist |
| POST | http://localhost:8000/api/v1/watchlists/{id}/symbols | Add symbol |
| DELETE | http://localhost:8000/api/v1/watchlists/{id}/symbols | Remove symbol |

### Market Data Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8000/api/v1/quotes/{symbol} | Get quote for symbol |
| GET | http://localhost:8000/api/v1/quotes | Get batch quotes |
| GET | http://localhost:8000/api/v1/options/expirations/{symbol} | Get options expirations |
| GET | http://localhost:8000/api/v1/options/chain/{symbol} | Get options chain |
| GET | http://localhost:8000/api/v1/historical/{symbol} | Get historical data |

### Alert Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | http://localhost:8000/api/v1/alerts | Create alert |
| GET | http://localhost:8000/api/v1/alerts | List alerts |
| GET | http://localhost:8000/api/v1/alerts/{id} | Get alert by ID |
| DELETE | http://localhost:8000/api/v1/alerts/{id} | Delete alert |
| PATCH | http://localhost:8000/api/v1/alerts/{id}/disable | Disable alert |
| PATCH | http://localhost:8000/api/v1/alerts/{id}/enable | Enable alert |

### Brokerage Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8000/api/v1/brokerages | List available brokerages |
| POST | http://localhost:8000/api/v1/brokerages/{id}/connect | Initiate OAuth |
| GET | http://localhost:8000/api/v1/brokerages/{id}/callback | OAuth callback |
| DELETE | http://localhost:8000/api/v1/brokerages/{id}/disconnect | Unlink account |
| GET | http://localhost:8000/api/v1/portfolio | Unified portfolio |
| GET | http://localhost:8000/api/v1/portfolio/positions | All positions |
| GET | http://localhost:8000/api/v1/portfolio/performance | P&L analytics |
| POST | http://localhost:8000/api/v1/portfolio/sync | Trigger manual sync |
| GET | http://localhost:8000/api/v1/transactions | Trade history |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| ws://localhost:8000/ws/quotes | Real-time quote stream |
| ws://localhost:8000/ws/portfolio | Real-time P&L stream |

---

## GEX Visualizer API (Port 8001)

### GEX Calculation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | http://localhost:8001/api/v1/gex/calculate | Calculate GEX from options chain |
| GET | http://localhost:8001/api/v1/gex/calculate/{symbol} | Calculate GEX with auto-fetched data |
| GET | http://localhost:8001/api/v1/gex/heatmap/{symbol} | Get GEX heatmap visualization data |
| GET | http://localhost:8001/api/v1/gex/gamma-flip/{symbol} | Get gamma flip level |
| GET | http://localhost:8001/api/v1/gex/market-maker/{symbol} | Get market maker positioning |

### Alert Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8001/api/v1/alerts/ | Get GEX alerts |
| GET | http://localhost:8001/api/v1/alerts/active | Get active alerts |
| GET | http://localhost:8001/api/v1/alerts/summary | Get alerts summary |
| POST | http://localhost:8001/api/v1/alerts/{id}/acknowledge | Acknowledge alert |

### Historical Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | http://localhost:8001/api/v1/historical/{symbol} | Get historical GEX data |
| GET | http://localhost:8001/api/v1/historical/{symbol}/summary | Get historical GEX statistics |
| GET | http://localhost:8001/api/v1/historical/{symbol}/chart | Get chart-ready GEX data |

---

## Generative UI API (Port 8004)

### Generation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | http://localhost:8004/api/v1/genui/generate | Generate UI from query |
| POST | http://localhost:8004/api/v1/genui/generate/stream | Stream generation progress |
| POST | http://localhost:8004/api/v1/genui/refine | Refine existing generation |
| GET | http://localhost:8004/api/v1/genui/history | Get generation history |
| POST | http://localhost:8004/api/v1/genui/favorite/{id} | Favorite a generation |
| GET | http://localhost:8004/api/v1/genui/components | List available components |

### WebSocket Endpoint

| Endpoint | Description |
|----------|-------------|
| ws://localhost:8004/ws/genui/{generation_id} | Real-time data for generated UI |

---

## Generative UI Components

### Data Components

| Component | Description | Props |
|-----------|-------------|-------|
| **OptionsChainTable** | Interactive options chain with calls/puts, Greeks, and real-time data | `symbol`, `expiration`, `columns`, `onStrikeSelect`, `highlightATM`, `showVolume` |
| **PositionCard** | Single position summary card with expandable details | `position`, `show_greeks`, `show_pnl`, `expandable` |
| **EarningsCalendar** | Upcoming earnings calendar with IV rank display | `symbols`, `date_range`, `show_iv`, `groupBy` |
| **FlowTicker** | Real-time unusual options flow ticker | `symbols`, `min_premium`, `flow_types`, `maxItems` |
| **QuoteCard** | Real-time stock quote card | `symbol`, `showExtended`, `showChart`, `compact` |
| **PortfolioSummary** | Portfolio overview with total value and P&L | `accounts`, `groupBy`, `showGreeks`, `showAllocations` |

### Visualization Components

| Component | Description | Props |
|-----------|-------------|-------|
| **GreeksGauges** | Visual gauges for Delta, Gamma, Theta, Vega | `greeks`, `ranges`, `format`, `showLabels`, `animated` |
| **PayoffDiagram** | Strategy payoff P&L chart | `legs`, `underlying_range`, `current_price`, `showBreakeven`, `showMaxPL` |
| **VolatilitySurface** | 3D implied volatility surface visualization | `symbol`, `expirations`, `strikes`, `colorScale`, `showGrid` |
| **GEXHeatmap** | Gamma exposure heatmap with gamma flip line | `symbol`, `expiration`, `color_scale`, `showFlipLine` |
| **IVRankGauge** | IV Rank/Percentile gauge with history | `symbol`, `showHistory`, `period` |
| **StrategyComparison** | Side-by-side strategy comparison | `strategies`, `metrics`, `showPayoffs` |

### Interactive Components

| Component | Description | Props |
|-----------|-------------|-------|
| **StrategyBuilder** | Drag-drop strategy leg builder | `symbol`, `available_legs`, `on_change`, `maxLegs` |
| **AlertConfigurator** | Alert setup interface | `symbol`, `alert_types`, `on_create`, `existing_alerts` |

### Educational Components

| Component | Description | Props |
|-----------|-------------|-------|
| **TradingEducation** | Educational component with animations | `topic`, `level`, `showExamples`, `interactive` |

---

## Example API Calls

### Generate UI

```bash
curl -X POST http://localhost:8004/api/v1/genui/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me AAPL options chain with high OI calls highlighted",
    "context": {"symbol": "AAPL", "current_price": 185.50}
  }'
```

### Calculate GEX

```bash
curl http://localhost:8001/api/v1/gex/calculate/SPY
```

### Get Options Chain

```bash
curl http://localhost:8000/api/v1/options/chain/AAPL
```

### Stream UI Generation

```bash
curl -X POST http://localhost:8004/api/v1/genui/generate/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query": "Show me SPY options for Friday expiry"}'
```

---

## Server Management

```bash
# Start all services
cd /Users/phillonmorris/dsdm-agents
./scripts/start_servers.sh

# Check status
./scripts/start_servers.sh status

# Stop all services
./scripts/start_servers.sh stop

# Start individual services
./scripts/start_servers.sh optix     # Port 8000
./scripts/start_servers.sh gex       # Port 8001

# Start Generative UI (manual)
cd /Users/phillonmorris/dsdm-agents/generated/optix
source genui_service/venv/bin/activate
GENUI_DEFAULT_LLM_PROVIDER=mock python -m uvicorn genui_service.api.app:app --port 8004
```

---

*Document generated: December 12, 2024*
