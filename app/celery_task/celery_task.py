import os
import shutil
import random
import time
from celery import shared_task
# from app import celery
from app.models import Task, Images


@shared_task(bind=True)
def cutting_task(self):
    from app.utils.create_zip.create_zip import create_zip
    task = Task.query.get(self.request.id)
    # print('task', task)
    if task:
        img = task.images
        # print('img', img)
        if img and os.path.isfile(img.file_path):
            path_cutting_img = img.cutting(celery_job=self)
            if path_cutting_img:
                create_zip(path_to_save=path_cutting_img, job=self)
                shutil.rmtree(path_cutting_img)  # Delete cutting folder
            os.remove(img.file_path)  # Delete download svs
            # task.complete = True
            # db.session.commit()
            return {'progress': 100,
                    'status': 'Task completed!',
                    'result': 'ready to download',
                    'filename': img.filename,
                    }
    else:
        self.update_state(state='FAILURE')
        return {'progress': 0, 'status': 'FAILED', 'result': 'EXCEPTION IN CUTTING TASK', }
