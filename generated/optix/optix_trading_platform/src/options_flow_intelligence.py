"""Main Options Flow Intelligence Engine for OPTIX Trading Platform."""
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal

from .models import OptionsTrade, FlowPattern, MarketMakerPosition, UnusualActivityAlert
from .detectors import SweepDetector, BlockDetector, DarkPoolDetector, FlowAnalyzer
from .analyzers import MarketMakerAnalyzer, OrderFlowAggregator
from .alerts import AlertManager, AlertDispatcher


class OptionsFlowIntelligence:
    """
    Main engine for detecting and analyzing unusual options activity.
    
    Features:
    - Detect sweeps, blocks, and dark pool prints
    - Identify smart money flow patterns
    - Real-time unusual activity alerts
    - Aggregate institutional order flow
    - Calculate market maker positioning
    """
    
    def __init__(
        self,
        enable_alerts: bool = True,
        alert_dispatch_channels: Optional[List[str]] = None,
    ):
        """
        Initialize Options Flow Intelligence engine.
        
        Args:
            enable_alerts: Enable real-time alerting
            alert_dispatch_channels: Channels for alert dispatch
        """
        # Detectors
        self.sweep_detector = SweepDetector()
        self.block_detector = BlockDetector()
        self.dark_pool_detector = DarkPoolDetector()
        self.flow_analyzer = FlowAnalyzer()
        
        # Analyzers
        self.mm_analyzer = MarketMakerAnalyzer()
        self.flow_aggregator = OrderFlowAggregator()
        
        # Alert system
        self.enable_alerts = enable_alerts
        self.alert_manager = AlertManager()
        self.alert_dispatcher = AlertDispatcher()
        self.alert_dispatch_channels = alert_dispatch_channels or ['console']
        
        # Statistics
        self._stats = {
            'trades_processed': 0,
            'sweeps_detected': 0,
            'blocks_detected': 0,
            'dark_pools_detected': 0,
            'patterns_detected': 0,
            'alerts_created': 0,
        }
    
    def process_trade(
        self,
        trade: OptionsTrade,
        market_timestamp: Optional[datetime] = None,
    ) -> Dict:
        """
        Process incoming options trade through all detectors.
        
        Args:
            trade: Options trade to process
            market_timestamp: Current market time
            
        Returns:
            Dictionary with detection results
        """
        self._stats['trades_processed'] += 1
        
        results = {
            'trade_id': trade.trade_id,
            'symbol': trade.underlying_symbol,
            'timestamp': trade.timestamp.isoformat(),
            'detections': [],
            'patterns': [],
            'alerts': [],
        }
        
        # 1. Detect sweep activity
        sweep_trades = self.sweep_detector.detect_sweep(trade)
        if sweep_trades:
            confidence = self.sweep_detector.calculate_sweep_score(sweep_trades)
            results['detections'].append({
                'type': 'sweep',
                'trades': len(sweep_trades),
                'confidence': confidence,
            })
            self._stats['sweeps_detected'] += 1
            
            # Create alert
            if self.enable_alerts and confidence >= 0.7:
                alert = self.alert_manager.create_sweep_alert(sweep_trades, confidence)
                self.alert_dispatcher.dispatch(alert, self.alert_dispatch_channels)
                results['alerts'].append(alert.alert_id)
                self._stats['alerts_created'] += 1
        
        # 2. Detect block trades
        recent_avg = self.block_detector.get_average_size(trade.underlying_symbol)
        is_block = self.block_detector.detect_block(trade, recent_avg)
        if is_block:
            confidence = self.block_detector.calculate_block_score(trade, recent_avg)
            results['detections'].append({
                'type': 'block',
                'confidence': confidence,
            })
            self._stats['blocks_detected'] += 1
            
            # Create alert
            if self.enable_alerts and confidence >= 0.7:
                alert = self.alert_manager.create_block_alert(trade, confidence)
                self.alert_dispatcher.dispatch(alert, self.alert_dispatch_channels)
                results['alerts'].append(alert.alert_id)
                self._stats['alerts_created'] += 1
        
        # Update volume stats
        self.block_detector.update_volume_stats(trade.underlying_symbol, trade.size)
        
        # 3. Detect dark pool prints
        is_dark_pool = self.dark_pool_detector.detect_dark_pool(trade, market_timestamp)
        if is_dark_pool:
            confidence = self.dark_pool_detector.calculate_dark_pool_score(trade, market_timestamp)
            results['detections'].append({
                'type': 'dark_pool',
                'confidence': confidence,
            })
            self._stats['dark_pools_detected'] += 1
            
            # Create alert
            if self.enable_alerts and confidence >= 0.7:
                alert = self.alert_manager.create_dark_pool_alert(trade, confidence)
                self.alert_dispatcher.dispatch(alert, self.alert_dispatch_channels)
                results['alerts'].append(alert.alert_id)
                self._stats['alerts_created'] += 1
        
        self.dark_pool_detector.add_to_history(trade)
        
        # 4. Analyze flow patterns
        patterns = self.flow_analyzer.analyze_trade(trade)
        for pattern in patterns:
            results['patterns'].append({
                'pattern_id': pattern.pattern_id,
                'type': pattern.pattern_type.value,
                'signal': pattern.signal.value,
                'confidence': pattern.confidence_score,
            })
            self._stats['patterns_detected'] += 1
            
            # Create alert for significant patterns
            if self.enable_alerts and pattern.is_significant:
                alert = self.alert_manager.create_flow_pattern_alert(pattern)
                self.alert_dispatcher.dispatch(alert, self.alert_dispatch_channels)
                results['alerts'].append(alert.alert_id)
                self._stats['alerts_created'] += 1
        
        # 5. Add to order flow aggregator
        self.flow_aggregator.add_trade(trade)
        
        return results
    
    def calculate_market_maker_position(
        self,
        symbol: str,
        lookback_minutes: int = 60,
        option_chain_data: Optional[Dict] = None,
    ) -> MarketMakerPosition:
        """
        Calculate estimated market maker positioning.
        
        Args:
            symbol: Underlying symbol
            lookback_minutes: Lookback period for analysis
            option_chain_data: Optional option chain data
            
        Returns:
            MarketMakerPosition object
        """
        # Get recent trades from flow analyzer
        flow_summary = self.flow_analyzer.get_flow_summary(symbol, lookback_minutes)
        
        # Get all trades from flow analyzer history
        trades = [
            t for t in self.flow_analyzer._trade_history
            if t.underlying_symbol == symbol
        ]
        
        position = self.mm_analyzer.calculate_position(
            symbol, trades, option_chain_data
        )
        
        # Check for gamma squeeze risk and create alert
        if self.enable_alerts and position.is_gamma_squeeze_risk:
            alert = self.alert_manager.create_gamma_squeeze_alert(position)
            self.alert_dispatcher.dispatch(alert, self.alert_dispatch_channels)
            self._stats['alerts_created'] += 1
        
        return position
    
    def get_order_flow_summary(
        self,
        symbol: str,
        lookback_minutes: Optional[int] = None,
    ) -> Dict:
        """
        Get aggregated order flow summary for symbol.
        
        Args:
            symbol: Underlying symbol
            lookback_minutes: Lookback period
            
        Returns:
            Dictionary with order flow statistics
        """
        return self.flow_aggregator.get_flow_by_symbol(symbol, lookback_minutes)
    
    def get_institutional_flow(
        self,
        lookback_minutes: Optional[int] = None,
    ) -> Dict:
        """
        Get institutional flow summary across all symbols.
        
        Args:
            lookback_minutes: Lookback period
            
        Returns:
            Dictionary with institutional flow data
        """
        return self.flow_aggregator.get_institutional_flow_summary(lookback_minutes)
    
    def get_flow_by_strike(
        self,
        symbol: str,
        expiration: Optional[datetime] = None,
    ) -> Dict:
        """
        Get order flow aggregated by strike price.
        
        Args:
            symbol: Underlying symbol
            expiration: Specific expiration
            
        Returns:
            Dictionary with flow by strike
        """
        return self.flow_aggregator.get_flow_by_strike(symbol, expiration)
    
    def get_active_alerts(
        self,
        symbol: Optional[str] = None,
        min_severity: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get active alerts.
        
        Args:
            symbol: Filter by symbol
            min_severity: Minimum severity level
            
        Returns:
            List of active alerts
        """
        from .models import AlertSeverity
        
        severity_map = {
            'critical': AlertSeverity.CRITICAL,
            'high': AlertSeverity.HIGH,
            'medium': AlertSeverity.MEDIUM,
            'low': AlertSeverity.LOW,
            'info': AlertSeverity.INFO,
        }
        
        min_sev = severity_map.get(min_severity.lower()) if min_severity else None
        
        alerts = self.alert_manager.get_active_alerts(
            symbol=symbol,
            min_severity=min_sev
        )
        
        return [alert.to_dict() for alert in alerts]
    
    def acknowledge_alert(self, alert_id: str, user: str = 'system') -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            user: User acknowledging
            
        Returns:
            True if successful
        """
        return self.alert_manager.acknowledge_alert(alert_id, user)
    
    def subscribe_to_alerts(
        self,
        callback: callable,
        alert_type: Optional[str] = None,
    ) -> None:
        """
        Subscribe to real-time alerts.
        
        Args:
            callback: Function to call when alert is created
            alert_type: Specific alert type (None = all)
        """
        from .models import AlertType
        
        type_map = {
            'sweep': AlertType.UNUSUAL_SWEEP,
            'block': AlertType.LARGE_BLOCK,
            'dark_pool': AlertType.DARK_POOL_PRINT,
            'smart_money': AlertType.SMART_MONEY_FLOW,
            'institutional': AlertType.INSTITUTIONAL_PATTERN,
            'gamma_squeeze': AlertType.GAMMA_SQUEEZE,
            'volume': AlertType.VOLUME_SPIKE,
        }
        
        at = type_map.get(alert_type.lower()) if alert_type else None
        
        self.alert_manager.subscribe(callback, at)
    
    def add_alert_webhook(self, url: str) -> None:
        """Add webhook URL for alert dispatch."""
        self.alert_dispatcher.add_webhook_handler(url)
        if 'webhook' not in self.alert_dispatch_channels:
            self.alert_dispatch_channels.append('webhook')
    
    def get_statistics(self) -> Dict:
        """Get engine statistics."""
        alert_stats = self.alert_manager.get_statistics()
        
        return {
            'engine': self._stats,
            'alerts': alert_stats,
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            'trades_processed': 0,
            'sweeps_detected': 0,
            'blocks_detected': 0,
            'dark_pools_detected': 0,
            'patterns_detected': 0,
            'alerts_created': 0,
        }
