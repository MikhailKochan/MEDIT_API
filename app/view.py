import glob
import time
import os
import torch
from sys import platform
from flask import current_app

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


def app_job(med, img):
    pred = img.make_predict(med)
    engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
    with Session(engine) as session:
        session.add(pred)
        session.commit()


class medit:
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
        # cfg.INPUT.MIN

        if Config.__dict__['dataset_format'] == 'Coco':
            cfg.merge_from_file(os.path.join(Config.__dict__['DETECTRON'],
                                             "configs/COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
        elif Config.__dict__['dataset_format'] == 'Pascal':
            cfg.merge_from_file(os.path.join(Config.__dict__['DETECTRON'],
                                             "configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml"))

        cfg.SOLVER.MAX_ITER = Config.__dict__['_ITER']
        cfg.MODEL.DEVICE = Config.__dict__['_CUDA_SET']
        cfg.DATASETS.TRAIN = ("mitoze_train",)
        cfg.DATASETS.TEST = ()
        cfg.DATALOADER.NUM_WORKERS = 2
        cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.pkl"  # initialize from model zoo
        cfg.SOLVER.IMS_PER_BATCH = 4
        cfg.SOLVER.BASE_LR = 0.0025
        cfg.OUTPUT_DIR = Config.__dict__['model_output']
        cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 4  # 3 classes (data, fig, hazelnut)
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

        cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set the testing threshold for this model
        self.cfg = cfg

    def make_predictor(self):
        # if app:
        #     if not os.getcwd() == app.config['DETECTRON']:
        #         os.chdir(app.config['DETECTRON'])
        # else:
        # if not os.getcwd() == Config.__dict__['DETECTRON'] and platform == 'win32':
        #     os.chdir(Config.__dict__['DETECTRON'])

        try:
            # if app:
            #     if app.config['dataset_format'] == 'Coco':
            #         register_coco_instances("mitoze_train", {},
            #                                 f"{app.config['reg_data_set']}/train/_annotations.coco.json",
            #                                 f"{app.config['reg_data_set']}/train")
            #
            #     elif app.config['dataset_format'] == 'Pascal':
            #         register_pascal_voc("mitoze_train", app.config['reg_data_set'], "train", "2012",
            #                             app.config['CLASS_NAMES'])
            # else:
            if Config.__dict__['dataset_format'] == 'Coco':
                register_coco_instances("mitoze_train", {},
                                        f"{Config.__dict__['reg_data_set']}/train/_annotations.coco.json",
                                        f"{Config.__dict__['reg_data_set']}/train")

            elif Config.__dict__['dataset_format'] == 'Pascal':
                register_pascal_voc("mitoze_train", Config.__dict__['reg_data_set'], "train", "2012",
                                    Config.__dict__['CLASS_NAMES'])

        except Exception as e:
            print(e)
        mitoz_metadata = MetadataCatalog.get("mitoze_train")
        mitoz_metadata.thing_colors = Config.__dict__['_COLORS']
        torch.multiprocessing.freeze_support()

        print('loop make predictor')
        if self.cfg is None:
            self.create_cfg()
        cfg = self.cfg

        predictor = DefaultPredictor(cfg)

        self.Visualizer = Visualizer
        self.ColorMode = ColorMode
        self.mitoz_metadata = mitoz_metadata

        return predictor

    # def create_config(self, register_pascal_voc, MetadataCatalog, get_cfg):
    #     try:
    #         register_pascal_voc("mitoze_train", "E:/mitosplus2", "train", "2012", current_app.config['CLASS_NAMES'])
    #         mitoz_metadata = MetadataCatalog.get("mitoze_train")
    #
    #         mitoz_metadata.thing_colors = [(0, 0, 0), (1.0, 0, 0), (1.0, 1.0, 240.0 / 255)]
    #         torch.multiprocessing.freeze_support()
    #
    #         print('loop')
    #
    #         num_gpu = 1
    #         bs = (num_gpu * 2)
    #         cfg = get_cfg()
    #         cfg.merge_from_file("./configs/PascalVOC-Detection/faster_rcnn_R_50_FPN.yaml")
    #         cfg.DATASETS.TRAIN = ("mitoze_train",)
    #         cfg.DATASETS.TEST = ()  # no metrics implemented for this dataset
    #         cfg.DATALOADER.NUM_WORKERS = 2
    #         cfg.MODEL.WEIGHTS = "detectron2://ImageNetPretrained/MSRA/R-50.pkl"  # initialize from model zoo
    #         cfg.SOLVER.IMS_PER_BATCH = 4
    #         cfg.SOLVER.BASE_LR = 0.02 * bs / 16
    #         cfg.SOLVER.MAX_ITER = 4000  # 300 iterations seems good enough, but you can certainly train longer
    #         cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # faster, and good enough for this toy dataset
    #         cfg.MODEL.ROI_HEADS.NUM_CLASSES = 4  # 3 classes (data, fig, hazelnut)
    #         # cfg.OUTPUT_DIR = app.config['']
    #         os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    #         cfg.MODEL.DEVICE = current_app.config['_CUDA_SET']
    #         return cfg, mitoz_metadata
    #     except Exception as e:
    #         print(f'ERROR in create config: {e}')
    #
    # def load_model(self, cfg, DefaultPredictor):
    #     cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
    #     cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set the testing threshold for this model
    #     predictor = DefaultPredictor(cfg)
    #     return predictor


class Medit:
    def __init__(self, app=None):
        self.mod = ''
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.medit = self
        # if not hasattr(app, 'extensions'):  # pragma: no cover
        #     app.extensions = {}
        # app.extensions['medit'] = medit
        # app.context_processor(self.context_processor)

    @staticmethod
    def context_processor():
        return {
            'medit': current_app.extensions['medit']
        }


if __name__ == '__main__':
    watcher()
