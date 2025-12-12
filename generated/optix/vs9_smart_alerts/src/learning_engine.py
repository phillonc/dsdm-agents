"""
VS-9 Smart Alerts Ecosystem - Learning Engine
OPTIX Trading Platform

Machine learning component that learns from user actions to improve alert relevance.
Tracks user behavior patterns and adjusts alert priorities and recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import math

from .models import (
    TriggeredAlert, AlertRule, UserAlertProfile, AlertAnalytics,
    AlertPriority, ConditionType, AlertStatus
)

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Machine learning engine for alert relevance optimization.
    Learns from user actions to improve alert quality and reduce noise.
    """
    
    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate
        self.user_profiles: Dict[str, UserAlertProfile] = {}
        self.action_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.min_samples_for_learning = 10
        
    def record_user_action(
        self,
        user_id: str,
        alert: TriggeredAlert,
        action_type: str,
        action_timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a user action on an alert for learning.
        
        Args:
            user_id: User identifier
            alert: The triggered alert
            action_type: Type of action (e.g., "opened_position", "closed_position", 
                        "acknowledged", "snoozed", "dismissed")
            action_timestamp: When action occurred (defaults to now)
        """
        action_timestamp = action_timestamp or datetime.utcnow()
        
        # Calculate response time
        response_time = (action_timestamp - alert.triggered_at).total_seconds()
        
        # Determine if this was a positive action (user engaged meaningfully)
        positive_actions = {"opened_position", "closed_position", "adjusted_position", "acknowledged"}
        is_positive = action_type in positive_actions
        
        # Record action
        action_record = {
            "alert_id": alert.alert_id,
            "rule_id": alert.rule_id,
            "action_type": action_type,
            "is_positive": is_positive,
            "response_time": response_time,
            "timestamp": action_timestamp,
            "priority": alert.priority,
            "trigger_values": alert.trigger_values,
            "symbol": alert.metadata.get("symbol"),
            "market_session": alert.market_session
        }
        
        self.action_history[user_id].append(action_record)
        
        # Update alert's action tracking
        alert.user_acted = is_positive
        alert.action_type = action_type
        alert.action_timestamp = action_timestamp
        
        logger.info(
            f"Recorded action for user {user_id}: {action_type} on alert {alert.alert_id} "
            f"(response_time: {response_time:.1f}s)"
        )
    
    def update_rule_relevance(self, rule: AlertRule, user_id: str) -> float:
        """
        Update a rule's relevance score based on user behavior.
        Returns the new relevance score.
        """
        if user_id not in self.action_history:
            return rule.relevance_score
        
        # Get actions for this rule
        rule_actions = [
            action for action in self.action_history[user_id]
            if action["rule_id"] == rule.rule_id
        ]
        
        if len(rule_actions) < self.min_samples_for_learning:
            return rule.relevance_score
        
        # Calculate action rate
        positive_actions = sum(1 for a in rule_actions if a["is_positive"])
        action_rate = positive_actions / len(rule_actions)
        
        # Calculate average response time (lower is better)
        avg_response_time = sum(a["response_time"] for a in rule_actions) / len(rule_actions)
        response_time_score = self._score_response_time(avg_response_time)
        
        # Calculate recency weight (recent actions matter more)
        recency_weight = self._calculate_recency_weight(rule_actions)
        
        # Combine scores
        raw_score = (action_rate * 0.6) + (response_time_score * 0.2) + (recency_weight * 0.2)
        
        # Update with learning rate (smooth updates)
        new_score = (1 - self.learning_rate) * rule.relevance_score + self.learning_rate * raw_score
        new_score = max(0.0, min(1.0, new_score))  # Clamp to [0, 1]
        
        rule.relevance_score = new_score
        
        logger.debug(
            f"Updated relevance for rule {rule.rule_id}: {rule.relevance_score:.3f} "
            f"(action_rate: {action_rate:.2f}, samples: {len(rule_actions)})"
        )
        
        return new_score
    
    def learn_user_profile(self, user_id: str) -> UserAlertProfile:
        """
        Learn and update user's alert profile based on behavior history.
        Returns the updated profile.
        """
        if user_id not in self.action_history:
            return UserAlertProfile(user_id=user_id)
        
        actions = self.action_history[user_id]
        
        if len(actions) < self.min_samples_for_learning:
            # Not enough data yet
            return self.user_profiles.get(user_id, UserAlertProfile(user_id=user_id))
        
        # Get or create profile
        profile = self.user_profiles.get(user_id, UserAlertProfile(user_id=user_id))
        
        # Analyze most acted-upon condition types
        positive_actions = [a for a in actions if a["is_positive"]]
        condition_counter = Counter()
        
        for action in positive_actions:
            for cond_type in action.get("trigger_values", {}).keys():
                try:
                    condition_counter[ConditionType(cond_type)] += 1
                except ValueError:
                    continue
        
        profile.most_acted_conditions = [
            cond_type for cond_type, _ in condition_counter.most_common(5)
        ]
        
        # Analyze preferred priorities
        priority_counter = Counter(a["priority"] for a in positive_actions)
        profile.preferred_priorities = [
            priority for priority, _ in priority_counter.most_common(3)
        ]
        
        # Analyze active trading hours
        profile.active_trading_hours = self._identify_active_hours(actions)
        
        # Calculate symbol interests
        profile.symbol_interests = self._calculate_symbol_interests(actions)
        
        # Calculate condition relevance
        profile.condition_relevance = self._calculate_condition_relevance(actions)
        
        # Calculate engagement metrics
        if positive_actions:
            profile.avg_response_time_seconds = sum(
                a["response_time"] for a in positive_actions
            ) / len(positive_actions)
        
        profile.action_rate = len(positive_actions) / len(actions) if actions else 0.0
        
        snoozed_count = sum(1 for a in actions if a["action_type"] == "snoozed")
        profile.snooze_rate = snoozed_count / len(actions) if actions else 0.0
        
        # Store ML features for advanced models
        profile.features = {
            "total_actions": len(actions),
            "positive_actions": len(positive_actions),
            "action_rate": profile.action_rate,
            "avg_response_time": profile.avg_response_time_seconds,
            "snooze_rate": profile.snooze_rate,
            "active_hours_count": len(profile.active_trading_hours),
            "symbol_diversity": len(profile.symbol_interests),
            "condition_diversity": len(profile.condition_relevance)
        }
        
        profile.updated_at = datetime.utcnow()
        profile.last_learning_cycle = datetime.utcnow()
        
        self.user_profiles[user_id] = profile
        
        logger.info(
            f"Updated profile for user {user_id}: "
            f"action_rate={profile.action_rate:.2f}, "
            f"top_conditions={[c.value for c in profile.most_acted_conditions[:3]]}"
        )
        
        return profile
    
    def predict_alert_relevance(
        self,
        alert: TriggeredAlert,
        user_id: str
    ) -> float:
        """
        Predict relevance score for an alert based on learned user preferences.
        Returns score between 0.0 and 1.0.
        """
        profile = self.user_profiles.get(user_id)
        
        if not profile or profile.action_rate == 0:
            return 0.5  # Default for new users
        
        score = 0.5  # Start with baseline
        
        # Check condition relevance
        for cond_type_str, value in alert.trigger_values.items():
            try:
                cond_type = ConditionType(cond_type_str)
                if cond_type in profile.most_acted_conditions:
                    # Boost score for preferred condition types
                    position = profile.most_acted_conditions.index(cond_type)
                    boost = 0.15 * (1 - position / len(profile.most_acted_conditions))
                    score += boost
            except ValueError:
                continue
        
        # Check symbol interest
        symbol = alert.metadata.get("symbol")
        if symbol and symbol in profile.symbol_interests:
            score += profile.symbol_interests[symbol] * 0.15
        
        # Check priority preference
        if alert.priority in profile.preferred_priorities:
            position = profile.preferred_priorities.index(alert.priority)
            boost = 0.1 * (1 - position / len(profile.preferred_priorities))
            score += boost
        
        # Check time of day
        current_hour = datetime.utcnow().strftime("%H:00")
        if current_hour in profile.active_trading_hours:
            score += 0.1
        
        # Clamp to valid range
        score = max(0.0, min(1.0, score))
        
        return score
    
    def get_alert_recommendations(
        self,
        user_id: str,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recommended alert configurations for a user based on learned preferences.
        """
        profile = self.user_profiles.get(user_id)
        
        if not profile or not profile.most_acted_conditions:
            return []
        
        recommendations = []
        
        # Recommend based on most acted conditions
        for i, cond_type in enumerate(profile.most_acted_conditions[:top_n]):
            relevance = profile.condition_relevance.get(cond_type.value, 0.5)
            
            recommendation = {
                "condition_type": cond_type,
                "relevance_score": relevance,
                "reason": f"You frequently act on {cond_type.value} alerts",
                "suggested_priority": profile.preferred_priorities[0] if profile.preferred_priorities else AlertPriority.MEDIUM,
                "rank": i + 1
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def generate_analytics(
        self,
        user_id: str,
        rule_id: Optional[str] = None,
        days: int = 30
    ) -> AlertAnalytics:
        """
        Generate analytics for a user's alert performance.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        actions = [
            a for a in self.action_history.get(user_id, [])
            if a["timestamp"] >= cutoff_date
        ]
        
        if rule_id:
            actions = [a for a in actions if a["rule_id"] == rule_id]
        
        analytics = AlertAnalytics(
            user_id=user_id,
            rule_id=rule_id,
            period_start=cutoff_date,
            period_end=datetime.utcnow()
        )
        
        if not actions:
            return analytics
        
        # Trigger metrics
        analytics.total_triggers = len(actions)
        
        # Count by condition
        for action in actions:
            for cond_type in action.get("trigger_values", {}).keys():
                analytics.triggers_by_condition[cond_type] = \
                    analytics.triggers_by_condition.get(cond_type, 0) + 1
        
        # Count by priority
        for action in actions:
            priority_str = action["priority"].value
            analytics.triggers_by_priority[priority_str] = \
                analytics.triggers_by_priority.get(priority_str, 0) + 1
        
        # Engagement metrics
        positive_actions = [a for a in actions if a["is_positive"]]
        analytics.acted_upon_count = len(positive_actions)
        analytics.snoozed_count = sum(1 for a in actions if a["action_type"] == "snoozed")
        analytics.dismissed_count = sum(1 for a in actions if a["action_type"] == "dismissed")
        analytics.acknowledged_count = sum(1 for a in actions if a["action_type"] == "acknowledged")
        
        # Timing metrics
        if positive_actions:
            analytics.avg_time_to_action_seconds = sum(
                a["response_time"] for a in positive_actions
            ) / len(positive_actions)
        
        # Relevance metrics
        analytics.action_rate = len(positive_actions) / len(actions) if actions else 0.0
        analytics.false_positive_rate = 1.0 - analytics.action_rate
        
        # Calculate relevance score
        profile = self.user_profiles.get(user_id)
        if profile:
            analytics.relevance_score = profile.action_rate
        
        return analytics
    
    def _score_response_time(self, response_time_seconds: float) -> float:
        """
        Score response time (faster is better).
        Returns score between 0.0 and 1.0.
        """
        # Use exponential decay: score = e^(-t/τ)
        # τ = 300 seconds (5 minutes)
        tau = 300
        score = math.exp(-response_time_seconds / tau)
        return score
    
    def _calculate_recency_weight(self, actions: List[Dict[str, Any]]) -> float:
        """Calculate weight based on recency of actions"""
        if not actions:
            return 0.5
        
        now = datetime.utcnow()
        recent_actions = [
            a for a in actions
            if (now - a["timestamp"]).days <= 7
        ]
        
        return len(recent_actions) / len(actions)
    
    def _identify_active_hours(self, actions: List[Dict[str, Any]]) -> List[str]:
        """Identify hours when user is most active"""
        hour_counter = Counter()
        
        for action in actions:
            if action["is_positive"]:
                hour = action["timestamp"].strftime("%H:00")
                hour_counter[hour] += 1
        
        # Return top 5 active hours
        return [hour for hour, _ in hour_counter.most_common(5)]
    
    def _calculate_symbol_interests(
        self,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate user's interest level in different symbols"""
        symbol_stats = defaultdict(lambda: {"total": 0, "positive": 0})
        
        for action in actions:
            symbol = action.get("symbol")
            if symbol:
                symbol_stats[symbol]["total"] += 1
                if action["is_positive"]:
                    symbol_stats[symbol]["positive"] += 1
        
        # Calculate interest score (action rate with volume weighting)
        interests = {}
        total_actions = len(actions)
        
        for symbol, stats in symbol_stats.items():
            action_rate = stats["positive"] / stats["total"] if stats["total"] > 0 else 0
            volume_weight = stats["total"] / total_actions
            interest_score = action_rate * (0.7 + 0.3 * volume_weight)
            interests[symbol] = min(1.0, interest_score)
        
        return interests
    
    def _calculate_condition_relevance(
        self,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate relevance scores for different condition types"""
        condition_stats = defaultdict(lambda: {"total": 0, "positive": 0})
        
        for action in actions:
            for cond_type in action.get("trigger_values", {}).keys():
                condition_stats[cond_type]["total"] += 1
                if action["is_positive"]:
                    condition_stats[cond_type]["positive"] += 1
        
        # Calculate relevance (action rate)
        relevance = {}
        for cond_type, stats in condition_stats.items():
            if stats["total"] >= self.min_samples_for_learning:
                relevance[cond_type] = stats["positive"] / stats["total"]
        
        return relevance
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning engine statistics"""
        total_users = len(self.user_profiles)
        total_actions = sum(len(actions) for actions in self.action_history.values())
        
        users_with_profiles = len([
            p for p in self.user_profiles.values()
            if p.most_acted_conditions
        ])
        
        return {
            "total_users": total_users,
            "users_with_learned_profiles": users_with_profiles,
            "total_actions_recorded": total_actions,
            "learning_rate": self.learning_rate,
            "min_samples_for_learning": self.min_samples_for_learning
        }
