"""Aggregates institutional order flow data."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from ..models import OptionsTrade, OrderType, TradeType


class OrderFlowAggregator:
    """Aggregates and analyzes institutional order flow."""
    
    def __init__(
        self,
        institutional_threshold: Decimal = Decimal('250000'),
        aggregation_window_minutes: int = 60,
    ):
        """
        Initialize order flow aggregator.
        
        Args:
            institutional_threshold: Min premium to consider institutional
            aggregation_window_minutes: Time window for aggregation
        """
        self.institutional_threshold = institutional_threshold
        self.aggregation_window = timedelta(minutes=aggregation_window_minutes)
        
        # Store trades
        self._all_trades: List[OptionsTrade] = []
        self._institutional_trades: List[OptionsTrade] = []
        
    def add_trade(self, trade: OptionsTrade) -> None:
        """Add trade to aggregator."""
        self._all_trades.append(trade)
        
        # Track institutional trades
        if trade.notional_value >= self.institutional_threshold:
            self._institutional_trades.append(trade)
        
        # Clean old data
        self._clean_old_trades()
    
    def _clean_old_trades(self) -> None:
        """Remove trades outside aggregation window."""
        cutoff = datetime.now() - self.aggregation_window
        
        self._all_trades = [
            t for t in self._all_trades
            if t.timestamp >= cutoff
        ]
        
        self._institutional_trades = [
            t for t in self._institutional_trades
            if t.timestamp >= cutoff
        ]
    
    def get_flow_by_symbol(
        self,
        symbol: str,
        lookback_minutes: Optional[int] = None,
    ) -> Dict:
        """
        Get aggregated flow data for symbol.
        
        Args:
            symbol: Underlying symbol
            lookback_minutes: Lookback period (None = use aggregation window)
            
        Returns:
            Dictionary with flow statistics
        """
        if lookback_minutes:
            cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        else:
            cutoff = datetime.now() - self.aggregation_window
        
        trades = [
            t for t in self._all_trades
            if t.underlying_symbol == symbol and t.timestamp >= cutoff
        ]
        
        if not trades:
            return self._empty_flow_data(symbol)
        
        # Aggregate by type
        call_trades = [t for t in trades if t.order_type == OrderType.CALL]
        put_trades = [t for t in trades if t.order_type == OrderType.PUT]
        
        # Calculate premiums
        call_premium = sum(t.notional_value for t in call_trades)
        put_premium = sum(t.notional_value for t in put_trades)
        total_premium = call_premium + put_premium
        
        # Calculate volumes
        call_volume = sum(t.size for t in call_trades)
        put_volume = sum(t.size for t in put_trades)
        
        # Analyze by trade type
        sweep_trades = [t for t in trades if t.trade_type == TradeType.SWEEP]
        block_trades = [t for t in trades if t.trade_type == TradeType.BLOCK]
        dark_pool_trades = [t for t in trades if t.trade_type == TradeType.DARK_POOL]
        
        # Sentiment analysis
        sentiment = self._calculate_sentiment(call_premium, put_premium)
        
        # Institutional analysis
        institutional_flow = self._analyze_institutional_flow(symbol, cutoff)
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(trades),
            'total_premium': str(total_premium),
            'total_volume': call_volume + put_volume,
            'call': {
                'trades': len(call_trades),
                'premium': str(call_premium),
                'volume': call_volume,
                'avg_premium': str(call_premium / len(call_trades)) if call_trades else '0',
            },
            'put': {
                'trades': len(put_trades),
                'premium': str(put_premium),
                'volume': put_volume,
                'avg_premium': str(put_premium / len(put_trades)) if put_trades else '0',
            },
            'call_put_ratio': {
                'premium': str(call_premium / put_premium) if put_premium > 0 else 'inf',
                'volume': str(Decimal(call_volume) / Decimal(put_volume)) if put_volume > 0 else 'inf',
            },
            'by_type': {
                'sweep': {
                    'count': len(sweep_trades),
                    'premium': str(sum(t.notional_value for t in sweep_trades)),
                },
                'block': {
                    'count': len(block_trades),
                    'premium': str(sum(t.notional_value for t in block_trades)),
                },
                'dark_pool': {
                    'count': len(dark_pool_trades),
                    'premium': str(sum(t.notional_value for t in dark_pool_trades)),
                },
            },
            'sentiment': sentiment,
            'institutional': institutional_flow,
        }
    
    def get_institutional_flow_summary(
        self,
        lookback_minutes: Optional[int] = None,
    ) -> Dict:
        """
        Get summary of institutional flow across all symbols.
        
        Args:
            lookback_minutes: Lookback period
            
        Returns:
            Dictionary with institutional flow summary
        """
        if lookback_minutes:
            cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        else:
            cutoff = datetime.now() - self.aggregation_window
        
        trades = [
            t for t in self._institutional_trades
            if t.timestamp >= cutoff
        ]
        
        if not trades:
            return {
                'total_trades': 0,
                'total_premium': '0',
                'symbols': [],
            }
        
        # Group by symbol
        by_symbol = defaultdict(list)
        for trade in trades:
            by_symbol[trade.underlying_symbol].append(trade)
        
        # Sort symbols by total premium
        symbol_summaries = []
        for symbol, symbol_trades in by_symbol.items():
            total_premium = sum(t.notional_value for t in symbol_trades)
            call_premium = sum(
                t.notional_value for t in symbol_trades
                if t.order_type == OrderType.CALL
            )
            put_premium = total_premium - call_premium
            
            symbol_summaries.append({
                'symbol': symbol,
                'trades': len(symbol_trades),
                'premium': str(total_premium),
                'call_premium': str(call_premium),
                'put_premium': str(put_premium),
                'sentiment': self._calculate_sentiment(call_premium, put_premium),
            })
        
        # Sort by premium
        symbol_summaries.sort(key=lambda x: float(x['premium']), reverse=True)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(trades),
            'total_premium': str(sum(t.notional_value for t in trades)),
            'unique_symbols': len(by_symbol),
            'symbols': symbol_summaries[:20],  # Top 20
        }
    
    def get_flow_by_strike(
        self,
        symbol: str,
        expiration: Optional[datetime] = None,
    ) -> Dict:
        """
        Get flow aggregated by strike price.
        
        Args:
            symbol: Underlying symbol
            expiration: Specific expiration (None = all)
            
        Returns:
            Dictionary with flow by strike
        """
        trades = [
            t for t in self._all_trades
            if t.underlying_symbol == symbol
        ]
        
        if expiration:
            trades = [t for t in trades if t.expiration.date() == expiration.date()]
        
        if not trades:
            return {'symbol': symbol, 'strikes': []}
        
        # Group by strike
        by_strike = defaultdict(lambda: {'calls': [], 'puts': []})
        
        for trade in trades:
            if trade.order_type == OrderType.CALL:
                by_strike[trade.strike]['calls'].append(trade)
            else:
                by_strike[trade.strike]['puts'].append(trade)
        
        # Build strike summaries
        strike_summaries = []
        for strike, strike_trades in sorted(by_strike.items()):
            call_trades = strike_trades['calls']
            put_trades = strike_trades['puts']
            
            call_volume = sum(t.size for t in call_trades)
            put_volume = sum(t.size for t in put_trades)
            
            call_premium = sum(t.notional_value for t in call_trades)
            put_premium = sum(t.notional_value for t in put_trades)
            
            strike_summaries.append({
                'strike': str(strike),
                'call_volume': call_volume,
                'put_volume': put_volume,
                'call_premium': str(call_premium),
                'put_premium': str(put_premium),
                'net_volume': call_volume - put_volume,
                'net_premium': str(call_premium - put_premium),
            })
        
        return {
            'symbol': symbol,
            'expiration': expiration.isoformat() if expiration else 'all',
            'strikes': strike_summaries,
        }
    
    def _calculate_sentiment(
        self,
        call_premium: Decimal,
        put_premium: Decimal,
    ) -> str:
        """Calculate overall sentiment from premiums."""
        if put_premium == 0:
            return "bullish"
        
        ratio = call_premium / put_premium
        
        if ratio > Decimal('2.0'):
            return "very_bullish"
        elif ratio > Decimal('1.3'):
            return "bullish"
        elif ratio > Decimal('0.7'):
            return "neutral"
        elif ratio > Decimal('0.5'):
            return "bearish"
        else:
            return "very_bearish"
    
    def _analyze_institutional_flow(
        self,
        symbol: str,
        cutoff: datetime,
    ) -> Dict:
        """Analyze institutional flow for symbol."""
        inst_trades = [
            t for t in self._institutional_trades
            if t.underlying_symbol == symbol and t.timestamp >= cutoff
        ]
        
        if not inst_trades:
            return {
                'trades': 0,
                'premium': '0',
                'sentiment': 'neutral',
            }
        
        call_premium = sum(
            t.notional_value for t in inst_trades
            if t.order_type == OrderType.CALL
        )
        put_premium = sum(
            t.notional_value for t in inst_trades
            if t.order_type == OrderType.PUT
        )
        
        return {
            'trades': len(inst_trades),
            'premium': str(call_premium + put_premium),
            'call_premium': str(call_premium),
            'put_premium': str(put_premium),
            'sentiment': self._calculate_sentiment(call_premium, put_premium),
            'largest_trade': str(max(t.notional_value for t in inst_trades)),
        }
    
    def _empty_flow_data(self, symbol: str) -> Dict:
        """Return empty flow data structure."""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'total_trades': 0,
            'total_premium': '0',
            'total_volume': 0,
            'call': {
                'trades': 0,
                'premium': '0',
                'volume': 0,
                'avg_premium': '0',
            },
            'put': {
                'trades': 0,
                'premium': '0',
                'volume': 0,
                'avg_premium': '0',
            },
            'sentiment': 'neutral',
        }
