import os
import sys

import numpy as np
import cv2
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide

from decimal import Decimal as D
# from tqdm import tqdm

from config import Config
from app.celery_task.async_test import quality_checking_image


def make_predict(image, predict, medit, job=None):

    if job:
        from app.utils.celery import _set_celery_task_progress as _set_task_progress
    else:
        from rq import get_current_job
        from app.new_tasks import _set_task_progress
        job = get_current_job()
    try:

        progress = 0

        max_mitoz_in_one_img = 0

        _set_task_progress(job=job,
                           state='PROGRESS',
                           progress=progress,
                           all_mitoz=0,
                           function='Predict',
                           analysis_number=image.analysis_number)

        Visualizer = medit.Visualizer

        cfg = medit.cfg
        print("Config CUDA :", cfg.MODEL.DEVICE)
        mitoz_metadata = medit.mitoz_metadata

        ColorMode = medit.ColorMode

        predictor = medit.predictor

        date_now = predict.timestamp.strftime('%d_%m_%Y__%H_%M')

        CLASS_NAMES = Config.CLASS_NAMES
        _CUT_IMAGE_SIZE = Config._CUT_IMAGE_SIZE

        h_sum = int(image.height / _CUT_IMAGE_SIZE[1])
        w_sum = int(image.width / _CUT_IMAGE_SIZE[0])

        if image.format.lower() == '.svs':
            f_path = os.path.join(Config.BASEDIR,
                                  Config.UPLOAD_FOLDER,
                                  image.filename)
            # current_app.logger.info(f"Directory {f_path} for open in openslide")
            # print('img.file_path in svs', img.file_path)
            file = openslide.OpenSlide(f_path)

        else:
            return f'{image.format} not added'

        h_rest = image.height % _CUT_IMAGE_SIZE[1]
        w_rest = image.width % _CUT_IMAGE_SIZE[0]
        s_col = int(h_rest / 2)
        s_row = int(w_rest / 2)
        total = h_sum * w_sum

        path_to_save_draw = os.path.join(Config.BASEDIR,
                                         Config.DRAW,
                                         # image.filename,
                                         f"{image.filename}_{date_now}")

        predict.path_to_save = f"{os.path.basename(path_to_save_draw)}.zip"

        os.makedirs(path_to_save_draw, exist_ok=True)

        mitoz = CLASS_NAMES.index('mitoz')

        all_mitoz = 0
        img_name = None
        for i in range(0, h_sum):
            for j in range(0, w_sum):

                start_row = j * _CUT_IMAGE_SIZE[0] + s_row
                start_col = i * _CUT_IMAGE_SIZE[1] + s_col

                img_name_draw = "0_im" + "_" + str(i) + "_" + str(j)

                img = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                img = img.convert('RGB')

                if quality_checking_image(img):

                    im = np.asarray(img)
                    # im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
                    outputs = predictor(im)

                    outputs = outputs["instances"].to('cpu')

                    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

                    if mitoz in classes:
                        v = Visualizer(im[:, :, ::-1],
                                       metadata=mitoz_metadata,
                                       scale=1,
                                       instance_mode=ColorMode.SEGMENTATION)

                        v = v.draw_instance_predictions(outputs)

                        cv2.imwrite(os.path.join(path_to_save_draw, f"{img_name_draw}.jpg"),
                                    v.get_image()[:, :, ::-1])
                        # cv2.imwrite(os.path.join(path_to_save_draw, f"{img_name_draw}_original.jpg"),
                        #             im)
                        all_mitoz += classes.count(mitoz)
                        if classes.count(mitoz) > max_mitoz_in_one_img:
                            max_mitoz_in_one_img = classes.count(mitoz)
                            img_name = f"{img_name_draw}.jpg"

                progress += 1 / total * 100.0

                fl_name = f'{image.filename}/{date_now}'

                _set_task_progress(
                    job=job,
                    progress=float(D(str(progress)).quantize(D("1.00"))),
                    all_mitoz=all_mitoz)

        predict.result_all_mitoz = all_mitoz

        predict.result_max_mitoz_in_one_img = max_mitoz_in_one_img

        predict.count_img = total

        # TODO решить проблему с добавлением инфы в бд, проверить тип вносимых данных
        # predict.name_img_have_max_mitoz = img_name if img_name else None

        predict.model = cfg.MODEL.WEIGHTS

        predict.image_id = image.id

        return predict, path_to_save_draw

    except Exception as e:
        print(f'ERROR in make_predict: {e}', sys.exc_info()[0])
        return type(e), e
        # current_app.logger.error(e)
