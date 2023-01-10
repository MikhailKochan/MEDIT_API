import os
import shutil
import json
import time

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from config import Config
from flask import current_app

from app.models import Task, Predict, Settings


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
    from app.utils.prediction.make_predict import make_predict_test
    from app.utils.create_zip.create_zip import create_zip
    from rq import get_current_job

    job = get_current_job()
    img = kwargs.get('img')
    start = time.time()

    image = kwargs.get('img')
    prd = kwargs.get('predict')
    mdt = kwargs.get('medit')
    settings = kwargs.get('settings', None)
    print(image, prd, mdt, settings)
    predict, path = make_predict_test(image=image,
                                      predict=prd,
                                      medit=mdt,
                                      settings=settings)
    if isinstance(predict, Predict):
        print(f'PREDICT TIME: {time.time() - start}')
        try:
            engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
            with Session(engine) as session:
                if predict:
                    session.add(predict)
                    task = session.query(Task).filter(Task.predict, Predict.id == predict.id).first()
                    # task = Task.query.filter(Task.predict, Predict.id == predict.id).first()
                create_zip(path_to_save=path)
                _set_task_progress(job, state='FINISHED', result='Predict finished')
                shutil.rmtree(path)
                os.remove(img.file_path)
                if task:
                    task.complete = True
                else:
                    print('ERROR in mk_pred new_tasks: TASK NOT FOUND')
                session.commit()
        except Exception as e:
            print('ERROR in mk_pred new_tasks', e)
    else:
        print(predict)
        print(path)


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
