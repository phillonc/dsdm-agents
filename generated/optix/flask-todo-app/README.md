# Flask Todo List Application

A simple, elegant, and fully-featured todo list web application built with Flask, SQLAlchemy, and Bootstrap.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- ✅ **Create Tasks** - Add new todo items with titles and descriptions
- 📋 **View Tasks** - Display all tasks with filtering options (All/Active/Completed)
- ✏️ **Edit Tasks** - Update task details and completion status
- 🔄 **Toggle Completion** - Quick toggle between complete/incomplete
- 🗑️ **Delete Tasks** - Remove individual tasks or clear all completed tasks
- 📊 **Statistics Dashboard** - Track total, active, and completed tasks
- 🎨 **Modern UI** - Clean, responsive design with Bootstrap 5
- 🔒 **CSRF Protection** - Secure forms with Flask-WTF
- 💾 **Data Persistence** - SQLite database with SQLAlchemy ORM

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd flask-todo-app
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run the application:**
   ```bash
   cd src
   python app.py
   ```

7. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

## 📁 Project Structure

```
flask-todo-app/
├── src/
│   ├── app.py              # Main application file
│   ├── models.py           # Database models
│   ├── forms.py            # WTForms form classes
│   └── templates/          # HTML templates
│       ├── base.html       # Base template
│       ├── index.html      # Home page
│       ├── todo_form.html  # Add/Edit form
│       └── errors/         # Error pages
│           ├── 404.html
│           └── 500.html
├── tests/
│   ├── test_models.py      # Model unit tests
│   └── test_routes.py      # Route integration tests
├── config/
│   └── config.py           # Configuration settings
├── docs/
│   └── FEASIBILITY_REPORT.md
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## 🧪 Running Tests

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

## 🎯 Usage Guide

### Creating a Task

1. Click the "Add Task" button in the navigation bar
2. Enter a task title (required)
3. Optionally add a description
4. Click "Save Task"

### Editing a Task

1. Click the edit icon (✏️) next to any task
2. Modify the title, description, or completion status
3. Click "Update" to save changes

### Completing a Task

- Click the checkmark icon (✓) next to a task to mark it as complete
- Click the undo icon (↻) on a completed task to mark it as incomplete

### Filtering Tasks

Use the filter buttons to view:
- **All** - Show all tasks
- **Active** - Show only incomplete tasks
- **Completed** - Show only completed tasks

### Deleting Tasks

- Click the trash icon (🗑️) next to a task to delete it
- Click "Clear Completed" to delete all completed tasks at once

## 🔧 Configuration

The application can be configured through environment variables or the `config/config.py` file:

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///todos.db
FLASK_ENV=development
```

### Configuration Classes

- **DevelopmentConfig** - Debug mode enabled, SQLite database
- **TestingConfig** - In-memory database, CSRF disabled
- **ProductionConfig** - Debug disabled, requires SECRET_KEY

## 📊 Database Schema

### Todo Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| title | String(200) | Task title (required) |
| description | Text | Optional detailed description |
| completed | Boolean | Completion status (default: False) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

## 🛡️ Security Features

- **CSRF Protection** - All forms protected with Flask-WTF tokens
- **SQL Injection Prevention** - SQLAlchemy ORM with parameterized queries
- **Input Validation** - WTForms validation on all user inputs
- **Secure Session Management** - Flask secure session cookies

## 🎨 Technology Stack

- **Backend Framework:** Flask 3.0
- **Database ORM:** SQLAlchemy
- **Forms:** Flask-WTF + WTForms
- **Frontend:** Bootstrap 5 + Font Awesome
- **Database:** SQLite (development)
- **Testing:** Pytest

## 📈 Performance

- Fast response times (<200ms for most operations)
- Lightweight SQLite database
- Efficient query patterns with SQLAlchemy
- Minimal JavaScript for enhanced user experience

## 🐛 Known Issues / Limitations

- Single-user application (no authentication)
- No real-time synchronization across devices
- SQLite not recommended for high-concurrency production use

## 🔮 Future Enhancements

- [ ] User authentication and multi-user support
- [ ] Task categories/tags
- [ ] Due dates and reminders
- [ ] Priority levels
- [ ] Task search functionality
- [ ] Export/Import tasks (JSON/CSV)
- [ ] Dark mode toggle
- [ ] Mobile application
- [ ] REST API endpoints

## 📝 Development

### Code Style

This project follows PEP 8 style guidelines:

```bash
# Check code style
flake8 src tests

# Format code
black src tests
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Author

Created as part of a DSDM (Dynamic Systems Development Method) feasibility study demonstration.

## 🙏 Acknowledgments

- Flask framework and community
- Bootstrap for the UI components
- Font Awesome for icons
- SQLAlchemy for database ORM

## 📞 Support

For issues, questions, or suggestions:
1. Check the [FEASIBILITY_REPORT.md](docs/FEASIBILITY_REPORT.md)
2. Review existing issues
3. Create a new issue with detailed information

---

**Happy Task Managing! 📝✨**
