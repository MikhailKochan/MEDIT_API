from app import create_app, db, ext_celery
from app.models import User, Predict, Images, Task, Notification, Status, Settings, Model


app = create_app()
celery = ext_celery.celery


@app.shell_context_processor
def make_shell_context():
    return {'Model': Model,
            'db': db,
            'User': User,
            'Predict': Predict,
            'Images': Images,
            'Task': Task,
            'Notification': Notification,
            'celery': celery,
            'Status': Status,
            'Settings': Settings}
