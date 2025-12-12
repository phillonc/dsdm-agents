"""
VS-9 Smart Alerts Ecosystem - Template Manager
OPTIX Trading Platform

Manages alert templates for common trading scenarios.
Provides pre-configured templates that users can quickly apply.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .models import (
    AlertTemplate, AlertRule, ConditionType, AlertPriority,
    MarketSession, create_alert_from_template
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manager for alert templates. Provides pre-built templates
    for common trading scenarios and allows custom template creation.
    """
    
    def __init__(self):
        self.templates: Dict[str, AlertTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self) -> None:
        """Initialize default alert templates"""
        
        # Price Breakout Template
        self.add_template(AlertTemplate(
            name="Price Breakout Alert",
            description="Alert when price breaks above resistance or below support",
            category="price_action",
            condition_templates=[
                {
                    "condition_type": "price_above",
                    "threshold": 0.0,  # User sets this
                    "timeframe": "5m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.HIGH,
            recommended_cooldown=15,
            tags=["price", "breakout", "momentum"]
        ))
        
        # Volatility Spike Template
        self.add_template(AlertTemplate(
            name="Volatility Spike",
            description="Alert when implied volatility spikes significantly",
            category="volatility",
            condition_templates=[
                {
                    "condition_type": "iv_above",
                    "threshold": 0.0,
                    "timeframe": "1h"
                },
                {
                    "condition_type": "iv_change",
                    "threshold": 20.0,  # 20% IV increase
                    "timeframe": "1h"
                }
            ],
            logic="OR",
            default_priority=AlertPriority.HIGH,
            recommended_cooldown=30,
            tags=["volatility", "iv", "options"]
        ))
        
        # Unusual Options Activity Template
        self.add_template(AlertTemplate(
            name="Unusual Options Activity",
            description="Alert on unusual options flow and volume",
            category="flow",
            condition_templates=[
                {
                    "condition_type": "unusual_activity",
                    "threshold": 3.0,  # 3x normal activity
                    "timeframe": "15m"
                },
                {
                    "condition_type": "volume_above",
                    "threshold": 2.0,  # 2x average volume
                    "timeframe": "15m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.HIGH,
            recommended_cooldown=20,
            tags=["flow", "volume", "unusual_activity"]
        ))
        
        # Bullish Flow Template
        self.add_template(AlertTemplate(
            name="Strong Bullish Flow",
            description="Alert on strong bullish options flow",
            category="flow",
            condition_templates=[
                {
                    "condition_type": "flow_bullish",
                    "threshold": 0.5,  # Put/Call ratio < 0.5
                    "timeframe": "30m"
                },
                {
                    "condition_type": "volume_above",
                    "threshold": 1.5,
                    "timeframe": "30m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.MEDIUM,
            recommended_cooldown=30,
            tags=["flow", "bullish", "sentiment"]
        ))
        
        # Bearish Flow Template
        self.add_template(AlertTemplate(
            name="Strong Bearish Flow",
            description="Alert on strong bearish options flow",
            category="flow",
            condition_templates=[
                {
                    "condition_type": "flow_bearish",
                    "threshold": 2.0,  # Put/Call ratio > 2.0
                    "timeframe": "30m"
                },
                {
                    "condition_type": "volume_above",
                    "threshold": 1.5,
                    "timeframe": "30m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.MEDIUM,
            recommended_cooldown=30,
            tags=["flow", "bearish", "sentiment"]
        ))
        
        # Position P&L Alert Template
        self.add_template(AlertTemplate(
            name="Position P&L Alert",
            description="Alert when position profit or loss reaches threshold",
            category="position_management",
            condition_templates=[
                {
                    "condition_type": "position_pnl",
                    "threshold": 10.0,  # 10% P&L change
                    "timeframe": None
                }
            ],
            logic="AND",
            default_priority=AlertPriority.HIGH,
            recommended_cooldown=10,
            tags=["position", "pnl", "risk_management"]
        ))
        
        # Expiration Warning Template
        self.add_template(AlertTemplate(
            name="Expiration Warning",
            description="Alert when options are approaching expiration",
            category="position_management",
            condition_templates=[
                {
                    "condition_type": "expiration_approaching",
                    "threshold": 3.0,  # 3 days to expiration
                    "timeframe": None
                }
            ],
            logic="AND",
            default_priority=AlertPriority.URGENT,
            recommended_cooldown=1440,  # Once per day
            tags=["expiration", "position", "risk_management"]
        ))
        
        # Gamma Exposure Template
        self.add_template(AlertTemplate(
            name="High Gamma Exposure",
            description="Alert on high gamma exposure levels",
            category="greeks",
            condition_templates=[
                {
                    "condition_type": "gamma_exposure",
                    "threshold": 1000.0,  # User adjusts
                    "timeframe": "1h"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.MEDIUM,
            recommended_cooldown=60,
            tags=["gamma", "greeks", "risk"]
        ))
        
        # Wide Spread Alert Template
        self.add_template(AlertTemplate(
            name="Wide Spread Alert",
            description="Alert when bid-ask spread becomes too wide",
            category="liquidity",
            condition_templates=[
                {
                    "condition_type": "spread_width",
                    "threshold": 5.0,  # 5% spread
                    "timeframe": None
                }
            ],
            logic="AND",
            default_priority=AlertPriority.LOW,
            recommended_cooldown=30,
            tags=["spread", "liquidity", "execution"]
        ))
        
        # Momentum + Volume Template
        self.add_template(AlertTemplate(
            name="Strong Momentum with Volume",
            description="Combined price momentum and volume confirmation",
            category="momentum",
            condition_templates=[
                {
                    "condition_type": "price_change",
                    "threshold": 3.0,  # 3% price change
                    "timeframe": "15m"
                },
                {
                    "condition_type": "volume_above",
                    "threshold": 2.0,  # 2x volume
                    "timeframe": "15m"
                }
            ],
            logic="AND",
            default_priority=AlertPriority.HIGH,
            recommended_cooldown=20,
            tags=["momentum", "volume", "trend"]
        ))
        
        logger.info(f"Initialized {len(self.templates)} default templates")
    
    def add_template(self, template: AlertTemplate) -> str:
        """Add a new template"""
        self.templates[template.template_id] = template
        return template.template_id
    
    def get_template(self, template_id: str) -> Optional[AlertTemplate]:
        """Get a template by ID"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[AlertTemplate]:
        """Get all templates"""
        return list(self.templates.values())
    
    def get_templates_by_category(self, category: str) -> List[AlertTemplate]:
        """Get templates by category"""
        return [
            template for template in self.templates.values()
            if template.category == category
        ]
    
    def get_templates_by_tag(self, tag: str) -> List[AlertTemplate]:
        """Get templates by tag"""
        return [
            template for template in self.templates.values()
            if tag in template.tags
        ]
    
    def search_templates(self, query: str) -> List[AlertTemplate]:
        """Search templates by name, description, or tags"""
        query_lower = query.lower()
        results = []
        
        for template in self.templates.values():
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results
    
    def create_alert_from_template(
        self,
        template_id: str,
        user_id: str,
        symbol: str,
        overrides: Optional[Dict[str, any]] = None
    ) -> Optional[AlertRule]:
        """Create an alert rule from a template"""
        template = self.get_template(template_id)
        
        if not template:
            logger.error(f"Template not found: {template_id}")
            return None
        
        try:
            alert_rule = create_alert_from_template(
                template, user_id, symbol, overrides
            )
            
            # Update template usage count
            template.usage_count += 1
            
            logger.info(
                f"Created alert from template '{template.name}' "
                f"for user {user_id}, symbol {symbol}"
            )
            
            return alert_rule
            
        except Exception as e:
            logger.error(f"Failed to create alert from template: {str(e)}")
            return None
    
    def get_popular_templates(self, limit: int = 10) -> List[AlertTemplate]:
        """Get most popular templates by usage"""
        sorted_templates = sorted(
            self.templates.values(),
            key=lambda t: t.usage_count,
            reverse=True
        )
        return sorted_templates[:limit]
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set(template.category for template in self.templates.values())
        return sorted(categories)
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags"""
        tags = set()
        for template in self.templates.values():
            tags.update(template.tags)
        return sorted(tags)
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        if template_id in self.templates:
            del self.templates[template_id]
            logger.info(f"Deleted template: {template_id}")
            return True
        return False
    
    def get_template_stats(self) -> Dict[str, any]:
        """Get template statistics"""
        total_templates = len(self.templates)
        total_usage = sum(t.usage_count for t in self.templates.values())
        
        by_category = {}
        for template in self.templates.values():
            by_category[template.category] = by_category.get(template.category, 0) + 1
        
        return {
            "total_templates": total_templates,
            "total_usage": total_usage,
            "by_category": by_category,
            "categories": self.get_categories(),
            "unique_tags": len(self.get_all_tags())
        }
