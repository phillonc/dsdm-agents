"""
Trade Capture Module for Trading Journal AI.

This module handles automatic trade capture from linked brokerages,
syncing with VS-7 (Brokerage Integration System).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import asyncio
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import (
    Trade, TradeDirection, TradeStatus, TradeCreate,
    SetupType, MarketCondition
)

logger = logging.getLogger(__name__)


class BrokerageIntegrationClient:
    """Client for interacting with VS-7 Brokerage Integration System."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the brokerage integration client.
        
        Args:
            base_url: Base URL for VS-7 API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_trades(
        self,
        user_id: str,
        broker_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch trades from brokerage via VS-7.
        
        Args:
            user_id: User identifier
            broker_id: Broker identifier
            start_date: Optional start date for trade filter
            end_date: Optional end date for trade filter
            
        Returns:
            List of trade dictionaries
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        
        params = {
            'user_id': user_id,
            'broker_id': broker_id
        }
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        url = f"{self.base_url}/api/v1/trades"
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('trades', [])
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching trades from VS-7: {e}")
            raise
    
    async def get_account_positions(
        self,
        user_id: str,
        broker_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch current positions from brokerage.
        
        Args:
            user_id: User identifier
            broker_id: Broker identifier
            
        Returns:
            List of position dictionaries
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        
        url = f"{self.base_url}/api/v1/positions"
        params = {
            'user_id': user_id,
            'broker_id': broker_id
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('positions', [])
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching positions from VS-7: {e}")
            raise


class TradeCapture:
    """
    Trade capture service for automatic trade import and synchronization.
    """
    
    def __init__(
        self,
        db_session: Session,
        vs7_client: BrokerageIntegrationClient
    ):
        """
        Initialize the trade capture service.
        
        Args:
            db_session: SQLAlchemy database session
            vs7_client: VS-7 brokerage integration client
        """
        self.db = db_session
        self.vs7_client = vs7_client
    
    def _normalize_broker_trade(self, broker_trade: Dict[str, Any]) -> TradeCreate:
        """
        Normalize broker trade data to internal format.
        
        Args:
            broker_trade: Raw trade data from broker
            
        Returns:
            TradeCreate schema object
        """
        # Determine direction
        direction = TradeDirection.LONG if broker_trade.get('side', '').upper() in ['BUY', 'LONG'] else TradeDirection.SHORT
        
        # Parse dates
        entry_date = self._parse_datetime(broker_trade.get('execution_time') or broker_trade.get('entry_date'))
        
        # Build trade creation schema
        trade_data = {
            'user_id': broker_trade.get('user_id'),
            'broker_id': broker_trade.get('broker_id'),
            'broker_trade_id': broker_trade.get('trade_id') or broker_trade.get('order_id'),
            'symbol': broker_trade.get('symbol'),
            'direction': direction,
            'entry_date': entry_date,
            'entry_price': float(broker_trade.get('price') or broker_trade.get('entry_price', 0)),
            'quantity': float(broker_trade.get('quantity') or broker_trade.get('shares', 0)),
            'entry_commission': float(broker_trade.get('commission', 0)),
            'metadata': {
                'broker_data': broker_trade,
                'captured_at': datetime.utcnow().isoformat()
            }
        }
        
        # Add optional fields if present
        if 'stop_loss' in broker_trade:
            trade_data['stop_loss'] = float(broker_trade['stop_loss'])
        if 'take_profit' in broker_trade:
            trade_data['take_profit'] = float(broker_trade['take_profit'])
        
        return TradeCreate(**trade_data)
    
    def _parse_datetime(self, date_value: Any) -> datetime:
        """
        Parse various datetime formats.
        
        Args:
            date_value: Date value to parse
            
        Returns:
            Parsed datetime object
        """
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Default to current time if parsing fails
        return datetime.utcnow()
    
    def _calculate_pnl(self, trade: Trade) -> None:
        """
        Calculate P&L for a closed trade.
        
        Args:
            trade: Trade object to calculate P&L for
        """
        if trade.status != TradeStatus.CLOSED or not trade.exit_price:
            return
        
        # Calculate gross P&L
        if trade.direction == TradeDirection.LONG:
            price_diff = trade.exit_price - trade.entry_price
        else:  # SHORT
            price_diff = trade.entry_price - trade.exit_price
        
        trade.gross_pnl = price_diff * trade.quantity
        
        # Calculate net P&L (including commissions)
        total_commission = trade.entry_commission + (trade.exit_commission or 0)
        trade.net_pnl = trade.gross_pnl - total_commission
        
        # Calculate P&L percentage
        cost_basis = trade.entry_price * trade.quantity
        if cost_basis > 0:
            trade.pnl_percent = (trade.net_pnl / cost_basis) * 100
        
        # Calculate risk/reward ratio if stop loss was set
        if trade.stop_loss:
            if trade.direction == TradeDirection.LONG:
                risk = trade.entry_price - trade.stop_loss
            else:
                risk = trade.stop_loss - trade.entry_price
            
            if risk > 0:
                reward = abs(price_diff)
                trade.risk_reward_ratio = reward / risk
    
    def create_trade(self, trade_data: TradeCreate) -> Trade:
        """
        Create a new trade in the database.
        
        Args:
            trade_data: Trade creation data
            
        Returns:
            Created trade object
        """
        trade = Trade(
            user_id=trade_data.user_id,
            broker_id=trade_data.broker_id,
            broker_trade_id=trade_data.broker_trade_id,
            symbol=trade_data.symbol,
            direction=trade_data.direction,
            status=TradeStatus.OPEN,
            entry_date=trade_data.entry_date,
            entry_price=trade_data.entry_price,
            quantity=trade_data.quantity,
            entry_commission=trade_data.entry_commission,
            stop_loss=trade_data.stop_loss,
            take_profit=trade_data.take_profit,
            setup_type=trade_data.setup_type,
            market_condition=trade_data.market_condition,
            sentiment=trade_data.sentiment,
            metadata=trade_data.metadata
        )
        
        try:
            self.db.add(trade)
            self.db.commit()
            self.db.refresh(trade)
            logger.info(f"Created trade {trade.id} for {trade.symbol}")
            return trade
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create trade: {e}")
            raise
    
    def update_trade_exit(
        self,
        trade_id: int,
        exit_price: float,
        exit_date: datetime,
        exit_commission: float = 0.0
    ) -> Trade:
        """
        Update trade with exit information.
        
        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_date: Exit date/time
            exit_commission: Exit commission
            
        Returns:
            Updated trade object
        """
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        trade.exit_price = exit_price
        trade.exit_date = exit_date
        trade.exit_commission = exit_commission
        trade.status = TradeStatus.CLOSED
        
        # Calculate P&L
        self._calculate_pnl(trade)
        
        self.db.commit()
        self.db.refresh(trade)
        logger.info(f"Updated trade {trade.id} with exit price {exit_price}")
        return trade
    
    async def sync_trades(
        self,
        user_id: str,
        broker_id: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Synchronize trades from brokerage.
        
        Args:
            user_id: User identifier
            broker_id: Broker identifier
            lookback_days: Number of days to look back
            
        Returns:
            Synchronization summary
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        try:
            # Fetch trades from broker
            broker_trades = await self.vs7_client.get_trades(
                user_id=user_id,
                broker_id=broker_id,
                start_date=start_date
            )
            
            stats = {
                'total_fetched': len(broker_trades),
                'new_trades': 0,
                'updated_trades': 0,
                'errors': 0
            }
            
            for broker_trade in broker_trades:
                try:
                    broker_trade_id = broker_trade.get('trade_id') or broker_trade.get('order_id')
                    
                    # Check if trade already exists
                    existing_trade = self.db.query(Trade).filter(
                        Trade.broker_trade_id == broker_trade_id
                    ).first()
                    
                    if existing_trade:
                        # Update if status changed or exit info available
                        if broker_trade.get('status') == 'CLOSED' and existing_trade.status != TradeStatus.CLOSED:
                            self.update_trade_exit(
                                trade_id=existing_trade.id,
                                exit_price=float(broker_trade.get('exit_price', 0)),
                                exit_date=self._parse_datetime(broker_trade.get('exit_date')),
                                exit_commission=float(broker_trade.get('exit_commission', 0))
                            )
                            stats['updated_trades'] += 1
                    else:
                        # Create new trade
                        trade_data = self._normalize_broker_trade(broker_trade)
                        self.create_trade(trade_data)
                        stats['new_trades'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing trade {broker_trade.get('trade_id')}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Trade sync completed for user {user_id}: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Trade sync failed for user {user_id}: {e}")
            raise
    
    async def sync_open_positions(
        self,
        user_id: str,
        broker_id: str
    ) -> Dict[str, Any]:
        """
        Synchronize open positions from brokerage.
        
        Args:
            user_id: User identifier
            broker_id: Broker identifier
            
        Returns:
            Synchronization summary
        """
        try:
            positions = await self.vs7_client.get_account_positions(
                user_id=user_id,
                broker_id=broker_id
            )
            
            stats = {
                'total_positions': len(positions),
                'synced': 0,
                'errors': 0
            }
            
            for position in positions:
                try:
                    # Check if we have an open trade for this position
                    symbol = position.get('symbol')
                    existing_trade = self.db.query(Trade).filter(
                        Trade.user_id == user_id,
                        Trade.broker_id == broker_id,
                        Trade.symbol == symbol,
                        Trade.status == TradeStatus.OPEN
                    ).first()
                    
                    if not existing_trade:
                        # Create trade from position
                        trade_data = self._normalize_broker_trade({
                            'user_id': user_id,
                            'broker_id': broker_id,
                            'trade_id': f"{broker_id}_{symbol}_{int(datetime.utcnow().timestamp())}",
                            'symbol': symbol,
                            'side': position.get('side', 'BUY'),
                            'entry_price': position.get('average_price'),
                            'quantity': position.get('quantity'),
                            'entry_date': position.get('opened_at', datetime.utcnow().isoformat()),
                            'commission': 0.0
                        })
                        self.create_trade(trade_data)
                        stats['synced'] += 1
                
                except Exception as e:
                    logger.error(f"Error syncing position {position.get('symbol')}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Position sync completed for user {user_id}: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Position sync failed for user {user_id}: {e}")
            raise
    
    def get_user_trades(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TradeStatus] = None,
        symbol: Optional[str] = None
    ) -> List[Trade]:
        """
        Get trades for a user with optional filters.
        
        Args:
            user_id: User identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            status: Optional status filter
            symbol: Optional symbol filter
            
        Returns:
            List of trades
        """
        query = self.db.query(Trade).filter(Trade.user_id == user_id)
        
        if start_date:
            query = query.filter(Trade.entry_date >= start_date)
        if end_date:
            query = query.filter(Trade.entry_date <= end_date)
        if status:
            query = query.filter(Trade.status == status)
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        
        return query.order_by(Trade.entry_date.desc()).all()
