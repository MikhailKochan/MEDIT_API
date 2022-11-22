import zipfile
import os
import glob
from tqdm import tqdm
from decimal import Decimal as D

from config import Config


def create_zip(path_to_save: str, job=None):
    if job:
        from app.utils.celery import _set_celery_task_progress as _set_task_progress
    else:
        from rq import get_current_job
        from app.new_tasks import _set_task_progress
        job = get_current_job()
    try:
        progress = 0

        folder_name = os.path.basename(path_to_save)

        _set_task_progress(
            job=job,
            progress=progress,
            function='Create zip',
            filename=folder_name)

        zip_folder = Config.__dict__['SAVE_ZIP']

        list_img = glob.glob(f"{path_to_save}/*")

        zipFile = zipfile.ZipFile(os.path.join(zip_folder, f'{folder_name}.zip'), 'w', zipfile.ZIP_DEFLATED)

        total = len(list_img)

        for file in list_img:

            filename = os.path.basename(file)
            zipFile.write(file, arcname=filename)

            # pbar.update(1)

            progress += 1 / total * 100.0

            _set_task_progress(job=job,
                               progress=float(D(str(progress)).quantize(D("1.00"))),
                               func='Create zip',
                               filename=folder_name)

        zipFile.close()

    except Exception as e:
        print('ERROR in create_zip', e)


