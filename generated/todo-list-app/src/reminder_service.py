"""
Background service for checking and sending task reminders.
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from src.models import db, Task


class ReminderService:
    """Service to check for upcoming tasks and send reminders."""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler()
        
    def init_app(self, app):
        """Initialize the reminder service with the Flask app."""
        self.app = app
        
        if app.config.get('ENABLE_REMINDERS', True):
            interval = app.config.get('REMINDER_CHECK_INTERVAL', 3600)
            self.scheduler.add_job(
                func=self.check_reminders,
                trigger='interval',
                seconds=interval,
                id='reminder_check',
                name='Check task reminders',
                replace_existing=True
            )
            self.scheduler.start()
    
    def check_reminders(self):
        """Check for tasks with upcoming due dates and flag them for reminders."""
        if not self.app:
            return
        
        with self.app.app_context():
            try:
                # Find tasks due within the next 24 hours that haven't been reminded
                now = datetime.utcnow()
                tomorrow = now + timedelta(hours=24)
                
                tasks_to_remind = Task.query.filter(
                    Task.due_date.isnot(None),
                    Task.due_date <= tomorrow,
                    Task.due_date > now,
                    Task.completed == False,
                    Task.reminder_sent == False
                ).all()
                
                for task in tasks_to_remind:
                    # Mark reminder as sent
                    task.reminder_sent = True
                    
                    # In a real application, you would send an email or push notification here
                    # For this MVP, we'll just flag it in the database
                    # and show it in the UI as a "reminder pending"
                    
                    self.app.logger.info(
                        f'Reminder set for task {task.id}: "{task.title}" '
                        f'due at {task.due_date}'
                    )
                
                if tasks_to_remind:
                    db.session.commit()
                    self.app.logger.info(f'Processed {len(tasks_to_remind)} task reminders')
                    
            except Exception as e:
                self.app.logger.error(f'Error checking reminders: {str(e)}')
                db.session.rollback()
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown()


# Global instance
reminder_service = ReminderService()
