"""
Form classes for todo list application using Flask-WTF.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class TodoForm(FlaskForm):
    """
    Form for creating and editing todo items.
    
    Fields:
        title: Required field for task title (max 200 chars)
        description: Optional field for detailed description
        completed: Checkbox for completion status
        submit: Submit button
    """
    title = StringField(
        'Title',
        validators=[
            DataRequired(message='Title is required'),
            Length(min=1, max=200, message='Title must be between 1 and 200 characters')
        ],
        render_kw={'placeholder': 'Enter task title...', 'class': 'form-control'}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Length(max=1000, message='Description cannot exceed 1000 characters')],
        render_kw={'placeholder': 'Optional description...', 'class': 'form-control', 'rows': 3}
    )
    
    completed = BooleanField(
        'Completed',
        render_kw={'class': 'form-check-input'}
    )
    
    submit = SubmitField('Save Task', render_kw={'class': 'btn btn-primary'})


class DeleteForm(FlaskForm):
    """
    Simple form for delete confirmation with CSRF protection.
    """
    submit = SubmitField('Delete', render_kw={'class': 'btn btn-danger btn-sm'})
