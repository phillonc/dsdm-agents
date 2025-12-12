# OPTIX Frontend

Options Trading Intelligence Platform - Web Frontend

## Quick Start

### Start the Frontend Server

```bash
cd /Users/phillonmorris/dsdm-agents/generated/optix/frontend
python3 -m http.server 3000
```

Then open http://localhost:3000 in your browser.

---

## Page URLs

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

---

## Test User Accounts

Use these credentials to test the platform (when backend is running):

| Email | Password | Description |
|-------|----------|-------------|
| `demo@optix.com` | `DemoPass123#` | Standard demo account |
| `trader@optix.com` | `Trader123#` | Active trader with positions |
| `admin@optix.com` | `Admin123#` | Admin account with full access |
| `test@example.com` | `Test1234#` | Basic test account |

**Note:** Passwords require: 8+ chars, uppercase, lowercase, number, and special character (`#`, `@`, `$`, etc.)

### Quick Login for Development

To bypass authentication during development, run this in browser console:
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

## Backend Services

The frontend connects to these backend APIs:

| Service | Port | Health Check |
|---------|------|--------------|
| OPTIX Main API | 8000 | http://localhost:8000/health |
| GEX Visualizer | 8001 | http://localhost:8001/health |
| Generative UI | 8004 | http://localhost:8004/health |

### Start All Backend Services

```bash
cd /Users/phillonmorris/dsdm-agents
./scripts/start_servers.sh
```

---

## Project Structure

```
frontend/
├── index.html                    # Landing page
├── README.md                     # This file
├── assets/
│   ├── css/
│   │   └── optix-design-system.css  # Design tokens & components
│   └── js/
│       ├── optix-data-bridge.js     # API communication layer
│       ├── auth.js                  # Authentication module
│       └── component-loader.js      # Dynamic component loading
├── pages/
│   ├── auth/
│   │   ├── login.html               # Login page
│   │   └── register.html            # Registration page
│   ├── dashboard.html               # Main dashboard
│   ├── watchlist.html               # Watchlist management
│   ├── options.html                 # Options chain viewer
│   ├── gex.html                     # GEX analysis
│   ├── strategies.html              # Options strategy builder
│   ├── flow.html                    # Options flow feed
│   ├── positions.html               # Portfolio positions
│   ├── performance.html             # Performance analytics
│   └── alerts.html                  # Alerts management
└── components/
    └── layout/
        ├── header.html              # App header with search
        └── sidebar.html             # Navigation sidebar
```

---

## Features

### Authentication
- Email/password login with JWT tokens
- Social login (Google OAuth)
- Password strength validation
- Session management with auto-refresh

### Dashboard
- Portfolio summary with P&L
- Quick quotes for watchlist symbols
- Market status indicator
- Recent alerts feed

### Watchlist
- Multiple watchlists support
- Real-time price updates via WebSocket
- Add/remove symbols
- Click-through to options chain

### Options Chain
- Traditional dual-column layout (Calls | Strike | Puts)
- ITM/ATM/OTM highlighting
- Strike range filtering
- IV Rank gauge
- URL parameter support (?symbol=AAPL)

### GEX Analysis
- Gamma Exposure heatmap
- Gamma flip level indicator
- Call/Put GEX breakdown
- Market maker positioning
- Historical GEX charts

### Strategies
- Pre-built strategy templates (Covered Call, Iron Condor, Spreads, etc.)
- Custom strategy builder with leg configuration
- Risk/reward visualization
- P&L calculator
- Save and load custom strategies

### Options Flow
- Real-time options order flow feed
- Bullish/bearish sentiment analysis
- Call/Put ratio tracking
- Unusual activity alerts
- Large block trade highlights
- Customizable filters

### Positions
- Open positions overview
- Real-time P&L tracking
- Position grouping by symbol
- Greeks display for options
- Close position functionality

### Performance
- Portfolio equity curve
- Monthly returns heatmap
- Win rate and trade statistics
- Performance by symbol/strategy
- Time-of-day analysis
- Key metrics (Sharpe ratio, max drawdown)

### Alerts
- Create price and activity alerts
- Multiple notification methods (Push, Email, SMS)
- Quick alert templates
- Alert history and statistics
- Pause/resume functionality

---

## Design System

The frontend uses CSS custom properties for theming:

```css
--optix-primary: #2563EB;      /* Primary blue */
--optix-bg-dark: #0F172A;      /* Dark background */
--optix-text: #F1F5F9;         /* Light text */
--optix-green: #22C55E;        /* Positive/profit */
--optix-red: #EF4444;          /* Negative/loss */
```

---

## API Configuration

Edit `assets/js/optix-data-bridge.js` to change API endpoints:

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000/api/v1',
  GEX_API_BASE: 'http://localhost:8001/api/v1',
  GENUI_API_BASE: 'http://localhost:8004/api/v1',
  WS_BASE: 'ws://localhost:8000/ws',
};
```

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Development

### Mock Authentication (No Backend)

```javascript
// Set in browser console to skip login
localStorage.setItem('optix_access_token', 'mock-token');
```

### Clear Authentication

```javascript
localStorage.removeItem('optix_access_token');
localStorage.removeItem('optix_refresh_token');
localStorage.removeItem('optix_user');
```

---

*OPTIX - Options Trading Intelligence Platform*
