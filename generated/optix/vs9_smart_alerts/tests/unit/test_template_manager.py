"""
Unit tests for VS-9 Template Manager
"""

import pytest
from src.template_manager import TemplateManager
from src.models import AlertPriority, ConditionType


class TestTemplateManager:
    """Test TemplateManager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = TemplateManager()
    
    def test_initialization(self):
        """Test manager initializes with default templates"""
        templates = self.manager.get_all_templates()
        assert len(templates) >= 10  # Should have at least 10 default templates
    
    def test_get_template_by_id(self):
        """Test retrieving template by ID"""
        templates = self.manager.get_all_templates()
        template_id = templates[0].template_id
        
        retrieved = self.manager.get_template(template_id)
        assert retrieved is not None
        assert retrieved.template_id == template_id
    
    def test_get_templates_by_category(self):
        """Test filtering templates by category"""
        price_templates = self.manager.get_templates_by_category("price_action")
        assert len(price_templates) > 0
        assert all(t.category == "price_action" for t in price_templates)
    
    def test_get_templates_by_tag(self):
        """Test filtering templates by tag"""
        iv_templates = self.manager.get_templates_by_tag("iv")
        assert len(iv_templates) > 0
        assert all("iv" in t.tags for t in iv_templates)
    
    def test_search_templates(self):
        """Test template search"""
        results = self.manager.search_templates("volatility")
        assert len(results) > 0
        
        # Check that search matches name, description, or tags
        for template in results:
            assert ("volatility" in template.name.lower() or
                   "volatility" in template.description.lower() or
                   any("volatility" in tag.lower() for tag in template.tags))
    
    def test_create_alert_from_template(self):
        """Test creating alert from template"""
        templates = self.manager.get_all_templates()
        template_id = templates[0].template_id
        
        alert_rule = self.manager.create_alert_from_template(
            template_id=template_id,
            user_id="user123",
            symbol="AAPL"
        )
        
        assert alert_rule is not None
        assert alert_rule.user_id == "user123"
        assert alert_rule.template_id == template_id
        assert len(alert_rule.conditions) > 0
        assert all(c.symbol == "AAPL" for c in alert_rule.conditions)
    
    def test_create_with_overrides(self):
        """Test creating alert with parameter overrides"""
        templates = self.manager.get_all_templates()
        template_id = templates[0].template_id
        
        alert_rule = self.manager.create_alert_from_template(
            template_id=template_id,
            user_id="user123",
            symbol="SPY",
            overrides={
                "name": "Custom Name",
                "priority": AlertPriority.URGENT,
                "cooldown_minutes": 30
            }
        )
        
        assert alert_rule.name == "Custom Name"
        assert alert_rule.priority == AlertPriority.URGENT
        assert alert_rule.cooldown_minutes == 30
    
    def test_template_usage_tracking(self):
        """Test that template usage is tracked"""
        templates = self.manager.get_all_templates()
        template = templates[0]
        initial_count = template.usage_count
        
        self.manager.create_alert_from_template(
            template_id=template.template_id,
            user_id="user123",
            symbol="AAPL"
        )
        
        assert template.usage_count == initial_count + 1
    
    def test_get_popular_templates(self):
        """Test getting popular templates"""
        # Use some templates
        templates = self.manager.get_all_templates()[:3]
        for i, template in enumerate(templates):
            for _ in range(i + 1):  # Use each template different number of times
                self.manager.create_alert_from_template(
                    template.template_id,
                    "user123",
                    "AAPL"
                )
        
        popular = self.manager.get_popular_templates(limit=3)
        assert len(popular) <= 3
        # Check sorted by usage (descending)
        for i in range(len(popular) - 1):
            assert popular[i].usage_count >= popular[i + 1].usage_count
    
    def test_get_categories(self):
        """Test getting all categories"""
        categories = self.manager.get_categories()
        assert len(categories) > 0
        assert isinstance(categories, list)
        assert all(isinstance(c, str) for c in categories)
    
    def test_get_all_tags(self):
        """Test getting all tags"""
        tags = self.manager.get_all_tags()
        assert len(tags) > 0
        assert isinstance(tags, list)
        assert all(isinstance(t, str) for t in tags)
    
    def test_get_template_stats(self):
        """Test template statistics"""
        stats = self.manager.get_template_stats()
        
        assert "total_templates" in stats
        assert "by_category" in stats
        assert "categories" in stats
        assert stats["total_templates"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
