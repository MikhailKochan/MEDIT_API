import os
import numpy as np
import cv2
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide

from decimal import Decimal as D
from tqdm import tqdm

from app.models import _set_task_progress, Config


def make_predict(img, predict, medit):
    try:
        progress = 0

        max_mitoz_in_one_img = 0

        _set_task_progress(progress, 0, func='predict')

        Visualizer = medit.Visualizer

        cfg = medit.cfg

        mitoz_metadata = medit.mitoz_metadata

        ColorMode = medit.ColorMode

        predictor = medit.predictor

        date_now = predict.timestamp.strftime('%d_%m_%Y__%H_%M')

        CLASS_NAMES = Config.CLASS_NAMES
        _CUT_IMAGE_SIZE = Config._CUT_IMAGE_SIZE

        h_sum = int(img.height / _CUT_IMAGE_SIZE[1])
        w_sum = int(img.width / _CUT_IMAGE_SIZE[0])

        if img.format.lower() == '.svs':
            # current_app.logger.info(f"Directory {f_path} for open in openslide")
            print('img.file_path in svs', img.file_path)
            file = openslide.OpenSlide(img.file_path)

        else:
            return f'{img.format} not added'

        h_rest = img.height % _CUT_IMAGE_SIZE[1]
        w_rest = img.width % _CUT_IMAGE_SIZE[0]
        s_col = int(h_rest / 2)
        s_row = int(w_rest / 2)
        total = h_sum * w_sum

        path_to_save_draw = os.path.join(Config.BASEDIR,
                                         f"{Config.DRAW}/{img.filename}/{date_now}")

        if not os.path.exists(path_to_save_draw):

            os.mkdir(path_to_save_draw)

            # current_app.logger.info(f"Directory {img.filename} for draw created")

        mitoz = CLASS_NAMES.index('mitoz')

        all_mitoz = 0

        with tqdm(total=total, position=0, leave=False) as pbar:
            for i in range(0, w_sum):
                for j in range(0, h_sum):
                    pbar.set_description(f"Total img: {total}. Start cutting")

                    start_row = j * _CUT_IMAGE_SIZE[0] + s_row
                    start_col = i * _CUT_IMAGE_SIZE[1] + s_col

                    filename = "0_im" + "_" + str(i) + "_" + str(j)

                    if img.format.lower() == '.svs':

                        img = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                        img = img.convert('RGB')

                        im = np.asarray(img)

                        outputs = predictor(im)

                        outputs = outputs["instances"].to("cpu")

                        classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

                        if mitoz in classes:
                            v = Visualizer(im[:, :, ::-1],
                                           metadata=mitoz_metadata,
                                           scale=1,
                                           instance_mode=ColorMode.SEGMENTATION)

                            v = v.draw_instance_predictions(outputs)
                            cv2.imwrite(os.path.join(path_to_save_draw, f"{filename}.jpg"),
                                        v.get_image()[:, :, ::-1])

                            all_mitoz += classes.count(mitoz)
                            if classes.count(mitoz) > max_mitoz_in_one_img:
                                max_mitoz_in_one_img = classes.count(mitoz)
                                # img_name = f"{filename}.jpg"

                    progress += 1 / total * 100.0

                    _set_task_progress(float(D(str(progress)).quantize(D("1.00"))),
                                       all_mitoz=all_mitoz,
                                       filename=f'{img.filename}/{date_now}',
                                       func='predict')

                    pbar.update(1)

        predict.result_all_mitoz = all_mitoz

        predict.result_max_mitoz_in_one_img = max_mitoz_in_one_img

        predict.count_img = total

        # predict.name_img_have_max_mitoz = img_name

        predict.model = cfg.MODEL.WEIGHTS

        predict.image_id = img.id

        return predict, path_to_save_draw

    except Exception as e:
        print(e)
        # current_app.logger.error(e)
