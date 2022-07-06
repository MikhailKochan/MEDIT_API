from app import app, db, models, view
from app.models import User, Predict, Images
from app.view import watcher


@app.shell_context_processor
def make_shell_context():
    return {'models': models, 'db': db, 'User': User, 'Predict': Predict, 'Images': Images}
