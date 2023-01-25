from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pathlib
import os
import redis
import rq

import json
from time import time

from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')
import openslide

import sqlite3
from app import login, db


def generator_id(cls):
    try:
        connect = sqlite3.connect('app.db')
        cursor = connect.cursor()
        cursor.execute(f"SELECT * FROM {type(cls).__name__}")
        result = cursor.fetchall()
        connect.commit()
        return len(result) + int(1)
    except Exception as e:
        print(f'Error in generator_id : {e}')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    settings_id = db.Column(db.Integer, db.ForeignKey('settings.id'))

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    predict = db.relationship('Predict', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def launch_task(self, name, description, job_timeout: int = 1800, **kwargs):
        current_app.logger.info(f"{self.username} create task")

        image = kwargs.get('img')
        predict = kwargs.get('predict')
        kwargs['settings'] = self.get_settings()

        rq_job = current_app.task_queue.enqueue('app.new_tasks.' + name,
                                                job_timeout=job_timeout,
                                                **kwargs
                                                )

        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)

        if image:
            task.images = image
        if predict:
            task.predict = predict

        db.session.add(task)
        current_app.logger.info(f"task id: {task.id} - add to db")

        return task

    def get_settings(self):
        settings = self.settings
        if settings is None:
            settings = Settings(user=self)
            self.settings = settings
            db.session.add(settings)
        return settings

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).all()


class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    url = db.Column(db.String(128))
    description = db.Column(db.Text)

    settings = db.relationship('Settings', backref='model', lazy='dynamic')
    predict = db.relationship('Predict', backref='model', lazy='dynamic')

    def __init__(self, name: str = None, url: str = None, description: str = None):
        self.name = name if name else current_app.config['MODEL_NAME']
        self.url = url if url else current_app.config['MODEL_URL']
        self.description = description if description else current_app.config['MODEL_DESCRIPTION']

    def __repr__(self):
        return f'ModelWeights\nName: {self.name}\nUrl: {self.url}\nDescription: {self.description}'


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user = db.relationship('User', backref='settings', lazy='dynamic')

    model_id = db.Column(db.Integer, db.ForeignKey('model.id'))

    cutting_images_size = db.Column(db.Text)

    percentage_white = db.Column(db.Integer)
    percentage_black = db.Column(db.Integer)

    color_for_draw_rectangle = db.Column(db.Text)
    color_for_draw_text = db.Column(db.Text)

    def __init__(self, user: User = None):
        if user is not None:
            self.user_id = user.id
        self.percentage_white = int(current_app.config['PERCENTAGE_WHITE'])
        self.percentage_black = int(current_app.config['PERCENTAGE_BLACK'])
        self.color_for_draw_rectangle = json.dumps(current_app.config['COLOR_FOR_DRAW_RECTANGLE'])
        self.color_for_draw_text = json.dumps(current_app.config['COLOR_FOR_DRAW_TEXT'])
        self.cutting_images_size = json.dumps(current_app.config['_CUT_IMAGE_SIZE'])
        model = Model.query.get(1)
        if model is None:
            model = Model()
        self.model = model

    def get_cutting_size(self):
        return tuple(json.loads(self.cutting_images_size))

    def get_height(self):
        return int(json.loads(self.cutting_images_size)[1])

    def get_width(self):
        return int(json.loads(self.cutting_images_size)[0])

    def get_color_for_rectangle(self):
        return list(json.loads(self.color_for_draw_rectangle))

    def get_color_for_text(self):
        return list(json.loads(str(self.color_for_draw_text)))

    @staticmethod
    def get_default_settings():
        return {'percentage_white': int(current_app.config['PERCENTAGE_WHITE']),
                'percentage_black': int(current_app.config['PERCENTAGE_BLACK']),
                'color_for_draw_rectangle': json.dumps(current_app.config['COLOR_FOR_DRAW_RECTANGLE']),
                'color_for_draw_text': json.dumps(current_app.config['COLOR_FOR_DRAW_TEXT']),
                'cutting_images_size': json.dumps(current_app.config['_CUT_IMAGE_SIZE'])}


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_number = db.Column(db.Integer, unique=False)
    name = db.Column(db.String(64), index=True, unique=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    img_creation_time = db.Column(db.String(64), index=True)
    img_creation_date = db.Column(db.String(64), index=True)

    predict = db.relationship('Predict', backref='images', lazy='dynamic')

    tasks = db.relationship('Task', backref='images', lazy='dynamic', cascade="all, delete", passive_deletes=True)

    filename = db.Column(db.String(128))
    cut_file = db.Column(db.Boolean, default=False, nullable=False)
    format = db.Column(db.String(64))
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    file_path = db.Column(db.String(128), index=True)

    notifications = db.relationship('Notification', backref='images',
                                    lazy='dynamic')

    def __init__(self, path: str = None):
        # self.id = generator_id(self)
        self.timestamp = datetime.utcnow()
        self.cut_file = False
        if path:
            self.file_path = path
            self.filename = os.path.basename(path)
            self.format = pathlib.Path(path).suffix
            if self.format.lower() == '.svs':
                file = openslide.OpenSlide(path)
                self.analysis_number = file.properties['aperio.ImageID']
                self.name = file.properties['aperio.Filename']
                self.img_creation_time = file.properties['aperio.Time']
                self.img_creation_date = file.properties['aperio.Date']
                self.width, self.height = file.level_dimensions[0]
            # TODO add more format
            elif self.format.lower() == '.jpg':
                pass

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), images=self)
        db.session.add(n)
        return n

    def cutting(self, celery_job=None):
        try:
            f_path = os.path.join(current_app.config['BASEDIR'],
                                  current_app.config['UPLOAD_FOLDER'],
                                  self.filename)

            if self.format.lower() == '.svs':
                from app.utils.cutting.cutting_svs import cutting as start_cut

            elif self.format.lower() == '.jpg':
                current_app.logger.info('JPG not added in APP')
                return

            else:
                current_app.logger.info(f'{self.format} not added in APP')
                return

            current_app.logger.info(f'start cutting {self.filename}')

            save_folder = start_cut(path=f_path,
                                    CUTTING_FOLDER=current_app.config['CUTTING_FOLDER'],
                                    _CUT_IMAGE_SIZE=current_app.config['_CUT_IMAGE_SIZE'],
                                    job=celery_job)

            current_app.logger.info(f'finish cutting {self.filename}')

            return save_folder
        except Exception as e:
            current_app.logger.error(f"ERROR IN CUTTING: {e}")

    def make_predict(self, settings: Settings, celery_job=None):
        try:
            time_now = datetime.utcnow()
            predict = Predict(images=self,
                              timestamp=time_now,
                              path_to_save=os.path.join(current_app.config['BASEDIR'],
                                                        current_app.config['DRAW'],
                                                        f"{self.filename[:-4]}_{time_now.strftime('%d_%m_%Y__%H_%M')}"))
            os.makedirs(predict.path_to_save, exist_ok=True)

            if self.format.lower() == '.svs':
                from app.utils.prediction.make_predict import make_predict_celery as start_predict

            elif self.format.lower() == '.jpg':
                return current_app.logger.info('JPG not added in APP')

            else:
                return current_app.logger.info(f'{self.format} not added in APP')

            current_app.logger.info(f'start predict {self.filename}')

            predict = start_predict(image=self,
                                    predict=predict,
                                    job=celery_job,
                                    settings=settings)

            current_app.logger.info(f'finish predict {self.filename}')
            return predict
        except Exception as e:
            print(f"ERROR in predict: {e}")
            if current_app:
                current_app.logger.error(e)

    def __repr__(self):
        if self.timestamp:
            text = f'<Image {self.name} load on server {self.timestamp.strftime("%d/%m/%Y %H:%M:%S")}' \
                   f' and create {self.img_creation_date} {self.img_creation_time}>'
        else:
            text = f'<Image {self.name}'
        return text


class Predict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    result_all_mitoz = db.Column(db.Integer)
    result_max_mitoz_in_one_img = db.Column(db.String(128))
    count_img = db.Column(db.Integer)
    name_img_have_max_mitoz = db.Column(db.String(512))

    path_to_save = db.Column(db.String(512))

    tasks = db.relationship('Task', backref='predict', lazy='dynamic', cascade="all, delete", passive_deletes=True)

    status_id = db.Column(db.Integer, db.ForeignKey('status.id'))

    image_id = db.Column(db.Integer, db.ForeignKey('images.id'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    model_id = db.Column(db.Integer, db.ForeignKey('model.id'))

    def __repr__(self):
        return f'<Predict Images {self.images.filename} create {self.timestamp.strftime("%d/%m/%Y %H:%M:%S")}>'

    def add_status(self, name, data):
        s = self.status.first()
        if s:
            self.status.update({'payload_json': json.dumps(data)})

        else:
            s = Status(name=name, payload_json=json.dumps(data), predict=self)
            db.session.add(s)

        if s and data['progress'] >= 100:
            self.status.delete()
            return
        return s

    def create_zip(self, path_to_save_draw: str):
        from app.utils.create_zip.create_zip import create_zip
        try:

            result = create_zip(self, path_to_save_draw)

        except Exception as e:
            result = e

        return result


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    predict_id = db.Column(db.Integer, db.ForeignKey('predict.id', ondelete="CASCADE"))
    image_id = db.Column(db.Integer, db.ForeignKey('images.id', ondelete="CASCADE"))

    complete = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError) as e:
            current_app.logger.error(e)
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

    def get_filename(self):
        job = self.get_rq_job()
        return job.meta.get('filename')


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)

    predict = db.relationship('Predict', backref='status', lazy='dynamic')

    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
