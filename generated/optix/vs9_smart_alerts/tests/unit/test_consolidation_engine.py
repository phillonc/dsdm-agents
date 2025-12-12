"""
Unit tests for VS-9 Consolidation Engine
"""

import pytest
from datetime import datetime, timedelta
from src.consolidation_engine import ConsolidationEngine
from src.models import TriggeredAlert, AlertPriority, AlertStatus


class TestConsolidationEngine:
    """Test ConsolidationEngine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = ConsolidationEngine(consolidation_window_minutes=5)
    
    def test_process_single_alert(self):
        """Test processing a single alert"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test Alert",
            message="Test message",
            priority=AlertPriority.HIGH
        )
        alert.metadata["allow_consolidation"] = False
        
        consolidated = self.engine.process_alert(alert)
        
        assert consolidated is not None
        assert consolidated.alert_count == 1
        assert len(consolidated.alerts) == 1
    
    def test_consolidation_pending(self):
        """Test alert pending consolidation"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test Alert",
            message="Test",
            priority=AlertPriority.MEDIUM
        )
        alert.metadata["allow_consolidation"] = True
        
        # First alert should pend
        consolidated = self.engine.process_alert(alert)
        assert consolidated is None
        assert self.engine.get_pending_count("user123") == 1
    
    def test_consolidation_after_window(self):
        """Test consolidation after time window"""
        # Add first alert
        alert1 = TriggeredAlert(
            rule_id="rule1",
            user_id="user123",
            title="Alert 1",
            message="Test",
            priority=AlertPriority.MEDIUM
        )
        alert1.metadata["symbol"] = "AAPL"
        alert1.metadata["allow_consolidation"] = True
        
        self.engine.process_alert(alert1)
        
        # Simulate time passing
        self.engine.last_flush_time["user123"] = datetime.utcnow() - timedelta(minutes=6)
        
        # Add second alert - should trigger flush
        alert2 = TriggeredAlert(
            rule_id="rule2",
            user_id="user123",
            title="Alert 2",
            message="Test",
            priority=AlertPriority.MEDIUM
        )
        alert2.metadata["symbol"] = "AAPL"
        alert2.metadata["allow_consolidation"] = True
        
        consolidated = self.engine.process_alert(alert2)
        
        assert consolidated is not None
        assert consolidated.alert_count >= 1
    
    def test_group_by_symbol(self):
        """Test grouping alerts by symbol"""
        alerts = []
        for i, symbol in enumerate(["AAPL", "AAPL", "SPY"]):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["symbol"] = symbol
            alert.metadata["allow_consolidation"] = True
            alerts.append(alert)
        
        # Add alerts
        for alert in alerts:
            self.engine.process_alert(alert)
        
        # Force flush
        consolidated = self.engine.force_flush_user("user123")
        
        assert consolidated is not None
    
    def test_priority_elevation(self):
        """Test priority elevation in consolidation"""
        alerts = []
        priorities = [AlertPriority.LOW, AlertPriority.MEDIUM, AlertPriority.HIGH]
        
        for i, priority in enumerate(priorities):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message="Test",
                priority=priority
            )
            alert.metadata["symbol"] = "AAPL"
            alert.metadata["allow_consolidation"] = True
            alerts.append(alert)
            self.engine.process_alert(alert)
        
        # Force flush and check priority
        consolidated = self.engine.force_flush_user("user123")
        
        assert consolidated is not None
        assert consolidated.priority == AlertPriority.HIGH  # Highest priority wins
    
    def test_consolidation_by_group(self):
        """Test consolidation using explicit groups"""
        alerts = []
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"Alert {i}",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["consolidation_group"] = "price_alerts"
            alert.metadata["allow_consolidation"] = True
            alerts.append(alert)
            self.engine.process_alert(alert)
        
        consolidated = self.engine.force_flush_user("user123")
        
        assert consolidated is not None
        assert "price_alerts" in consolidated.consolidation_group
    
    def test_force_flush_all(self):
        """Test forcing flush for all users"""
        # Add alerts for multiple users
        for user_id in ["user1", "user2", "user3"]:
            alert = TriggeredAlert(
                rule_id=f"rule_{user_id}",
                user_id=user_id,
                title="Test",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["allow_consolidation"] = True
            self.engine.process_alert(alert)
        
        results = self.engine.force_flush_all()
        
        assert len(results) == 3
    
    def test_consolidation_summary_creation(self):
        """Test creation of consolidation summary"""
        alerts = []
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title=f"AAPL Alert {i}",
                message=f"Price alert {i}",
                priority=AlertPriority.MEDIUM,
                trigger_values={"price_above": 150.0 + i}
            )
            alert.metadata["symbol"] = "AAPL"
            alert.metadata["allow_consolidation"] = True
            alerts.append(alert)
            self.engine.process_alert(alert)
        
        consolidated = self.engine.force_flush_user("user123")
        
        assert consolidated is not None
        assert "AAPL" in consolidated.title
        assert len(consolidated.summary) > 0
    
    def test_clear_user_pending(self):
        """Test clearing pending alerts"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test",
            priority=AlertPriority.MEDIUM
        )
        alert.metadata["allow_consolidation"] = True
        
        self.engine.process_alert(alert)
        assert self.engine.get_pending_count("user123") == 1
        
        self.engine.clear_user_pending("user123")
        assert self.engine.get_pending_count("user123") == 0
    
    def test_consolidation_stats(self):
        """Test consolidation statistics"""
        # Add some alerts
        for i in range(5):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["allow_consolidation"] = True
            self.engine.process_alert(alert)
        
        stats = self.engine.get_consolidation_stats()
        
        assert stats["total_pending_alerts"] == 5
        assert stats["users_with_pending"] == 1
        assert stats["consolidation_window_minutes"] == 5
    
    def test_multi_symbol_consolidation(self):
        """Test consolidation with multiple symbols"""
        symbols = ["AAPL", "SPY", "NVDA"]
        
        for i, symbol in enumerate(symbols):
            for j in range(2):  # 2 alerts per symbol
                alert = TriggeredAlert(
                    rule_id=f"rule{i}_{j}",
                    user_id="user123",
                    title=f"{symbol} Alert",
                    message="Test",
                    priority=AlertPriority.MEDIUM
                )
                alert.metadata["symbol"] = symbol
                alert.metadata["allow_consolidation"] = True
                self.engine.process_alert(alert)
        
        consolidated = self.engine.force_flush_user("user123")
        
        assert consolidated is not None
        assert consolidated.alert_count == 6
        # Title should mention multiple symbols
        assert "symbols" in consolidated.title.lower() or any(
            sym in consolidated.title for sym in symbols
        )
    
    def test_max_alerts_trigger_flush(self):
        """Test that max alerts triggers flush"""
        # Add 10 alerts (threshold for auto-flush)
        for i in range(10):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["allow_consolidation"] = True
            
            consolidated = self.engine.process_alert(alert)
            
            # Last alert should trigger flush
            if i == 9:
                assert consolidated is not None
    
    def test_related_alerts_linking(self):
        """Test that related alerts are linked"""
        alerts = []
        for i in range(3):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.MEDIUM
            )
            alert.metadata["symbol"] = "AAPL"
            alert.metadata["allow_consolidation"] = True
            alerts.append(alert)
            self.engine.process_alert(alert)
        
        consolidated = self.engine.force_flush_user("user123")
        
        # Check that alerts are linked
        for alert in consolidated.alerts:
            assert alert.is_consolidated is True
            assert alert.consolidated_alert_id == consolidated.consolidated_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
