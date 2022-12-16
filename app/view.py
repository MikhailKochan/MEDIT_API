import glob
import time
import os
import torch
import zipfile

from sys import platform
from flask import current_app
from datetime import datetime

import sqlite3
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from .models import Images, Predict
from config import Config

from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data.datasets import register_coco_instances, register_pascal_voc
from detectron2.engine import DefaultPredictor, DefaultTrainer
from detectron2.utils.visualizer import ColorMode, Visualizer

from app import db


def file_name_maker(filename):
    """
    функция для предотвращения повторения имен при сохранении
    Args:
        filename:
            str
    Returns:
        filename + (n)
        n - count filename repeated
    """
    g = glob.glob(f"{os.path.join(current_app.config['UPLOAD_FOLDER'], filename[:-4])}*")

    if g:
        g = g.sort()
        point = '.'
        print(g[0])
        spl = g[0].split(point)
        end_str = spl.pop(-1)
        name = point.join(spl)
        new_filename = name + f"_{l}." + end_str
        return os.path.basename(new_filename)
    else:
        return filename


def file_save_and_add_to_db(request, do_predict=False):
    files = request.files.getlist("file")
    if files:
        for file in files:
            filename = file_name_maker(file.filename)
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            current_app.logger.info(f'получил файл {file.filename}')
            file.save(path)
            current_app.logger.info(f"сохранил файл {filename}")
            img = Images(path)
            # if Images.query.filter_by(analysis_number=img.analysis_number).first() is None:
            db.session.add(img)
            db.session.commit()
            current_app.logger.info(f"{filename} saved to {current_app.config['UPLOAD_FOLDER']}")
            # else:
            #     current_app.logger.info(f"{filename} already in bd")
            # img = Images.query.filter_by(analysis_number=img.analysis_number).first()

            if do_predict:
                path_to_save_draw = os.path.join(Config.BASEDIR, Config.DRAW, filename)
                if not os.path.exists(path_to_save_draw):
                    os.mkdir(path_to_save_draw)
            return img
    else:
        return None


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
        with tqdm(total=len(path_img), position=0, leave=False) as pbar:
            for file in path_img:
                pbar.set_description(f"Total img: {len(path_img)}. Start zip:")
                filename = os.path.basename(file)
                zipFile.write(file, arcname=filename)
                pbar.update(1)
        zipFile.close()

        result = f'{zip_file_name}.zip created'

    except Exeption as e:
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

            path_to_config = os.path.join(Config.__dict__['DETECTRON'],
                                          'configs/COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml')

        elif Config.__dict__['DATASET_FORMAT'] == 'Pascal':
            path_to_config = os.path.join(Config.__dict__['DETECTRON'],
                                          "configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml")
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
        # cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.pkl"  # initialize from model zoo
        cfg.SOLVER.IMS_PER_BATCH = 2
        cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
        cfg.SOLVER.BASE_LR = 0.001
        cfg.OUTPUT_DIR = Config.__dict__['_MODEL_OUTPUT']

        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3  # 3 classes (mitoz, GMCC, ostiocit)
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

        cfg.SOLVER.GAMMA = 0.05

        cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.95  # set the testing threshold for this model
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
