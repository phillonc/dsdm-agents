"""
Interactive Brokers Client Portal API connector
Supports both Gateway and Web API modes
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType, TransactionType


class IBKRConnector(BrokerageConnector):
    """
    Interactive Brokers Client Portal API connector
    Supports both local Gateway and Web API modes
    """
    
    # Web API endpoints (recommended for cloud deployment)
    WEB_API_BASE = "https://api.ibkr.com/v1/api"
    WEB_AUTH_URL = "https://www.interactivebrokers.com/authorize"
    WEB_TOKEN_URL = "https://api.ibkr.com/v1/api/oauth/token"
    
    # Gateway endpoints (alternative - local installation)
    GATEWAY_BASE = "https://localhost:5000/v1/api"
    
    # Rate limiting
    MAX_REQUESTS_PER_SECOND = 10
    
    def __init__(
        self,
        connection,
        client_id: str,
        client_secret: str,
        use_gateway: bool = False
    ):
        """
        Initialize IBKR connector
        
        Args:
            connection: BrokerageConnection instance
            client_id: IBKR client ID
            client_secret: IBKR client secret
            use_gateway: Use local gateway vs web API (default: False)
        """
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = self.GATEWAY_BASE if use_gateway else self.WEB_API_BASE
        self.use_gateway = use_gateway
    
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """
        Authenticate and obtain access tokens
        
        Args:
            authorization_code: OAuth authorization code
            
        Returns:
            Dict with access_token, expires_at, account_id
        """
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            response = await client.post(
                self.WEB_TOKEN_URL if not self.use_gateway else f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Get account list
            accounts = await self._get_accounts(data["access_token"])
            primary_account = accounts[0] if accounts else {}
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600)),
                "account_id": primary_account.get("accountId", "primary"),
                "account_name": primary_account.get("accountTitle", "IBKR Account"),
            }
    
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh access token
        
        Returns:
            Dict with new access_token and expires_at
        """
        if not self.connection.refresh_token:
            raise ValueError("No refresh token available")
        
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            response = await client.post(
                self.WEB_TOKEN_URL if not self.use_gateway else f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.connection.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600)),
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict with account details
        """
        accounts = await self._get_accounts(self.connection.access_token)
        account = next(
            (acc for acc in accounts if acc["accountId"] == self.connection.account_id),
            accounts[0] if accounts else {}
        )
        
        return {
            "account_id": account.get("accountId"),
            "account_name": account.get("accountTitle", "IBKR Account"),
            "account_type": account.get("type", "INDIVIDUAL"),
        }
    
    async def get_positions(self) -> List[Position]:
        """
        Get current positions
        
        Returns:
            List of Position objects
        """
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            response = await client.get(
                f"{self.base_url}/portfolio/{self.connection.account_id}/positions",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos in data:
                quantity = self._decimal(pos.get("position", 0))
                avg_price = self._decimal(pos.get("avgPrice", 0))
                market_price = self._decimal(pos.get("marketPrice", 0))
                market_value = self._decimal(pos.get("marketValue", 0))
                
                cost_basis = quantity * avg_price
                unrealized_pl = self._decimal(pos.get("unrealizedPnl", 0))
                unrealized_pl_pct = (unrealized_pl / cost_basis * 100) if cost_basis else Decimal("0")
                
                position = Position(
                    connection_id=self.connection.id,
                    symbol=pos.get("ticker", pos.get("contractDesc", "UNKNOWN")),
                    position_type=self._map_position_type(pos.get("assetClass", "STK")),
                    quantity=quantity,
                    average_price=avg_price,
                    cost_basis=cost_basis,
                    current_price=market_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_pct,
                )
                
                # Add option-specific data if available
                if pos.get("assetClass") == "OPT":
                    position.strike_price = self._decimal(pos.get("strike"))
                    position.option_type = pos.get("right")  # C or P
                    if pos.get("expiry"):
                        position.expiration_date = datetime.strptime(pos["expiry"], "%Y%m%d")
                
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        
        Returns:
            Dict with balance details
        """
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            # Get account summary
            response = await client.get(
                f"{self.base_url}/portfolio/{self.connection.account_id}/summary",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Get ledger for cash balance
            ledger_response = await client.get(
                f"{self.base_url}/portfolio/{self.connection.account_id}/ledger",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            ledger_response.raise_for_status()
            ledger = ledger_response.json()
            
            # Extract USD balances (convert multi-currency if needed)
            cash = 0.0
            for currency, balance in ledger.items():
                if currency == "BASE":
                    cash = float(balance.get("cashbalance", 0))
                    break
            
            return {
                "cash": cash,
                "equity": float(data.get("totalcashvalue", {}).get("amount", 0)),
                "buying_power": float(data.get("buyingpower", {}).get("amount", 0)),
                "margin_balance": float(data.get("marginbalance", {}).get("amount", 0)),
            }
    
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get transaction history
        
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
        
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            response = await client.get(
                f"{self.base_url}/iserver/account/trades",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data:
                # Filter by date range
                txn_date = datetime.fromisoformat(txn["execution_time"])
                if not (start_date <= txn_date <= end_date):
                    continue
                
                transaction = Transaction(
                    connection_id=self.connection.id,
                    transaction_type=self._map_transaction_type(txn.get("side", "")),
                    symbol=txn.get("ticker"),
                    quantity=self._decimal(txn.get("size", 0)),
                    price=self._decimal(txn.get("price", 0)),
                    amount=self._decimal(txn.get("amount", 0)),
                    fees=self._decimal(txn.get("commission", 0)),
                    transaction_date=txn_date,
                    description=txn.get("order_description"),
                )
                transactions.append(transaction)
            
            return transactions
    
    async def disconnect(self):
        """
        Logout and revoke session
        """
        try:
            async with httpx.AsyncClient(verify=not self.use_gateway) as client:
                await client.post(
                    f"{self.base_url}/logout",
                    headers={"Authorization": f"Bearer {self.connection.access_token}"},
                )
            self.logger.info(f"Successfully logged out IBKR connection {self.connection.id}")
        except Exception as e:
            self.logger.warning(f"Failed to logout IBKR: {e}")
    
    async def _get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get list of accounts"""
        async with httpx.AsyncClient(verify=not self.use_gateway) as client:
            response = await client.get(
                f"{self.base_url}/portfolio/accounts",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    def _map_position_type(self, asset_class: str) -> PositionType:
        """Map IBKR asset class to PositionType"""
        mapping = {
            "STK": PositionType.STOCK,
            "OPT": PositionType.OPTION,
            "ETF": PositionType.ETF,
            "FUT": PositionType.OPTION,  # Map futures to option for now
        }
        return mapping.get(asset_class, PositionType.STOCK)
    
    def _map_transaction_type(self, side: str) -> TransactionType:
        """Map IBKR side to TransactionType"""
        mapping = {
            "BUY": TransactionType.BUY,
            "SELL": TransactionType.SELL,
            "B": TransactionType.BUY,
            "S": TransactionType.SELL,
        }
        return mapping.get(side.upper(), TransactionType.BUY)
