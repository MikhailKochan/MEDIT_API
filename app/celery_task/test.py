import os
import shutil
import random
import time
import json

from celery import shared_task
from flask import current_app
# from app import celery
from app.models import Task, Images, User
from app import db


def _set_task_progress(job, **kwargs):
    if job:
        job_id = job.get_id()
        if current_app:
            rd = current_app.redis
        else:
            from redis import Redis
            rd = Redis.from_url(Config.__dict__['REDIS_URL'])
        data = rd.get(job_id)
        if data:
            send = json.loads(data)
        else:
            send = {}
        send.update(kwargs)
        rd.set(job_id, json.dumps(send))


def test_test(image: Images, *args, **kwargs):
    """
        -открываем картинуку
        -находим область
        -если предикт
            -отправляем в предикт
        -при необходимости сохраняем эту область
    Args:
        medit:

    Returns:

    """
    file = images_opener(image)
    cut_space_generator = space_selector(image, file)

    if 'medit' in kwargs and 'predict' in kwargs:
        medit = kwargs.get('medit')

        max_mitoz_in_one_img = 0
        all_mitoz = 0

        Visualizer = medit.Visualizer

        mitoz_metadata = medit.mitoz_metadata

        ColorMode = medit.ColorMode

        predictor = medit.predictor
        pred = kwargs.get('predict')
        date_now = pred.timestamp.strftime('%d_%m_%Y__%H_%M')
        path_to_save_draw = os.path.join(Config.BASEDIR, f"{Config.DRAW}/{image.filename}/{date_now}")

    for filename, img in cut_space_generator:  # находим области для обработки
        if predictor:
            output = pridict(predictor)


def predict(predictor, im):
    outputs = predictor(im)

    outputs = outputs["instances"].to("cpu")

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

        return all_mitoz, max_mitoz_in_one_img


def space_selector(image: Images, file):
    height, width = image.height, image.width

    h_sum = int(height / current_app.config.CUT_IMAGE_SIZE[1])
    w_sum = int(width / current_app.config.CUT_IMAGE_SIZE[0])

    h_rest = height % current_app.config.CUT_IMAGE_SIZE[1]
    w_rest = width % current_app.config.CUT_IMAGE_SIZE[0]

    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

    # total = h_sum * w_sum

    for i in range(0, w_sum):
        for j in range(0, h_sum):

            start_row = j * _CUT_IMAGE_SIZE[0] + s_row
            start_col = i * _CUT_IMAGE_SIZE[1] + s_col

            filename = f"im_.{str(i)}.{str(j)}"

            # path_to_save_cut_file = os.path.join(save_folder, f"{filename}.jpg")
            if image.format.lower() == '.svs':
                img = file.read_region((start_row, start_col), 0, current_app.configCUT_IMAGE_SIZE)
            else:
                img = None
            img = img.convert('RGB')

            yield filename, img


def images_opener(image: Images):
    """

    Args:
        image:
            take image path and open
    Returns:
        obj images
    """
    if image.format.lower() == '.svs':
        import os
        # import sys
        from sys import platform

        if platform == 'win32':
            os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

        import openslide
        file = openslide.OpenSlide(image.file_path)
    else:
        return f'{image.format} not add'
    return file