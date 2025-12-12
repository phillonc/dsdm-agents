"""
Alert Service - Manages real-time alert generation and delivery
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict

from ..models.alert_models import (
    Alert, AlertType, AlertSeverity, AlertStatus, AlertChannel,
    AlertConfig, AlertCondition, AlertDeliveryLog
)
from ..models.pattern_models import ChartPattern
from ..models.analysis_models import PredictionSignal, VolatilityForecast
from ..models.user_models import PersonalizedInsight


class AlertService:
    """
    Service for generating and delivering real-time alerts
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.alert_cache = {}  # For deduplication
        self.delivery_logs = []
        
    async def generate_pattern_alert(
        self,
        user_id: str,
        pattern: ChartPattern,
        alert_config: AlertConfig
    ) -> Optional[Alert]:
        """
        Generate alert for detected pattern
        
        Args:
            user_id: User identifier
            pattern: Detected chart pattern
            alert_config: User's alert configuration
            
        Returns:
            Alert if conditions are met, None otherwise
        """
        # Check if alert should be generated
        if not self._should_generate_alert(pattern, alert_config):
            return None
        
        # Check for deduplication
        if self._is_duplicate_alert(user_id, pattern.pattern_id, alert_config):
            return None
        
        # Determine severity
        severity = self._calculate_pattern_severity(pattern)
        
        # Create alert message
        title, message = self._create_pattern_alert_message(pattern)
        
        # Determine channels
        channels = alert_config.preferred_channels or [AlertChannel.IN_APP]
        
        # Calculate priority score
        priority_score = pattern.confidence
        
        # Create alert
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            alert_type=AlertType.PATTERN_DETECTED,
            severity=severity,
            symbol=pattern.symbol,
            title=title,
            message=message,
            channels=channels,
            actionable=True,
            action_url=f"/patterns/{pattern.pattern_id}",
            action_data={
                'pattern_type': pattern.pattern_type.value,
                'confidence': pattern.confidence,
                'price_target': pattern.price_target
            },
            expiry=datetime.utcnow() + timedelta(hours=24),
            triggered_by=pattern.pattern_id,
            related_entities={'pattern_id': pattern.pattern_id},
            priority_score=priority_score
        )
        
        # Cache for deduplication
        self._cache_alert(user_id, pattern.pattern_id, alert_config)
        
        return alert
    
    async def generate_signal_alert(
        self,
        user_id: str,
        signal: PredictionSignal,
        alert_config: AlertConfig
    ) -> Optional[Alert]:
        """
        Generate alert for prediction signal
        
        Args:
            user_id: User identifier
            signal: Prediction signal
            alert_config: User's alert configuration
            
        Returns:
            Alert if conditions are met, None otherwise
        """
        # Check confidence threshold
        if signal.confidence < alert_config.min_confidence:
            return None
        
        # Check for deduplication
        if self._is_duplicate_alert(user_id, signal.signal_id, alert_config):
            return None
        
        # Determine severity
        severity = self._calculate_signal_severity(signal)
        
        # Check min severity
        if self._severity_level(severity) < self._severity_level(alert_config.min_severity):
            return None
        
        # Create alert message
        title, message = self._create_signal_alert_message(signal)
        
        # Create alert
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            alert_type=AlertType.PREDICTION_SIGNAL,
            severity=severity,
            symbol=signal.symbol,
            title=title,
            message=message,
            channels=alert_config.preferred_channels or [AlertChannel.IN_APP],
            actionable=True,
            action_url=f"/signals/{signal.signal_id}",
            action_data={
                'signal_type': signal.signal_type.value,
                'confidence': signal.confidence,
                'predicted_price': signal.predicted_price
            },
            expiry=datetime.utcnow() + timedelta(hours=12),
            triggered_by=signal.signal_id,
            related_entities={'signal_id': signal.signal_id},
            priority_score=signal.confidence
        )
        
        # Cache for deduplication
        self._cache_alert(user_id, signal.signal_id, alert_config)
        
        return alert
    
    async def generate_volatility_alert(
        self,
        user_id: str,
        forecast: VolatilityForecast,
        alert_config: AlertConfig
    ) -> Optional[Alert]:
        """
        Generate alert for volatility changes
        
        Args:
            user_id: User identifier
            forecast: Volatility forecast
            alert_config: User's alert configuration
            
        Returns:
            Alert if conditions are met, None otherwise
        """
        # Check if significant volatility change
        vol_change = abs(
            forecast.forecasted_volatility - forecast.current_volatility
        ) / forecast.current_volatility
        
        if vol_change < 0.2:  # Less than 20% change
            return None
        
        # Check regime change probability
        if forecast.regime_change_probability < 0.6:
            return None
        
        # Determine severity
        if vol_change > 0.5:
            severity = AlertSeverity.HIGH
        elif vol_change > 0.3:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW
        
        # Create message
        direction = "increase" if forecast.forecasted_volatility > forecast.current_volatility else "decrease"
        title = f"Volatility {direction.title()} Expected for {forecast.symbol}"
        message = (
            f"Volatility forecast shows a {vol_change:.1%} {direction} "
            f"from {forecast.current_volatility:.1%} to {forecast.forecasted_volatility:.1%}. "
            f"Regime change probability: {forecast.regime_change_probability:.1%}."
        )
        
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            alert_type=AlertType.VOLATILITY_CHANGE,
            severity=severity,
            symbol=forecast.symbol,
            title=title,
            message=message,
            channels=alert_config.preferred_channels or [AlertChannel.IN_APP],
            actionable=True,
            expiry=datetime.utcnow() + timedelta(hours=48),
            triggered_by=forecast.forecast_id,
            related_entities={'forecast_id': forecast.forecast_id},
            priority_score=forecast.regime_change_probability
        )
        
        return alert
    
    async def generate_insight_alert(
        self,
        insight: PersonalizedInsight,
        alert_config: AlertConfig
    ) -> Optional[Alert]:
        """
        Generate alert from personalized insight
        
        Args:
            insight: Personalized insight
            alert_config: User's alert configuration
            
        Returns:
            Alert if conditions are met, None otherwise
        """
        # Map insight priority to alert severity
        severity_map = {
            'urgent': AlertSeverity.CRITICAL,
            'high': AlertSeverity.HIGH,
            'medium': AlertSeverity.MEDIUM,
            'low': AlertSeverity.LOW
        }
        severity = severity_map.get(insight.priority.value, AlertSeverity.MEDIUM)
        
        # Map insight type to alert type
        type_map = {
            'opportunity': AlertType.OPPORTUNITY,
            'warning': AlertType.RISK_WARNING,
            'performance': AlertType.CUSTOM,
            'education': AlertType.CUSTOM
        }
        alert_type = type_map.get(insight.insight_type.value, AlertType.CUSTOM)
        
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            user_id=insight.user_id,
            alert_type=alert_type,
            severity=severity,
            symbol=insight.symbol,
            title=insight.title,
            message=insight.description,
            channels=alert_config.preferred_channels or [AlertChannel.IN_APP],
            actionable=insight.actionable,
            action_data={
                'action_items': insight.action_items,
                'learning_content': insight.learning_content
            } if insight.actionable else None,
            expiry=insight.expiry,
            triggered_by=insight.insight_id,
            related_entities={
                'insight_id': insight.insight_id,
                'related_patterns': insight.related_patterns,
                'related_signals': insight.related_signals
            },
            priority_score=insight.relevance_score
        )
        
        return alert
    
    async def deliver_alert(
        self,
        alert: Alert,
        channels: Optional[List[AlertChannel]] = None
    ) -> List[AlertDeliveryLog]:
        """
        Deliver alert through specified channels
        
        Args:
            alert: Alert to deliver
            channels: Channels to use (default: use alert.channels)
            
        Returns:
            List of delivery logs
        """
        delivery_logs = []
        channels = channels or alert.channels
        
        # Deliver to each channel concurrently
        delivery_tasks = [
            self._deliver_to_channel(alert, channel)
            for channel in channels
        ]
        
        results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
        
        for channel, result in zip(channels, results):
            if isinstance(result, AlertDeliveryLog):
                delivery_logs.append(result)
            elif isinstance(result, Exception):
                # Log failure
                log = AlertDeliveryLog(
                    log_id=f"log_{uuid.uuid4().hex[:8]}",
                    alert_id=alert.alert_id,
                    channel=channel,
                    status="failed",
                    error_message=str(result)
                )
                delivery_logs.append(log)
        
        # Update alert status
        if all(log.status == "success" for log in delivery_logs):
            alert.status = AlertStatus.DELIVERED
            alert.delivered_at = datetime.utcnow()
        elif any(log.status == "success" for log in delivery_logs):
            alert.status = AlertStatus.SENT
            alert.sent_at = datetime.utcnow()
        else:
            alert.status = AlertStatus.FAILED
        
        self.delivery_logs.extend(delivery_logs)
        
        return delivery_logs
    
    async def process_alert_batch(
        self,
        user_alerts: Dict[str, List[Alert]],
        alert_configs: Dict[str, AlertConfig]
    ) -> Dict[str, List[AlertDeliveryLog]]:
        """
        Process and deliver a batch of alerts
        
        Args:
            user_alerts: Dictionary of user_id -> list of alerts
            alert_configs: Dictionary of user_id -> alert config
            
        Returns:
            Dictionary of user_id -> delivery logs
        """
        results = {}
        
        for user_id, alerts in user_alerts.items():
            alert_config = alert_configs.get(user_id)
            
            if not alert_config or not alert_config.enabled:
                continue
            
            # Check daily limit
            if alert_config.max_alerts_per_day:
                daily_count = self._count_daily_alerts(user_id)
                if daily_count >= alert_config.max_alerts_per_day:
                    continue
            
            # Check quiet hours
            if self._is_quiet_hours(alert_config):
                continue
            
            # Filter and prioritize alerts
            filtered_alerts = self._filter_and_prioritize_alerts(
                alerts, alert_config
            )
            
            # Deliver alerts
            user_logs = []
            for alert in filtered_alerts:
                logs = await self.deliver_alert(alert)
                user_logs.extend(logs)
            
            results[user_id] = user_logs
        
        return results
    
    async def check_alert_conditions(
        self,
        user_id: str,
        alert_config: AlertConfig,
        current_data: Dict[str, Any]
    ) -> bool:
        """
        Check if alert conditions are met
        
        Args:
            user_id: User identifier
            alert_config: Alert configuration with conditions
            current_data: Current market data
            
        Returns:
            True if conditions are met
        """
        if not alert_config.conditions:
            return True
        
        for condition in alert_config.conditions:
            # Get current value for condition
            current_value = current_data.get(condition.condition_type)
            
            if current_value is None:
                continue
            
            condition.current_value = current_value
            
            # Check operator
            met = self._evaluate_condition(
                current_value,
                condition.operator,
                condition.threshold
            )
            condition.met = met
            
            if not met:
                return False
        
        return True
    
    # Private helper methods
    
    def _should_generate_alert(
        self,
        pattern: ChartPattern,
        alert_config: AlertConfig
    ) -> bool:
        """Check if alert should be generated for pattern"""
        # Check if enabled
        if not alert_config.enabled:
            return False
        
        # Check symbol filter
        if alert_config.symbol and alert_config.symbol != pattern.symbol:
            return False
        
        # Check confidence threshold
        if pattern.confidence < alert_config.min_confidence:
            return False
        
        return True
    
    def _is_duplicate_alert(
        self,
        user_id: str,
        entity_id: str,
        alert_config: AlertConfig
    ) -> bool:
        """Check if alert is duplicate within deduplication window"""
        cache_key = f"{user_id}:{entity_id}"
        
        if cache_key in self.alert_cache:
            last_alert_time = self.alert_cache[cache_key]
            time_since_last = (datetime.utcnow() - last_alert_time).total_seconds()
            
            if time_since_last < alert_config.deduplication_window:
                return True
        
        return False
    
    def _cache_alert(
        self,
        user_id: str,
        entity_id: str,
        alert_config: AlertConfig
    ):
        """Cache alert for deduplication"""
        cache_key = f"{user_id}:{entity_id}"
        self.alert_cache[cache_key] = datetime.utcnow()
        
        # Clean old cache entries
        cutoff_time = datetime.utcnow() - timedelta(
            seconds=alert_config.deduplication_window * 2
        )
        self.alert_cache = {
            k: v for k, v in self.alert_cache.items()
            if v > cutoff_time
        }
    
    def _calculate_pattern_severity(self, pattern: ChartPattern) -> AlertSeverity:
        """Calculate severity for pattern alert"""
        if pattern.confidence > 0.9:
            return AlertSeverity.HIGH
        elif pattern.confidence > 0.75:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _calculate_signal_severity(self, signal: PredictionSignal) -> AlertSeverity:
        """Calculate severity for signal alert"""
        if signal.signal_strength.value == 'very_strong':
            return AlertSeverity.HIGH
        elif signal.signal_strength.value == 'strong':
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _create_pattern_alert_message(
        self,
        pattern: ChartPattern
    ) -> tuple[str, str]:
        """Create alert message for pattern"""
        pattern_name = pattern.pattern_type.value.replace('_', ' ').title()
        
        title = f"{pattern_name} Pattern Detected on {pattern.symbol}"
        
        message = (
            f"A {pattern_name.lower()} pattern has been detected on {pattern.symbol} "
            f"with {pattern.confidence:.1%} confidence. "
        )
        
        if pattern.trend_direction:
            message += f"Trend direction: {pattern.trend_direction.value}. "
        
        if pattern.price_target:
            message += f"Price target: ${pattern.price_target:.2f}. "
        
        if pattern.support_level:
            message += f"Support: ${pattern.support_level:.2f}. "
        
        if pattern.resistance_level:
            message += f"Resistance: ${pattern.resistance_level:.2f}."
        
        return title, message
    
    def _create_signal_alert_message(
        self,
        signal: PredictionSignal
    ) -> tuple[str, str]:
        """Create alert message for signal"""
        signal_name = signal.signal_type.value.replace('_', ' ').title()
        
        title = f"{signal_name} Signal for {signal.symbol}"
        
        change_pct = (
            (signal.predicted_price - signal.current_price) / signal.current_price * 100
        )
        
        message = (
            f"{signal_name} signal detected for {signal.symbol} "
            f"with {signal.confidence:.1%} confidence. "
            f"Current price: ${signal.current_price:.2f}, "
            f"Predicted price: ${signal.predicted_price:.2f} "
            f"({change_pct:+.1f}%) over {signal.time_horizon}. "
        )
        
        if signal.price_target:
            message += f"Target: ${signal.price_target:.2f}. "
        
        if signal.risk_reward_ratio:
            message += f"Risk/Reward: {signal.risk_reward_ratio:.2f}."
        
        return title, message
    
    async def _deliver_to_channel(
        self,
        alert: Alert,
        channel: AlertChannel
    ) -> AlertDeliveryLog:
        """Deliver alert to specific channel"""
        start_time = datetime.utcnow()
        
        try:
            # Simulate delivery (in production, integrate with actual services)
            if channel == AlertChannel.IN_APP:
                await self._deliver_in_app(alert)
            elif channel == AlertChannel.EMAIL:
                await self._deliver_email(alert)
            elif channel == AlertChannel.SMS:
                await self._deliver_sms(alert)
            elif channel == AlertChannel.PUSH_NOTIFICATION:
                await self._deliver_push(alert)
            elif channel == AlertChannel.WEBHOOK:
                await self._deliver_webhook(alert)
            
            delivery_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            log = AlertDeliveryLog(
                log_id=f"log_{uuid.uuid4().hex[:8]}",
                alert_id=alert.alert_id,
                channel=channel,
                status="success",
                delivery_time_ms=delivery_time_ms
            )
            
            return log
            
        except Exception as e:
            log = AlertDeliveryLog(
                log_id=f"log_{uuid.uuid4().hex[:8]}",
                alert_id=alert.alert_id,
                channel=channel,
                status="failed",
                error_message=str(e)
            )
            return log
    
    async def _deliver_in_app(self, alert: Alert):
        """Deliver in-app notification"""
        # Simulate async delivery
        await asyncio.sleep(0.1)
        # In production: Store in database for user's notification center
        pass
    
    async def _deliver_email(self, alert: Alert):
        """Deliver email notification"""
        await asyncio.sleep(0.2)
        # In production: Integrate with email service (SendGrid, SES, etc.)
        pass
    
    async def _deliver_sms(self, alert: Alert):
        """Deliver SMS notification"""
        await asyncio.sleep(0.15)
        # In production: Integrate with SMS service (Twilio, etc.)
        pass
    
    async def _deliver_push(self, alert: Alert):
        """Deliver push notification"""
        await asyncio.sleep(0.1)
        # In production: Integrate with push service (FCM, APNS, etc.)
        pass
    
    async def _deliver_webhook(self, alert: Alert):
        """Deliver webhook notification"""
        await asyncio.sleep(0.2)
        # In production: POST to user's webhook URL
        pass
    
    def _count_daily_alerts(self, user_id: str) -> int:
        """Count alerts sent to user today"""
        today = datetime.utcnow().date()
        count = sum(
            1 for log in self.delivery_logs
            if log.attempted_at.date() == today and
            log.status == "success"
        )
        return count
    
    def _is_quiet_hours(self, alert_config: AlertConfig) -> bool:
        """Check if current time is in quiet hours"""
        if not alert_config.quiet_hours:
            return False
        
        current_hour = datetime.utcnow().hour
        
        start_hour = alert_config.quiet_hours.get('start_hour', 22)
        end_hour = alert_config.quiet_hours.get('end_hour', 8)
        
        if start_hour < end_hour:
            return start_hour <= current_hour < end_hour
        else:  # Wraps around midnight
            return current_hour >= start_hour or current_hour < end_hour
    
    def _filter_and_prioritize_alerts(
        self,
        alerts: List[Alert],
        alert_config: AlertConfig
    ) -> List[Alert]:
        """Filter and prioritize alerts based on config"""
        # Filter by custom filters
        filtered = alerts
        
        if alert_config.custom_filters:
            filtered = [
                a for a in filtered
                if self._apply_custom_filters(a, alert_config.custom_filters)
            ]
        
        # Sort by priority
        sorted_alerts = sorted(
            filtered,
            key=lambda a: (self._severity_level(a.severity), -a.priority_score),
            reverse=True
        )
        
        # Limit to reasonable number
        max_batch = alert_config.custom_filters.get('max_batch_size', 10)
        return sorted_alerts[:max_batch]
    
    def _apply_custom_filters(
        self,
        alert: Alert,
        custom_filters: Dict[str, Any]
    ) -> bool:
        """Apply custom filters to alert"""
        # Example filters
        if 'min_priority_score' in custom_filters:
            if alert.priority_score < custom_filters['min_priority_score']:
                return False
        
        if 'symbols' in custom_filters:
            if alert.symbol and alert.symbol not in custom_filters['symbols']:
                return False
        
        return True
    
    def _evaluate_condition(
        self,
        value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """Evaluate condition"""
        operators = {
            '>': lambda v, t: v > t,
            '<': lambda v, t: v < t,
            '>=': lambda v, t: v >= t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: v == t,
            '!=': lambda v, t: v != t
        }
        
        op_func = operators.get(operator)
        if op_func:
            return op_func(value, threshold)
        
        return False
    
    def _severity_level(self, severity: AlertSeverity) -> int:
        """Get numeric level for severity"""
        levels = {
            AlertSeverity.INFO: 0,
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4
        }
        return levels.get(severity, 0)
