# Todo List Web Application

A simple, secure, and elegant todo list application with user authentication, task management, and due date reminders. Built following DSDM (Dynamic Systems Development Method) principles.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### ✅ Must Have (Implemented)
- **User Authentication**: Secure registration, login, and logout
- **Task Management**: Create, read, update, and delete tasks
- **Task Details**: Title, description, due dates, and completion status
- **Task Filtering**: View all, active, completed, or due soon tasks
- **Due Date Reminders**: Background service checks for upcoming tasks
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Security**: Password hashing, CSRF protection, and session management

### 🎯 Key Capabilities
- Personal task lists isolated per user
- Real-time task statistics dashboard
- Overdue task detection and highlighting
- Task completion toggle with visual feedback
- Intuitive Bootstrap 5 UI with modern design
- SQLite database (easily upgradeable to PostgreSQL)

## Technology Stack

- **Backend**: Flask 3.0 (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (production: PostgreSQL)
- **Authentication**: Flask-Login with Werkzeug password hashing
- **Forms**: Flask-WTF with CSRF protection
- **Scheduler**: APScheduler for reminder checks
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Testing**: Pytest with fixtures and mocks

## Architecture

```
todo-list-app/
├── src/
│   ├── app.py              # Application factory
│   ├── models.py           # Database models
│   ├── routes.py           # View functions and routes
│   ├── forms.py            # WTForms for validation
│   └── reminder_service.py # Background reminder checker
├── templates/
│   ├── base.html           # Base template
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── dashboard.html      # Main task dashboard
│   └── task_form.html      # Task create/edit form
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── config/
│   └── config.py           # Configuration settings
├── docs/                   # Documentation
└── requirements.txt        # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd todo-list-app
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your configuration (especially `SECRET_KEY` for production).

6. **Initialize the database**:
   The database will be created automatically on first run.

### Running the Application

**Development Mode**:
```bash
export FLASK_APP=src.app
export FLASK_ENV=development
flask run
```

Or simply:
```bash
python src/app.py
```

The application will be available at `http://localhost:5000`

**Production Mode** (using Gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:8000 "src.app:create_app('production')"
```

## Usage Guide

### 1. Register a New Account
- Navigate to `/register`
- Enter username, email, and password
- Click "Register"

### 2. Login
- Navigate to `/login`
- Enter your credentials
- Optionally check "Remember Me"

### 3. Create Tasks
- Click "New Task" button
- Enter task title (required)
- Add description (optional)
- Set due date (optional) for reminders
- Click "Create"

### 4. Manage Tasks
- **Complete**: Click the circle icon to mark as complete
- **Edit**: Click the pencil icon to modify task details
- **Delete**: Click the trash icon to remove the task

### 5. Filter Tasks
- **All**: View all tasks
- **Active**: View incomplete tasks only
- **Completed**: View finished tasks only
- **Due Soon**: View tasks with upcoming due dates

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v
```

### Test Coverage
- **Unit Tests**: Models, forms, and business logic
- **Integration Tests**: Routes, authentication, and user workflows
- **Fixtures**: Reusable test data and authenticated clients

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Flask Configuration
FLASK_APP=src.app
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database Configuration
DATABASE_URL=sqlite:///todo.db

# Security
SESSION_COOKIE_SECURE=False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Reminder Configuration
ENABLE_REMINDERS=True
REMINDER_CHECK_INTERVAL=3600  # Check every hour (in seconds)
```

### Database Configuration

**Development** (SQLite):
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///todo.db'
```

**Production** (PostgreSQL):
```python
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/todoapp'
```

## Security Features

1. **Password Security**:
   - Werkzeug SHA256 password hashing
   - Passwords never stored in plain text

2. **CSRF Protection**:
   - Flask-WTF CSRF tokens on all forms
   - Prevents cross-site request forgery

3. **Session Security**:
   - Secure session cookies (HTTPS recommended)
   - HTTP-only cookies to prevent XSS
   - SameSite attribute for CSRF protection

4. **SQL Injection Prevention**:
   - SQLAlchemy ORM parameterized queries
   - No raw SQL execution

5. **XSS Prevention**:
   - Jinja2 template auto-escaping
   - Content Security Policy headers recommended

## API Design

### Authentication Routes
- `GET /register` - Registration form
- `POST /register` - Create new user
- `GET /login` - Login form
- `POST /login` - Authenticate user
- `GET /logout` - Logout current user

### Task Routes (Authenticated)
- `GET /dashboard` - View all tasks
- `GET /dashboard?filter=<type>` - Filtered task view
- `GET /task/create` - Task creation form
- `POST /task/create` - Create new task
- `GET /task/<id>/edit` - Task edit form
- `POST /task/<id>/edit` - Update task
- `POST /task/<id>/delete` - Delete task
- `POST /task/<id>/toggle` - Toggle completion

## Database Schema

### Users Table
```sql
- id (INTEGER, PRIMARY KEY)
- username (STRING, UNIQUE, INDEXED)
- email (STRING, UNIQUE, INDEXED)
- password_hash (STRING)
- created_at (DATETIME)
```

### Tasks Table
```sql
- id (INTEGER, PRIMARY KEY)
- title (STRING)
- description (TEXT)
- completed (BOOLEAN, INDEXED)
- due_date (DATETIME, INDEXED)
- reminder_sent (BOOLEAN)
- created_at (DATETIME)
- updated_at (DATETIME)
- user_id (INTEGER, FOREIGN KEY, INDEXED)
```

## Deployment

### Production Checklist

- [ ] Set strong `SECRET_KEY` in environment
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable `SESSION_COOKIE_SECURE` (requires HTTPS)
- [ ] Set `FLASK_ENV=production`
- [ ] Use Gunicorn or uWSGI as WSGI server
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Configure proper logging
- [ ] Set up database backups
- [ ] Use environment-specific configuration
- [ ] Enable HTTPS/SSL certificates

### Example Gunicorn Production Command
```bash
gunicorn -w 4 \
         -b 0.0.0.0:8000 \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         --log-level info \
         "src.app:create_app('production')"
```

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "src.app:create_app('production')"]
```

Build and run:
```bash
docker build -t todo-app .
docker run -p 8000:8000 -e SECRET_KEY=your-secret todo-app
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'src'`
- **Solution**: Ensure you're running from the project root and virtual environment is activated

**Issue**: Database errors on startup
- **Solution**: Delete `todo.db` and restart (will recreate fresh database)

**Issue**: CSRF token errors
- **Solution**: Clear browser cookies and restart the server

**Issue**: Reminder service not running
- **Solution**: Check `ENABLE_REMINDERS=True` in `.env` and restart application

## Contributing

This project was built following DSDM principles:
1. Focus on business need
2. Deliver on time
3. Collaborate
4. Never compromise quality
5. Build incrementally

To contribute:
1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation in `docs/`
- Review the feasibility report in `docs/FEASIBILITY_REPORT.md`

## Acknowledgments

- Flask documentation and community
- Bootstrap team for excellent UI framework
- DSDM Consortium for methodology guidance

---

**Built with ❤️ using DSDM methodology**
