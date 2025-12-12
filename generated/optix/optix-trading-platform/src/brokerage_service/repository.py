"""
Brokerage Repository
Data access layer for brokerage connections and portfolio data
"""
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import BrokerageConnection, Position, Transaction


class BrokerageRepository:
    """
    Brokerage repository for database operations
    In production, use PostgreSQL with proper encryption for tokens
    """
    
    def __init__(self):
        # In-memory storage for demonstration
        self._connections: Dict[uuid.UUID, BrokerageConnection] = {}
        self._positions: Dict[uuid.UUID, Position] = {}
        self._transactions: Dict[uuid.UUID, Transaction] = {}
        self._user_connection_index: Dict[uuid.UUID, List[uuid.UUID]] = {}
    
    def create_connection(self, connection: BrokerageConnection) -> BrokerageConnection:
        """Create new brokerage connection"""
        self._connections[connection.id] = connection
        
        # Update user index
        if connection.user_id not in self._user_connection_index:
            self._user_connection_index[connection.user_id] = []
        self._user_connection_index[connection.user_id].append(connection.id)
        
        return connection
    
    def get_connection(self, connection_id: uuid.UUID) -> Optional[BrokerageConnection]:
        """Get connection by ID"""
        return self._connections.get(connection_id)
    
    def get_user_connections(self, user_id: uuid.UUID) -> List[BrokerageConnection]:
        """Get all connections for a user"""
        connection_ids = self._user_connection_index.get(user_id, [])
        connections = [
            self._connections[cid]
            for cid in connection_ids
            if cid in self._connections
        ]
        return connections
    
    def update_connection(
        self,
        connection_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> BrokerageConnection:
        """Update connection"""
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError("Connection not found")
        
        for key, value in updates.items():
            if hasattr(connection, key):
                setattr(connection, key, value)
        
        connection.updated_at = datetime.utcnow()
        return connection
    
    def delete_connection(self, connection_id: uuid.UUID) -> bool:
        """Delete connection and associated data"""
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        
        # Delete associated positions
        position_ids = [
            pid for pid, pos in self._positions.items()
            if pos.connection_id == connection_id
        ]
        for pid in position_ids:
            del self._positions[pid]
        
        # Delete associated transactions
        txn_ids = [
            tid for tid, txn in self._transactions.items()
            if txn.connection_id == connection_id
        ]
        for tid in txn_ids:
            del self._transactions[tid]
        
        # Delete connection
        del self._connections[connection_id]
        
        # Update user index
        if connection.user_id in self._user_connection_index:
            self._user_connection_index[connection.user_id].remove(connection_id)
        
        return True
    
    def save_positions(self, positions: List[Position]):
        """Save/update positions"""
        for position in positions:
            self._positions[position.id] = position
    
    def get_connection_positions(
        self,
        connection_id: uuid.UUID
    ) -> List[Position]:
        """Get positions for a connection"""
        return [
            pos for pos in self._positions.values()
            if pos.connection_id == connection_id
        ]
    
    def get_user_positions(self, user_id: uuid.UUID) -> List[Position]:
        """Get all positions for a user"""
        return [
            pos for pos in self._positions.values()
            if pos.user_id == user_id
        ]
    
    def save_transactions(self, transactions: List[Transaction]):
        """Save transactions"""
        for transaction in transactions:
            self._transactions[transaction.id] = transaction
    
    def get_user_transactions(
        self,
        user_id: uuid.UUID,
        limit: int = 100
    ) -> List[Transaction]:
        """Get transactions for a user"""
        txns = [
            txn for txn in self._transactions.values()
            if txn.user_id == user_id
        ]
        # Sort by date descending
        txns.sort(key=lambda t: t.transaction_date, reverse=True)
        return txns[:limit]
