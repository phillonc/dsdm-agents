"""
User Service Repository
Data access layer for user and profile management
"""
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
from .models import User, UserProfile


class UserRepository:
    """
    User repository for database operations
    In production, this would interact with PostgreSQL
    """
    
    def __init__(self):
        # In-memory storage for demonstration
        # In production, use SQLAlchemy or similar ORM
        self._users: Dict[uuid.UUID, User] = {}
        self._profiles: Dict[uuid.UUID, UserProfile] = {}
        self._email_index: Dict[str, uuid.UUID] = {}
    
    def create_user(self, user: User) -> User:
        """Create new user"""
        self._users[user.id] = user
        self._email_index[user.email.lower()] = user.id
        return user
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None
    
    def update_user(self, user_id: uuid.UUID, updates: Dict[str, Any]) -> User:
        """Update user fields"""
        user = self._users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        return user
    
    def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp"""
        user = self._users.get(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
    
    def delete_user(self, user_id: uuid.UUID) -> bool:
        """Soft delete user (set inactive)"""
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False
    
    def create_profile(self, profile: UserProfile) -> UserProfile:
        """Create user profile"""
        self._profiles[profile.user_id] = profile
        return profile
    
    def get_profile(self, user_id: uuid.UUID) -> Optional[UserProfile]:
        """Get user profile"""
        return self._profiles.get(user_id)
    
    def update_profile(
        self,
        user_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> UserProfile:
        """Update user profile"""
        profile = self._profiles.get(user_id)
        if not profile:
            raise ValueError("Profile not found")
        
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        return profile
