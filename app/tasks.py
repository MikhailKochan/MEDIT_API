import sys
import os
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
        predict = Predict.query.get(pred_id)
        img = predict.images
        # data = img.make_predict(predict=predict, cutting=img.cut_file)
        data = img.alternative_predict(predict=predict)

        if data:
            path_draw = f"{current_app.config['DRAW']}/" \
                        f"{img.filename}/" \
                        f"{data.timestamp.strftime('%d_%m_%Y__%H_%M')}"

            data.create_zip(path_draw)
            db.session.add(data)

        else:
            db.session.add(predict)

    except Exception as e:
        print(f'ERROR in img_prediction : {e}')
        # _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

    else:
        os.remove(img.file_path)
        app.logger.info(f'{img.file_path} deleted')
        img.query.filter_by(id=img.id).delete()
        db.session.commit()
        app.logger.info(f'{img.id} deleted on bd')
