import sys
import os
import time
import json

from flask import current_app
from rq import get_current_job

from app import create_app
from app import db
from app.models import Task, User, Images, Predict
from app.view import app_job

from config import Config


app = create_app()
app.app_context().push()


def _set_task_progress(progress, all_mitoz=None, func=None):
    job = get_current_job()
    if job:
        job_id = job.get_id()
        job.meta['progress'] = progress
        job.save_meta()
        current_app.redis.set(job_id, json.dumps({'task_id': job_id,
                                                  'mitoze': all_mitoz,
                                                  'func': {f'{func}': {
                                                      'progress': progress}}}))
        try:
            if progress >= 100:
                task = Task.query.get(job_id)
                task.complete = True
                db.session.commit()

        except Exception as e:
            print(f'ERROR in set_task_progress: {e}')
            if current_app:
                current_app.logger.error(e)
            db.session.rollback()


def img_prediction(pred_id):
    try:
        print(f'pred_id : {pred_id}')
        # img = Images.query.filter_by(predict=pred_id)
        predict = Predict.query.get(pred_id)
        img = predict.images

        os.makedirs(f"{Config.DRAW}/{img.filename}", exist_ok=True)

        # data = img.make_predict(predict=predict, cutting=img.cut_file)
        data = img.alternative_predict(predict=predict)

        if data:
            path_draw = f"{Config.DRAW}/" \
                        f"{img.filename}/" \
                        f"{data.timestamp.strftime('%d_%m_%Y__%H_%M')}"

            data.create_zip(path_draw)
            db.session.add(data)

        # else:
        #     db.session.add(predict)

        db.session.commit()
        print("Вот и сказочке конец, а кто слушал - молодец.")
        os.remove(img.file_path)
        app.logger.info(f'{img.file_path} deleted')

    except Exception as e:
        print(f'ERROR in img_prediction : {e}')
        # _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def img_cutt(image_id):
    print(image_id)
    img = Images.query.filter_by(id=image_id).first()
    # for i in range(101):
    #     _set_task_progress(i, func='cutting')
    #     print(i)
    #     time.sleep(0.1)
    #
    # for i in range(101):
    #     _set_task_progress(i, func='create_zip')
    #     print(i)
    #     time.sleep(0.1)

    img.cutting()
    path_cut_file = f"{Config.CUTTING_FOLDER}/{img.filename}"

    img.create_zip(path_cut_file)
