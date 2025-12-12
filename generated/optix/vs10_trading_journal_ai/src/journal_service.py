"""
Journal Service Module for Trading Journal AI.

This module handles journal entry creation, management, and AI-powered
insights generation for individual journal entries.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .models import (
    JournalEntry, Trade, Tag, JournalEntryCreate,
    JournalEntryResponse, TagCreate, TagResponse
)

logger = logging.getLogger(__name__)


class JournalService:
    """
    Service for managing trading journal entries and tags.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the journal service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_journal_entry(
        self,
        entry_data: JournalEntryCreate
    ) -> JournalEntry:
        """
        Create a new journal entry.
        
        Args:
            entry_data: Journal entry creation data
            
        Returns:
            Created journal entry object
        """
        # Validate trade exists if trade_id provided
        if entry_data.trade_id:
            trade = self.db.query(Trade).filter(Trade.id == entry_data.trade_id).first()
            if not trade:
                raise ValueError(f"Trade {entry_data.trade_id} not found")
            if trade.user_id != entry_data.user_id:
                raise ValueError("Trade does not belong to user")
        
        entry = JournalEntry(
            user_id=entry_data.user_id,
            trade_id=entry_data.trade_id,
            title=entry_data.title,
            content=entry_data.content,
            notes=entry_data.notes,
            mood_rating=entry_data.mood_rating,
            confidence_level=entry_data.confidence_level,
            discipline_rating=entry_data.discipline_rating,
            screenshots=entry_data.screenshots,
            chart_images=entry_data.chart_images,
            entry_date=entry_data.entry_date
        )
        
        # Generate AI insights for the entry
        if entry.trade_id:
            entry.ai_insights = self._generate_entry_insights(entry)
            entry.ai_suggestions = self._generate_entry_suggestions(entry)
        
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        
        logger.info(f"Created journal entry {entry.id} for user {entry_data.user_id}")
        return entry
    
    def update_journal_entry(
        self,
        entry_id: int,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> JournalEntry:
        """
        Update an existing journal entry.
        
        Args:
            entry_id: Journal entry identifier
            user_id: User identifier (for authorization)
            update_data: Dictionary of fields to update
            
        Returns:
            Updated journal entry object
        """
        entry = self.db.query(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == user_id
        ).first()
        
        if not entry:
            raise ValueError(f"Journal entry {entry_id} not found")
        
        # Update allowed fields
        allowed_fields = [
            'title', 'content', 'notes', 'mood_rating', 
            'confidence_level', 'discipline_rating', 
            'screenshots', 'chart_images'
        ]
        
        for field, value in update_data.items():
            if field in allowed_fields:
                setattr(entry, field, value)
        
        # Regenerate AI insights if content changed
        if 'content' in update_data or 'notes' in update_data:
            if entry.trade_id:
                entry.ai_insights = self._generate_entry_insights(entry)
                entry.ai_suggestions = self._generate_entry_suggestions(entry)
        
        self.db.commit()
        self.db.refresh(entry)
        
        logger.info(f"Updated journal entry {entry_id}")
        return entry
    
    def delete_journal_entry(
        self,
        entry_id: int,
        user_id: str
    ) -> bool:
        """
        Delete a journal entry.
        
        Args:
            entry_id: Journal entry identifier
            user_id: User identifier (for authorization)
            
        Returns:
            True if deleted successfully
        """
        entry = self.db.query(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == user_id
        ).first()
        
        if not entry:
            raise ValueError(f"Journal entry {entry_id} not found")
        
        self.db.delete(entry)
        self.db.commit()
        
        logger.info(f"Deleted journal entry {entry_id}")
        return True
    
    def get_journal_entry(
        self,
        entry_id: int,
        user_id: str
    ) -> Optional[JournalEntry]:
        """
        Get a specific journal entry.
        
        Args:
            entry_id: Journal entry identifier
            user_id: User identifier (for authorization)
            
        Returns:
            Journal entry if found
        """
        return self.db.query(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == user_id
        ).first()
    
    def get_user_journal_entries(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        trade_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JournalEntry]:
        """
        Get journal entries for a user with optional filters.
        
        Args:
            user_id: User identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            trade_id: Optional trade ID filter
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List of journal entries
        """
        query = self.db.query(JournalEntry).filter(JournalEntry.user_id == user_id)
        
        if start_date:
            query = query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.entry_date <= end_date)
        if trade_id:
            query = query.filter(JournalEntry.trade_id == trade_id)
        
        return query.order_by(JournalEntry.entry_date.desc()).limit(limit).offset(offset).all()
    
    def _generate_entry_insights(self, entry: JournalEntry) -> Dict[str, Any]:
        """
        Generate AI insights for a journal entry.
        
        Args:
            entry: Journal entry object
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        
        # Mood analysis
        if entry.mood_rating:
            if entry.mood_rating >= 8:
                insights['mood'] = 'Positive mood - likely to make good decisions'
            elif entry.mood_rating >= 5:
                insights['mood'] = 'Neutral mood - stay focused on your plan'
            else:
                insights['mood'] = 'Low mood detected - consider taking a break'
        
        # Confidence analysis
        if entry.confidence_level:
            if entry.confidence_level >= 8:
                insights['confidence'] = 'High confidence - good, but watch for overconfidence'
            elif entry.confidence_level >= 5:
                insights['confidence'] = 'Healthy confidence level'
            else:
                insights['confidence'] = 'Low confidence - wait for clearer setups'
        
        # Discipline analysis
        if entry.discipline_rating:
            if entry.discipline_rating >= 8:
                insights['discipline'] = 'Excellent discipline - keep it up!'
            elif entry.discipline_rating >= 5:
                insights['discipline'] = 'Good discipline - maintain your rules'
            else:
                insights['discipline'] = 'Discipline needs improvement - review your trading plan'
        
        # Trade analysis if linked
        if entry.trade_id:
            trade = self.db.query(Trade).filter(Trade.id == entry.trade_id).first()
            if trade:
                if trade.net_pnl and trade.net_pnl > 0:
                    insights['trade_outcome'] = f'Winning trade: ${trade.net_pnl:.2f}'
                elif trade.net_pnl and trade.net_pnl < 0:
                    insights['trade_outcome'] = f'Losing trade: ${trade.net_pnl:.2f} - learn from it'
                
                # Setup analysis
                if trade.setup_type:
                    insights['setup'] = f'{trade.setup_type.value} setup'
                
                # Risk/reward
                if trade.risk_reward_ratio:
                    if trade.risk_reward_ratio >= 2.0:
                        insights['risk_reward'] = f'Excellent R:R of {trade.risk_reward_ratio:.2f}:1'
                    elif trade.risk_reward_ratio < 1.0:
                        insights['risk_reward'] = f'Poor R:R of {trade.risk_reward_ratio:.2f}:1 - aim for 2:1 minimum'
        
        return insights
    
    def _generate_entry_suggestions(self, entry: JournalEntry) -> str:
        """
        Generate AI suggestions for a journal entry.
        
        Args:
            entry: Journal entry object
            
        Returns:
            Suggestion text
        """
        suggestions = []
        
        # Based on mood
        if entry.mood_rating and entry.mood_rating < 5:
            suggestions.append("Your mood is low. Consider taking a break before your next trade.")
        
        # Based on confidence
        if entry.confidence_level and entry.confidence_level < 5:
            suggestions.append("Low confidence detected. Wait for clearer, higher probability setups.")
        
        # Based on discipline
        if entry.discipline_rating and entry.discipline_rating < 5:
            suggestions.append("Focus on following your trading plan strictly. Review your rules before the next trade.")
        
        # Based on trade outcome
        if entry.trade_id:
            trade = self.db.query(Trade).filter(Trade.id == entry.trade_id).first()
            if trade:
                if trade.net_pnl and trade.net_pnl < 0:
                    suggestions.append("Document what went wrong in this trade to avoid repeating the mistake.")
                elif trade.net_pnl and trade.net_pnl > 0:
                    suggestions.append("Great trade! Document what went right so you can replicate this success.")
                
                # Behavioral flags
                if trade.is_fomo:
                    suggestions.append("This appears to be a FOMO trade. Take breaks after big wins to avoid impulsive decisions.")
                if trade.is_revenge:
                    suggestions.append("This looks like revenge trading. Never try to 'get back' at the market after a loss.")
        
        # General suggestion
        suggestions.append("Keep detailed notes on emotions and market conditions to improve future decisions.")
        
        return " ".join(suggestions[:3])  # Return top 3 suggestions
    
    # Tag management methods
    
    def create_tag(self, tag_data: TagCreate) -> Tag:
        """
        Create a new tag.
        
        Args:
            tag_data: Tag creation data
            
        Returns:
            Created tag object
        """
        # Check for duplicate
        existing_tag = self.db.query(Tag).filter(
            Tag.user_id == tag_data.user_id,
            Tag.name == tag_data.name
        ).first()
        
        if existing_tag:
            raise ValueError(f"Tag '{tag_data.name}' already exists")
        
        tag = Tag(
            user_id=tag_data.user_id,
            name=tag_data.name,
            category=tag_data.category,
            color=tag_data.color,
            description=tag_data.description
        )
        
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        
        logger.info(f"Created tag {tag.id}: {tag.name}")
        return tag
    
    def get_user_tags(self, user_id: str) -> List[Tag]:
        """
        Get all tags for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of tags
        """
        return self.db.query(Tag).filter(Tag.user_id == user_id).all()
    
    def add_tag_to_trade(
        self,
        trade_id: int,
        tag_id: int,
        user_id: str
    ) -> bool:
        """
        Add a tag to a trade.
        
        Args:
            trade_id: Trade identifier
            tag_id: Tag identifier
            user_id: User identifier (for authorization)
            
        Returns:
            True if successful
        """
        trade = self.db.query(Trade).filter(
            Trade.id == trade_id,
            Trade.user_id == user_id
        ).first()
        
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        tag = self.db.query(Tag).filter(
            Tag.id == tag_id,
            Tag.user_id == user_id
        ).first()
        
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")
        
        if tag not in trade.tags:
            trade.tags.append(tag)
            self.db.commit()
        
        logger.info(f"Added tag {tag_id} to trade {trade_id}")
        return True
    
    def remove_tag_from_trade(
        self,
        trade_id: int,
        tag_id: int,
        user_id: str
    ) -> bool:
        """
        Remove a tag from a trade.
        
        Args:
            trade_id: Trade identifier
            tag_id: Tag identifier
            user_id: User identifier (for authorization)
            
        Returns:
            True if successful
        """
        trade = self.db.query(Trade).filter(
            Trade.id == trade_id,
            Trade.user_id == user_id
        ).first()
        
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")
        
        tag = self.db.query(Tag).filter(
            Tag.id == tag_id,
            Tag.user_id == user_id
        ).first()
        
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")
        
        if tag in trade.tags:
            trade.tags.remove(tag)
            self.db.commit()
        
        logger.info(f"Removed tag {tag_id} from trade {trade_id}")
        return True
    
    def search_journal_entries(
        self,
        user_id: str,
        search_query: str,
        limit: int = 50
    ) -> List[JournalEntry]:
        """
        Search journal entries by content.
        
        Args:
            user_id: User identifier
            search_query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching journal entries
        """
        query = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == user_id
        )
        
        # Search in title, content, and notes
        search_filter = (
            JournalEntry.title.contains(search_query) |
            JournalEntry.content.contains(search_query) |
            JournalEntry.notes.contains(search_query)
        )
        
        query = query.filter(search_filter)
        
        return query.order_by(JournalEntry.entry_date.desc()).limit(limit).all()
    
    def get_mood_trend(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get mood trend analysis over time.
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            Mood trend data
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        entries = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.mood_rating.isnot(None)
        ).order_by(JournalEntry.entry_date).all()
        
        if not entries:
            return {'average_mood': 0, 'trend': 'insufficient_data', 'data_points': []}
        
        mood_data = [
            {
                'date': entry.entry_date.isoformat(),
                'mood': entry.mood_rating
            }
            for entry in entries
        ]
        
        moods = [e.mood_rating for e in entries]
        avg_mood = sum(moods) / len(moods)
        
        # Simple trend detection
        if len(moods) >= 5:
            first_half_avg = sum(moods[:len(moods)//2]) / (len(moods)//2)
            second_half_avg = sum(moods[len(moods)//2:]) / (len(moods) - len(moods)//2)
            
            if second_half_avg > first_half_avg + 1:
                trend = 'improving'
            elif second_half_avg < first_half_avg - 1:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'average_mood': round(avg_mood, 2),
            'trend': trend,
            'data_points': mood_data
        }
