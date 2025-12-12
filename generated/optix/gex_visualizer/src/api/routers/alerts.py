"""Alerts API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from src.services import StorageService
from src.models.database import AlertHistory

router = APIRouter()


def get_storage(request: Request) -> StorageService:
    """Get storage service from app state."""
    return request.app.state.storage


@router.get("/", response_model=List[dict])
async def get_alerts(
    symbol: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: bool = False,
    storage: StorageService = Depends(get_storage)
) -> List[dict]:
    """
    Get alerts with optional filtering.
    
    Args:
        symbol: Filter by symbol (optional)
        severity: Minimum severity level (low, medium, high, critical)
        acknowledged: Include acknowledged alerts
        storage: Storage service (injected)
        
    Returns:
        List of alerts
    """
    try:
        if not acknowledged:
            alerts = await storage.get_active_alerts(symbol=symbol, min_severity=severity)
        else:
            # TODO: Implement get_all_alerts method
            alerts = await storage.get_active_alerts(symbol=symbol, min_severity=severity)
        
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "symbol": alert.symbol,
                "message": alert.message,
                "details": alert.details,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged": alert.acknowledged,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "acknowledged_by": alert.acknowledged_by
            }
            for alert in alerts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.get("/active", response_model=List[dict])
async def get_active_alerts(
    symbol: Optional[str] = None,
    storage: StorageService = Depends(get_storage)
) -> List[dict]:
    """
    Get all active (unacknowledged) alerts.
    
    Args:
        symbol: Filter by symbol (optional)
        storage: Storage service (injected)
        
    Returns:
        List of active alerts
    """
    try:
        alerts = await storage.get_active_alerts(symbol=symbol)
        
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "symbol": alert.symbol,
                "message": alert.message,
                "details": alert.details,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in alerts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active alerts: {str(e)}")


@router.get("/critical", response_model=List[dict])
async def get_critical_alerts(
    symbol: Optional[str] = None,
    storage: StorageService = Depends(get_storage)
) -> List[dict]:
    """
    Get critical severity alerts.
    
    Args:
        symbol: Filter by symbol (optional)
        storage: Storage service (injected)
        
    Returns:
        List of critical alerts
    """
    try:
        alerts = await storage.get_active_alerts(symbol=symbol, min_severity="critical")
        
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "symbol": alert.symbol,
                "message": alert.message,
                "details": alert.details,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in alerts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve critical alerts: {str(e)}")


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str,
    storage: StorageService = Depends(get_storage)
) -> dict:
    """
    Acknowledge an alert.
    
    Args:
        alert_id: Alert ID to acknowledge
        acknowledged_by: Username acknowledging the alert
        storage: Storage service (injected)
        
    Returns:
        Success message
    """
    try:
        await storage.acknowledge_alert(alert_id=alert_id, acknowledged_by=acknowledged_by)
        
        return {
            "status": "success",
            "message": f"Alert {alert_id} acknowledged",
            "acknowledged_by": acknowledged_by
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.get("/summary")
async def get_alerts_summary(
    storage: StorageService = Depends(get_storage)
) -> dict:
    """
    Get summary of alert statistics.
    
    Args:
        storage: Storage service (injected)
        
    Returns:
        Alert summary statistics
    """
    try:
        alerts = await storage.get_active_alerts()
        
        # Count by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        # Count by type
        type_counts = {}
        
        # Count by symbol
        symbol_counts = {}
        
        for alert in alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            type_counts[alert.alert_type] = type_counts.get(alert.alert_type, 0) + 1
            symbol_counts[alert.symbol] = symbol_counts.get(alert.symbol, 0) + 1
        
        return {
            "total_active": len(alerts),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "by_symbol": symbol_counts,
            "has_critical": severity_counts["critical"] > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate alert summary: {str(e)}")
