"""
Application routes and view functions.
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User, Task
from src.forms import RegistrationForm, LoginForm, TaskForm

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Home page - redirect to login or dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.login'))


@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing user's tasks."""
    # Get filter parameter
    filter_type = request.args.get('filter', 'all')
    
    # Base query for current user's tasks
    query = Task.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if filter_type == 'active':
        query = query.filter_by(completed=False)
    elif filter_type == 'completed':
        query = query.filter_by(completed=True)
    elif filter_type == 'due_soon':
        now = datetime.utcnow()
        query = query.filter(
            Task.completed == False,
            Task.due_date.isnot(None),
            Task.due_date >= now
        )
    
    # Order by due date (nulls last), then by creation date
    tasks = query.order_by(
        Task.due_date.is_(None),
        Task.due_date.asc(),
        Task.created_at.desc()
    ).all()
    
    # Count statistics
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    active_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    
    # Check for overdue tasks
    now = datetime.utcnow()
    overdue_count = Task.query.filter(
        Task.user_id == current_user.id,
        Task.completed == False,
        Task.due_date.isnot(None),
        Task.due_date < now
    ).count()
    
    return render_template(
        'dashboard.html',
        tasks=tasks,
        filter_type=filter_type,
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
        overdue_count=overdue_count,
        now=now
    )


@bp.route('/task/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """Create a new task."""
    form = TaskForm()
    
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            completed=form.completed.data,
            user_id=current_user.id
        )
        
        db.session.add(task)
        db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('task_form.html', form=form, title='Create Task', action='Create')


@bp.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit an existing task."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure user owns this task
    if task.user_id != current_user.id:
        flash('You do not have permission to edit this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = TaskForm(obj=task)
    
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.completed = form.completed.data
        
        # Reset reminder if due date changed
        if form.due_date.data != task.due_date:
            task.reminder_sent = False
        
        db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('task_form.html', form=form, title='Edit Task', action='Update', task=task)


@bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure user owns this task
    if task.user_id != current_user.id:
        flash('You do not have permission to delete this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(task)
    db.session.commit()
    
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))


@bp.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    """Toggle task completion status."""
    task = Task.query.get_or_404(task_id)
    
    # Ensure user owns this task
    if task.user_id != current_user.id:
        flash('You do not have permission to modify this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    task.completed = not task.completed
    db.session.commit()
    
    status = 'completed' if task.completed else 'reopened'
    flash(f'Task {status}!', 'success')
    return redirect(url_for('main.dashboard'))
