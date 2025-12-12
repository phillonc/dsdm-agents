"""
Main Flask application factory and configuration.
"""
import os
from flask import Flask
from flask_login import LoginManager
from src.models import db, User
from src.routes import bp
from src.reminder_service import reminder_service
from config.config import config


def create_app(config_name=None):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize reminder service
    reminder_service.init_app(app)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
