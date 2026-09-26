"""
Data repository for brokerage service
Handles database operations for connections, positions, and transactions
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uuid
import logging

from .models import (
    BrokerageConnection,
    Position,
    Transaction,
    PortfolioSnapshot,
    AccountBalance,
    BrokerageProvider,
)

logger = logging.getLogger(__name__)


class BrokerageRepository:
    """
    Repository for brokerage data access
    
    Note: This is a mock implementation. In production, this would
    interface with SQLAlchemy or another ORM.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize repository
        
        Args:
            db_session: Database session (SQLAlchemy session in production)
        """
        self.db = db_session
        # In-memory storage for demo purposes
        self._connections: Dict[uuid.UUID, BrokerageConnection] = {}
        self._positions: Dict[uuid.UUID, List[Position]] = {}
        self._transactions: Dict[uuid.UUID, List[Transaction]] = {}
        self._snapshots: Dict[uuid.UUID, List[PortfolioSnapshot]] = {}
        self._balances: Dict[uuid.UUID, AccountBalance] = {}
    
    # Connection operations
    
    def create_connection(self, connection: BrokerageConnection) -> BrokerageConnection:
        """Create a new brokerage connection"""
        self._connections[connection.id] = connection
        logger.info(f"Created connection {connection.id} for user {connection.user_id}")
        return connection
    
    def get_connection(self, connection_id: uuid.UUID) -> Optional[BrokerageConnection]:
        """Get connection by ID"""
        return self._connections.get(connection_id)
    
    def get_user_connections(
        self,
        user_id: uuid.UUID,
        active_only: bool = True
    ) -> List[BrokerageConnection]:
        """Get all connections for a user"""
        connections = [
            conn for conn in self._connections.values()
            if conn.user_id == user_id
        ]
        if active_only:
            connections = [conn for conn in connections if conn.is_active]
        return connections
    
    def update_connection(self, connection: BrokerageConnection) -> BrokerageConnection:
        """Update connection"""
        connection.updated_at = datetime.utcnow()
        self._connections[connection.id] = connection
        return connection
    
    def delete_connection(self, connection_id: uuid.UUID) -> bool:
        """Delete connection"""
        if connection_id in self._connections:
            del self._connections[connection_id]
            logger.info(f"Deleted connection {connection_id}")
            return True
        return False
    
    # Position operations
    
    def save_positions(self, positions: List[Position]) -> List[Position]:
        """Save positions for a connection"""
        if not positions:
            return []
        
        connection_id = positions[0].connection_id
        self._positions[connection_id] = positions
        logger.info(f"Saved {len(positions)} positions for connection {connection_id}")
        return positions
    
    def get_positions(self, connection_id: uuid.UUID) -> List[Position]:
        """Get positions for a connection"""
        return self._positions.get(connection_id, [])
    
    def get_user_positions(self, user_id: uuid.UUID) -> List[Position]:
        """Get all positions for a user across all connections"""
        connections = self.get_user_connections(user_id)
        positions = []
        for conn in connections:
            positions.extend(self.get_positions(conn.id))
        return positions
    
    def delete_positions_for_connection(self, connection_id: uuid.UUID) -> bool:
        """Delete all positions for a connection"""
        if connection_id in self._positions:
            del self._positions[connection_id]
            logger.info(f"Deleted positions for connection {connection_id}")
            return True
        return False
    
    # Transaction operations
    
    def save_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """Save transactions for a connection"""
        if not transactions:
            return []
        
        connection_id = transactions[0].connection_id
        existing = self._transactions.get(connection_id, [])
        existing.extend(transactions)
        self._transactions[connection_id] = existing
        logger.info(f"Saved {len(transactions)} transactions for connection {connection_id}")
        return transactions
    
    def get_transactions(
        self,
        connection_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Transaction]:
        """Get transactions for a connection"""
        transactions = self._transactions.get(connection_id, [])
        
        # Filter by date range
        if start_date:
            transactions = [t for t in transactions if t.transaction_date >= start_date]
        if end_date:
            transactions = [t for t in transactions if t.transaction_date <= end_date]
        
        # Sort by date descending
        transactions.sort(key=lambda t: t.transaction_date, reverse=True)
        
        # Apply limit
        if limit:
            transactions = transactions[:limit]
        
        return transactions
    
    def get_user_transactions(
        self,
        user_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Transaction]:
        """Get all transactions for a user"""
        connections = self.get_user_connections(user_id)
        transactions = []
        for conn in connections:
            transactions.extend(self.get_transactions(conn.id, start_date, end_date))
        
        # Sort by date descending
        transactions.sort(key=lambda t: t.transaction_date, reverse=True)
        
        # Apply limit
        if limit:
            transactions = transactions[:limit]
        
        return transactions
    
    def delete_transactions_for_connection(self, connection_id: uuid.UUID) -> bool:
        """Delete all transactions for a connection"""
        if connection_id in self._transactions:
            del self._transactions[connection_id]
            logger.info(f"Deleted transactions for connection {connection_id}")
            return True
        return False
    
    # Portfolio snapshot operations
    
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Save a portfolio snapshot"""
        if snapshot.user_id not in self._snapshots:
            self._snapshots[snapshot.user_id] = []
        self._snapshots[snapshot.user_id].append(snapshot)
        logger.info(f"Saved {snapshot.snapshot_type} snapshot for user {snapshot.user_id}")
        return snapshot
    
    def get_portfolio_snapshot(
        self,
        user_id: uuid.UUID,
        snapshot_type: str,
        snapshot_date: Optional[date] = None
    ) -> Optional[PortfolioSnapshot]:
        """Get most recent snapshot of given type"""
        if snapshot_date is None:
            snapshot_date = date.today()
        
        snapshots = self._snapshots.get(user_id, [])
        matching = [
            s for s in snapshots
            if s.snapshot_type == snapshot_type
            and s.captured_at.date() == snapshot_date
        ]
        
        if matching:
            return max(matching, key=lambda s: s.captured_at)
        return None
    
    def get_snapshots_for_user(
        self,
        user_id: uuid.UUID,
        days: int = 5
    ) -> List[PortfolioSnapshot]:
        """Get recent snapshots for a user"""
        cutoff = datetime.utcnow().date()
        snapshots = self._snapshots.get(user_id, [])
        return [
            s for s in snapshots
            if (cutoff - s.captured_at.date()).days <= days
        ]
    
    # Account balance operations
    
    def save_account_balance(self, balance: AccountBalance) -> AccountBalance:
        """Save account balance"""
        self._balances[balance.connection_id] = balance
        return balance
    
    def get_account_balance(self, connection_id: uuid.UUID) -> Optional[AccountBalance]:
        """Get account balance"""
        return self._balances.get(connection_id)
    
    def get_user_balances(self, user_id: uuid.UUID) -> List[AccountBalance]:
        """Get all account balances for a user"""
        connections = self.get_user_connections(user_id)
        balances = []
        for conn in connections:
            balance = self.get_account_balance(conn.id)
            if balance:
                balances.append(balance)
        return balances
