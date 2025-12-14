# Project: OPTIX

## Technical Requirements Document - DSDM Atern Methodology

Version 1.0 | December 2025

---

## Overview

This Technical Requirements Document is structured according to DSDM Atern principles, ensuring iterative delivery with fixed timeboxes and flexible scope. The MoSCoW prioritization technique is applied throughout.

## Business Context

OPTIX is a mobile-first options trading platform that requires robust technical architecture to support real-time market data, multi-brokerage integration, and AI-powered trading insights.

## Stakeholders

- **Document Owner:** Technical Architecture Team
- **PRD Reference:** OPTIX_PRD_v1.0
- **Methodology:** DSDM Atern (Dynamic Systems Development Method)
- **Status:** Baselined for Foundations Phase

---

## 1. DSDM Framework Overview

### 1.1 Methodology Alignment

This Technical Requirements Document is structured according to DSDM Atern principles, ensuring iterative delivery with fixed timeboxes and flexible scope. The MoSCoW prioritization technique is applied throughout.

### 1.2 DSDM Principles Applied

1. **Focus on Business Need:** All technical decisions trace back to PRD features
2. **Deliver on Time:** Timeboxed iterations with MoSCoW-prioritized requirements
3. **Never Compromise Quality:** NFRs define baseline quality that cannot be traded
4. **Build Incrementally:** Architecture supports incremental feature delivery
5. **Develop Iteratively:** Feedback loops built into every development cycle
6. **Demonstrate Control:** Observable systems with comprehensive monitoring

### 1.3 Timebox Structure

| Phase | Duration | Technical Focus |
|-------|----------|-----------------|
| Foundations | 4 weeks | Architecture, CI/CD, core infrastructure |
| Exploration | 2-week sprints | Feature prototypes, API contracts, spikes |
| Engineering | 2-week sprints | Production-ready implementation, testing |
| Deployment | 1 week | Release, monitoring, feedback collection |

---

## 2. System Architecture

### 2.1 Architecture Overview

OPTIX employs a cloud-native microservices architecture designed for horizontal scalability, resilience, and independent service deployment.

| Layer | Components | Technologies |
|-------|------------|--------------|
| Presentation | Mobile Apps, Web App, API Gateway | React Native, Next.js, Kong |
| Application | Microservices, Event Processors, AI | Node.js, Python, Go, K8s |
| Data | Databases, Caches, Queues | PostgreSQL, Redis, Kafka |
| Infrastructure | Cloud, CDN, Monitoring | AWS, CloudFlare, Datadog |

### 2.2 Microservices

| Service | Responsibility | Stack | Priority |
|---------|----------------|-------|----------|
| user-service | Auth, profiles | Node.js, PostgreSQL | **Must Have** |
| portfolio-service | Holdings, P&L | Go, PostgreSQL, Redis | **Must Have** |
| market-data | Quotes, chains | Go, TimescaleDB | **Must Have** |
| brokerage-sync | OAuth, sync | Node.js, PostgreSQL | **Must Have** |
| ai-engine | AIE, ML models | Python, PyTorch | **Should Have** |
| options-flow | Flow analysis | Python, Kafka | **Should Have** |
| gex-service | Gamma exposure | Python, NumPy | **Could Have** |

---

## 3. Non-Functional Requirements (NFRs)

NFRs define baseline quality that cannot be compromised. Per DSDM, quality remains fixed while scope flexes.

### 3.1 NFR-001: API Response Time

| Attribute | Value |
|-----------|-------|
| **Requirement** | 95th percentile < 200ms reads, < 500ms writes |
| **Priority** | **Must Have** |
| **Measurement** | Datadog APM p95 latency metrics |

**Gherkin Test Scenario:**

```gherkin
Feature: API Response Time Compliance

  @nfr @performance
  Scenario Outline: API endpoints meet response time SLA
    Given the system is under <load> load
    When I make <count> concurrent requests to <endpoint>
    Then p95 response time should be less than <max_ms> ms
    Examples:
      | load   | endpoint           | count | max_ms |
      | normal | /api/v1/portfolio  | 100   | 200    |
      | normal | /api/v1/quotes     | 100   | 150    |
      | peak   | /api/v1/portfolio  | 500   | 300    |
```

### 3.2 NFR-002: Real-Time Data Latency

| Attribute | Value |
|-----------|-------|
| **Requirement** | Market data delivered within 500ms of source receipt |
| **Priority** | **Must Have** |

**Gherkin Test Scenario:**

```gherkin
Feature: Real-Time Market Data Latency

  @nfr @realtime
  Scenario: Market data propagation meets latency requirements
    Given I am subscribed to real-time quotes for "AAPL"
    When a price update is received from the market data feed
    Then the update should reach my client within 500 ms

  Scenario: Options flow alerts delivered in real-time
    Given I have an alert for unusual activity on "TSLA"
    When unusual flow is detected
    Then I should receive notification within 2 seconds
```

### 3.3 NFR-003: Scalability

| Attribute | Value |
|-----------|-------|
| **Requirement** | Support 500K concurrent users, linear scaling to 2M |
| **Priority** | **Must Have** |

**Gherkin Test Scenario:**

```gherkin
Feature: Horizontal Scalability

  @nfr @scalability
  Scenario Outline: System scales under increasing load
    Given baseline pod count is <initial> for <service>
    When concurrent users increase to <users>
    Then service should scale to at least <expected> pods
    And response time SLA should remain within thresholds
    Examples:
      | service   | initial | users  | expected |
      | portfolio | 3       | 100000 | 6        |
      | portfolio | 3       | 250000 | 12       |
```

### 3.4 NFR-004: Availability

| Attribute | Value |
|-----------|-------|
| **Requirement** | 99.9% uptime during market hours, 99.5% overall |
| **Priority** | **Must Have** |

**Gherkin Test Scenario:**

```gherkin
Feature: High Availability

  @nfr @availability
  Scenario: System remains available during node failure
    Given portfolio-service runs with 3 replicas
    When 1 pod is terminated unexpectedly
    Then service should remain available
    And replacement pod scheduled within 30 seconds

  Scenario: Database failover maintains availability
    Given primary database has standby replica
    When primary becomes unavailable
    Then failover should occur within 30 seconds
    And no data loss should occur
```

### 3.5 NFR-005: Security - Encryption

| Attribute | Value |
|-----------|-------|
| **Requirement** | AES-256 at rest, TLS 1.3 in transit, field-level encryption for PII |
| **Priority** | **Must Have** |
| **Compliance** | SOC 2 Type II, CCPA, GDPR |

**Gherkin Test Scenario:**

```gherkin
Feature: Data Encryption Compliance

  @nfr @security
  Scenario: All API traffic uses TLS 1.3
    When I inspect the connection security
    Then the protocol should be TLS 1.3
    And weak cipher suites should be rejected

  Scenario: Sensitive data encrypted at rest
    Given a user has linked their brokerage account
    When OAuth tokens are stored in database
    Then tokens should be encrypted with AES-256

  Scenario: PII protected with field-level encryption
    Given a user profile contains email and phone
    When data is queried directly from database
    Then email and phone fields should be encrypted
```

### 3.6 NFR-006: Authentication & Authorization

| Attribute | Value |
|-----------|-------|
| **Requirement** | JWT auth with refresh tokens, RBAC, MFA for brokerage connections |
| **Priority** | **Must Have** |

**Gherkin Test Scenario:**

```gherkin
Feature: Authentication and Authorization

  @nfr @auth
  Scenario: JWT token lifecycle
    Given I am authenticated
    When access token expires after 15 minutes
    Then I can refresh using refresh token
    And old access token should be invalidated

  Scenario: MFA required for brokerage connection
    Given I am logged in with basic auth
    When I attempt to link a brokerage account
    Then I should be prompted for MFA

  Scenario: RBAC enforces subscription tier access
    Given I am a "Free" tier user
    When I request "/api/v1/gex/AAPL"
    Then I should receive 403 Forbidden
```

### 3.7 NFR-007: Disaster Recovery

| Attribute | Value |
|-----------|-------|
| **Requirement** | RPO < 1 hour, RTO < 4 hours, multi-region deployment |
| **Priority** | **Must Have** |

**Gherkin Test Scenario:**

```gherkin
Feature: Disaster Recovery

  @nfr @dr
  Scenario: Database backup meets RPO
    Given continuous replication is enabled
    When I check replication lag
    Then lag should be less than 1 minute

  Scenario: Regional failover meets RTO
    Given primary region becomes unavailable
    When failover is triggered
    Then traffic should route to secondary within 5 min
    And full service restored within 4 hours
```

---

## 4. Functional Requirements - Gherkin Specifications

The following Gherkin scenarios define acceptance criteria for the 10 core features from the PRD.

### 4.1 Feature 1: Adaptive Intelligence Engine (AIE)

| PRD Feature | Priority |
|-------------|----------|
| Adaptive Intelligence Engine - Personalized AI insights | **Should Have** |

```gherkin
Feature: Adaptive Intelligence Engine
  As a trader, I want personalized AI insights based on my history

  @aie @personalization
  Scenario: AIE identifies successful trading patterns
    Given I have 50+ trades in the past 90 days
    When AIE analyzes my trading history
    Then it should identify at least 3 recurring patterns
    And each pattern should have significance > 65%

  @aie @guidance
  Scenario: AIE provides contextual entry guidance
    Given I am viewing options chain for "NVDA"
    And conditions match my profitable setups
    When I request AI guidance
    Then I should receive personalized guidance
    And it should NOT include explicit price predictions

  @aie @risk
  Scenario: AIE adjusts for portfolio heat
    Given my portfolio has 70% options exposure
    And my typical successful exposure is 40-50%
    When I view my dashboard
    Then I should see a risk calibration warning
```

### 4.2 Feature 2: Options Flow Intelligence

| PRD Feature | Priority |
|-------------|----------|
| Options Flow Intelligence - Institutional flow analysis | **Should Have** |

```gherkin
Feature: Options Flow Intelligence
  As a trader, I want interpreted unusual options activity

  @flow @filtering
  Scenario: Smart flow filtering for watchlist
    Given I have "AAPL", "MSFT" on my watchlist
    When unusual flow is detected across market
    Then I should only see alerts for my watchlist
    And flow below $500K premium should be filtered

  @flow @classification
  Scenario: AI classifies flow intent
    Given a $2M call sweep on "TSLA"
    When flow is processed by classification model
    Then it should be classified as Directional/Hedge/Spread
    And reasoning provided in plain English

  @flow @impact
  Scenario: Flow impact analysis for positions
    Given I hold 10 AAPL $200 calls
    When large put sweep detected on AAPL
    Then I should receive position-specific alert
```

### 4.3 Feature 3: Visual Strategy Builder

| PRD Feature | Priority |
|-------------|----------|
| Visual Strategy Builder - Drag-and-drop options construction | **Should Have** |

```gherkin
Feature: Visual Strategy Builder
  As an options trader, I want to build strategies visually

  @strategy @construction
  Scenario: Drag-and-drop iron condor
    Given I am on strategy builder for "SPY"
    When I select "Iron Condor" template
    And I drag strikes to adjust width
    Then P&L diagram should update in real-time
    And max profit/loss and breakevens should display

  @strategy @greeks
  Scenario: Greeks dashboard with explanations
    Given I have built a butterfly spread
    When I view the Greeks panel
    Then I should see Delta, Gamma, Theta, Vega
    And each should have plain-English explanation
```

### 4.4 Feature 4: Collective Intelligence Network

| PRD Feature | Priority |
|-------------|----------|
| Collective Intelligence Network - Social trading platform | **Should Have** |

```gherkin
Feature: Collective Intelligence Network
  As a community member, I want to share trading ideas

  @community @identity
  Scenario: Anonymous posting option
    Given I am creating a thesis thread
    When I toggle "Post Anonymously"
    Then my username should be hidden
    But moderation should have access to identity

  @community @verified
  Scenario: Verified performance badge
    Given my 90-day returns are in top 10%
    When I post with verification enabled
    Then my "Top 10% Trader" badge should display

  @community @sentiment
  Scenario: Crowd sentiment aggregation
    Given I am viewing ticker page for "NVDA"
    Then I should see bullish/bearish percentages
    And sentiment trend over past 7 days
```

### 4.5 Feature 5: GEX Visualizer

| PRD Feature | Priority |
|-------------|----------|
| Gamma Exposure Visualizer - Market maker positioning | **Could Have** |

```gherkin
Feature: Gamma Exposure Visualizer
  As a Pro user, I want to visualize gamma positioning

  @gex @heatmap
  Scenario: GEX heatmap display
    Given I am a Pro subscriber
    When I navigate to GEX for "SPY"
    Then I should see color-coded strike heatmap
    And positive gamma green, negative red

  @gex @alerts
  Scenario: Gamma flip level alerts
    Given I enabled GEX alerts for "QQQ"
    When price approaches gamma flip level
    Then I should receive proximity alert
```

### 4.6 Feature 6: Time Machine Backtester

| PRD Feature | Priority |
|-------------|----------|
| Time Machine Backtester - Historical strategy testing | **Could Have** |

```gherkin
Feature: Time Machine Backtester
  As a strategy developer, I want to backtest strategies

  @backtest @replay
  Scenario: Visual trade replay
    Given I configured wheel strategy on "AAPL"
    When I run backtest with visual replay
    Then chart should animate through time
    And trade entries/exits marked on chart

  @backtest @attribution
  Scenario: Performance attribution
    Given backtest has completed
    When I view attribution report
    Then I should see breakdown by Delta, Theta, Vega
```

### 4.7 Feature 7: Universal Brokerage Sync

| PRD Feature | Priority |
|-------------|----------|
| Universal Brokerage Sync - Multi-broker integration | **Must Have** |

```gherkin
Feature: Universal Brokerage Sync
  As a multi-brokerage user, I want unified tracking

  @brokerage @oauth
  Scenario Outline: OAuth connection under 60 seconds
    When I select <brokerage> and complete OAuth
    Then account should be linked within 60 seconds
    Examples:
      | brokerage           |
      | Schwab              |
      | Fidelity            |
      | Robinhood           |
      | Interactive Brokers |
      | Webull              |

  @brokerage @unified
  Scenario: Unified portfolio view
    Given I have linked Schwab and Fidelity
    When I view portfolio dashboard
    Then I should see combined positions
    And total portfolio value
```

### 4.8 Feature 8: Volatility Compass

| PRD Feature | Priority |
|-------------|----------|
| Volatility Compass - Comprehensive IV analytics | **Should Have** |

```gherkin
Feature: Volatility Compass
  As an options trader, I want IV analytics

  @volatility @dashboard
  Scenario: IV Rank watchlist view
    Given I have a watchlist of 10 tickers
    When I view IV dashboard
    Then I should see IV Rank/Percentile for each

  @volatility @suggestions
  Scenario: Strategy suggestions based on IV
    Given "TSLA" has IV Rank above 80%
    Then I should see suggestion to sell premium
```

### 4.9 Feature 9: Smart Alerts Ecosystem

| PRD Feature | Priority |
|-------------|----------|
| Smart Alerts - AI-curated notifications | **Should Have** |

```gherkin
Feature: Smart Alerts Ecosystem
  As a trader, I want intelligent alerts

  @alerts @learning
  Scenario: Alert relevance learning
    Given I received 100 alerts over 30 days
    And acted on 20 of them
    Then similar alerts should be prioritized
    And ignored types should be deprioritized

  @alerts @multi-condition
  Scenario: Multi-condition triggers
    Given alert with: TSLA drop 3%, IV spike 10%, put flow
    When all conditions met simultaneously
    Then I should receive single consolidated alert
```

### 4.10 Feature 10: Trading Journal AI

| PRD Feature | Priority |
|-------------|----------|
| Trading Journal AI - Automated journaling with analysis | **Should Have** |

```gherkin
Feature: Trading Journal AI
  As a self-improving trader, I want automated journaling

  @journal @capture
  Scenario: Automatic trade capture
    Given I linked my Schwab account
    When I execute a trade in Schwab
    Then trade should appear in journal within 5 min

  @journal @patterns
  Scenario: AI pattern discovery
    Given I have 100+ journal entries
    When AI analyzes my patterns
    Then it should identify tag-outcome correlations
    And surface insights like "FOMO trades have 40% lower win rate"

  @journal @review
  Scenario: Weekly AI review
    Given it is Sunday evening
    And I made at least 5 trades this week
    Then I should receive summary with P&L, win rate, tips
```

---

## 5. API Specifications

### 5.1 Design Principles

- **RESTful Design:** Resource-oriented endpoints
- **Versioning:** URL-based (/api/v1/) with 12-month deprecation
- **Authentication:** Bearer token (JWT)
- **Rate Limiting:** Token bucket, varies by tier
- **Pagination:** Cursor-based for lists

### 5.2 Core Endpoints

| Method | Endpoint | Description | Priority |
|--------|----------|-------------|----------|
| GET | /api/v1/portfolio | Unified portfolio | **Must Have** |
| GET | /api/v1/quotes/{symbol} | Real-time quote | **Must Have** |
| GET | /api/v1/options/chain/{symbol} | Options chain | **Must Have** |
| POST | /api/v1/alerts | Create alert | **Must Have** |
| GET | /api/v1/flow/unusual | Unusual flow | **Should Have** |
| GET | /api/v1/ai/insights | AI insights | **Should Have** |
| GET | /api/v1/gex/{symbol} | Gamma exposure | **Could Have** |
| POST | /api/v1/backtest | Run backtest | **Could Have** |

### 5.3 WebSocket Channels

| Channel | Purpose | Frequency |
|---------|---------|-----------|
| quotes:{symbol} | Real-time prices | ~100ms throttled |
| portfolio:{user_id} | Portfolio updates | ~1s |
| flow:unusual | Options flow | Event-driven |
| alerts:{user_id} | User alerts | Event-driven |

---

## 6. Security Architecture

### 6.1 Security Controls

- **Network:** WAF, DDoS protection, VPC isolation
- **Application:** Input validation, parameterized queries, CSP
- **Data:** AES-256 at rest, TLS 1.3 in transit
- **Identity:** OAuth 2.0 + PKCE, MFA for sensitive ops
- **Secrets:** AWS Secrets Manager, automated rotation

### 6.2 Compliance

| Standard | Scope | Timeline |
|----------|-------|----------|
| SOC 2 Type II | All production systems | Month 12 |
| CCPA | California user data | Launch |
| GDPR | EU users (future) | Month 18 |

**Security Test Scenarios:**

```gherkin
Feature: Security Controls

  @security @injection
  Scenario: SQL injection prevention
    When I submit query with SQL injection payload
    Then request should be sanitized
    And attempt should be logged

  @security @bruteforce
  Scenario: Brute force protection
    When 5 failed logins occur within 5 minutes
    Then account should be temporarily locked
    And security notification sent to user
```

---

## 7. Infrastructure Requirements

### 7.1 Cloud Infrastructure

- **Cloud:** AWS (us-east-1 primary, us-west-2 DR)
- **Orchestration:** Amazon EKS (Kubernetes 1.28+)
- **Database:** RDS PostgreSQL Multi-AZ, ElastiCache Redis
- **Messaging:** Amazon MSK (Managed Kafka)
- **CI/CD:** GitHub Actions + ArgoCD

### 7.2 Environments

| Environment | Purpose | Data | Scale |
|-------------|---------|------|-------|
| Development | Feature dev | Synthetic | Minimal |
| Staging | Integration | Anonymized | 20% prod |
| Production | Live traffic | Real | Full + headroom |

---

## 8. Testing Strategy

Following DSDM's "Never Compromise Quality" principle, testing is integrated throughout development.

| Test Level | Coverage | Tools | Execution |
|------------|----------|-------|-----------|
| Unit | 80% coverage | Jest, pytest | Every commit |
| Integration | All APIs | Supertest, Pact | Every PR |
| E2E (Gherkin) | Critical paths | Cucumber, Playwright | Nightly |
| Performance | NFR compliance | k6, Locust | Weekly |
| Security | OWASP Top 10 | ZAP, Snyk | Every PR |

---

## 9. Appendices

### Appendix A: MoSCoW Summary

| Priority | Count | Key Items |
|----------|-------|-----------|
| **Must Have** | 12 | Core services, brokerage sync, all NFRs |
| **Should Have** | 8 | AIE, Flow, Community, Volatility, Alerts, Journal |
| **Could Have** | 4 | GEX Visualizer, Backtester, Advanced analytics |
| **Won't Have** | 0 | (Deferred to future releases) |

### Appendix B: Glossary

| Term | Definition |
|------|------------|
| AIE | Adaptive Intelligence Engine - personalized ML system |
| DSDM | Dynamic Systems Development Method - Agile framework |
| GEX | Gamma Exposure - market maker hedging activity measure |
| IV | Implied Volatility - expected future price movement |
| MoSCoW | Must/Should/Could/Won't - prioritization technique |
| NFR | Non-Functional Requirement - quality attribute |
| RPO/RTO | Recovery Point/Time Objective - DR metrics |

---

## Constraints

### Technical Constraints

- Must use AWS cloud infrastructure
- Must integrate with existing brokerage OAuth systems
- Mobile-first development approach (React Native)

### Business Constraints

- Must achieve SOC 2 Type II compliance by Month 12
- Launch with support for 5 major brokerages

### Resource Constraints

- Core team size scales with phases

---

## Assumptions

- AWS services will meet availability SLAs
- Brokerage APIs maintain backwards compatibility
- Market data providers support required throughput

## Dependencies

- AWS infrastructure services
- Third-party market data feeds
- Brokerage OAuth API availability

## Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| NFR non-compliance at launch | High | Medium | Continuous load testing, early performance optimization |
| Security breach | High | Low | Comprehensive security testing, SOC 2 compliance |
| Brokerage API instability | Medium | Medium | Circuit breakers, retry logic, fallback data sources |
| Scaling bottlenecks | Medium | Medium | Auto-scaling, capacity planning, caching strategy |

---

## Acceptance Criteria

- [ ] All Must Have microservices deployed and operational
- [ ] All NFRs validated through automated testing
- [ ] Security controls pass penetration testing
- [ ] 99.9% uptime achieved in staging environment

## Success Metrics

- API response time p95 < 200ms for reads
- Real-time data latency < 500ms
- System supports 500K concurrent users
- Zero critical security vulnerabilities

---

*--- End of Document ---*
