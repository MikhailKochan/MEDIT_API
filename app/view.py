import glob
import time
import os
import numpy as np
import zipfile
import cv2
from sys import platform
from flask import current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import pathlib
import sqlite3
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from .models import Images, Predict, Settings
from config import Config

# from detectron2.config import get_cfg
# from detectron2 import model_zoo
# from detectron2.data import MetadataCatalog, DatasetCatalog
# from detectron2.data.datasets import register_coco_instances, register_pascal_voc
# from detectron2.engine import DefaultPredictor, DefaultTrainer
# from detectron2.utils.visualizer import ColorMode, Visualizer

from app import db


def check_req(req):
    for key, value in req.items():
        if not value:
            req[f'{key}'] = 0
    return req


def quality_checking_image(img: np.asarray,
                           quality_black=False,
                           lower=None,
                           upper=None,
                           settings=None) -> bool:
    """

    Args:
        settings: user settings class Settings in models
        upper: upper range for HSV color
        lower: lower range for HSV color
        img: MUST be BGR
        quality_black: Black mode for images

    Returns:
        True or False quality
    """
    # print('START QUALITY')
    # start = time.time()
    if settings is None:
        percentage = 50
    else:
        percentage = int(settings.percentage_white)

    if quality_black:
        if settings is None:
            percentage = 10
        else:
            percentage = int(settings.percentage_black)

        if lower is None and upper is None:
            lower = np.array([0, 0, 0], dtype=np.uint8)
            upper = np.array([180, 255, 68], dtype=np.uint8)

    if lower is None and upper is None:
        lower = np.array([0, 0, 168], dtype=np.uint8)
        upper = np.array([180, 30, 255], dtype=np.uint8)
    # print('quality black', quality_black)
    # print('percentage', percentage)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)

    imgh, imgw = img.shape[:2]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    summa_S = 0.0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        summa_S += w * h

    # print(f"percentage: {percentage}")
    # print(f"imgh * imgw: {imgh * imgw}")
    # print(f"imgh * imgw / 100 * percentage: {imgh * imgw / 100 * percentage}")
    # print(f"summa: {summa_S}")
    if summa_S > (imgh * imgw / 100 * percentage):
        quality = False
    else:
        # print(f"summa: {summa_S} |  {imgh * imgw / 100 * percentage}")
        quality = True

    return quality


def draw_predict(image: np.asarray, coord: list, labels: list, settings: Settings = None):
    """
    draw Image
    Args:
        settings: user settings
        image: MUST be BGR
        coord: [[x,y,x1,y1], n1, n2... nx]
        labels: lest names

    Returns:
        draw Image: np.assarray
    """
    if settings is not None:
        # users settings
        rectangle_color = settings.get_color_for_rectangle()
        text_color = settings.get_color_for_text()
    else:
        # default settings
        rectangle_color = (2, 202, 244)
        text_color = (0, 0, 0)
    for i in range(len(coord)):
        x, y, x1, y1 = coord[i]
        x, y, x1, y1 = int(x), int(y), int(x1), int(y1)
        cv2.rectangle(image, (x, y), (x1, y1), rectangle_color, 2)
        cv2.rectangle(image, (x - 1, y - 23), (x + 134, y + 1), rectangle_color, -1)
        image = cv2.putText(image, f"{labels[i]}", (x, y - 1), cv2.FONT_HERSHEY_SIMPLEX,
                            .8, text_color, 2, cv2.LINE_AA)
    return image


def space_selector(height: int, width: int, CUT_IMAGE_SIZE):
    # start = time.time()
    h_sum = int(height / CUT_IMAGE_SIZE[1])
    w_sum = int(width / CUT_IMAGE_SIZE[0])

    h_rest = height % CUT_IMAGE_SIZE[1]
    w_rest = width % CUT_IMAGE_SIZE[0]

    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

    for i in range(0, h_sum):
        for j in range(0, w_sum):
            start_row = j * CUT_IMAGE_SIZE[0] + s_row
            start_col = i * CUT_IMAGE_SIZE[1] + s_col

            filename = f"im_.{str(i)}.{str(j)}"
            # print(f'generator time: {time.time() - start} s')
            yield start_row, start_col, filename


def file_name_maker(filename):
    """
    функция для предотвращения повторения имен при сохранении
    и проверки вредной информации в имени файла
    Args:
        filename:
            str
    Returns:
        filename_n
        n - count filename repeated
    """
    filename = secure_filename(filename)

    spl = os.path.splitext(filename)
    searching_name = spl[0]

    g = glob.glob(f"{os.path.join(current_app.config['UPLOAD_FOLDER'], searching_name)}*")

    if g:
        filename = searching_name + f"_{len(g)}" + spl[-1]

    return filename


def check_zip(path):
    with zipfile.ZipFile(path, 'r') as zipF:
        namelist = zipF.namelist()
        list_to_extract = []
        for file in namelist:
            if file.endswith('.mrxs'):
                open_file = file  # images file to open openslide
                folder = file.replace('.mrxs', '/')
                mst1 = folder + 'Index.dat'
                mst2 = folder + 'Slidedat.ini'
                if mst1 in namelist and mst2 in namelist:
                    list_to_extract.append(file)
                    for file in namelist:
                        if folder in file:
                            list_to_extract.append(file)
                    # if list_to_extract:
                    #     return {'list_to_extract': list_to_extract, 'open_file': open_file}
            elif file.endswith('.svs'):
                open_file = file  # images file to open openslide
                list_to_extract.append(file)
            if list_to_extract:
                return {'list_to_extract': list_to_extract, 'open_file': open_file}
    return False


def pre_work_zip(path, job):
    from app.new_tasks import _set_task_progress as _set_celery_task_progress

    progress = 0
    _set_celery_task_progress(
        job=job,
        state='PROGRESS',
        progress=progress,
        function='unzip')

    check = check_zip(path)
    if check:
        list_to_extract = check.get('list_to_extract')
        total = len(list_to_extract)
        with zipfile.ZipFile(path, 'r') as zipF:
            for file in list_to_extract:
                # filename = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(file))
                # with open(filename, "wb") as f:
                #     f.write(zipF.read(file))
                zipF.extract(file, current_app.config['UPLOAD_FOLDER'])

                progress += 1 / total * 100.0
                _set_celery_task_progress(
                    job=job,
                    progress=progress,
                    function='unzip')

    os.remove(path)
    return os.path.join(current_app.config['UPLOAD_FOLDER'], check.get('open_file')) if check else False


def file_save_and_add_to_db(path):
    if zipfile.is_zipfile(path):
        path = pre_work_zip(path)
    if os.path.isfile(path) and path.endswith(tuple(current_app.config['IMAGE_FORMAT'])):
        img = Images(path, name=file.filename)
        db.session.add(img)
        db.session.commit()
        current_app.logger.info(f"{filename} saved to {current_app.config['UPLOAD_FOLDER']}")
    else:
        os.remove(path)
    return img


def show_all_table(db='app.db'):
    connect = sqlite3.connect(db)
    cursor = connect.cursor()
    cursor.execute(f"""SELECT * FROM sqlite_master WHERE type = 'table'""")
    tables = cursor.fetchall()
    for table in tables:
        print(table[1])


def _to_db(cls, search_column=None, search=None):
    connect = sqlite3.connect('app.db')
    cursor = connect.cursor()
    try:
        if search_column and search:
            cursor.execute(f"""SELECT * FROM {type(cls).__name__} WHERE {search_column} = '{search}'""")
            result = cursor.fetchone()
        else:
            cursor.execute(f"SELECT * FROM {type(cls).__name__}")
            result = cursor.fetchall()
        if result is None:
            print("cursor.fetchone() is None")
            if type(cls).__name__ == 'Images' and cls.name is not None:
                cursor.execute("INSERT INTO 'images' VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (cls.id,
                                cls.analysis_number,
                                cls.name,
                                cls.timestamp,
                                cls.img_creation_time,
                                cls.img_creation_date,
                                cls.filename,
                                cls.cut_file,
                                cls.format,
                                cls.height,
                                cls.width,
                                cls.file_path))
                # print(f"images ID = {data['id']} added to bd")
            elif type(cls).__name__ == 'Predict':
                print('type Predict')
                cursor.execute("INSERT INTO 'Predict' VALUES( ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (cls.id,
                                cls.timestamp,
                                cls.result_all_mitoz,
                                cls.result_max_mitoz_in_one_img,
                                cls.count_img,
                                cls.name_img_have_max_mitoz,
                                cls.status,
                                cls.image_id,
                                cls.model))
        else:
            if type(cls).__name__ == 'Images' and cls.name is not None:
                print('here')
                print(cls.cut_file)
                cursor.execute(f"""UPDATE {type(cls).__name__} SET 'cut_file' = '{int(cls.cut_file)}'
                 WHERE id = '{cls.id}'""")
                connect.commit()
            return result
        connect.commit()

    except sqlite3.Error as error:
        print("Failed to read data from table:", error)
        connect.commit()


def watcher():
    while True:
        files = glob.glob(Config.UPLOAD_FOLDER + '/*')
        query = _to_db(Images())
        old_img = [el[6] for el in query]
        for new in files:
            if os.path.basename(new) not in old_img:
                img = Images(new)
                _to_db(img, 'filename', img.filename)
                print(f"{os.path.basename(new)} add in DB")
                img.cutting()
                _to_db(img)
        break
        time.sleep(Config.UPDATE_TIME)


def alchemy_watcher():
    med = medit()
    med.predictor = med.make_predictor()
    while True:
        try:
            engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
            files = glob.glob(Config.UPLOAD_FOLDER + '/*')
            with Session(engine) as session:
                query = session.scalars(select(Images)).all()
                old_img = [img.filename for img in query]
                for new in files:
                    if os.path.basename(new) not in old_img:
                        img = Images(new)
                        session.add(img)
                [image.cutting() for image in query if image.cut_file is False]
                # for img in query: if len(img.predict.all()) < 1 and img.cut_file is True: pred = el.make_predict(
                # med) print(pred) session.add(pred) [session.add(img.make_predict(med)) for img in query if len(
                # img.predict.all()) < 1 and img.cut_file is True]
                session.commit()
                # time.sleep(Config.__dict__[''])
        except Exception as e:
            print(e)


def create_zip(path_to_save_draw: str, date: datetime, image_name: str):
    try:
        zip_folder = Config.SAVE_ZIP

        path_img = glob.glob(f"{path_to_save_draw}/*")

        zip_file_name = f"{image_name}_{date.strftime('%d_%m_%Y__%H_%M')}"

        zipFile = zipfile.ZipFile(os.path.join(zip_folder, f'{zip_file_name}.zip'), 'w', zipfile.ZIP_DEFLATED)
        # with tqdm(total=len(path_img), position=0, leave=False) as pbar:
        for file in path_img:
            # pbar.set_description(f"Total img: {len(path_img)}. Start zip:")
            filename = os.path.basename(file)
            zipFile.write(file, arcname=filename)
            # pbar.update(1)
        zipFile.close()

        result = f'{zip_file_name}.zip created'

    except Exception as e:
        result = e

    else:
        return result


def app_job(med, img):
    pred = img.make_predict(med)
    engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
    with Session(engine) as session:
        session.add(pred)
        session.commit()


class Medit:
    def __init__(self, app=None):
        self.predictor = None
        self.Visualizer = None
        self.ColorMode = None
        self.mitoz_metadata = None
        self.cfg = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.medit = self
        self.predictor = self.make_predictor()

    def create_cfg(self):

        cfg = get_cfg()
        # TODO add config

        if Config.__dict__['DATASET_FORMAT'] == 'Coco':

            path_to_config = model_zoo.get_config_file('COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml')

        elif Config.__dict__['DATASET_FORMAT'] == 'Pascal':
            # path_to_config = os.path.join(Config.__dict__['DETECTRON'],
            #                               "configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml")
            path_to_config = model_zoo.get_config_file('PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml')
        else:
            return 'need set DATASET_FORMAT in .env and config'
        cfg.merge_from_file(path_to_config)
        cfg.INPUT.MIN_SIZE_TRAIN = (3072,)
        cfg.INPUT.MAX_SIZE_TRAIN = 4080
        cfg.INPUT.MAX_SIZE_TEST = 4080
        cfg.INPUT.MIN_SIZE_TEST = 3072
        cfg.SOLVER.STEPS = (1000,)
        cfg.SOLVER.MAX_ITER = Config.__dict__['_ITER']
        cfg.MODEL.DEVICE = Config.__dict__['_CUDA_SET']
        cfg.DATASETS.TRAIN = ("mitoze_train",)
        cfg.DATASETS.TEST = ()
        cfg.DATALOADER.NUM_WORKERS = 2
        # cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.p kl"  # initialize from model zoo
        cfg.SOLVER.IMS_PER_BATCH = 2
        cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
        cfg.SOLVER.BASE_LR = 0.001
        cfg.OUTPUT_DIR = Config.__dict__['_MODEL_OUTPUT']

        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3  # 3 classes (mitoz, GMCC, ostiocit)
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

        cfg.SOLVER.GAMMA = 0.05

        cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.80  # set the testing threshold for this model
        self.cfg = cfg

    def make_predictor(self):
        try:
            if Config.__dict__['DATASET_FORMAT'] == 'Coco':
                register_coco_instances("mitoze_train", {},
                                        f"{Config.__dict__['REG_DATA_SET']}/train/_annotations.coco.json",
                                        f"{Config.__dict__['REG_DATA_SET']}/train")

            elif Config.__dict__['DATASET_FORMAT'] == 'Pascal':
                register_pascal_voc("mitoze_train", Config.__dict__['REG_DATA_SET'], "train_mitoz", "2012",
                                    Config.__dict__['CLASS_NAMES'])

        except Exception as e:
            print(e)
        mitoz_metadata = MetadataCatalog.get("mitoze_train")
        mitoz_metadata.thing_colors = Config.__dict__['_COLORS']
        # torch.multiprocessing.freeze_support()
        # torch.multiprocessing.set_start_method('spawn')
        print('loop make predictor')
        if self.cfg is None:
            self.create_cfg()
        cfg = self.cfg

        predictor = DefaultPredictor(cfg)

        self.Visualizer = Visualizer
        self.ColorMode = ColorMode
        self.mitoz_metadata = mitoz_metadata

        return predictor


if __name__ == '__main__':
    watcher()
