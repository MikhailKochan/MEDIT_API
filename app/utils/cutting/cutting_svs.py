import os

from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide

from decimal import Decimal as D
from tqdm import tqdm

from app.models import _set_task_progress, Config


def cutting(f_path):
    CUTTING_FOLDER, _CUT_IMAGE_SIZE = Config.CUTTING_FOLDER, Config._CUT_IMAGE_SIZE
    try:
        progress = 0
        _set_task_progress(progress=progress, func='cutting')

        file = openslide.OpenSlide(f_path)

        height, width = file.level_dimensions[0]

        h_sum = int(height / _CUT_IMAGE_SIZE[1])
        w_sum = int(width / _CUT_IMAGE_SIZE[0])

        h_rest = height % _CUT_IMAGE_SIZE[1]
        w_rest = width % _CUT_IMAGE_SIZE[0]

        s_col = int(h_rest / 2)
        s_row = int(w_rest / 2)

        total = h_sum * w_sum
        img_filename = os.path.basename(f_path)

        save_folder = os.path.join(CUTTING_FOLDER, img_filename)

        if not os.path.exists(save_folder):
            os.mkdir(save_folder)

        with tqdm(total=total, position=0, leave=False) as pbar:
            for i in range(0, w_sum):
                for j in range(0, h_sum):
                    pbar.set_description(f"Total img: {total}. Start cutting")

                    start_row = j * _CUT_IMAGE_SIZE[0] + s_row
                    start_col = i * _CUT_IMAGE_SIZE[1] + s_col

                    filename = f"{img_filename[:10]}_im" + "_." + str(i) + "." + str(j)

                    path_to_save_cut_file = os.path.join(save_folder, f"{filename}.jpg")

                    img = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                    img = img.convert('RGB')
                    img.save(path_to_save_cut_file)

                    progress += 1 / total * 100.0

                    _set_task_progress(float(D(str(progress)).quantize(D("1.00"))), func='cutting')

                    pbar.update(1)

        return save_folder
    except Exception as e:
        print(f"ERROR in cutting: {e}")

        _set_task_progress(100, func='cutting')
