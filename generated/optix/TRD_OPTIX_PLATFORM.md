# OPTIX Platform - Technical Requirements Document (TRD)

> **Document ID:** TRD-OPTIX-2025-001
> **Version:** 1.0
> **Created:** December 14, 2025
> **Status:** Draft
> **Classification:** Internal

---

## Table of Contents

1. [Document Overview](#1-document-overview)
2. [Non-Functional Requirements (NFRs)](#2-non-functional-requirements-nfrs)
3. [Critical Priority Stories](#3-critical-priority-stories)
4. [High Priority Stories](#4-high-priority-stories)
5. [Medium Priority Stories](#5-medium-priority-stories)
6. [Low Priority Stories](#6-low-priority-stories)
7. [Appendix](#7-appendix)

---

## 1. Document Overview

### 1.1 Purpose

This Technical Requirements Document (TRD) defines the complete functional and non-functional requirements for the OPTIX Options Trading Platform UI/UX implementation. It includes detailed user stories with acceptance criteria and comprehensive test scenarios written in Gherkin syntax.

### 1.2 Scope

This document covers:
- 127 UI/UX tasks across 4 priority levels
- Non-functional requirements for performance, security, scalability, and reliability
- Gherkin test scenarios for automated testing
- Integration requirements with backend services

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|------------|
| NFR | Non-Functional Requirement |
| GEX | Gamma Exposure |
| IV | Implied Volatility |
| ATM | At The Money |
| ITM | In The Money |
| OTM | Out of The Money |
| JWT | JSON Web Token |
| WebSocket | Full-duplex communication protocol |
| P&L | Profit and Loss |

### 1.4 References

| Document | Description |
|----------|-------------|
| REMAINING_UI_UX_TASKS.md | UI/UX task breakdown |
| README.md | Platform overview |
| optix-design-system.css | Design system specification |

---

## 2. Non-Functional Requirements (NFRs)

### 2.1 Performance Requirements

#### NFR-PERF-001: Page Load Time
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Initial page load shall complete within 3 seconds on 4G connection |
| **Metric** | Time to First Contentful Paint (FCP) |
| **Target** | < 1.5 seconds |
| **Maximum** | < 3.0 seconds |
| **Measurement** | Lighthouse Performance Score |

#### NFR-PERF-002: API Response Time
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | API responses shall return within acceptable latency thresholds |
| **Read Operations** | < 200ms (95th percentile) |
| **Write Operations** | < 500ms (95th percentile) |
| **Complex Queries** | < 2000ms (95th percentile) |

#### NFR-PERF-003: Real-Time Data Latency
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Real-time data updates shall display within 100ms of receipt |
| **Quote Updates** | < 100ms |
| **Order Flow** | < 150ms |
| **Alert Triggers** | < 200ms |

#### NFR-PERF-004: Chart Rendering
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Charts shall render within performance thresholds |
| **Initial Render** | < 500ms for 1000 data points |
| **Update Render** | < 50ms per tick update |
| **Interaction Response** | < 100ms for zoom/pan |

#### NFR-PERF-005: Concurrent Users
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | System shall support concurrent user load |
| **Target** | 10,000 concurrent users |
| **Peak** | 25,000 concurrent users |
| **Degradation** | Graceful degradation above peak |

### 2.2 Security Requirements

#### NFR-SEC-001: Authentication
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | All user sessions shall be authenticated via JWT |
| **Token Expiry** | Access token: 15 minutes |
| **Refresh Token** | 7 days with secure storage |
| **Algorithm** | RS256 asymmetric signing |

#### NFR-SEC-002: Authorization
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Role-based access control (RBAC) |
| **Roles** | Admin, Premium, Standard, Guest |
| **Enforcement** | Server-side and client-side |

#### NFR-SEC-003: Data Encryption
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | All data transmission shall be encrypted |
| **In Transit** | TLS 1.3 minimum |
| **At Rest** | AES-256 encryption |
| **API Keys** | Encrypted storage, never exposed to frontend |

#### NFR-SEC-004: Input Validation
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | All user inputs shall be validated and sanitized |
| **XSS Prevention** | Content Security Policy headers |
| **CSRF Protection** | Token-based CSRF prevention |
| **SQL Injection** | Parameterized queries only |

#### NFR-SEC-005: Session Management
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Secure session handling |
| **Idle Timeout** | 30 minutes |
| **Absolute Timeout** | 24 hours |
| **Concurrent Sessions** | Maximum 3 per user |

### 2.3 Scalability Requirements

#### NFR-SCALE-001: Horizontal Scaling
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Frontend shall support horizontal scaling |
| **CDN** | Static assets served via CDN |
| **State** | Stateless frontend design |
| **Load Balancing** | Round-robin with health checks |

#### NFR-SCALE-002: Data Volume
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | UI shall handle large data volumes |
| **Options Chain** | Up to 500 strikes per expiration |
| **Watchlist** | Up to 100 symbols per user |
| **Historical Data** | Up to 5 years of daily data |

### 2.4 Availability Requirements

#### NFR-AVAIL-001: Uptime
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | System shall maintain high availability |
| **Target** | 99.9% uptime (excluding planned maintenance) |
| **Market Hours** | 99.99% during market hours |
| **Maintenance Window** | Weekends 2:00-6:00 AM EST |

#### NFR-AVAIL-002: Disaster Recovery
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | System shall recover from failures |
| **RTO** | 4 hours |
| **RPO** | 1 hour |
| **Failover** | Automatic to secondary region |

### 2.5 Reliability Requirements

#### NFR-REL-001: Error Handling
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Graceful error handling throughout |
| **User Feedback** | Clear error messages |
| **Logging** | All errors logged with context |
| **Recovery** | Automatic retry for transient failures |

#### NFR-REL-002: Data Integrity
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Data consistency across UI |
| **Optimistic Updates** | With rollback on failure |
| **Cache Invalidation** | Real-time cache updates |
| **Conflict Resolution** | Last-write-wins with notification |

### 2.6 Usability Requirements

#### NFR-USE-001: Accessibility
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | WCAG 2.1 AA compliance |
| **Screen Readers** | Full ARIA support |
| **Keyboard Navigation** | All features accessible |
| **Color Contrast** | Minimum 4.5:1 ratio |

#### NFR-USE-002: Responsiveness
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Responsive design across devices |
| **Desktop** | 1024px - 2560px |
| **Tablet** | 768px - 1023px |
| **Mobile** | 320px - 767px |

#### NFR-USE-003: Browser Support
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Cross-browser compatibility |
| **Chrome** | Last 2 versions |
| **Firefox** | Last 2 versions |
| **Safari** | Last 2 versions |
| **Edge** | Last 2 versions |

### 2.7 Maintainability Requirements

#### NFR-MAINT-001: Code Quality
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Maintainable codebase |
| **Test Coverage** | Minimum 80% |
| **Documentation** | JSDoc for all public APIs |
| **Linting** | ESLint with strict rules |

#### NFR-MAINT-002: Modularity
| Attribute | Specification |
|-----------|---------------|
| **Requirement** | Component-based architecture |
| **Coupling** | Loose coupling between modules |
| **Reusability** | Shared component library |
| **Versioning** | Semantic versioning |

---

## 3. Critical Priority Stories

### 3.1 Epic: Real-Time Data Integration (CP-1)

#### Story CP-1.1: WebSocket Connection Manager

**Story ID:** CP-1.1
**Title:** As a user, I want the application to maintain a persistent WebSocket connection so that I receive real-time market data without manual refresh.

**Acceptance Criteria:**
- WebSocket connects automatically on page load
- Connection reconnects within 5 seconds after disconnection
- Connection status indicator visible in header
- Exponential backoff for reconnection attempts
- Maximum 5 reconnection attempts before showing error

**Gherkin Test Scenarios:**

```gherkin
Feature: WebSocket Connection Manager
  As a user
  I want a reliable WebSocket connection
  So that I can receive real-time market data

  Background:
    Given I am logged into the OPTIX platform
    And I am on a page that requires real-time data

  @critical @websocket
  Scenario: Successful WebSocket connection on page load
    When the page finishes loading
    Then a WebSocket connection should be established
    And the connection status indicator should show "Connected"
    And the indicator should be green

  @critical @websocket
  Scenario: Automatic reconnection after disconnection
    Given the WebSocket connection is established
    When the connection is unexpectedly lost
    Then the connection status indicator should show "Reconnecting"
    And the system should attempt to reconnect within 5 seconds
    And the connection should be re-established
    And the status indicator should return to "Connected"

  @critical @websocket
  Scenario: Exponential backoff for reconnection attempts
    Given the WebSocket connection is lost
    And the server is unavailable
    When the system attempts to reconnect
    Then the first retry should occur after 1 second
    And the second retry should occur after 2 seconds
    And the third retry should occur after 4 seconds
    And the fourth retry should occur after 8 seconds
    And the fifth retry should occur after 16 seconds

  @critical @websocket
  Scenario: Maximum reconnection attempts exceeded
    Given the WebSocket connection is lost
    And the server remains unavailable
    When 5 reconnection attempts have failed
    Then the connection status indicator should show "Disconnected"
    And an error message should be displayed to the user
    And a "Retry Connection" button should be visible

  @critical @websocket
  Scenario: Manual reconnection after failure
    Given the maximum reconnection attempts have been exceeded
    And the "Retry Connection" button is visible
    When I click the "Retry Connection" button
    Then the reconnection attempts should reset
    And the system should attempt to connect again

  @critical @websocket
  Scenario: Connection maintained during page navigation
    Given the WebSocket connection is established
    When I navigate to another page within the application
    Then the WebSocket connection should remain active
    And no reconnection should be required

  @critical @websocket @performance
  Scenario: Connection latency monitoring
    Given the WebSocket connection is established
    When I receive a heartbeat message
    Then the round-trip latency should be measured
    And if latency exceeds 500ms a warning should be logged
```

#### Story CP-1.2: Real-Time Quote Streaming for Watchlist

**Story ID:** CP-1.2
**Title:** As a user, I want to see real-time price updates on my watchlist so that I can monitor market movements without refreshing.

**Acceptance Criteria:**
- Quotes update in real-time (< 100ms latency)
- Price changes show visual flash animation (green up, red down)
- Last update timestamp visible per symbol
- Handles 100+ symbols without performance degradation
- Graceful fallback to polling if WebSocket unavailable

**Gherkin Test Scenarios:**

```gherkin
Feature: Real-Time Quote Streaming for Watchlist
  As a user
  I want real-time quote updates on my watchlist
  So that I can monitor market movements instantly

  Background:
    Given I am logged into the OPTIX platform
    And I am on the watchlist page
    And the WebSocket connection is established
    And I have symbols in my watchlist

  @critical @quotes @realtime
  Scenario: Real-time quote update display
    Given "AAPL" is in my watchlist with price "$150.00"
    When a new quote for "AAPL" arrives with price "$150.50"
    Then the price should update to "$150.50"
    And the update should occur within 100 milliseconds
    And the last updated timestamp should refresh

  @critical @quotes @visual
  Scenario: Price increase visual indication
    Given "AAPL" is showing price "$150.00"
    When a new quote arrives with price "$150.50"
    Then the price cell should flash green
    And the change indicator should show "+$0.50"
    And the percentage change should show "+0.33%"

  @critical @quotes @visual
  Scenario: Price decrease visual indication
    Given "AAPL" is showing price "$150.00"
    When a new quote arrives with price "$149.50"
    Then the price cell should flash red
    And the change indicator should show "-$0.50"
    And the percentage change should show "-0.33%"

  @critical @quotes @performance
  Scenario: Handle high-frequency updates
    Given I have 50 symbols in my watchlist
    When quotes arrive for all 50 symbols within 1 second
    Then all prices should update correctly
    And the UI should remain responsive
    And no updates should be dropped

  @critical @quotes @performance
  Scenario: Performance with large watchlist
    Given I have 100 symbols in my watchlist
    When real-time updates are streaming
    Then the page frame rate should stay above 30fps
    And memory usage should remain stable
    And CPU usage should stay below 50%

  @critical @quotes @fallback
  Scenario: Fallback to polling when WebSocket unavailable
    Given the WebSocket connection is unavailable
    When I view the watchlist page
    Then the system should fall back to polling mode
    And quotes should update every 5 seconds
    And a "Limited connectivity" indicator should appear

  @critical @quotes
  Scenario: Quote subscription management
    Given I am viewing my watchlist
    When I add a new symbol "TSLA"
    Then the system should subscribe to "TSLA" quotes
    And "TSLA" should start receiving real-time updates

  @critical @quotes
  Scenario: Quote unsubscription on symbol removal
    Given "MSFT" is in my watchlist with active subscription
    When I remove "MSFT" from my watchlist
    Then the system should unsubscribe from "MSFT" quotes
    And no further updates should be received for "MSFT"
```

#### Story CP-1.3: Live Options Chain Updates

**Story ID:** CP-1.3
**Title:** As a user, I want the options chain to update in real-time so that I can see current pricing and Greeks without refreshing.

**Acceptance Criteria:**
- Options prices update in real-time
- Greeks recalculate on price changes
- Price change highlighting (flash animation)
- Bid/ask spread visualization updates
- IV changes highlighted distinctly

**Gherkin Test Scenarios:**

```gherkin
Feature: Live Options Chain Updates
  As a user
  I want real-time options chain updates
  So that I can make informed trading decisions with current data

  Background:
    Given I am logged into the OPTIX platform
    And I am on the options chain page for "SPY"
    And the WebSocket connection is established

  @critical @optionschain @realtime
  Scenario: Real-time option price update
    Given I am viewing the "SPY" options chain
    And the 450 call option shows bid "$5.00" ask "$5.10"
    When a new quote arrives with bid "$5.05" ask "$5.15"
    Then the bid should update to "$5.05"
    And the ask should update to "$5.15"
    And the update should occur within 100 milliseconds

  @critical @optionschain @greeks
  Scenario: Greeks recalculation on price change
    Given I am viewing the 450 call option
    And delta shows "0.45"
    When the underlying price changes from "$448.00" to "$449.00"
    Then the delta should recalculate
    And the new delta should be approximately "0.47"
    And gamma, theta, and vega should also update

  @critical @optionschain @visual
  Scenario: Price increase highlighting
    Given the 450 call shows last price "$5.00"
    When a trade occurs at "$5.10"
    Then the last price cell should flash green
    And the change should show "+$0.10"

  @critical @optionschain @visual
  Scenario: Price decrease highlighting
    Given the 450 put shows last price "$3.00"
    When a trade occurs at "$2.90"
    Then the last price cell should flash red
    And the change should show "-$0.10"

  @critical @optionschain @spread
  Scenario: Bid-ask spread visualization
    Given the 450 call shows bid "$5.00" ask "$5.20"
    Then the spread should display as "$0.20"
    And the spread percentage should show "3.9%"
    When the spread widens to bid "$4.95" ask "$5.25"
    Then the spread should update to "$0.30"
    And the spread should be highlighted as "wide"

  @critical @optionschain @iv
  Scenario: IV change highlighting
    Given the 450 call shows IV "25.5%"
    When IV updates to "27.0%"
    Then the IV cell should flash with distinct color
    And the IV change indicator should show "+1.5%"

  @critical @optionschain @performance
  Scenario: Performance with full chain loaded
    Given I am viewing all expirations for "SPY"
    And there are 500+ option contracts visible
    When real-time updates stream for all contracts
    Then the UI should remain responsive
    And updates should not be delayed by more than 200ms

  @critical @optionschain @atm
  Scenario: ATM strike highlighting updates
    Given the underlying "SPY" is at "$450.00"
    And the 450 strike is highlighted as ATM
    When the underlying moves to "$451.50"
    Then the 451 or 452 strike should become highlighted as ATM
    And the previous ATM highlight should be removed
```

#### Story CP-1.4: Order Flow Streaming

**Story ID:** CP-1.4
**Title:** As a user, I want to see real-time options order flow so that I can identify unusual activity and market sentiment.

**Acceptance Criteria:**
- Order flow updates stream in real-time
- Large orders highlighted with distinct styling
- Filtering does not interrupt streaming
- Sentiment aggregation updates live
- Export functionality for captured flow

**Gherkin Test Scenarios:**

```gherkin
Feature: Order Flow Streaming
  As a user
  I want real-time options order flow
  So that I can identify unusual activity and market sentiment

  Background:
    Given I am logged into the OPTIX platform
    And I am on the options flow page
    And the WebSocket connection is established

  @critical @orderflow @realtime
  Scenario: New order appears in real-time
    Given I am viewing the order flow feed
    When a new order is executed for "AAPL 150C"
    Then the order should appear at the top of the flow
    And the entry should animate into view
    And the timestamp should show current time

  @critical @orderflow @highlight
  Scenario: Large order highlighting
    Given the large order threshold is set to "$1,000,000"
    When an order for "$1,500,000" premium arrives
    Then the order row should be highlighted distinctly
    And a "LARGE" badge should appear
    And an optional sound alert should play

  @critical @orderflow @sweep
  Scenario: Sweep order identification
    Given I am viewing the order flow
    When a sweep order is detected across multiple exchanges
    Then the order should be tagged as "SWEEP"
    And the exchanges involved should be listed
    And the total size should be aggregated

  @critical @orderflow @filter
  Scenario: Filtering maintains streaming
    Given orders are streaming in real-time
    When I apply a filter for "AAPL" only
    Then only "AAPL" orders should display
    And new "AAPL" orders should continue streaming
    And non-matching orders should be filtered out

  @critical @orderflow @filter
  Scenario: Multiple filter criteria
    Given I am viewing all order flow
    When I set symbol filter to "SPY"
    And I set minimum premium to "$100,000"
    And I set order type to "CALL"
    Then only matching orders should display
    And the filter summary should show active criteria

  @critical @orderflow @sentiment
  Scenario: Live sentiment aggregation
    Given I am viewing the sentiment panel
    When bullish orders outweigh bearish orders
    Then the sentiment gauge should show bullish bias
    And the call/put ratio should update in real-time
    And the premium distribution chart should refresh

  @critical @orderflow @export
  Scenario: Export captured flow data
    Given I have been capturing flow for 30 minutes
    When I click the "Export" button
    Then I should be able to download a CSV file
    And the file should contain all captured orders
    And filters should be reflected in the export

  @critical @orderflow @pause
  Scenario: Pause and resume streaming
    Given orders are streaming in real-time
    When I click the "Pause" button
    Then new orders should stop appearing
    And the pause indicator should be visible
    When I click "Resume"
    Then streaming should continue
    And any missed orders should be backfilled
```

#### Story CP-1.5: Position P&L Real-Time Updates

**Story ID:** CP-1.5
**Title:** As a user, I want my position P&L to update in real-time so that I can monitor my portfolio performance without refreshing.

**Acceptance Criteria:**
- Position P&L updates with market prices
- Total portfolio P&L aggregates correctly
- Greeks update with underlying changes
- Day P&L vs total P&L both visible
- Percentage and dollar changes shown

**Gherkin Test Scenarios:**

```gherkin
Feature: Position P&L Real-Time Updates
  As a user
  I want real-time P&L updates for my positions
  So that I can monitor portfolio performance instantly

  Background:
    Given I am logged into the OPTIX platform
    And I am on the positions page
    And the WebSocket connection is established
    And I have open positions

  @critical @positions @pnl
  Scenario: Individual position P&L update
    Given I have a position in "AAPL 150C" with cost basis "$5.00"
    And the current price is "$5.50" showing P&L "+$50.00"
    When the option price updates to "$5.75"
    Then the P&L should update to "+$75.00"
    And the update should occur within 100 milliseconds

  @critical @positions @pnl
  Scenario: Portfolio total P&L aggregation
    Given I have 3 positions with P&L "+$100", "-$50", "+$200"
    And the total portfolio P&L shows "+$250"
    When one position P&L changes to "+$150"
    Then the total portfolio P&L should update to "+$300"
    And the calculation should be accurate

  @critical @positions @greeks
  Scenario: Position Greeks update with underlying
    Given I have a "SPY 450C" position
    And position delta shows "45.0"
    When the SPY price moves from "$448" to "$450"
    Then the position delta should recalculate
    And gamma, theta, vega should also update
    And portfolio Greeks totals should refresh

  @critical @positions @daypnl
  Scenario: Day P&L calculation
    Given my position opened today at "$5.00"
    And the previous close was "$4.80"
    And the current price is "$5.25"
    Then the day P&L should show "+$25.00" (from today's open)
    And the total P&L should show "+$25.00" (from cost basis)

  @critical @positions @daypnl
  Scenario: Distinguish day P&L from total P&L
    Given my position has cost basis "$4.00"
    And yesterday's close was "$5.00"
    And current price is "$5.50"
    Then total P&L should show "+$150.00"
    And day P&L should show "+$50.00"
    And both should be clearly labeled

  @critical @positions @percentage
  Scenario: Percentage change display
    Given my position cost basis is "$1,000"
    And current value is "$1,250"
    Then P&L should show "+$250.00"
    And percentage should show "+25.0%"
    When value changes to "$1,300"
    Then percentage should update to "+30.0%"

  @critical @positions @visual
  Scenario: Visual indication of P&L changes
    Given my position shows P&L "+$100.00"
    When P&L increases to "+$120.00"
    Then the P&L cell should flash green briefly
    When P&L decreases to "+$80.00"
    Then the P&L cell should flash red briefly
```

---

### 3.2 Epic: Authentication Flow (CP-2)

#### Story CP-2.1: Login Form Integration

**Story ID:** CP-2.1
**Title:** As a user, I want to log in with my email and password so that I can access my trading account.

**Acceptance Criteria:**
- Login form validates email format
- Password field masks input
- Error messages are clear and helpful
- Successful login redirects to dashboard
- Failed attempts show appropriate error

**Gherkin Test Scenarios:**

```gherkin
Feature: Login Form Integration
  As a user
  I want to log in with email and password
  So that I can access my trading account

  Background:
    Given I am on the login page
    And I am not currently authenticated

  @critical @auth @login
  Scenario: Successful login with valid credentials
    Given I have a registered account with email "trader@example.com"
    When I enter email "trader@example.com"
    And I enter password "SecurePass123!"
    And I click the "Login" button
    Then I should be redirected to the dashboard
    And my session should be authenticated
    And my name should appear in the header

  @critical @auth @login
  Scenario: Login failure with invalid email
    When I enter email "invalid-email"
    And I enter password "SecurePass123!"
    And I click the "Login" button
    Then I should see error message "Please enter a valid email address"
    And I should remain on the login page

  @critical @auth @login
  Scenario: Login failure with wrong password
    Given I have a registered account with email "trader@example.com"
    When I enter email "trader@example.com"
    And I enter password "WrongPassword123!"
    And I click the "Login" button
    Then I should see error message "Invalid email or password"
    And I should remain on the login page
    And the password field should be cleared

  @critical @auth @login
  Scenario: Login failure with non-existent account
    When I enter email "nonexistent@example.com"
    And I enter password "AnyPassword123!"
    And I click the "Login" button
    Then I should see error message "Invalid email or password"
    And no account existence should be revealed

  @critical @auth @login
  Scenario: Password field masking
    When I enter password "SecurePass123!"
    Then the password should be displayed as dots or asterisks
    When I click the "Show password" icon
    Then the password should be visible as "SecurePass123!"

  @critical @auth @login
  Scenario: Form validation before submission
    When I leave the email field empty
    And I leave the password field empty
    And I click the "Login" button
    Then I should see error "Email is required"
    And I should see error "Password is required"
    And no API request should be made

  @critical @auth @login
  Scenario: Loading state during authentication
    When I enter valid credentials
    And I click the "Login" button
    Then the button should show a loading spinner
    And the form fields should be disabled
    And I should not be able to submit again

  @critical @auth @login @security
  Scenario: Account lockout after failed attempts
    Given I have a registered account
    When I enter wrong password 5 times consecutively
    Then I should see message "Account temporarily locked"
    And I should see "Try again in 15 minutes"
    And further login attempts should be blocked
```

#### Story CP-2.2: Token Refresh Mechanism

**Story ID:** CP-2.2
**Title:** As a user, I want my session to automatically refresh so that I don't get logged out unexpectedly during active use.

**Acceptance Criteria:**
- Access token refreshes before expiration
- Refresh happens transparently to user
- Failed refresh redirects to login
- Refresh token rotation implemented
- Multiple tabs stay synchronized

**Gherkin Test Scenarios:**

```gherkin
Feature: Token Refresh Mechanism
  As a user
  I want automatic session refresh
  So that I don't get logged out during active use

  Background:
    Given I am logged into the OPTIX platform
    And my access token expires in 15 minutes

  @critical @auth @token
  Scenario: Automatic token refresh before expiration
    Given my access token will expire in 2 minutes
    When the refresh timer triggers
    Then a new access token should be obtained
    And the new token should be stored securely
    And my session should continue uninterrupted

  @critical @auth @token
  Scenario: Transparent refresh during API call
    Given my access token is expired
    When I trigger an API call
    Then the system should automatically refresh the token
    And then retry the original API call
    And I should not see any error

  @critical @auth @token
  Scenario: Refresh failure redirects to login
    Given my refresh token is expired
    When the system attempts to refresh
    Then the refresh should fail
    And I should be redirected to the login page
    And I should see message "Session expired. Please log in again."

  @critical @auth @token
  Scenario: Refresh token rotation
    Given I have a valid refresh token
    When the access token is refreshed
    Then a new refresh token should also be issued
    And the old refresh token should be invalidated
    And the new refresh token should be stored

  @critical @auth @token
  Scenario: Multiple tabs synchronization
    Given I have the application open in two browser tabs
    When the token is refreshed in Tab 1
    Then Tab 2 should also use the new token
    And both tabs should remain authenticated

  @critical @auth @token
  Scenario: Activity extends session
    Given my session is about to timeout due to inactivity
    When I perform an action in the application
    Then the inactivity timer should reset
    And my session should continue

  @critical @auth @token @security
  Scenario: Token storage security
    When I inspect browser storage
    Then the access token should be in memory only
    And the refresh token should be in httpOnly cookie
    And no tokens should be in localStorage
```

#### Story CP-2.3: Session Timeout Warning

**Story ID:** CP-2.3
**Title:** As a user, I want to be warned before my session times out so that I can choose to extend it and not lose my work.

**Acceptance Criteria:**
- Warning appears 5 minutes before timeout
- User can extend session with one click
- User can choose to log out
- Countdown timer shows remaining time
- Warning does not appear during active use

**Gherkin Test Scenarios:**

```gherkin
Feature: Session Timeout Warning
  As a user
  I want to be warned before session timeout
  So that I can extend my session and not lose work

  Background:
    Given I am logged into the OPTIX platform
    And session timeout is set to 30 minutes of inactivity

  @critical @auth @timeout
  Scenario: Warning modal appears before timeout
    Given I have been inactive for 25 minutes
    When the 5-minute warning threshold is reached
    Then a session timeout warning modal should appear
    And it should show "Your session will expire in 5:00"
    And it should have "Extend Session" and "Log Out" buttons

  @critical @auth @timeout
  Scenario: Countdown timer in warning modal
    Given the session timeout warning is displayed
    And the timer shows "5:00"
    When 30 seconds pass
    Then the timer should show "4:30"
    And the timer should continue counting down

  @critical @auth @timeout
  Scenario: Extend session from warning
    Given the session timeout warning is displayed
    When I click "Extend Session"
    Then the warning modal should close
    And my session should be extended by 30 minutes
    And the inactivity timer should reset

  @critical @auth @timeout
  Scenario: Log out from warning
    Given the session timeout warning is displayed
    When I click "Log Out"
    Then I should be logged out
    And I should be redirected to the login page
    And my session data should be cleared

  @critical @auth @timeout
  Scenario: Automatic logout when timer reaches zero
    Given the session timeout warning is displayed
    And I do not interact with the modal
    When the countdown reaches 0:00
    Then I should be automatically logged out
    And I should see message "Session expired due to inactivity"

  @critical @auth @timeout
  Scenario: No warning during active use
    Given I have been actively using the application
    And I made an action 2 minutes ago
    When the system checks for inactivity
    Then no timeout warning should appear
    And my session should continue normally

  @critical @auth @timeout
  Scenario: Activity dismisses warning
    Given the session timeout warning is displayed
    When I click anywhere outside the modal on the application
    Then the warning should close
    And my session should be extended
```

#### Story CP-2.4: Password Reset Flow

**Story ID:** CP-2.4
**Title:** As a user, I want to reset my password if I forget it so that I can regain access to my account.

**Acceptance Criteria:**
- Reset link sent to registered email
- Link expires after 1 hour
- Password requirements clearly shown
- Success confirmation displayed
- Cannot reuse recent passwords

**Gherkin Test Scenarios:**

```gherkin
Feature: Password Reset Flow
  As a user
  I want to reset my forgotten password
  So that I can regain access to my account

  Background:
    Given I am on the login page

  @critical @auth @password
  Scenario: Request password reset
    When I click "Forgot Password?"
    And I enter my email "trader@example.com"
    And I click "Send Reset Link"
    Then I should see "If an account exists, a reset link has been sent"
    And an email should be sent to "trader@example.com"
    And the email should contain a reset link

  @critical @auth @password
  Scenario: Password reset link validity
    Given I received a password reset email
    When I click the reset link within 1 hour
    Then I should be taken to the password reset page
    And the link should be valid

  @critical @auth @password
  Scenario: Expired password reset link
    Given I received a password reset email
    When I click the reset link after 1 hour
    Then I should see "This reset link has expired"
    And I should be prompted to request a new link

  @critical @auth @password
  Scenario: Set new password with requirements
    Given I am on the password reset page
    When I enter new password "NewSecure123!"
    And I confirm password "NewSecure123!"
    And I click "Reset Password"
    Then my password should be updated
    And I should see "Password successfully reset"
    And I should be redirected to login

  @critical @auth @password
  Scenario: Password requirements validation
    Given I am on the password reset page
    When I enter password "weak"
    Then I should see requirement indicators:
      | Requirement              | Status |
      | At least 8 characters    | ❌     |
      | One uppercase letter     | ❌     |
      | One lowercase letter     | ✓      |
      | One number               | ❌     |
      | One special character    | ❌     |

  @critical @auth @password
  Scenario: Password confirmation mismatch
    Given I am on the password reset page
    When I enter password "NewSecure123!"
    And I enter confirmation "DifferentPass123!"
    Then I should see "Passwords do not match"
    And the submit button should be disabled

  @critical @auth @password @security
  Scenario: Cannot reuse recent passwords
    Given my password history contains "OldSecure123!"
    When I try to set password to "OldSecure123!"
    Then I should see "Cannot reuse your last 5 passwords"
    And the password should not be changed

  @critical @auth @password @security
  Scenario: Reset link single use
    Given I successfully reset my password using a link
    When I try to use the same reset link again
    Then I should see "This link has already been used"
    And I should be prompted to request a new link
```

#### Story CP-2.5: OAuth Social Login

**Story ID:** CP-2.5
**Title:** As a user, I want to log in using my Google or Apple account so that I can access the platform without creating a new password.

**Acceptance Criteria:**
- Google OAuth login button works
- Apple OAuth login button works
- First-time social login creates account
- Existing email links to social account
- Profile photo imported from provider

**Gherkin Test Scenarios:**

```gherkin
Feature: OAuth Social Login
  As a user
  I want to log in with Google or Apple
  So that I can access the platform easily

  Background:
    Given I am on the login page

  @critical @auth @oauth
  Scenario: Successful Google login - new user
    Given I do not have an OPTIX account
    When I click "Continue with Google"
    And I authenticate with Google as "newuser@gmail.com"
    Then a new OPTIX account should be created
    And I should be redirected to the dashboard
    And my Google profile photo should be imported

  @critical @auth @oauth
  Scenario: Successful Google login - existing user
    Given I have an OPTIX account linked to Google
    When I click "Continue with Google"
    And I authenticate with Google
    Then I should be logged into my existing account
    And I should be redirected to the dashboard

  @critical @auth @oauth
  Scenario: Successful Apple login - new user
    Given I do not have an OPTIX account
    When I click "Continue with Apple"
    And I authenticate with Apple as "user@privaterelay.appleid.com"
    Then a new OPTIX account should be created
    And I should be redirected to the dashboard

  @critical @auth @oauth
  Scenario: Link social account to existing email
    Given I have an OPTIX account with email "trader@example.com"
    And the account was created with password
    When I click "Continue with Google" with same email
    Then I should be prompted to link accounts
    And after confirmation, Google should be linked
    And I can use either login method

  @critical @auth @oauth
  Scenario: Cancel OAuth flow
    When I click "Continue with Google"
    And I cancel the Google authentication
    Then I should return to the login page
    And no account should be created
    And no error should be shown

  @critical @auth @oauth
  Scenario: OAuth provider error handling
    When I click "Continue with Google"
    And Google returns an authentication error
    Then I should see "Unable to authenticate with Google"
    And I should be able to try again or use password login

  @critical @auth @oauth @security
  Scenario: OAuth state validation
    Given an OAuth flow is initiated
    When the callback is received with invalid state
    Then the authentication should be rejected
    And an error should be logged
    And user should see "Authentication failed"
```

#### Story CP-2.6: Account Settings Page

**Story ID:** CP-2.6
**Title:** As a user, I want to manage my account settings so that I can update my profile, security settings, and preferences.

**Acceptance Criteria:**
- View and edit profile information
- Change password (requires current password)
- Manage connected social accounts
- Configure notification preferences
- Enable/disable two-factor authentication

**Gherkin Test Scenarios:**

```gherkin
Feature: Account Settings Page
  As a user
  I want to manage my account settings
  So that I can control my profile and security

  Background:
    Given I am logged into the OPTIX platform
    And I navigate to the account settings page

  @critical @auth @settings
  Scenario: View profile information
    When I view the profile section
    Then I should see my name "John Trader"
    And I should see my email "trader@example.com"
    And I should see my profile photo
    And I should see my account creation date

  @critical @auth @settings
  Scenario: Update profile information
    When I click "Edit Profile"
    And I change my name to "John Q Trader"
    And I click "Save Changes"
    Then my name should be updated to "John Q Trader"
    And I should see "Profile updated successfully"

  @critical @auth @settings
  Scenario: Change password successfully
    When I click "Change Password"
    And I enter current password "OldPass123!"
    And I enter new password "NewPass456!"
    And I confirm new password "NewPass456!"
    And I click "Update Password"
    Then my password should be changed
    And I should see "Password updated successfully"
    And I should receive a confirmation email

  @critical @auth @settings
  Scenario: Change password with wrong current password
    When I click "Change Password"
    And I enter current password "WrongPass!"
    And I enter new password "NewPass456!"
    And I confirm new password "NewPass456!"
    And I click "Update Password"
    Then I should see "Current password is incorrect"
    And my password should not be changed

  @critical @auth @settings
  Scenario: View connected social accounts
    Given my account is linked to Google
    When I view the "Connected Accounts" section
    Then I should see Google is connected
    And I should see the linked email "trader@gmail.com"
    And I should see option to disconnect

  @critical @auth @settings
  Scenario: Disconnect social account
    Given my account is linked to Google
    And I have a password set
    When I click "Disconnect" next to Google
    And I confirm the disconnection
    Then Google should be disconnected
    And I can still log in with password

  @critical @auth @settings
  Scenario: Enable two-factor authentication
    When I click "Enable 2FA"
    And I scan the QR code with my authenticator app
    And I enter the 6-digit code "123456"
    And I save the backup codes
    Then 2FA should be enabled
    And I should see "Two-factor authentication enabled"

  @critical @auth @settings
  Scenario: Configure notification preferences
    When I view the "Notifications" section
    Then I should see toggles for:
      | Notification Type    | Email | Push | SMS |
      | Price Alerts         | ✓     | ✓    | ✓   |
      | Order Fills          | ✓     | ✓    | ✓   |
      | Account Security     | ✓     | -    | ✓   |
      | Marketing            | ✓     | -    | -   |
    When I toggle off "Marketing" email
    And I click "Save Preferences"
    Then my notification preferences should be saved
```

---

### 3.3 Epic: Core API Integration (CP-3)

#### Story CP-3.1: API Client Module

**Story ID:** CP-3.1
**Title:** As a developer, I want a centralized API client module so that all API calls are consistent and properly handled.

**Acceptance Criteria:**
- Centralized configuration for base URL
- Automatic auth header injection
- Request/response interceptors
- Consistent error response format
- Request cancellation support

**Gherkin Test Scenarios:**

```gherkin
Feature: API Client Module
  As a developer
  I want a centralized API client
  So that API calls are consistent and maintainable

  Background:
    Given I am using the OPTIX API client module

  @critical @api @client
  Scenario: Automatic auth header injection
    Given I am authenticated with a valid token
    When I make an API request to "/api/portfolio"
    Then the request should include "Authorization: Bearer <token>"
    And the request should proceed to the server

  @critical @api @client
  Scenario: Request without auth for public endpoints
    When I make a request to "/api/public/market-status"
    Then the request should not include Authorization header
    And the request should succeed

  @critical @api @client
  Scenario: Consistent error response format
    When the API returns a 400 error with message "Invalid symbol"
    Then the error should be parsed into standard format:
      | Field   | Value          |
      | code    | 400            |
      | message | Invalid symbol |
      | type    | VALIDATION     |

  @critical @api @client
  Scenario: Request timeout handling
    Given the API request timeout is 30 seconds
    When a request takes longer than 30 seconds
    Then the request should be aborted
    And an error with type "TIMEOUT" should be returned

  @critical @api @client
  Scenario: Request cancellation
    Given I initiate an API request
    When I navigate away from the page
    Then the pending request should be cancelled
    And no response handlers should execute

  @critical @api @client
  Scenario: Base URL configuration
    Given the base URL is configured as "https://api.optix.com"
    When I make a request to "/portfolio"
    Then the full URL should be "https://api.optix.com/portfolio"

  @critical @api @client
  Scenario: Request retry configuration
    Given retry is enabled with max 3 attempts
    When a request fails with a 503 error
    Then the request should be retried up to 3 times
    And exponential backoff should be applied
```

#### Story CP-3.2: Loading States

**Story ID:** CP-3.2
**Title:** As a user, I want to see loading indicators so that I know when data is being fetched.

**Acceptance Criteria:**
- Skeleton loaders for content areas
- Spinner for action buttons
- Progress bar for long operations
- Loading states don't block interaction with loaded content
- Consistent loading patterns across app

**Gherkin Test Scenarios:**

```gherkin
Feature: Loading States
  As a user
  I want to see loading indicators
  So that I know when data is being fetched

  @critical @ui @loading
  Scenario: Skeleton loader for data grids
    Given I navigate to the watchlist page
    When the data is being fetched
    Then I should see skeleton placeholder rows
    And the skeleton should pulse/animate
    When the data loads
    Then the skeleton should be replaced with actual data

  @critical @ui @loading
  Scenario: Button loading state
    Given I am on a form
    When I click the "Submit" button
    Then the button should show a spinner
    And the button text should change to "Submitting..."
    And the button should be disabled
    When the operation completes
    Then the button should return to normal state

  @critical @ui @loading
  Scenario: Progress bar for uploads
    Given I am uploading a file
    Then a progress bar should be visible
    And it should show percentage complete
    And it should update as upload progresses

  @critical @ui @loading
  Scenario: Partial loading does not block loaded content
    Given the dashboard has 4 widgets
    And 2 widgets have loaded
    When 2 widgets are still loading
    Then I should be able to interact with the loaded widgets
    And the loading widgets should show spinners

  @critical @ui @loading
  Scenario: Page transition loading
    When I navigate from dashboard to options page
    Then a top progress bar should appear
    And the previous content should remain visible
    Until the new page is ready to render
```

#### Story CP-3.3: Error Boundary Components

**Story ID:** CP-3.3
**Title:** As a user, I want graceful error handling so that application errors don't crash the entire page.

**Acceptance Criteria:**
- Component-level error boundaries
- User-friendly error messages
- Retry functionality for failed components
- Error logging for debugging
- Fallback UI for critical failures

**Gherkin Test Scenarios:**

```gherkin
Feature: Error Boundary Components
  As a user
  I want graceful error handling
  So that errors don't crash the entire application

  @critical @ui @error
  Scenario: Component error containment
    Given I am on the dashboard
    When the "Market Summary" widget encounters an error
    Then only that widget should show an error state
    And other widgets should continue functioning
    And a "Retry" button should appear on the failed widget

  @critical @ui @error
  Scenario: User-friendly error message
    When a component fails to load
    Then I should see "Something went wrong"
    And I should see "We couldn't load this content"
    And I should NOT see technical error stack traces

  @critical @ui @error
  Scenario: Retry failed component
    Given a widget shows an error state
    When I click the "Retry" button
    Then the widget should attempt to reload
    And if successful, normal content should display

  @critical @ui @error
  Scenario: Critical page error fallback
    When the entire page fails to render
    Then I should see a full-page error screen
    And I should see a "Return to Dashboard" link
    And I should see a "Contact Support" option

  @critical @ui @error
  Scenario: Error logging
    When any error occurs in the application
    Then the error should be logged with:
      | Field      | Value                    |
      | timestamp  | Current time             |
      | component  | Component name           |
      | error      | Error message            |
      | stack      | Stack trace              |
      | userId     | Current user ID          |
      | page       | Current page URL         |
```

#### Story CP-3.4: Toast Notification System

**Story ID:** CP-3.4
**Title:** As a user, I want toast notifications so that I receive feedback about my actions and system events.

**Acceptance Criteria:**
- Success, error, warning, info toast types
- Auto-dismiss with configurable duration
- Manual dismiss capability
- Stack multiple toasts
- Action buttons in toasts (optional)

**Gherkin Test Scenarios:**

```gherkin
Feature: Toast Notification System
  As a user
  I want toast notifications
  So that I receive feedback about actions and events

  @critical @ui @toast
  Scenario: Success toast notification
    When I successfully add a symbol to my watchlist
    Then a green success toast should appear
    And it should show "Symbol added to watchlist"
    And it should auto-dismiss after 5 seconds

  @critical @ui @toast
  Scenario: Error toast notification
    When an API request fails
    Then a red error toast should appear
    And it should show the error message
    And it should remain until manually dismissed

  @critical @ui @toast
  Scenario: Warning toast notification
    When I'm about to exceed my watchlist limit
    Then a yellow warning toast should appear
    And it should show "Approaching watchlist limit"

  @critical @ui @toast
  Scenario: Info toast notification
    When the market opens
    Then a blue info toast should appear
    And it should show "Market is now open"

  @critical @ui @toast
  Scenario: Manual toast dismissal
    Given a toast is displayed
    When I click the dismiss "X" button
    Then the toast should immediately close

  @critical @ui @toast
  Scenario: Multiple stacked toasts
    Given a success toast is displayed
    When another action triggers an error toast
    Then both toasts should be visible
    And they should be stacked vertically
    And each should manage its own lifecycle

  @critical @ui @toast
  Scenario: Toast with action button
    When I delete a symbol from watchlist
    Then a toast should appear with "Symbol removed"
    And an "Undo" action button should be present
    When I click "Undo"
    Then the deletion should be reversed

  @critical @ui @toast
  Scenario: Toast accessibility
    When a toast appears
    Then it should be announced to screen readers
    And it should be focusable for keyboard users
    And pressing Escape should dismiss it
```

#### Story CP-3.5: Retry Logic with Exponential Backoff

**Story ID:** CP-3.5
**Title:** As a user, I want failed requests to automatically retry so that transient network issues don't require manual intervention.

**Acceptance Criteria:**
- Configurable retry attempts (default 3)
- Exponential backoff (1s, 2s, 4s)
- Only retry on specific error codes (5xx, network errors)
- User notification of retry attempts
- Final failure shows clear error

**Gherkin Test Scenarios:**

```gherkin
Feature: Retry Logic with Exponential Backoff
  As a user
  I want automatic request retries
  So that transient issues resolve without manual intervention

  @critical @api @retry
  Scenario: Successful retry after transient failure
    Given an API request fails with 503 error
    When the system retries after 1 second
    And the retry succeeds
    Then the original request should complete successfully
    And no error should be shown to the user

  @critical @api @retry
  Scenario: Exponential backoff timing
    Given an API request fails
    Then retry 1 should occur after 1 second
    And retry 2 should occur after 2 seconds
    And retry 3 should occur after 4 seconds

  @critical @api @retry
  Scenario: Retry only on appropriate errors
    Given an API request fails with 500 error
    Then the request should be retried
    Given an API request fails with 400 error
    Then the request should NOT be retried
    And the error should be shown immediately

  @critical @api @retry
  Scenario: Network error retry
    Given a request fails due to network disconnection
    Then the request should be retried
    When network is restored
    Then the retry should succeed

  @critical @api @retry
  Scenario: Retry notification to user
    Given an API request fails and retries begin
    Then a subtle indicator should show "Retrying..."
    And retry count should be visible "Retry 1 of 3"

  @critical @api @retry
  Scenario: Final failure after max retries
    Given all 3 retry attempts fail
    Then an error toast should appear
    And it should show "Unable to complete request"
    And a "Try Again" button should be available

  @critical @api @retry
  Scenario: Cancel retries on page navigation
    Given a request is in retry loop
    When I navigate to a different page
    Then pending retries should be cancelled
    And no error should be shown
```

---

## 4. High Priority Stories

### 4.1 Epic: Interactive Charting Integration (HP-1)

#### Story HP-1.1: TradingView Lightweight Charts Integration

**Story ID:** HP-1.1
**Title:** As a user, I want interactive candlestick charts so that I can analyze price action visually.

**Acceptance Criteria:**
- Candlestick charts render with OHLC data
- Charts support zoom, pan, and crosshair
- Multiple timeframes available (1m, 5m, 15m, 1h, 4h, 1D, 1W)
- Drawing tools for trendlines and shapes
- Chart settings persist across sessions

**Gherkin Test Scenarios:**

```gherkin
Feature: TradingView Lightweight Charts Integration
  As a user
  I want interactive candlestick charts
  So that I can analyze price action visually

  Background:
    Given I am logged into the OPTIX platform
    And I navigate to a page with charts

  @high @charts @render
  Scenario: Candlestick chart renders correctly
    Given I select symbol "AAPL"
    When the chart loads
    Then candlesticks should display with correct OHLC data
    And green candles should indicate price increase
    And red candles should indicate price decrease
    And volume bars should appear below the chart

  @high @charts @interaction
  Scenario: Chart zoom functionality
    Given the chart is displaying daily data
    When I scroll up on the chart (mouse wheel)
    Then the chart should zoom in
    And more detail should be visible
    When I scroll down on the chart
    Then the chart should zoom out
    And more history should be visible

  @high @charts @interaction
  Scenario: Chart pan functionality
    Given the chart is zoomed in
    When I click and drag left on the chart
    Then the chart should pan to show older data
    When I click and drag right
    Then the chart should pan to show newer data

  @high @charts @crosshair
  Scenario: Crosshair displays price and time
    When I hover over a candlestick
    Then a crosshair should appear
    And the price should be shown on the Y-axis
    And the date/time should be shown on the X-axis
    And OHLC values should appear in the legend

  @high @charts @timeframe
  Scenario: Change chart timeframe
    Given the chart is showing daily candles
    When I select "1H" timeframe
    Then the chart should reload with hourly data
    And candles should represent 1-hour periods
    And the X-axis should show hourly timestamps

  @high @charts @timeframe
  Scenario Outline: Multiple timeframe support
    When I select timeframe "<timeframe>"
    Then candles should represent <period> periods
    And appropriate date format should be used

    Examples:
      | timeframe | period    |
      | 1m        | 1-minute  |
      | 5m        | 5-minute  |
      | 15m       | 15-minute |
      | 1h        | 1-hour    |
      | 4h        | 4-hour    |
      | 1D        | 1-day     |
      | 1W        | 1-week    |

  @high @charts @drawing
  Scenario: Draw trendline on chart
    When I select the "Trendline" drawing tool
    And I click on point A on the chart
    And I click on point B on the chart
    Then a trendline should be drawn between the points
    And the line should be selectable and deletable

  @high @charts @persistence
  Scenario: Chart settings persist
    Given I set chart timeframe to "4H"
    And I enable "Volume" indicator
    When I navigate away and return
    Then the timeframe should still be "4H"
    And "Volume" indicator should still be enabled

  @high @charts @performance
  Scenario: Chart performance with large dataset
    Given I load 5 years of daily data
    When the chart renders
    Then rendering should complete within 500ms
    And zoom/pan should remain smooth (60fps)
```

#### Story HP-1.2: Dashboard Candlestick Chart Component

**Story ID:** HP-1.2
**Title:** As a user, I want a chart widget on my dashboard so that I can quickly view price action for my primary symbol.

**Acceptance Criteria:**
- Compact chart widget fits dashboard grid
- Quick symbol switcher
- Mini timeframe selector
- Expandable to full-screen mode
- Shows key price levels (support/resistance)

**Gherkin Test Scenarios:**

```gherkin
Feature: Dashboard Candlestick Chart Component
  As a user
  I want a chart widget on my dashboard
  So that I can quickly view price action

  Background:
    Given I am on the dashboard page
    And the chart widget is visible

  @high @dashboard @chart
  Scenario: Chart widget displays current symbol
    Given my primary symbol is "SPY"
    When I view the chart widget
    Then it should display "SPY" candlestick chart
    And current price should be visible
    And daily change should be shown

  @high @dashboard @chart
  Scenario: Quick symbol switcher
    Given the chart shows "SPY"
    When I click on the symbol name
    And I type "AAPL"
    And I press Enter
    Then the chart should switch to "AAPL"
    And the widget title should update

  @high @dashboard @chart
  Scenario: Mini timeframe selector
    Given the chart widget is visible
    Then I should see compact timeframe buttons: 1D, 1W, 1M, 3M, 1Y
    When I click "1W"
    Then the chart should show 1 week of data

  @high @dashboard @chart
  Scenario: Expand to full-screen
    When I click the expand icon on the chart widget
    Then the chart should open in full-screen modal
    And full charting tools should be available
    When I press Escape
    Then the modal should close
    And I should return to dashboard

  @high @dashboard @chart
  Scenario: Responsive widget sizing
    Given the dashboard grid has various widget sizes
    When I resize the chart widget to be smaller
    Then the chart should adapt to the new size
    And controls should remain accessible
```

#### Story HP-1.3: IV Rank Visualization

**Story ID:** HP-1.3
**Title:** As a user, I want to see IV rank and percentile visualizations so that I can assess if options are expensive or cheap.

**Acceptance Criteria:**
- IV Rank gauge (0-100 scale)
- IV Percentile indicator
- Historical IV chart overlay
- Color coding (low/medium/high)
- Comparison to 52-week range

**Gherkin Test Scenarios:**

```gherkin
Feature: IV Rank Visualization
  As a user
  I want IV rank visualizations
  So that I can assess option pricing levels

  Background:
    Given I am on the options chain page
    And I have selected symbol "AAPL"

  @high @iv @visualization
  Scenario: IV Rank gauge display
    Given AAPL has IV Rank of 35
    Then the IV Rank gauge should show 35
    And the gauge should be on a 0-100 scale
    And the current value should be highlighted

  @high @iv @visualization
  Scenario: IV Rank color coding
    Given the IV Rank gauge is displayed
    When IV Rank is below 25
    Then the gauge should be colored green (low IV)
    When IV Rank is between 25 and 75
    Then the gauge should be colored yellow (medium IV)
    When IV Rank is above 75
    Then the gauge should be colored red (high IV)

  @high @iv @visualization
  Scenario: IV Percentile display
    Given AAPL has IV Percentile of 42%
    Then the IV Percentile should display "42%"
    And tooltip should explain "IV is higher than 42% of readings in past year"

  @high @iv @visualization
  Scenario: Historical IV chart
    When I view the IV history section
    Then a line chart should show IV over time
    And current IV level should be marked
    And 52-week high and low should be indicated

  @high @iv @comparison
  Scenario: 52-week IV comparison
    Given AAPL current IV is 28%
    And 52-week low IV is 18%
    And 52-week high IV is 65%
    Then the display should show:
      | Metric        | Value |
      | Current IV    | 28%   |
      | 52W Low       | 18%   |
      | 52W High      | 65%   |
      | IV Rank       | 21    |
```

#### Story HP-1.4: P&L Payoff Diagram

**Story ID:** HP-1.4
**Title:** As a user, I want to see payoff diagrams for my strategies so that I can visualize profit and loss scenarios.

**Acceptance Criteria:**
- Interactive payoff curve
- Break-even points marked
- Max profit/loss indicated
- Multiple expiration scenarios
- Greeks sensitivity display

**Gherkin Test Scenarios:**

```gherkin
Feature: P&L Payoff Diagram
  As a user
  I want payoff diagrams for strategies
  So that I can visualize profit/loss scenarios

  Background:
    Given I am on the strategy builder page
    And I have constructed a bull call spread
    With long 100 call at $5.00 and short 105 call at $2.00

  @high @strategy @payoff
  Scenario: Payoff curve renders correctly
    When I view the payoff diagram
    Then a line chart should display
    And X-axis should show underlying price range
    And Y-axis should show P&L in dollars
    And the payoff curve should be accurate for the spread

  @high @strategy @payoff
  Scenario: Break-even points marked
    Given the net debit is $3.00
    When I view the payoff diagram
    Then break-even at $103 should be marked
    And a vertical line should indicate the break-even
    And label should show "BE: $103.00"

  @high @strategy @payoff
  Scenario: Max profit and loss indicated
    When I view the payoff diagram
    Then max profit of $200 should be labeled at $105+
    And max loss of $300 should be labeled below $100
    And these zones should be color-coded

  @high @strategy @payoff
  Scenario: Current price marker
    Given the underlying is at $102
    When I view the payoff diagram
    Then a vertical marker should show current price
    And current P&L at that price should be displayed

  @high @strategy @payoff
  Scenario: Expiration scenario slider
    When I move the "Days to Expiration" slider
    Then the payoff curve should update
    And time decay effect should be visible
    And current theoretical value should update

  @high @strategy @payoff
  Scenario: Interactive hover details
    When I hover over the payoff curve
    Then a tooltip should show:
      | Field           | Example Value |
      | Underlying Price| $103.50       |
      | P&L             | +$50          |
      | Return on Risk  | +16.7%        |

  @high @strategy @greeks
  Scenario: Greeks sensitivity display
    When I view the Greeks panel
    Then position Greeks should show:
      | Greek | Value |
      | Delta | 0.45  |
      | Gamma | 0.02  |
      | Theta | -0.15 |
      | Vega  | 0.12  |
```

#### Story HP-1.5: Equity Curve Chart

**Story ID:** HP-1.5
**Title:** As a user, I want to see my equity curve so that I can track portfolio performance over time.

**Acceptance Criteria:**
- Line chart showing portfolio value over time
- Drawdown visualization
- Benchmark comparison (SPY)
- Custom date range selection
- Export chart as image

**Gherkin Test Scenarios:**

```gherkin
Feature: Equity Curve Chart
  As a user
  I want to see my equity curve
  So that I can track portfolio performance over time

  Background:
    Given I am on the performance page
    And I have trading history

  @high @performance @equity
  Scenario: Equity curve renders
    When I view the equity curve section
    Then a line chart should display portfolio value
    And X-axis should show dates
    And Y-axis should show dollar values
    And the line should be smooth and continuous

  @high @performance @equity
  Scenario: Drawdown visualization
    When I enable "Show Drawdowns"
    Then drawdown periods should be shaded red
    And maximum drawdown should be labeled
    And drawdown percentage should be visible

  @high @performance @equity
  Scenario: Benchmark comparison
    When I enable "Compare to SPY"
    Then a second line for SPY should appear
    And both lines should be normalized to same starting point
    And legend should distinguish both lines

  @high @performance @equity
  Scenario: Custom date range selection
    When I select date range "Last 6 Months"
    Then the chart should show only last 6 months
    And statistics should recalculate for that period

    When I set custom range from "2024-01-01" to "2024-06-30"
    Then the chart should show that exact range

  @high @performance @equity
  Scenario: Export chart
    When I click "Export" button
    Then I should see options for PNG, SVG, PDF
    When I select "PNG"
    Then the chart should download as an image file

  @high @performance @equity
  Scenario: Key statistics display
    When viewing the equity curve
    Then key statistics should be visible:
      | Metric           | Example  |
      | Total Return     | +45.2%   |
      | Sharpe Ratio     | 1.85     |
      | Max Drawdown     | -12.3%   |
      | Win Rate         | 62%      |
      | Profit Factor    | 2.1      |
```

#### Story HP-1.6: GEX Heatmap Visualization

**Story ID:** HP-1.6
**Title:** As a user, I want GEX heatmap visualizations so that I can identify key gamma levels and market maker positioning.

**Acceptance Criteria:**
- 2D heatmap of gamma exposure by strike
- Color intensity indicates gamma magnitude
- Gamma flip level clearly marked
- Interactive hover showing exact values
- Time-lapse animation for historical GEX

**Gherkin Test Scenarios:**

```gherkin
Feature: GEX Heatmap Visualization
  As a user
  I want GEX heatmap visualizations
  So that I can identify key gamma levels

  Background:
    Given I am on the GEX analysis page
    And I have selected symbol "SPY"

  @high @gex @heatmap
  Scenario: GEX heatmap renders
    When the GEX data loads
    Then a heatmap should display
    And X-axis should show strike prices
    And color intensity should indicate gamma magnitude
    And positive gamma should be green
    And negative gamma should be red

  @high @gex @heatmap
  Scenario: Gamma flip level indication
    Given the gamma flip level is at $448
    When I view the heatmap
    Then the $448 level should be prominently marked
    And a label should indicate "Gamma Flip: $448"
    And a horizontal line should cross the heatmap

  @high @gex @heatmap
  Scenario: Interactive hover details
    When I hover over a cell in the heatmap
    Then a tooltip should display:
      | Field          | Example    |
      | Strike         | $450       |
      | Call GEX       | +$2.5B     |
      | Put GEX        | -$1.2B     |
      | Net GEX        | +$1.3B     |
      | Call OI        | 125,000    |
      | Put OI         | 89,000     |

  @high @gex @heatmap
  Scenario: Key levels summary
    When I view the GEX summary panel
    Then I should see:
      | Level              | Strike |
      | Max Positive Gamma | $450   |
      | Max Negative Gamma | $440   |
      | Gamma Flip         | $448   |
      | High Vol Zone      | $445-455|

  @high @gex @heatmap
  Scenario: Historical GEX animation
    When I click "Play History"
    Then the heatmap should animate through historical data
    And I should see how GEX evolved over time
    And playback controls should be available (play/pause/speed)

  @high @gex @heatmap
  Scenario: Call vs Put breakdown toggle
    When I toggle to "Calls Only"
    Then only call gamma should display
    When I toggle to "Puts Only"
    Then only put gamma should display
    When I toggle to "Net"
    Then combined net gamma should display
```

---

### 4.2 Epic: Backtester UI (HP-2)

#### Story HP-2.1: Backtester Page Layout

**Story ID:** HP-2.1
**Title:** As a user, I want a dedicated backtester page so that I can test my trading strategies against historical data.

**Acceptance Criteria:**
- Clear page layout with configuration and results sections
- Navigation from main menu
- Responsive design for various screens
- Loading states during backtest execution
- Help/documentation access

**Gherkin Test Scenarios:**

```gherkin
Feature: Backtester Page Layout
  As a user
  I want a dedicated backtester page
  So that I can test my trading strategies

  Background:
    Given I am logged into the OPTIX platform

  @high @backtester @layout
  Scenario: Navigate to backtester page
    When I click "Backtester" in the main navigation
    Then I should be taken to the backtester page
    And the page should have a clear layout
    And I should see strategy configuration section
    And I should see results display section

  @high @backtester @layout
  Scenario: Page sections visible
    When I am on the backtester page
    Then I should see these sections:
      | Section              | Purpose                    |
      | Strategy Selection   | Choose strategy to test    |
      | Date Range           | Set backtest period        |
      | Parameters           | Configure strategy params  |
      | Run Controls         | Start/stop backtest        |
      | Results Dashboard    | View backtest results      |
      | Trade History        | See individual trades      |

  @high @backtester @layout
  Scenario: Responsive layout
    When I view on desktop (1920px)
    Then configuration and results should be side-by-side
    When I view on tablet (768px)
    Then sections should stack vertically

  @high @backtester @layout
  Scenario: Loading state during execution
    When I start a backtest
    Then a progress indicator should appear
    And estimated time remaining should display
    And I should be able to cancel the backtest

  @high @backtester @layout
  Scenario: Help documentation access
    When I click the help icon
    Then documentation for backtesting should open
    And it should explain how to use the backtester
```

#### Story HP-2.2: Strategy Selection Panel

**Story ID:** HP-2.2
**Title:** As a user, I want to select from predefined strategies or custom strategies so that I can choose what to backtest.

**Acceptance Criteria:**
- List of predefined strategies with descriptions
- Custom strategy import capability
- Strategy parameter preview
- Favorite strategies list
- Strategy search/filter

**Gherkin Test Scenarios:**

```gherkin
Feature: Strategy Selection Panel
  As a user
  I want to select strategies for backtesting
  So that I can test different approaches

  Background:
    Given I am on the backtester page
    And I am in the strategy selection panel

  @high @backtester @strategy
  Scenario: View predefined strategies
    When I view the strategy list
    Then I should see predefined strategies:
      | Strategy          | Type    |
      | Iron Condor       | Income  |
      | Butterfly Spread  | Income  |
      | Vertical Spread   | Directional |
      | Straddle          | Volatility |
      | Covered Call      | Income  |
      | Wheel Strategy    | Income  |

  @high @backtester @strategy
  Scenario: Strategy description and preview
    When I click on "Iron Condor" strategy
    Then a description panel should expand
    And I should see:
      | Field       | Content                           |
      | Description | Sell OTM strangle, buy further OTM|
      | Best For    | Range-bound markets               |
      | Risk        | Defined risk, limited profit      |
      | Parameters  | Wing width, delta targets         |

  @high @backtester @strategy
  Scenario: Select strategy for backtest
    When I click "Select" on Iron Condor
    Then Iron Condor should be set as active strategy
    And parameter configuration should become available
    And strategy name should appear in the header

  @high @backtester @strategy
  Scenario: Import custom strategy
    When I click "Import Custom Strategy"
    And I upload a strategy definition file
    Then the strategy should appear in "My Strategies"
    And I should be able to select it for backtesting

  @high @backtester @strategy
  Scenario: Add strategy to favorites
    When I click the star icon on "Iron Condor"
    Then Iron Condor should be added to favorites
    And it should appear in "Favorite Strategies" section

  @high @backtester @strategy
  Scenario: Search and filter strategies
    When I type "spread" in the search box
    Then only strategies containing "spread" should show
    When I filter by type "Income"
    Then only income strategies should display
```

#### Story HP-2.3: Date Range Picker

**Story ID:** HP-2.3
**Title:** As a user, I want to select a date range for my backtest so that I can test strategies over specific time periods.

**Acceptance Criteria:**
- Calendar picker for start/end dates
- Preset ranges (1Y, 2Y, 5Y, All)
- Date validation (start before end)
- Market calendar awareness (excludes weekends/holidays)
- Visual indicator of selected range

**Gherkin Test Scenarios:**

```gherkin
Feature: Date Range Picker
  As a user
  I want to select date ranges for backtesting
  So that I can test strategies over specific periods

  Background:
    Given I am on the backtester page
    And I am configuring a backtest

  @high @backtester @daterange
  Scenario: Select custom date range
    When I click on the start date field
    And I select "January 1, 2020"
    And I click on the end date field
    And I select "December 31, 2023"
    Then the date range should be "Jan 1, 2020 - Dec 31, 2023"
    And the data points indicator should show available data

  @high @backtester @daterange
  Scenario: Use preset date ranges
    When I click "2Y" preset button
    Then the range should be set to last 2 years
    When I click "5Y" preset button
    Then the range should be set to last 5 years
    When I click "All" preset button
    Then all available historical data should be selected

  @high @backtester @daterange
  Scenario: Date validation
    When I set start date to "June 1, 2024"
    And I set end date to "January 1, 2024"
    Then I should see error "Start date must be before end date"
    And the backtest should not be runnable

  @high @backtester @daterange
  Scenario: Future date prevention
    When I try to select a future date
    Then future dates should be disabled in the picker
    And I should not be able to select them

  @high @backtester @daterange
  Scenario: Market calendar display
    When I view the date picker
    Then weekends should be grayed out
    And major market holidays should be indicated
    And only trading days should be selectable
```

#### Story HP-2.4: Parameter Configuration Form

**Story ID:** HP-2.4
**Title:** As a user, I want to configure strategy parameters so that I can customize how the strategy operates during backtesting.

**Acceptance Criteria:**
- Dynamic form based on selected strategy
- Input validation with helpful errors
- Parameter descriptions/tooltips
- Default values provided
- Parameter presets/profiles

**Gherkin Test Scenarios:**

```gherkin
Feature: Parameter Configuration Form
  As a user
  I want to configure strategy parameters
  So that I can customize the backtest

  Background:
    Given I am on the backtester page
    And I have selected "Iron Condor" strategy

  @high @backtester @params
  Scenario: View strategy parameters
    When I view the parameter form
    Then I should see configuration options:
      | Parameter         | Type    | Default |
      | Days to Expiration| Number  | 45      |
      | Short Put Delta   | Number  | -0.16   |
      | Short Call Delta  | Number  | 0.16    |
      | Wing Width        | Number  | 5       |
      | Position Size     | Percent | 10%     |
      | Profit Target     | Percent | 50%     |
      | Stop Loss         | Percent | 200%    |

  @high @backtester @params
  Scenario: Parameter tooltips
    When I hover over "Wing Width" label
    Then a tooltip should appear explaining
    "Distance in strikes between short and long options"

  @high @backtester @params
  Scenario: Input validation
    When I enter "150" for Short Put Delta
    Then I should see error "Delta must be between -1 and 0"
    When I enter "-0.30" for Short Put Delta
    Then the input should be accepted

  @high @backtester @params
  Scenario: Load parameter preset
    When I click "Load Preset"
    And I select "Conservative Settings"
    Then parameters should populate with conservative values
    And I should see "Preset: Conservative" indicator

  @high @backtester @params
  Scenario: Save custom preset
    When I configure custom parameters
    And I click "Save as Preset"
    And I name it "My Iron Condor Settings"
    Then the preset should be saved
    And it should appear in my presets list

  @high @backtester @params
  Scenario: Reset to defaults
    When I modify several parameters
    And I click "Reset to Defaults"
    Then all parameters should return to default values
```

#### Story HP-2.5: Results Dashboard

**Story ID:** HP-2.5
**Title:** As a user, I want a comprehensive results dashboard so that I can evaluate backtest performance.

**Acceptance Criteria:**
- Key performance metrics displayed prominently
- Equity curve visualization
- Monthly returns heatmap
- Drawdown analysis
- Comparison with benchmarks

**Gherkin Test Scenarios:**

```gherkin
Feature: Backtest Results Dashboard
  As a user
  I want a comprehensive results dashboard
  So that I can evaluate backtest performance

  Background:
    Given I have run a backtest
    And results are available

  @high @backtester @results
  Scenario: Key metrics display
    When I view the results dashboard
    Then I should see key metrics:
      | Metric              | Example Value |
      | Total Return        | +156.3%       |
      | CAGR                | 24.5%         |
      | Sharpe Ratio        | 1.87          |
      | Sortino Ratio       | 2.34          |
      | Max Drawdown        | -18.2%        |
      | Win Rate            | 68%           |
      | Profit Factor       | 2.15          |
      | Total Trades        | 142           |
      | Average Trade       | +$245         |

  @high @backtester @results
  Scenario: Equity curve visualization
    When I view the equity curve
    Then I should see portfolio value over time
    And starting value should be initial capital
    And ending value should reflect total return
    And underwater/drawdown periods should be visible

  @high @backtester @results
  Scenario: Monthly returns heatmap
    When I view the monthly returns
    Then a calendar heatmap should display
    And green cells should indicate positive months
    And red cells should indicate negative months
    And intensity should reflect magnitude

  @high @backtester @results
  Scenario: Drawdown analysis
    When I view the drawdown section
    Then I should see:
      | Drawdown     | Start Date | End Date   | Recovery |
      | -18.2%       | 2022-02-15 | 2022-06-30 | 95 days  |
      | -12.1%       | 2023-03-01 | 2023-04-15 | 32 days  |

  @high @backtester @results
  Scenario: Benchmark comparison
    When I enable "Compare to SPY"
    Then SPY returns should overlay on equity curve
    And relative performance stats should display
    And alpha/beta should be calculated
```

#### Story HP-2.6: Trade History Table

**Story ID:** HP-2.6
**Title:** As a user, I want to see individual trades from the backtest so that I can analyze specific entries and exits.

**Acceptance Criteria:**
- Sortable, filterable table of trades
- Entry/exit prices and dates
- P&L for each trade
- Trade details expandable
- Export to CSV

**Gherkin Test Scenarios:**

```gherkin
Feature: Trade History Table
  As a user
  I want to see individual trades from backtest
  So that I can analyze specific entries and exits

  Background:
    Given I have completed a backtest
    And I am viewing the trade history section

  @high @backtester @trades
  Scenario: Trade table displays
    When I view the trade history
    Then a table should show all trades with columns:
      | Column       | Description           |
      | #            | Trade number          |
      | Entry Date   | Date position opened  |
      | Exit Date    | Date position closed  |
      | Symbol       | Underlying symbol     |
      | Strategy     | Strategy type         |
      | Entry Price  | Net debit/credit      |
      | Exit Price   | Closing price         |
      | P&L          | Profit/Loss           |
      | Return       | Percentage return     |
      | Duration     | Days held             |

  @high @backtester @trades
  Scenario: Sort trades by column
    When I click on "P&L" column header
    Then trades should sort by P&L descending
    When I click again
    Then trades should sort by P&L ascending

  @high @backtester @trades
  Scenario: Filter trades
    When I filter by "Winners Only"
    Then only profitable trades should display
    When I filter by "Losers Only"
    Then only losing trades should display
    When I filter date range to "2023"
    Then only 2023 trades should display

  @high @backtester @trades
  Scenario: Expand trade details
    When I click on a trade row
    Then trade details should expand showing:
      | Detail           | Information              |
      | Legs             | All option legs in trade |
      | Entry Greeks     | Delta, Gamma, Theta, Vega|
      | Exit Reason      | Profit target, stop, exp |
      | Chart            | Price chart at entry/exit|

  @high @backtester @trades
  Scenario: Export trade history
    When I click "Export to CSV"
    Then a CSV file should download
    And it should contain all visible trades
    And all columns should be included
```

#### Story HP-2.7: Monte Carlo Simulation Display

**Story ID:** HP-2.7
**Title:** As a user, I want to see Monte Carlo simulation results so that I can understand the range of possible outcomes.

**Acceptance Criteria:**
- Multiple simulation paths visualized
- Confidence intervals shown (5th, 50th, 95th percentile)
- Distribution of final outcomes
- Risk of ruin calculation
- Adjustable number of simulations

**Gherkin Test Scenarios:**

```gherkin
Feature: Monte Carlo Simulation Display
  As a user
  I want Monte Carlo simulation results
  So that I can understand outcome probability ranges

  Background:
    Given I have completed a backtest
    And I navigate to Monte Carlo section

  @high @backtester @montecarlo
  Scenario: Run Monte Carlo simulation
    When I click "Run Monte Carlo"
    And simulations are processing
    Then a progress indicator should show
    And number of completed simulations should update
    When complete, results should display

  @high @backtester @montecarlo
  Scenario: Simulation paths visualization
    When I view the Monte Carlo chart
    Then I should see multiple equity curves
    And each represents a randomized sequence
    And curves should fan out from starting point

  @high @backtester @montecarlo
  Scenario: Confidence intervals
    When I view the confidence bands
    Then I should see:
      | Percentile | Ending Value | Color  |
      | 5th        | $85,000      | Red    |
      | 50th       | $145,000     | Yellow |
      | 95th       | $220,000     | Green  |

  @high @backtester @montecarlo
  Scenario: Outcome distribution histogram
    When I view the distribution chart
    Then a histogram should show final values
    And mean and median should be marked
    And I should see probability of profit

  @high @backtester @montecarlo
  Scenario: Risk of ruin calculation
    Given my account size is $100,000
    When risk of ruin is calculated
    Then I should see:
      | Metric                 | Value |
      | Risk of 20% Drawdown   | 35%   |
      | Risk of 50% Drawdown   | 8%    |
      | Risk of Ruin (90% loss)| 0.5%  |

  @high @backtester @montecarlo
  Scenario: Adjust simulation parameters
    When I set number of simulations to 10,000
    And I click "Re-run"
    Then simulations should run with new count
    And results should update
```

---

### 4.3 Epic: Trading Journal UI (HP-3)

#### Story HP-3.1: Journal Page Layout

**Story ID:** HP-3.1
**Title:** As a user, I want a dedicated trading journal page so that I can record and review my trades.

**Acceptance Criteria:**
- Clean, intuitive page layout
- Quick entry form always accessible
- Journal entries list/calendar view
- Search and filter capabilities
- Export functionality

**Gherkin Test Scenarios:**

```gherkin
Feature: Trading Journal Page Layout
  As a user
  I want a dedicated trading journal page
  So that I can record and review my trades

  Background:
    Given I am logged into the OPTIX platform

  @high @journal @layout
  Scenario: Navigate to journal page
    When I click "Journal" in the navigation
    Then I should be taken to the trading journal page
    And I should see the journal entries list
    And a "New Entry" button should be visible

  @high @journal @layout
  Scenario: Page sections
    When I view the journal page
    Then I should see:
      | Section        | Purpose                    |
      | Entry List     | View past journal entries  |
      | Quick Entry    | Fast trade logging         |
      | Calendar View  | Visual trade calendar      |
      | Statistics     | Journal analytics          |
      | Search/Filter  | Find specific entries      |

  @high @journal @layout
  Scenario: View toggle between list and calendar
    Given I am viewing the list view
    When I click "Calendar View"
    Then I should see a calendar with trade markers
    When I click "List View"
    Then I should return to chronological list

  @high @journal @layout
  Scenario: Responsive design
    When I view on mobile
    Then the layout should be single column
    And touch interactions should work properly
```

#### Story HP-3.2: Trade Entry Form

**Story ID:** HP-3.2
**Title:** As a user, I want a rich trade entry form so that I can log detailed information about my trades.

**Acceptance Criteria:**
- Symbol, strategy, and P&L fields
- Rich text notes with formatting
- Image/screenshot attachment
- Emotion/mindset tagging
- Auto-import from positions

**Gherkin Test Scenarios:**

```gherkin
Feature: Trade Entry Form
  As a user
  I want a rich trade entry form
  So that I can log detailed trade information

  Background:
    Given I am on the trading journal page
    And I click "New Entry"

  @high @journal @entry
  Scenario: Basic trade information
    When I fill out the entry form
    Then I should be able to enter:
      | Field          | Input Type    |
      | Symbol         | Symbol picker |
      | Entry Date     | Date picker   |
      | Exit Date      | Date picker   |
      | Strategy       | Dropdown      |
      | Entry Price    | Currency      |
      | Exit Price     | Currency      |
      | Position Size  | Number        |
      | P&L            | Auto-calc     |

  @high @journal @entry
  Scenario: Rich text notes
    When I focus on the notes field
    Then I should have formatting options:
      | Format     | Shortcut    |
      | Bold       | Ctrl+B      |
      | Italic     | Ctrl+I      |
      | Bullet List| Ctrl+Shift+8|
      | Numbered   | Ctrl+Shift+7|
      | Heading    | Ctrl+H      |

  @high @journal @entry
  Scenario: Attach screenshots
    When I click "Attach Image"
    And I select a chart screenshot
    Then the image should upload
    And a thumbnail should appear in the entry
    And I can add a caption

  @high @journal @entry
  Scenario: Emotion tagging
    When I view the emotion section
    Then I should see emotion options:
      | Emotion    | Icon |
      | Confident  | 😊   |
      | Fearful    | 😰   |
      | Greedy     | 🤑   |
      | FOMO       | 😫   |
      | Revenge    | 😤   |
      | Calm       | 😌   |

  @high @journal @entry
  Scenario: Auto-import closed position
    When I click "Import from Positions"
    And I select a recently closed trade
    Then the form should auto-populate with:
      | Field       | Value                    |
      | Symbol      | From position            |
      | Entry/Exit  | Actual dates             |
      | Prices      | Entry/exit prices        |
      | P&L         | Actual P&L               |

  @high @journal @entry
  Scenario: Save journal entry
    When I complete the form
    And I click "Save Entry"
    Then the entry should be saved
    And I should see "Entry saved successfully"
    And the entry should appear in my journal list
```

#### Story HP-3.3: Trade Tagging System

**Story ID:** HP-3.3
**Title:** As a user, I want to tag my trades so that I can categorize and analyze them by different criteria.

**Acceptance Criteria:**
- Predefined tag categories
- Custom tag creation
- Multiple tags per entry
- Tag-based filtering
- Tag analytics/breakdown

**Gherkin Test Scenarios:**

```gherkin
Feature: Trade Tagging System
  As a user
  I want to tag my trades
  So that I can categorize and analyze them

  Background:
    Given I am creating or editing a journal entry

  @high @journal @tags
  Scenario: View predefined tags
    When I view the tags section
    Then I should see predefined categories:
      | Category     | Tags                           |
      | Setup Type   | Breakout, Reversal, Trend      |
      | Timeframe    | Scalp, Day, Swing              |
      | Market       | Bullish, Bearish, Neutral      |
      | Result       | Winner, Loser, Scratch         |
      | Mistake      | Oversize, Early Exit, Late Entry|

  @high @journal @tags
  Scenario: Add tags to entry
    When I click on "Breakout" tag
    And I click on "Swing" tag
    And I click on "Winner" tag
    Then all three tags should be applied
    And tags should display as pills on the entry

  @high @journal @tags
  Scenario: Create custom tag
    When I click "Add Custom Tag"
    And I type "Earnings Play"
    And I press Enter
    Then "Earnings Play" tag should be created
    And it should be applied to the entry
    And it should be available for future entries

  @high @journal @tags
  Scenario: Filter by tags
    When I am in the journal list view
    And I click on filter
    And I select "Winner" tag
    Then only entries with "Winner" tag should display

  @high @journal @tags
  Scenario: Tag analytics
    When I view journal statistics
    Then I should see tag breakdown:
      | Tag      | Count | Win Rate | Avg P&L |
      | Breakout | 45    | 62%      | +$320   |
      | Reversal | 28    | 54%      | +$180   |
```

#### Story HP-3.4: Calendar View

**Story ID:** HP-3.4
**Title:** As a user, I want a calendar view of my trades so that I can see my trading activity over time.

**Acceptance Criteria:**
- Monthly calendar grid
- Daily P&L color coding
- Click to view day's trades
- Navigate between months
- Weekly/monthly summary stats

**Gherkin Test Scenarios:**

```gherkin
Feature: Journal Calendar View
  As a user
  I want a calendar view of trades
  So that I can visualize trading activity over time

  Background:
    Given I am on the trading journal page
    And I select "Calendar View"

  @high @journal @calendar
  Scenario: Monthly calendar display
    When I view the calendar
    Then I should see the current month
    And days should be arranged in a grid
    And trading days should have indicators

  @high @journal @calendar
  Scenario: Daily P&L color coding
    Given December 15 had +$500 P&L
    And December 16 had -$200 P&L
    And December 17 had no trades
    Then December 15 should be green
    And December 16 should be red
    And December 17 should be neutral/gray

  @high @journal @calendar
  Scenario: Click to view day details
    When I click on December 15
    Then a detail panel should expand
    And I should see all trades from that day
    And total P&L for the day should display

  @high @journal @calendar
  Scenario: Navigate between months
    When I click the right arrow
    Then I should see next month
    When I click the left arrow
    Then I should return to current month
    When I click on month name
    Then a month picker should appear

  @high @journal @calendar
  Scenario: Monthly summary statistics
    When viewing a month
    Then I should see monthly stats:
      | Metric         | Value   |
      | Total P&L      | +$3,450 |
      | Trading Days   | 18      |
      | Win Rate       | 65%     |
      | Best Day       | +$890   |
      | Worst Day      | -$320   |
```

#### Story HP-3.5: AI Trade Analysis

**Story ID:** HP-3.5
**Title:** As a user, I want AI-powered analysis of my trades so that I can gain insights into my trading patterns.

**Acceptance Criteria:**
- Pattern recognition in trading behavior
- Mistake identification
- Strength/weakness analysis
- Personalized improvement suggestions
- Trend analysis over time

**Gherkin Test Scenarios:**

```gherkin
Feature: AI Trade Analysis
  As a user
  I want AI-powered trade analysis
  So that I can gain insights into my patterns

  Background:
    Given I have at least 20 journal entries
    And I navigate to the AI Analysis section

  @high @journal @ai
  Scenario: Generate AI analysis
    When I click "Generate Analysis"
    Then the AI should analyze my trading history
    And a comprehensive report should be generated
    And key insights should be highlighted

  @high @journal @ai
  Scenario: Pattern recognition
    When AI analyzes my trades
    Then it should identify patterns like:
      | Pattern                    | Finding                    |
      | Best performing days       | Tuesdays (72% win rate)    |
      | Worst performing strategy  | Reversals (45% win rate)   |
      | Optimal hold time          | 3-5 days (best returns)    |
      | Overtrading indicator      | >5 trades/day reduces wins |

  @high @journal @ai
  Scenario: Mistake identification
    When AI reviews losing trades
    Then it should identify common mistakes:
      | Mistake Type    | Frequency | Impact     |
      | Early exits     | 28%       | -$2,450    |
      | Oversizing      | 15%       | -$1,800    |
      | FOMO entries    | 12%       | -$980      |

  @high @journal @ai
  Scenario: Improvement suggestions
    When I view recommendations
    Then I should see actionable advice:
      | Suggestion                                    | Priority |
      | Reduce position size on reversal trades       | High     |
      | Implement trailing stops for trend trades     | Medium   |
      | Avoid trading first 30 min after market open  | Medium   |

  @high @journal @ai
  Scenario: Trend analysis
    When I view my performance trend
    Then I should see metrics over time:
      | Period    | Win Rate | Avg P&L | Sharpe |
      | Q1 2024   | 58%      | +$180   | 1.2    |
      | Q2 2024   | 62%      | +$220   | 1.5    |
      | Q3 2024   | 65%      | +$280   | 1.8    |
```

---

### 4.4 Epic: Volatility Compass UI (HP-4)

#### Story HP-4.1: Volatility Dashboard

**Story ID:** HP-4.1
**Title:** As a user, I want a volatility dashboard so that I can monitor IV levels across my watchlist.

**Acceptance Criteria:**
- IV overview for multiple symbols
- IV rank/percentile sorting
- Historical IV trends
- Volatility alerts indicator
- Symbol comparison capability

**Gherkin Test Scenarios:**

```gherkin
Feature: Volatility Dashboard
  As a user
  I want a volatility dashboard
  So that I can monitor IV levels across symbols

  Background:
    Given I am logged into the OPTIX platform
    And I navigate to the Volatility page

  @high @volatility @dashboard
  Scenario: View IV overview
    When I view the volatility dashboard
    Then I should see a table of symbols with:
      | Column       | Description          |
      | Symbol       | Stock ticker         |
      | Current IV   | Current implied vol  |
      | IV Rank      | 0-100 scale          |
      | IV Percentile| Historical percentile|
      | 30-Day Change| IV change            |
      | Status       | High/Normal/Low      |

  @high @volatility @dashboard
  Scenario: Sort by IV Rank
    When I click "IV Rank" column header
    Then symbols should sort by IV Rank descending
    And highest IV Rank should appear first

  @high @volatility @dashboard
  Scenario: Filter high IV opportunities
    When I click "High IV Only" filter
    Then only symbols with IV Rank > 50 should display

  @high @volatility @dashboard
  Scenario: Mini IV chart per symbol
    When I hover over a symbol row
    Then a mini sparkline should show 30-day IV trend

  @high @volatility @dashboard
  Scenario: Add symbol to comparison
    When I check the box next to "AAPL"
    And I check the box next to "MSFT"
    And I click "Compare"
    Then a comparison view should open
    And both symbols' IV should be charted together
```

#### Story HP-4.2: Volatility Surface 3D Visualization

**Story ID:** HP-4.2
**Title:** As a user, I want to see a 3D volatility surface so that I can analyze IV across strikes and expirations.

**Acceptance Criteria:**
- 3D surface plot with IV as height
- X-axis: Strike prices
- Y-axis: Days to expiration
- Interactive rotation and zoom
- Color gradient for IV levels

**Gherkin Test Scenarios:**

```gherkin
Feature: Volatility Surface 3D Visualization
  As a user
  I want a 3D volatility surface
  So that I can analyze IV structure

  Background:
    Given I am on the volatility page
    And I select symbol "SPY"

  @high @volatility @surface
  Scenario: 3D surface renders
    When I view the volatility surface
    Then a 3D plot should display
    And X-axis should show strike prices
    And Y-axis should show days to expiration
    And Z-axis (height) should show IV
    And surface should be colored by IV level

  @high @volatility @surface
  Scenario: Interactive rotation
    When I click and drag on the surface
    Then the view should rotate
    And I can view from different angles

  @high @volatility @surface
  Scenario: Zoom functionality
    When I scroll on the surface
    Then I should zoom in/out
    And detail should increase when zoomed in

  @high @volatility @surface
  Scenario: Hover data display
    When I hover over a point on the surface
    Then I should see:
      | Field      | Example |
      | Strike     | $450    |
      | DTE        | 30      |
      | IV         | 22.5%   |

  @high @volatility @surface
  Scenario: Skew visualization
    When viewing the surface
    Then I should be able to see:
      | Feature        | Visualization              |
      | Put skew       | Higher IV on left (OTM puts)|
      | Term structure | IV change across DTE        |
      | Smile          | U-shape across strikes     |
```

#### Story HP-4.3: IV Crush Calendar

**Story ID:** HP-4.3
**Title:** As a user, I want an IV crush calendar so that I can see upcoming earnings and expected volatility changes.

**Acceptance Criteria:**
- Calendar showing earnings dates
- Expected IV drop after earnings
- Historical IV crush data
- Trade ideas for IV plays
- Alert setup for events

**Gherkin Test Scenarios:**

```gherkin
Feature: IV Crush Calendar
  As a user
  I want an IV crush calendar
  So that I can plan volatility trades around events

  Background:
    Given I am on the volatility page
    And I view the IV Crush Calendar section

  @high @volatility @earnings
  Scenario: View earnings calendar
    When I view the calendar
    Then I should see upcoming earnings with:
      | Column          | Description              |
      | Date            | Earnings date            |
      | Symbol          | Company ticker           |
      | Time            | Before/After market      |
      | Current IV      | Pre-earnings IV          |
      | Expected Crush  | Projected IV drop        |
      | Historical Crush| Past earnings IV drops   |

  @high @volatility @earnings
  Scenario: Expected IV crush calculation
    Given AAPL reports earnings tomorrow
    And current IV is 45%
    And historical average post-earnings IV is 28%
    Then expected crush should show ~17% (45% - 28%)

  @high @volatility @earnings
  Scenario: Historical IV crush data
    When I click on "AAPL" in the calendar
    Then I should see past 4 earnings:
      | Date       | Pre-IV | Post-IV | Crush  |
      | Q3 2024    | 42%    | 25%     | -17%   |
      | Q2 2024    | 38%    | 24%     | -14%   |
      | Q1 2024    | 45%    | 28%     | -17%   |
      | Q4 2023    | 40%    | 26%     | -14%   |

  @high @volatility @earnings
  Scenario: Trade ideas
    When I view trade ideas for earnings
    Then I should see suggested strategies:
      | Strategy         | Bias               | Risk    |
      | Short Straddle   | Sell premium       | High    |
      | Iron Condor      | Collect IV crush   | Defined |
      | Calendar Spread  | Long post-earnings | Moderate|

  @high @volatility @earnings
  Scenario: Set earnings alert
    When I click "Alert" on AAPL earnings
    Then I should be able to set reminders:
      | Reminder          | Timing            |
      | 1 day before      | Day before close  |
      | Market open       | Morning of        |
      | After announcement| Post-release      |
```

---

### 4.5 Epic: Collective Intelligence UI (HP-5)

#### Story HP-5.1: Community Dashboard

**Story ID:** HP-5.1
**Title:** As a user, I want a community dashboard so that I can see what other traders are doing and thinking.

**Acceptance Criteria:**
- Top traders leaderboard
- Popular trades/strategies
- Community sentiment gauge
- Trending symbols
- Recent activity feed

**Gherkin Test Scenarios:**

```gherkin
Feature: Community Dashboard
  As a user
  I want a community dashboard
  So that I can see what other traders are doing

  Background:
    Given I am logged into the OPTIX platform
    And I navigate to the Community page

  @high @community @dashboard
  Scenario: View community dashboard sections
    When I view the community dashboard
    Then I should see:
      | Section           | Content                    |
      | Top Traders       | Leaderboard of performers  |
      | Trending Trades   | Popular current trades     |
      | Sentiment         | Community bullish/bearish  |
      | Hot Symbols       | Most discussed tickers     |
      | Activity Feed     | Recent community activity  |

  @high @community @dashboard
  Scenario: View top traders leaderboard
    When I view the leaderboard
    Then I should see ranked traders with:
      | Column        | Data                |
      | Rank          | Position            |
      | Trader        | Username/avatar     |
      | Return (30d)  | Recent performance  |
      | Win Rate      | Success rate        |
      | Followers     | Number of followers |
      | Trades        | Trade count         |

  @high @community @dashboard
  Scenario: Community sentiment gauge
    When I view the sentiment section
    Then I should see:
      | Metric             | Display              |
      | Overall Sentiment  | Bullish 62%/Bearish 38% |
      | Bull/Bear Ratio    | 1.63                 |
      | Sentiment Trend    | Increasing bullish   |

  @high @community @dashboard
  Scenario: Trending symbols
    When I view hot symbols
    Then I should see most active symbols:
      | Symbol | Mentions | Sentiment | Price Move |
      | NVDA   | 1,245    | 75% Bull  | +3.2%      |
      | TSLA   | 892      | 55% Bull  | -1.5%      |
      | SPY    | 756      | 60% Bull  | +0.8%      |
```

#### Story HP-5.2: Trader Profile Pages

**Story ID:** HP-5.2
**Title:** As a user, I want to view trader profiles so that I can learn about successful traders and their strategies.

**Acceptance Criteria:**
- Performance statistics
- Trading style/strategy info
- Historical trades (public)
- Follow/copy options
- Reputation score

**Gherkin Test Scenarios:**

```gherkin
Feature: Trader Profile Pages
  As a user
  I want to view trader profiles
  So that I can learn about successful traders

  Background:
    Given I am on the community page
    And I click on a trader's name

  @high @community @profile
  Scenario: View trader profile
    When I view a trader's profile
    Then I should see:
      | Section          | Content                   |
      | Header           | Avatar, name, badges      |
      | Stats            | Performance metrics       |
      | Strategy         | Trading style description |
      | Shared Trades    | Public trade history      |
      | Reputation       | Community trust score     |

  @high @community @profile
  Scenario: Performance statistics
    When I view the stats section
    Then I should see:
      | Metric           | Example    |
      | Total Return     | +245%      |
      | 30-Day Return    | +12.5%     |
      | Win Rate         | 68%        |
      | Avg Trade        | +$340      |
      | Sharpe Ratio     | 1.92       |
      | Max Drawdown     | -15.2%     |

  @high @community @profile
  Scenario: Trading style description
    When I view the strategy section
    Then I should see:
      | Info              | Content                      |
      | Primary Strategy  | Iron Condors on SPY          |
      | Timeframe         | Weekly options               |
      | Risk Level        | Conservative                 |
      | Description       | Trader's strategy narrative  |

  @high @community @profile
  Scenario: Follow trader
    When I click "Follow"
    Then I should receive their trade alerts
    And they should appear in my following list
    And their follower count should increment

  @high @community @profile
  Scenario: View trade history
    When I view shared trades
    Then I should see public trades with:
      | Field      | Data                    |
      | Date       | Trade date              |
      | Symbol     | Underlying              |
      | Strategy   | Trade type              |
      | Result     | P&L and return          |
```

#### Story HP-5.3: Copy Trading Functionality

**Story ID:** HP-5.3
**Title:** As a user, I want to copy trades from successful traders so that I can replicate their strategies.

**Acceptance Criteria:**
- One-click copy trade
- Position size adjustment
- Copy settings (all trades vs selective)
- Risk management controls
- Performance tracking of copied trades

**Gherkin Test Scenarios:**

```gherkin
Feature: Copy Trading Functionality
  As a user
  I want to copy trades from successful traders
  So that I can replicate their strategies

  Background:
    Given I am logged in and viewing a trader's profile

  @high @community @copy
  Scenario: Enable copy trading
    When I click "Copy Trader"
    Then I should see copy configuration:
      | Setting           | Options                    |
      | Position Size     | Fixed $, % of account      |
      | Max Positions     | Limit concurrent copies    |
      | Stop Loss         | Override with max loss     |
      | Trade Types       | All, Options only, etc.    |

  @high @community @copy
  Scenario: Configure copy settings
    When I set position size to "$500"
    And I set max positions to 5
    And I enable "Auto-close on 50% loss"
    And I click "Start Copying"
    Then copy trading should be active
    And I should see "Copying TraderName"

  @high @community @copy
  Scenario: Receive copy trade notification
    Given I am copying TraderX
    When TraderX opens a new position
    Then I should receive a notification
    And the trade should be auto-executed
    And it should appear in my positions

  @high @community @copy
  Scenario: Selective copy trade
    Given I have "Manual approval" enabled
    When TraderX opens a new position
    Then I should receive a prompt
    And I can choose to "Copy" or "Skip"

  @high @community @copy
  Scenario: Copy trading performance
    When I view my copy trading dashboard
    Then I should see:
      | Metric              | Value              |
      | Traders Copying     | 3                  |
      | Total Copied Trades | 45                 |
      | Copy P&L            | +$2,340            |
      | Best Performer      | TraderX (+$1,200)  |
      | Worst Performer     | TraderY (-$150)    |

  @high @community @copy
  Scenario: Stop copying trader
    When I click "Stop Copying" on TraderX
    Then I should see options:
      | Option                     |
      | Close all copied positions |
      | Keep positions, stop new   |
    When I select "Keep positions"
    Then copying should stop
    And existing positions should remain
```

---

## 5. Medium Priority Stories

### 5.1 Epic: Mobile Responsive Design (MP-1)

#### Story MP-1.1: Mobile Navigation

**Story ID:** MP-1.1
**Title:** As a mobile user, I want a hamburger menu navigation so that I can access all features on my phone.

**Acceptance Criteria:**
- Hamburger icon visible on mobile viewports
- Slide-out menu with all navigation items
- Smooth animation transitions
- Touch-friendly tap targets (44x44px minimum)
- Close on outside tap or swipe

**Gherkin Test Scenarios:**

```gherkin
Feature: Mobile Navigation
  As a mobile user
  I want hamburger menu navigation
  So that I can access all features on my phone

  Background:
    Given I am viewing the application on a mobile device
    And the viewport width is less than 768px

  @medium @mobile @navigation
  Scenario: Hamburger menu visibility
    When I view any page
    Then I should see a hamburger menu icon in the header
    And the desktop navigation should be hidden

  @medium @mobile @navigation
  Scenario: Open mobile menu
    When I tap the hamburger icon
    Then a slide-out menu should appear from the left
    And all navigation items should be visible
    And the animation should be smooth (300ms)

  @medium @mobile @navigation
  Scenario: Navigate from mobile menu
    Given the mobile menu is open
    When I tap on "Dashboard"
    Then I should navigate to the dashboard
    And the menu should close automatically

  @medium @mobile @navigation
  Scenario: Close menu by tapping outside
    Given the mobile menu is open
    When I tap outside the menu area
    Then the menu should close
    And the overlay should disappear

  @medium @mobile @navigation
  Scenario: Close menu by swiping left
    Given the mobile menu is open
    When I swipe left on the menu
    Then the menu should close with a swipe animation

  @medium @mobile @navigation
  Scenario: Touch target sizes
    Given the mobile menu is open
    Then all menu items should have minimum 44px height
    And there should be adequate spacing between items
```

#### Story MP-1.2: Responsive Grid System

**Story ID:** MP-1.2
**Title:** As a user, I want the layout to adapt to my screen size so that I can use the platform on any device.

**Acceptance Criteria:**
- Breakpoints at 320px, 768px, 1024px, 1440px
- Single column layout on mobile
- Two column on tablet
- Multi-column on desktop
- No horizontal scrolling on any viewport

**Gherkin Test Scenarios:**

```gherkin
Feature: Responsive Grid System
  As a user
  I want adaptive layouts
  So that I can use the platform on any device

  @medium @mobile @grid
  Scenario Outline: Layout adapts to viewport
    Given the viewport width is <width>px
    When I view the dashboard
    Then the layout should be <columns> column(s)
    And no horizontal scrollbar should appear

    Examples:
      | width | columns |
      | 320   | 1       |
      | 480   | 1       |
      | 768   | 2       |
      | 1024  | 3       |
      | 1440  | 4       |

  @medium @mobile @grid
  Scenario: Cards stack on mobile
    Given I am on mobile (375px)
    When I view the dashboard
    Then all cards should stack vertically
    And cards should be full width

  @medium @mobile @grid
  Scenario: Tables become scrollable on mobile
    Given I am on mobile
    When I view a data table
    Then the table should be horizontally scrollable
    And a scroll indicator should be visible
    And the first column should optionally be sticky
```

#### Story MP-1.3: Mobile Options Chain

**Story ID:** MP-1.3
**Title:** As a mobile user, I want to view options chains on my phone so that I can analyze options on the go.

**Acceptance Criteria:**
- Vertical scrolling chain layout
- Collapsible call/put sections
- Swipe between expirations
- Tap to expand strike details
- Quick action buttons for each strike

**Gherkin Test Scenarios:**

```gherkin
Feature: Mobile Options Chain
  As a mobile user
  I want to view options chains on my phone
  So that I can analyze options on the go

  Background:
    Given I am on mobile
    And I am viewing the options chain for "SPY"

  @medium @mobile @optionschain
  Scenario: Vertical chain layout
    When I view the options chain
    Then strikes should be displayed in a vertical list
    And each strike should show key data (price, delta, OI)
    And I can scroll vertically through strikes

  @medium @mobile @optionschain
  Scenario: Collapsible call/put sections
    When I view the options chain
    Then I should see "Calls" and "Puts" sections
    When I tap "Calls" header
    Then the calls section should collapse/expand
    And I can view calls and puts separately

  @medium @mobile @optionschain
  Scenario: Swipe between expirations
    Given I am viewing Dec 20 expiration
    When I swipe left on the chain
    Then I should see the next expiration (Dec 27)
    And a swipe indicator should show available expirations

  @medium @mobile @optionschain
  Scenario: Tap to expand strike details
    When I tap on the 450 strike row
    Then the row should expand
    And I should see full Greeks (Delta, Gamma, Theta, Vega)
    And I should see volume and open interest
    And action buttons should appear

  @medium @mobile @optionschain
  Scenario: Quick actions for strike
    Given I have expanded a strike row
    Then I should see action buttons:
      | Action          |
      | Add to Strategy |
      | Set Alert       |
      | View Chart      |
```

---

### 5.2 Epic: Advanced Options Chain Features (MP-2)

#### Story MP-2.1: Multi-Expiration Comparison

**Story ID:** MP-2.1
**Title:** As a user, I want to compare options across multiple expirations so that I can choose the best expiration for my strategy.

**Acceptance Criteria:**
- Select 2-4 expirations to compare
- Side-by-side or stacked view
- Same strike alignment across expirations
- Highlighting differences in Greeks/IV
- Quick switch between view modes

**Gherkin Test Scenarios:**

```gherkin
Feature: Multi-Expiration Comparison
  As a user
  I want to compare options across expirations
  So that I can choose the best expiration

  Background:
    Given I am on the options chain page
    And I select symbol "SPY"

  @medium @optionschain @comparison
  Scenario: Select multiple expirations
    When I click "Compare Expirations"
    And I select "Dec 20", "Dec 27", "Jan 17"
    And I click "Compare"
    Then all three expirations should display
    And they should be aligned by strike

  @medium @optionschain @comparison
  Scenario: Side-by-side view
    Given I am comparing 3 expirations
    When I select "Side by Side" view
    Then expirations should appear in columns
    And strikes should align horizontally

  @medium @optionschain @comparison
  Scenario: Highlight differences
    Given I am comparing expirations
    When I enable "Highlight Differences"
    Then significant IV differences should be highlighted
    And theta decay differences should be visible
    And color intensity should indicate magnitude

  @medium @optionschain @comparison
  Scenario: Compare specific strike across expirations
    When I click on the 450 strike
    Then a comparison card should show:
      | Expiration | Price | IV    | Delta | Theta |
      | Dec 20     | $5.00 | 22%   | 0.50  | -0.15 |
      | Dec 27     | $6.50 | 23%   | 0.52  | -0.12 |
      | Jan 17     | $9.00 | 24%   | 0.55  | -0.08 |
```

#### Story MP-2.2: Strike Filtering

**Story ID:** MP-2.2
**Title:** As a user, I want to filter visible strikes so that I can focus on the options relevant to my strategy.

**Acceptance Criteria:**
- ITM/ATM/OTM toggle filters
- Delta range filter
- Price range filter
- Volume/OI minimum filter
- Save filter presets

**Gherkin Test Scenarios:**

```gherkin
Feature: Strike Filtering
  As a user
  I want to filter visible strikes
  So that I can focus on relevant options

  Background:
    Given I am on the options chain page
    And I have a full chain loaded

  @medium @optionschain @filter
  Scenario: ITM/ATM/OTM toggles
    Given all strikes are visible
    When I click "OTM Only" toggle
    Then only out-of-the-money strikes should display
    When I click "ITM Only" toggle
    Then only in-the-money strikes should display

  @medium @optionschain @filter
  Scenario: Delta range filter
    When I set delta filter to "0.20 - 0.40"
    Then only strikes with delta in that range should show
    And strikes outside the range should be hidden

  @medium @optionschain @filter
  Scenario: Minimum volume filter
    When I set minimum volume to "1000"
    Then only strikes with volume >= 1000 should display
    And low volume strikes should be hidden

  @medium @optionschain @filter
  Scenario: Save filter preset
    Given I have configured filters
    When I click "Save Preset"
    And I name it "My Spread Targets"
    Then the preset should be saved
    And I can quickly apply it later
```

---

### 5.3 Epic: Enhanced Alert System (MP-3)

#### Story MP-3.1: Visual Alert Builder

**Story ID:** MP-3.1
**Title:** As a user, I want a visual alert builder so that I can create complex alerts without writing code.

**Acceptance Criteria:**
- Drag-and-drop condition builder
- Multiple condition support (AND/OR)
- Preview of alert logic
- Test alert before activation
- Template library

**Gherkin Test Scenarios:**

```gherkin
Feature: Visual Alert Builder
  As a user
  I want a visual alert builder
  So that I can create complex alerts easily

  Background:
    Given I am on the alerts page
    And I click "Create New Alert"

  @medium @alerts @builder
  Scenario: Add condition to alert
    When I drag "Price" condition to the builder
    And I set symbol to "SPY"
    And I set condition to "crosses above"
    And I set value to "$450"
    Then the condition should appear in the builder
    And a preview should show "SPY price crosses above $450"

  @medium @alerts @builder
  Scenario: Multiple conditions with AND
    Given I have a price condition set
    When I click "Add Condition"
    And I add "Volume > 1,000,000"
    And I set operator to "AND"
    Then the alert should require both conditions
    And preview should show "SPY price > $450 AND Volume > 1M"

  @medium @alerts @builder
  Scenario: Multiple conditions with OR
    Given I have conditions set
    When I change operator to "OR"
    Then the alert should trigger on either condition
    And preview should reflect OR logic

  @medium @alerts @builder
  Scenario: Test alert
    Given I have configured an alert
    When I click "Test Alert"
    Then the system should evaluate current conditions
    And show whether alert would trigger now
    And display the current values vs thresholds

  @medium @alerts @builder
  Scenario: Use alert template
    When I click "Use Template"
    And I select "Unusual Volume Spike"
    Then the builder should populate with template conditions
    And I can customize the values
```

#### Story MP-3.2: Alert History and Analytics

**Story ID:** MP-3.2
**Title:** As a user, I want to see my alert history so that I can analyze which alerts are most useful.

**Acceptance Criteria:**
- List of triggered alerts with timestamps
- Chart showing price at trigger
- Alert effectiveness metrics
- Export alert history
- Re-activate past alerts

**Gherkin Test Scenarios:**

```gherkin
Feature: Alert History and Analytics
  As a user
  I want to see alert history
  So that I can analyze alert effectiveness

  Background:
    Given I am on the alerts page
    And I navigate to "Alert History"

  @medium @alerts @history
  Scenario: View triggered alerts
    When I view the alert history
    Then I should see a list of triggered alerts with:
      | Column      | Data                |
      | Alert Name  | Name of the alert   |
      | Triggered   | Date and time       |
      | Symbol      | Ticker symbol       |
      | Condition   | What triggered it   |
      | Price Then  | Price at trigger    |
      | Price Now   | Current price       |

  @medium @alerts @history
  Scenario: View chart at trigger time
    When I click on a triggered alert
    Then I should see a chart showing:
      | Element          | Description              |
      | Price chart      | Historical prices        |
      | Trigger point    | Marked on chart          |
      | Price movement   | What happened after      |

  @medium @alerts @history
  Scenario: Alert effectiveness metrics
    When I view alert analytics
    Then I should see:
      | Metric                | Example |
      | Total Alerts Triggered| 45      |
      | Avg Move After Trigger| +2.3%   |
      | Best Performing Alert | Price > 50 SMA (78% win) |
      | False Positive Rate   | 12%     |

  @medium @alerts @history
  Scenario: Export history
    When I click "Export"
    Then I should download a CSV with all alert history
```

---

### 5.4 Epic: Dashboard Customization (MP-4)

#### Story MP-4.1: Drag-and-Drop Widget Layout

**Story ID:** MP-4.1
**Title:** As a user, I want to customize my dashboard layout so that I can arrange widgets according to my preferences.

**Acceptance Criteria:**
- Drag widgets to reposition
- Resize widgets
- Add/remove widgets
- Multiple layout presets
- Auto-save layout changes

**Gherkin Test Scenarios:**

```gherkin
Feature: Drag-and-Drop Widget Layout
  As a user
  I want to customize dashboard layout
  So that I can arrange widgets to my preference

  Background:
    Given I am on the dashboard
    And I click "Edit Layout"

  @medium @dashboard @customize
  Scenario: Drag widget to new position
    Given the "Portfolio Summary" widget is in position 1
    When I drag "Portfolio Summary" to position 3
    Then the widget should move to position 3
    And other widgets should reflow

  @medium @dashboard @customize
  Scenario: Resize widget
    Given the "Chart" widget is 1x1 size
    When I drag the resize handle
    And I expand it to 2x2
    Then the widget should resize
    And show more detail in expanded view

  @medium @dashboard @customize
  Scenario: Add new widget
    When I click "Add Widget"
    Then I should see a widget library with:
      | Widget           | Description         |
      | Market Summary   | Indices overview    |
      | Watchlist Mini   | Quick watchlist     |
      | Recent Alerts    | Latest alert feed   |
      | News Feed        | Market news         |
    When I click "Market Summary"
    Then the widget should be added to my dashboard

  @medium @dashboard @customize
  Scenario: Remove widget
    When I click the "X" on a widget
    Then a confirmation should appear
    When I confirm removal
    Then the widget should be removed
    And other widgets should reflow

  @medium @dashboard @customize
  Scenario: Save layout preset
    Given I have customized my layout
    When I click "Save as Preset"
    And I name it "Trading View"
    Then the preset should be saved
    And I can switch between presets

  @medium @dashboard @customize
  Scenario: Auto-save changes
    When I make layout changes
    Then changes should auto-save
    And when I return later, my layout should persist
```

---

### 5.5 Epic: Performance Analytics Enhancement (MP-5)

#### Story MP-5.1: Detailed Metrics Breakdown

**Story ID:** MP-5.1
**Title:** As a user, I want detailed performance metrics so that I can understand my trading results in depth.

**Acceptance Criteria:**
- Core metrics (Sharpe, Sortino, Calmar)
- Risk metrics (VaR, max drawdown, volatility)
- Trade statistics (win rate, avg win/loss)
- Periodic breakdowns (daily, weekly, monthly)
- Benchmark comparisons

**Gherkin Test Scenarios:**

```gherkin
Feature: Detailed Performance Metrics
  As a user
  I want detailed performance metrics
  So that I can understand my trading results

  Background:
    Given I am on the performance page
    And I have trading history

  @medium @performance @metrics
  Scenario: View core performance metrics
    When I view the metrics section
    Then I should see:
      | Metric        | Value   | Benchmark |
      | Total Return  | +45.2%  | +23.5%    |
      | CAGR          | 38.2%   | 18.4%     |
      | Sharpe Ratio  | 1.85    | 0.92      |
      | Sortino Ratio | 2.34    | 1.15      |
      | Calmar Ratio  | 3.12    | 1.45      |

  @medium @performance @metrics
  Scenario: View risk metrics
    When I view the risk section
    Then I should see:
      | Metric           | Value   |
      | Max Drawdown     | -12.3%  |
      | Value at Risk    | -$2,450 |
      | Volatility       | 18.5%   |
      | Beta             | 0.65    |
      | Downside Dev     | 8.2%    |

  @medium @performance @metrics
  Scenario: Trade statistics breakdown
    When I view trade statistics
    Then I should see:
      | Statistic        | Value   |
      | Total Trades     | 156     |
      | Win Rate         | 62%     |
      | Average Win      | +$385   |
      | Average Loss     | -$245   |
      | Largest Win      | +$2,340 |
      | Largest Loss     | -$890   |
      | Profit Factor    | 2.15    |

  @medium @performance @metrics
  Scenario: Periodic breakdown
    When I select "Monthly" view
    Then I should see monthly performance:
      | Month    | Return  | Trades | Win Rate |
      | Dec 2024 | +8.2%   | 18     | 72%      |
      | Nov 2024 | +5.1%   | 22     | 59%      |
      | Oct 2024 | -2.3%   | 15     | 47%      |

  @medium @performance @metrics
  Scenario: Benchmark comparison
    When I enable SPY benchmark
    Then all metrics should show benchmark comparison
    And alpha should be calculated
    And correlation should be displayed
```

---

## 6. Low Priority Stories

### 6.1 Epic: Theme System (LP-1)

#### Story LP-1.1: Dark/Light Theme Toggle

**Story ID:** LP-1.1
**Title:** As a user, I want to switch between dark and light themes so that I can choose the appearance that suits me.

**Acceptance Criteria:**
- Toggle in header/settings
- Instant theme switch without reload
- Persist preference across sessions
- System preference detection
- Smooth transition animation

**Gherkin Test Scenarios:**

```gherkin
Feature: Dark/Light Theme Toggle
  As a user
  I want to switch between themes
  So that I can choose my preferred appearance

  Background:
    Given I am logged into the OPTIX platform

  @low @theme @toggle
  Scenario: Toggle theme from light to dark
    Given the current theme is light
    When I click the theme toggle in the header
    Then the theme should switch to dark
    And the background should become dark
    And text should become light
    And the transition should be smooth (200ms)

  @low @theme @toggle
  Scenario: Theme persists across sessions
    Given I set the theme to dark
    When I log out and log back in
    Then the theme should still be dark

  @low @theme @toggle
  Scenario: System preference detection
    Given my OS is set to dark mode
    And I am a new user with no preference
    When I log in
    Then the theme should default to dark

  @low @theme @toggle
  Scenario: Theme affects all pages
    Given I set the theme to dark
    When I navigate to different pages
    Then all pages should use dark theme
    And charts should use dark color scheme
```

---

### 6.2 Epic: Accessibility Improvements (LP-2)

#### Story LP-2.1: Keyboard Navigation

**Story ID:** LP-2.1
**Title:** As a user with mobility impairments, I want full keyboard navigation so that I can use the platform without a mouse.

**Acceptance Criteria:**
- Tab navigation through all interactive elements
- Focus indicators clearly visible
- Keyboard shortcuts for common actions
- Skip links for main content
- Modal focus trapping

**Gherkin Test Scenarios:**

```gherkin
Feature: Keyboard Navigation
  As a user with mobility impairments
  I want full keyboard navigation
  So that I can use the platform without a mouse

  @low @accessibility @keyboard
  Scenario: Tab through navigation
    Given I am on any page
    When I press Tab repeatedly
    Then focus should move through all interactive elements
    And focus order should be logical (top-to-bottom, left-to-right)

  @low @accessibility @keyboard
  Scenario: Visible focus indicator
    When I tab to a button
    Then a clear focus ring should be visible
    And it should meet WCAG contrast requirements

  @low @accessibility @keyboard
  Scenario: Keyboard shortcuts
    When I press "?" key
    Then a keyboard shortcuts modal should appear
    And it should list:
      | Shortcut | Action              |
      | G then D | Go to Dashboard     |
      | G then W | Go to Watchlist     |
      | G then O | Go to Options Chain |
      | /        | Focus search        |
      | Esc      | Close modal         |

  @low @accessibility @keyboard
  Scenario: Skip to main content
    When I press Tab on page load
    Then the first focusable element should be "Skip to main content"
    When I press Enter
    Then focus should jump to the main content area

  @low @accessibility @keyboard
  Scenario: Modal focus trapping
    Given a modal is open
    When I tab through the modal
    Then focus should stay within the modal
    And not escape to the page behind
```

#### Story LP-2.2: Screen Reader Support

**Story ID:** LP-2.2
**Title:** As a visually impaired user, I want screen reader compatibility so that I can use the platform with assistive technology.

**Acceptance Criteria:**
- ARIA labels on all interactive elements
- Live regions for dynamic content
- Proper heading structure
- Alternative text for images
- Form labels and error announcements

**Gherkin Test Scenarios:**

```gherkin
Feature: Screen Reader Support
  As a visually impaired user
  I want screen reader compatibility
  So that I can use assistive technology

  @low @accessibility @screenreader
  Scenario: ARIA labels on buttons
    When a screen reader encounters a button
    Then it should announce the button's purpose
    And icon-only buttons should have aria-label

  @low @accessibility @screenreader
  Scenario: Live region for price updates
    Given I am on the watchlist
    When a price updates
    Then the screen reader should announce "AAPL price updated to $150.50"
    And the announcement should not be disruptive

  @low @accessibility @screenreader
  Scenario: Heading structure
    When I navigate by headings (H key in screen reader)
    Then I should find a logical heading structure
    And h1 should be the page title
    And sections should have h2, h3 appropriately

  @low @accessibility @screenreader
  Scenario: Form error announcements
    Given I am filling out a form
    When I submit with errors
    Then errors should be announced
    And focus should move to the first error
    And the error message should be read
```

---

### 6.3 Epic: Performance Optimization (LP-3)

#### Story LP-3.1: Lazy Loading

**Story ID:** LP-3.1
**Title:** As a user, I want pages to load quickly so that I can start using features without waiting.

**Acceptance Criteria:**
- Above-fold content loads first
- Below-fold content loads on scroll
- Images lazy load with placeholders
- Heavy components deferred
- Loading indicators for deferred content

**Gherkin Test Scenarios:**

```gherkin
Feature: Lazy Loading
  As a user
  I want fast page loads
  So that I can start using features quickly

  @low @performance @lazyload
  Scenario: Above-fold content priority
    When I load the dashboard
    Then visible content should render first
    And below-fold widgets should load after
    And initial paint should occur within 1.5s

  @low @performance @lazyload
  Scenario: Image lazy loading
    Given I am on a page with many images
    Then only visible images should load initially
    When I scroll down
    Then more images should load
    And placeholders should show while loading

  @low @performance @lazyload
  Scenario: Heavy component deferral
    Given the page has a complex chart
    Then basic layout should render first
    And the chart should load after critical content
    And a skeleton should show while loading
```

#### Story LP-3.2: Virtual Scrolling

**Story ID:** LP-3.2
**Title:** As a user, I want smooth scrolling through large lists so that performance remains good with lots of data.

**Acceptance Criteria:**
- Render only visible rows
- Smooth scrolling with large datasets
- Maintain scroll position
- Search within virtual list
- Consistent row heights or dynamic measurement

**Gherkin Test Scenarios:**

```gherkin
Feature: Virtual Scrolling
  As a user
  I want smooth scrolling in large lists
  So that performance remains good

  Background:
    Given I am viewing a list with 10,000 items

  @low @performance @virtualscroll
  Scenario: Only visible rows rendered
    When I view the list
    Then only visible rows should be in the DOM
    And typically 20-30 rows should be rendered
    And total DOM nodes should be minimal

  @low @performance @virtualscroll
  Scenario: Smooth scrolling
    When I scroll quickly through the list
    Then scrolling should remain at 60fps
    And no blank areas should appear
    And rows should render smoothly

  @low @performance @virtualscroll
  Scenario: Maintain scroll position
    Given I have scrolled to row 5000
    When I switch tabs and return
    Then I should still be at row 5000

  @low @performance @virtualscroll
  Scenario: Search within virtual list
    When I type in the search box
    Then results should filter instantly
    And scrolling should reset to top
    And virtual scrolling should still work
```

---

### 6.4 Epic: Onboarding and Help (LP-4)

#### Story LP-4.1: First-Time User Tour

**Story ID:** LP-4.1
**Title:** As a new user, I want a guided tour so that I can learn how to use the platform quickly.

**Acceptance Criteria:**
- Interactive tooltips highlighting features
- Step-by-step progression
- Skip option available
- Can restart tour from settings
- Tracks completion for each section

**Gherkin Test Scenarios:**

```gherkin
Feature: First-Time User Tour
  As a new user
  I want a guided tour
  So that I can learn the platform quickly

  Background:
    Given I am a new user
    And I log in for the first time

  @low @onboarding @tour
  Scenario: Tour starts on first login
    When I land on the dashboard
    Then a welcome modal should appear
    And it should offer "Start Tour" and "Skip"

  @low @onboarding @tour
  Scenario: Step through tour
    Given I started the tour
    When I am on step 1
    Then a tooltip should highlight the navigation
    And explain its purpose
    When I click "Next"
    Then I should move to step 2
    And the tooltip should move to the next feature

  @low @onboarding @tour
  Scenario: Skip tour
    Given the tour is in progress
    When I click "Skip Tour"
    Then the tour should end
    And I should see normal interface

  @low @onboarding @tour
  Scenario: Restart tour from settings
    Given I previously skipped the tour
    When I go to Settings > Help
    And I click "Restart Tour"
    Then the tour should begin again

  @low @onboarding @tour
  Scenario: Tour completion tracking
    Given I completed the dashboard tour
    When I visit the options chain for the first time
    Then a mini-tour for options chain should start
    And it should be specific to that page
```

#### Story LP-4.2: Contextual Help Tooltips

**Story ID:** LP-4.2
**Title:** As a user, I want contextual help tooltips so that I can understand features without leaving the page.

**Acceptance Criteria:**
- Help icon (?) next to complex features
- Hover/click to show explanation
- Links to full documentation
- Examples where helpful
- Dismissable and remembers preference

**Gherkin Test Scenarios:**

```gherkin
Feature: Contextual Help Tooltips
  As a user
  I want contextual help tooltips
  So that I can understand features easily

  @low @onboarding @help
  Scenario: Help icon on complex features
    When I view the options chain
    Then I should see help icons next to:
      | Element     |
      | IV Rank     |
      | Delta       |
      | Gamma       |
      | Theta       |
      | Vega        |

  @low @onboarding @help
  Scenario: Show help tooltip
    When I hover over the "?" next to IV Rank
    Then a tooltip should appear explaining:
      | Content                                    |
      | "IV Rank shows current IV relative to its |
      | 52-week range. 0 = lowest, 100 = highest" |

  @low @onboarding @help
  Scenario: Link to full documentation
    Given a help tooltip is shown
    Then it should include "Learn more" link
    When I click "Learn more"
    Then I should go to the relevant documentation page

  @low @onboarding @help
  Scenario: Dismiss help tooltips
    When I click "Don't show again" on a tooltip
    Then that tooltip should not appear on hover
    And preference should persist
```

---

### 6.5 Epic: Generative UI Integration (LP-5)

#### Story LP-5.1: GenUI Prompt Input

**Story ID:** LP-5.1
**Title:** As a user, I want to describe what I want to see in natural language so that the UI can be generated automatically.

**Acceptance Criteria:**
- Natural language input field
- Real-time preview of generated UI
- Edit and refine prompts
- Save successful prompts as templates
- History of past prompts

**Gherkin Test Scenarios:**

```gherkin
Feature: GenUI Prompt Input
  As a user
  I want to describe UI in natural language
  So that it can be generated automatically

  Background:
    Given I am on the GenUI page
    And I have access to the generative UI feature

  @low @genui @prompt
  Scenario: Enter natural language prompt
    When I type "Show me a comparison of SPY and QQQ IV over 30 days"
    And I click "Generate"
    Then the system should process my request
    And a loading indicator should show
    And a preview should generate

  @low @genui @prompt
  Scenario: Real-time preview
    Given the system generated a UI
    Then I should see a preview of the component
    And it should show SPY vs QQQ IV chart
    And I can interact with the preview

  @low @genui @prompt
  Scenario: Refine prompt
    Given a UI was generated
    When I click "Refine"
    And I add "with daily granularity"
    Then the UI should regenerate
    And changes should be reflected

  @low @genui @prompt
  Scenario: Save prompt as template
    Given a successful UI was generated
    When I click "Save as Template"
    And I name it "IV Comparison Chart"
    Then the template should be saved
    And I can use it again later

  @low @genui @prompt
  Scenario: View prompt history
    When I click "Prompt History"
    Then I should see past prompts
    And I can re-run any previous prompt
    And I can delete prompts from history
```

#### Story LP-5.2: GenUI Component Customization

**Story ID:** LP-5.2
**Title:** As a user, I want to customize generated UI components so that I can fine-tune the output.

**Acceptance Criteria:**
- Visual property editor
- Color scheme selection
- Data source configuration
- Layout adjustments
- Save customizations

**Gherkin Test Scenarios:**

```gherkin
Feature: GenUI Component Customization
  As a user
  I want to customize generated components
  So that I can fine-tune the output

  Background:
    Given a UI component was generated
    And I am viewing the customization panel

  @low @genui @customize
  Scenario: Visual property editor
    When I open the property editor
    Then I should see editable properties:
      | Property    | Current Value |
      | Title       | "IV Comparison"|
      | Chart Type  | Line          |
      | Time Range  | 30 days       |
      | Show Legend | true          |

  @low @genui @customize
  Scenario: Change color scheme
    When I click "Colors"
    And I select "Blue theme"
    Then the component colors should update
    And preview should reflect changes

  @low @genui @customize
  Scenario: Adjust layout
    When I select "2-column layout"
    Then the component should reconfigure
    And elements should arrange in 2 columns

  @low @genui @customize
  Scenario: Save customizations
    Given I have customized the component
    When I click "Save"
    Then customizations should persist
    And the component should render with my settings

  @low @genui @customize
  Scenario: Add to dashboard
    Given I am satisfied with the component
    When I click "Add to Dashboard"
    Then the component should be added to my dashboard
    And it should function with live data
```

---

## 7. Appendix

### 7.1 Test Tag Reference

| Tag | Description |
|-----|-------------|
| @critical | Critical priority tests |
| @high | High priority tests |
| @medium | Medium priority tests |
| @low | Low priority tests |
| @websocket | WebSocket related tests |
| @auth | Authentication related tests |
| @api | API integration tests |
| @ui | User interface tests |
| @mobile | Mobile responsive tests |
| @performance | Performance related tests |
| @accessibility | Accessibility tests |
| @security | Security related tests |

### 7.2 Test Environment Requirements

| Environment | Purpose | Data |
|-------------|---------|------|
| Development | Feature testing | Mock data |
| Staging | Integration testing | Sanitized prod data |
| Production | Smoke tests only | Live data |

### 7.3 Test Data Requirements

| Data Type | Description | Volume |
|-----------|-------------|--------|
| User accounts | Test users with various roles | 50 |
| Symbols | Stocks/ETFs with options | 100 |
| Historical data | OHLC price data | 5 years |
| Options chains | Full chains with Greeks | 500 strikes/symbol |
| Order flow | Historical options flow | 1M records |

### 7.4 Definition of Done

For each story to be considered complete:

- [ ] All Gherkin scenarios pass
- [ ] Code meets NFR requirements
- [ ] Accessibility audit passes
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Code review approved
- [ ] QA sign-off obtained

---

**Document End**

---

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 14, 2025 | OPTIX Team | Initial document |
