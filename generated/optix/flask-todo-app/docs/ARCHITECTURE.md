# Architecture Documentation - Flask Todo App

## System Overview

The Flask Todo Application follows a traditional MVC (Model-View-Controller) architecture pattern, adapted for Flask's conventions.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Client Browser                       │
│                 (HTML/CSS/JavaScript)                    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    Flask Application                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │               Routes (app.py)                    │   │
│  │  - Index / List        - Toggle Completion       │   │
│  │  - Add Todo            - Delete Todo             │   │
│  │  - Edit Todo           - Clear Completed         │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────┐   │
│  │           Forms (forms.py)                       │   │
│  │  - TodoForm (Create/Edit)                        │   │
│  │  - DeleteForm (CSRF Protection)                  │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼──────────────────────────────────┐   │
│  │          Models (models.py)                      │   │
│  │  - Todo Model (SQLAlchemy ORM)                   │   │
│  │  - Database Operations                           │   │
│  └──────────────┬──────────────────────────────────┘   │
└─────────────────┼────────────────────────────────────────┘
                  │ SQL
                  ▼
┌─────────────────────────────────────────────────────────┐
│                   SQLite Database                        │
│                     (todos.db)                           │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Application Layer (app.py)

**Responsibilities:**
- Route handling and request processing
- Business logic coordination
- Response generation
- Error handling

**Key Functions:**
```python
create_app()      # Application factory
index()           # Home page with task list
add_todo()        # Create new task
edit_todo()       # Update existing task
toggle_todo()     # Toggle completion status
delete_todo()     # Delete single task
clear_completed() # Delete all completed tasks
```

**Design Patterns:**
- Application Factory Pattern
- Dependency Injection (database, forms)
- Separation of Concerns

---

### 2. Data Layer (models.py)

**Responsibilities:**
- Database schema definition
- Data validation
- Business logic for data operations
- Query methods

**Todo Model:**
```python
class Todo(db.Model):
    - id: Integer (Primary Key)
    - title: String(200)
    - description: Text
    - completed: Boolean
    - created_at: DateTime
    - updated_at: DateTime
```

**Methods:**
- `get_all()` - Retrieve all todos
- `get_active()` - Get incomplete todos
- `get_completed()` - Get completed todos
- `toggle_completion()` - Toggle status
- `to_dict()` - JSON serialization

---

### 3. Presentation Layer (templates/)

**Template Hierarchy:**
```
base.html
├── index.html          # Task list view
├── todo_form.html      # Add/Edit form
└── errors/
    ├── 404.html        # Not Found
    └── 500.html        # Server Error
```

**Template Features:**
- Jinja2 template inheritance
- Responsive Bootstrap 5 design
- Font Awesome icons
- Client-side form validation
- Flash message handling

---

### 4. Form Layer (forms.py)

**Responsibilities:**
- Input validation
- CSRF protection
- Form rendering
- Error message generation

**Forms:**
```python
TodoForm      # Create/Edit tasks
DeleteForm    # Delete confirmation (CSRF)
```

**Validation Rules:**
- Title: Required, 1-200 characters
- Description: Optional, max 1000 characters
- Completed: Boolean checkbox

---

### 5. Configuration Layer (config/config.py)

**Environment Configurations:**
- **Development:** Debug enabled, SQLite database
- **Testing:** In-memory database, CSRF disabled
- **Production:** Debug disabled, secure settings

**Configuration Options:**
- SECRET_KEY: Session encryption
- DATABASE_URL: Database connection
- SQLALCHEMY_TRACK_MODIFICATIONS: False (performance)
- WTF_CSRF_ENABLED: CSRF protection toggle

---

## Data Flow

### Creating a Todo

```
1. User submits form
   ↓
2. POST /add
   ↓
3. TodoForm validates input
   ↓
4. Create Todo object
   ↓
5. db.session.add(todo)
   ↓
6. db.session.commit()
   ↓
7. Flash success message
   ↓
8. Redirect to index
   ↓
9. Render updated task list
```

### Toggling Todo Status

```
1. User clicks toggle button
   ↓
2. POST /toggle/<id>
   ↓
3. Query todo by ID
   ↓
4. todo.toggle_completion()
   ↓
5. db.session.commit()
   ↓
6. Flash message
   ↓
7. Redirect to index
```

---

## Database Schema

### Todos Table

```sql
CREATE TABLE todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_completed ON todos(completed);
CREATE INDEX idx_created_at ON todos(created_at DESC);
```

---

## Security Architecture

### 1. CSRF Protection
- Token generated for each session
- Validated on all POST requests
- Implemented via Flask-WTF

### 2. SQL Injection Prevention
- SQLAlchemy ORM with parameterized queries
- No raw SQL execution
- Input sanitization

### 3. XSS Protection
- Jinja2 auto-escaping enabled
- User input sanitized in templates
- No `|safe` filter on user content

### 4. Session Security
- Secure session cookies
- Secret key for encryption
- HTTPOnly cookies (production)

---

## Scalability Considerations

### Current Limitations
- Single-threaded Flask development server
- SQLite (not suitable for high concurrency)
- No caching layer
- No load balancing

### Scalability Improvements

**Phase 1: Production Server**
```
Flask App → Gunicorn/uWSGI → Nginx
```

**Phase 2: Database Upgrade**
```
SQLite → PostgreSQL/MySQL
+ Connection pooling
+ Read replicas
```

**Phase 3: Caching**
```
+ Redis for session storage
+ Memcached for query caching
```

**Phase 4: Horizontal Scaling**
```
Load Balancer → Multiple App Instances
+ Shared database
+ Shared cache
+ Shared file storage
```

---

## Testing Architecture

### Test Structure
```
tests/
├── test_models.py      # Unit tests (models)
├── test_routes.py      # Integration tests (routes)
└── conftest.py         # Shared fixtures
```

### Test Coverage
- **Models:** CRUD operations, validations
- **Routes:** HTTP methods, redirects, errors
- **Forms:** Validation rules, CSRF tokens

### Testing Strategy
```python
# Arrange
app = create_test_app()
todo = create_sample_todo()

# Act
response = client.post('/toggle/1')

# Assert
assert response.status_code == 302
assert todo.completed == True
```

---

## Performance Optimization

### Database Optimization
- Indexes on frequently queried columns
- Lazy loading for relationships
- Query result caching (future)

### Application Optimization
- Template caching (production)
- Static file compression
- CDN for Bootstrap/Font Awesome

### Frontend Optimization
- Minified CSS/JS (production)
- Browser caching headers
- Lazy loading for images

---

## Deployment Architecture

### Development
```
python app.py
→ Flask dev server (localhost:5000)
→ SQLite database
```

### Production (Recommended)
```
User → Nginx (Reverse Proxy)
     → Gunicorn (WSGI Server)
          → Flask App (Multiple Workers)
               → PostgreSQL Database
```

**Production Stack:**
- **Web Server:** Nginx
- **WSGI Server:** Gunicorn (4 workers)
- **Database:** PostgreSQL
- **Cache:** Redis
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack

---

## Error Handling

### Error Flow
```
Exception Raised
    ↓
Flask Error Handler
    ↓
Rollback Database Session (if needed)
    ↓
Log Error
    ↓
Render Error Page (404/500)
```

### Error Types
- **404:** Resource not found
- **500:** Server error (automatic rollback)
- **400:** Bad request (form validation)

---

## Extension Points

### Future Enhancements

**1. Authentication System**
```python
from flask_login import LoginManager

# Add User model
# Add login/logout routes
# Protect routes with @login_required
```

**2. REST API**
```python
from flask_restful import Api, Resource

# Add JSON endpoints
# API authentication (JWT)
# Versioning (/api/v1/)
```

**3. WebSocket Support**
```python
from flask_socketio import SocketIO

# Real-time updates
# Multi-user sync
# Live notifications
```

**4. Background Tasks**
```python
from celery import Celery

# Email reminders
# Scheduled tasks
# Data export jobs
```

---

## Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Flask | 3.0.0 |
| ORM | SQLAlchemy | 3.1.1 |
| Forms | Flask-WTF | 1.2.1 |
| Database | SQLite | 3.x |
| Frontend | Bootstrap | 5.3.0 |
| Icons | Font Awesome | 6.4.0 |
| Testing | pytest | 7.4.3 |

---

## Maintenance Guidelines

### Regular Tasks
- [ ] Update dependencies (monthly)
- [ ] Review security advisories
- [ ] Backup database (production)
- [ ] Monitor error logs
- [ ] Review performance metrics

### Update Process
```bash
# Check for updates
pip list --outdated

# Update dependencies
pip install --upgrade flask flask-sqlalchemy

# Run tests
pytest

# Update requirements.txt
pip freeze > requirements.txt
```

---

## Conclusion

This architecture provides a solid foundation for a todo list application with:
- Clear separation of concerns
- Scalability path
- Security best practices
- Comprehensive testing
- Easy maintenance

For questions or improvements, refer to the [README](../README.md) or create an issue.
