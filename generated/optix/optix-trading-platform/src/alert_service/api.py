"""
Alert Service REST API
Price alerts and notifications
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List
import uuid
from .models import Alert, CreateAlertRequest, AlertStatus
from .repository import AlertRepository
from .monitor import AlertMonitor


router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def get_alert_repository() -> AlertRepository:
    """Get alert repository instance"""
    return AlertRepository()


def get_alert_monitor() -> AlertMonitor:
    """Get alert monitor instance"""
    return AlertMonitor()


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context"""
    return uuid.uuid4()


@router.post("", response_model=Alert, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: CreateAlertRequest,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository),
    monitor: AlertMonitor = Depends(get_alert_monitor)
):
    """
    Create price alert
    
    - **symbol**: Stock/ETF symbol
    - **alert_type**: Type of alert (price_above, price_below, percent_change)
    - **threshold_value**: Trigger threshold
    - **expires_at**: Optional expiration date
    
    **Performance**: Alert triggers within 30 seconds of condition (AC)
    """
    # Check alert limit (50 per user)
    existing_alerts = repo.get_user_alerts(user_id, status=AlertStatus.ACTIVE)
    if len(existing_alerts) >= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 active alerts allowed"
        )
    
    alert = Alert(
        user_id=user_id,
        symbol=alert_data.symbol.upper(),
        alert_type=alert_data.alert_type,
        threshold_value=alert_data.threshold_value,
        message=alert_data.message,
        expires_at=alert_data.expires_at
    )
    
    created_alert = repo.create_alert(alert)
    
    # Start monitoring in background
    background_tasks.add_task(monitor.start_monitoring, created_alert.id)
    
    return created_alert


@router.get("", response_model=List[Alert])
async def list_alerts(
    status: AlertStatus = None,
    symbol: str = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository)
):
    """
    List user's alerts
    
    - **status**: Filter by alert status (optional)
    - **symbol**: Filter by symbol (optional)
    """
    alerts = repo.get_user_alerts(user_id, status=status, symbol=symbol)
    return alerts


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository)
):
    """Get alert by ID"""
    alert = repo.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    if alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository),
    monitor: AlertMonitor = Depends(get_alert_monitor)
):
    """Delete alert"""
    alert = repo.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    if alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Stop monitoring
    monitor.stop_monitoring(alert_id)
    
    # Delete alert
    repo.delete_alert(alert_id)


@router.patch("/{alert_id}/disable", response_model=Alert)
async def disable_alert(
    alert_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository),
    monitor: AlertMonitor = Depends(get_alert_monitor)
):
    """Disable alert temporarily"""
    alert = repo.get_alert(alert_id)
    
    if not alert or alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Stop monitoring
    monitor.stop_monitoring(alert_id)
    
    # Update status
    updated_alert = repo.update_alert(alert_id, {"status": AlertStatus.DISABLED})
    return updated_alert


@router.patch("/{alert_id}/enable", response_model=Alert)
async def enable_alert(
    alert_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: AlertRepository = Depends(get_alert_repository),
    monitor: AlertMonitor = Depends(get_alert_monitor)
):
    """Re-enable disabled alert"""
    alert = repo.get_alert(alert_id)
    
    if not alert or alert.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update status
    updated_alert = repo.update_alert(alert_id, {"status": AlertStatus.ACTIVE})
    
    # Resume monitoring
    background_tasks.add_task(monitor.start_monitoring, alert_id)
    
    return updated_alert
