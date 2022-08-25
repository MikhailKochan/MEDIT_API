import sys
import time
from app import create_app
from rq import get_current_job
from app import db
from app.models import Task, User, Images, Predict
from app.view import app_job

app = create_app()
app.app_context().push()


def _set_task_progress(progress, all_mitoz=None):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.predict.add_status('task_progress', {'task_id': job.get_id(),
                                                  'mitoze': all_mitoz,
                                                  'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def img_prediction(pred_id):
    try:
        print(f'pred_id : {pred_id}')
        # img = Images.query.filter_by(predict=pred_id)
        pred = Predict.query.get(pred_id)
        img = pred.images
        data = img.make_predict(cutting=img.cut_file, predict_date=pred.timestamp)

        if data:
            pred.result_all_mitoz = data.result_all_mitoz
            pred.result_max_mitoz_in_one_img = data.result_max_mitoz_in_one_img
            pred.count_img = data.count_img
            pred.name_img_have_max_mitoz = data.name_img_have_max_mitoz
            pred.model = data.model
            pred.image_id = data.image_id
        db.session.add(pred)
        db.session.commit()
    except Exception as e:
        print(f'ERROR in img_prediction : {e}')
        # _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
