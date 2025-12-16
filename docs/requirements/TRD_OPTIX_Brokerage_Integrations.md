# OPTIX Trading Platform - Brokerage Integrations

## Technical Requirements Document (TRD)

**DSDM Atern Methodology**

Version 1.0 | December 16, 2025

---

## Document Control

| Attribute | Value |
|-----------|-------|
| **Document Owner** | Technical Architecture Team |
| **PRD Reference** | OPTIX_PRD_v1.0 |
| **Vertical Slice** | VS-7: Universal Brokerage Sync |
| **Phase** | Phase 1 (Months 2-4) |
| **Priority** | **Must Have** |
| **Status** | Implementation Required |
| **Repository** | https://github.com/phillonc/dsdm-agents |
| **Location** | `generated/optix/optix-trading-platform/src/brokerage_service/` |

---

## Executive Summary

This TRD defines the technical requirements for completing the Universal Brokerage Sync feature (VS-7). Currently, only Schwab/TD Ameritrade connector is implemented. This document specifies requirements for the remaining 4 brokerage integrations, portfolio logic completion, and security hardening.

### Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Schwab/TD Ameritrade Connector | ✅ Complete | Full OAuth, positions, transactions |
| Fidelity Connector | ❌ Not Started | OAuth 2.0 integration required |
| Robinhood Connector | ❌ Not Started | Plaid integration required |
| Interactive Brokers Connector | ❌ Not Started | Client Portal API required |
| Webull Connector | ❌ Not Started | Official API integration required |
| Portfolio Logic | ⚠️ Partial | Cash, realized P&L, day P&L incomplete |
| Security | ⚠️ Partial | CSRF validation, token revocation missing |

### Completion Target

- **4 new brokerage connectors** following existing `BrokerageConnector` abstract interface
- **Portfolio logic gaps** filled for complete P&L tracking
- **Security hardening** with CSRF protection and token management

---

## 1. Architecture Overview

### 1.1 Current System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI REST API                           │
│                   /api/v1/brokerages/*                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PortfolioSyncService                         │
│              (sync_service.py - 194 lines)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ sync_account│  │sync_all_acct│  │get_unified_portfolio    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BrokerageConnector (Abstract)                  │
│                  (connectors/base.py - 89 lines)                │
└─────────────────────────────────────────────────────────────────┘
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ Schwab │  │Fidelity│  │Robinhood│ │  IBKR  │  │ Webull │
   │   ✅   │  │   ❌   │  │   ❌   │  │   ❌   │  │   ❌   │
   └────────┘  └────────┘  └────────┘  └────────┘  └────────┘
```

### 1.2 Connector Interface Contract

All connectors must implement the `BrokerageConnector` abstract base class:

```python
class BrokerageConnector(ABC):
    @abstractmethod
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]

    @abstractmethod
    async def refresh_token(self) -> Dict[str, Any]

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]

    @abstractmethod
    async def get_positions(self) -> List[Position]

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]

    @abstractmethod
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]

    async def disconnect(self)  # Optional override
    async def test_connection(self) -> bool
```

---

## 2. Brokerage Connector Specifications

### 2.1 Fidelity Connector

| Attribute | Value |
|-----------|-------|
| **File** | `src/brokerage_service/connectors/fidelity.py` |
| **Authentication** | OAuth 2.0 |
| **API Base URL** | `https://api.fidelity.com/v1` |
| **Token URL** | `https://api.fidelity.com/oauth2/token` |
| **Auth URL** | `https://api.fidelity.com/oauth2/authorize` |
| **Priority** | **Must Have** |
| **Phase** | Month 2 |

#### 2.1.1 API Endpoints to Implement

| Endpoint | Purpose | Maps To |
|----------|---------|---------|
| `GET /accounts` | List user accounts | `get_account_info()` |
| `GET /accounts/{id}/balances` | Cash and equity balances | `get_account_balance()` |
| `GET /accounts/{id}/positions` | Current positions | `get_positions()` |
| `GET /accounts/{id}/transactions` | Trade history | `get_transactions()` |
| `POST /oauth2/revoke` | Token revocation | `disconnect()` |

#### 2.1.2 Implementation Requirements

```python
class FidelityConnector(BrokerageConnector):
    """
    Fidelity Official API connector
    OAuth 2.0 authentication flow
    """

    BASE_URL = "https://api.fidelity.com/v1"
    AUTH_URL = "https://api.fidelity.com/oauth2/authorize"
    TOKEN_URL = "https://api.fidelity.com/oauth2/token"
    REVOKE_URL = "https://api.fidelity.com/oauth2/revoke"

    # Scopes required
    SCOPES = ["accounts:read", "positions:read", "transactions:read"]

    # Token refresh buffer (refresh 5 min before expiry)
    TOKEN_REFRESH_BUFFER = timedelta(minutes=5)
```

#### 2.1.3 Response Mapping

| Fidelity Field | OPTIX Position Field | Notes |
|----------------|---------------------|-------|
| `symbol` | `symbol` | Direct mapping |
| `assetType` | `position_type` | Map: EQUITY→STOCK, OPTION→OPTION |
| `quantity` | `quantity` | Convert to Decimal |
| `costBasis` | `cost_basis` | Total cost basis |
| `marketValue` | `market_value` | Current value |
| `unrealizedGainLoss` | `unrealized_pl` | P&L amount |
| `unrealizedGainLossPercent` | `unrealized_pl_percent` | P&L percentage |

#### 2.1.4 Gherkin Specification

```gherkin
Feature: Fidelity Brokerage Connection

  @fidelity @oauth
  Scenario: Connect Fidelity account via OAuth
    Given I am on the "Link Accounts" screen
    When I select "Fidelity"
    And I complete the Fidelity OAuth authorization
    Then my Fidelity account should be linked within 60 seconds
    And I should see my positions populate
    And my account balance should be visible

  @fidelity @positions
  Scenario: Sync Fidelity positions
    Given I have a connected Fidelity account
    When position sync is triggered
    Then all stock positions should be imported
    And all option positions should include Greeks
    And P&L calculations should be accurate

  @fidelity @transactions
  Scenario: Import Fidelity transaction history
    Given I have a connected Fidelity account
    When I request transaction history for last 90 days
    Then all trades should be imported
    And transaction types should be correctly classified
```

---

### 2.2 Robinhood Connector

| Attribute | Value |
|-----------|-------|
| **File** | `src/brokerage_service/connectors/robinhood.py` |
| **Authentication** | Plaid Integration |
| **API Provider** | Plaid |
| **Plaid Products** | `investments`, `transactions` |
| **Priority** | **Must Have** |
| **Phase** | Month 3 |

#### 2.2.1 Plaid Integration Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     OPTIX Frontend                           │
│                 Plaid Link Component                         │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Plaid Link API                            │
│          User authenticates with Robinhood                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼ public_token
┌──────────────────────────────────────────────────────────────┐
│                   OPTIX Backend                              │
│          Exchange public_token for access_token              │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Plaid API                                 │
│        /investments/holdings, /investments/transactions      │
└──────────────────────────────────────────────────────────────┘
```

#### 2.2.2 Implementation Requirements

```python
class RobinhoodConnector(BrokerageConnector):
    """
    Robinhood connector via Plaid
    Uses Plaid Investment APIs
    """

    PLAID_ENV = "production"  # or "sandbox" for testing
    PLAID_BASE_URL = "https://production.plaid.com"

    def __init__(self, connection, plaid_client_id: str, plaid_secret: str):
        super().__init__(connection)
        self.plaid_client_id = plaid_client_id
        self.plaid_secret = plaid_secret

    async def authenticate(self, public_token: str) -> Dict[str, Any]:
        """
        Exchange Plaid public_token for access_token
        Note: Different flow than OAuth - receives public_token from Plaid Link
        """
        pass

    async def get_positions(self) -> List[Position]:
        """
        Fetch positions via Plaid /investments/holdings
        """
        pass
```

#### 2.2.3 Plaid API Endpoints

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `POST /item/public_token/exchange` | Exchange token | Returns `access_token` |
| `GET /investments/holdings/get` | Get positions | Returns holdings list |
| `GET /investments/transactions/get` | Get transactions | Date range supported |
| `POST /item/remove` | Disconnect | Removes Plaid item |

#### 2.2.4 Plaid Response Mapping

| Plaid Field | OPTIX Position Field | Notes |
|-------------|---------------------|-------|
| `security.ticker_symbol` | `symbol` | Stock/ETF ticker |
| `security.type` | `position_type` | Map: equity→STOCK, etf→ETF, derivative→OPTION |
| `quantity` | `quantity` | Number of shares |
| `cost_basis` | `cost_basis` | Total cost basis |
| `institution_value` | `market_value` | Current market value |

#### 2.2.5 Gherkin Specification

```gherkin
Feature: Robinhood Brokerage Connection via Plaid

  @robinhood @plaid
  Scenario: Connect Robinhood via Plaid Link
    Given I am on the "Link Accounts" screen
    When I select "Robinhood"
    Then Plaid Link should open
    When I select my Robinhood account in Plaid
    And I complete Robinhood authentication
    Then my account should be linked
    And positions should begin syncing

  @robinhood @holdings
  Scenario: Import Robinhood holdings
    Given I have a connected Robinhood account via Plaid
    When holdings sync completes
    Then all stock holdings should appear
    And fractional shares should be supported
    And crypto holdings should be excluded (not supported)
```

---

### 2.3 Interactive Brokers Connector

| Attribute | Value |
|-----------|-------|
| **File** | `src/brokerage_service/connectors/ibkr.py` |
| **Authentication** | Client Portal API (OAuth 2.0) |
| **API Base URL** | `https://localhost:5000/v1/api` (Gateway) |
| **Alternative** | Web API (https://api.ibkr.com) |
| **Priority** | **Should Have** |
| **Phase** | Month 4 |

#### 2.3.1 Client Portal Gateway Architecture

Interactive Brokers requires a local gateway for the Client Portal API:

```
┌─────────────────────────────────────────────────────────────┐
│                    OPTIX Backend                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            IB Client Portal Gateway (localhost:5000)        │
│                    (Java application)                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Interactive Brokers                        │
│                    Trading Systems                          │
└─────────────────────────────────────────────────────────────┘
```

**Alternative: Web API (Recommended for Cloud Deployment)**

```
┌─────────────────────────────────────────────────────────────┐
│                    OPTIX Backend                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            IB Web API (api.ibkr.com)                        │
│              OAuth 2.0 Authentication                       │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3.2 Implementation Requirements

```python
class IBKRConnector(BrokerageConnector):
    """
    Interactive Brokers Client Portal API connector
    Supports both Gateway and Web API modes
    """

    # Web API endpoints (recommended)
    WEB_API_BASE = "https://api.ibkr.com/v1/api"
    WEB_AUTH_URL = "https://www.interactivebrokers.com/authorize"
    WEB_TOKEN_URL = "https://api.ibkr.com/v1/api/oauth/token"

    # Gateway endpoints (alternative)
    GATEWAY_BASE = "https://localhost:5000/v1/api"

    def __init__(
        self,
        connection,
        client_id: str,
        client_secret: str,
        use_gateway: bool = False
    ):
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = self.GATEWAY_BASE if use_gateway else self.WEB_API_BASE
```

#### 2.3.3 API Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /portfolio/accounts` | List accounts | Account IDs and info |
| `GET /portfolio/{accountId}/positions` | Get positions | Position details |
| `GET /portfolio/{accountId}/summary` | Account summary | Balances, buying power |
| `GET /portfolio/{accountId}/ledger` | Account ledger | Cash balances by currency |
| `GET /iserver/account/trades` | Trade history | Recent trades |

#### 2.3.4 IBKR-Specific Considerations

| Consideration | Handling |
|---------------|----------|
| **Multi-currency** | Aggregate positions by base currency |
| **Sub-accounts** | Support FA (Financial Advisor) accounts |
| **Session management** | Re-authenticate if session expires (tickle endpoint) |
| **Rate limits** | 10 requests/second max |
| **Options symbology** | Convert OCC format to standard |

#### 2.3.5 Gherkin Specification

```gherkin
Feature: Interactive Brokers Connection

  @ibkr @oauth
  Scenario: Connect Interactive Brokers account
    Given I am on the "Link Accounts" screen
    When I select "Interactive Brokers"
    And I complete IB OAuth authorization
    Then my IB account should be linked
    And all sub-accounts should be visible (if FA account)

  @ibkr @positions
  Scenario: Sync IBKR multi-currency positions
    Given I have a connected IBKR account with USD and EUR positions
    When position sync completes
    Then all positions should be converted to USD
    And currency conversion rates should be applied
    And portfolio total should reflect USD value

  @ibkr @options
  Scenario: Import IBKR options positions
    Given I have IBKR options positions
    When positions sync
    Then options should have correct strike and expiration
    And Greeks should be populated
    And underlying symbol should be correctly linked
```

---

### 2.4 Webull Connector

| Attribute | Value |
|-----------|-------|
| **File** | `src/brokerage_service/connectors/webull.py` |
| **Authentication** | Official API (OAuth 2.0) |
| **API Base URL** | `https://quoteapi.webull.com/api` |
| **Trade API** | `https://tradeapi.webull.com/api` |
| **Priority** | **Should Have** |
| **Phase** | Month 4 |

#### 2.4.1 Implementation Requirements

```python
class WebullConnector(BrokerageConnector):
    """
    Webull Official API connector
    OAuth 2.0 authentication
    """

    QUOTE_API_BASE = "https://quoteapi.webull.com/api"
    TRADE_API_BASE = "https://tradeapi.webull.com/api"
    AUTH_URL = "https://www.webull.com/oauth2/authorize"
    TOKEN_URL = "https://quoteapi.webull.com/api/oauth2/token"

    # Device ID required for API calls
    device_id: str

    def __init__(
        self,
        connection,
        client_id: str,
        client_secret: str,
        device_id: str
    ):
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
        self.device_id = device_id
```

#### 2.4.2 API Endpoints

| Endpoint | Purpose | Notes |
|----------|---------|-------|
| `GET /account/getSecAccountList` | List accounts | Returns account IDs |
| `GET /account/getAccountInfo` | Account details | Balance, buying power |
| `GET /account/positions` | Get positions | Stock and options |
| `GET /order/listOrders` | Order history | Includes fills |
| `POST /oauth2/revoke` | Revoke access | Disconnect |

#### 2.4.3 Webull-Specific Considerations

| Consideration | Handling |
|---------------|----------|
| **Device ID** | Generate unique device ID per user |
| **PIN requirement** | Trading PIN not needed for read-only |
| **Paper trading** | Separate account type, filter out |
| **Crypto** | Separate crypto account, optionally include |

#### 2.4.4 Gherkin Specification

```gherkin
Feature: Webull Brokerage Connection

  @webull @oauth
  Scenario: Connect Webull account
    Given I am on the "Link Accounts" screen
    When I select "Webull"
    And I complete Webull OAuth authorization
    Then my Webull account should be linked
    And my positions should begin syncing

  @webull @positions
  Scenario: Sync Webull positions excluding paper trading
    Given I have connected Webull with both live and paper accounts
    When sync completes
    Then only live account positions should appear
    And paper trading positions should be excluded
```

---

## 3. Portfolio Logic Completion

### 3.1 Total Cash Calculation

**File:** `src/brokerage_service/sync_service.py`
**Method:** `get_unified_portfolio()`
**Current State:** Returns `Decimal("0")` (TODO comment)

#### 3.1.1 Requirements

```python
async def get_unified_portfolio(self, user_id: uuid.UUID) -> Portfolio:
    """
    Enhanced portfolio calculation with cash aggregation
    """
    connections = self.repo.get_user_connections(user_id)

    # Aggregate cash from all accounts
    total_cash = Decimal("0")

    for connection in connections:
        connector = self.get_connector(connection)
        balance = await connector.get_account_balance()
        total_cash += Decimal(str(balance.get("cash", 0)))

    # ... rest of calculation
    portfolio.total_cash = total_cash
```

#### 3.1.2 Acceptance Criteria

- [ ] Cash balances aggregated from all connected brokerages
- [ ] Multi-currency cash converted to USD (base currency)
- [ ] Sweep accounts and money market funds included
- [ ] Margin debit balances subtracted from total
- [ ] Cash displayed per-account and total

---

### 3.2 Realized P&L Calculation

**File:** `src/brokerage_service/sync_service.py`
**Method:** `get_unified_portfolio()`
**Current State:** Returns `Decimal("0")` (TODO comment)

#### 3.2.1 Requirements

```python
async def calculate_realized_pl(self, user_id: uuid.UUID) -> Decimal:
    """
    Calculate realized P&L from transaction history

    Realized P&L = Sum of (sale proceeds - cost basis) for closed positions
    """
    transactions = self.repo.get_user_transactions(user_id, limit=1000)

    realized_pl = Decimal("0")

    # Filter closing transactions
    closing_types = ["sell", "buy_to_close", "sell_to_close", "expired", "assigned"]

    for txn in transactions:
        if txn.transaction_type in closing_types:
            # amount already includes cost basis impact
            realized_pl += txn.amount - txn.fees

    return realized_pl
```

#### 3.2.2 Transaction Types for Realized P&L

| Transaction Type | Treatment | Notes |
|-----------------|-----------|-------|
| `sell` | Proceeds - Cost Basis | Stock sales |
| `buy_to_close` | Cost - Premium Received | Short options |
| `sell_to_close` | Proceeds - Premium Paid | Long options |
| `expired` | -Premium Paid (long) or +Premium Received (short) | Option expiration |
| `assigned` | Handle as stock transaction | Option assignment |
| `exercised` | Handle as stock transaction | Option exercise |
| `dividend` | Add to realized P&L | Cash dividends |

#### 3.2.3 Acceptance Criteria

- [ ] All closing transactions contribute to realized P&L
- [ ] Option assignments and exercises handled correctly
- [ ] Dividends included in realized P&L
- [ ] Fees and commissions subtracted
- [ ] Wash sale adjustments applied (if data available)
- [ ] Realized P&L aggregated across all accounts

---

### 3.3 Day P&L Calculation

**File:** `src/brokerage_service/sync_service.py`
**Method:** `get_unified_portfolio()`
**Current State:** Returns `Decimal("0")` (TODO comment)

#### 3.3.1 Requirements

```python
async def calculate_day_pl(self, user_id: uuid.UUID) -> tuple[Decimal, Decimal]:
    """
    Calculate day P&L (change from market open)

    Returns: (day_pl, day_pl_percent)

    Day P&L = Current Value - Start of Day Value + Withdrawals - Deposits
    """
    # Get start of day snapshot
    start_of_day = await self.repo.get_portfolio_snapshot(
        user_id,
        snapshot_type="start_of_day"
    )

    # Get current portfolio
    current_portfolio = await self.get_unified_portfolio(user_id)

    # Calculate day change
    day_pl = current_portfolio.total_value - start_of_day.total_value

    # Adjust for intraday deposits/withdrawals
    intraday_deposits = await self.get_intraday_deposits(user_id)
    intraday_withdrawals = await self.get_intraday_withdrawals(user_id)

    day_pl = day_pl + intraday_withdrawals - intraday_deposits

    # Calculate percentage
    day_pl_percent = (day_pl / start_of_day.total_value * 100) if start_of_day.total_value else Decimal("0")

    return day_pl, day_pl_percent
```

#### 3.3.2 Start-of-Day Snapshot Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Timing** | Capture at 9:30 AM ET (market open) |
| **Storage** | Redis or database snapshot table |
| **Retention** | Keep 5 trading days for historical |
| **Pre-market** | Use previous close until market open |
| **Fallback** | If no snapshot, use previous close prices |

#### 3.3.3 Database Schema for Snapshots

```sql
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    snapshot_type VARCHAR(20) NOT NULL, -- 'start_of_day', 'end_of_day'
    total_value DECIMAL(15, 2) NOT NULL,
    total_cash DECIMAL(15, 2) NOT NULL,
    positions_snapshot JSONB, -- Array of position values
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, snapshot_type, DATE(captured_at))
);

CREATE INDEX idx_snapshots_user_date ON portfolio_snapshots(user_id, captured_at);
```

#### 3.3.4 Acceptance Criteria

- [ ] Start-of-day snapshots captured at market open
- [ ] Day P&L calculated correctly
- [ ] Deposits and withdrawals accounted for
- [ ] Day P&L percentage calculated
- [ ] Pre-market hours show previous day change
- [ ] Handles market holidays correctly

---

## 4. Security Requirements

### 4.1 CSRF Protection for OAuth

**File:** `src/brokerage_service/api.py`
**Location:** `oauth_callback()` endpoint
**Current State:** TODO comment: "Verify state matches"

#### 4.1.1 Requirements

```python
# Store state in Redis with expiry
async def initiate_brokerage_connection(
    provider: BrokerageProvider,
    user_id: uuid.UUID,
    redis: Redis
):
    state = str(uuid.uuid4())

    # Store state in Redis with 10-minute expiry
    await redis.setex(
        f"oauth_state:{state}",
        timedelta(minutes=10),
        json.dumps({
            "user_id": str(user_id),
            "provider": provider,
            "created_at": datetime.utcnow().isoformat()
        })
    )

    return {"authorization_url": ..., "state": state}


async def oauth_callback(
    provider: BrokerageProvider,
    code: str,
    state: str,
    redis: Redis
):
    # Verify state
    state_data = await redis.get(f"oauth_state:{state}")

    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state"
        )

    state_info = json.loads(state_data)

    # Verify provider matches
    if state_info["provider"] != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch"
        )

    # Delete state (one-time use)
    await redis.delete(f"oauth_state:{state}")

    # Continue with OAuth flow...
```

#### 4.1.2 Acceptance Criteria

- [ ] State generated as UUID for each OAuth initiation
- [ ] State stored in Redis with 10-minute TTL
- [ ] State validated on callback
- [ ] Provider verified to match original request
- [ ] State deleted after use (one-time)
- [ ] Expired states rejected
- [ ] Invalid states return 400 error

---

### 4.2 Token Revocation

**File:** `src/brokerage_service/api.py`
**Location:** `disconnect_brokerage()` endpoint
**Current State:** TODO comment: "Revoke tokens with brokerage"

#### 4.2.1 Requirements

```python
async def disconnect_brokerage(
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
    repo: BrokerageRepository,
    sync_service: PortfolioSyncService
):
    connection = repo.get_connection(connection_id)

    # Verify ownership
    if connection.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Revoke tokens with brokerage
    connector = sync_service.get_connector(connection)

    try:
        await connector.disconnect()
    except Exception as e:
        # Log but don't fail - we still want to remove local connection
        logger.warning(f"Token revocation failed: {e}")

    # Delete all associated data
    repo.delete_positions_for_connection(connection_id)
    repo.delete_transactions_for_connection(connection_id)
    repo.delete_connection(connection_id)
```

#### 4.2.2 Connector `disconnect()` Implementation

Each connector must implement token revocation:

```python
# Fidelity
async def disconnect(self):
    async with httpx.AsyncClient() as client:
        await client.post(
            self.REVOKE_URL,
            data={"token": self.connection.access_token}
        )

# Robinhood (Plaid)
async def disconnect(self):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{self.PLAID_BASE_URL}/item/remove",
            json={
                "client_id": self.plaid_client_id,
                "secret": self.plaid_secret,
                "access_token": self.connection.access_token
            }
        )

# IBKR
async def disconnect(self):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{self.base_url}/logout",
            headers={"Authorization": f"Bearer {self.connection.access_token}"}
        )

# Webull
async def disconnect(self):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{self.TOKEN_URL}/revoke",
            data={"token": self.connection.access_token}
        )
```

#### 4.2.3 Acceptance Criteria

- [ ] Token revocation attempted for all brokerages
- [ ] Revocation failures logged but don't block disconnection
- [ ] All positions deleted for connection
- [ ] All transactions deleted for connection
- [ ] Connection record deleted
- [ ] User notified of successful disconnection

---

### 4.3 Token Encryption

**Requirement:** Encrypt OAuth tokens at rest

#### 4.3.1 Implementation

```python
from cryptography.fernet import Fernet

class TokenEncryption:
    """
    Encrypt/decrypt OAuth tokens for storage
    Uses Fernet symmetric encryption (AES-128)
    """

    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, token: str) -> str:
        """Encrypt token for storage"""
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        """Decrypt token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()


# Usage in BrokerageConnection model
class BrokerageConnection(BaseModel):
    # Store encrypted tokens
    _access_token_encrypted: str
    _refresh_token_encrypted: str

    @property
    def access_token(self) -> str:
        return token_encryption.decrypt(self._access_token_encrypted)

    @access_token.setter
    def access_token(self, value: str):
        self._access_token_encrypted = token_encryption.encrypt(value)
```

#### 4.3.2 Acceptance Criteria

- [ ] Access tokens encrypted before database storage
- [ ] Refresh tokens encrypted before database storage
- [ ] Encryption key stored in environment variable or secrets manager
- [ ] Key rotation mechanism implemented
- [ ] Decryption happens in memory only

---

## 5. API Endpoints Summary

### 5.1 Existing Endpoints (Implemented)

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/api/v1/brokerages` | ✅ Complete |
| POST | `/api/v1/brokerages/{provider}/connect` | ✅ Complete |
| GET | `/api/v1/brokerages/{provider}/callback` | ⚠️ Needs CSRF |
| DELETE | `/api/v1/brokerages/{id}/disconnect` | ⚠️ Needs token revocation |
| GET | `/api/v1/portfolio` | ⚠️ Needs cash/P&L logic |
| GET | `/api/v1/portfolio/positions` | ✅ Complete |
| GET | `/api/v1/portfolio/performance` | ⚠️ Needs day P&L |
| POST | `/api/v1/portfolio/sync` | ✅ Complete |
| GET | `/api/v1/transactions` | ✅ Complete |

### 5.2 New Endpoints Required

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/portfolio/cash` | Get cash breakdown by account |
| GET | `/api/v1/portfolio/day-change` | Get day P&L details |
| GET | `/api/v1/brokerages/connections` | List user's connected brokerages |
| GET | `/api/v1/brokerages/connections/{id}/status` | Check connection health |
| POST | `/api/v1/brokerages/connections/{id}/refresh` | Force token refresh |

---

## 6. Database Schema Updates

### 6.1 New Tables Required

```sql
-- Portfolio snapshots for day P&L calculation
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    snapshot_type VARCHAR(20) NOT NULL,
    total_value DECIMAL(15, 2) NOT NULL,
    total_cash DECIMAL(15, 2) NOT NULL,
    positions_snapshot JSONB,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Account balances cache
CREATE TABLE account_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL,
    cash DECIMAL(15, 2) DEFAULT 0,
    equity DECIMAL(15, 2) DEFAULT 0,
    buying_power DECIMAL(15, 2) DEFAULT 0,
    margin_balance DECIMAL(15, 2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OAuth state for CSRF protection
-- (Alternative to Redis - for persistence)
CREATE TABLE oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Indexes
CREATE INDEX idx_snapshots_user ON portfolio_snapshots(user_id, captured_at);
CREATE INDEX idx_balances_connection ON account_balances(connection_id);
CREATE INDEX idx_oauth_state ON oauth_states(state);
CREATE INDEX idx_oauth_expires ON oauth_states(expires_at);
```

---

## 7. Configuration Requirements

### 7.1 Environment Variables

```bash
# Fidelity API
FIDELITY_CLIENT_ID=your_fidelity_client_id
FIDELITY_CLIENT_SECRET=your_fidelity_client_secret
FIDELITY_REDIRECT_URI=https://optix.app/oauth/callback/fidelity

# Plaid (for Robinhood)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=production  # sandbox, development, or production

# Interactive Brokers
IBKR_CLIENT_ID=your_ibkr_client_id
IBKR_CLIENT_SECRET=your_ibkr_client_secret
IBKR_REDIRECT_URI=https://optix.app/oauth/callback/ibkr

# Webull
WEBULL_CLIENT_ID=your_webull_client_id
WEBULL_CLIENT_SECRET=your_webull_client_secret
WEBULL_REDIRECT_URI=https://optix.app/oauth/callback/webull

# Token Encryption
TOKEN_ENCRYPTION_KEY=your_32_byte_base64_encoded_key

# Redis (for OAuth state)
REDIS_URL=redis://localhost:6379/0
```

### 7.2 Settings Class

```python
from pydantic_settings import BaseSettings

class BrokerageSettings(BaseSettings):
    # Fidelity
    fidelity_client_id: str
    fidelity_client_secret: str
    fidelity_redirect_uri: str = "https://optix.app/oauth/callback/fidelity"

    # Plaid
    plaid_client_id: str
    plaid_secret: str
    plaid_env: str = "production"

    # IBKR
    ibkr_client_id: str
    ibkr_client_secret: str
    ibkr_redirect_uri: str = "https://optix.app/oauth/callback/ibkr"

    # Webull
    webull_client_id: str
    webull_client_secret: str
    webull_redirect_uri: str = "https://optix.app/oauth/callback/webull"

    # Security
    token_encryption_key: str

    class Config:
        env_file = ".env"
        env_prefix = ""
```

---

## 8. Testing Requirements

### 8.1 Unit Tests

| Test File | Coverage Target |
|-----------|-----------------|
| `test_fidelity_connector.py` | 85%+ |
| `test_robinhood_connector.py` | 85%+ |
| `test_ibkr_connector.py` | 85%+ |
| `test_webull_connector.py` | 85%+ |
| `test_portfolio_logic.py` | 90%+ |
| `test_security.py` | 95%+ |

### 8.2 Integration Tests

```gherkin
Feature: Brokerage Integration Tests

  @integration @fidelity
  Scenario: Full Fidelity connection flow
    Given valid Fidelity API credentials
    When I initiate OAuth flow
    And complete Fidelity authorization
    Then connection should be established
    And positions should sync within 30 seconds

  @integration @portfolio
  Scenario: Multi-broker portfolio aggregation
    Given I have connected Schwab and Fidelity
    And both accounts have positions
    When I request unified portfolio
    Then all positions should be combined
    And total value should sum correctly
    And Greeks should aggregate across all options

  @integration @security
  Scenario: CSRF protection validation
    Given I initiate OAuth for Schwab
    When I try callback with modified state
    Then I should receive 400 error
    And connection should not be created
```

### 8.3 Mock Services

For testing without live APIs:

```python
class MockBrokerageConnector(BrokerageConnector):
    """Mock connector for testing"""

    async def authenticate(self, code: str) -> Dict[str, Any]:
        return {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }

    async def get_positions(self) -> List[Position]:
        return [
            Position(
                symbol="AAPL",
                position_type=PositionType.STOCK,
                quantity=Decimal("100"),
                average_price=Decimal("150.00"),
                cost_basis=Decimal("15000.00"),
                current_price=Decimal("175.00"),
                market_value=Decimal("17500.00"),
                unrealized_pl=Decimal("2500.00"),
                unrealized_pl_percent=Decimal("16.67")
            )
        ]
```

---

## 9. Non-Functional Requirements

| NFR ID | Requirement | Target | Priority |
|--------|-------------|--------|----------|
| NFR-B01 | OAuth connection completion | < 60 seconds | **Must Have** |
| NFR-B02 | Position sync time | < 30 seconds | **Must Have** |
| NFR-B03 | Unified portfolio response | < 2 seconds | **Must Have** |
| NFR-B04 | Token encryption | AES-256 | **Must Have** |
| NFR-B05 | API rate limiting | Per-brokerage limits | **Must Have** |
| NFR-B06 | Connection test frequency | Every 5 minutes | **Should Have** |
| NFR-B07 | Token refresh buffer | 5 minutes before expiry | **Should Have** |
| NFR-B08 | Error retry logic | 3 attempts with backoff | **Should Have** |

---

## 10. Implementation Plan

### 10.1 Phase 1: Fidelity Connector (Week 1-2)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Create `fidelity.py` connector | 8 hours | None |
| Implement OAuth flow | 4 hours | Connector |
| Implement positions sync | 4 hours | OAuth |
| Implement transactions sync | 4 hours | OAuth |
| Add Fidelity to sync_service | 2 hours | Connector |
| Unit tests | 4 hours | All above |
| Integration tests | 4 hours | All above |

### 10.2 Phase 2: Robinhood/Plaid (Week 2-3)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Integrate Plaid SDK | 4 hours | None |
| Create `robinhood.py` connector | 6 hours | Plaid SDK |
| Implement Plaid Link flow | 4 hours | Connector |
| Implement holdings sync | 4 hours | Link flow |
| Implement transactions sync | 4 hours | Link flow |
| Unit tests | 4 hours | All above |
| Integration tests | 4 hours | All above |

### 10.3 Phase 3: IBKR & Webull (Week 3-4)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Create `ibkr.py` connector | 8 hours | None |
| Create `webull.py` connector | 6 hours | None |
| Multi-currency handling | 4 hours | IBKR connector |
| Unit tests | 6 hours | All above |
| Integration tests | 4 hours | All above |

### 10.4 Phase 4: Portfolio Logic & Security (Week 4-5)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Cash aggregation | 4 hours | All connectors |
| Realized P&L calculation | 6 hours | Transactions |
| Day P&L with snapshots | 8 hours | None |
| CSRF protection | 4 hours | Redis |
| Token revocation | 4 hours | All connectors |
| Token encryption | 4 hours | None |
| Security tests | 4 hours | All above |

---

## 11. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Brokerage API changes | High | Medium | Abstract interface, version monitoring |
| Plaid cost increase | Medium | Low | Evaluate direct Robinhood API if available |
| Rate limit exceeded | Medium | Medium | Request throttling, caching |
| Token refresh failures | High | Low | Proactive refresh, user notification |
| Multi-currency complexity | Medium | Medium | Clear USD base currency conversion |

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Connection success rate | > 95% | OAuth completions / attempts |
| Sync reliability | > 99% | Successful syncs / total syncs |
| Portfolio accuracy | 100% | Spot check against brokerage |
| User adoption | > 50% | Users with 1+ brokerage linked |
| Multi-broker users | > 20% | Users with 2+ brokerages linked |

---

## 13. Appendix

### 13.1 File Structure

```
src/brokerage_service/
├── __init__.py
├── api.py                    # REST endpoints
├── models.py                 # Pydantic models
├── repository.py             # Data access layer
├── sync_service.py           # Portfolio sync logic
├── settings.py               # NEW: Brokerage settings
├── encryption.py             # NEW: Token encryption
├── connectors/
│   ├── __init__.py
│   ├── base.py               # Abstract base class
│   ├── schwab.py             # ✅ Implemented
│   ├── fidelity.py           # NEW: Fidelity connector
│   ├── robinhood.py          # NEW: Robinhood/Plaid connector
│   ├── ibkr.py               # NEW: Interactive Brokers connector
│   └── webull.py             # NEW: Webull connector
└── tests/
    ├── __init__.py
    ├── test_fidelity.py      # NEW
    ├── test_robinhood.py     # NEW
    ├── test_ibkr.py          # NEW
    ├── test_webull.py        # NEW
    ├── test_portfolio.py     # NEW
    └── test_security.py      # NEW
```

### 13.2 Dependencies to Add

```
# requirements.txt additions
plaid-python>=14.0.0      # Plaid SDK for Robinhood
cryptography>=41.0.0      # Token encryption
```

---

*End of Document*

*Version: 1.0*
*Last Updated: December 16, 2025*
*Author: Technical Architecture Team*