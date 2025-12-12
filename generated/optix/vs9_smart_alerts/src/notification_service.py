"""
VS-9 Smart Alerts Ecosystem - Notification Service
OPTIX Trading Platform

Multi-channel notification delivery service supporting push, email, SMS, and webhooks.
Handles delivery preferences, rate limiting, and quiet hours.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict
from enum import Enum

from .models import (
    ConsolidatedAlert, TriggeredAlert, DeliveryPreference,
    DeliveryChannel, AlertPriority, AlertStatus
)

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    QUIET_HOURS = "quiet_hours"
    CHANNEL_DISABLED = "channel_disabled"


class NotificationService:
    """
    Multi-channel notification delivery service with intelligent routing,
    rate limiting, and user preference management.
    """
    
    def __init__(self):
        self.delivery_preferences: Dict[str, DeliveryPreference] = {}
        self.delivery_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.rate_limit_trackers: Dict[str, Dict[str, List[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Mock delivery handlers (in production, these would be real integrations)
        self.delivery_handlers = {
            DeliveryChannel.PUSH: self._deliver_push,
            DeliveryChannel.EMAIL: self._deliver_email,
            DeliveryChannel.SMS: self._deliver_sms,
            DeliveryChannel.IN_APP: self._deliver_in_app,
            DeliveryChannel.WEBHOOK: self._deliver_webhook
        }
    
    def set_user_preferences(
        self,
        user_id: str,
        preferences: DeliveryPreference
    ) -> None:
        """Set delivery preferences for a user"""
        preferences.user_id = user_id
        preferences.updated_at = datetime.utcnow()
        self.delivery_preferences[user_id] = preferences
        logger.info(f"Updated delivery preferences for user {user_id}")
    
    def get_user_preferences(self, user_id: str) -> DeliveryPreference:
        """Get delivery preferences for a user (with defaults)"""
        if user_id in self.delivery_preferences:
            return self.delivery_preferences[user_id]
        
        # Return default preferences
        return DeliveryPreference(user_id=user_id)
    
    def deliver_alert(
        self,
        alert: ConsolidatedAlert
    ) -> Dict[DeliveryChannel, DeliveryStatus]:
        """
        Deliver a consolidated alert through appropriate channels.
        Returns delivery status for each channel.
        """
        user_id = alert.user_id
        preferences = self.get_user_preferences(user_id)
        
        # Determine which channels to use based on priority
        channels = self._select_channels(alert.priority, preferences)
        
        # Check quiet hours
        if self._is_quiet_hours(preferences) and alert.priority.value != AlertPriority.URGENT.value:
            logger.info(f"Alert {alert.consolidated_id} suppressed due to quiet hours")
            return {
                channel: DeliveryStatus.QUIET_HOURS
                for channel in channels
            }
        
        # Attempt delivery through each channel
        delivery_results = {}
        
        for channel in channels:
            # Check rate limits
            if self._is_rate_limited(user_id, channel, preferences):
                delivery_results[channel] = DeliveryStatus.RATE_LIMITED
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on channel {channel.value}"
                )
                continue
            
            # Attempt delivery
            try:
                status = self._deliver_to_channel(alert, channel, preferences)
                delivery_results[channel] = status
                
                # Record delivery attempt
                self._record_delivery(user_id, alert, channel, status)
                
                # Update rate limit tracker
                if status == DeliveryStatus.SENT:
                    self._update_rate_limit(user_id, channel)
                
            except Exception as e:
                logger.error(
                    f"Delivery failed for channel {channel.value}: {str(e)}"
                )
                delivery_results[channel] = DeliveryStatus.FAILED
        
        # Update alert's delivery tracking
        for channel, status in delivery_results.items():
            if status == DeliveryStatus.SENT:
                if channel not in alert.alerts[0].delivered_channels:
                    alert.alerts[0].delivered_channels.append(channel)
        
        logger.info(
            f"Delivered alert {alert.consolidated_id} to {len(delivery_results)} channels"
        )
        
        return delivery_results
    
    def _select_channels(
        self,
        priority: AlertPriority,
        preferences: DeliveryPreference
    ) -> List[DeliveryChannel]:
        """Select appropriate delivery channels based on priority"""
        # Get channels for this priority level
        channels = preferences.priority_channel_map.get(
            priority,
            [DeliveryChannel.IN_APP, DeliveryChannel.PUSH]
        )
        
        # Filter to only enabled channels
        enabled_channels = [
            channel for channel in channels
            if channel in preferences.enabled_channels
        ]
        
        return enabled_channels
    
    def _is_quiet_hours(self, preferences: DeliveryPreference) -> bool:
        """Check if current time is within user's quiet hours"""
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        try:
            current_time = datetime.utcnow().time()
            start = datetime.strptime(preferences.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
            
            # Handle overnight quiet hours
            if start <= end:
                return start <= current_time <= end
            else:
                return current_time >= start or current_time <= end
        
        except ValueError as e:
            logger.error(f"Invalid quiet hours format: {e}")
            return False
    
    def _is_rate_limited(
        self,
        user_id: str,
        channel: DeliveryChannel,
        preferences: DeliveryPreference
    ) -> bool:
        """Check if user has exceeded rate limits for a channel"""
        now = datetime.utcnow()
        
        # Get recent deliveries for this channel
        recent_deliveries = self.rate_limit_trackers[user_id][channel.value]
        
        # Clean up old entries
        recent_deliveries = [
            dt for dt in recent_deliveries
            if now - dt < timedelta(hours=1)
        ]
        self.rate_limit_trackers[user_id][channel.value] = recent_deliveries
        
        # Check hourly limit
        if len(recent_deliveries) >= preferences.max_alerts_per_hour:
            return True
        
        # Check SMS daily limit
        if channel == DeliveryChannel.SMS:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_sms = [dt for dt in recent_deliveries if dt >= day_start]
            if len(daily_sms) >= preferences.max_sms_per_day:
                return True
        
        return False
    
    def _update_rate_limit(self, user_id: str, channel: DeliveryChannel) -> None:
        """Update rate limit tracker for a successful delivery"""
        self.rate_limit_trackers[user_id][channel.value].append(datetime.utcnow())
    
    def _deliver_to_channel(
        self,
        alert: ConsolidatedAlert,
        channel: DeliveryChannel,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver alert through specific channel"""
        handler = self.delivery_handlers.get(channel)
        
        if not handler:
            logger.error(f"No handler for channel: {channel.value}")
            return DeliveryStatus.FAILED
        
        try:
            return handler(alert, preferences)
        except Exception as e:
            logger.error(f"Delivery handler error for {channel.value}: {str(e)}")
            return DeliveryStatus.FAILED
    
    def _deliver_push(
        self,
        alert: ConsolidatedAlert,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver push notification"""
        if not preferences.push_tokens:
            logger.warning("No push tokens configured")
            return DeliveryStatus.CHANNEL_DISABLED
        
        # Mock push notification delivery
        notification_payload = {
            "title": alert.title,
            "body": alert.summary,
            "priority": alert.priority.value,
            "alert_id": alert.consolidated_id,
            "alert_count": alert.alert_count,
            "data": {
                "consolidated_id": alert.consolidated_id,
                "user_id": alert.user_id,
                "timestamp": alert.created_at.isoformat()
            }
        }
        
        logger.info(
            f"[PUSH] Sent to {len(preferences.push_tokens)} devices: {alert.title}"
        )
        
        return DeliveryStatus.SENT
    
    def _deliver_email(
        self,
        alert: ConsolidatedAlert,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver email notification"""
        if not preferences.email:
            logger.warning("No email configured")
            return DeliveryStatus.CHANNEL_DISABLED
        
        # Mock email delivery
        email_content = {
            "to": preferences.email,
            "subject": f"[OPTIX Alert] {alert.title}",
            "body": self._format_email_body(alert),
            "priority": alert.priority.value
        }
        
        logger.info(
            f"[EMAIL] Sent to {preferences.email}: {alert.title}"
        )
        
        return DeliveryStatus.SENT
    
    def _deliver_sms(
        self,
        alert: ConsolidatedAlert,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver SMS notification"""
        if not preferences.phone:
            logger.warning("No phone number configured")
            return DeliveryStatus.CHANNEL_DISABLED
        
        # Mock SMS delivery (truncate message for SMS)
        sms_message = f"OPTIX: {alert.title[:100]}"
        
        logger.info(
            f"[SMS] Sent to {preferences.phone}: {sms_message}"
        )
        
        return DeliveryStatus.SENT
    
    def _deliver_in_app(
        self,
        alert: ConsolidatedAlert,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver in-app notification"""
        # Mock in-app notification (would store in database)
        notification = {
            "user_id": alert.user_id,
            "alert_id": alert.consolidated_id,
            "title": alert.title,
            "message": alert.summary,
            "priority": alert.priority.value,
            "timestamp": alert.created_at.isoformat(),
            "read": False
        }
        
        logger.info(
            f"[IN-APP] Created for user {alert.user_id}: {alert.title}"
        )
        
        return DeliveryStatus.SENT
    
    def _deliver_webhook(
        self,
        alert: ConsolidatedAlert,
        preferences: DeliveryPreference
    ) -> DeliveryStatus:
        """Deliver webhook notification"""
        if not preferences.webhook_url:
            logger.warning("No webhook URL configured")
            return DeliveryStatus.CHANNEL_DISABLED
        
        # Mock webhook delivery
        webhook_payload = {
            "event": "alert.triggered",
            "alert_id": alert.consolidated_id,
            "user_id": alert.user_id,
            "title": alert.title,
            "summary": alert.summary,
            "priority": alert.priority.value,
            "alert_count": alert.alert_count,
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "rule_id": a.rule_id,
                    "symbol": a.metadata.get("symbol"),
                    "trigger_values": a.trigger_values
                }
                for a in alert.alerts
            ],
            "timestamp": alert.created_at.isoformat()
        }
        
        logger.info(
            f"[WEBHOOK] Posted to {preferences.webhook_url}: {alert.title}"
        )
        
        return DeliveryStatus.SENT
    
    def _format_email_body(self, alert: ConsolidatedAlert) -> str:
        """Format email body for alert"""
        body_parts = [
            f"Priority: {alert.priority.value.upper()}",
            f"Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"Summary: {alert.summary}",
            "",
            f"This consolidated alert contains {alert.alert_count} individual alert(s):",
            ""
        ]
        
        # Add details for each alert
        for i, individual_alert in enumerate(alert.alerts[:10], 1):
            symbol = individual_alert.metadata.get("symbol", "N/A")
            body_parts.append(f"{i}. {symbol}: {individual_alert.message}")
        
        if len(alert.alerts) > 10:
            body_parts.append(f"... and {len(alert.alerts) - 10} more alerts")
        
        body_parts.extend([
            "",
            "---",
            "OPTIX Trading Platform",
            "Smart Alerts Ecosystem"
        ])
        
        return "\n".join(body_parts)
    
    def _record_delivery(
        self,
        user_id: str,
        alert: ConsolidatedAlert,
        channel: DeliveryChannel,
        status: DeliveryStatus
    ) -> None:
        """Record delivery attempt for analytics"""
        record = {
            "timestamp": datetime.utcnow(),
            "alert_id": alert.consolidated_id,
            "channel": channel.value,
            "status": status.value,
            "priority": alert.priority.value,
            "alert_count": alert.alert_count
        }
        
        self.delivery_history[user_id].append(record)
    
    def get_delivery_history(
        self,
        user_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get delivery history for a user"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        history = [
            record for record in self.delivery_history.get(user_id, [])
            if record["timestamp"] >= cutoff
        ]
        
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)
    
    def get_delivery_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get delivery statistics"""
        if user_id:
            history = self.delivery_history.get(user_id, [])
        else:
            # Aggregate across all users
            history = []
            for user_history in self.delivery_history.values():
                history.extend(user_history)
        
        if not history:
            return {
                "total_deliveries": 0,
                "by_channel": {},
                "by_status": {},
                "success_rate": 0.0
            }
        
        # Count by channel
        by_channel = defaultdict(int)
        by_status = defaultdict(int)
        
        for record in history:
            by_channel[record["channel"]] += 1
            by_status[record["status"]] += 1
        
        # Calculate success rate
        successful = by_status.get("sent", 0)
        total = len(history)
        success_rate = (successful / total * 100) if total > 0 else 0.0
        
        return {
            "total_deliveries": total,
            "by_channel": dict(by_channel),
            "by_status": dict(by_status),
            "success_rate": success_rate
        }
    
    def test_delivery_channel(
        self,
        user_id: str,
        channel: DeliveryChannel
    ) -> DeliveryStatus:
        """Test a delivery channel for a user"""
        preferences = self.get_user_preferences(user_id)
        
        # Create test alert
        from .models import TriggeredAlert
        test_alert = TriggeredAlert(
            user_id=user_id,
            title="Test Alert",
            message="This is a test alert from OPTIX Smart Alerts",
            priority=AlertPriority.LOW
        )
        
        test_consolidated = ConsolidatedAlert(
            user_id=user_id,
            alerts=[test_alert],
            alert_ids=[test_alert.alert_id],
            title="Test Alert",
            summary="This is a test alert",
            priority=AlertPriority.LOW,
            alert_count=1,
            consolidation_reason="test"
        )
        
        try:
            status = self._deliver_to_channel(test_consolidated, channel, preferences)
            logger.info(f"Test delivery for user {user_id} on {channel.value}: {status.value}")
            return status
        except Exception as e:
            logger.error(f"Test delivery failed: {str(e)}")
            return DeliveryStatus.FAILED
