"""
SQLAlchemy database models for the Generative UI Service.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    ForeignKey, Index, DateTime, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class GenUIGeneration(Base):
    """
    Stores generated UI instances.
    """
    __tablename__ = "genui_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=True)
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fsm_state: Mapped[dict] = mapped_column(JSONB, nullable=True)
    generated_html: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, default=1)
    final_score: Mapped[float] = mapped_column(Float, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("genui_generations.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    component_usage = relationship(
        "GenUIComponentUsage",
        back_populates="generation",
        cascade="all, delete-orphan"
    )
    feedback = relationship(
        "GenUIFeedback",
        back_populates="generation",
        cascade="all, delete-orphan"
    )
    refinements = relationship(
        "GenUIGeneration",
        backref="parent",
        remote_side=[id]
    )

    __table_args__ = (
        Index('idx_genui_generations_created_at', created_at.desc()),
        Index(
            'idx_genui_generations_favorite',
            user_id,
            is_favorite,
            postgresql_where=(is_favorite == True)
        ),
    )


class GenUIComponentUsage(Base):
    """
    Tracks which components are used in generations for analytics.
    """
    __tablename__ = "genui_component_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("genui_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    component_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    component_config: Mapped[dict] = mapped_column(JSONB, nullable=True)
    render_count: Mapped[int] = mapped_column(Integer, default=1)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    generation = relationship("GenUIGeneration", back_populates="component_usage")


class GenUIUserPreferences(Base):
    """
    Stores user preferences for UI generation.
    """
    __tablename__ = "genui_user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True
    )
    default_theme: Mapped[str] = mapped_column(
        String(20),
        default="dark"
    )
    preferred_chart_type: Mapped[str] = mapped_column(
        String(50),
        default="candlestick"
    )
    expertise_level: Mapped[str] = mapped_column(
        String(20),
        default="intermediate"
    )
    favorite_components: Mapped[list] = mapped_column(
        ARRAY(Text),
        nullable=True
    )
    custom_color_scheme: Mapped[dict] = mapped_column(JSONB, nullable=True)
    accessibility_settings: Mapped[dict] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class GenUIFeedback(Base):
    """
    Stores user feedback on generated UIs for model improvement.
    """
    __tablename__ = "genui_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("genui_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )
    feedback_type: Mapped[str] = mapped_column(
        String(50),
        nullable=True
    )
    feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    generation = relationship("GenUIGeneration", back_populates="feedback")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )


class GenUITemplate(Base):
    """
    Stores reusable UI templates.
    """
    __tablename__ = "genui_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    template_html: Mapped[str] = mapped_column(Text, nullable=False)
    props_schema: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fsm_states: Mapped[list] = mapped_column(ARRAY(Text), nullable=True)
    preview_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class GenUICache(Base):
    """
    Caches generated UIs for similar queries.
    """
    __tablename__ = "genui_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    query_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    generated_html: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_hit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
