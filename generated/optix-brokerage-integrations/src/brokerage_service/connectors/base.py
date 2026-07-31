"""
Base abstract connector for all brokerage integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import logging

from ..models import Position, Transaction, BrokerageConnection

logger = logging.getLogger(__name__)


class BrokerageConnector(ABC):
    """
    Abstract base class for all brokerage connectors
    
    All brokerage integrations must implement this interface to ensure
    consistent behavior across different providers.
    """
    
    def __init__(self, connection: BrokerageConnection):
        """
        Initialize connector with brokerage connection
        
        Args:
            connection: BrokerageConnection instance with credentials
        """
        self.connection = connection
        self.logger = logger
    
    @abstractmethod
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """
        Authenticate user and obtain access tokens
        
        Args:
            authorization_code: OAuth authorization code from callback
            
        Returns:
            Dict containing:
                - access_token: Access token
                - refresh_token: Refresh token (optional)
                - expires_at: Token expiration datetime
                - account_id: Primary account ID
                - account_name: Account display name
        """
        pass
    
    @abstractmethod
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh expired access token
        
        Returns:
            Dict containing new access_token and expires_at
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict containing account details:
                - account_id: Account ID
                - account_name: Account name
                - account_type: Account type (e.g., 'CASH', 'MARGIN')
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get current positions for the account
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        
        Returns:
            Dict containing:
                - cash: Available cash
                - equity: Total equity value
                - buying_power: Available buying power
                - margin_balance: Margin balance (if applicable)
        """
        pass
    
    @abstractmethod
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get transaction history
        
        Args:
            start_date: Start date for transaction query
            end_date: End date for transaction query
            
        Returns:
            List of Transaction objects
        """
        pass
    
    async def disconnect(self):
        """
        Disconnect and revoke tokens with brokerage
        
        Optional override for brokerages that support token revocation
        """
        self.logger.info(f"Disconnect not implemented for {self.connection.provider}")
    
    async def test_connection(self) -> bool:
        """
        Test if connection is valid
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            await self.get_account_info()
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def _decimal(self, value: Any) -> Decimal:
        """
        Convert value to Decimal safely
        
        Args:
            value: Value to convert
            
        Returns:
            Decimal value
        """
        if value is None:
            return Decimal("0")
        return Decimal(str(value))
