"""Alert models for unusual activity."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from decimal import Decimal


class AlertSeverity(Enum):
    """Alert severity level."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(Enum):
    """Type of alert."""
    UNUSUAL_SWEEP = "unusual_sweep"
    LARGE_BLOCK = "large_block"
    DARK_POOL_PRINT = "dark_pool_print"
    SMART_MONEY_FLOW = "smart_money_flow"
    INSTITUTIONAL_PATTERN = "institutional_pattern"
    GAMMA_SQUEEZE = "gamma_squeeze"
    VOLUME_SPIKE = "volume_spike"
    SPREAD_PATTERN = "spread_pattern"
    UNUSUAL_IV = "unusual_iv"


@dataclass
class UnusualActivityAlert:
    """Alert for unusual options activity."""
    
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    symbol: str
    underlying_symbol: str
    created_at: datetime
    
    # Alert details
    title: str
    description: str
    
    # Trade/pattern references
    related_trade_ids: List[str] = field(default_factory=list)
    related_pattern_ids: List[str] = field(default_factory=list)
    
    # Metrics
    total_premium: Optional[Decimal] = None
    total_contracts: Optional[int] = None
    confidence_score: float = 0.0
    
    # Context
    underlying_price: Optional[Decimal] = None
    strikes_involved: List[Decimal] = field(default_factory=list)
    expirations_involved: List[datetime] = field(default_factory=list)
    
    # Actions and status
    is_active: bool = True
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def age_seconds(self) -> float:
        """Get alert age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def priority_score(self) -> int:
        """Calculate priority score for alert routing."""
        severity_scores = {
            AlertSeverity.CRITICAL: 100,
            AlertSeverity.HIGH: 75,
            AlertSeverity.MEDIUM: 50,
            AlertSeverity.LOW: 25,
            AlertSeverity.INFO: 10,
        }
        base_score = severity_scores.get(self.severity, 0)
        
        # Boost for high confidence
        if self.confidence_score >= 0.8:
            base_score += 10
        
        # Boost for large notional
        if self.total_premium and self.total_premium >= Decimal('1000000'):
            base_score += 15
        
        return base_score
    
    def acknowledge(self, user: str) -> None:
        """Acknowledge the alert."""
        self.is_acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
    
    def deactivate(self) -> None:
        """Deactivate the alert."""
        self.is_active = False
    
    def to_dict(self) -> dict:
        """Convert alert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'symbol': self.symbol,
            'underlying_symbol': self.underlying_symbol,
            'created_at': self.created_at.isoformat(),
            'title': self.title,
            'description': self.description,
            'total_premium': str(self.total_premium) if self.total_premium else None,
            'total_contracts': self.total_contracts,
            'confidence_score': self.confidence_score,
            'priority_score': self.priority_score,
            'is_active': self.is_active,
            'is_acknowledged': self.is_acknowledged,
            'age_seconds': self.age_seconds,
            'tags': self.tags,
            'metadata': self.metadata,
        }
