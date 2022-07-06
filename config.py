import torch
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.flaskenv'))


class Config(object):
    DETECTRON = 'D:/nina/detectron2_repo'

    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    BASIC_AUTH_ES = tuple(os.environ.get('BASIC_AUTH_ES').split(','))

    SECRET_KEY = os.environ.get('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(basedir, 'static/downloads')
    SAVE_ZIP = os.path.join(basedir, "static/zip")
    CUTTING_FOLDER = os.path.join(basedir, "static/cutting_file")

    CLASS_NAMES = ("mitoz", "GMCC", "osteocit")

    _CUT_IMAGE_SIZE = (4080, 3072)
    _CUDA_SET = "cpu"
    if torch.cuda.is_available():
        _CUDA_SET = "cuda"
    _COLORS = [(0, 0, 0), (1.0, 0, 0), (1.0, 1.0, 240.0 / 255)]
    _ITER = 4000
    _DATASET_FOLDER = './PUT_YOUR_DATASET_HERE'
    if not os.path.exists(_DATASET_FOLDER):
        os.mkdir(_DATASET_FOLDER)
        print(f"Directory {_DATASET_FOLDER} created")

    POSTS_PER_PAGE = 3

    LANGUAGES = ['en', 'ru']

    YANDEX_TOKEN = os.environ.get('yandex_token')
    YANDEX_FOLDER_ID = os.environ.get('yandex_folder_id')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['unix.mk@gmail.com']

