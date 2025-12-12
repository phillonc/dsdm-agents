# Quick Start Guide - Flask Todo App

Get your todo list application running in under 5 minutes!

## 🚀 Installation Steps

### Step 1: Set Up Python Environment

```bash
# Navigate to project directory
cd flask-todo-app

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
cd src
python app.py
```

### Step 4: Access the Application

Open your browser and go to: **http://localhost:5000**

## ✅ Verify Installation

You should see:
- A welcome page with task statistics (0/0/0)
- Navigation bar with "My Todo List" and "Add Task" button
- Empty state message prompting you to add your first task

## 🎯 First Tasks

1. **Create your first task:**
   - Click "Add Task"
   - Enter title: "Welcome to Todo List"
   - Add description: "This is my first task!"
   - Click "Save Task"

2. **Test task operations:**
   - Mark the task as complete (✓ button)
   - Edit the task (✏️ button)
   - Delete the task (🗑️ button)

## 🧪 Run Tests (Optional)

```bash
# From project root
pytest

# With coverage
pytest --cov=src
```

## ⚙️ Configuration (Optional)

Create a `.env` file for custom configuration:

```bash
cp .env.example .env
```

Edit `.env`:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///todos.db
FLASK_ENV=development
```

## 🛠️ Troubleshooting

### Port Already in Use
If port 5000 is busy, edit `src/app.py` line 182:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
```

### Import Errors
Ensure you're in the virtual environment:
```bash
which python  # Should show venv path
```

### Database Issues
Delete the database and restart:
```bash
rm instance/todos.db
python app.py
```

## 📚 Next Steps

- Read the [full README](../README.md) for detailed documentation
- Review the [Feasibility Report](FEASIBILITY_REPORT.md) for project details
- Explore the code in `src/` directory

## 🎉 You're Ready!

Your Flask Todo List application is now running. Start managing your tasks!
