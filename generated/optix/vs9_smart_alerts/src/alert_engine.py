"""
VS-9 Smart Alerts Ecosystem - Alert Engine
OPTIX Trading Platform

Core alert evaluation engine that processes market data against alert rules,
handles multi-condition logic, and triggers alerts based on user-defined criteria.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from .models import (
    AlertRule, AlertCondition, TriggeredAlert, MarketData, Position,
    AlertStatus, AlertPriority, ConditionType, MarketSession
)

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Core engine for evaluating alert rules against market data.
    Handles multi-condition logic, cooldown periods, and market hours awareness.
    """
    
    def __init__(self):
        self.active_rules: Dict[str, AlertRule] = {}
        self.cooldown_tracker: Dict[str, datetime] = {}
        self.market_hours_cache: Dict[str, Tuple[bool, MarketSession]] = {}
        
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule to the engine"""
        if rule.status == AlertStatus.ACTIVE:
            self.active_rules[rule.rule_id] = rule
            logger.info(f"Added alert rule: {rule.rule_id} - {rule.name}")
    
    def remove_rule(self, rule_id: str) -> None:
        """Remove an alert rule from the engine"""
        if rule_id in self.active_rules:
            del self.active_rules[rule_id]
            if rule_id in self.cooldown_tracker:
                del self.cooldown_tracker[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
    
    def update_rule(self, rule: AlertRule) -> None:
        """Update an existing alert rule"""
        if rule.status == AlertStatus.ACTIVE:
            self.active_rules[rule.rule_id] = rule
        else:
            self.remove_rule(rule.rule_id)
    
    def evaluate_market_data(
        self,
        market_data: MarketData,
        user_positions: Optional[List[Position]] = None
    ) -> List[TriggeredAlert]:
        """
        Evaluate market data against all active rules.
        Returns list of triggered alerts.
        """
        triggered_alerts = []
        current_time = datetime.utcnow()
        
        # Filter rules relevant to this symbol
        relevant_rules = [
            rule for rule in self.active_rules.values()
            if self._is_rule_relevant(rule, market_data, user_positions)
        ]
        
        logger.debug(f"Evaluating {len(relevant_rules)} rules for {market_data.symbol}")
        
        for rule in relevant_rules:
            # Check if rule is in cooldown
            if self._is_in_cooldown(rule, current_time):
                continue
            
            # Check if rule is expired
            if rule.expires_at and current_time > rule.expires_at:
                rule.status = AlertStatus.EXPIRED
                self.remove_rule(rule.rule_id)
                continue
            
            # Check market hours
            if not self._check_market_hours(rule, market_data):
                continue
            
            # Evaluate conditions
            triggered, matched_conditions, trigger_values = self._evaluate_rule(
                rule, market_data, user_positions
            )
            
            if triggered:
                alert = self._create_triggered_alert(
                    rule, market_data, matched_conditions, trigger_values, user_positions
                )
                triggered_alerts.append(alert)
                
                # Update cooldown and stats
                self.cooldown_tracker[rule.rule_id] = current_time
                rule.last_triggered_at = current_time
                rule.trigger_count += 1
                
                logger.info(
                    f"Alert triggered: {rule.name} for {market_data.symbol} "
                    f"(priority: {alert.priority.value})"
                )
        
        return triggered_alerts
    
    def _is_rule_relevant(
        self,
        rule: AlertRule,
        market_data: MarketData,
        user_positions: Optional[List[Position]]
    ) -> bool:
        """Check if rule is relevant to current market data and positions"""
        # Check if any condition matches the symbol
        symbol_match = any(
            cond.symbol == market_data.symbol for cond in rule.conditions
        )
        
        if not symbol_match:
            return False
        
        # Check position awareness
        if rule.position_aware and user_positions:
            position_symbols = {pos.symbol for pos in user_positions}
            return market_data.symbol in position_symbols
        
        return True
    
    def _is_in_cooldown(self, rule: AlertRule, current_time: datetime) -> bool:
        """Check if rule is in cooldown period"""
        if rule.rule_id not in self.cooldown_tracker:
            return False
        
        last_triggered = self.cooldown_tracker[rule.rule_id]
        cooldown_end = last_triggered + timedelta(minutes=rule.cooldown_minutes)
        
        return current_time < cooldown_end
    
    def _check_market_hours(self, rule: AlertRule, market_data: MarketData) -> bool:
        """Check if alert should fire based on market hours settings"""
        if not rule.market_hours_only:
            return True
        
        # Check if current session is allowed
        return market_data.session in rule.allowed_sessions
    
    def _evaluate_rule(
        self,
        rule: AlertRule,
        market_data: MarketData,
        user_positions: Optional[List[Position]]
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Evaluate all conditions in a rule.
        Returns (triggered, matched_condition_ids, trigger_values)
        """
        matched_conditions = []
        trigger_values = {}
        
        for condition in rule.conditions:
            if condition.symbol != market_data.symbol:
                continue
            
            matched, value = self._evaluate_condition(
                condition, market_data, user_positions
            )
            
            if matched:
                matched_conditions.append(condition.condition_id)
                trigger_values[condition.condition_type.value] = value
        
        # Apply logic (AND/OR)
        if rule.logic == "AND":
            triggered = len(matched_conditions) == len(rule.conditions)
        else:  # OR
            triggered = len(matched_conditions) > 0
        
        return triggered, matched_conditions, trigger_values
    
    def _evaluate_condition(
        self,
        condition: AlertCondition,
        market_data: MarketData,
        user_positions: Optional[List[Position]]
    ) -> Tuple[bool, Any]:
        """
        Evaluate a single condition against market data.
        Returns (matched, trigger_value)
        """
        cond_type = condition.condition_type
        threshold = condition.threshold
        
        # Price conditions
        if cond_type == ConditionType.PRICE_ABOVE:
            return market_data.price > threshold, market_data.price
        
        elif cond_type == ConditionType.PRICE_BELOW:
            return market_data.price < threshold, market_data.price
        
        elif cond_type == ConditionType.PRICE_CHANGE:
            change_pct = market_data.price_change_percent
            return abs(change_pct) >= threshold, change_pct
        
        # IV conditions
        elif cond_type == ConditionType.IV_ABOVE:
            if market_data.implied_volatility is None:
                return False, None
            return market_data.implied_volatility > threshold, market_data.implied_volatility
        
        elif cond_type == ConditionType.IV_BELOW:
            if market_data.implied_volatility is None:
                return False, None
            return market_data.implied_volatility < threshold, market_data.implied_volatility
        
        elif cond_type == ConditionType.IV_CHANGE:
            iv_rank = market_data.iv_rank
            if iv_rank is None:
                return False, None
            return abs(iv_rank) >= threshold, iv_rank
        
        # Volume conditions
        elif cond_type == ConditionType.VOLUME_ABOVE:
            return market_data.volume_ratio >= threshold, market_data.volume_ratio
        
        # Flow conditions
        elif cond_type == ConditionType.FLOW_BULLISH:
            if market_data.put_call_ratio is None:
                return False, None
            # Low put/call ratio indicates bullish flow
            return market_data.put_call_ratio < threshold, market_data.put_call_ratio
        
        elif cond_type == ConditionType.FLOW_BEARISH:
            if market_data.put_call_ratio is None:
                return False, None
            # High put/call ratio indicates bearish flow
            return market_data.put_call_ratio > threshold, market_data.put_call_ratio
        
        elif cond_type == ConditionType.UNUSUAL_ACTIVITY:
            if market_data.unusual_activity_score is None:
                return False, None
            return market_data.unusual_activity_score >= threshold, market_data.unusual_activity_score
        
        # Spread conditions
        elif cond_type == ConditionType.SPREAD_WIDTH:
            spread = market_data.ask - market_data.bid
            spread_pct = (spread / market_data.price) * 100 if market_data.price > 0 else 0
            return spread_pct >= threshold, spread_pct
        
        # Greeks conditions
        elif cond_type == ConditionType.DELTA_CHANGE:
            if market_data.total_delta is None:
                return False, None
            return abs(market_data.total_delta) >= threshold, market_data.total_delta
        
        elif cond_type == ConditionType.GAMMA_EXPOSURE:
            if market_data.total_gamma is None:
                return False, None
            return abs(market_data.total_gamma) >= threshold, market_data.total_gamma
        
        # Position-based conditions
        elif cond_type == ConditionType.POSITION_PNL:
            if not user_positions:
                return False, None
            
            relevant_positions = [
                pos for pos in user_positions
                if pos.symbol == condition.symbol
            ]
            
            for pos in relevant_positions:
                if abs(pos.unrealized_pnl_percent) >= threshold:
                    return True, pos.unrealized_pnl_percent
            
            return False, None
        
        elif cond_type == ConditionType.EXPIRATION_APPROACHING:
            if not user_positions:
                return False, None
            
            relevant_positions = [
                pos for pos in user_positions
                if pos.symbol == condition.symbol and pos.expiration
            ]
            
            current_time = datetime.utcnow()
            for pos in relevant_positions:
                days_to_expiry = (pos.expiration - current_time).days
                if days_to_expiry <= threshold:
                    return True, days_to_expiry
            
            return False, None
        
        # Default: condition not matched
        logger.warning(f"Unknown condition type: {cond_type}")
        return False, None
    
    def _create_triggered_alert(
        self,
        rule: AlertRule,
        market_data: MarketData,
        matched_conditions: List[str],
        trigger_values: Dict[str, Any],
        user_positions: Optional[List[Position]]
    ) -> TriggeredAlert:
        """Create a TriggeredAlert from a matched rule"""
        # Build alert message
        title = self._build_alert_title(rule, market_data, trigger_values)
        message = self._build_alert_message(rule, market_data, trigger_values)
        
        # Collect related positions
        related_positions = []
        if user_positions:
            related_positions = [
                pos.position_id for pos in user_positions
                if pos.symbol == market_data.symbol
            ]
        
        alert = TriggeredAlert(
            rule_id=rule.rule_id,
            user_id=rule.user_id,
            triggered_at=datetime.utcnow(),
            trigger_values=trigger_values,
            matched_conditions=matched_conditions,
            title=title,
            message=message,
            priority=rule.priority,
            status=AlertStatus.TRIGGERED,
            market_session=market_data.session,
            related_positions=related_positions,
            metadata={
                "symbol": market_data.symbol,
                "price": market_data.price,
                "rule_name": rule.name,
                "consolidation_group": rule.consolidation_group,
                "allow_consolidation": rule.allow_consolidation
            }
        )
        
        return alert
    
    def _build_alert_title(
        self,
        rule: AlertRule,
        market_data: MarketData,
        trigger_values: Dict[str, Any]
    ) -> str:
        """Build alert title"""
        return f"{rule.name} - {market_data.symbol}"
    
    def _build_alert_message(
        self,
        rule: AlertRule,
        market_data: MarketData,
        trigger_values: Dict[str, Any]
    ) -> str:
        """Build detailed alert message"""
        parts = [f"{market_data.symbol} at ${market_data.price:.2f}"]
        
        for cond_type, value in trigger_values.items():
            if value is not None:
                if "price" in cond_type:
                    parts.append(f"{cond_type}: ${value:.2f}")
                elif "percent" in cond_type or "iv" in cond_type:
                    parts.append(f"{cond_type}: {value:.2f}%")
                else:
                    parts.append(f"{cond_type}: {value}")
        
        return " | ".join(parts)
    
    def get_active_rules_count(self) -> int:
        """Get count of active rules"""
        return len(self.active_rules)
    
    def get_rules_by_user(self, user_id: str) -> List[AlertRule]:
        """Get all active rules for a user"""
        return [
            rule for rule in self.active_rules.values()
            if rule.user_id == user_id
        ]
    
    def get_rules_by_symbol(self, symbol: str) -> List[AlertRule]:
        """Get all active rules monitoring a symbol"""
        return [
            rule for rule in self.active_rules.values()
            if any(cond.symbol == symbol for cond in rule.conditions)
        ]
    
    def clear_cooldowns(self) -> None:
        """Clear all cooldown trackers (for testing)"""
        self.cooldown_tracker.clear()
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        total_rules = len(self.active_rules)
        rules_in_cooldown = len(self.cooldown_tracker)
        
        # Count by priority
        by_priority = defaultdict(int)
        for rule in self.active_rules.values():
            by_priority[rule.priority.value] += 1
        
        # Count by category
        by_category = defaultdict(int)
        for rule in self.active_rules.values():
            by_category[rule.category] += 1
        
        return {
            "total_active_rules": total_rules,
            "rules_in_cooldown": rules_in_cooldown,
            "rules_by_priority": dict(by_priority),
            "rules_by_category": dict(by_category),
            "cooldown_tracker_size": len(self.cooldown_tracker)
        }
