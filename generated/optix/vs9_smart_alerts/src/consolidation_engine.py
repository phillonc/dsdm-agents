"""
VS-9 Smart Alerts Ecosystem - Consolidation Engine
OPTIX Trading Platform

Intelligent alert consolidation to group related alerts and reduce notification fatigue.
Implements time-window and semantic grouping strategies.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .models import (
    TriggeredAlert, ConsolidatedAlert, AlertPriority, AlertStatus
)

logger = logging.getLogger(__name__)


class ConsolidationEngine:
    """
    Engine for consolidating related alerts to reduce notification noise.
    Groups alerts by symbol, time window, and semantic similarity.
    """
    
    def __init__(self, consolidation_window_minutes: int = 5):
        self.consolidation_window_minutes = consolidation_window_minutes
        self.pending_alerts: Dict[str, List[TriggeredAlert]] = defaultdict(list)
        self.consolidation_groups: Dict[str, ConsolidatedAlert] = {}
        self.last_flush_time: Dict[str, datetime] = {}
        
    def process_alert(
        self,
        alert: TriggeredAlert,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[ConsolidatedAlert]:
        """
        Process an alert for potential consolidation.
        Returns ConsolidatedAlert if consolidation window is met, None if alert is pending.
        """
        # Check if consolidation is enabled for this alert
        if not alert.metadata.get("allow_consolidation", True):
            return self._create_single_alert_consolidation(alert)
        
        # Check user preferences
        if user_preferences and not user_preferences.get("enable_consolidation", True):
            return self._create_single_alert_consolidation(alert)
        
        user_id = alert.user_id
        
        # Add to pending alerts
        self.pending_alerts[user_id].append(alert)
        
        # Check if we should flush (consolidation window passed)
        if self._should_flush(user_id):
            return self._flush_pending_alerts(user_id)
        
        return None
    
    def _should_flush(self, user_id: str) -> bool:
        """Check if consolidation window has passed for a user"""
        if user_id not in self.last_flush_time:
            self.last_flush_time[user_id] = datetime.utcnow()
            return False
        
        time_since_last_flush = datetime.utcnow() - self.last_flush_time[user_id]
        window_passed = time_since_last_flush >= timedelta(minutes=self.consolidation_window_minutes)
        
        # Also flush if we have too many pending alerts
        alert_count = len(self.pending_alerts[user_id])
        too_many_alerts = alert_count >= 10
        
        return window_passed or too_many_alerts
    
    def _flush_pending_alerts(self, user_id: str) -> Optional[ConsolidatedAlert]:
        """
        Flush pending alerts for a user and create consolidated alerts.
        Returns the consolidated alert if any were pending.
        """
        pending = self.pending_alerts[user_id]
        
        if not pending:
            return None
        
        # Group alerts by consolidation strategy
        grouped_alerts = self._group_alerts(pending)
        
        # Clear pending for this user
        self.pending_alerts[user_id] = []
        self.last_flush_time[user_id] = datetime.utcnow()
        
        # If only one group or single alert, return it directly
        if len(grouped_alerts) == 1 and len(list(grouped_alerts.values())[0]) == 1:
            alert = list(grouped_alerts.values())[0][0]
            return self._create_single_alert_consolidation(alert)
        
        # Create consolidated alerts for each group
        consolidated_alerts = []
        for group_key, alerts in grouped_alerts.items():
            if len(alerts) == 1:
                consolidated = self._create_single_alert_consolidation(alerts[0])
            else:
                consolidated = self._create_consolidated_alert(alerts, group_key)
            
            consolidated_alerts.append(consolidated)
            self.consolidation_groups[consolidated.consolidated_id] = consolidated
        
        # If multiple consolidations, merge them into a super-consolidation
        if len(consolidated_alerts) > 1:
            return self._merge_consolidations(consolidated_alerts, user_id)
        
        return consolidated_alerts[0] if consolidated_alerts else None
    
    def _group_alerts(
        self,
        alerts: List[TriggeredAlert]
    ) -> Dict[str, List[TriggeredAlert]]:
        """
        Group alerts by similarity for consolidation.
        Groups by: consolidation_group, symbol, priority
        """
        groups: Dict[str, List[TriggeredAlert]] = defaultdict(list)
        
        for alert in alerts:
            # Try to use explicit consolidation group first
            group_id = alert.metadata.get("consolidation_group")
            
            if not group_id:
                # Create group key from alert characteristics
                symbol = alert.metadata.get("symbol", "unknown")
                priority = alert.priority.value
                group_id = f"{symbol}_{priority}"
            
            groups[group_id].append(alert)
        
        return groups
    
    def _create_single_alert_consolidation(
        self,
        alert: TriggeredAlert
    ) -> ConsolidatedAlert:
        """Create a consolidated alert from a single alert"""
        consolidated = ConsolidatedAlert(
            user_id=alert.user_id,
            alert_ids=[alert.alert_id],
            alerts=[alert],
            consolidation_reason="single_alert",
            consolidation_group=alert.metadata.get("consolidation_group", "single"),
            title=alert.title,
            summary=alert.message,
            priority=alert.priority,
            alert_count=1,
            status=alert.status
        )
        
        # Mark original alert as consolidated
        alert.is_consolidated = True
        alert.consolidated_alert_id = consolidated.consolidated_id
        
        return consolidated
    
    def _create_consolidated_alert(
        self,
        alerts: List[TriggeredAlert],
        group_key: str
    ) -> ConsolidatedAlert:
        """Create a consolidated alert from multiple related alerts"""
        if not alerts:
            raise ValueError("Cannot consolidate empty alert list")
        
        # Determine highest priority
        max_priority = max(alert.priority for alert in alerts)
        
        # Create title and summary
        title = self._create_consolidated_title(alerts)
        summary = self._create_consolidated_summary(alerts)
        
        # Create consolidated alert
        consolidated = ConsolidatedAlert(
            user_id=alerts[0].user_id,
            alert_ids=[alert.alert_id for alert in alerts],
            alerts=alerts,
            consolidation_reason=self._determine_consolidation_reason(alerts),
            consolidation_group=group_key,
            title=title,
            summary=summary,
            priority=max_priority,
            alert_count=len(alerts),
            status=AlertStatus.TRIGGERED
        )
        
        # Mark all alerts as consolidated
        for alert in alerts:
            alert.is_consolidated = True
            alert.consolidated_alert_id = consolidated.consolidated_id
            alert.related_alert_ids = [
                a.alert_id for a in alerts if a.alert_id != alert.alert_id
            ]
        
        logger.info(
            f"Created consolidated alert {consolidated.consolidated_id} "
            f"from {len(alerts)} alerts (priority: {max_priority.value})"
        )
        
        return consolidated
    
    def _merge_consolidations(
        self,
        consolidations: List[ConsolidatedAlert],
        user_id: str
    ) -> ConsolidatedAlert:
        """Merge multiple consolidated alerts into a super-consolidation"""
        all_alerts = []
        all_alert_ids = []
        
        for cons in consolidations:
            all_alerts.extend(cons.alerts)
            all_alert_ids.extend(cons.alert_ids)
        
        max_priority = max(cons.priority for cons in consolidations)
        
        # Create summary
        summary_parts = [
            f"{cons.alert_count} {cons.consolidation_group} alerts"
            for cons in consolidations
        ]
        summary = " | ".join(summary_parts)
        
        merged = ConsolidatedAlert(
            user_id=user_id,
            alert_ids=all_alert_ids,
            alerts=all_alerts,
            consolidation_reason="multiple_groups",
            consolidation_group="merged",
            title=f"{len(all_alerts)} alerts across multiple groups",
            summary=summary,
            priority=max_priority,
            alert_count=len(all_alerts),
            status=AlertStatus.TRIGGERED
        )
        
        return merged
    
    def _create_consolidated_title(self, alerts: List[TriggeredAlert]) -> str:
        """Create title for consolidated alert"""
        if not alerts:
            return "Consolidated Alerts"
        
        # Get unique symbols
        symbols = set(alert.metadata.get("symbol") for alert in alerts)
        symbols = {s for s in symbols if s is not None}
        
        if len(symbols) == 1:
            symbol = list(symbols)[0]
            return f"{len(alerts)} alerts for {symbol}"
        elif len(symbols) <= 3:
            symbol_str = ", ".join(sorted(symbols))
            return f"{len(alerts)} alerts for {symbol_str}"
        else:
            return f"{len(alerts)} alerts across {len(symbols)} symbols"
    
    def _create_consolidated_summary(self, alerts: List[TriggeredAlert]) -> str:
        """Create summary for consolidated alert"""
        # Group by symbol
        by_symbol = defaultdict(list)
        for alert in alerts:
            symbol = alert.metadata.get("symbol", "unknown")
            by_symbol[symbol].append(alert)
        
        # Create summary parts
        summary_parts = []
        for symbol, symbol_alerts in sorted(by_symbol.items()):
            # Get unique condition types
            conditions = set()
            for alert in symbol_alerts:
                conditions.update(alert.trigger_values.keys())
            
            condition_str = ", ".join(sorted(conditions))
            summary_parts.append(f"{symbol}: {condition_str}")
        
        # Limit summary length
        summary = " | ".join(summary_parts[:5])
        if len(summary_parts) > 5:
            summary += f" | +{len(summary_parts) - 5} more"
        
        return summary
    
    def _determine_consolidation_reason(self, alerts: List[TriggeredAlert]) -> str:
        """Determine why alerts were consolidated"""
        if not alerts:
            return "unknown"
        
        # Check if same symbol
        symbols = {alert.metadata.get("symbol") for alert in alerts}
        if len(symbols) == 1:
            return f"same_symbol_{list(symbols)[0]}"
        
        # Check if same consolidation group
        groups = {alert.metadata.get("consolidation_group") for alert in alerts}
        if len(groups) == 1 and list(groups)[0] is not None:
            return f"group_{list(groups)[0]}"
        
        # Check time proximity
        time_range = max(a.triggered_at for a in alerts) - min(a.triggered_at for a in alerts)
        if time_range < timedelta(minutes=1):
            return "time_proximity"
        
        return "related_alerts"
    
    def force_flush_user(self, user_id: str) -> Optional[ConsolidatedAlert]:
        """Force flush pending alerts for a user"""
        if user_id in self.pending_alerts and self.pending_alerts[user_id]:
            return self._flush_pending_alerts(user_id)
        return None
    
    def force_flush_all(self) -> List[ConsolidatedAlert]:
        """Force flush all pending alerts"""
        results = []
        for user_id in list(self.pending_alerts.keys()):
            consolidated = self.force_flush_user(user_id)
            if consolidated:
                results.append(consolidated)
        return results
    
    def get_consolidation(self, consolidated_id: str) -> Optional[ConsolidatedAlert]:
        """Get a consolidated alert by ID"""
        return self.consolidation_groups.get(consolidated_id)
    
    def get_pending_count(self, user_id: str) -> int:
        """Get count of pending alerts for a user"""
        return len(self.pending_alerts.get(user_id, []))
    
    def clear_user_pending(self, user_id: str) -> None:
        """Clear pending alerts for a user without consolidating"""
        if user_id in self.pending_alerts:
            del self.pending_alerts[user_id]
        if user_id in self.last_flush_time:
            del self.last_flush_time[user_id]
    
    def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get consolidation engine statistics"""
        total_pending = sum(len(alerts) for alerts in self.pending_alerts.values())
        users_with_pending = len([k for k, v in self.pending_alerts.items() if v])
        
        # Consolidation metrics
        total_consolidations = len(self.consolidation_groups)
        total_alerts_consolidated = sum(
            c.alert_count for c in self.consolidation_groups.values()
        )
        
        avg_alerts_per_consolidation = (
            total_alerts_consolidated / total_consolidations
            if total_consolidations > 0 else 0
        )
        
        return {
            "total_pending_alerts": total_pending,
            "users_with_pending": users_with_pending,
            "total_consolidations": total_consolidations,
            "total_alerts_consolidated": total_alerts_consolidated,
            "avg_alerts_per_consolidation": avg_alerts_per_consolidation,
            "consolidation_window_minutes": self.consolidation_window_minutes
        }
