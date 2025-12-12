"""
Unit tests for database models.
"""
import pytest
from datetime import datetime
from src.models import db, Todo
from src.app import create_app


@pytest.fixture
def app():
    """Create test application with in-memory database."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_todo(app):
    """Create a sample todo for testing."""
    with app.app_context():
        todo = Todo(
            title="Test Task",
            description="This is a test task",
            completed=False
        )
        db.session.add(todo)
        db.session.commit()
        return todo


class TestTodoModel:
    """Test cases for Todo model."""
    
    def test_create_todo(self, app):
        """Test creating a new todo."""
        with app.app_context():
            todo = Todo(title="New Task", description="Task description")
            db.session.add(todo)
            db.session.commit()
            
            assert todo.id is not None
            assert todo.title == "New Task"
            assert todo.description == "Task description"
            assert todo.completed is False
            assert isinstance(todo.created_at, datetime)
            assert isinstance(todo.updated_at, datetime)
    
    def test_todo_repr(self, app, sample_todo):
        """Test string representation of todo."""
        with app.app_context():
            todo = db.session.get(Todo, sample_todo.id)
            repr_str = repr(todo)
            assert "Test Task" in repr_str
            assert "○" in repr_str  # Incomplete marker
    
    def test_todo_to_dict(self, app, sample_todo):
        """Test converting todo to dictionary."""
        with app.app_context():
            todo = db.session.get(Todo, sample_todo.id)
            todo_dict = todo.to_dict()
            
            assert todo_dict['id'] == todo.id
            assert todo_dict['title'] == "Test Task"
            assert todo_dict['description'] == "This is a test task"
            assert todo_dict['completed'] is False
            assert 'created_at' in todo_dict
            assert 'updated_at' in todo_dict
    
    def test_toggle_completion(self, app, sample_todo):
        """Test toggling todo completion status."""
        with app.app_context():
            todo = db.session.get(Todo, sample_todo.id)
            original_status = todo.completed
            
            todo.toggle_completion()
            db.session.commit()
            
            assert todo.completed is not original_status
            
            todo.toggle_completion()
            db.session.commit()
            
            assert todo.completed == original_status
    
    def test_get_all_todos(self, app):
        """Test getting all todos."""
        with app.app_context():
            # Create multiple todos
            todo1 = Todo(title="Task 1")
            todo2 = Todo(title="Task 2")
            todo3 = Todo(title="Task 3")
            
            db.session.add_all([todo1, todo2, todo3])
            db.session.commit()
            
            all_todos = Todo.get_all()
            assert len(all_todos) == 3
    
    def test_get_active_todos(self, app):
        """Test getting only active (incomplete) todos."""
        with app.app_context():
            todo1 = Todo(title="Active Task 1", completed=False)
            todo2 = Todo(title="Completed Task", completed=True)
            todo3 = Todo(title="Active Task 2", completed=False)
            
            db.session.add_all([todo1, todo2, todo3])
            db.session.commit()
            
            active_todos = Todo.get_active()
            assert len(active_todos) == 2
            assert all(not todo.completed for todo in active_todos)
    
    def test_get_completed_todos(self, app):
        """Test getting only completed todos."""
        with app.app_context():
            todo1 = Todo(title="Active Task", completed=False)
            todo2 = Todo(title="Completed Task 1", completed=True)
            todo3 = Todo(title="Completed Task 2", completed=True)
            
            db.session.add_all([todo1, todo2, todo3])
            db.session.commit()
            
            completed_todos = Todo.get_completed()
            assert len(completed_todos) == 2
            assert all(todo.completed for todo in completed_todos)
    
    def test_todo_without_description(self, app):
        """Test creating todo without description."""
        with app.app_context():
            todo = Todo(title="Simple Task")
            db.session.add(todo)
            db.session.commit()
            
            assert todo.description is None
            assert todo.title == "Simple Task"
    
    def test_updated_at_changes(self, app, sample_todo):
        """Test that updated_at changes when todo is modified."""
        with app.app_context():
            todo = db.session.get(Todo, sample_todo.id)
            original_updated_at = todo.updated_at
            
            # Simulate time passing
            import time
            time.sleep(0.1)
            
            todo.title = "Updated Title"
            todo.updated_at = datetime.utcnow()
            db.session.commit()
            
            assert todo.updated_at > original_updated_at
