import os
import shutil
import random
import time
from celery import shared_task
from flask import current_app
from app.models import Task, Images, User
from app import db


@shared_task(bind=True)
def cutting_task(self):
    from app.utils.create_zip.create_zip import create_zip
    task = Task.query.get(self.request.id)
    # print('task', task)
    if task:
        img = task.images
        # print('img', img)
        if img and os.path.isfile(img.file_path):
            path_cutting_img = img.cutting(celery_job=self)
            if path_cutting_img:
                create_zip(path_to_save=path_cutting_img, job=self)
                shutil.rmtree(path_cutting_img)  # Delete cutting folder
            os.remove(img.file_path)  # Delete download svs
            task.complete = True
            db.session.commit()
            return {'progress': 100,
                    'status': 'Task completed!',
                    'result': 'ready to download',
                    'filename': img.filename,
                    }
    else:
        self.update_state(state='FAILURE')
        return {'progress': 0, 'status': 'FAILED', 'result': 'EXCEPTION IN CUTTING TASK', }


@shared_task(bind=True)
def make_predict_task(self):

    from app.utils.create_zip.create_zip import create_zip

    task = Task.query.get(self.request.id)
    # print('task', task)
    if task:
        img = task.images
        predict = task.predict
        if img and os.path.isfile(img.file_path):
            predict, path_predict_img = img.make_predict(predict, celery_job=self)

            path_to_save_draw_img = os.path.join(current_app.config['BASEDIR'],
                                                 f"{current_app.config['DRAW']}/{img.filename}")

            if not os.path.exists(path_to_save_draw_img):
                os.mkdir(path_to_save_draw_img)

            if path_predict_img:
                create_zip(path_to_save=path_predict_img, job=self)
                shutil.rmtree(path_predict_img)  # Delete cutting folder
            os.remove(img.file_path)  # Delete download svs

            db.session.add(predict)
            task.complete = True
            db.session.commit()
            return {'progress': 100,
                    'status': 'Task completed!',
                    'result': 'ready to download',
                    'filename': img.filename,
                    }
    else:
        self.update_state(state='FAILURE')
        return {'progress': 0, 'status': 'FAILED', 'result': 'EXCEPTION IN CUTTING TASK', }


@shared_task(bind=True)
def test(self):
    task = Task(id=self.request.id)
    u = User.query.filter_by(username='Vasa').all()
    if u:
        User.query.filter_by(username='Vasa').delete()
        db.session.commit()
    u = User(username='Vasa')
    db.session.add(task)
    db.session.add(u)
    db.session.commit()
    return 'Done'


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
    for filename, img in cut_space_generator:
        if predictor:
            output = pridict(predictor,
                             img,
                             filename,
                             all_mitoz,
                             mitoz_metadata,
                             ColorMode,
                             path_to_save_draw,
                             Visualizer)


def predict(predictor, im, img_name_draw, all_mitoz, mitoz_metadata, ColorMode, path_to_save_draw, Visualizer):
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
            # img_name = f"{filename}.jpg"
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


def space_selector_test(height, width, size):
    # height, width = 40000, 100000
    if height < size or width < size:
        return 'Size less height or width'
    h_sum = int(height / size)
    w_sum = int(width / size)
    print(h_sum, w_sum)  ###########
    h_rest = height % size
    w_rest = width % size
    print(h_rest, w_rest)  ##############
    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)
    print(s_col, s_row)  ###############
    # total = h_sum * w_sum
    # print(total)  #################
    for i in range(0, w_sum):
        for j in range(0, h_sum):

            start_row = j * size + s_row
            start_col = i * size + s_col

            yield start_row, start_col
