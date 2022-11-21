import os
import shutil
import json

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from config import Config
from flask import current_app


def img_test(**kwargs):
    import time
    from rq import get_current_job

    job = get_current_job()
    img = kwargs.get('img')
    _set_task_progress(job,
                       state='PENDING',
                       function='TEST',
                       filename=img.filename,
                       analysis_number=img.analysis_number)
    time.sleep(10)
    for i in range(101):
        # print('progress:', i)
        _set_task_progress(job, state='PROGRESS', progress=i, all_mitoz=i*2)
        time.sleep(1)
    _set_task_progress(job, state='FINISHED', result='Predict finished')


def img_cutt(**kwargs):
    from app.utils.cutting.cutting_svs import cutting
    from app.utils.create_zip.create_zip import create_zip

    path_cutting_img = cutting(path=kwargs.get('path'),
                               CUTTING_FOLDER=kwargs.get('CUTTING_FOLDER'),
                               _CUT_IMAGE_SIZE=kwargs.get('_CUT_IMAGE_SIZE'))

    result = create_zip(path_cutting_img)  # Create zip file

    os.remove(kwargs.get('path'))  # Delete download svs
    shutil.rmtree(path_cutting_img)  # Delete cutting folder


def mk_pred(**kwargs):
    from app.utils.prediction.make_predict import make_predict
    from app.utils.create_zip.create_zip import create_zip
    from rq import get_current_job

    job = get_current_job()
    img = kwargs.get('img')

    predict, path = make_predict(image=kwargs.get('img'), predict=kwargs.get('predict'), medit=kwargs.get('medit'))

    try:
        engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
        with Session(engine) as session:
            if predict:
                session.add(predict)
                session.commit()
            create_zip(path_to_save=path)
            _set_task_progress(job, state='FINISHED', result='Predict finished')
            shutil.rmtree(path)
            os.remove(img.file_path)
    except Exception as e:
        print('ERROR in mk_pred new_tasks', e)


def _set_task_progress(job, **kwargs):
    if job:
        job_id = job.get_id()
        if current_app:
            rd = current_app.redis
        else:
            from redis import Redis
            rd = Redis.from_url(Config.__dict__['REDIS_URL'])
        data = rd.get(job_id)
        if data:
            send = json.loads(data)
        else:
            send = {}
        send.update(kwargs)
        rd.set(job_id, json.dumps(send))
