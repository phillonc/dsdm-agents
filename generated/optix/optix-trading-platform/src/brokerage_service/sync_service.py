"""
Portfolio Sync Service
Background service for syncing brokerage data
"""
from typing import List, Dict, Any
import uuid
from decimal import Decimal
from datetime import datetime
from .models import BrokerageConnection, Portfolio, Position
from .repository import BrokerageRepository
from .connectors.base import BrokerageConnector
from .connectors.schwab import SchwabConnector


class PortfolioSyncService:
    """
    Service for syncing portfolio data from brokerages
    Runs background sync tasks
    """
    
    def __init__(self):
        self.repo = BrokerageRepository()
    
    def get_connector(self, connection: BrokerageConnection) -> BrokerageConnector:
        """Get appropriate connector for brokerage"""
        from .models import BrokerageProvider
        
        # In production, load credentials from secure config
        if connection.provider == BrokerageProvider.SCHWAB:
            return SchwabConnector(
                connection,
                client_id="YOUR_CLIENT_ID",
                client_secret="YOUR_CLIENT_SECRET"
            )
        elif connection.provider == BrokerageProvider.TD_AMERITRADE:
            return SchwabConnector(  # TD uses same API as Schwab now
                connection,
                client_id="YOUR_CLIENT_ID",
                client_secret="YOUR_CLIENT_SECRET"
            )
        else:
            raise ValueError(f"Unsupported provider: {connection.provider}")
    
    async def sync_account(self, connection_id: uuid.UUID):
        """
        Sync single brokerage account
        
        **Performance**: Completes within 30 seconds (AC)
        """
        connection = self.repo.get_connection(connection_id)
        if not connection:
            raise ValueError("Connection not found")
        
        try:
            connector = self.get_connector(connection)
            
            # Test connection
            if not await connector.test_connection():
                # Try to refresh token
                token_data = await connector.refresh_token()
                self.repo.update_connection(connection_id, {
                    "access_token": token_data["access_token"],
                    "token_expires_at": token_data["expires_at"]
                })
            
            # Fetch positions
            positions = await connector.get_positions()
            self.repo.save_positions(positions)
            
            # Fetch recent transactions
            transactions = await connector.get_transactions()
            self.repo.save_transactions(transactions)
            
            # Update last sync time
            self.repo.update_connection(connection_id, {
                "last_sync_at": datetime.utcnow(),
                "sync_error": None
            })
            
        except Exception as e:
            # Log error
            self.repo.update_connection(connection_id, {
                "sync_error": str(e)
            })
            raise
    
    async def sync_all_accounts(self, user_id: uuid.UUID):
        """Sync all connected accounts for a user"""
        connections = self.repo.get_user_connections(user_id)
        
        for connection in connections:
            try:
                await self.sync_account(connection.id)
            except Exception as e:
                print(f"Sync failed for connection {connection.id}: {e}")
                # Continue with other accounts
    
    async def get_unified_portfolio(self, user_id: uuid.UUID) -> Portfolio:
        """
        Generate unified portfolio view
        
        - Aggregates positions from all accounts
        - Calculates total values and P&L
        - Sums Greeks across options positions
        """
        # Get all connections and positions
        connections = self.repo.get_user_connections(user_id)
        positions = self.repo.get_user_positions(user_id)
        
        # Calculate totals
        total_value = Decimal("0")
        total_stocks_value = Decimal("0")
        total_options_value = Decimal("0")
        total_unrealized_pl = Decimal("0")
        
        # Portfolio Greeks
        total_delta = Decimal("0")
        total_gamma = Decimal("0")
        total_theta = Decimal("0")
        total_vega = Decimal("0")
        
        for position in positions:
            total_value += position.market_value
            total_unrealized_pl += position.unrealized_pl
            
            if position.position_type.value == "stock":
                total_stocks_value += position.market_value
            elif position.position_type.value == "option":
                total_options_value += position.market_value
                
                # Sum Greeks
                if position.delta:
                    total_delta += position.delta * position.quantity
                if position.gamma:
                    total_gamma += position.gamma * position.quantity
                if position.theta:
                    total_theta += position.theta * position.quantity
                if position.vega:
                    total_vega += position.vega * position.quantity
        
        # Calculate percentages
        total_unrealized_pl_percent = (
            (total_unrealized_pl / (total_value - total_unrealized_pl) * 100)
            if total_value > total_unrealized_pl else Decimal("0")
        )
        
        portfolio = Portfolio(
            user_id=user_id,
            total_value=total_value,
            total_cash=Decimal("0"),  # TODO: Calculate from account balances
            total_stocks_value=total_stocks_value,
            total_options_value=total_options_value,
            total_unrealized_pl=total_unrealized_pl,
            total_unrealized_pl_percent=total_unrealized_pl_percent,
            total_realized_pl=Decimal("0"),  # TODO: Calculate from transactions
            day_pl=Decimal("0"),  # TODO: Calculate day change
            day_pl_percent=Decimal("0"),
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            positions=positions,
            connections=connections
        )
        
        return portfolio
    
    async def calculate_performance(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        portfolio = await self.get_unified_portfolio(user_id)
        transactions = self.repo.get_user_transactions(user_id, limit=500)
        
        # Calculate win rate
        closed_trades = [t for t in transactions if t.transaction_type in ["sell", "buy_to_close"]]
        winning_trades = [t for t in closed_trades if t.amount > 0]
        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        return {
            "total_value": float(portfolio.total_value),
            "unrealized_pl": float(portfolio.total_unrealized_pl),
            "unrealized_pl_percent": float(portfolio.total_unrealized_pl_percent),
            "day_pl": float(portfolio.day_pl),
            "day_pl_percent": float(portfolio.day_pl_percent),
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "portfolio_greeks": {
                "delta": float(portfolio.total_delta),
                "gamma": float(portfolio.total_gamma),
                "theta": float(portfolio.total_theta),
                "vega": float(portfolio.total_vega)
            }
        }
