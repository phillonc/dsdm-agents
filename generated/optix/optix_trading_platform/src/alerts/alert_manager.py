"""Manages and routes unusual activity alerts."""
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from collections import defaultdict

from ..models import (
    UnusualActivityAlert, AlertType, AlertSeverity,
    OptionsTrade, FlowPattern, MarketMakerPosition, TradeType
)


class AlertManager:
    """Manages creation, routing, and lifecycle of alerts."""
    
    def __init__(self, alert_retention_hours: int = 24):
        """
        Initialize alert manager.
        
        Args:
            alert_retention_hours: How long to keep alerts in memory
        """
        self.alert_retention = timedelta(hours=alert_retention_hours)
        
        # Active alerts
        self._alerts: List[UnusualActivityAlert] = []
        
        # Alert subscribers (callbacks)
        self._subscribers: Dict[AlertType, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        
        # Alert statistics
        self._stats = {
            'total_created': 0,
            'by_type': defaultdict(int),
            'by_severity': defaultdict(int),
        }
    
    def create_sweep_alert(
        self,
        sweep_trades: List[OptionsTrade],
        confidence: float,
    ) -> UnusualActivityAlert:
        """Create alert for sweep detection."""
        if not sweep_trades:
            raise ValueError("No trades provided for sweep alert")
        
        trade = sweep_trades[0]
        total_premium = sum(t.notional_value for t in sweep_trades)
        total_contracts = sum(t.size for t in sweep_trades)
        
        # Determine severity based on size and confidence
        severity = self._calculate_severity(
            total_premium, confidence, len(sweep_trades)
        )
        
        alert = UnusualActivityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.UNUSUAL_SWEEP,
            severity=severity,
            symbol=trade.symbol,
            underlying_symbol=trade.underlying_symbol,
            created_at=datetime.now(),
            title=f"Unusual Options Sweep: {trade.underlying_symbol}",
            description=(
                f"{trade.order_type.value.upper()} sweep detected: "
                f"{total_contracts} contracts across {len(sweep_trades)} exchanges. "
                f"Total premium: ${float(total_premium):,.0f}"
            ),
            related_trade_ids=[t.trade_id for t in sweep_trades],
            total_premium=total_premium,
            total_contracts=total_contracts,
            confidence_score=confidence,
            underlying_price=trade.underlying_price,
            strikes_involved=[trade.strike],
            expirations_involved=[trade.expiration],
            tags=['sweep', trade.order_type.value, trade.sentiment],
            metadata={
                'exchanges': list({t.exchange for t in sweep_trades}),
                'execution_time_seconds': (
                    sweep_trades[-1].timestamp - sweep_trades[0].timestamp
                ).total_seconds(),
            }
        )
        
        self._add_alert(alert)
        return alert
    
    def create_block_alert(
        self,
        trade: OptionsTrade,
        confidence: float,
    ) -> UnusualActivityAlert:
        """Create alert for block trade."""
        severity = self._calculate_severity(
            trade.notional_value, confidence, 1
        )
        
        alert = UnusualActivityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.LARGE_BLOCK,
            severity=severity,
            symbol=trade.symbol,
            underlying_symbol=trade.underlying_symbol,
            created_at=datetime.now(),
            title=f"Large Block Trade: {trade.underlying_symbol}",
            description=(
                f"Large {trade.order_type.value} block detected: "
                f"{trade.size} contracts at ${trade.strike}. "
                f"Premium: ${float(trade.notional_value):,.0f}"
            ),
            related_trade_ids=[trade.trade_id],
            total_premium=trade.notional_value,
            total_contracts=trade.size,
            confidence_score=confidence,
            underlying_price=trade.underlying_price,
            strikes_involved=[trade.strike],
            expirations_involved=[trade.expiration],
            tags=['block', trade.order_type.value, trade.sentiment],
            metadata={
                'execution_side': trade.execution_side,
                'is_opening': trade.is_opening,
            }
        )
        
        self._add_alert(alert)
        return alert
    
    def create_dark_pool_alert(
        self,
        trade: OptionsTrade,
        confidence: float,
    ) -> UnusualActivityAlert:
        """Create alert for dark pool print."""
        severity = self._calculate_severity(
            trade.notional_value, confidence, 1
        )
        
        alert = UnusualActivityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.DARK_POOL_PRINT,
            severity=severity,
            symbol=trade.symbol,
            underlying_symbol=trade.underlying_symbol,
            created_at=datetime.now(),
            title=f"Dark Pool Print: {trade.underlying_symbol}",
            description=(
                f"Dark pool {trade.order_type.value} print: "
                f"{trade.size} contracts at ${trade.strike}. "
                f"Premium: ${float(trade.notional_value):,.0f}"
            ),
            related_trade_ids=[trade.trade_id],
            total_premium=trade.notional_value,
            total_contracts=trade.size,
            confidence_score=confidence,
            underlying_price=trade.underlying_price,
            strikes_involved=[trade.strike],
            expirations_involved=[trade.expiration],
            tags=['dark_pool', trade.order_type.value],
            metadata={
                'exchange': trade.exchange,
                'execution_side': trade.execution_side,
            }
        )
        
        self._add_alert(alert)
        return alert
    
    def create_flow_pattern_alert(
        self,
        pattern: FlowPattern,
    ) -> UnusualActivityAlert:
        """Create alert for detected flow pattern."""
        # Map pattern type to alert type
        alert_type_map = {
            'aggressive_call_buying': AlertType.SMART_MONEY_FLOW,
            'aggressive_put_buying': AlertType.SMART_MONEY_FLOW,
            'institutional_flow': AlertType.INSTITUTIONAL_PATTERN,
            'spread_pattern': AlertType.SPREAD_PATTERN,
            'unusual_volume': AlertType.VOLUME_SPIKE,
        }
        
        alert_type = alert_type_map.get(
            pattern.pattern_type.value,
            AlertType.SMART_MONEY_FLOW
        )
        
        severity = self._calculate_severity(
            pattern.total_premium,
            pattern.confidence_score,
            pattern.trade_count
        )
        
        alert = UnusualActivityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            symbol=pattern.symbol,
            underlying_symbol=pattern.underlying_symbol,
            created_at=pattern.detected_at,
            title=f"Flow Pattern: {pattern.pattern_type.value.replace('_', ' ').title()}",
            description=pattern.description or (
                f"{pattern.pattern_type.value.replace('_', ' ').title()} detected. "
                f"Signal: {pattern.signal.value}, "
                f"Premium: ${float(pattern.total_premium):,.0f}"
            ),
            related_pattern_ids=[pattern.pattern_id],
            total_premium=pattern.total_premium,
            total_contracts=pattern.total_contracts,
            confidence_score=pattern.confidence_score,
            tags=[
                pattern.pattern_type.value,
                pattern.signal.value,
                pattern.net_sentiment
            ],
            metadata=pattern.metadata
        )
        
        self._add_alert(alert)
        return alert
    
    def create_gamma_squeeze_alert(
        self,
        position: MarketMakerPosition,
    ) -> UnusualActivityAlert:
        """Create alert for gamma squeeze risk."""
        alert = UnusualActivityAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.GAMMA_SQUEEZE,
            severity=AlertSeverity.HIGH,
            symbol=position.symbol,
            underlying_symbol=position.underlying_symbol,
            created_at=position.calculated_at,
            title=f"Gamma Squeeze Risk: {position.symbol}",
            description=(
                f"Market makers showing short gamma position. "
                f"Net gamma: {position.net_gamma}, "
                f"Hedge pressure: {position.hedge_pressure}"
            ),
            confidence_score=position.confidence,
            tags=['gamma_squeeze', position.hedge_pressure],
            metadata={
                'net_delta': str(position.net_delta),
                'net_gamma': str(position.net_gamma),
                'position_bias': position.position_bias.value,
                'max_pain': str(position.max_pain_price) if position.max_pain_price else None,
            }
        )
        
        self._add_alert(alert)
        return alert
    
    def _add_alert(self, alert: UnusualActivityAlert) -> None:
        """Add alert to active list and notify subscribers."""
        self._alerts.append(alert)
        
        # Update statistics
        self._stats['total_created'] += 1
        self._stats['by_type'][alert.alert_type.value] += 1
        self._stats['by_severity'][alert.severity.value] += 1
        
        # Notify subscribers
        self._notify_subscribers(alert)
        
        # Clean old alerts
        self._clean_old_alerts()
    
    def _notify_subscribers(self, alert: UnusualActivityAlert) -> None:
        """Notify subscribers of new alert."""
        # Type-specific subscribers
        for callback in self._subscribers.get(alert.alert_type, []):
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert subscriber: {e}")
        
        # Global subscribers
        for callback in self._global_subscribers:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in global subscriber: {e}")
    
    def _calculate_severity(
        self,
        premium: Decimal,
        confidence: float,
        trade_count: int,
    ) -> AlertSeverity:
        """Calculate alert severity."""
        score = 0
        
        # Premium score
        if premium >= Decimal('5000000'):  # $5M+
            score += 40
        elif premium >= Decimal('1000000'):  # $1M+
            score += 30
        elif premium >= Decimal('500000'):  # $500K+
            score += 20
        elif premium >= Decimal('100000'):  # $100K+
            score += 10
        
        # Confidence score
        if confidence >= 0.9:
            score += 30
        elif confidence >= 0.8:
            score += 20
        elif confidence >= 0.7:
            score += 10
        
        # Trade count score
        if trade_count >= 10:
            score += 20
        elif trade_count >= 5:
            score += 10
        
        # Map score to severity
        if score >= 70:
            return AlertSeverity.CRITICAL
        elif score >= 50:
            return AlertSeverity.HIGH
        elif score >= 30:
            return AlertSeverity.MEDIUM
        elif score >= 15:
            return AlertSeverity.LOW
        else:
            return AlertSeverity.INFO
    
    def subscribe(
        self,
        callback: Callable[[UnusualActivityAlert], None],
        alert_type: Optional[AlertType] = None,
    ) -> None:
        """
        Subscribe to alerts.
        
        Args:
            callback: Function to call when alert is created
            alert_type: Specific alert type (None = all alerts)
        """
        if alert_type:
            self._subscribers[alert_type].append(callback)
        else:
            self._global_subscribers.append(callback)
    
    def get_active_alerts(
        self,
        symbol: Optional[str] = None,
        alert_type: Optional[AlertType] = None,
        min_severity: Optional[AlertSeverity] = None,
    ) -> List[UnusualActivityAlert]:
        """
        Get active alerts with optional filters.
        
        Args:
            symbol: Filter by symbol
            alert_type: Filter by alert type
            min_severity: Minimum severity level
            
        Returns:
            List of matching active alerts
        """
        alerts = [a for a in self._alerts if a.is_active]
        
        if symbol:
            alerts = [a for a in alerts if a.underlying_symbol == symbol]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if min_severity:
            severity_order = {
                AlertSeverity.INFO: 0,
                AlertSeverity.LOW: 1,
                AlertSeverity.MEDIUM: 2,
                AlertSeverity.HIGH: 3,
                AlertSeverity.CRITICAL: 4,
            }
            min_level = severity_order[min_severity]
            alerts = [
                a for a in alerts
                if severity_order[a.severity] >= min_level
            ]
        
        # Sort by priority score
        alerts.sort(key=lambda a: a.priority_score, reverse=True)
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge(user)
                return True
        return False
    
    def deactivate_alert(self, alert_id: str) -> bool:
        """Deactivate an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.deactivate()
                return True
        return False
    
    def _clean_old_alerts(self) -> None:
        """Remove alerts outside retention window."""
        cutoff = datetime.now() - self.alert_retention
        self._alerts = [
            a for a in self._alerts
            if a.created_at >= cutoff
        ]
    
    def get_statistics(self) -> Dict:
        """Get alert statistics."""
        active_count = len([a for a in self._alerts if a.is_active])
        acknowledged_count = len([a for a in self._alerts if a.is_acknowledged])
        
        return {
            'total_created': self._stats['total_created'],
            'active': active_count,
            'acknowledged': acknowledged_count,
            'by_type': dict(self._stats['by_type']),
            'by_severity': dict(self._stats['by_severity']),
        }
