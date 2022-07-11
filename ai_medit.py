from app import create_app, db, models
from app.models import User, Predict, Images


app, predictor = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'models': models, 'db': db, 'User': User, 'Predict': Predict, 'Images': Images, 'predictor': predictor}
