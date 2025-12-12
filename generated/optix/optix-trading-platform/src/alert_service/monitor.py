"""
Alert Monitor
Background service for monitoring price alerts
"""
import asyncio
from typing import Dict, Set
import uuid
from decimal import Decimal
from datetime import datetime
from .models import Alert, AlertStatus, AlertType, AlertTriggered
from .repository import AlertRepository


class AlertMonitor:
    """
    Alert monitoring service
    Checks prices and triggers alerts
    """
    
    def __init__(self):
        self.repo = AlertRepository()
        self._monitoring: Set[uuid.UUID] = set()
        self._tasks: Dict[uuid.UUID, asyncio.Task] = {}
    
    async def start_monitoring(self, alert_id: uuid.UUID):
        """Start monitoring an alert"""
        if alert_id in self._monitoring:
            return  # Already monitoring
        
        self._monitoring.add(alert_id)
        task = asyncio.create_task(self._monitor_alert(alert_id))
        self._tasks[alert_id] = task
    
    def stop_monitoring(self, alert_id: uuid.UUID):
        """Stop monitoring an alert"""
        if alert_id in self._monitoring:
            self._monitoring.remove(alert_id)
        
        if alert_id in self._tasks:
            self._tasks[alert_id].cancel()
            del self._tasks[alert_id]
    
    async def _monitor_alert(self, alert_id: uuid.UUID):
        """Monitor alert and check for triggers"""
        while alert_id in self._monitoring:
            try:
                alert = self.repo.get_alert(alert_id)
                
                if not alert or alert.status != AlertStatus.ACTIVE:
                    self.stop_monitoring(alert_id)
                    break
                
                # Check if expired
                if alert.expires_at and datetime.utcnow() > alert.expires_at:
                    self.repo.update_alert(alert_id, {"status": AlertStatus.EXPIRED})
                    self.stop_monitoring(alert_id)
                    break
                
                # Get current price (mock for now)
                current_price = await self._get_current_price(alert.symbol)
                
                # Check if alert should trigger
                should_trigger = self._check_trigger_condition(alert, current_price)
                
                if should_trigger:
                    await self._trigger_alert(alert, current_price)
                    self.stop_monitoring(alert_id)
                    break
                
                # Check every 5 seconds
                await asyncio.sleep(5)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error monitoring alert {alert_id}: {e}")
                await asyncio.sleep(5)
    
    def _check_trigger_condition(self, alert: Alert, current_price: Decimal) -> bool:
        """Check if alert condition is met"""
        if alert.alert_type == AlertType.PRICE_ABOVE:
            return current_price >= alert.threshold_value
        
        elif alert.alert_type == AlertType.PRICE_BELOW:
            return current_price <= alert.threshold_value
        
        elif alert.alert_type == AlertType.PERCENT_CHANGE:
            # Would need previous price to calculate
            return False
        
        elif alert.alert_type == AlertType.VOLUME_SPIKE:
            # Would need volume data
            return False
        
        return False
    
    async def _trigger_alert(self, alert: Alert, current_price: Decimal):
        """Trigger alert and send notification"""
        # Update alert status
        self.repo.update_alert(alert.id, {
            "status": AlertStatus.TRIGGERED,
            "triggered_at": datetime.utcnow(),
            "triggered_price": current_price
        })
        
        # Create notification
        notification = AlertTriggered(
            alert_id=alert.id,
            symbol=alert.symbol,
            alert_type=alert.alert_type,
            threshold_value=alert.threshold_value,
            current_price=current_price,
            message=alert.message,
            triggered_at=datetime.utcnow()
        )
        
        # Send push notification (would integrate with FCM/APNs)
        await self._send_notification(alert.user_id, notification)
    
    async def _send_notification(self, user_id: uuid.UUID, notification: AlertTriggered):
        """Send push notification to user"""
        # In production, integrate with Firebase Cloud Messaging / Apple Push Notification Service
        print(f"[NOTIFICATION] User {user_id}: {notification.symbol} alert triggered at ${notification.current_price}")
    
    async def _get_current_price(self, symbol: str) -> Decimal:
        """Get current price for symbol"""
        # In production, integrate with market data service
        # For now, return mock price
        return Decimal("150.00")
