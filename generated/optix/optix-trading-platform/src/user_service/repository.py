"""
User Service Repository
Data access layer for user and profile management
"""
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
from .models import User, UserProfile


# Singleton storage - persists across requests (in-memory for demo)
# In production, this would be replaced with PostgreSQL database
_user_storage: Dict[uuid.UUID, User] = {}
_profile_storage: Dict[uuid.UUID, UserProfile] = {}
_email_index: Dict[str, uuid.UUID] = {}


class UserRepository:
    """
    User repository for database operations
    In production, this would interact with PostgreSQL
    Uses module-level singleton storage for persistence across requests
    """

    def __init__(self):
        # Use module-level singleton storage for persistence across requests
        # This ensures registered users persist until server restart
        self._users = _user_storage
        self._profiles = _profile_storage
        self._email_index = _email_index
    
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
