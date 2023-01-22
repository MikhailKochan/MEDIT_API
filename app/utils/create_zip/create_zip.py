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
        # print(f'folder_name: {folder_name}')
        _set_task_progress(
            job=job,
            progress=progress,
            function='Create zip',
            filename=folder_name)

        list_img = glob.glob(f"{path_to_save}/*")

        zp_name = os.path.join(Config.__dict__['SAVE_ZIP'], f'{folder_name}.zip')

        with zipfile.ZipFile(zp_name, mode='w', compression=zipfile.ZIP_DEFLATED) as zipFile:

            total = len(list_img)

            for file in list_img:
                filename = os.path.basename(file)
                zipFile.write(file, arcname=filename)

                if os.path.isdir(file):
                    inside_list = glob.glob(f"{file}/*")
                    for deep_file in inside_list:
                        # print(deep_file)
                        file_name = os.path.basename(deep_file)
                        # print(filename)
                        zipFile.write(deep_file, arcname=f'{filename}/{file_name}')
                progress += 1 / total * 100.0

                _set_task_progress(job=job,
                                   progress=int(progress),
                                   function='Create zip',
                                   filename=folder_name
                                   )

            zipFile.close()

    except Exception as e:
        print('ERROR in create_zip', e)
