"""
Unit tests for VS-9 Alert Engine
"""

import pytest
from datetime import datetime, timedelta
from src.alert_engine import AlertEngine
from src.models import (
    AlertRule, AlertCondition, MarketData, Position,
    ConditionType, AlertPriority, AlertStatus, MarketSession
)


class TestAlertEngine:
    """Test AlertEngine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = AlertEngine()
    
    def test_add_rule(self):
        """Test adding a rule to engine"""
        rule = AlertRule(
            user_id="user123",
            name="Test Rule",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                )
            ]
        )
        
        self.engine.add_rule(rule)
        assert rule.rule_id in self.engine.active_rules
        assert self.engine.get_active_rules_count() == 1
    
    def test_remove_rule(self):
        """Test removing a rule"""
        rule = AlertRule(
            user_id="user123",
            name="Test Rule",
            conditions=[]
        )
        
        self.engine.add_rule(rule)
        assert self.engine.get_active_rules_count() == 1
        
        self.engine.remove_rule(rule.rule_id)
        assert self.engine.get_active_rules_count() == 0
    
    def test_price_above_condition(self):
        """Test PRICE_ABOVE condition evaluation"""
        rule = AlertRule(
            user_id="user123",
            name="Price Above",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                )
            ],
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        # Test with price above threshold
        market_data = MarketData(
            symbol="AAPL",
            price=155.0,
            bid=154.95,
            ask=155.05,
            volume=1000000
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
        assert alerts[0].rule_id == rule.rule_id
    
    def test_price_below_condition(self):
        """Test PRICE_BELOW condition evaluation"""
        rule = AlertRule(
            user_id="user123",
            name="Price Below",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_BELOW,
                    symbol="SPY",
                    threshold=400.0
                )
            ],
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="SPY",
            price=395.0,
            bid=394.95,
            ask=395.05,
            volume=5000000
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
    
    def test_volume_condition(self):
        """Test VOLUME_ABOVE condition"""
        rule = AlertRule(
            user_id="user123",
            name="Volume Alert",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.VOLUME_ABOVE,
                    symbol="TSLA",
                    threshold=2.0  # 2x normal volume
                )
            ],
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="TSLA",
            price=200.0,
            bid=199.95,
            ask=200.05,
            volume=10000000,
            volume_ratio=2.5
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
    
    def test_iv_conditions(self):
        """Test implied volatility conditions"""
        rule = AlertRule(
            user_id="user123",
            name="IV Alert",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.IV_ABOVE,
                    symbol="NVDA",
                    threshold=0.50
                )
            ],
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="NVDA",
            price=500.0,
            bid=499.95,
            ask=500.05,
            volume=1000000,
            implied_volatility=0.60
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
    
    def test_multi_condition_and_logic(self):
        """Test multiple conditions with AND logic"""
        rule = AlertRule(
            user_id="user123",
            name="Multi Condition",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                ),
                AlertCondition(
                    condition_type=ConditionType.VOLUME_ABOVE,
                    symbol="AAPL",
                    threshold=2.0
                )
            ],
            logic="AND",
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        # Both conditions met
        market_data = MarketData(
            symbol="AAPL",
            price=155.0,
            bid=154.95,
            ask=155.05,
            volume=10000000,
            volume_ratio=2.5
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
        
        # Only one condition met - should not trigger
        self.engine.clear_cooldowns()
        market_data.price = 145.0
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 0
    
    def test_multi_condition_or_logic(self):
        """Test multiple conditions with OR logic"""
        rule = AlertRule(
            user_id="user123",
            name="Multi Condition OR",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="SPY",
                    threshold=500.0
                ),
                AlertCondition(
                    condition_type=ConditionType.VOLUME_ABOVE,
                    symbol="SPY",
                    threshold=3.0
                )
            ],
            logic="OR",
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        # Only price condition met
        market_data = MarketData(
            symbol="SPY",
            price=505.0,
            bid=504.95,
            ask=505.05,
            volume=1000000,
            volume_ratio=1.0
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
    
    def test_cooldown_period(self):
        """Test alert cooldown functionality"""
        rule = AlertRule(
            user_id="user123",
            name="Cooldown Test",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                )
            ],
            cooldown_minutes=5,
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="AAPL",
            price=155.0,
            bid=154.95,
            ask=155.05,
            volume=1000000
        )
        
        # First trigger
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1
        
        # Immediate re-evaluation should be blocked by cooldown
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 0
    
    def test_market_hours_filter(self):
        """Test market hours filtering"""
        rule = AlertRule(
            user_id="user123",
            name="Market Hours Only",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="SPY",
                    threshold=400.0
                )
            ],
            market_hours_only=True,
            allowed_sessions=[MarketSession.REGULAR]
        )
        
        self.engine.add_rule(rule)
        
        # Pre-market data
        market_data = MarketData(
            symbol="SPY",
            price=405.0,
            bid=404.95,
            ask=405.05,
            volume=100000,
            session=MarketSession.PRE_MARKET
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 0  # Should not trigger
        
        # Regular hours
        market_data.session = MarketSession.REGULAR
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1  # Should trigger
    
    def test_rule_expiration(self):
        """Test rule expiration"""
        expired_time = datetime.utcnow() - timedelta(days=1)
        
        rule = AlertRule(
            user_id="user123",
            name="Expired Rule",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                )
            ],
            expires_at=expired_time,
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="AAPL",
            price=155.0,
            bid=154.95,
            ask=155.05,
            volume=1000000
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 0  # Expired rule should not trigger
        assert rule.status == AlertStatus.EXPIRED
    
    def test_get_rules_by_user(self):
        """Test getting rules by user"""
        rule1 = AlertRule(user_id="user1", name="Rule 1", conditions=[])
        rule2 = AlertRule(user_id="user2", name="Rule 2", conditions=[])
        rule3 = AlertRule(user_id="user1", name="Rule 3", conditions=[])
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        self.engine.add_rule(rule3)
        
        user1_rules = self.engine.get_rules_by_user("user1")
        assert len(user1_rules) == 2
        
        user2_rules = self.engine.get_rules_by_user("user2")
        assert len(user2_rules) == 1
    
    def test_get_rules_by_symbol(self):
        """Test getting rules by symbol"""
        rule1 = AlertRule(
            user_id="user1",
            name="AAPL Rule",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="AAPL",
                    threshold=150.0
                )
            ]
        )
        
        rule2 = AlertRule(
            user_id="user1",
            name="SPY Rule",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.PRICE_ABOVE,
                    symbol="SPY",
                    threshold=400.0
                )
            ]
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        aapl_rules = self.engine.get_rules_by_symbol("AAPL")
        assert len(aapl_rules) == 1
        assert aapl_rules[0].name == "AAPL Rule"
    
    def test_engine_stats(self):
        """Test engine statistics"""
        rule1 = AlertRule(
            user_id="user1",
            name="Rule 1",
            conditions=[],
            priority=AlertPriority.HIGH
        )
        rule2 = AlertRule(
            user_id="user1",
            name="Rule 2",
            conditions=[],
            priority=AlertPriority.LOW
        )
        
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        stats = self.engine.get_engine_stats()
        assert stats["total_active_rules"] == 2
        assert "high" in stats["rules_by_priority"]
        assert "low" in stats["rules_by_priority"]
    
    def test_flow_conditions(self):
        """Test flow-based conditions"""
        rule = AlertRule(
            user_id="user123",
            name="Bullish Flow",
            conditions=[
                AlertCondition(
                    condition_type=ConditionType.FLOW_BULLISH,
                    symbol="AAPL",
                    threshold=0.5  # Put/Call ratio < 0.5
                )
            ],
            market_hours_only=False
        )
        
        self.engine.add_rule(rule)
        
        market_data = MarketData(
            symbol="AAPL",
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=1000000,
            put_call_ratio=0.3
        )
        
        alerts = self.engine.evaluate_market_data(market_data)
        assert len(alerts) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
