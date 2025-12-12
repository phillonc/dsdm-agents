"""
Unit tests for VS-9 Smart Alerts data models
"""

import pytest
from datetime import datetime, timedelta
from src.models import (
    AlertRule, AlertCondition, TriggeredAlert, AlertPriority,
    AlertStatus, ConditionType, DeliveryChannel, MarketSession,
    DeliveryPreference, AlertTemplate, Position, MarketData,
    create_alert_from_template
)


class TestAlertCondition:
    """Test AlertCondition model"""
    
    def test_create_alert_condition(self):
        """Test creating an alert condition"""
        condition = AlertCondition(
            condition_type=ConditionType.PRICE_ABOVE,
            symbol="AAPL",
            threshold=150.0
        )
        
        assert condition.symbol == "AAPL"
        assert condition.threshold == 150.0
        assert condition.condition_type == ConditionType.PRICE_ABOVE
        assert condition.condition_id is not None
    
    def test_condition_with_parameters(self):
        """Test condition with additional parameters"""
        condition = AlertCondition(
            condition_type=ConditionType.VOLUME_ABOVE,
            symbol="TSLA",
            threshold=2.0,
            timeframe="15m",
            parameters={"lookback_days": 30}
        )
        
        assert condition.timeframe == "15m"
        assert condition.parameters["lookback_days"] == 30


class TestAlertRule:
    """Test AlertRule model"""
    
    def test_create_alert_rule(self):
        """Test creating an alert rule"""
        condition = AlertCondition(
            condition_type=ConditionType.PRICE_ABOVE,
            symbol="SPY",
            threshold=400.0
        )
        
        rule = AlertRule(
            user_id="user123",
            name="SPY Breakout",
            description="Alert when SPY breaks $400",
            conditions=[condition],
            priority=AlertPriority.HIGH
        )
        
        assert rule.user_id == "user123"
        assert rule.name == "SPY Breakout"
        assert len(rule.conditions) == 1
        assert rule.priority == AlertPriority.HIGH
        assert rule.status == AlertStatus.ACTIVE
    
    def test_multi_condition_rule(self):
        """Test rule with multiple conditions"""
        conditions = [
            AlertCondition(
                condition_type=ConditionType.PRICE_ABOVE,
                symbol="NVDA",
                threshold=500.0
            ),
            AlertCondition(
                condition_type=ConditionType.VOLUME_ABOVE,
                symbol="NVDA",
                threshold=2.0
            )
        ]
        
        rule = AlertRule(
            user_id="user123",
            name="NVDA Momentum",
            conditions=conditions,
            logic="AND"
        )
        
        assert len(rule.conditions) == 2
        assert rule.logic == "AND"
    
    def test_rule_expiration(self):
        """Test rule with expiration"""
        future_time = datetime.utcnow() + timedelta(days=7)
        
        rule = AlertRule(
            user_id="user123",
            name="Temporary Alert",
            conditions=[],
            expires_at=future_time
        )
        
        assert rule.expires_at == future_time
    
    def test_position_aware_rule(self):
        """Test position-aware rule"""
        rule = AlertRule(
            user_id="user123",
            name="Position Alert",
            conditions=[],
            position_aware=True,
            relevant_positions=["pos1", "pos2"]
        )
        
        assert rule.position_aware is True
        assert len(rule.relevant_positions) == 2


class TestTriggeredAlert:
    """Test TriggeredAlert model"""
    
    def test_create_triggered_alert(self):
        """Test creating a triggered alert"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="SPY Alert",
            message="SPY broke $400",
            priority=AlertPriority.HIGH
        )
        
        assert alert.rule_id == "rule123"
        assert alert.user_id == "user123"
        assert alert.title == "SPY Alert"
        assert alert.status == AlertStatus.TRIGGERED
    
    def test_alert_with_trigger_values(self):
        """Test alert with trigger values"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Alert",
            message="Test",
            trigger_values={
                "price_above": 400.50,
                "volume_ratio": 2.5
            }
        )
        
        assert "price_above" in alert.trigger_values
        assert alert.trigger_values["volume_ratio"] == 2.5
    
    def test_alert_user_action(self):
        """Test recording user action on alert"""
        alert = TriggeredAlert(
            rule_id="rule123",
            user_id="user123",
            title="Alert",
            message="Test"
        )
        
        alert.user_acted = True
        alert.action_type = "opened_position"
        alert.action_timestamp = datetime.utcnow()
        
        assert alert.user_acted is True
        assert alert.action_type == "opened_position"
        assert alert.action_timestamp is not None


class TestDeliveryPreference:
    """Test DeliveryPreference model"""
    
    def test_default_preferences(self):
        """Test default delivery preferences"""
        prefs = DeliveryPreference(user_id="user123")
        
        assert DeliveryChannel.IN_APP in prefs.enabled_channels
        assert DeliveryChannel.PUSH in prefs.enabled_channels
        assert prefs.enable_consolidation is True
        assert prefs.max_alerts_per_hour == 50
    
    def test_custom_preferences(self):
        """Test custom delivery preferences"""
        prefs = DeliveryPreference(
            user_id="user123",
            enabled_channels=[DeliveryChannel.EMAIL, DeliveryChannel.SMS],
            email="user@example.com",
            phone="+1234567890",
            quiet_hours_start="22:00",
            quiet_hours_end="07:00"
        )
        
        assert prefs.email == "user@example.com"
        assert prefs.phone == "+1234567890"
        assert prefs.quiet_hours_start == "22:00"
    
    def test_priority_channel_mapping(self):
        """Test priority to channel mapping"""
        prefs = DeliveryPreference(user_id="user123")
        
        # Check default mappings
        assert DeliveryChannel.IN_APP in prefs.priority_channel_map[AlertPriority.LOW]
        assert DeliveryChannel.SMS in prefs.priority_channel_map[AlertPriority.URGENT]


class TestAlertTemplate:
    """Test AlertTemplate model"""
    
    def test_create_template(self):
        """Test creating an alert template"""
        template = AlertTemplate(
            name="Price Breakout",
            description="Alert on price breakout",
            category="price_action",
            condition_templates=[
                {
                    "condition_type": "price_above",
                    "threshold": 0.0,
                    "timeframe": "5m"
                }
            ]
        )
        
        assert template.name == "Price Breakout"
        assert len(template.condition_templates) == 1
        assert template.usage_count == 0
    
    def test_template_with_tags(self):
        """Test template with tags"""
        template = AlertTemplate(
            name="Volatility Spike",
            description="IV spike alert",
            category="volatility",
            tags=["iv", "volatility", "options"]
        )
        
        assert "iv" in template.tags
        assert len(template.tags) == 3


class TestCreateAlertFromTemplate:
    """Test creating alerts from templates"""
    
    def test_create_from_template(self):
        """Test creating alert rule from template"""
        template = AlertTemplate(
            name="Test Template",
            description="Test",
            category="test",
            condition_templates=[
                {
                    "condition_type": "price_above",
                    "threshold": 100.0,
                    "timeframe": "5m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.HIGH
        )
        
        alert_rule = create_alert_from_template(
            template=template,
            user_id="user123",
            symbol="AAPL"
        )
        
        assert alert_rule.user_id == "user123"
        assert len(alert_rule.conditions) == 1
        assert alert_rule.conditions[0].symbol == "AAPL"
        assert alert_rule.template_id == template.template_id
        assert alert_rule.priority == AlertPriority.HIGH
    
    def test_create_with_overrides(self):
        """Test creating from template with overrides"""
        template = AlertTemplate(
            name="Test Template",
            description="Test",
            category="test",
            condition_templates=[],
            default_priority=AlertPriority.MEDIUM
        )
        
        alert_rule = create_alert_from_template(
            template=template,
            user_id="user123",
            symbol="SPY",
            overrides={
                "name": "Custom Name",
                "priority": AlertPriority.HIGH,
                "cooldown_minutes": 30
            }
        )
        
        assert alert_rule.name == "Custom Name"
        assert alert_rule.priority == AlertPriority.HIGH
        assert alert_rule.cooldown_minutes == 30


class TestPosition:
    """Test Position model"""
    
    def test_create_position(self):
        """Test creating a position"""
        position = Position(
            user_id="user123",
            symbol="AAPL",
            quantity=100,
            entry_price=150.0,
            current_price=155.0,
            position_type="long"
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.position_type == "long"
    
    def test_option_position(self):
        """Test options position"""
        expiration = datetime.utcnow() + timedelta(days=30)
        
        position = Position(
            user_id="user123",
            symbol="SPY",
            quantity=10,
            entry_price=5.0,
            current_price=6.0,
            position_type="option",
            option_type="call",
            strike=400.0,
            expiration=expiration,
            delta=0.65
        )
        
        assert position.option_type == "call"
        assert position.strike == 400.0
        assert position.delta == 0.65


class TestMarketData:
    """Test MarketData model"""
    
    def test_create_market_data(self):
        """Test creating market data"""
        data = MarketData(
            symbol="AAPL",
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=1000000,
            price_change_percent=2.5
        )
        
        assert data.symbol == "AAPL"
        assert data.price == 150.0
        assert data.price_change_percent == 2.5
    
    def test_market_data_with_options(self):
        """Test market data with options data"""
        data = MarketData(
            symbol="SPY",
            price=400.0,
            bid=399.95,
            ask=400.05,
            volume=5000000,
            implied_volatility=0.15,
            iv_rank=45.0,
            put_call_ratio=0.8,
            unusual_activity_score=3.5
        )
        
        assert data.implied_volatility == 0.15
        assert data.iv_rank == 45.0
        assert data.put_call_ratio == 0.8
        assert data.unusual_activity_score == 3.5
    
    def test_market_session(self):
        """Test market session"""
        data = MarketData(
            symbol="AAPL",
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=100000,
            session=MarketSession.PRE_MARKET,
            is_trading_hours=False
        )
        
        assert data.session == MarketSession.PRE_MARKET
        assert data.is_trading_hours is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
