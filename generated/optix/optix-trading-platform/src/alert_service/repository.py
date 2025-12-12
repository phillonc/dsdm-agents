"""
Alert Repository
Data access layer for alerts
"""
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
from .models import Alert, AlertStatus


class AlertRepository:
    """Alert repository for database operations"""
    
    def __init__(self):
        self._alerts: Dict[uuid.UUID, Alert] = {}
        self._user_index: Dict[uuid.UUID, List[uuid.UUID]] = {}
    
    def create_alert(self, alert: Alert) -> Alert:
        """Create new alert"""
        self._alerts[alert.id] = alert
        
        if alert.user_id not in self._user_index:
            self._user_index[alert.user_id] = []
        self._user_index[alert.user_id].append(alert.id)
        
        return alert
    
    def get_alert(self, alert_id: uuid.UUID) -> Optional[Alert]:
        """Get alert by ID"""
        return self._alerts.get(alert_id)
    
    def get_user_alerts(
        self,
        user_id: uuid.UUID,
        status: Optional[AlertStatus] = None,
        symbol: Optional[str] = None
    ) -> List[Alert]:
        """Get user's alerts with optional filters"""
        alert_ids = self._user_index.get(user_id, [])
        alerts = [
            self._alerts[aid]
            for aid in alert_ids
            if aid in self._alerts
        ]
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol.upper()]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def update_alert(
        self,
        alert_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Alert:
        """Update alert"""
        alert = self._alerts.get(alert_id)
        if not alert:
            raise ValueError("Alert not found")
        
        for key, value in updates.items():
            if hasattr(alert, key):
                setattr(alert, key, value)
        
        alert.updated_at = datetime.utcnow()
        return alert
    
    def delete_alert(self, alert_id: uuid.UUID) -> bool:
        """Delete alert"""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        del self._alerts[alert_id]
        
        if alert.user_id in self._user_index:
            self._user_index[alert.user_id].remove(alert_id)
        
        return True
