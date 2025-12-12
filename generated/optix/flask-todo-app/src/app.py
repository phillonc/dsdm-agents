"""
Flask Todo List Application - Main Application Module

A simple, elegant todo list application built with Flask and SQLAlchemy.
"""
import os
from flask import Flask, render_template, redirect, url_for, flash, request
from models import db, Todo
from forms import TodoForm, DeleteForm


def create_app(config=None):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config (dict): Optional configuration dictionary
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///todos.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Apply custom config if provided
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Routes
    @app.route('/')
    def index():
        """
        Home page showing all todos with filter options.
        """
        # Get filter parameter
        filter_type = request.args.get('filter', 'all')
        
        # Fetch todos based on filter
        if filter_type == 'active':
            todos = Todo.get_active()
        elif filter_type == 'completed':
            todos = Todo.get_completed()
        else:
            todos = Todo.get_all()
        
        # Create delete forms for each todo (CSRF protection)
        delete_forms = {todo.id: DeleteForm() for todo in todos}
        
        # Count statistics
        total_count = Todo.query.count()
        active_count = Todo.query.filter_by(completed=False).count()
        completed_count = Todo.query.filter_by(completed=True).count()
        
        return render_template(
            'index.html',
            todos=todos,
            delete_forms=delete_forms,
            filter_type=filter_type,
            total_count=total_count,
            active_count=active_count,
            completed_count=completed_count
        )
    
    @app.route('/add', methods=['GET', 'POST'])
    def add_todo():
        """
        Add a new todo item.
        """
        form = TodoForm()
        
        if form.validate_on_submit():
            todo = Todo(
                title=form.title.data,
                description=form.description.data,
                completed=form.completed.data
            )
            db.session.add(todo)
            db.session.commit()
            
            flash(f'Task "{todo.title}" added successfully!', 'success')
            return redirect(url_for('index'))
        
        return render_template('todo_form.html', form=form, title='Add New Task', action='Add')
    
    @app.route('/edit/<int:todo_id>', methods=['GET', 'POST'])
    def edit_todo(todo_id):
        """
        Edit an existing todo item.
        
        Args:
            todo_id (int): ID of the todo to edit
        """
        todo = Todo.query.get_or_404(todo_id)
        form = TodoForm(obj=todo)
        
        if form.validate_on_submit():
            todo.title = form.title.data
            todo.description = form.description.data
            todo.completed = form.completed.data
            db.session.commit()
            
            flash(f'Task "{todo.title}" updated successfully!', 'success')
            return redirect(url_for('index'))
        
        return render_template('todo_form.html', form=form, title='Edit Task', action='Update')
    
    @app.route('/toggle/<int:todo_id>', methods=['POST'])
    def toggle_todo(todo_id):
        """
        Toggle the completion status of a todo.
        
        Args:
            todo_id (int): ID of the todo to toggle
        """
        todo = Todo.query.get_or_404(todo_id)
        todo.toggle_completion()
        db.session.commit()
        
        status = "completed" if todo.completed else "reactivated"
        flash(f'Task "{todo.title}" {status}!', 'success')
        
        return redirect(url_for('index'))
    
    @app.route('/delete/<int:todo_id>', methods=['POST'])
    def delete_todo(todo_id):
        """
        Delete a todo item.
        
        Args:
            todo_id (int): ID of the todo to delete
        """
        form = DeleteForm()
        
        if form.validate_on_submit():
            todo = Todo.query.get_or_404(todo_id)
            title = todo.title
            db.session.delete(todo)
            db.session.commit()
            
            flash(f'Task "{title}" deleted successfully!', 'success')
        
        return redirect(url_for('index'))
    
    @app.route('/clear-completed', methods=['POST'])
    def clear_completed():
        """
        Delete all completed todos.
        """
        completed_todos = Todo.get_completed()
        count = len(completed_todos)
        
        for todo in completed_todos:
            db.session.delete(todo)
        
        db.session.commit()
        flash(f'{count} completed task(s) cleared!', 'success')
        
        return redirect(url_for('index'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
