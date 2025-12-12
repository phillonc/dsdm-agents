"""
Schwab/TD Ameritrade Connector
Implements Schwab OAuth 2.0 API integration
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import httpx
from .base import BrokerageConnector
from ..models import Position, Transaction, PositionType


class SchwabConnector(BrokerageConnector):
    """
    Schwab API connector (formerly TD Ameritrade)
    Official OAuth 2.0 API
    """
    
    BASE_URL = "https://api.schwabapi.com/v1"
    AUTH_URL = "https://api.schwabapi.com/oauth2/authorize"
    TOKEN_URL = "https://api.schwabapi.com/oauth2/token"
    
    def __init__(self, connection, client_id: str, client_secret: str):
        super().__init__(connection)
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """Complete OAuth flow with authorization code"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": "https://optix.app/oauth/callback/schwab"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"])
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
                    "client_secret": self.client_secret
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "access_token": data["access_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data["expires_in"])
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}",
                headers={"Authorization": f"Bearer {self.connection.access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_positions(self) -> List[Position]:
        """Fetch current positions"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{self.connection.account_id}/positions",
                headers={"Authorization": f"Bearer {self.connection.access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for pos_data in data.get("positions", []):
                instrument = pos_data["instrument"]
                
                # Determine position type
                if instrument["assetType"] == "EQUITY":
                    position_type = PositionType.STOCK
                elif instrument["assetType"] == "OPTION":
                    position_type = PositionType.OPTION
                else:
                    position_type = PositionType.ETF
                
                # Calculate P&L
                quantity = Decimal(str(pos_data["longQuantity"]))
                avg_price = Decimal(str(pos_data["averagePrice"]))
                current_price = Decimal(str(pos_data["marketPrice"]))
                
                cost_basis = quantity * avg_price
                market_value = quantity * current_price
                unrealized_pl = market_value - cost_basis
                unrealized_pl_percent = (unrealized_pl / cost_basis * 100) if cost_basis != 0 else Decimal("0")
                
                position = Position(
                    connection_id=self.connection.id,
                    user_id=self.connection.user_id,
                    symbol=instrument["symbol"],
                    position_type=position_type,
                    quantity=quantity,
                    average_price=avg_price,
                    cost_basis=cost_basis,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_percent=unrealized_pl_percent
                )
                
                # Add option-specific data
                if position_type == PositionType.OPTION:
                    option_details = instrument.get("optionDetails", {})
                    position.option_symbol = instrument.get("cusip")
                    position.strike = Decimal(str(option_details.get("strikePrice", 0)))
                    position.expiration_date = datetime.strptime(
                        option_details.get("expirationDate", ""), "%Y-%m-%d"
                    ).date()
                    position.option_type = option_details.get("putCall", "").lower()
                    
                    # Greeks (if available)
                    greeks = option_details.get("greeks", {})
                    position.delta = Decimal(str(greeks.get("delta", 0)))
                    position.gamma = Decimal(str(greeks.get("gamma", 0)))
                    position.theta = Decimal(str(greeks.get("theta", 0)))
                    position.vega = Decimal(str(greeks.get("vega", 0)))
                
                positions.append(position)
            
            return positions
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        account_info = await self.get_account_info()
        balances = account_info.get("currentBalances", {})
        
        return {
            "cash": float(balances.get("cashBalance", 0)),
            "equity": float(balances.get("equity", 0)),
            "buying_power": float(balances.get("buyingPower", 0)),
            "market_value": float(balances.get("marketValue", 0))
        }
    
    async def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Fetch transaction history"""
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
                    "endDate": end_date.isoformat()
                }
            )
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn_data in data.get("transactions", []):
                transaction = Transaction(
                    connection_id=self.connection.id,
                    user_id=self.connection.user_id,
                    symbol=txn_data["instrument"]["symbol"],
                    transaction_type=txn_data["type"].lower(),
                    quantity=Decimal(str(abs(txn_data.get("quantity", 0)))),
                    price=Decimal(str(txn_data.get("price", 0))),
                    amount=Decimal(str(txn_data.get("netAmount", 0))),
                    fees=Decimal(str(txn_data.get("fees", 0))),
                    transaction_date=datetime.fromisoformat(txn_data["transactionDate"])
                )
                transactions.append(transaction)
            
            return transactions
