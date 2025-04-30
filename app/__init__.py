import sys
import logging

from config import Config

from redis import Redis
from sqlalchemy import MetaData

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_celeryext import FlaskCeleryExt

from logging import StreamHandler

from flask_moment import Moment
from app.utils.celery import make_celery

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Введите логин и пароль прежде чем просмотреть эту страницу'

moment = Moment()

redis_client = Redis.from_url(Config.REDIS_URL)
ext_celery = FlaskCeleryExt(create_celery_app=make_celery)


def register_blueprints(_app):

    from app.errors import bp as errors_bp
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.celery_task import bp as celery_task_bp
    from app.utils.cutting import bp as cutting_bp
    from app.utils.prediction import bp as predict_bp

    _app.register_blueprint(errors_bp)
    _app.register_blueprint(auth_bp, url_prefix='/auth')
    _app.register_blueprint(main_bp)
    _app.register_blueprint(celery_task_bp)
    _app.register_blueprint(cutting_bp)
    _app.register_blueprint(predict_bp)


def create_logger_handlers():
    formatter = logging.Formatter('[%(asctime)s] [%(process)d] [%(levelname)s]: %(message)s')

    handler = StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    err_handler = StreamHandler(sys.stderr)
    err_handler.setFormatter(formatter)
    err_handler.setLevel(logging.WARNING)

    return handler, err_handler


def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    handler, err_handler = create_logger_handlers()
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.addHandler(err_handler)
    app.logger.setLevel(logging.DEBUG if app.config.get('DEBUG') else logging.INFO)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login.init_app(app)

    app.redis = redis_client
    # Celery init
    ext_celery.init_app(app)

    register_blueprints(app)

    return app


from app import models
