"""
Database models for the Todo List application.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Todo(db.Model):
    """
    Todo model representing a single task.
    
    Attributes:
        id (int): Primary key, auto-incremented
        title (str): Task title (required, max 200 chars)
        description (str): Optional detailed description
        completed (bool): Task completion status (default: False)
        created_at (datetime): Timestamp when task was created
        updated_at (datetime): Timestamp when task was last updated
    """
    __tablename__ = 'todos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        """String representation of Todo object."""
        status = "✓" if self.completed else "○"
        return f'<Todo {self.id}: {status} {self.title}>'
    
    def to_dict(self):
        """
        Convert Todo object to dictionary for JSON serialization.
        
        Returns:
            dict: Dictionary representation of the todo item
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_all(cls):
        """Get all todos ordered by creation date (newest first)."""
        return cls.query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_active(cls):
        """Get all incomplete todos."""
        return cls.query.filter_by(completed=False).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_completed(cls):
        """Get all completed todos."""
        return cls.query.filter_by(completed=True).order_by(cls.updated_at.desc()).all()
    
    def toggle_completion(self):
        """Toggle the completion status of the todo."""
        self.completed = not self.completed
        self.updated_at = datetime.utcnow()
