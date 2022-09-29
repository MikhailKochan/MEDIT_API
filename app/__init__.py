import logging
import os
import rq
# from raven.contrib.flask import Sentry
from config import Config
from redis import Redis

from celery import Celery

from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_celeryext import FlaskCeleryExt

from logging.handlers import SMTPHandler, RotatingFileHandler
# from flask_mail import Mail
# from flask_bootstrap import Bootstrap
from flask_moment import Moment
from app.utils.celery import make_celery

# import sentry_sdk
# from sentry_sdk.integrations.flask import FlaskIntegration
# from flask_babel import Babel, lazy_gettext as _l


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
# mail = Mail()
# bootstrap = Bootstrap()
moment = Moment()
# babel = Babel()
# sentry = Sentry(dsn='http://2abaac024c2d415280fe49b22288f719@localhost:9000/3')
ext_celery = FlaskCeleryExt(create_celery_app=make_celery)


def create_app(config_class=Config):
    # sentry_sdk.init(
    #     dsn="http://2abaac024c2d415280fe49b22288f719@localhost:9000/3",
    #     integrations=[
    #         FlaskIntegration(),
    #     ],
    #     traces_sample_rate=1.0
    # )

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    # bootstrap.init_app(app)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('medit-task', connection=app.redis)

    # Celery init
    ext_celery.init_app(app)

    # sentry.init_app(app)

    from app.view import medit
    Med = medit()
    Med.init_app(app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='MEDIT Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
            # логи
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/medit.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('MEDIT startup')

    return app


from app import models
