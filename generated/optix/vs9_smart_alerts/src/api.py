"""
VS-9 Smart Alerts Ecosystem - REST API
OPTIX Trading Platform

FastAPI-based REST API for the Smart Alerts system.
Provides endpoints for alert management, delivery preferences, templates, and analytics.
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .models import (
    AlertRule, AlertCondition, TriggeredAlert, AlertPriority,
    AlertStatus, ConditionType, DeliveryChannel, MarketSession,
    DeliveryPreference, Position, MarketData
)
from .alert_engine import AlertEngine
from .learning_engine import LearningEngine
from .consolidation_engine import ConsolidationEngine
from .notification_service import NotificationService
from .template_manager import TemplateManager

# Initialize FastAPI app
app = FastAPI(
    title="OPTIX Smart Alerts API",
    description="Intelligent alert system for options trading",
    version="1.0.0"
)

# Initialize engines
alert_engine = AlertEngine()
learning_engine = LearningEngine()
consolidation_engine = ConsolidationEngine()
notification_service = NotificationService()
template_manager = TemplateManager()


# ============================================================================
# Pydantic Models for API
# ============================================================================

class AlertConditionCreate(BaseModel):
    condition_type: ConditionType
    symbol: str
    threshold: float
    comparison_value: Optional[float] = None
    timeframe: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AlertRuleCreate(BaseModel):
    user_id: str
    name: str
    description: str = ""
    conditions: List[AlertConditionCreate]
    logic: str = "AND"
    priority: AlertPriority = AlertPriority.MEDIUM
    market_hours_only: bool = True
    allowed_sessions: List[MarketSession] = Field(
        default_factory=lambda: [MarketSession.REGULAR]
    )
    position_aware: bool = False
    cooldown_minutes: int = 5
    expires_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[AlertPriority] = None
    status: Optional[AlertStatus] = None
    cooldown_minutes: Optional[int] = None
    tags: Optional[List[str]] = None


class MarketDataInput(BaseModel):
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    price_change_percent: float = 0.0
    volume_ratio: float = 1.0
    implied_volatility: Optional[float] = None
    iv_rank: Optional[float] = None
    put_call_ratio: Optional[float] = None
    unusual_activity_score: Optional[float] = None
    total_gamma: Optional[float] = None
    total_delta: Optional[float] = None
    session: MarketSession = MarketSession.REGULAR


class UserActionRecord(BaseModel):
    alert_id: str
    action_type: str
    action_timestamp: Optional[datetime] = None


class DeliveryPreferenceUpdate(BaseModel):
    enabled_channels: Optional[List[DeliveryChannel]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    push_tokens: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    enable_consolidation: Optional[bool] = None
    max_alerts_per_hour: Optional[int] = None


class TemplateApply(BaseModel):
    template_id: str
    symbol: str
    overrides: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Alert Rules Endpoints
# ============================================================================

@app.post("/api/v1/alerts/rules", status_code=201)
async def create_alert_rule(rule_data: AlertRuleCreate):
    """Create a new alert rule"""
    try:
        # Convert conditions
        conditions = [
            AlertCondition(
                condition_type=cond.condition_type,
                symbol=cond.symbol,
                threshold=cond.threshold,
                comparison_value=cond.comparison_value,
                timeframe=cond.timeframe,
                parameters=cond.parameters
            )
            for cond in rule_data.conditions
        ]
        
        # Create alert rule
        alert_rule = AlertRule(
            user_id=rule_data.user_id,
            name=rule_data.name,
            description=rule_data.description,
            conditions=conditions,
            logic=rule_data.logic,
            priority=rule_data.priority,
            market_hours_only=rule_data.market_hours_only,
            allowed_sessions=rule_data.allowed_sessions,
            position_aware=rule_data.position_aware,
            cooldown_minutes=rule_data.cooldown_minutes,
            expires_at=rule_data.expires_at,
            tags=rule_data.tags
        )
        
        # Add to engine
        alert_engine.add_rule(alert_rule)
        
        return {
            "rule_id": alert_rule.rule_id,
            "name": alert_rule.name,
            "status": alert_rule.status.value,
            "created_at": alert_rule.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/alerts/rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    """Get alert rule by ID"""
    rule = alert_engine.active_rules.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    return {
        "rule_id": rule.rule_id,
        "user_id": rule.user_id,
        "name": rule.name,
        "description": rule.description,
        "priority": rule.priority.value,
        "status": rule.status.value,
        "trigger_count": rule.trigger_count,
        "action_count": rule.action_count,
        "relevance_score": rule.relevance_score,
        "created_at": rule.created_at.isoformat(),
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
        "conditions": [
            {
                "condition_id": cond.condition_id,
                "condition_type": cond.condition_type.value,
                "symbol": cond.symbol,
                "threshold": cond.threshold
            }
            for cond in rule.conditions
        ]
    }


@app.get("/api/v1/alerts/rules")
async def list_alert_rules(
    user_id: Optional[str] = Query(None),
    status: Optional[AlertStatus] = Query(None),
    symbol: Optional[str] = Query(None)
):
    """List alert rules with optional filters"""
    rules = list(alert_engine.active_rules.values())
    
    # Apply filters
    if user_id:
        rules = [r for r in rules if r.user_id == user_id]
    if status:
        rules = [r for r in rules if r.status == status]
    if symbol:
        rules = [r for r in rules if any(c.symbol == symbol for c in r.conditions)]
    
    return {
        "total": len(rules),
        "rules": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "priority": r.priority.value,
                "status": r.status.value,
                "trigger_count": r.trigger_count,
                "relevance_score": r.relevance_score
            }
            for r in rules
        ]
    }


@app.patch("/api/v1/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: str, updates: AlertRuleUpdate):
    """Update an existing alert rule"""
    rule = alert_engine.active_rules.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    # Apply updates
    if updates.name is not None:
        rule.name = updates.name
    if updates.description is not None:
        rule.description = updates.description
    if updates.priority is not None:
        rule.priority = updates.priority
    if updates.status is not None:
        rule.status = updates.status
    if updates.cooldown_minutes is not None:
        rule.cooldown_minutes = updates.cooldown_minutes
    if updates.tags is not None:
        rule.tags = updates.tags
    
    # Update in engine
    alert_engine.update_rule(rule)
    
    return {"message": "Alert rule updated", "rule_id": rule_id}


@app.delete("/api/v1/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule"""
    if rule_id not in alert_engine.active_rules:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    alert_engine.remove_rule(rule_id)
    return {"message": "Alert rule deleted", "rule_id": rule_id}


# ============================================================================
# Market Data & Evaluation Endpoints
# ============================================================================

@app.post("/api/v1/alerts/evaluate")
async def evaluate_market_data(market_data: MarketDataInput):
    """Evaluate market data against all alert rules"""
    try:
        # Convert to MarketData model
        data = MarketData(
            symbol=market_data.symbol,
            price=market_data.price,
            bid=market_data.bid,
            ask=market_data.ask,
            volume=market_data.volume,
            price_change_percent=market_data.price_change_percent,
            volume_ratio=market_data.volume_ratio,
            implied_volatility=market_data.implied_volatility,
            iv_rank=market_data.iv_rank,
            put_call_ratio=market_data.put_call_ratio,
            unusual_activity_score=market_data.unusual_activity_score,
            total_gamma=market_data.total_gamma,
            total_delta=market_data.total_delta,
            session=market_data.session
        )
        
        # Evaluate
        triggered_alerts = alert_engine.evaluate_market_data(data)
        
        # Process through consolidation
        consolidated_results = []
        for alert in triggered_alerts:
            consolidated = consolidation_engine.process_alert(alert)
            if consolidated:
                # Deliver notifications
                delivery_results = notification_service.deliver_alert(consolidated)
                consolidated_results.append({
                    "alert_id": consolidated.consolidated_id,
                    "title": consolidated.title,
                    "summary": consolidated.summary,
                    "priority": consolidated.priority.value,
                    "alert_count": consolidated.alert_count,
                    "delivery_results": {
                        channel.value: status.value
                        for channel, status in delivery_results.items()
                    }
                })
        
        return {
            "triggered_alerts": len(triggered_alerts),
            "consolidated_alerts": len(consolidated_results),
            "alerts": consolidated_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Learning & Actions Endpoints
# ============================================================================

@app.post("/api/v1/alerts/actions")
async def record_user_action(user_id: str, action: UserActionRecord):
    """Record a user action on an alert for learning"""
    try:
        # In a real system, retrieve the alert from database
        # For now, create a mock alert
        from .models import TriggeredAlert
        alert = TriggeredAlert(
            alert_id=action.alert_id,
            user_id=user_id
        )
        
        learning_engine.record_user_action(
            user_id=user_id,
            alert=alert,
            action_type=action.action_type,
            action_timestamp=action.action_timestamp
        )
        
        return {"message": "User action recorded", "user_id": user_id}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/alerts/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get learned user profile"""
    profile = learning_engine.learn_user_profile(user_id)
    
    return {
        "user_id": profile.user_id,
        "action_rate": profile.action_rate,
        "avg_response_time_seconds": profile.avg_response_time_seconds,
        "most_acted_conditions": [c.value for c in profile.most_acted_conditions],
        "preferred_priorities": [p.value for p in profile.preferred_priorities],
        "active_trading_hours": profile.active_trading_hours,
        "symbol_interests": profile.symbol_interests,
        "updated_at": profile.updated_at.isoformat()
    }


@app.get("/api/v1/alerts/recommendations/{user_id}")
async def get_recommendations(user_id: str, top_n: int = Query(5, ge=1, le=20)):
    """Get alert recommendations for user"""
    recommendations = learning_engine.get_alert_recommendations(user_id, top_n)
    
    return {
        "user_id": user_id,
        "recommendations": [
            {
                "condition_type": rec["condition_type"].value,
                "relevance_score": rec["relevance_score"],
                "reason": rec["reason"],
                "suggested_priority": rec["suggested_priority"].value,
                "rank": rec["rank"]
            }
            for rec in recommendations
        ]
    }


@app.get("/api/v1/alerts/analytics/{user_id}")
async def get_analytics(user_id: str, days: int = Query(30, ge=1, le=365)):
    """Get alert analytics for user"""
    analytics = learning_engine.generate_analytics(user_id, days=days)
    
    return {
        "user_id": analytics.user_id,
        "period_start": analytics.period_start.isoformat(),
        "period_end": analytics.period_end.isoformat(),
        "total_triggers": analytics.total_triggers,
        "acted_upon_count": analytics.acted_upon_count,
        "action_rate": analytics.action_rate,
        "relevance_score": analytics.relevance_score,
        "triggers_by_condition": analytics.triggers_by_condition,
        "triggers_by_priority": analytics.triggers_by_priority
    }


# ============================================================================
# Delivery Preferences Endpoints
# ============================================================================

@app.get("/api/v1/delivery/preferences/{user_id}")
async def get_delivery_preferences(user_id: str):
    """Get user's delivery preferences"""
    prefs = notification_service.get_user_preferences(user_id)
    
    return {
        "user_id": prefs.user_id,
        "enabled_channels": [c.value for c in prefs.enabled_channels],
        "email": prefs.email,
        "phone": prefs.phone,
        "quiet_hours_start": prefs.quiet_hours_start,
        "quiet_hours_end": prefs.quiet_hours_end,
        "enable_consolidation": prefs.enable_consolidation,
        "max_alerts_per_hour": prefs.max_alerts_per_hour
    }


@app.put("/api/v1/delivery/preferences/{user_id}")
async def update_delivery_preferences(user_id: str, updates: DeliveryPreferenceUpdate):
    """Update user's delivery preferences"""
    prefs = notification_service.get_user_preferences(user_id)
    
    # Apply updates
    if updates.enabled_channels is not None:
        prefs.enabled_channels = updates.enabled_channels
    if updates.email is not None:
        prefs.email = updates.email
    if updates.phone is not None:
        prefs.phone = updates.phone
    if updates.push_tokens is not None:
        prefs.push_tokens = updates.push_tokens
    if updates.webhook_url is not None:
        prefs.webhook_url = updates.webhook_url
    if updates.quiet_hours_start is not None:
        prefs.quiet_hours_start = updates.quiet_hours_start
    if updates.quiet_hours_end is not None:
        prefs.quiet_hours_end = updates.quiet_hours_end
    if updates.enable_consolidation is not None:
        prefs.enable_consolidation = updates.enable_consolidation
    if updates.max_alerts_per_hour is not None:
        prefs.max_alerts_per_hour = updates.max_alerts_per_hour
    
    notification_service.set_user_preferences(user_id, prefs)
    
    return {"message": "Delivery preferences updated", "user_id": user_id}


@app.post("/api/v1/delivery/test/{user_id}/{channel}")
async def test_delivery_channel(user_id: str, channel: DeliveryChannel):
    """Test a delivery channel"""
    from .notification_service import DeliveryStatus
    
    status = notification_service.test_delivery_channel(user_id, channel)
    
    return {
        "user_id": user_id,
        "channel": channel.value,
        "status": status.value,
        "success": status == DeliveryStatus.SENT
    }


# ============================================================================
# Templates Endpoints
# ============================================================================

@app.get("/api/v1/templates")
async def list_templates(
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None)
):
    """List available alert templates"""
    if category:
        templates = template_manager.get_templates_by_category(category)
    elif tag:
        templates = template_manager.get_templates_by_tag(tag)
    else:
        templates = template_manager.get_all_templates()
    
    return {
        "total": len(templates),
        "templates": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "tags": t.tags,
                "usage_count": t.usage_count
            }
            for t in templates
        ]
    }


@app.get("/api/v1/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    template = template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "condition_templates": template.condition_templates,
        "logic": template.logic,
        "default_priority": template.default_priority.value,
        "recommended_cooldown": template.recommended_cooldown,
        "tags": template.tags,
        "usage_count": template.usage_count
    }


@app.post("/api/v1/templates/apply")
async def apply_template(user_id: str, template_apply: TemplateApply):
    """Apply a template to create an alert rule"""
    alert_rule = template_manager.create_alert_from_template(
        template_apply.template_id,
        user_id,
        template_apply.symbol,
        template_apply.overrides
    )
    
    if not alert_rule:
        raise HTTPException(status_code=400, detail="Failed to create alert from template")
    
    # Add to engine
    alert_engine.add_rule(alert_rule)
    
    return {
        "rule_id": alert_rule.rule_id,
        "name": alert_rule.name,
        "template_id": alert_rule.template_id
    }


@app.get("/api/v1/templates/search")
async def search_templates(q: str = Query(..., min_length=2)):
    """Search templates"""
    results = template_manager.search_templates(q)
    
    return {
        "query": q,
        "total": len(results),
        "results": [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category
            }
            for t in results
        ]
    }


# ============================================================================
# System Stats Endpoints
# ============================================================================

@app.get("/api/v1/stats/engine")
async def get_engine_stats():
    """Get alert engine statistics"""
    return alert_engine.get_engine_stats()


@app.get("/api/v1/stats/learning")
async def get_learning_stats():
    """Get learning engine statistics"""
    return learning_engine.get_learning_stats()


@app.get("/api/v1/stats/consolidation")
async def get_consolidation_stats():
    """Get consolidation engine statistics"""
    return consolidation_engine.get_consolidation_stats()


@app.get("/api/v1/stats/delivery")
async def get_delivery_stats(user_id: Optional[str] = Query(None)):
    """Get delivery statistics"""
    return notification_service.get_delivery_stats(user_id)


@app.get("/api/v1/stats/templates")
async def get_template_stats():
    """Get template statistics"""
    return template_manager.get_template_stats()


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "alert_engine": "operational",
            "learning_engine": "operational",
            "consolidation_engine": "operational",
            "notification_service": "operational",
            "template_manager": "operational"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
