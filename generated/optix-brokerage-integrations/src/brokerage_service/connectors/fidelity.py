"""
Fidelity brokerage connector
OAuth 2.0 authentication flow
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx

from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType, TransactionType


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
    
    def __init__(self, connection, client_id: str, client_secret: str):
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: OAuth authorization code from callback
            
        Returns:
            Dict with access_token, refresh_token, expires_at, account_id
        """
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
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Get account info to get primary account ID
            accounts_response = await client.get(
                f"{self.BASE_URL}/accounts",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
            accounts_response.raise_for_status()
            accounts = accounts_response.json()
            
            primary_account = accounts.get("accounts", [{}])[0]
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
                "account_id": primary_account.get("accountId", "primary"),
                "account_name": primary_account.get("accountName", "Fidelity Account"),
            }
    
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh expired access token
        
        Returns:
            Dict with new access_token and expires_at
        """
        if not self.connection.refresh_token:
            raise ValueError("No refresh token available")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.connection.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", self.connection.refresh_token),
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"]),
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        
        Returns:
            Dict with account_id, account_name, account_type
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "account_id": data.get("accountId"),
                "account_name": data.get("accountName", "Fidelity Account"),
                "account_type": data.get("accountType", "CASH"),
            }
    
    async def get_positions(self) -> List[Position]:
        """
        Get current positions
        
        Returns:
            List of Position objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}/positions",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos in data.get("positions", []):
                # Map Fidelity fields to OPTIX Position
                quantity = self._decimal(pos.get("quantity", 0))
                cost_basis = self._decimal(pos.get("costBasis", 0))
                market_value = self._decimal(pos.get("marketValue", 0))
                unrealized_pl = self._decimal(pos.get("unrealizedGainLoss", 0))
                
                # Calculate average price
                avg_price = cost_basis / quantity if quantity else Decimal("0")
                
                # Calculate unrealized P&L percentage
                unrealized_pl_pct = (unrealized_pl / cost_basis * 100) if cost_basis else Decimal("0")
                
                # Current price
                current_price = market_value / quantity if quantity else Decimal("0")
                
                position = Position(
                    connection_id=self.connection.id,
                    symbol=pos.get("symbol", ""),
                    position_type=self._map_position_type(pos.get("assetType", "EQUITY")),
                    quantity=quantity,
                    average_price=avg_price,
                    cost_basis=cost_basis,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_pct,
                )
                
                # Add option-specific fields if applicable
                if pos.get("assetType") == "OPTION":
                    position.strike_price = self._decimal(pos.get("strikePrice"))
                    position.option_type = pos.get("optionType")  # CALL or PUT
                    if pos.get("expirationDate"):
                        position.expiration_date = datetime.fromisoformat(pos["expirationDate"])
                
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        
        Returns:
            Dict with cash, equity, buying_power, margin_balance
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}/balances",
                headers={"Authorization": f"Bearer {self.connection.access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            balances = data.get("balances", {})
            return {
                "cash": float(balances.get("cashBalance", 0)),
                "equity": float(balances.get("accountValue", 0)),
                "buying_power": float(balances.get("buyingPower", 0)),
                "margin_balance": float(balances.get("marginBalance", 0)),
            }
    
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """
        Get transaction history
        
        Args:
            start_date: Start date for query (default: 90 days ago)
            end_date: End date for query (default: now)
            
        Returns:
            List of Transaction objects
        """
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
                    transaction_type=self._map_transaction_type(txn.get("transactionType", "")),
                    symbol=txn.get("symbol"),
                    quantity=self._decimal(txn.get("quantity", 0)),
                    price=self._decimal(txn.get("price", 0)),
                    amount=self._decimal(txn.get("amount", 0)),
                    fees=self._decimal(txn.get("commission", 0)),
                    transaction_date=datetime.fromisoformat(txn["transactionDate"]),
                    description=txn.get("description"),
                )
                transactions.append(transaction)
            
            return transactions
    
    async def disconnect(self):
        """
        Revoke access token with Fidelity
        """
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.REVOKE_URL,
                    data={"token": self.connection.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            self.logger.info(f"Successfully revoked Fidelity token for connection {self.connection.id}")
        except Exception as e:
            self.logger.warning(f"Failed to revoke Fidelity token: {e}")
            # Don't raise - we still want to delete local connection
    
    def _map_position_type(self, asset_type: str) -> PositionType:
        """Map Fidelity asset type to PositionType"""
        mapping = {
            "EQUITY": PositionType.STOCK,
            "OPTION": PositionType.OPTION,
            "ETF": PositionType.ETF,
            "MUTUAL_FUND": PositionType.MUTUAL_FUND,
        }
        return mapping.get(asset_type.upper(), PositionType.STOCK)
    
    def _map_transaction_type(self, txn_type: str) -> TransactionType:
        """Map Fidelity transaction type to TransactionType"""
        mapping = {
            "BUY": TransactionType.BUY,
            "SELL": TransactionType.SELL,
            "BUY_TO_OPEN": TransactionType.BUY_TO_OPEN,
            "SELL_TO_OPEN": TransactionType.SELL_TO_OPEN,
            "BUY_TO_CLOSE": TransactionType.BUY_TO_CLOSE,
            "SELL_TO_CLOSE": TransactionType.SELL_TO_CLOSE,
            "DIVIDEND": TransactionType.DIVIDEND,
            "INTEREST": TransactionType.INTEREST,
            "DEPOSIT": TransactionType.DEPOSIT,
            "WITHDRAWAL": TransactionType.WITHDRAWAL,
        }
        return mapping.get(txn_type.upper(), TransactionType.BUY)
