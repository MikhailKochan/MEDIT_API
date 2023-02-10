import os
import shutil
import time
import zipfile

from celery import shared_task
from flask import current_app

from app.view import pre_work_zip
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
    job_id = self.request.id
    from app.utils.create_zip.create_zip import create_zip
    img = Images.query.get(kwargs.get('img_id'))
    if img and os.path.isfile(img.file_path):
        path_cutting_img = img.cutting(celery_job=self)
        if path_cutting_img:
            create_zip(path_to_save=path_cutting_img, job=self)
            shutil.rmtree(path_cutting_img)  # Delete cutting folder
        os.remove(img.file_path)  # Delete download svs
        current_app.logger.info(f'str: {str(job_id)} type: {type(self.request.id)}')
        task = task_getter(str(job_id))
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
    job_id = str(self.request.id)
    user_id = kwargs.get('user_id')

    start = time.time()
    result = {'job_id': job_id, 'user_id': user_id}

    user = User.query.get(user_id)
    settings = user.settings

    path_to_file = kwargs.get('path_file')
    filename = os.path.basename(path_to_file)

    if zipfile.is_zipfile(path_to_file):
        path_to_file = pre_work_zip(path_to_file, self)

    img = Images(path_to_file, name=filename)
    task = Task(id=job_id, name='img_predict', description=f'Predict {img.filename}', user=user, images=img)

    try:
        db.session.add(task)
        db.session.add(img)
    except Exception as e:
        result.update(add_images_task=False)
        current_app.logger.error(f"ERROR in db.session.add(task, img): {e}")
        db.session.rollback()
        self.update_state(state='FAILURE')
        # raise
    else:
        db.session.commit()
        result.update(add_images_task_to_db=True)
        current_app.logger.info(f"task {task.id} add to db")
        current_app.logger.info(f"Images {img.id} add to db")

        if img and os.path.isfile(img.file_path):
            image_predict = img.make_predict(celery_job=self, settings=settings)
            if image_predict and isinstance(image_predict, Predict):
                result.update(make_predict=True)
                try:
                    create_zip(path_to_save=image_predict.path_to_save, job=self)
                except Exception as e:
                    result.update(make_zip=f'{e}')
                else:
                    result.update(make_zip=True)
                shutil.rmtree(image_predict.path_to_save)  # Delete cutting folder
                image_predict.path_to_save = os.path.basename(image_predict.path_to_save)
                try:
                    db.session.add(image_predict)
                    task.predict = image_predict
                except Exception as e:
                    result.update(add_task_image_predict=f'{e}')
                    current_app.logger.error(f"ERROR in db.session.add(image_predict): {e}")
                    db.session.rollback()
                    self.update_state(state='FAILURE')
                    # raise
                else:
                    result.update(add_task_image_predict=True)
                    current_app.logger.info(f"Predict {Predict.id} add to db")
                    db.session.commit()
            else:
                result.update(make_predict=False)
                current_app.logger.error(f"Predict failed")
                self.update_state(state='FAILURE')
                return {'progress': 0, 'status': 'PREDICT FAILED'}
    finally:
        try:
            t = Task.query.get(job_id)
            t.complete = True
        except Exception as e:
            result.update(task_complete=False)
            current_app.logger.error(f"ERROR in task.complete = True: {e}")
            db.session.rollback()
            self.update_state(state='FAILURE')
        else:
            result.update(task_complete=True)
            db.session.commit()
        try:
            os.remove(path_to_file)  # Delete download
        except Exception as e:
            result.update(file_remove=f'{e}')
        result.update(file_remove=True)
        if img.format.lower() == '.mrxs':
            img_folder = img.file_path[:-5]
            if os.path.isdir(img_folder):
                shutil.rmtree(img_folder)
                result.update(folder_mrxs_remove=True)
                current_app.logger.info(f'DELETE folder: {img_folder}')
        result.update(duration_of_work=time.time() - start)
        current_app.logger.info(f'TASK FINISH WITH RESULT: {result}')
        self.update_state(state='FINISHED')
        return {'progress': 100,
                'status': 'FINISHED',
                'result': result,
                }


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
