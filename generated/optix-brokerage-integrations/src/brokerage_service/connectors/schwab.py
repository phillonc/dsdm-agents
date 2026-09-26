"""
Schwab/TD Ameritrade connector (reference implementation - already complete)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType, TransactionType


class SchwabConnector(BrokerageConnector):
    """
    Schwab/TD Ameritrade OAuth 2.0 connector
    Reference implementation - already complete
    """
    
    BASE_URL = "https://api.schwabapi.com/trader/v1"
    AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
    TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
    
    def __init__(self, connection, client_id: str, client_secret: str):
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.connection.account_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
                "account_id": data.get("account_id", "primary"),
                "account_name": "Schwab Account",
            }
    
    async def refresh_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
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
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "account_id": data["accountId"],
                "account_name": data.get("accountName", "Schwab Account"),
                "account_type": data.get("type", "CASH"),
            }
    
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}/positions",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos in data.get("positions", []):
                instrument = pos["instrument"]
                position = Position(
                    connection_id=self.connection.id,
                    symbol=instrument["symbol"],
                    position_type=self._map_position_type(instrument["assetType"]),
                    quantity=self._decimal(pos["longQuantity"]),
                    average_price=self._decimal(pos["averagePrice"]),
                    cost_basis=self._decimal(pos["averagePrice"]) * self._decimal(pos["longQuantity"]),
                    current_price=self._decimal(pos["marketValue"]) / self._decimal(pos["longQuantity"]),
                    market_value=self._decimal(pos["marketValue"]),
                    unrealized_pl=self._decimal(pos["unrealizedProfitLoss"]),
                    unrealized_pl_percent=self._decimal(pos["unrealizedProfitLossPercent"]),
                )
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            balances = data.get("currentBalances", {})
            return {
                "cash": float(balances.get("cashBalance", 0)),
                "equity": float(balances.get("equity", 0)),
                "buying_power": float(balances.get("buyingPower", 0)),
                "margin_balance": float(balances.get("marginBalance", 0)),
            }
    
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Get transaction history"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=90)
        if not end_date:
            end_date = datetime.utcnow()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}/transactions",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
                params={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                },
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("transactions", []):
                transaction = Transaction(
                    connection_id=self.connection.id,
                    transaction_type=self._map_transaction_type(txn["type"]),
                    symbol=txn.get("instrument", {}).get("symbol"),
                    quantity=self._decimal(txn.get("quantity", 0)),
                    price=self._decimal(txn.get("price", 0)),
                    amount=self._decimal(txn["amount"]),
                    fees=self._decimal(txn.get("fees", {}).get("commission", 0)),
                    transaction_date=datetime.fromisoformat(txn["transactionDate"]),
                    description=txn.get("description"),
                )
                transactions.append(transaction)
            
            return transactions
    
    def _map_position_type(self, asset_type: str) -> PositionType:
        """Map Schwab asset type to PositionType"""
        mapping = {
            "EQUITY": PositionType.STOCK,
            "OPTION": PositionType.OPTION,
            "ETF": PositionType.ETF,
            "MUTUAL_FUND": PositionType.MUTUAL_FUND,
        }
        return mapping.get(asset_type, PositionType.STOCK)
    
    def _map_transaction_type(self, txn_type: str) -> TransactionType:
        """Map Schwab transaction type to TransactionType"""
        mapping = {
            "BUY": TransactionType.BUY,
            "SELL": TransactionType.SELL,
            "DIVIDEND": TransactionType.DIVIDEND,
            "INTEREST": TransactionType.INTEREST,
        }
        return mapping.get(txn_type, TransactionType.BUY)
