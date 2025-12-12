"""
API endpoints for alerts
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional
from datetime import datetime

from ..models.alert_models import (
    Alert, AlertConfig, AlertType, AlertSeverity, AlertChannel,
    AlertStatus, AlertStatistics
)
from ..services.alert_service import AlertService

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def get_alert_service() -> AlertService:
    return AlertService()


@router.get("/user/{user_id}", response_model=List[Alert])
async def get_user_alerts(
    user_id: str,
    status: Optional[AlertStatus] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: AlertService = Depends(get_alert_service)
):
    """
    Get alerts for user
    
    Args:
        user_id: User identifier
        status: Filter by status
        limit: Maximum number of alerts
        
    Returns:
        List of alerts
    """
    # In production, fetch from database
    raise HTTPException(status_code=501, detail="Not implemented - fetch from database")


@router.get("/alert/{alert_id}", response_model=Alert)
async def get_alert_details(
    alert_id: str,
    service: AlertService = Depends(get_alert_service)
):
    """
    Get alert details
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Alert details
    """
    # In production, fetch from database
    raise HTTPException(status_code=404, detail="Alert not found")


@router.put("/alert/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    status: AlertStatus = Body(...),
    service: AlertService = Depends(get_alert_service)
):
    """
    Update alert status
    
    Args:
        alert_id: Alert identifier
        status: New status
        
    Returns:
        Success message
    """
    # In production, update in database
    return {
        "status": "success",
        "message": f"Alert status updated to {status.value}"
    }


@router.put("/alert/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    service: AlertService = Depends(get_alert_service)
):
    """
    Dismiss an alert
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success message
    """
    # In production, update in database
    return {"status": "success", "message": "Alert dismissed"}


@router.get("/config/{user_id}", response_model=List[AlertConfig])
async def get_alert_configs(
    user_id: str,
    service: AlertService = Depends(get_alert_service)
):
    """
    Get user's alert configurations
    
    Args:
        user_id: User identifier
        
    Returns:
        List of alert configurations
    """
    # In production, fetch from database
    # Return sample config
    config = AlertConfig(
        config_id=f"cfg_{user_id}",
        user_id=user_id,
        enabled=True,
        alert_type=AlertType.PATTERN_DETECTED,
        min_confidence=0.7,
        min_severity=AlertSeverity.MEDIUM,
        preferred_channels=[AlertChannel.IN_APP, AlertChannel.PUSH_NOTIFICATION],
        max_alerts_per_day=20
    )
    return [config]


@router.post("/config/{user_id}", response_model=AlertConfig)
async def create_alert_config(
    user_id: str,
    config: AlertConfig = Body(...),
    service: AlertService = Depends(get_alert_service)
):
    """
    Create alert configuration
    
    Args:
        user_id: User identifier
        config: Alert configuration
        
    Returns:
        Created alert configuration
    """
    try:
        config.user_id = user_id
        config.created_at = datetime.utcnow()
        config.updated_at = datetime.utcnow()
        
        # In production, save to database
        return config
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/{config_id}", response_model=AlertConfig)
async def update_alert_config(
    config_id: str,
    config: AlertConfig = Body(...),
    service: AlertService = Depends(get_alert_service)
):
    """
    Update alert configuration
    
    Args:
        config_id: Configuration identifier
        config: Updated configuration
        
    Returns:
        Updated configuration
    """
    try:
        config.config_id = config_id
        config.updated_at = datetime.utcnow()
        
        # In production, update in database
        return config
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/{config_id}")
async def delete_alert_config(
    config_id: str,
    service: AlertService = Depends(get_alert_service)
):
    """
    Delete alert configuration
    
    Args:
        config_id: Configuration identifier
        
    Returns:
        Success message
    """
    # In production, delete from database
    return {"status": "success", "message": "Configuration deleted"}


@router.post("/test/{user_id}")
async def send_test_alert(
    user_id: str,
    alert_type: AlertType = Query(default=AlertType.CUSTOM),
    channel: AlertChannel = Query(default=AlertChannel.IN_APP),
    service: AlertService = Depends(get_alert_service)
):
    """
    Send a test alert to user
    
    Args:
        user_id: User identifier
        alert_type: Type of alert to send
        channel: Channel to use
        
    Returns:
        Delivery result
    """
    try:
        # Create test alert
        alert = Alert(
            alert_id=f"test_{datetime.utcnow().timestamp()}",
            user_id=user_id,
            alert_type=alert_type,
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="This is a test alert to verify your notification settings are working correctly.",
            channels=[channel],
            actionable=False,
            priority_score=0.5
        )
        
        # Deliver alert
        logs = await service.deliver_alert(alert, [channel])
        
        return {
            "status": "success",
            "alert_id": alert.alert_id,
            "delivery_logs": [
                {
                    "channel": log.channel.value,
                    "status": log.status,
                    "delivery_time_ms": log.delivery_time_ms
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{user_id}", response_model=AlertStatistics)
async def get_alert_statistics(
    user_id: str,
    days_back: int = Query(default=30, ge=1, le=365),
    service: AlertService = Depends(get_alert_service)
):
    """
    Get alert statistics for user
    
    Args:
        user_id: User identifier
        days_back: Number of days to analyze
        
    Returns:
        Alert statistics
    """
    from datetime import timedelta
    
    # In production, calculate from database
    # Return sample statistics
    statistics = AlertStatistics(
        user_id=user_id,
        period_start=datetime.utcnow() - timedelta(days=days_back),
        period_end=datetime.utcnow(),
        total_alerts=150,
        alerts_by_type={
            AlertType.PATTERN_DETECTED: 45,
            AlertType.PREDICTION_SIGNAL: 38,
            AlertType.OPPORTUNITY: 32,
            AlertType.RISK_WARNING: 15,
            AlertType.VOLATILITY_CHANGE: 20
        },
        alerts_by_severity={
            AlertSeverity.HIGH: 25,
            AlertSeverity.MEDIUM: 68,
            AlertSeverity.LOW: 57
        },
        delivery_success_rate=0.97,
        average_delivery_time_ms=150.5,
        read_rate=0.82,
        action_taken_rate=0.35,
        dismissed_rate=0.15,
        user_satisfaction_score=4.2
    )
    
    return statistics
