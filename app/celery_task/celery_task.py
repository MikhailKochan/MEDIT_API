import os
import shutil
import time

from celery import shared_task
from flask import current_app

from app.models import Task, Images, User, Predict, Settings
from app import db


@shared_task
def error_handler(request, exc, traceback):
    current_app.logger.error('Task {0} raised exception: {1!r}\n{2!r}'.format(
        request.id, exc, traceback))


def task_getter(task_id: str):
    for _ in range(10):
        task = Task.query.get(task_id)
        if task:
            return task
        time.sleep(0.1)


@shared_task(bind=True)
def cutting_task(self, **kwargs):
    # print(self)
    from app.utils.create_zip.create_zip import create_zip
    img = Images.query.get(kwargs.get('img_id'))
    if img and os.path.isfile(img.file_path):
        path_cutting_img = img.cutting(celery_job=self)
        if path_cutting_img:
            create_zip(path_to_save=path_cutting_img, job=self)
            shutil.rmtree(path_cutting_img)  # Delete cutting folder
        os.remove(img.file_path)  # Delete download svs
        task = task_getter(self.request.id)
        current_app.logger.info(f'{task} task in 30 line in celery_task.py')
        if task:
            task.complete = True
        else:
            current_app.logger.error(f'{self.request.id} task not found')
        db.session.commit()
        return {'progress': 100,
                'status': 'Task completed!',
                'result': 'ready to download',
                'filename': img.filename,
                }
    else:
        # time.sleep(1)
        # if count < 3:
        #     count += 1
        #     cutting_task(self, count=count)
        self.update_state(state='FAILURE')
        current_app.logger.error(f'{self.request.id} task failed')
        return {'progress': 0, 'status': 'FAILED', 'result': 'EXCEPTION IN CUTTING TASK', }


@shared_task(bind=True)
def make_predict_task(self, **kwargs):
    from app.utils.create_zip.create_zip import create_zip

    img = Images.query.get(kwargs.get('img'))
    settings = Settings.query.get(kwargs.get('settings'))

    if img and os.path.isfile(img.file_path):

        image_predict = img.make_predict(celery_job=self, settings=settings)
        # print(image_predict, path_predict_img)
        task = Task.query.get(self.request.id)

        if image_predict and isinstance(image_predict, Predict):
            create_zip(path_to_save=image_predict.path_to_save, job=self)
            shutil.rmtree(image_predict.path_to_save)  # Delete cutting folder
            image_predict.path_to_save = os.path.basename(image_predict.path_to_save)

            db.session.add(image_predict)
            task.complete = True
            task.predict = image_predict

        os.remove(img.file_path)  # Delete download svs
        db.session.commit()
        self.update_state(state='FINISHED')
        return {'progress': 100,
                'status': 'FINISHED',
                'result': 'ready to download',
                }
    else:
        self.update_state(state='FAILURE')
        return {'progress': 0, 'status': 'FAILED'}


@shared_task(bind=True)
def test(self):
    task = Task(id=self.request.id)
    u = User.query.filter_by(username='Vasa').all()
    if u:
        User.query.filter_by(username='Vasa').delete()
        db.session.commit()

    u = User()
    u.username = 'Vasa'

    db.session.add(task)
    db.session.add(u)
    db.session.commit()
    return 'Done'
