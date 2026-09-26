"""
Robinhood connector via Plaid
Uses Plaid Investment APIs
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType, TransactionType


class RobinhoodConnector(BrokerageConnector):
    """
    Robinhood connector via Plaid
    Uses Plaid Investment APIs for data access
    """
    
    PLAID_ENV = "production"  # or "sandbox" for testing
    PLAID_BASE_URL = "https://production.plaid.com"
    
    def __init__(self, connection, plaid_client_id: str, plaid_secret: str):
        """
        Initialize Robinhood connector with Plaid credentials
        
        Args:
            connection: BrokerageConnection instance
            plaid_client_id: Plaid client ID
            plaid_secret: Plaid secret key
        """
        super().__init__(connection)
        self.plaid_client_id = plaid_client_id
        self.plaid_secret = plaid_secret
    
    async def authenticate(self, public_token: str) -> Dict[str, Any]:
        """
        Exchange Plaid public_token for access_token
        
        Note: Different flow than OAuth - receives public_token from Plaid Link
        
        Args:
            public_token: Plaid public token from Link flow
            
        Returns:
            Dict with access_token, account_id, account_name
        """
        async with httpx.AsyncClient() as client:
            # Exchange public token for access token
            response = await client.post(
                f"{self.PLAID_BASE_URL}/item/public_token/exchange",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "public_token": public_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            access_token = data["access_token"]
            item_id = data["item_id"]
            
            # Get account info
            accounts_response = await client.post(
                f"{self.PLAID_BASE_URL}/accounts/get",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "access_token": access_token,
                },
            )
            accounts_response.raise_for_status()
            accounts_data = accounts_response.json()
            
            # Get first investment account
            accounts = accounts_data.get("accounts", [])
            investment_account = next(
                (acc for acc in accounts if acc.get("type") == "investment"),
                accounts[0] if accounts else {}
            )
            
            return {
                "access_token": access_token,
                "refresh_token": None,  # Plaid doesn't use refresh tokens
                "expires_at": None,  # Plaid access tokens don't expire
                "account_id": investment_account.get("account_id", item_id),
                "account_name": investment_account.get("name", "Robinhood Account"),
            }
    
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh token - not needed for Plaid
        Plaid access tokens don't expire
        
        Returns:
            Current access token info
        """
        return {
            "access_token": self.connection.access_token,
            "expires_at": None,
        }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict with account details
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.PLAID_BASE_URL}/accounts/get",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "access_token": self.connection.access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            accounts = data.get("accounts", [])
            account = next(
                (acc for acc in accounts if acc["account_id"] == self.connection.account_id),
                accounts[0] if accounts else {}
            )
            
            return {
                "account_id": account.get("account_id"),
                "account_name": account.get("name", "Robinhood Account"),
                "account_type": account.get("subtype", "investment").upper(),
            }
    
    async def get_positions(self) -> List[Position]:
        """
        Fetch positions via Plaid /investments/holdings
        
        Returns:
            List of Position objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.PLAID_BASE_URL}/investments/holdings/get",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "access_token": self.connection.access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            securities = {sec["security_id"]: sec for sec in data.get("securities", [])}
            
            for holding in data.get("holdings", []):
                # Skip if not for this account
                if holding.get("account_id") != self.connection.account_id:
                    continue
                
                security = securities.get(holding["security_id"], {})
                
                # Skip crypto (not supported yet)
                if security.get("type") == "cryptocurrency":
                    continue
                
                quantity = self._decimal(holding.get("quantity", 0))
                cost_basis = self._decimal(holding.get("cost_basis", 0))
                market_value = self._decimal(holding.get("institution_value", 0))
                
                # Calculate metrics
                avg_price = cost_basis / quantity if quantity else Decimal("0")
                current_price = market_value / quantity if quantity else Decimal("0")
                unrealized_pl = market_value - cost_basis
                unrealized_pl_pct = (unrealized_pl / cost_basis * 100) if cost_basis else Decimal("0")
                
                position = Position(
                    connection_id=self.connection.id,
                    symbol=security.get("ticker_symbol", "UNKNOWN"),
                    position_type=self._map_position_type(security.get("type", "equity")),
                    quantity=quantity,
                    average_price=avg_price,
                    cost_basis=cost_basis,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_pct,
                )
                
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        
        Returns:
            Dict with cash and equity balances
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.PLAID_BASE_URL}/accounts/balance/get",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "access_token": self.connection.access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            accounts = data.get("accounts", [])
            account = next(
                (acc for acc in accounts if acc["account_id"] == self.connection.account_id),
                {}
            )
            
            balances = account.get("balances", {})
            
            return {
                "cash": float(balances.get("available", 0)),
                "equity": float(balances.get("current", 0)),
                "buying_power": float(balances.get("available", 0)),
                "margin_balance": 0,  # Robinhood via Plaid doesn't provide margin
            }
    
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get transaction history via Plaid
        
        Args:
            start_date: Start date (default: 90 days ago)
            end_date: End date (default: today)
            
        Returns:
            List of Transaction objects
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=90)
        if not end_date:
            end_date = datetime.utcnow()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.PLAID_BASE_URL}/investments/transactions/get",
                json={
                    "client_id": self.plaid_client_id,
                    "secret": self.plaid_secret,
                    "access_token": self.connection.access_token,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                },
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            securities = {sec["security_id"]: sec for sec in data.get("securities", [])}
            
            for txn in data.get("investment_transactions", []):
                # Skip if not for this account
                if txn.get("account_id") != self.connection.account_id:
                    continue
                
                security = securities.get(txn.get("security_id"), {})
                
                transaction = Transaction(
                    connection_id=self.connection.id,
                    transaction_type=self._map_transaction_type(txn.get("type", "")),
                    symbol=security.get("ticker_symbol"),
                    quantity=self._decimal(txn.get("quantity", 0)),
                    price=self._decimal(txn.get("price", 0)),
                    amount=self._decimal(txn.get("amount", 0)),
                    fees=self._decimal(txn.get("fees", 0)),
                    transaction_date=datetime.strptime(txn["date"], "%Y-%m-%d"),
                    description=txn.get("name"),
                )
                transactions.append(transaction)
            
            return transactions
    
    async def disconnect(self):
        """
        Disconnect and remove Plaid item
        """
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.PLAID_BASE_URL}/item/remove",
                    json={
                        "client_id": self.plaid_client_id,
                        "secret": self.plaid_secret,
                        "access_token": self.connection.access_token,
                    },
                )
            self.logger.info(f"Successfully removed Plaid item for connection {self.connection.id}")
        except Exception as e:
            self.logger.warning(f"Failed to remove Plaid item: {e}")
    
    def _map_position_type(self, security_type: str) -> PositionType:
        """Map Plaid security type to PositionType"""
        mapping = {
            "equity": PositionType.STOCK,
            "etf": PositionType.ETF,
            "derivative": PositionType.OPTION,
            "mutual fund": PositionType.MUTUAL_FUND,
        }
        return mapping.get(security_type.lower(), PositionType.STOCK)
    
    def _map_transaction_type(self, txn_type: str) -> TransactionType:
        """Map Plaid transaction type to TransactionType"""
        mapping = {
            "buy": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "cash": TransactionType.DEPOSIT,
            "dividend": TransactionType.DIVIDEND,
            "interest": TransactionType.INTEREST,
        }
        return mapping.get(txn_type.lower(), TransactionType.BUY)
