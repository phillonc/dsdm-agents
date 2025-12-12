"""
Unit tests for WTForms.
"""
from src.forms import RegistrationForm, LoginForm, TaskForm


def test_registration_form_validation(app):
    """Test registration form validation."""
    with app.test_request_context():
        form = RegistrationForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert form.validate()


def test_registration_form_password_mismatch(app):
    """Test registration form with mismatched passwords."""
    with app.test_request_context():
        form = RegistrationForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'different'
        })
        assert not form.validate()
        assert 'Passwords must match' in str(form.confirm_password.errors)


def test_registration_form_invalid_email(app):
    """Test registration form with invalid email."""
    with app.test_request_context():
        form = RegistrationForm(data={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert not form.validate()


def test_login_form_validation(app):
    """Test login form validation."""
    with app.test_request_context():
        form = LoginForm(data={
            'username': 'testuser',
            'password': 'password123'
        })
        assert form.validate()


def test_task_form_validation(app):
    """Test task form validation."""
    with app.test_request_context():
        form = TaskForm(data={
            'title': 'Test Task',
            'description': 'Test Description',
            'completed': False
        })
        assert form.validate()


def test_task_form_title_required(app):
    """Test that task title is required."""
    with app.test_request_context():
        form = TaskForm(data={
            'title': '',
            'description': 'Test Description'
        })
        assert not form.validate()
