"""
Webull Official API connector
OAuth 2.0 authentication
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx
import uuid

from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType, TransactionType


class WebullConnector(BrokerageConnector):
    """
    Webull Official API connector
    OAuth 2.0 authentication with device ID requirement
    """
    
    QUOTE_API_BASE = "https://quoteapi.webull.com/api"
    TRADE_API_BASE = "https://tradeapi.webull.com/api"
    AUTH_URL = "https://www.webull.com/oauth2/authorize"
    TOKEN_URL = "https://quoteapi.webull.com/api/oauth2/token"
    REVOKE_URL = "https://quoteapi.webull.com/api/oauth2/revoke"
    
    def __init__(
        self,
        connection,
        client_id: str,
        client_secret: str,
        device_id: Optional[str] = None
    ):
        """
        Initialize Webull connector
        
        Args:
            connection: BrokerageConnection instance
            client_id: Webull client ID
            client_secret: Webull client secret
            device_id: Device ID (generated if not provided)
        """
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
        self.device_id = device_id or self._generate_device_id()
    
    def _generate_device_id(self) -> str:
        """Generate a unique device ID"""
        return str(uuid.uuid4())
    
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """
        Authenticate and obtain access tokens
        
        Args:
            authorization_code: OAuth authorization code
            
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
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "device-id": self.device_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Get account list
            accounts = await self._get_account_list(data["access_token"])
            primary_account = accounts[0] if accounts else {}
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600)),
                "account_id": str(primary_account.get("secAccountId", "primary")),
                "account_name": primary_account.get("accountType", "Webull Account"),
            }
    
    async def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh access token
        
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
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "device-id": self.device_id,
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
        accounts = await self._get_account_list(self.connection.access_token)
        account = next(
            (acc for acc in accounts if str(acc["secAccountId"]) == self.connection.account_id),
            accounts[0] if accounts else {}
        )
        
        # Get detailed account info
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.TRADE_API_BASE}/account/getAccountInfo",
                headers={
                    "Authorization": f"Bearer {self.connection.access_token}",
                    "device-id": self.device_id,
                },
                params={"secAccountId": self.connection.account_id},
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "account_id": self.connection.account_id,
            "account_name": data.get("accountType", "Webull Account"),
            "account_type": account.get("accountType", "CASH"),
        }
    
    async def get_positions(self) -> List[Position]:
        """
        Get current positions
        
        Returns:
            List of Position objects (excluding paper trading)
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.TRADE_API_BASE}/account/positions",
                headers={
                    "Authorization": f"Bearer {self.connection.access_token}",
                    "device-id": self.device_id,
                },
                params={"secAccountId": self.connection.account_id},
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos in data.get("positions", []):
                # Skip paper trading positions
                if pos.get("isPaper", False):
                    continue
                
                quantity = self._decimal(pos.get("position", 0))
                cost_per_share = self._decimal(pos.get("costPrice", 0))
                current_price = self._decimal(pos.get("marketValue", 0)) / quantity if quantity else Decimal("0")
                market_value = self._decimal(pos.get("marketValue", 0))
                cost_basis = quantity * cost_per_share
                
                unrealized_pl = self._decimal(pos.get("unrealizedProfitLoss", 0))
                unrealized_pl_pct = self._decimal(pos.get("unrealizedProfitLossRate", 0)) * 100
                
                position = Position(
                    connection_id=self.connection.id,
                    symbol=pos.get("ticker", {}).get("symbol", "UNKNOWN"),
                    position_type=self._map_position_type(pos.get("assetType", "stock")),
                    quantity=quantity,
                    average_price=cost_per_share,
                    cost_basis=cost_basis,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_pct,
                )
                
                # Add option-specific fields if applicable
                if pos.get("assetType") == "option":
                    option_data = pos.get("optionData", {})
                    position.strike_price = self._decimal(option_data.get("strikePrice"))
                    position.option_type = option_data.get("direction")  # CALL or PUT
                    if option_data.get("expireDate"):
                        position.expiration_date = datetime.fromtimestamp(
                            option_data["expireDate"] / 1000  # Convert milliseconds to seconds
                        )
                
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance information
        
        Returns:
            Dict with balance details
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.TRADE_API_BASE}/account/getAccountInfo",
                headers={
                    "Authorization": f"Bearer {self.connection.access_token}",
                    "device-id": self.device_id,
                },
                params={"secAccountId": self.connection.account_id},
            )
            response.raise_for_status()
            data = response.json()
            
            account_mem_data = data.get("accountMembers", [{}])[0]
            
            return {
                "cash": float(account_mem_data.get("cashBalance", 0)),
                "equity": float(account_mem_data.get("netLiquidation", 0)),
                "buying_power": float(account_mem_data.get("buyingPower", 0)),
                "margin_balance": float(account_mem_data.get("unsettledCash", 0)),
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
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.TRADE_API_BASE}/order/listOrders",
                headers={
                    "Authorization": f"Bearer {self.connection.access_token}",
                    "device-id": self.device_id,
                },
                params={
                    "secAccountId": self.connection.account_id,
                    "startTime": int(start_date.timestamp() * 1000),
                    "endTime": int(end_date.timestamp() * 1000),
                    "status": "Filled",  # Only filled orders
                },
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for order in data.get("orders", []):
                # Skip if not filled
                if order.get("status") != "Filled":
                    continue
                
                transaction = Transaction(
                    connection_id=self.connection.id,
                    transaction_type=self._map_transaction_type(order.get("action", "")),
                    symbol=order.get("ticker", {}).get("symbol"),
                    quantity=self._decimal(order.get("filledQuantity", 0)),
                    price=self._decimal(order.get("avgFilledPrice", 0)),
                    amount=self._decimal(order.get("filledValue", 0)),
                    fees=self._decimal(order.get("fees", 0)),
                    transaction_date=datetime.fromtimestamp(order["createTime"] / 1000),
                    description=f"{order.get('action')} {order.get('ticker', {}).get('symbol')}",
                )
                transactions.append(transaction)
            
            return transactions
    
    async def disconnect(self):
        """
        Revoke access token
        """
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.REVOKE_URL,
                    data={"token": self.connection.access_token},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "device-id": self.device_id,
                    },
                )
            self.logger.info(f"Successfully revoked Webull token for connection {self.connection.id}")
        except Exception as e:
            self.logger.warning(f"Failed to revoke Webull token: {e}")
    
    async def _get_account_list(self, access_token: str) -> List[Dict[str, Any]]:
        """Get list of accounts"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.TRADE_API_BASE}/account/getSecAccountList",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "device-id": self.device_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            # Filter out paper trading accounts
            return [acc for acc in data.get("accounts", []) if not acc.get("isPaper", False)]
    
    def _map_position_type(self, asset_type: str) -> PositionType:
        """Map Webull asset type to PositionType"""
        mapping = {
            "stock": PositionType.STOCK,
            "option": PositionType.OPTION,
            "etf": PositionType.ETF,
        }
        return mapping.get(asset_type.lower(), PositionType.STOCK)
    
    def _map_transaction_type(self, action: str) -> TransactionType:
        """Map Webull action to TransactionType"""
        mapping = {
            "BUY": TransactionType.BUY,
            "SELL": TransactionType.SELL,
            "BUY_OPEN": TransactionType.BUY_TO_OPEN,
            "SELL_OPEN": TransactionType.SELL_TO_OPEN,
            "BUY_CLOSE": TransactionType.BUY_TO_CLOSE,
            "SELL_CLOSE": TransactionType.SELL_TO_CLOSE,
        }
        return mapping.get(action.upper(), TransactionType.BUY)
