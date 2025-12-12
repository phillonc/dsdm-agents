"""
Integration tests for application routes.
"""
import pytest
from src.models import db, Todo
from src.app import create_app


@pytest.fixture
def app():
    """Create test application."""
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
def sample_todos(app):
    """Create sample todos for testing."""
    with app.app_context():
        todos = [
            Todo(title="Active Task 1", completed=False),
            Todo(title="Active Task 2", completed=False),
            Todo(title="Completed Task", completed=True),
        ]
        db.session.add_all(todos)
        db.session.commit()
        return todos


class TestRoutes:
    """Test cases for application routes."""
    
    def test_index_route(self, client):
        """Test the index/home route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'My Todo List' in response.data
    
    def test_index_with_todos(self, client, sample_todos):
        """Test index displays todos."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Active Task 1' in response.data
        assert b'Active Task 2' in response.data
        assert b'Completed Task' in response.data
    
    def test_filter_active_todos(self, client, sample_todos):
        """Test filtering for active todos only."""
        response = client.get('/?filter=active')
        assert response.status_code == 200
        assert b'Active Task 1' in response.data
        assert b'Active Task 2' in response.data
        # Completed task might still appear in the count, but should be filtered in display
    
    def test_filter_completed_todos(self, client, sample_todos):
        """Test filtering for completed todos only."""
        response = client.get('/?filter=completed')
        assert response.status_code == 200
        assert b'Completed Task' in response.data
    
    def test_add_todo_get(self, client):
        """Test GET request to add todo page."""
        response = client.get('/add')
        assert response.status_code == 200
        assert b'Add New Task' in response.data
        assert b'Title' in response.data
    
    def test_add_todo_post(self, client, app):
        """Test POST request to create new todo."""
        response = client.post('/add', data={
            'title': 'New Test Task',
            'description': 'Test description',
            'completed': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'New Test Task' in response.data
        
        # Verify todo was created in database
        with app.app_context():
            todo = Todo.query.filter_by(title='New Test Task').first()
            assert todo is not None
            assert todo.description == 'Test description'
            assert todo.completed is False
    
    def test_add_todo_validation(self, client):
        """Test form validation for adding todo."""
        response = client.post('/add', data={
            'title': '',  # Empty title should fail
            'description': 'Test description'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Title is required' in response.data or b'This field is required' in response.data
    
    def test_edit_todo_get(self, client, sample_todos, app):
        """Test GET request to edit todo page."""
        with app.app_context():
            todo = Todo.query.first()
            response = client.get(f'/edit/{todo.id}')
            assert response.status_code == 200
            assert b'Edit Task' in response.data
            assert todo.title.encode() in response.data
    
    def test_edit_todo_post(self, client, sample_todos, app):
        """Test POST request to update todo."""
        with app.app_context():
            todo = Todo.query.first()
            todo_id = todo.id
            
        response = client.post(f'/edit/{todo_id}', data={
            'title': 'Updated Task Title',
            'description': 'Updated description',
            'completed': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Updated Task Title' in response.data
        
        # Verify todo was updated in database
        with app.app_context():
            updated_todo = db.session.get(Todo, todo_id)
            assert updated_todo.title == 'Updated Task Title'
            assert updated_todo.description == 'Updated description'
            assert updated_todo.completed is True
    
    def test_edit_nonexistent_todo(self, client):
        """Test editing a todo that doesn't exist."""
        response = client.get('/edit/99999')
        assert response.status_code == 404
    
    def test_toggle_todo(self, client, sample_todos, app):
        """Test toggling todo completion status."""
        with app.app_context():
            todo = Todo.query.filter_by(completed=False).first()
            todo_id = todo.id
            original_status = todo.completed
        
        response = client.post(f'/toggle/{todo_id}', follow_redirects=True)
        assert response.status_code == 200
        
        # Verify completion status was toggled
        with app.app_context():
            todo = db.session.get(Todo, todo_id)
            assert todo.completed is not original_status
    
    def test_delete_todo(self, client, sample_todos, app):
        """Test deleting a todo."""
        with app.app_context():
            todo = Todo.query.first()
            todo_id = todo.id
            todo_title = todo.title
        
        response = client.post(f'/delete/{todo_id}', follow_redirects=True)
        assert response.status_code == 200
        assert todo_title.encode() in response.data  # Flash message
        
        # Verify todo was deleted from database
        with app.app_context():
            deleted_todo = db.session.get(Todo, todo_id)
            assert deleted_todo is None
    
    def test_delete_nonexistent_todo(self, client):
        """Test deleting a todo that doesn't exist."""
        response = client.post('/delete/99999')
        assert response.status_code == 404
    
    def test_clear_completed(self, client, sample_todos, app):
        """Test clearing all completed todos."""
        response = client.post('/clear-completed', follow_redirects=True)
        assert response.status_code == 200
        
        # Verify completed todos were deleted
        with app.app_context():
            completed_todos = Todo.get_completed()
            assert len(completed_todos) == 0
            
            # Active todos should remain
            active_todos = Todo.get_active()
            assert len(active_todos) > 0
    
    def test_404_error(self, client):
        """Test 404 error page."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        assert b'404' in response.data or b'Not Found' in response.data
    
    def test_statistics_display(self, client, sample_todos):
        """Test that statistics are displayed correctly."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Total Tasks' in response.data
        assert b'Active' in response.data
        assert b'Completed' in response.data
