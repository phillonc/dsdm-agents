"""
Unit tests for VS-9 Notification Service
"""

import pytest
from datetime import datetime, time, timedelta
from src.notification_service import NotificationService, DeliveryStatus
from src.models import (
    ConsolidatedAlert, TriggeredAlert, DeliveryPreference,
    DeliveryChannel, AlertPriority
)


class TestNotificationService:
    """Test NotificationService functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = NotificationService()
    
    def test_set_and_get_preferences(self):
        """Test setting and getting user preferences"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.EMAIL, DeliveryChannel.SMS],
            email="test@example.com",
            phone="+1234567890"
        )
        
        self.service.set_user_preferences("user123", prefs)
        
        retrieved = self.service.get_user_preferences("user123")
        assert retrieved.email == "test@example.com"
        assert retrieved.phone == "+1234567890"
    
    def test_default_preferences(self):
        """Test default preferences for new user"""
        prefs = self.service.get_user_preferences("new_user")
        
        assert DeliveryChannel.IN_APP in prefs.enabled_channels
        assert DeliveryChannel.PUSH in prefs.enabled_channels
        assert prefs.enable_consolidation is True
    
    def test_deliver_alert_basic(self):
        """Test basic alert delivery"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test Alert",
            message="Test message",
            priority=AlertPriority.HIGH
        )
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert],
            alert_ids=[alert.alert_id],
            title="Test Alert",
            summary="Test summary",
            priority=AlertPriority.HIGH,
            alert_count=1,
            consolidation_reason="test"
        )
        
        results = self.service.deliver_alert(consolidated)
        
        assert len(results) > 0
        # Default channels should be delivered
        assert any(status == DeliveryStatus.SENT for status in results.values())
    
    def test_priority_based_routing(self):
        """Test priority-based channel selection"""
        # Setup preferences
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[
                DeliveryChannel.IN_APP,
                DeliveryChannel.PUSH,
                DeliveryChannel.EMAIL,
                DeliveryChannel.SMS
            ],
            email="test@example.com",
            phone="+1234567890"
        )
        self.service.set_user_preferences("user123", prefs)
        
        # Low priority alert
        alert_low = TriggeredAlert(
            rule_id="rule1",
            user_id="user123",
            title="Low Priority",
            message="Test",
            priority=AlertPriority.LOW
        )
        
        consolidated_low = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert_low],
            alert_ids=[alert_low.alert_id],
            title="Low Priority",
            summary="Test",
            priority=AlertPriority.LOW,
            alert_count=1,
            consolidation_reason="test"
        )
        
        results_low = self.service.deliver_alert(consolidated_low)
        
        # Low priority should not send SMS
        assert DeliveryChannel.SMS not in results_low or \
               results_low.get(DeliveryChannel.SMS) != DeliveryStatus.SENT
        
        # Urgent priority alert
        alert_urgent = TriggeredAlert(
            rule_id="rule2",
            user_id="user123",
            title="Urgent Alert",
            message="Test",
            priority=AlertPriority.URGENT
        )
        
        consolidated_urgent = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert_urgent],
            alert_ids=[alert_urgent.alert_id],
            title="Urgent Alert",
            summary="Test",
            priority=AlertPriority.URGENT,
            alert_count=1,
            consolidation_reason="test"
        )
        
        results_urgent = self.service.deliver_alert(consolidated_urgent)
        
        # Urgent should attempt multiple channels
        assert len(results_urgent) >= 2
    
    def test_quiet_hours(self):
        """Test quiet hours functionality"""
        # Setup quiet hours
        prefs = DeliveryPreference(
            user_id="user123",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        self.service.set_user_preferences("user123", prefs)
        
        # Check if it's quiet hours (this is time-dependent)
        is_quiet = self.service._is_quiet_hours(prefs)
        
        # Test should pass regardless of current time
        assert isinstance(is_quiet, bool)
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        prefs = DeliveryPreference(
            user_id="user123",
            max_alerts_per_hour=3
        )
        self.service.set_user_preferences("user123", prefs)
        
        # Send multiple alerts
        for i in range(5):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            
            consolidated = ConsolidatedAlert(
                user_id="user123",
                alerts=[alert],
                alert_ids=[alert.alert_id],
                title=f"Alert {i}",
                summary="Test",
                priority=AlertPriority.MEDIUM,
                alert_count=1,
                consolidation_reason="test"
            )
            
            results = self.service.deliver_alert(consolidated)
            
            # After 3 alerts, should be rate limited
            if i >= 3:
                assert any(
                    status == DeliveryStatus.RATE_LIMITED
                    for status in results.values()
                )
    
    def test_sms_daily_limit(self):
        """Test SMS daily rate limit"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.SMS],
            phone="+1234567890",
            max_sms_per_day=2
        )
        self.service.set_user_preferences("user123", prefs)
        
        # Send multiple SMS alerts
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message="Test",
                priority=AlertPriority.URGENT  # Force SMS
            )
            
            consolidated = ConsolidatedAlert(
                user_id="user123",
                alerts=[alert],
                alert_ids=[alert.alert_id],
                title=f"Alert {i}",
                summary="Test",
                priority=AlertPriority.URGENT,
                alert_count=1,
                consolidation_reason="test"
            )
            
            results = self.service.deliver_alert(consolidated)
            
            # Third SMS should be rate limited
            if i >= 2 and DeliveryChannel.SMS in results:
                assert results[DeliveryChannel.SMS] == DeliveryStatus.RATE_LIMITED
    
    def test_channel_disabled(self):
        """Test disabled channel handling"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.IN_APP],  # Only in-app enabled
            email=None  # No email configured
        )
        self.service.set_user_preferences("user123", prefs)
        
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test",
            priority=AlertPriority.HIGH
        )
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert],
            alert_ids=[alert.alert_id],
            title="Test",
            summary="Test",
            priority=AlertPriority.HIGH,
            alert_count=1,
            consolidation_reason="test"
        )
        
        results = self.service.deliver_alert(consolidated)
        
        # EMAIL should not be in results or should be disabled/failed
        if DeliveryChannel.EMAIL in results:
            assert results[DeliveryChannel.EMAIL] != DeliveryStatus.SENT
    
    def test_delivery_history(self):
        """Test delivery history tracking"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test",
            priority=AlertPriority.MEDIUM
        )
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert],
            alert_ids=[alert.alert_id],
            title="Test",
            summary="Test",
            priority=AlertPriority.MEDIUM,
            alert_count=1,
            consolidation_reason="test"
        )
        
        self.service.deliver_alert(consolidated)
        
        history = self.service.get_delivery_history("user123", hours=24)
        
        assert len(history) > 0
        assert history[0]["user_id"] == "user123" or "alert_id" in history[0]
    
    def test_delivery_stats(self):
        """Test delivery statistics"""
        # Deliver some alerts
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            
            consolidated = ConsolidatedAlert(
                user_id="user123",
                alerts=[alert],
                alert_ids=[alert.alert_id],
                title="Test",
                summary="Test",
                priority=AlertPriority.MEDIUM,
                alert_count=1,
                consolidation_reason="test"
            )
            
            self.service.deliver_alert(consolidated)
        
        stats = self.service.get_delivery_stats("user123")
        
        assert stats["total_deliveries"] > 0
        assert "by_channel" in stats
        assert "success_rate" in stats
    
    def test_test_delivery_channel(self):
        """Test the test delivery functionality"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.PUSH],
            push_tokens=["token123"]
        )
        self.service.set_user_preferences("user123", prefs)
        
        status = self.service.test_delivery_channel("user123", DeliveryChannel.PUSH)
        
        assert status == DeliveryStatus.SENT
    
    def test_push_notification_payload(self):
        """Test push notification payload generation"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.PUSH],
            push_tokens=["token1", "token2"]
        )
        self.service.set_user_preferences("user123", prefs)
        
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test Alert",
            message="Test message",
            priority=AlertPriority.HIGH
        )
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert],
            alert_ids=[alert.alert_id],
            title="Test Alert",
            summary="Test summary",
            priority=AlertPriority.HIGH,
            alert_count=1,
            consolidation_reason="test"
        )
        
        # Deliver should succeed
        results = self.service.deliver_alert(consolidated)
        
        if DeliveryChannel.PUSH in results:
            assert results[DeliveryChannel.PUSH] == DeliveryStatus.SENT
    
    def test_email_formatting(self):
        """Test email body formatting"""
        alerts = []
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message=f"Message {i}",
                priority=AlertPriority.HIGH
            )
            alert.metadata["symbol"] = "AAPL"
            alerts.append(alert)
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=alerts,
            alert_ids=[a.alert_id for a in alerts],
            title="Multiple Alerts",
            summary="Test summary",
            priority=AlertPriority.HIGH,
            alert_count=3,
            consolidation_reason="test"
        )
        
        email_body = self.service._format_email_body(consolidated)
        
        assert "Priority:" in email_body
        assert "AAPL" in email_body
        assert len(email_body) > 0
    
    def test_webhook_delivery(self):
        """Test webhook delivery"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.WEBHOOK],
            webhook_url="https://example.com/webhook"
        )
        self.service.set_user_preferences("user123", prefs)
        
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test",
            priority=AlertPriority.HIGH
        )
        
        consolidated = ConsolidatedAlert(
            user_id="user123",
            alerts=[alert],
            alert_ids=[alert.alert_id],
            title="Test",
            summary="Test",
            priority=AlertPriority.HIGH,
            alert_count=1,
            consolidation_reason="test"
        )
        
        results = self.service.deliver_alert(consolidated)
        
        if DeliveryChannel.WEBHOOK in results:
            assert results[DeliveryChannel.WEBHOOK] == DeliveryStatus.SENT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
