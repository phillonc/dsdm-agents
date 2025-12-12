"""Storage service for GEX data persistence."""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_

from src.models.database import (
    Base,
    OptionData,
    GEXSnapshot,
    AlertHistory,
    HistoricalGEXData,
)
from src.models.schemas import (
    GEXHeatmap,
    GammaFlipLevel,
    MarketMakerPosition,
    PinRiskAnalysis,
    GEXAlert,
    HistoricalGEX,
)
from config.settings import settings


class StorageService:
    """
    Service for storing and retrieving GEX data.
    """
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        """
        Initialize storage service.
        
        Args:
            database_url: Database connection URL
        """
        db_url = database_url or settings.database_url
        
        # Convert postgresql:// to postgresql+asyncpg:// for async
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.engine = create_async_engine(
            db_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def store_gex_snapshot(
        self,
        symbol: str,
        spot_price: Decimal,
        heatmap: GEXHeatmap,
        gamma_flip: GammaFlipLevel,
        market_maker_position: MarketMakerPosition,
        pin_risk: Optional[PinRiskAnalysis] = None
    ) -> None:
        """
        Store GEX snapshot to database.
        
        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            heatmap: GEX heatmap data
            gamma_flip: Gamma flip data
            market_maker_position: Market maker positioning
            pin_risk: Pin risk analysis (if available)
        """
        async with self.session_factory() as session:
            # Prepare strike-level data
            strike_gex_data = [
                {
                    "strike": str(strike),
                    "gex": gex,
                    "color": color
                }
                for strike, gex, color in zip(
                    heatmap.strikes,
                    heatmap.gex_values,
                    heatmap.colors
                )
            ]
            
            snapshot = GEXSnapshot(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                spot_price=spot_price,
                total_call_gex=heatmap.total_call_gex,
                total_put_gex=heatmap.total_put_gex,
                total_net_gex=heatmap.total_net_gex,
                strike_gex_data=strike_gex_data,
                gamma_flip_strike=gamma_flip.gamma_flip_strike,
                gamma_flip_distance_pct=gamma_flip.distance_pct,
                market_regime=gamma_flip.market_regime,
                dealer_gamma_exposure=market_maker_position.dealer_gamma_exposure,
                dealer_position=market_maker_position.dealer_position,
                hedging_pressure=market_maker_position.hedging_pressure,
                max_pain_strike=pin_risk.max_pain_strike if pin_risk else None,
                pin_risk_score=pin_risk.pin_risk_score if pin_risk else None
            )
            
            session.add(snapshot)
            await session.commit()
    
    async def get_latest_snapshot(
        self,
        symbol: str
    ) -> Optional[GEXSnapshot]:
        """
        Get latest GEX snapshot for a symbol.
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Latest GEXSnapshot or None
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(GEXSnapshot)
                .where(GEXSnapshot.symbol == symbol)
                .order_by(GEXSnapshot.timestamp.desc())
                .limit(1)
            )
            
            return result.scalar_one_or_none()
    
    async def store_alert(self, alert: GEXAlert) -> None:
        """
        Store alert to database.
        
        Args:
            alert: GEXAlert object
        """
        async with self.session_factory() as session:
            alert_record = AlertHistory(
                alert_id=alert.alert_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                symbol=alert.symbol,
                message=alert.message,
                details=alert.details,
                triggered_at=alert.triggered_at,
                acknowledged=alert.acknowledged
            )
            
            session.add(alert_record)
            await session.commit()
    
    async def get_active_alerts(
        self,
        symbol: Optional[str] = None,
        min_severity: Optional[str] = None
    ) -> List[AlertHistory]:
        """
        Get active (unacknowledged) alerts.
        
        Args:
            symbol: Filter by symbol (optional)
            min_severity: Minimum severity level (optional)
            
        Returns:
            List of active alerts
        """
        async with self.session_factory() as session:
            query = select(AlertHistory).where(
                AlertHistory.acknowledged == False
            )
            
            if symbol:
                query = query.where(AlertHistory.symbol == symbol)
            
            if min_severity:
                severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                min_level = severity_order.get(min_severity, 1)
                
                # Filter by severity level
                query = query.where(
                    AlertHistory.severity.in_([
                        s for s, l in severity_order.items() if l >= min_level
                    ])
                )
            
            query = query.order_by(AlertHistory.triggered_at.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> None:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User acknowledging the alert
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(AlertHistory).where(AlertHistory.alert_id == alert_id)
            )
            
            alert = result.scalar_one_or_none()
            
            if alert:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                alert.acknowledged_by = acknowledged_by
                await session.commit()
    
    async def store_historical_gex(
        self,
        symbol: str,
        spot_price: Decimal,
        heatmap: GEXHeatmap,
        gamma_flip: GammaFlipLevel
    ) -> None:
        """
        Store daily historical GEX data.
        
        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            heatmap: GEX heatmap
            gamma_flip: Gamma flip data
        """
        async with self.session_factory() as session:
            today = date.today()
            
            # Check if record already exists for today
            result = await session.execute(
                select(HistoricalGEXData).where(
                    and_(
                        HistoricalGEXData.symbol == symbol,
                        HistoricalGEXData.date == today
                    )
                )
            )
            
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing record
                existing.timestamp = datetime.utcnow()
                existing.spot_price = spot_price
                existing.total_gex = heatmap.total_net_gex
                existing.call_gex = heatmap.total_call_gex
                existing.put_gex = heatmap.total_put_gex
                existing.gamma_flip_level = gamma_flip.gamma_flip_strike
                existing.market_regime = gamma_flip.market_regime
                existing.max_gex_strike = heatmap.max_gex_strike
                existing.min_gex_strike = heatmap.min_gex_strike
            else:
                # Create new record
                historical = HistoricalGEXData(
                    symbol=symbol,
                    date=today,
                    timestamp=datetime.utcnow(),
                    spot_price=spot_price,
                    total_gex=heatmap.total_net_gex,
                    call_gex=heatmap.total_call_gex,
                    put_gex=heatmap.total_put_gex,
                    gamma_flip_level=gamma_flip.gamma_flip_strike,
                    market_regime=gamma_flip.market_regime,
                    max_gex_strike=heatmap.max_gex_strike,
                    min_gex_strike=heatmap.min_gex_strike
                )
                session.add(historical)
            
            await session.commit()
    
    async def get_historical_gex(
        self,
        symbol: str,
        days: int = 30
    ) -> List[HistoricalGEX]:
        """
        Get historical GEX data.
        
        Args:
            symbol: Underlying symbol
            days: Number of days to retrieve
            
        Returns:
            List of historical GEX data
        """
        async with self.session_factory() as session:
            start_date = date.today() - timedelta(days=days)
            
            result = await session.execute(
                select(HistoricalGEXData)
                .where(
                    and_(
                        HistoricalGEXData.symbol == symbol,
                        HistoricalGEXData.date >= start_date
                    )
                )
                .order_by(HistoricalGEXData.date.desc())
            )
            
            records = result.scalars().all()
            
            return [
                HistoricalGEX(
                    symbol=r.symbol,
                    timestamp=r.timestamp,
                    spot_price=r.spot_price,
                    total_gex=r.total_gex,
                    call_gex=r.call_gex,
                    put_gex=r.put_gex,
                    gamma_flip_level=r.gamma_flip_level,
                    market_regime=r.market_regime
                )
                for r in records
            ]
    
    async def cleanup_old_data(self, days_to_keep: int) -> None:
        """
        Clean up old historical data.
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        async with self.session_factory() as session:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            
            # Delete old snapshots
            await session.execute(
                GEXSnapshot.__table__.delete().where(
                    GEXSnapshot.timestamp < datetime.combine(cutoff_date, datetime.min.time())
                )
            )
            
            # Delete old historical data
            await session.execute(
                HistoricalGEXData.__table__.delete().where(
                    HistoricalGEXData.date < cutoff_date
                )
            )
            
            await session.commit()
