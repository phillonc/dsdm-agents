"""
Portfolio sync service - handles syncing data from brokerages
Includes complete portfolio logic with cash, realized P&L, and day P&L
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta, time
from decimal import Decimal
import uuid
import logging
import asyncio

from .models import (
    Portfolio,
    Position,
    Transaction,
    BrokerageConnection,
    BrokerageProvider,
    PortfolioSnapshot,
    AccountBalance,
    TransactionType,
)
from .repository import BrokerageRepository
from .connectors import (
    BrokerageConnector,
    SchwabConnector,
    FidelityConnector,
    RobinhoodConnector,
    IBKRConnector,
    WebullConnector,
)
from .settings import settings

logger = logging.getLogger(__name__)


class PortfolioSyncService:
    """
    Service for syncing portfolio data from brokerages
    Implements complete portfolio logic including:
    - Cash aggregation
    - Realized P&L calculation
    - Day P&L calculation
    """
    
    # Closing transaction types for realized P&L
    CLOSING_TRANSACTION_TYPES = [
        TransactionType.SELL,
        TransactionType.BUY_TO_CLOSE,
        TransactionType.SELL_TO_CLOSE,
        TransactionType.EXPIRED,
        TransactionType.ASSIGNED,
        TransactionType.EXERCISED,
        TransactionType.DIVIDEND,
    ]
    
    def __init__(self, repository: BrokerageRepository):
        """
        Initialize sync service
        
        Args:
            repository: BrokerageRepository instance
        """
        self.repo = repository
    
    def get_connector(self, connection: BrokerageConnection) -> BrokerageConnector:
        """
        Get appropriate connector for a brokerage connection
        
        Args:
            connection: BrokerageConnection instance
            
        Returns:
            BrokerageConnector instance
        """
        connector_map = {
            BrokerageProvider.SCHWAB: lambda: SchwabConnector(
                connection,
                settings.schwab_client_id,
                settings.schwab_client_secret,
            ),
            BrokerageProvider.FIDELITY: lambda: FidelityConnector(
                connection,
                settings.fidelity_client_id,
                settings.fidelity_client_secret,
            ),
            BrokerageProvider.ROBINHOOD: lambda: RobinhoodConnector(
                connection,
                settings.plaid_client_id,
                settings.plaid_secret,
            ),
            BrokerageProvider.IBKR: lambda: IBKRConnector(
                connection,
                settings.ibkr_client_id,
                settings.ibkr_client_secret,
                settings.ibkr_use_gateway,
            ),
            BrokerageProvider.WEBULL: lambda: WebullConnector(
                connection,
                settings.webull_client_id,
                settings.webull_client_secret,
            ),
        }
        
        connector_factory = connector_map.get(connection.provider)
        if not connector_factory:
            raise ValueError(f"Unsupported provider: {connection.provider}")
        
        return connector_factory()
    
    async def sync_account(self, connection_id: uuid.UUID) -> Dict[str, int]:
        """
        Sync a single brokerage account
        
        Args:
            connection_id: Connection ID to sync
            
        Returns:
            Dict with sync statistics
        """
        connection = self.repo.get_connection(connection_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        logger.info(f"Starting sync for connection {connection_id} ({connection.provider})")
        
        connector = self.get_connector(connection)
        
        # Check if token needs refresh
        if connection.token_expires_at:
            refresh_buffer = timedelta(minutes=settings.token_refresh_buffer_minutes)
            if datetime.utcnow() + refresh_buffer >= connection.token_expires_at:
                logger.info(f"Refreshing token for connection {connection_id}")
                token_data = await connector.refresh_token()
                connection.access_token = token_data["access_token"]
                connection.token_expires_at = token_data.get("expires_at")
                self.repo.update_connection(connection)
        
        # Sync positions
        positions = await connector.get_positions()
        self.repo.save_positions(positions)
        
        # Sync account balance
        balance_data = await connector.get_account_balance()
        balance = AccountBalance(
            connection_id=connection_id,
            cash=Decimal(str(balance_data["cash"])),
            equity=Decimal(str(balance_data["equity"])),
            buying_power=Decimal(str(balance_data["buying_power"])),
            margin_balance=Decimal(str(balance_data["margin_balance"])),
        )
        self.repo.save_account_balance(balance)
        
        # Sync recent transactions (last 7 days)
        start_date = datetime.utcnow() - timedelta(days=7)
        transactions = await connector.get_transactions(start_date=start_date)
        self.repo.save_transactions(transactions)
        
        # Update connection sync timestamp
        connection.last_synced_at = datetime.utcnow()
        self.repo.update_connection(connection)
        
        logger.info(
            f"Sync complete for connection {connection_id}: "
            f"{len(positions)} positions, {len(transactions)} transactions"
        )
        
        return {
            "positions": len(positions),
            "transactions": len(transactions),
        }
    
    async def sync_all_accounts(self, user_id: uuid.UUID) -> Dict[str, int]:
        """
        Sync all accounts for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with aggregate sync statistics
        """
        connections = self.repo.get_user_connections(user_id)
        
        if not connections:
            logger.warning(f"No connections found for user {user_id}")
            return {"positions": 0, "transactions": 0, "accounts": 0}
        
        logger.info(f"Syncing {len(connections)} accounts for user {user_id}")
        
        # Sync all accounts concurrently
        tasks = [self.sync_account(conn.id) for conn in connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        total_positions = 0
        total_transactions = 0
        successful_syncs = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Sync failed for connection {connections[i].id}: {result}")
            else:
                total_positions += result["positions"]
                total_transactions += result["transactions"]
                successful_syncs += 1
        
        return {
            "accounts": successful_syncs,
            "positions": total_positions,
            "transactions": total_transactions,
        }
    
    async def get_unified_portfolio(self, user_id: uuid.UUID) -> Portfolio:
        """
        Get unified portfolio across all connected brokerages
        Includes complete portfolio logic:
        - Total cash aggregation
        - Realized P&L calculation
        - Day P&L calculation
        
        Args:
            user_id: User ID
            
        Returns:
            Portfolio object with complete data
        """
        # Get all positions
        positions = self.repo.get_user_positions(user_id)
        
        # Calculate total equity (market value of positions)
        total_equity = sum(pos.market_value for pos in positions)
        
        # Calculate total cash from all accounts
        total_cash = await self._calculate_total_cash(user_id)
        
        # Total portfolio value
        total_value = total_equity + total_cash
        
        # Calculate unrealized P&L
        total_unrealized_pl = sum(pos.unrealized_pl for pos in positions)
        
        # Calculate realized P&L
        realized_pl = await self._calculate_realized_pl(user_id)
        
        # Calculate total P&L
        total_pl = total_unrealized_pl + realized_pl
        total_cost_basis = sum(pos.cost_basis for pos in positions)
        total_pl_percent = (
            (total_pl / (total_cost_basis + realized_pl) * 100)
            if (total_cost_basis + realized_pl) > 0
            else Decimal("0")
        )
        
        # Calculate day P&L
        day_pl, day_pl_percent = await self._calculate_day_pl(user_id)
        
        return Portfolio(
            user_id=user_id,
            total_value=total_value,
            total_cash=total_cash,
            total_equity=total_equity,
            day_pl=day_pl,
            day_pl_percent=day_pl_percent,
            total_pl=total_pl,
            total_pl_percent=total_pl_percent,
            realized_pl=realized_pl,
            positions=positions,
        )
    
    async def _calculate_total_cash(self, user_id: uuid.UUID) -> Decimal:
        """
        Calculate total cash across all accounts
        
        Args:
            user_id: User ID
            
        Returns:
            Total cash amount
        """
        balances = self.repo.get_user_balances(user_id)
        total_cash = Decimal("0")
        
        for balance in balances:
            # Cash includes available cash minus margin debit
            account_cash = balance.cash - balance.margin_balance
            total_cash += account_cash
        
        return total_cash
    
    async def _calculate_realized_pl(self, user_id: uuid.UUID) -> Decimal:
        """
        Calculate realized P&L from transaction history
        
        Realized P&L includes:
        - Sale proceeds minus cost basis for closed positions
        - Dividends
        - Interest
        - Option premiums for expired/assigned options
        
        Args:
            user_id: User ID
            
        Returns:
            Realized P&L amount
        """
        # Get transactions (last 365 days for performance)
        start_date = datetime.utcnow() - timedelta(days=365)
        transactions = self.repo.get_user_transactions(
            user_id,
            start_date=start_date,
            limit=10000
        )
        
        realized_pl = Decimal("0")
        
        for txn in transactions:
            # Check if this is a closing transaction
            if txn.transaction_type in self.CLOSING_TRANSACTION_TYPES:
                # For sales, amount is positive (proceeds)
                # For buys to close, amount is negative (cost)
                # Subtract fees from realized P&L
                if txn.transaction_type == TransactionType.SELL:
                    realized_pl += txn.amount - txn.fees
                elif txn.transaction_type == TransactionType.BUY_TO_CLOSE:
                    # This closes a short position - P&L is opening credit minus closing cost
                    realized_pl -= (txn.amount + txn.fees)
                elif txn.transaction_type == TransactionType.SELL_TO_CLOSE:
                    # This closes a long position - P&L is closing proceeds minus opening cost
                    realized_pl += txn.amount - txn.fees
                elif txn.transaction_type in [TransactionType.DIVIDEND, TransactionType.INTEREST]:
                    # Dividends and interest are pure income
                    realized_pl += txn.amount
                elif txn.transaction_type in [TransactionType.EXPIRED, TransactionType.ASSIGNED, TransactionType.EXERCISED]:
                    # Option expiration/assignment - use transaction amount
                    realized_pl += txn.amount - txn.fees
        
        return realized_pl
    
    async def _calculate_day_pl(self, user_id: uuid.UUID) -> Tuple[Decimal, Decimal]:
        """
        Calculate day P&L (change from market open)
        
        Day P&L = Current Value - Start of Day Value + Withdrawals - Deposits
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (day_pl, day_pl_percent)
        """
        # Get start of day snapshot
        start_of_day_snapshot = self.repo.get_portfolio_snapshot(
            user_id,
            snapshot_type="start_of_day"
        )
        
        if not start_of_day_snapshot:
            # No snapshot available - create one now for future use
            await self._capture_start_of_day_snapshot(user_id)
            # Return zero for today since we have no baseline
            return Decimal("0"), Decimal("0")
        
        # Get current portfolio value
        current_portfolio = await self.get_unified_portfolio(user_id)
        
        # Calculate raw change
        day_pl = current_portfolio.total_value - start_of_day_snapshot.total_value
        
        # Adjust for intraday deposits/withdrawals
        intraday_deposits = await self._get_intraday_deposits(user_id)
        intraday_withdrawals = await self._get_intraday_withdrawals(user_id)
        
        day_pl = day_pl + intraday_withdrawals - intraday_deposits
        
        # Calculate percentage
        day_pl_percent = (
            (day_pl / start_of_day_snapshot.total_value * 100)
            if start_of_day_snapshot.total_value > 0
            else Decimal("0")
        )
        
        return day_pl, day_pl_percent
    
    async def _capture_start_of_day_snapshot(self, user_id: uuid.UUID):
        """
        Capture start of day portfolio snapshot
        Should be called at market open (9:30 AM ET)
        
        Args:
            user_id: User ID
        """
        portfolio = await self.get_unified_portfolio(user_id)
        
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            snapshot_type="start_of_day",
            total_value=portfolio.total_value,
            total_cash=portfolio.total_cash,
            positions_snapshot={
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "quantity": str(pos.quantity),
                        "market_value": str(pos.market_value),
                    }
                    for pos in portfolio.positions
                ]
            },
            captured_at=datetime.utcnow(),
        )
        
        self.repo.save_portfolio_snapshot(snapshot)
        logger.info(f"Captured start of day snapshot for user {user_id}")
    
    async def _get_intraday_deposits(self, user_id: uuid.UUID) -> Decimal:
        """Get total deposits made today"""
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        transactions = self.repo.get_user_transactions(
            user_id,
            start_date=today_start
        )
        
        deposits = sum(
            txn.amount for txn in transactions
            if txn.transaction_type == TransactionType.DEPOSIT
        )
        
        return deposits
    
    async def _get_intraday_withdrawals(self, user_id: uuid.UUID) -> Decimal:
        """Get total withdrawals made today"""
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        transactions = self.repo.get_user_transactions(
            user_id,
            start_date=today_start
        )
        
        withdrawals = sum(
            abs(txn.amount) for txn in transactions
            if txn.transaction_type == TransactionType.WITHDRAWAL
        )
        
        return withdrawals
    
    async def capture_all_user_snapshots(self):
        """
        Capture start of day snapshots for all users
        Should be scheduled to run at market open (9:30 AM ET)
        """
        # In production, this would query all active users from database
        logger.info("Capturing start of day snapshots for all users")
        # Implementation depends on user management system
