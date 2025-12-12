"""
Pytest configuration and fixtures.
"""
import pytest
from src.app import create_app
from src.models import db, User, Task


@pytest.fixture
def app():
    """Create and configure a test application."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def user(app):
    """Create a test user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def authenticated_client(client, user):
    """Create a logged-in test client."""
    client.post('/login', data={
        'username': user.username,
        'password': 'password123'
    }, follow_redirects=True)
    return client
