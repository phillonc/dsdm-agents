"""Database models for GEX Visualizer."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean,
    Index, ForeignKey, Numeric, JSON, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class OptionData(Base):
    """Option contract data storage."""
    
    __tablename__ = "option_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    strike = Column(Numeric(10, 2), nullable=False)
    expiration = Column(Date, nullable=False, index=True)
    option_type = Column(String(4), nullable=False)  # call or put
    bid = Column(Numeric(10, 2))
    ask = Column(Numeric(10, 2))
    last = Column(Numeric(10, 2))
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_symbol_expiration", "symbol", "expiration"),
        Index("idx_symbol_timestamp", "symbol", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<OptionData(symbol={self.symbol}, strike={self.strike}, "
            f"expiration={self.expiration}, type={self.option_type})>"
        )


class GEXSnapshot(Base):
    """GEX calculation snapshot storage."""
    
    __tablename__ = "gex_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    spot_price = Column(Numeric(10, 2), nullable=False)
    
    # Aggregated GEX values
    total_call_gex = Column(Float, nullable=False)
    total_put_gex = Column(Float, nullable=False)
    total_net_gex = Column(Float, nullable=False)
    
    # Strike-level data (JSON)
    strike_gex_data = Column(JSON, nullable=False)
    
    # Gamma flip information
    gamma_flip_strike = Column(Numeric(10, 2))
    gamma_flip_distance_pct = Column(Float)
    market_regime = Column(String(20), nullable=False)
    
    # Market maker positioning
    dealer_gamma_exposure = Column(Float)
    dealer_position = Column(String(20))
    hedging_pressure = Column(String(20))
    
    # Pin risk
    max_pain_strike = Column(Numeric(10, 2))
    pin_risk_score = Column(Float)
    
    __table_args__ = (
        Index("idx_symbol_timestamp_gex", "symbol", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<GEXSnapshot(symbol={self.symbol}, timestamp={self.timestamp}, "
            f"net_gex={self.total_net_gex})>"
        )


class AlertHistory(Base):
    """Alert history storage."""
    
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), unique=True, nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))
    
    __table_args__ = (
        Index("idx_symbol_triggered", "symbol", "triggered_at"),
        Index("idx_alert_type_severity", "alert_type", "severity"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AlertHistory(alert_id={self.alert_id}, type={self.alert_type}, "
            f"severity={self.severity})>"
        )


class HistoricalGEXData(Base):
    """Historical GEX data for trend analysis."""
    
    __tablename__ = "historical_gex_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    spot_price = Column(Numeric(10, 2), nullable=False)
    
    # Daily GEX metrics
    total_gex = Column(Float, nullable=False)
    call_gex = Column(Float, nullable=False)
    put_gex = Column(Float, nullable=False)
    gamma_flip_level = Column(Numeric(10, 2))
    market_regime = Column(String(20), nullable=False)
    
    # Additional metrics
    max_gex_strike = Column(Numeric(10, 2))
    min_gex_strike = Column(Numeric(10, 2))
    gex_volatility = Column(Float)  # Standard deviation of GEX across strikes
    
    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date", unique=True),
    )
    
    def __repr__(self) -> str:
        return (
            f"<HistoricalGEXData(symbol={self.symbol}, date={self.date}, "
            f"total_gex={self.total_gex})>"
        )
