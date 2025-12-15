# OPTIX Trading Platform - Remaining Tasks

## 🚨 Critical Missing Features (Phase 1 Gaps)

These features were listed as "Must Have" or part of Phase 1 deliverables but are currently missing or incomplete.

### 1. Brokerage Integrations (VS-7)
The README claims support for 5 brokerages, but only Schwab/TD Ameritrade is implemented.

- [ ] **Implement Fidelity Connector**
  - Create `src/brokerage_service/connectors/fidelity.py`
  - Implement OAuth flow for Fidelity
  - Update `PortfolioSyncService` to support Fidelity provider

- [ ] **Implement Robinhood Connector**
  - Create `src/brokerage_service/connectors/robinhood.py`
  - Implement Plaid integration for Robinhood (as per `api.py` metadata)
  - Update `PortfolioSyncService`

- [ ] **Implement Webull Connector**
  - Create `src/brokerage_service/connectors/webull.py`
  - Implement storage for API credentials

- [ ] **Implement Interactive Brokers Connector**
  - Create `src/brokerage_service/connectors/ibkr.py`
  - Implement Client Portal API integration

### 2. Portfolio Logic Gaps
Several key portfolio metrics have `TODO` comments in `src/brokerage_service/sync_service.py` and strictly return 0.

- [ ] **Calculate Total Cash**
  - Aggregate cash balances from all connected brokerage accounts
  - Update `get_unified_portfolio` method

- [ ] **Calculate Total Realized P&L**
  - Aggregate realized P&L from transaction history
  - Requires processing distinct transaction types (sell, buy_to_close)

- [ ] **Calculate Day P&L**
  - Implement mechanism to track "start of day" portfolio value
  - Calculate `day_pl` = `current_value` - `start_of_day_value` + `withdrawals` - `deposits`

### 3. Security & Reliability
- [ ] **CSRF Verification**
  - Implement state validation in `oauth_callback` (currently marked `# TODO: Verify state matches`)
  - Requires caching generated state with expiry in Redis

- [ ] **Token Revocation**
  - Implement token revocation in `disconnect_brokerage` (currently marked `# TODO: Revoke tokens`)
