"""
Base Brokerage Connector
Abstract interface for brokerage integrations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import Position, Transaction, BrokerageConnection


class BrokerageConnector(ABC):
    """
    Abstract base class for brokerage connectors
    Each brokerage implements this interface
    """
    
    def __init__(self, connection: BrokerageConnection):
        self.connection = connection
    
    @abstractmethod
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """
        Complete OAuth authentication flow
        Returns: access_token, refresh_token, expires_at
        """
        pass
    
    @abstractmethod
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh expired access token
        Returns: new access_token and expires_at
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        Returns: account details including type, name, etc.
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Fetch current positions from brokerage
        Returns: List of Position objects
        """
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        Returns: cash, equity, buying_power, etc.
        """
        pass
    
    @abstractmethod
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Fetch transaction history
        Returns: List of Transaction objects
        """
        pass
    
    async def disconnect(self):
        """
        Disconnect and revoke access
        Optional: Override if brokerage supports token revocation
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        Test if connection is still valid
        Returns: True if connection works, False otherwise
        """
        try:
            await self.get_account_info()
            return True
        except Exception:
            return False
