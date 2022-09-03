import zipfile
import os
import glob
from tqdm import tqdm
from decimal import Decimal as D

from app.models import _set_task_progress, Config


def create_zip(path_to_save: str):
    try:
        progress = 0

        folder_name = os.path.basename(path_to_save)

        _set_task_progress(progress,
                           func='create_zip',
                           filename=folder_name)

        zip_folder = Config.__dict__['SAVE_ZIP']

        path_img = glob.glob(f"{path_to_save}/*")

        zipFile = zipfile.ZipFile(os.path.join(zip_folder, f'{folder_name}.zip'), 'w', zipfile.ZIP_DEFLATED)

        total = len(path_img)

        with tqdm(total=total, position=0, leave=False) as pbar:
            for file in path_img:
                pbar.set_description(f"Total img: {total}. Start zip:")

                filename = os.path.basename(file)
                zipFile.write(file, arcname=filename)

                pbar.update(1)

                progress += 1 / total * 100.0

                _set_task_progress(float(D(str(progress)).quantize(D("1.00"))),
                                   func='create_zip',
                                   filename=folder_name)

        zipFile.close()
        _set_task_progress(100,
                           func='create_zip',
                           filename=folder_name)

        result = f'{folder_name}.zip created'

    except Exception as e:
        result = e

    else:
        return result
