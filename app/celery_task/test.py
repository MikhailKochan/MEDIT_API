from typing import Any

import os
import shutil
import random
import time
import json

import numpy as np
import cv2

from celery import shared_task
from flask import current_app
# from app import celery
from app.models import Task, Images, User, Predict
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


def test_cutting(self):
    #  ОТКРЫВАЕМ КАРТИНКУ
    file = images_opener(self)
    assert file, 'Нет возможности открыть файл'
    cut_space_generator = space_selector(self, file)

    save_folder = os.path.join(CUTTING_FOLDER, self.filename)
    if not os.path.exists(save_folder):
        os.mkdir(save_folder)

    for filename, img in cut_space_generator:  # перебираем области для обработки
        if cut_file:
            if image.format.lower() == '.svs':
                img.save(os.path.join(save_folder, f"{filename}.jpg"))

    create_zip(save_folder)


def test_general_process(image: Images, make_analysis: Predict = None, **kwargs):
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
    #  ОТКРЫВАЕМ КАРТИНКУ
    file = images_opener(image)
    assert file, 'Нет возможности открыть файл'

    #  СОЗДАЕМ ГЕНЕРАТОР ОБЛАСТЕЙ КАРТИНКИ(координаты)
    cut_space_generator = space_selector(image, file)

    if make_analysis:
        if not os.path.exists(make_analysis.path_to_save):
            os.mkdir(make_analysis.path_to_save)
            current_app.logger.info(f"Directory {make_analysis.path_to_save} for draw created")

    if cut_file:
        save_folder = os.path.join(CUTTING_FOLDER, image.filename)
        if not os.path.exists(save_folder):
            os.mkdir(save_folder)

    for filename, img in cut_space_generator:  # перебираем области для обработки

        if make_analysis and current_app.medit:
            make_predict(img_name_draw=filename,
                         img=img,
                         predict=make_analysis)

        if cut_file:
            if image.format.lower() == '.svs':
                img.save(os.path.join(save_folder, f"{filename}.jpg"))

    file_path: str = save_folder if cut_file else make_analysis.path_to_save
    create_zip(file_path)


def make_predict(img_name_draw, img, predict: Predict):

    path_to_save_draw = predict.path_to_save

    assert current_app.medit, 'Object medit not added in app'

    im = np.asarray(img)
    outputs = current_app.medit.predictor(im)
    outputs = outputs["instances"].to(current_app.medit.cfg.MODEL.DEVICE)

    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

    if mitoz in classes:
        v = current_app.meditVisualizer(im[:, :, ::-1],
                                        metadata=current_app.medit.mitoz_metadata,
                                        scale=1,
                                        instance_mode=current_app.medit.ColorMode.SEGMENTATION)

        v = v.draw_instance_predictions(outputs)

        cv2.imwrite(os.path.join(path_to_save_draw, f"{img_name_draw}.jpg"),
                    v.get_image()[:, :, ::-1])

        predict.result_all_mitoz += classes.count(mitoz)
        if classes.count(mitoz) > predict.result_max_mitoz_in_one_img:
            predict.result_max_mitoz_in_one_img = classes.count(mitoz)

        return predict


def space_selector(image: Images, file):
    height, width = image.height, image.width

    h_sum = int(height / current_app.config.CUT_IMAGE_SIZE[1])
    w_sum = int(width / current_app.config.CUT_IMAGE_SIZE[0])

    h_rest = height % current_app.config.CUT_IMAGE_SIZE[1]
    w_rest = width % current_app.config.CUT_IMAGE_SIZE[0]

    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

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
            assert img, f'images: {img}, {image.filename}, {image.format}'
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
    try:
        if image.format.lower() == '.svs':
            import os
            from sys import platform
            import openslide
            if platform == 'win32':
                os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')
            file = openslide.OpenSlide(image.file_path)

        else:
            current_app.logger.info(f'{image.format} not add')
            file = None

        return file

    except Exception as e:
        current_app.logger.info(f'ERROR IN images_opener: {e}')
        return None
