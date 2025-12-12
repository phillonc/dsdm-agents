"""
Unit tests for database models.
"""
from datetime import datetime, timedelta
from src.models import User, Task


def test_user_password_hashing(app):
    """Test that passwords are properly hashed."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('secretpassword')
        
        assert user.password_hash != 'secretpassword'
        assert user.check_password('secretpassword')
        assert not user.check_password('wrongpassword')


def test_user_creation(app, user):
    """Test user creation and retrieval."""
    with app.app_context():
        retrieved_user = User.query.filter_by(username='testuser').first()
        assert retrieved_user is not None
        assert retrieved_user.username == 'testuser'
        assert retrieved_user.email == 'test@example.com'


def test_task_creation(app, user):
    """Test task creation."""
    with app.app_context():
        from src.models import db
        
        task = Task(
            title='Test Task',
            description='Test Description',
            user_id=user.id
        )
        db.session.add(task)
        db.session.commit()
        
        retrieved_task = Task.query.first()
        assert retrieved_task is not None
        assert retrieved_task.title == 'Test Task'
        assert retrieved_task.completed is False
        assert retrieved_task.reminder_sent is False


def test_task_completion(app, user):
    """Test task completion toggle."""
    with app.app_context():
        from src.models import db
        
        task = Task(title='Complete Me', user_id=user.id)
        db.session.add(task)
        db.session.commit()
        
        assert task.completed is False
        task.completed = True
        db.session.commit()
        
        updated_task = Task.query.first()
        assert updated_task.completed is True


def test_task_due_date(app, user):
    """Test task with due date."""
    with app.app_context():
        from src.models import db
        
        due_date = datetime.utcnow() + timedelta(days=7)
        task = Task(
            title='Task with Due Date',
            due_date=due_date,
            user_id=user.id
        )
        db.session.add(task)
        db.session.commit()
        
        retrieved_task = Task.query.first()
        assert retrieved_task.due_date is not None
        assert retrieved_task.due_date.date() == due_date.date()


def test_user_task_relationship(app, user):
    """Test relationship between users and tasks."""
    with app.app_context():
        from src.models import db
        
        task1 = Task(title='Task 1', user_id=user.id)
        task2 = Task(title='Task 2', user_id=user.id)
        db.session.add_all([task1, task2])
        db.session.commit()
        
        user_tasks = User.query.get(user.id).tasks.all()
        assert len(user_tasks) == 2
        assert all(task.user_id == user.id for task in user_tasks)


def test_task_to_dict(app, user):
    """Test task serialization to dictionary."""
    with app.app_context():
        from src.models import db
        
        task = Task(
            title='Serialize Me',
            description='Test description',
            user_id=user.id
        )
        db.session.add(task)
        db.session.commit()
        
        task_dict = task.to_dict()
        assert task_dict['title'] == 'Serialize Me'
        assert task_dict['description'] == 'Test description'
        assert task_dict['completed'] is False
        assert 'id' in task_dict
        assert 'created_at' in task_dict
