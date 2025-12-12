"""
Unit tests for VS-9 Learning Engine
"""

import pytest
from datetime import datetime, timedelta
from src.learning_engine import LearningEngine
from src.models import (
    AlertRule, TriggeredAlert, AlertPriority, ConditionType, MarketSession
)


class TestLearningEngine:
    """Test LearningEngine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = LearningEngine(learning_rate=0.1)
    
    def test_record_user_action(self):
        """Test recording user actions"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test Alert",
            message="Test",
            priority=AlertPriority.HIGH,
            trigger_values={"price_above": 150.0}
        )
        alert.metadata["symbol"] = "AAPL"
        
        self.engine.record_user_action(
            user_id="user123",
            alert=alert,
            action_type="opened_position"
        )
        
        assert "user123" in self.engine.action_history
        assert len(self.engine.action_history["user123"]) == 1
        assert self.engine.action_history["user123"][0]["action_type"] == "opened_position"
        assert self.engine.action_history["user123"][0]["is_positive"] is True
    
    def test_record_negative_action(self):
        """Test recording negative actions (snoozed/dismissed)"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test"
        )
        
        self.engine.record_user_action(
            user_id="user123",
            alert=alert,
            action_type="dismissed"
        )
        
        action = self.engine.action_history["user123"][0]
        assert action["is_positive"] is False
    
    def test_update_rule_relevance_insufficient_data(self):
        """Test relevance update with insufficient data"""
        rule = AlertRule(
            user_id="user123",
            name="Test Rule",
            conditions=[],
            relevance_score=0.5
        )
        
        # With no actions, score should remain unchanged
        new_score = self.engine.update_rule_relevance(rule, "user123")
        assert new_score == 0.5
    
    def test_update_rule_relevance_with_data(self):
        """Test relevance update with sufficient data"""
        rule = AlertRule(
            rule_id="rule123",
            user_id="user123",
            name="Test Rule",
            conditions=[],
            relevance_score=0.5
        )
        
        # Record multiple positive actions
        for i in range(15):
            alert = TriggeredAlert(
                rule_id="rule123",
                user_id="user123",
                title="Test",
                message="Test"
            )
            action_type = "opened_position" if i < 12 else "dismissed"
            self.engine.record_user_action("user123", alert, action_type)
        
        # Update relevance
        new_score = self.engine.update_rule_relevance(rule, "user123")
        
        # Score should increase (80% action rate)
        assert new_score > 0.5
        assert rule.relevance_score > 0.5
    
    def test_learn_user_profile_insufficient_data(self):
        """Test profile learning with insufficient data"""
        profile = self.engine.learn_user_profile("user123")
        
        assert profile.user_id == "user123"
        assert len(profile.most_acted_conditions) == 0
        assert profile.action_rate == 0.0
    
    def test_learn_user_profile_with_data(self):
        """Test profile learning with sufficient data"""
        # Record 20 actions with patterns
        for i in range(20):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.HIGH if i < 15 else AlertPriority.LOW,
                trigger_values={
                    "price_above": 150.0,
                    "volume_above": 2.0
                }
            )
            alert.metadata["symbol"] = "AAPL" if i < 12 else "SPY"
            
            action_type = "opened_position" if i < 16 else "dismissed"
            self.engine.record_user_action("user123", alert, action_type)
        
        profile = self.engine.learn_user_profile("user123")
        
        assert profile.action_rate == 0.8  # 16/20
        assert len(profile.most_acted_conditions) > 0
        assert AlertPriority.HIGH in profile.preferred_priorities
        assert "AAPL" in profile.symbol_interests
    
    def test_predict_alert_relevance_new_user(self):
        """Test relevance prediction for new user"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Test",
            message="Test"
        )
        
        score = self.engine.predict_alert_relevance(alert, "new_user")
        assert score == 0.5  # Default score
    
    def test_predict_alert_relevance_with_profile(self):
        """Test relevance prediction with learned profile"""
        # Build profile with price_above preference
        for i in range(15):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.HIGH,
                trigger_values={"price_above": 150.0}
            )
            alert.metadata["symbol"] = "AAPL"
            self.engine.record_user_action("user123", alert, "opened_position")
        
        self.engine.learn_user_profile("user123")
        
        # Test prediction for similar alert
        test_alert = TriggeredAlert(
            rule_id="test_rule",
            user_id="user123",
            title="Test",
            message="Test",
            priority=AlertPriority.HIGH,
            trigger_values={"price_above": 155.0}
        )
        test_alert.metadata["symbol"] = "AAPL"
        
        score = self.engine.predict_alert_relevance(test_alert, "user123")
        assert score > 0.5  # Should be higher than baseline
    
    def test_get_alert_recommendations(self):
        """Test getting alert recommendations"""
        # Build profile
        for i in range(15):
            alert = TriggeredAlert(
                rule_id=f"rule{i}",
                user_id="user123",
                title="Test",
                message="Test",
                trigger_values={
                    "price_above": 150.0,
                    "volume_above": 2.0
                }
            )
            self.engine.record_user_action("user123", alert, "opened_position")
        
        self.engine.learn_user_profile("user123")
        
        recommendations = self.engine.get_alert_recommendations("user123", top_n=3)
        
        assert len(recommendations) <= 3
        assert all("condition_type" in rec for rec in recommendations)
        assert all("relevance_score" in rec for rec in recommendations)
    
    def test_generate_analytics(self):
        """Test analytics generation"""
        # Record various actions
        for i in range(20):
            alert = TriggeredAlert(
                rule_id="rule123",
                user_id="user123",
                title="Test",
                message="Test",
                priority=AlertPriority.HIGH,
                trigger_values={"price_above": 150.0}
            )
            
            action_type = "opened_position" if i < 15 else "dismissed"
            self.engine.record_user_action("user123", alert, action_type)
        
        analytics = self.engine.generate_analytics("user123", days=30)
        
        assert analytics.user_id == "user123"
        assert analytics.total_triggers == 20
        assert analytics.acted_upon_count == 15
        assert analytics.action_rate == 0.75
        assert analytics.dismissed_count == 5
    
    def test_generate_analytics_by_rule(self):
        """Test analytics for specific rule"""
        # Record actions for different rules
        for rule_id in ["rule1", "rule2"]:
            for i in range(10):
                alert = TriggeredAlert(
                    rule_id=rule_id,
                    user_id="user123",
                    title="Test",
                    message="Test"
                )
                self.engine.record_user_action("user123", alert, "opened_position")
        
        # Get analytics for specific rule
        analytics = self.engine.generate_analytics("user123", rule_id="rule1", days=30)
        
        assert analytics.rule_id == "rule1"
        assert analytics.total_triggers == 10
    
    def test_calculate_symbol_interests(self):
        """Test symbol interest calculation"""
        # Record actions with different symbols
        symbols_actions = [
            ("AAPL", "opened_position", 10),
            ("SPY", "dismissed", 5),
            ("NVDA", "opened_position", 8)
        ]
        
        for symbol, action, count in symbols_actions:
            for i in range(count):
                alert = TriggeredAlert(
                    rule_id=f"rule{i}",
                    user_id="user123",
                    title="Test",
                    message="Test"
                )
                alert.metadata["symbol"] = symbol
                self.engine.record_user_action("user123", alert, action)
        
        profile = self.engine.learn_user_profile("user123")
        
        # AAPL should have highest interest (100% action rate)
        assert "AAPL" in profile.symbol_interests
        assert profile.symbol_interests["AAPL"] > profile.symbol_interests["SPY"]
    
    def test_active_hours_identification(self):
        """Test identification of active trading hours"""
        # Record actions at specific hours
        for hour in [9, 10, 14, 15]:
            for i in range(5):
                alert = TriggeredAlert(
                    rule_id=f"rule{i}",
                    user_id="user123",
                    title="Test",
                    message="Test"
                )
                
                # Set timestamp to specific hour
                action_timestamp = datetime.utcnow().replace(hour=hour, minute=0)
                self.engine.record_user_action(
                    "user123",
                    alert,
                    "opened_position",
                    action_timestamp
                )
        
        profile = self.engine.learn_user_profile("user123")
        
        assert len(profile.active_trading_hours) > 0
    
    def test_learning_stats(self):
        """Test learning engine statistics"""
        # Create some data
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user1",
            title="Test",
            message="Test"
        )
        self.engine.record_user_action("user1", alert, "opened_position")
        
        alert2 = TriggeredAlert(
            rule_id="rule456",
            user_id="user2",
            title="Test",
            message="Test"
        )
        self.engine.record_user_action("user2", alert2, "dismissed")
        
        stats = self.engine.get_learning_stats()
        
        assert stats["total_actions_recorded"] == 2
        assert stats["learning_rate"] == 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
