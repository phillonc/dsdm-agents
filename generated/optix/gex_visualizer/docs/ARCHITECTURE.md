# GEX Visualizer Architecture

## System Architecture Overview

The GEX Visualizer follows a layered architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ GEX Router   │  │Alert Router  │  │Historical    │     │
│  │              │  │              │  │Router        │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ GEX Service  │  │Storage       │  │Options Data  │     │
│  │              │  │Service       │  │Service       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Engines                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │GEX         │ │Gamma Flip  │ │Pin Risk    │             │
│  │Calculator  │ │Detector    │ │Analyzer    │             │
│  └────────────┘ └────────────┘ └────────────┘             │
│  ┌────────────┐ ┌────────────┐                            │
│  │Market Maker│ │Alert       │                            │
│  │Analyzer    │ │Engine      │                            │
│  └────────────┘ └────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────────┐       ┌──────────────────┐          │
│  │   PostgreSQL     │       │      Redis       │          │
│  │   (Persistence)  │       │     (Cache)      │          │
│  └──────────────────┘       └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### API Layer

**FastAPI Application**
- Async request handling
- OpenAPI/Swagger documentation
- CORS middleware
- Prometheus metrics endpoint
- Health check endpoint

**Routers**
- `gex.py`: GEX calculation endpoints
- `alerts.py`: Alert management endpoints
- `historical.py`: Historical data endpoints

### Service Layer

**GEXService**
- Orchestrates GEX calculations
- Coordinates core engines
- Manages data persistence
- Generates comprehensive analysis

**StorageService**
- Async database operations
- CRUD for snapshots, alerts, historical data
- Connection pooling
- Query optimization with indexes

**OptionsDataService**
- External API integration
- Data validation and parsing
- Mock data generation for testing

### Core Engines

**GEXCalculator**
- Black-Scholes gamma calculation
- Strike-by-strike GEX computation
- Heatmap data generation
- Time to expiry calculations

**GammaFlipDetector**
- Zero-crossing detection
- Linear interpolation for precision
- Market regime classification
- Distance calculations

**PinRiskAnalyzer**
- High OI strike identification
- Max pain calculation
- Pin risk scoring algorithm
- Proximity-based risk assessment

**MarketMakerAnalyzer**
- Dealer gamma exposure
- Position classification
- Hedging pressure determination
- Vanna/charm exposure

**AlertEngine**
- Rule-based alert generation
- Severity assignment
- Multiple alert types
- Historical comparison

### Data Layer

**PostgreSQL Tables**
- `option_data`: Raw options data
- `gex_snapshots`: Calculated GEX snapshots
- `alert_history`: Alert records
- `historical_gex_data`: Daily aggregates

**Indexes**
- Symbol + timestamp for time-series queries
- Alert severity + type for filtering
- Date-based indexes for historical data

## Data Flow

### GEX Calculation Flow

```
1. API Request → GEX Router
2. Router → GEXService.calculate_gex()
3. GEXService → GEXCalculator.calculate_gex_for_chain()
4. For each strike:
   - Calculate gamma (Black-Scholes)
   - Multiply by OI and spot²
   - Create GammaExposure object
5. GEXService → GammaFlipDetector.detect_flip_level()
6. GEXService → PinRiskAnalyzer.analyze_pin_risk()
7. GEXService → MarketMakerAnalyzer.analyze_positioning()
8. GEXService → AlertEngine.generate_alerts()
9. GEXService → StorageService.store_*()
10. Response → Client
```

### Alert Generation Flow

```
1. AlertEngine receives analysis results
2. Check gamma flip proximity
   - Calculate distance percentage
   - Compare to threshold
   - Assign severity
3. Check GEX concentration
   - Compare total GEX to threshold
   - Assign severity
4. Check pin risk
   - Evaluate pin risk score
   - Check days to expiration
5. Check regime change
   - Compare to previous regime
6. Check dealer position
   - Evaluate if destabilizing
7. Generate GEXAlert objects
8. Store in database
9. Return alerts to caller
```

## Technology Stack Rationale

### FastAPI
- **Why**: Modern, fast, async-first framework
- **Benefits**: Automatic OpenAPI docs, type validation, excellent performance
- **Alternatives considered**: Flask (synchronous), Django (heavy)

### PostgreSQL
- **Why**: Robust relational database with JSON support
- **Benefits**: ACID compliance, complex queries, time-series data, indexes
- **Alternatives considered**: MongoDB (less structured), TimescaleDB (overkill)

### SQLAlchemy 2.0
- **Why**: Mature ORM with async support
- **Benefits**: Query builder, migrations, connection pooling
- **Alternatives considered**: Raw SQL (less maintainable), Tortoise ORM (less mature)

### Pydantic
- **Why**: Data validation and serialization
- **Benefits**: Type hints, automatic validation, JSON schema generation
- **Alternatives considered**: Marshmallow (less integrated), dataclasses (no validation)

### NumPy/SciPy
- **Why**: Industry standard for numerical computing
- **Benefits**: Fast array operations, statistical functions, well-tested
- **Alternatives considered**: Pure Python (too slow), QuantLib (overkill)

## Scalability Considerations

### Horizontal Scaling
- Stateless API design allows multiple instances
- Load balancer distributes requests
- Shared PostgreSQL and Redis for state

### Caching Strategy
- Redis for frequently accessed GEX data
- 5-minute TTL for real-time balance
- Cache invalidation on new calculations

### Database Optimization
- Indexes on time-series queries
- Connection pooling (10 connections + 20 overflow)
- Async queries prevent blocking
- Periodic cleanup of old data

### Performance Targets
- GEX calculation: < 2 seconds for 500 contracts
- API response: < 500ms for cached data
- Database query: < 100ms for indexed lookups
- Concurrent users: 100+ with < 1s p99 latency

## Security Architecture

### API Security
- HTTPS/TLS encryption in transit
- API key authentication (planned)
- Rate limiting per client (planned)
- Input validation via Pydantic

### Database Security
- SSL connections to PostgreSQL
- Prepared statements (SQL injection prevention)
- Least privilege database users
- Regular backups

### Application Security
- Environment variables for secrets
- No hardcoded credentials
- Security headers in responses
- Audit logging for sensitive operations

## Monitoring & Observability

### Metrics (Prometheus)
- Request count by endpoint
- Request duration (histogram)
- Error rate by type
- Database query times
- GEX calculation times

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request/response logging
- Error stack traces

### Health Checks
- `/health` endpoint for liveness
- Database connectivity check
- Redis connectivity check
- Kubernetes readiness probe compatible

## Deployment Architecture

### Development
```
Docker Compose:
  - gex-visualizer (API)
  - postgres (Database)
  - redis (Cache)
```

### Production (Kubernetes)
```
Pods:
  - gex-visualizer (3+ replicas)
  - postgres (StatefulSet)
  - redis (StatefulSet)
Services:
  - LoadBalancer for API
  - ClusterIP for databases
Ingress:
  - HTTPS termination
  - Path-based routing
```

## Error Handling Strategy

### API Errors
- 400: Invalid request (validation errors)
- 404: Resource not found
- 500: Internal server error
- Detailed error messages in response

### Calculation Errors
- Graceful handling of missing Greeks
- Default values for edge cases
- Logging of calculation warnings
- Partial results when possible

### Database Errors
- Connection retry logic
- Transaction rollback on failure
- Graceful degradation for cache misses

## Future Architecture Enhancements

1. **Event-Driven Architecture**: Kafka/RabbitMQ for async processing
2. **CQRS Pattern**: Separate read/write models for scalability
3. **GraphQL API**: More flexible querying for clients
4. **Microservices Split**: Separate calculation and storage services
5. **Real-time WebSockets**: Live GEX updates without polling
6. **Distributed Caching**: Redis Cluster for larger deployments
