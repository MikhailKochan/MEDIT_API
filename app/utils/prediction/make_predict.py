import os
import sys
import requests
import numpy as np
import cv2
import openslide

from config import Config
from app.celery_task.async_test import quality_checking_image, draw_predict


def send_image_to_model(path_to_image, url):
    with open(path_to_image, 'rb') as f:
        params = {"uploadType": "multipart/form-data"}
        resp = requests.post(url=url,
                             files={'file': f.read()},
                             params=params)
        if resp.status_code != 200:
            print("--ERROR--")
            print(resp.text)
        else:
            return resp.json()


def make_predict_celery(image, predict, job_id, settings):
    from app.view import space_selector
    from app.new_tasks import _set_task_progress as _set_celery_task_progress
    try:
        all_mitoz = 0
        progress = 0
        max_mitoz_in_one_img = 0

        url = settings.model.url
        f_path = os.path.join(Config.BASEDIR,
                              Config.UPLOAD_FOLDER,
                              image.filename)
        file = openslide.OpenSlide(f_path)

        assert file, f"IMAGE FORMAT: {image.format} NOT SUPPORTED"

        _set_celery_task_progress(
            job=job_id,
            progress=progress,
            all_mitoses=all_mitoz,
            function='Predict',
            state='PROGRESS',
            analysis_number=image.analysis_number)

        _CUT_IMAGE_SIZE = settings.get_cutting_size()

        total = int(image.height / _CUT_IMAGE_SIZE[1]) * int(image.width / _CUT_IMAGE_SIZE[0])
        valid_percent = _CUT_IMAGE_SIZE[1] * _CUT_IMAGE_SIZE[0] * 0.10
        zeros = np.zeros([_CUT_IMAGE_SIZE[1], _CUT_IMAGE_SIZE[0], 3], dtype=np.uint8)
        for start_row, start_col, img_name in space_selector(image.height, image.width, _CUT_IMAGE_SIZE):
            try:
                img_PILLOW = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                img_PILLOW = img_PILLOW.convert('RGB')

                im_RGB = np.asarray(img_PILLOW)
                image_BGR = cv2.cvtColor(im_RGB, cv2.COLOR_RGB2BGR)

                is_black = np.count_nonzero(image_BGR == zeros) / 3

                if (is_black < valid_percent) and quality_checking_image(image_BGR, settings=settings):
                    save_image_path = os.path.join(predict.path_to_save, f"{img_name}.jpg")
                    img_PILLOW.save(save_image_path)

                    check = True
                    img_name_not_valid = f'{img_name}_not_valid'
                    response = send_image_to_model(path_to_image=save_image_path,
                                                   url=url)
                    if response is None:
                        print(f'server in URL:{url} don`t send response')
                        os.remove(save_image_path)
                        continue
                    response = response['response']

                    request_coord, request_label = response['request_coord'], response['request_label']

                    coord_not_valid, label_not_valid = [], []
                    coord_valid, label_valid = [], []

                    for index, box_coord in enumerate(request_coord):

                        x, y, x1, y1 = box_coord
                        predict_zone = image_BGR[int(y): int(y1), int(x): int(x1)]

                        if not quality_checking_image(predict_zone, settings=settings):
                            check = False
                            img_name_not_valid = img_name_not_valid + '_white'

                        if not quality_checking_image(predict_zone, quality_black=True, settings=settings):
                            check = False
                            img_name_not_valid = img_name_not_valid + '_black'

                        if not check:
                            coord_not_valid.append([int(x), int(y), int(x1), int(y1)])
                            if request_label[index]:
                                label_not_valid.append(request_label[index])

                        else:
                            coord_valid.append([int(x), int(y), int(x1), int(y1)])
                            if request_label[index]:
                                label_valid.append(request_label[index])

                    if coord_not_valid:
                        # print(f'coord_not_valid: {coord_not_valid}')
                        image_draw_not_valid = draw_predict(image=image_BGR,
                                                            coord=coord_not_valid,
                                                            labels=label_not_valid,
                                                            settings=settings)
                        not_valid_path = os.path.join(predict.path_to_save, 'not_valid')
                        os.makedirs(not_valid_path, exist_ok=True)
                        save_image_path_not_valid = os.path.join(not_valid_path, f"{img_name_not_valid}.jpg")
                        cv2.imwrite(save_image_path_not_valid, image_draw_not_valid)

                    if coord_valid:
                        # print(f'coord_valid: {coord_valid}')
                        image_draw = draw_predict(image=image_BGR,
                                                  coord=coord_valid,
                                                  labels=label_valid,
                                                  settings=settings)
                        cv2.imwrite(save_image_path, image_draw)
                    else:
                        os.remove(save_image_path)
                    all_mitoz += len(coord_valid)
            except Exception as e:
                print(f'ERROR in make_predict_celery in iteration: {e}', sys.exc_info()[0])
            finally:
                progress += 1 / total * 100.0

                _set_celery_task_progress(
                    job=job_id,
                    progress=int(progress),
                    all_mitoses=all_mitoz,
                    function='Predict',
                    analysis_number=image.analysis_number
                )

        predict.result_all_mitoz = all_mitoz
        predict.result_max_mitoz_in_one_img = max_mitoz_in_one_img
        predict.count_img = total
        predict.model = settings.model
        predict.image_id = image.id

        return predict

    except Exception as e:
        print(f'ERROR in make_predict_celery: {e}', sys.exc_info()[0])
