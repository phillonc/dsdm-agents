# OPTIX Generative UI Service

AI-powered dynamic interface generation for the OPTIX options trading platform. Creates custom, interactive experiences from natural language queries.

## Overview

The Generative UI Service implements VS-11 of the OPTIX platform, enabling users to describe desired interfaces in natural language and receive fully functional, interactive HTML/CSS/JS UIs rendered inline with chat responses.

Based on research from:
- [Generative UI: LLMs are Effective UI Generators](https://generativeui.github.io/) - Google Research
- [Generative Interfaces for Language Models](https://arxiv.org/html/2508.19227v2)

## Features

- **Natural Language UI Generation**: Describe what you want, get interactive UIs
- **Options Trading Components**: Pre-built library optimized for trading
- **Real-Time Data Integration**: Connect to live market data
- **Iterative Refinement**: Improve UIs with follow-up instructions
- **FSM-Based State Management**: Predictable component behavior
- **Security Sandboxing**: Safe execution in WebView

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GenUI Engine                              │
├─────────────────────────────────────────────────────────────────┤
│  1. Requirement Parser    →  Natural language → Structured spec  │
│  2. FSM Builder          →  Component state machines            │
│  3. Code Synthesizer     →  LLM-powered HTML/CSS/JS generation  │
│  4. Post-Processor       →  Security, styling, accessibility    │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
genui_service/
├── api/                    # FastAPI endpoints
│   ├── app.py             # Application factory
│   ├── router.py          # API routes
│   └── websocket.py       # Real-time updates
├── core/                   # Core engine modules
│   ├── engine.py          # Main orchestrator
│   ├── requirement_parser.py
│   ├── fsm_builder.py
│   ├── code_synthesizer.py
│   └── post_processor.py
├── llm/                    # LLM integration
│   ├── providers.py       # Anthropic, Google, OpenAI
│   └── prompts/           # System and generation prompts
├── components/             # Component library
│   └── registry.py        # Pre-built components
├── models/                 # Data models
│   ├── schemas.py         # Pydantic schemas
│   └── database.py        # SQLAlchemy models
├── data/                   # Data bridges
│   └── market_data_bridge.py
└── security/               # Security modules
```

## Quick Start

### Installation

```bash
cd generated/optix/genui_service
pip install -r requirements.txt
```

### Configuration

Set environment variables or create `.env`:

```bash
# LLM Provider (anthropic, google, openai, mock)
GENUI_DEFAULT_LLM_PROVIDER=mock

# API Keys (optional - uses mock if not set)
GENUI_ANTHROPIC_API_KEY=your-key
GENUI_GOOGLE_API_KEY=your-key
GENUI_OPENAI_API_KEY=your-key

# Server
GENUI_HOST=0.0.0.0
GENUI_PORT=8004
GENUI_DEBUG=true
```

### Running the Service

```bash
# Development
python -m uvicorn genui_service.api.app:app --reload --port 8004

# Or use the module
python -m genui_service.api.app
```

### API Documentation

When running in debug mode, access:
- Swagger UI: http://localhost:8004/docs
- ReDoc: http://localhost:8004/redoc

## API Usage

### Generate UI

```bash
curl -X POST http://localhost:8004/api/v1/genui/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me AAPL options chain with high OI calls highlighted",
    "context": {
      "symbol": "AAPL",
      "current_price": 185.50
    }
  }'
```

### Stream Generation

```bash
curl -X POST http://localhost:8004/api/v1/genui/generate/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "Show me SPY options for Friday expiry"
  }'
```

### Refine UI

```bash
curl -X POST http://localhost:8004/api/v1/genui/refine \
  -H "Content-Type: application/json" \
  -d '{
    "generation_id": "gen_abc123",
    "refinement": "Add the puts side and show delta values"
  }'
```

### List Components

```bash
curl http://localhost:8004/api/v1/genui/components
```

## Available Components

| Component | Description |
|-----------|-------------|
| OptionsChainTable | Interactive options chain with Greeks |
| GreeksGauges | Visual gauges for Delta, Gamma, Theta, Vega |
| PayoffDiagram | Strategy P&L chart |
| VolatilitySurface | 3D IV surface visualization |
| PositionCard | Position summary card |
| StrategyBuilder | Drag-drop strategy constructor |
| AlertConfigurator | Alert setup interface |
| EarningsCalendar | Earnings with IV display |
| GEXHeatmap | Gamma exposure heatmap |
| FlowTicker | Real-time unusual flow |

## WebSocket API

Connect for real-time data updates:

```javascript
const ws = new WebSocket('ws://localhost:8004/ws/genui/{generation_id}?token={token}');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'data_update') {
    updateUI(message.channel, message.data);
  }
};

// Subscribe to additional channels
ws.send(JSON.stringify({ action: 'subscribe', channel: 'quote:MSFT' }));
```

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=genui_service --cov-report=html
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Initial generation | < 30s (p95) |
| Incremental refinement | < 10s (p95) |
| UI render time | < 500ms |
| Real-time data latency | < 500ms |
| Generation success rate | > 95% |

## Security

- All generated code runs in sandboxed WebView
- CSP headers prevent XSS
- Blocked patterns: eval, innerHTML, external scripts
- Network requests proxied through data bridge
- Rate limiting: 20 generations/min per user

## License

Copyright (c) 2024 OPTIX. All rights reserved.
