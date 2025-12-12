"""Dispatches alerts to various channels."""
from typing import List, Dict, Optional
from datetime import datetime
import json

from ..models import UnusualActivityAlert, AlertSeverity


class AlertDispatcher:
    """Dispatches alerts to configured channels."""
    
    def __init__(self):
        """Initialize alert dispatcher."""
        self._channels: Dict[str, List[callable]] = {
            'console': [self._console_handler],
            'webhook': [],
            'email': [],
            'sms': [],
        }
        
        # Dispatch log
        self._dispatch_log: List[Dict] = []
    
    def dispatch(
        self,
        alert: UnusualActivityAlert,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        Dispatch alert to channels.
        
        Args:
            alert: Alert to dispatch
            channels: List of channel names (None = all enabled)
            
        Returns:
            Dict mapping channel name to success status
        """
        if channels is None:
            channels = ['console']  # Default to console only
        
        results = {}
        
        for channel in channels:
            if channel not in self._channels:
                results[channel] = False
                continue
            
            # Try all handlers for channel
            channel_success = False
            for handler in self._channels[channel]:
                try:
                    handler(alert)
                    channel_success = True
                except Exception as e:
                    print(f"Error dispatching to {channel}: {e}")
            
            results[channel] = channel_success
        
        # Log dispatch
        self._log_dispatch(alert, channels, results)
        
        return results
    
    def _console_handler(self, alert: UnusualActivityAlert) -> None:
        """Handle console output."""
        severity_symbols = {
            AlertSeverity.CRITICAL: '🔴',
            AlertSeverity.HIGH: '🟠',
            AlertSeverity.MEDIUM: '🟡',
            AlertSeverity.LOW: '🔵',
            AlertSeverity.INFO: '⚪',
        }
        
        symbol = severity_symbols.get(alert.severity, '•')
        
        print(f"\n{symbol} [{alert.severity.value.upper()}] {alert.title}")
        print(f"   {alert.description}")
        print(f"   Symbol: {alert.underlying_symbol}")
        print(f"   Premium: ${float(alert.total_premium):,.0f}" if alert.total_premium else "")
        print(f"   Confidence: {alert.confidence_score:.1%}")
        print(f"   Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Alert ID: {alert.alert_id}")
    
    def add_webhook_handler(self, url: str) -> None:
        """Add webhook URL for alert dispatch."""
        def webhook_handler(alert: UnusualActivityAlert) -> None:
            # In production, use requests library
            # requests.post(url, json=alert.to_dict())
            print(f"[Webhook] Would POST to {url}: {alert.title}")
        
        self._channels['webhook'].append(webhook_handler)
    
    def add_email_handler(self, smtp_config: Dict) -> None:
        """Add email handler for alert dispatch."""
        def email_handler(alert: UnusualActivityAlert) -> None:
            # In production, use smtplib
            print(f"[Email] Would send to {smtp_config.get('to')}: {alert.title}")
        
        self._channels['email'].append(email_handler)
    
    def add_custom_handler(
        self,
        channel_name: str,
        handler: callable,
    ) -> None:
        """Add custom alert handler."""
        if channel_name not in self._channels:
            self._channels[channel_name] = []
        self._channels[channel_name].append(handler)
    
    def _log_dispatch(
        self,
        alert: UnusualActivityAlert,
        channels: List[str],
        results: Dict[str, bool],
    ) -> None:
        """Log alert dispatch."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'alert_id': alert.alert_id,
            'alert_type': alert.alert_type.value,
            'severity': alert.severity.value,
            'channels': channels,
            'results': results,
        }
        
        self._dispatch_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self._dispatch_log) > 1000:
            self._dispatch_log = self._dispatch_log[-1000:]
    
    def get_dispatch_log(
        self,
        limit: int = 100,
    ) -> List[Dict]:
        """Get recent dispatch log entries."""
        return self._dispatch_log[-limit:]
