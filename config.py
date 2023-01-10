import torch
import os
from dotenv import load_dotenv
from sys import platform

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.flaskenv'))


class Config(object):

    # location where install detectron2
    DETECTRON = os.environ.get('DETECTRON_PATH')

    _DATASET_FOLDER = './PUT_YOUR_DATASET_HERE'
    _DATASET_NAME = os.environ.get('DATASET_NAME')

    MODEL_NAME = ''
    _MODEL_OUTPUT = os.path.join(_DATASET_FOLDER, f'{_DATASET_NAME}/model20_11_2022')

    REG_DATA_SET = os.path.join(basedir, _DATASET_FOLDER, _DATASET_NAME)

    DATASET_FORMAT = os.environ.get('dataset_format')

    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    BASIC_AUTH_ES = tuple(os.environ.get('BASIC_AUTH_ES').split(','))

    SECRET_KEY = os.environ.get('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    CELERY_BROKER_URL = os.environ.get('REDIS_URL') + '/0' or 'redis://localhost:6379/0'
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    UPDATE_TIME = int(1)  # time in second

    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/downloads')
    SAVE_ZIP = os.path.join(basedir, "app/static/zip")
    CUTTING_FOLDER = os.path.join(basedir, "app/static/cutting_file")
    DRAW = os.path.join(basedir, "app/static/draw")

    BASEDIR = basedir

    if platform == 'win32':
        _MODEL_OUTPUT = _MODEL_OUTPUT.replace('/', '\\')
        REG_DATA_SET = REG_DATA_SET.replace('/', '\\')
        UPLOAD_FOLDER = UPLOAD_FOLDER.replace('/', '\\')
        SAVE_ZIP = SAVE_ZIP.replace('/', '\\')
        CUTTING_FOLDER = CUTTING_FOLDER.replace('/', '\\')
        DRAW = DRAW.replace('/', '\\')

        DETECTRON = os.environ.get('DETECTRON_PATH_WIN')

    folder_list = [UPLOAD_FOLDER, SAVE_ZIP, CUTTING_FOLDER, DRAW]

    for folder in folder_list:
        if not os.path.exists(folder):
            os.mkdir(folder)
            print(f"Directory {folder} created")

    CLASS_NAMES = ("mitoz", "GMCC", "osteocit")

    _CUT_IMAGE_SIZE = (4080, 3072)
    CUT_IMAGE_SIZE = (4080, 3072)

    PERCENTAGE_WHITE = 30
    PERCENTAGE_BLACK = 10

    COLOR_FOR_WHITE_FILTER = [2, 202, 244]  # Its HSV color range for openCV2
    COLOR_FOR_BLACK_FILTER = [2, 202, 244]  # Its HSV color range for openCV2

    COLOR_FOR_DRAW_RECTANGLE = [2, 202, 244]
    COLOR_FOR_DRAW_TEXT = [0, 0, 0]



    _CUDA_SET = "cpu"
    if torch.cuda.is_available():
        _CUDA_SET = "cuda"
    _COLORS = [(0, 0, 0), (1.0, 0, 0), (1.0, 1.0, 240.0 / 255)]
    _ITER = 5000

    POSTS_PER_PAGE = 6

    LANGUAGES = ['en', 'ru']

    YANDEX_TOKEN = os.environ.get('yandex_token')
    YANDEX_FOLDER_ID = os.environ.get('yandex_folder_id')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['unix.mk@gmail.com']

    @property
    def CUT_IMAGE_SIZE(self):
        return self._CUT_IMAGE_SIZE

