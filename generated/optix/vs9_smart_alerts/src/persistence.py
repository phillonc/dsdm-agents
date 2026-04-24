"""
VS-9 Smart Alerts Ecosystem - PostgreSQL persistence layer.

This module maps the dataclass domain models to SQLAlchemy ORM records and
provides a repository facade for production storage. The code is dependency
safe: importing the module works without SQLAlchemy installed, while runtime use
of the repository requires SQLAlchemy and a configured database URL.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .models import AlertCondition, AlertPriority, AlertRule, AlertStatus, DeliveryPreference, TriggeredAlert

try:  # pragma: no cover - import availability depends on deployment image
    from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
except ImportError:  # pragma: no cover
    Boolean = DateTime = ForeignKey = Integer = String = Text = create_engine = None
    JSONB = UUID = None
    DeclarativeBase = object
    Mapped = Session = mapped_column = relationship = sessionmaker = None


class PersistenceNotConfigured(RuntimeError):
    """Raised when database persistence cannot be initialized."""


class Base(DeclarativeBase if DeclarativeBase is not object else object):
    """SQLAlchemy declarative base."""


if mapped_column:

    class AlertRuleRecord(Base):
        __tablename__ = "alert_rules"

        id: Mapped[str] = mapped_column(String(64), primary_key=True)
        user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        name: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[str] = mapped_column(Text, default="")
        logic: Mapped[str] = mapped_column(String(10), default="AND")
        priority: Mapped[str] = mapped_column(String(20), default=AlertPriority.MEDIUM.value)
        status: Mapped[str] = mapped_column(String(20), default=AlertStatus.ACTIVE.value, index=True)
        market_hours_only: Mapped[bool] = mapped_column(Boolean, default=True)
        position_aware: Mapped[bool] = mapped_column(Boolean, default=False)
        cooldown_minutes: Mapped[int] = mapped_column(Integer, default=5)
        expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
        last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=list)
        metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

        conditions: Mapped[List["AlertConditionRecord"]] = relationship(
            back_populates="rule", cascade="all, delete-orphan"
        )

    class AlertConditionRecord(Base):
        __tablename__ = "alert_conditions"

        id: Mapped[str] = mapped_column(String(64), primary_key=True)
        rule_id: Mapped[str] = mapped_column(String(64), ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
        condition_type: Mapped[str] = mapped_column(String(50), nullable=False)
        symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
        threshold: Mapped[str] = mapped_column(String(64), nullable=False)
        comparison_value: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
        timeframe: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
        parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        rule: Mapped[AlertRuleRecord] = relationship(back_populates="conditions")

    class TriggeredAlertRecord(Base):
        __tablename__ = "triggered_alerts"

        id: Mapped[str] = mapped_column(String(64), primary_key=True)
        rule_id: Mapped[str] = mapped_column(String(64), index=True)
        user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
        title: Mapped[str] = mapped_column(String(255), nullable=False)
        message: Mapped[str] = mapped_column(Text, default="")
        priority: Mapped[str] = mapped_column(String(20), default=AlertPriority.MEDIUM.value)
        status: Mapped[str] = mapped_column(String(20), default=AlertStatus.TRIGGERED.value, index=True)
        triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
        acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
        trigger_values: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
        metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    class DeliveryPreferenceRecord(Base):
        __tablename__ = "delivery_preferences"

        user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
        enabled_channels: Mapped[List[str]] = mapped_column(JSONB, default=list)
        priority_channel_map: Mapped[Dict[str, List[str]]] = mapped_column(JSONB, default=dict)
        email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
        phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
        push_tokens: Mapped[List[str]] = mapped_column(JSONB, default=list)
        webhook_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
        quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
        quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
        enable_consolidation: Mapped[bool] = mapped_column(Boolean, default=True)
        max_alerts_per_hour: Mapped[int] = mapped_column(Integer, default=50)
        max_sms_per_day: Mapped[int] = mapped_column(Integer, default=10)
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class DeliveryLogRecord(Base):
        __tablename__ = "delivery_logs"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        alert_id: Mapped[str] = mapped_column(String(64), index=True)
        user_id: Mapped[str] = mapped_column(String(64), index=True)
        channel: Mapped[str] = mapped_column(String(20), nullable=False)
        status: Mapped[str] = mapped_column(String(20), nullable=False)
        error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        delivered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
        metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

else:
    AlertRuleRecord = AlertConditionRecord = TriggeredAlertRecord = DeliveryPreferenceRecord = DeliveryLogRecord = None


def _ensure_sqlalchemy_available() -> None:
    if create_engine is None or sessionmaker is None:
        raise PersistenceNotConfigured(
            "SQLAlchemy is not installed. Install sqlalchemy and psycopg2/asyncpg to enable PostgreSQL persistence."
        )


class SmartAlertsRepository:
    """Repository facade for alert rules, triggered alerts, preferences, and delivery logs."""

    def __init__(self, database_url: Optional[str] = None):
        _ensure_sqlalchemy_available()
        self.database_url = database_url or os.getenv("OPTIX_DATABASE_URL")
        if not self.database_url:
            raise PersistenceNotConfigured("OPTIX_DATABASE_URL is required for PostgreSQL persistence")
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(bind=self.engine)

    def save_alert_rule(self, rule: AlertRule) -> None:
        with self.SessionLocal() as session:
            record = AlertRuleRecord(
                id=rule.rule_id,
                user_id=rule.user_id,
                name=rule.name,
                description=rule.description,
                logic=rule.logic,
                priority=rule.priority.value,
                status=rule.status.value,
                market_hours_only=rule.market_hours_only,
                position_aware=rule.position_aware,
                cooldown_minutes=rule.cooldown_minutes,
                expires_at=rule.expires_at,
                last_triggered_at=rule.last_triggered_at,
                created_at=rule.created_at,
                tags=rule.tags,
                metadata_json={
                    "allowed_sessions": [s.value for s in rule.allowed_sessions],
                    "category": rule.category,
                    "template_id": rule.template_id,
                    "relevance_score": rule.relevance_score,
                },
                conditions=[
                    AlertConditionRecord(
                        id=cond.condition_id,
                        condition_type=cond.condition_type.value,
                        symbol=cond.symbol,
                        threshold=str(cond.threshold),
                        comparison_value=str(cond.comparison_value) if cond.comparison_value is not None else None,
                        timeframe=cond.timeframe,
                        parameters=cond.parameters,
                    )
                    for cond in rule.conditions
                ],
            )
            session.merge(record)
            session.commit()

    def save_triggered_alert(self, alert: TriggeredAlert) -> None:
        with self.SessionLocal() as session:
            session.merge(
                TriggeredAlertRecord(
                    id=alert.alert_id,
                    rule_id=alert.rule_id,
                    user_id=alert.user_id,
                    title=alert.title,
                    message=alert.message,
                    priority=alert.priority.value,
                    status=alert.status.value,
                    triggered_at=alert.triggered_at,
                    acknowledged_at=alert.acknowledged_at,
                    trigger_values=alert.trigger_values,
                    metadata_json=alert.metadata,
                )
            )
            session.commit()

    def save_delivery_preferences(self, preferences: DeliveryPreference) -> None:
        with self.SessionLocal() as session:
            session.merge(
                DeliveryPreferenceRecord(
                    user_id=preferences.user_id,
                    enabled_channels=[c.value for c in preferences.enabled_channels],
                    priority_channel_map={k.value: [c.value for c in v] for k, v in preferences.priority_channel_map.items()},
                    email=preferences.email,
                    phone=preferences.phone,
                    push_tokens=preferences.push_tokens,
                    webhook_url=preferences.webhook_url,
                    quiet_hours_start=preferences.quiet_hours_start,
                    quiet_hours_end=preferences.quiet_hours_end,
                    enable_consolidation=preferences.enable_consolidation,
                    max_alerts_per_hour=preferences.max_alerts_per_hour,
                    max_sms_per_day=preferences.max_sms_per_day,
                    updated_at=preferences.updated_at,
                )
            )
            session.commit()

    def record_delivery(self, user_id: str, alert_id: str, channel: str, status: str, error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self.SessionLocal() as session:
            session.add(
                DeliveryLogRecord(
                    user_id=user_id,
                    alert_id=alert_id,
                    channel=channel,
                    status=status,
                    error_message=error,
                    metadata_json=metadata or {},
                )
            )
            session.commit()


def repository_from_env() -> Optional[SmartAlertsRepository]:
    """Create repository when OPTIX_DATABASE_URL is configured; otherwise return None."""
    if not os.getenv("OPTIX_DATABASE_URL"):
        return None
    return SmartAlertsRepository(os.getenv("OPTIX_DATABASE_URL"))
