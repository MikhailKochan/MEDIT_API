import os
import sys
import requests
import numpy as np
import cv2
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')
import openslide
from decimal import Decimal as D
from config import Config
from app.celery_task.async_test import quality_checking_image, quality_predict_area, draw_predict


def make_predict_test(image, predict, medit, settings=None):
    from rq import get_current_job
    from app.new_tasks import _set_task_progress
    job = get_current_job()
    try:
        progress = 0
        max_mitoz_in_one_img = 0
        _set_task_progress(job=job,
                           state='PROGRESS',
                           progress=progress,
                           all_mitoses=0,
                           function='Predict',
                           analysis_number=image.analysis_number)
        cfg = medit.cfg
        print("Config CUDA :", cfg.MODEL.DEVICE)
        mitoz_metadata = medit.mitoz_metadata

        predictor = medit.predictor

        date_now = predict.timestamp.strftime('%d_%m_%Y__%H_%M')

        CLASS_NAMES = Config.CLASS_NAMES
        _CUT_IMAGE_SIZE = Config._CUT_IMAGE_SIZE
        if settings is not None:
            _CUT_IMAGE_SIZE = settings.get_cutting_size()
        h_sum = int(int(image.height) / int(_CUT_IMAGE_SIZE[1]))
        w_sum = int(int(image.width) / int(_CUT_IMAGE_SIZE[0]))

        if image.format.lower() == '.svs':
            f_path = os.path.join(Config.BASEDIR,
                                  Config.UPLOAD_FOLDER,
                                  image.filename)
            file = openslide.OpenSlide(f_path)

        else:
            print(f'{image.format} not added')
            return

        h_rest = image.height % _CUT_IMAGE_SIZE[1]
        w_rest = image.width % _CUT_IMAGE_SIZE[0]
        s_col = int(h_rest / 2)
        s_row = int(w_rest / 2)
        total = h_sum * w_sum

        path_to_save_draw = os.path.join(Config.BASEDIR,
                                         Config.DRAW,
                                         f"{image.filename}_{date_now}")

        predict.path_to_save = f"{os.path.basename(path_to_save_draw)}"

        os.makedirs(path_to_save_draw, exist_ok=True)

        mitoz = CLASS_NAMES.index('mitoz')

        all_mitoz = 0
        print('START ITER')
        for i in range(0, h_sum):
            for j in range(0, w_sum):

                start_row = j * _CUT_IMAGE_SIZE[0] + s_row
                start_col = i * _CUT_IMAGE_SIZE[1] + s_col

                img_name_draw = "0_im" + "_" + str(i) + "_" + str(j)

                img_PILLOW = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                img_PILLOW = img_PILLOW.convert('RGB')

                im_RGB = np.asarray(img_PILLOW)
                image_BGR = cv2.cvtColor(im_RGB, cv2.COLOR_RGB2BGR)

                if quality_checking_image(image_BGR, settings=settings):

                    outputs = predictor(im_RGB)

                    outputs = outputs["instances"].to('cpu')
                    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

                    if mitoz in classes:
                        request_coord, request_label = quality_predict_area(image=image_BGR,
                                                                            predictions=outputs,
                                                                            metadata=mitoz_metadata,
                                                                            mitoses=mitoz,
                                                                            settings=settings)
                        file_name = os.path.join(path_to_save_draw, f"{img_name_draw}.jpg")

                        image_draw = draw_predict(image=image_BGR,
                                                  coord=request_coord,
                                                  labels=request_label,
                                                  settings=settings)
                        if request_label:
                            cv2.imwrite(file_name, image_draw)

                            all_mitoz += len(request_coord)

                progress += 1 / total * 100.0

                _set_task_progress(
                    job=job,
                    progress=float(D(str(progress)).quantize(D("1.00"))),
                    all_mitoses=all_mitoz)

        predict.result_all_mitoz = all_mitoz
        predict.result_max_mitoz_in_one_img = max_mitoz_in_one_img
        predict.count_img = total
        predict.model = cfg.MODEL.WEIGHTS
        predict.image_id = image.id

        return predict, path_to_save_draw
    except Exception as e:
        print(f'ERROR in make_predict_test: {e}', sys.exc_info()[0])
        return type(e), e


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

                im = np.asarray(img)
                im_BGR = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
                if quality_checking_image(im_BGR):

                    outputs = predictor(im)

                    outputs = outputs["instances"].to('cpu')
                    print(outputs)

                    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

                    if mitoz in classes:
                        v = Visualizer(im[:, :, ::-1],
                                       metadata=mitoz_metadata,
                                       scale=1,
                                       instance_mode=ColorMode.SEGMENTATION)

                        v = v.draw_instance_predictions(outputs)

                        cv2.imwrite(os.path.join(path_to_save_draw, f"{img_name_draw}.jpg"),
                                    v.get_image()[:, :, ::-1])

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


def make_predict_celery(image, predict, job, settings):
    from app.view import space_selector
    from app.utils.celery import _set_celery_task_progress
    try:
        all_mitoz = 0
        progress = 0
        max_mitoz_in_one_img = 0
        # file = None
        url = settings.model.url
        # if image.format.lower() == '.svs':

        f_path = os.path.join(Config.BASEDIR,
                              Config.UPLOAD_FOLDER,
                              image.filename)
        file = openslide.OpenSlide(f_path)

        assert file, f"IMAGE FORMAT: {image.format} NOT SUPPORTED"

        _set_celery_task_progress(
            job=job,
            progress=progress,
            all_mitoses=all_mitoz,
            function='Predict',
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
                    job=job,
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
