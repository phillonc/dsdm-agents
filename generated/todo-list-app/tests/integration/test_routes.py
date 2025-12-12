"""
Integration tests for application routes.
"""
from datetime import datetime, timedelta
from src.models import db, User, Task


def test_index_redirect_to_login(client):
    """Test that index redirects to login for unauthenticated users."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.location


def test_index_redirect_to_dashboard(authenticated_client):
    """Test that index redirects to dashboard for authenticated users."""
    response = authenticated_client.get('/')
    assert response.status_code == 302
    assert '/dashboard' in response.location


def test_register_page_loads(client):
    """Test that registration page loads."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Create Account' in response.data


def test_user_registration(client, app):
    """Test user registration flow."""
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@example.com'


def test_duplicate_username_registration(client, user):
    """Test that duplicate username registration fails."""
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'different@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    
    assert b'Username already taken' in response.data


def test_login_page_loads(client):
    """Test that login page loads."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Welcome Back' in response.data


def test_user_login(client, user):
    """Test user login flow."""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Welcome back' in response.data


def test_invalid_login(client, user):
    """Test login with invalid credentials."""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    
    assert b'Invalid username or password' in response.data


def test_logout(authenticated_client):
    """Test user logout."""
    response = authenticated_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'logged out successfully' in response.data


def test_dashboard_requires_login(client):
    """Test that dashboard requires authentication."""
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.location


def test_dashboard_loads(authenticated_client):
    """Test that dashboard loads for authenticated users."""
    response = authenticated_client.get('/dashboard')
    assert response.status_code == 200
    assert b'My Tasks' in response.data


def test_create_task_page_loads(authenticated_client):
    """Test that create task page loads."""
    response = authenticated_client.get('/task/create')
    assert response.status_code == 200
    assert b'Create Task' in response.data


def test_create_task(authenticated_client, user, app):
    """Test task creation."""
    response = authenticated_client.post('/task/create', data={
        'title': 'New Task',
        'description': 'Task Description',
        'due_date': '',
        'completed': False
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Task created successfully' in response.data
    
    with app.app_context():
        task = Task.query.filter_by(title='New Task').first()
        assert task is not None
        assert task.description == 'Task Description'
        assert task.user_id == user.id


def test_edit_task_page_loads(authenticated_client, user, app):
    """Test that edit task page loads."""
    with app.app_context():
        task = Task(title='Edit Me', user_id=user.id)
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    
    response = authenticated_client.get(f'/task/{task_id}/edit')
    assert response.status_code == 200
    assert b'Edit Task' in response.data
    assert b'Edit Me' in response.data


def test_edit_task(authenticated_client, user, app):
    """Test task editing."""
    with app.app_context():
        task = Task(title='Original Title', user_id=user.id)
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    
    response = authenticated_client.post(f'/task/{task_id}/edit', data={
        'title': 'Updated Title',
        'description': 'Updated Description',
        'due_date': '',
        'completed': True
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Task updated successfully' in response.data
    
    with app.app_context():
        updated_task = Task.query.get(task_id)
        assert updated_task.title == 'Updated Title'
        assert updated_task.description == 'Updated Description'
        assert updated_task.completed is True


def test_delete_task(authenticated_client, user, app):
    """Test task deletion."""
    with app.app_context():
        task = Task(title='Delete Me', user_id=user.id)
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    
    response = authenticated_client.post(f'/task/{task_id}/delete', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Task deleted successfully' in response.data
    
    with app.app_context():
        deleted_task = Task.query.get(task_id)
        assert deleted_task is None


def test_toggle_task_completion(authenticated_client, user, app):
    """Test toggling task completion status."""
    with app.app_context():
        task = Task(title='Toggle Me', completed=False, user_id=user.id)
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    
    response = authenticated_client.post(f'/task/{task_id}/toggle', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Task completed' in response.data
    
    with app.app_context():
        toggled_task = Task.query.get(task_id)
        assert toggled_task.completed is True


def test_user_can_only_access_own_tasks(client, user, app):
    """Test that users can only access their own tasks."""
    # Create another user and their task
    with app.app_context():
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()
        
        other_task = Task(title='Other User Task', user_id=other_user.id)
        db.session.add(other_task)
        db.session.commit()
        other_task_id = other_task.id
    
    # Login as first user
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    # Try to access other user's task
    response = client.get(f'/task/{other_task_id}/edit', follow_redirects=True)
    assert b'do not have permission' in response.data


def test_task_filtering(authenticated_client, user, app):
    """Test task filtering on dashboard."""
    with app.app_context():
        # Create various tasks
        task1 = Task(title='Active Task', completed=False, user_id=user.id)
        task2 = Task(title='Completed Task', completed=True, user_id=user.id)
        db.session.add_all([task1, task2])
        db.session.commit()
    
    # Test active filter
    response = authenticated_client.get('/dashboard?filter=active')
    assert response.status_code == 200
    assert b'Active Task' in response.data
    
    # Test completed filter
    response = authenticated_client.get('/dashboard?filter=completed')
    assert response.status_code == 200
    assert b'Completed Task' in response.data
