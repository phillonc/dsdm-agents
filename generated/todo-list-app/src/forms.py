"""
WTForms for user input validation.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, DateTimeLocalField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from src.models import User


class RegistrationForm(FlaskForm):
    """User registration form."""
    
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    
    def validate_username(self, username):
        """Check if username already exists."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')


class LoginForm(FlaskForm):
    """User login form."""
    
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class TaskForm(FlaskForm):
    """Task creation/editing form."""
    
    title = StringField('Title', validators=[
        DataRequired(),
        Length(max=200, message='Title must be less than 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000, message='Description must be less than 1000 characters')
    ])
    due_date = DateTimeLocalField('Due Date', validators=[Optional()], format='%Y-%m-%dT%H:%M')
    completed = BooleanField('Completed')
