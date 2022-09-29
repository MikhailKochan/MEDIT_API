from app import create_app, db, models, ext_celery
from app.models import User, Predict, Images, Task, Notification, Status
from app.view import watcher
import threading


app = create_app()
celery = ext_celery.celery


# thr = threading.Thread(target=watcher, name='watcher', daemon=True)
# thr.start()


@app.shell_context_processor
def make_shell_context():
    return {'models': models,
            'db': db,
            'User': User,
            'Predict': Predict,
            'Images': Images,
            'Task': Task,
            'Notification': Notification,
            'predictor': app.medit.predictor,
            'Status': Status}
