"""
Alert engine for volatility changes and thresholds.
"""
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from .models import VolatilityAlert, VolatilityMetrics


class VolatilityAlertEngine:
    """Engine for detecting and generating volatility alerts."""
    
    def __init__(self):
        """Initialize alert engine with default thresholds."""
        self.thresholds = {
            'iv_spike_percent': 20.0,  # 20% increase in IV
            'iv_crush_percent': 20.0,  # 20% decrease in IV
            'iv_rank_high': 80.0,
            'iv_rank_low': 20.0,
            'skew_change_threshold': 0.15,  # 15% change in put/call ratio
            'iv_hv_divergence': 1.5,  # IV is 1.5x HV
        }
        
        self.alert_history: Dict[str, List[VolatilityAlert]] = {}
    
    def check_alerts(
        self,
        symbol: str,
        current_metrics: VolatilityMetrics,
        previous_metrics: Optional[VolatilityMetrics] = None,
        previous_iv: Optional[float] = None
    ) -> List[VolatilityAlert]:
        """
        Check for alert conditions and generate alerts.
        
        Args:
            symbol: Stock symbol
            current_metrics: Current volatility metrics
            previous_metrics: Previous period metrics (optional)
            previous_iv: Previous IV value for spike/crush detection
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # IV Spike detection
        if previous_iv is not None:
            spike_alert = self._check_iv_spike(
                symbol, current_metrics.current_iv, previous_iv
            )
            if spike_alert:
                alerts.append(spike_alert)
        
        # IV Crush detection
        if previous_iv is not None:
            crush_alert = self._check_iv_crush(
                symbol, current_metrics.current_iv, previous_iv
            )
            if crush_alert:
                alerts.append(crush_alert)
        
        # IV Rank threshold alerts
        rank_alerts = self._check_iv_rank_thresholds(symbol, current_metrics)
        alerts.extend(rank_alerts)
        
        # IV/HV divergence alert
        divergence_alert = self._check_iv_hv_divergence(symbol, current_metrics)
        if divergence_alert:
            alerts.append(divergence_alert)
        
        # Historical extreme alerts
        extreme_alerts = self._check_historical_extremes(symbol, current_metrics)
        alerts.extend(extreme_alerts)
        
        # Store alerts in history
        if symbol not in self.alert_history:
            self.alert_history[symbol] = []
        self.alert_history[symbol].extend(alerts)
        
        return alerts
    
    def _check_iv_spike(
        self,
        symbol: str,
        current_iv: float,
        previous_iv: float
    ) -> Optional[VolatilityAlert]:
        """Check for IV spike (rapid increase)."""
        if previous_iv == 0:
            return None
        
        change_percent = ((current_iv - previous_iv) / previous_iv) * 100
        
        if change_percent >= self.thresholds['iv_spike_percent']:
            severity = self._calculate_severity(change_percent, 20, 40, 60)
            
            return VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="iv_spike",
                severity=severity,
                message=f"IV spiked {change_percent:.1f}% from {previous_iv:.1f}% to {current_iv:.1f}%",
                current_value=current_iv,
                previous_value=previous_iv,
                change_percent=change_percent,
                threshold=self.thresholds['iv_spike_percent'],
                iv_rank=0.0,  # Will be updated by caller
                iv_percentile=0.0
            )
        
        return None
    
    def _check_iv_crush(
        self,
        symbol: str,
        current_iv: float,
        previous_iv: float
    ) -> Optional[VolatilityAlert]:
        """Check for IV crush (rapid decrease)."""
        if previous_iv == 0:
            return None
        
        change_percent = ((previous_iv - current_iv) / previous_iv) * 100
        
        if change_percent >= self.thresholds['iv_crush_percent']:
            severity = self._calculate_severity(change_percent, 20, 40, 60)
            
            return VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="iv_crush",
                severity=severity,
                message=f"IV crushed {change_percent:.1f}% from {previous_iv:.1f}% to {current_iv:.1f}%",
                current_value=current_iv,
                previous_value=previous_iv,
                change_percent=change_percent,
                threshold=self.thresholds['iv_crush_percent'],
                iv_rank=0.0,
                iv_percentile=0.0
            )
        
        return None
    
    def _check_iv_rank_thresholds(
        self,
        symbol: str,
        metrics: VolatilityMetrics
    ) -> List[VolatilityAlert]:
        """Check for IV rank crossing threshold levels."""
        alerts = []
        
        # High IV rank alert
        if metrics.iv_rank >= self.thresholds['iv_rank_high']:
            severity = "high" if metrics.iv_rank >= 90 else "medium"
            
            alerts.append(VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="rank_threshold",
                severity=severity,
                message=f"IV Rank at {metrics.iv_rank:.1f}% - Premium selling opportunity",
                current_value=metrics.iv_rank,
                previous_value=0.0,
                change_percent=0.0,
                threshold=self.thresholds['iv_rank_high'],
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile
            ))
        
        # Low IV rank alert
        elif metrics.iv_rank <= self.thresholds['iv_rank_low']:
            severity = "high" if metrics.iv_rank <= 10 else "medium"
            
            alerts.append(VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="rank_threshold",
                severity=severity,
                message=f"IV Rank at {metrics.iv_rank:.1f}% - Premium buying opportunity",
                current_value=metrics.iv_rank,
                previous_value=0.0,
                change_percent=0.0,
                threshold=self.thresholds['iv_rank_low'],
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile
            ))
        
        return alerts
    
    def _check_iv_hv_divergence(
        self,
        symbol: str,
        metrics: VolatilityMetrics
    ) -> Optional[VolatilityAlert]:
        """Check for significant IV/HV divergence."""
        if metrics.iv_hv_ratio >= self.thresholds['iv_hv_divergence']:
            return VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="iv_hv_divergence",
                severity="medium",
                message=f"IV/HV ratio at {metrics.iv_hv_ratio:.2f} - Options may be overpriced",
                current_value=metrics.iv_hv_ratio,
                previous_value=1.0,
                change_percent=((metrics.iv_hv_ratio - 1.0) / 1.0) * 100,
                threshold=self.thresholds['iv_hv_divergence'],
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile
            )
        
        return None
    
    def _check_historical_extremes(
        self,
        symbol: str,
        metrics: VolatilityMetrics
    ) -> List[VolatilityAlert]:
        """Check if current IV is at historical extremes."""
        alerts = []
        
        # Near 52-week high
        if metrics.current_iv >= metrics.max_iv_52w * 0.95:
            alerts.append(VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="historical_extreme",
                severity="high",
                message=f"IV at {metrics.current_iv:.1f}% near 52-week high of {metrics.max_iv_52w:.1f}%",
                current_value=metrics.current_iv,
                previous_value=metrics.max_iv_52w,
                change_percent=0.0,
                threshold=metrics.max_iv_52w * 0.95,
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile
            ))
        
        # Near 52-week low
        elif metrics.current_iv <= metrics.min_iv_52w * 1.05:
            alerts.append(VolatilityAlert(
                alert_id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                alert_type="historical_extreme",
                severity="high",
                message=f"IV at {metrics.current_iv:.1f}% near 52-week low of {metrics.min_iv_52w:.1f}%",
                current_value=metrics.current_iv,
                previous_value=metrics.min_iv_52w,
                change_percent=0.0,
                threshold=metrics.min_iv_52w * 1.05,
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile
            ))
        
        return alerts
    
    def _calculate_severity(
        self,
        value: float,
        medium_threshold: float,
        high_threshold: float,
        critical_threshold: float
    ) -> str:
        """Calculate alert severity based on value and thresholds."""
        if value >= critical_threshold:
            return "critical"
        elif value >= high_threshold:
            return "high"
        elif value >= medium_threshold:
            return "medium"
        else:
            return "low"
    
    def get_alert_summary(self, symbol: str, hours: int = 24) -> Dict:
        """
        Get summary of alerts for a symbol in the last N hours.
        
        Args:
            symbol: Stock symbol
            hours: Number of hours to look back
            
        Returns:
            Dictionary with alert summary statistics
        """
        if symbol not in self.alert_history:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_type': {},
                'recent_alerts': []
            }
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        recent_alerts = [
            alert for alert in self.alert_history[symbol]
            if alert.timestamp.timestamp() >= cutoff_time
        ]
        
        # Count by severity
        by_severity = {}
        for alert in recent_alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
        
        # Count by type
        by_type = {}
        for alert in recent_alerts:
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1
        
        return {
            'total_alerts': len(recent_alerts),
            'by_severity': by_severity,
            'by_type': by_type,
            'recent_alerts': recent_alerts[-5:]  # Last 5 alerts
        }
    
    def clear_old_alerts(self, symbol: str, days: int = 30):
        """Clear alerts older than specified days."""
        if symbol not in self.alert_history:
            return
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        self.alert_history[symbol] = [
            alert for alert in self.alert_history[symbol]
            if alert.timestamp.timestamp() >= cutoff_time
        ]
    
    def update_thresholds(self, threshold_updates: Dict[str, float]):
        """
        Update alert thresholds.
        
        Args:
            threshold_updates: Dictionary of threshold names and new values
        """
        for key, value in threshold_updates.items():
            if key in self.thresholds:
                self.thresholds[key] = value
