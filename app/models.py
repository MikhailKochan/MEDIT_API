from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pathlib
from config import Config
import os
from decimal import Decimal as D
import redis
import rq
import numpy as np

from rq import get_current_job
from rq import Retry
import json
from time import time
import zipfile

from sys import platform
if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')
import openslide

from tqdm import tqdm
import glob
import cv2
from pascal_voc_writer import Writer
import sqlite3
from app import login, db


# from app.view import create_zip


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

    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def launch_task(self, name, description, job_timeout: int = 1800, **kwargs):
        current_app.logger.info(f"{self.username} create task")

        rq_job = current_app.task_queue.enqueue('app.new_tasks.' + name,
                                                job_timeout=job_timeout,
                                                **kwargs
                                                )

        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)

        db.session.add(task)
        current_app.logger.info(f"task id: {task.id} - add to db")

        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_number = db.Column(db.Integer, unique=True)
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
                self.height, self.width = file.level_dimensions[0]
            # TODO add more format
            elif self.format.lower() == '.jpg':
                pass

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), images=self)
        db.session.add(n)
        return n

    def cutting(self):
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

            start_cut(path=f_path,
                      CUTTING_FOLDER=current_app.config['CUTTING_FOLDER'],
                      _CUT_IMAGE_SIZE=current_app.config['_CUT_IMAGE_SIZE'],
                      )
            current_app.logger.info(f'finish cutting {self.filename}')
        except Exception as e:
            current_app.logger.error(f"ERROR IN CUTTING: {e}")

    def make_predict(self, predict, cutting=False):
        try:
            all_mitoz = 0

            max_mitoz_in_one_img = 0

            progress = 0

            _set_task_progress(progress, all_mitoz, func='make_predict')

            Visualizer = current_app.medit.Visualizer

            cfg = current_app.medit.cfg

            mitoz_metadata = current_app.medit.mitoz_metadata

            ColorMode = current_app.medit.ColorMode

            predictor = current_app.medit.predictor

            CLASS_NAMES = current_app.config['CLASS_NAMES']

            path_img = glob.glob(f"{current_app.config['CUTTING_FOLDER']}/{self.filename}/*.jpg") if current_app else \
                glob.glob(f"{Config.__dict__['CUTTING_FOLDER']}/{self.filename}/*.jpg")

            date_now = predict.timestamp.strftime('%d_%m_%Y__%H_%M')

            path_to_save_draw = f"{current_app.config['DRAW']}/{self.filename}/" \
                                f"{date_now}" if current_app else \
                f"{Config.__dict__['DRAW']}/{self.filename}/{date_now}"

            mitoz = CLASS_NAMES.index('mitoz')

            if not cutting:
                current_app.logger.info(f'start img.cutting()')
                self.cutting()
                path_img = glob.glob(f"{current_app.config['CUTTING_FOLDER']}/{self.filename}/*.jpg")
                self.cut_file = True

                db.session.add(self)
                current_app.logger.info(f'finish cutting {self}, add to db')
                db.session.commit()

            total = len(path_img)

            if not os.path.exists(path_to_save_draw):
                os.mkdir(path_to_save_draw)
                current_app.logger.info(f"Directory {self.filename} for draw created")
            with tqdm(total=total, position=0, leave=False) as pbar:
                for img in path_img:
                    pbar.set_description(f"Total img: {total}. Start create predict")

                    filename = os.path.basename(img)[:-4]
                    path_to_save_xml = os.path.dirname(img)

                    im = cv2.imread(img)
                    outputs = predictor(im)

                    outputs = outputs["instances"].to("cpu")

                    classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None
                    boxes = outputs.pred_boxes if outputs.has("pred_boxes") else None

                    if mitoz in classes:
                        v = Visualizer(im[:, :, ::-1],
                                       metadata=mitoz_metadata,
                                       scale=1,
                                       instance_mode=ColorMode.SEGMENTATION)

                        v = v.draw_instance_predictions(outputs)
                        cv2.imwrite(os.path.join(path_to_save_draw, f"{filename}.jpg"), v.get_image()[:, :, ::-1])

                        all_mitoz += classes.count(mitoz)
                        if classes.count(mitoz) > max_mitoz_in_one_img:
                            max_mitoz_in_one_img = classes.count(mitoz)
                            img_name = f"{filename}.jpg"

                    boxes = boxes.tensor.detach().numpy()
                    num_instances = len(boxes)

                    height, width = im.shape[:2]
                    writer = Writer(img, height, width)
                    for i in range(num_instances):
                        x0, y0, x1, y1 = boxes[i]
                        x0 += 1.0
                        y0 += 1.0
                        writer.addObject(CLASS_NAMES[classes[i]], int(x0), int(y0), int(x1),
                                         int(y1))
                    writer.save(f'{path_to_save_xml}/{filename}.xml')

                    count = 1
                    if not cutting:
                        count = count / 2

                    progress += count / total * 100.0

                    _set_task_progress(float(D(str(progress)).quantize(D("1.00"))), all_mitoz, func='cutting')

                    pbar.update(1)

            return predict(result_all_mitoz=all_mitoz,
                           result_max_mitoz_in_one_img=max_mitoz_in_one_img,
                           count_img=total,
                           name_img_have_max_mitoz=img_name,
                           model=cfg.MODEL.WEIGHTS,
                           image_id=self.id)

        except Exception as e:
            print(f"ERROR in predict: {e}")
            if current_app:
                current_app.logger.error(e)

    def alternative_predict(self, predict):
        try:
            progress = 0

            max_mitoz_in_one_img = 0

            _set_task_progress(progress, 0, func='alternative_predict')

            Visualizer = current_app.medit.Visualizer

            cfg = current_app.medit.cfg

            mitoz_metadata = current_app.medit.mitoz_metadata

            ColorMode = current_app.medit.ColorMode

            predictor = current_app.medit.predictor

            date_now = predict.timestamp.strftime('%d_%m_%Y__%H_%M')

            CLASS_NAMES = current_app.config['CLASS_NAMES']
            _CUT_IMAGE_SIZE = current_app.config['_CUT_IMAGE_SIZE']

            h_sum = int(self.height / _CUT_IMAGE_SIZE[1])
            w_sum = int(self.width / _CUT_IMAGE_SIZE[0])

            if self.format.lower() == '.svs':
                f_path = os.path.join(current_app.config['BASEDIR'],
                                      current_app.config['UPLOAD_FOLDER'],
                                      self.filename)
                current_app.logger.info(f"Directory {f_path} for open in openslide")
                file = openslide.OpenSlide(f_path)

            else:
                return f'{self.format} not added'

            h_rest = self.height % _CUT_IMAGE_SIZE[1]
            w_rest = self.width % _CUT_IMAGE_SIZE[0]
            s_col = int(h_rest / 2)
            s_row = int(w_rest / 2)
            total = h_sum * w_sum

            path_to_save_draw = os.path.join(current_app.config['BASEDIR'],
                                             f"{current_app.config['DRAW']}/{self.filename}/{date_now}")

            if not os.path.exists(path_to_save_draw):

                os.mkdir(path_to_save_draw)

                current_app.logger.info(f"Directory {self.filename} for draw created")

            mitoz = CLASS_NAMES.index('mitoz')
            all_mitoz = 0

            with tqdm(total=total, position=0, leave=False) as pbar:
                for i in range(0, w_sum):
                    for j in range(0, h_sum):
                        pbar.set_description(f"Total img: {total}. Start cutting")

                        start_row = j * _CUT_IMAGE_SIZE[0] + s_row
                        start_col = i * _CUT_IMAGE_SIZE[1] + s_col

                        filename = "0_im" + "_" + str(i) + "_" + str(j)

                        if self.format.lower() == '.svs':

                            img = file.read_region((start_row, start_col), 0, _CUT_IMAGE_SIZE)
                            img = img.convert('RGB')

                            im = np.asarray(img)

                            outputs = predictor(im)

                            outputs = outputs["instances"].to("cpu")

                            classes = outputs.pred_classes.tolist() if outputs.has("pred_classes") else None

                            if mitoz in classes:
                                v = Visualizer(im[:, :, ::-1],
                                               metadata=mitoz_metadata,
                                               scale=1,
                                               instance_mode=ColorMode.SEGMENTATION)

                                v = v.draw_instance_predictions(outputs)
                                cv2.imwrite(os.path.join(path_to_save_draw, f"{filename}.jpg"),
                                            v.get_image()[:, :, ::-1])

                                all_mitoz += classes.count(mitoz)
                                if classes.count(mitoz) > max_mitoz_in_one_img:
                                    max_mitoz_in_one_img = classes.count(mitoz)
                                    # img_name = f"{filename}.jpg"

                        progress += 1 / total * 100.0

                        _set_task_progress(float(D(str(progress)).quantize(D("1.00"))),
                                           all_mitoz=all_mitoz,
                                           func='alternative_predict')

                        pbar.update(1)

            predict.result_all_mitoz = all_mitoz

            predict.result_max_mitoz_in_one_img = max_mitoz_in_one_img

            predict.count_img = total

            # predict.name_img_have_max_mitoz = img_name

            predict.model = cfg.MODEL.WEIGHTS

            predict.image_id = self.id

            return predict

        except Exception as e:
            current_app.logger.error(e)

    def launch_task(self, name, description, *args, **kwargs):
        task = self.get_tasks_in_progress()
        if len(task) >= 1:
            return 'You can make only one task in moment'
        else:
            rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, job_timeout=10800, retry=Retry(max=3))
            task = Task(id=rq_job.get_id(), name=name, description=description,
                        predict_id=self.id)
            db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(predict=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, predict=self,
                                    complete=False).first()

    def create_zip(self, path_to_save_draw: str):
        from app.utils.create_zip.create_zip import create_zip
        try:

            result = create_zip(self, path_to_save_draw)

        except Exception as e:
            result = e

        else:
            return result

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
    name_img_have_max_mitoz = db.Column(db.Integer)

    tasks = db.relationship('Task', backref='predict', lazy='dynamic', cascade="all, delete", passive_deletes=True)

    status = db.relationship('Status', backref='predict', lazy='dynamic', cascade="all, delete", passive_deletes=True)

    image_id = db.Column(db.Integer, db.ForeignKey('images.id'))

    model = db.Column(db.String(128))

    # def __init__(self,
    #              image_id=None,
    #              result_all_mitoz=None,
    #              result_max_mitoz_in_one_img=None,
    #              count_img=None,
    #              name_img_have_max_mitoz=None,
    #              model=None,
    #              ):
    #
    #     self.image_id = image_id
    #     self.result_all_mitoz = result_all_mitoz
    #     self.result_max_mitoz_in_one_img = result_max_mitoz_in_one_img
    #     self.count_img = count_img
    #     self.name_img_have_max_mitoz = name_img_have_max_mitoz
    #     self.model = model

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

    def launch_task(self, name, description, *args, **kwargs):
        task = self.get_tasks_in_progress()
        if len(task) >= 1:
            return 'You can make only one task in moment'
        else:
            rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, job_timeout=10800, retry=Retry(max=3))
            task = Task(id=rq_job.get_id(), name=name, description=description,
                        predict_id=self.id)
            db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(predict=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, predict=self,
                                    complete=False).first()

    def create_zip(self, path_to_save_draw: str):
        from app.utils.create_zip.create_zip import create_zip
        try:

            result = create_zip(self, path_to_save_draw)

        except Exception as e:
            result = e

        else:
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


def _set_task_progress(progress, all_mitoz=None, func=None, filename=None):
    print('in _set_task_in_progress')
    job = get_current_job()
    if job:
        job_id = job.get_id()
        job.meta['progress'] = progress
        job.save_meta()

        if current_app:
            rd = current_app.redis
        else:
            from redis import Redis
            rd = Redis.from_url(Config.__dict__['REDIS_URL'])

        rd.set(job_id, json.dumps({'task_id': job_id,
                                   'mitoze': all_mitoz,
                                   'filename': filename,
                                   'func': func,
                                   'progress': progress}))
        try:
            if progress >= 100:
                if current_app:
                    task = Task.query.get(job_id)
                    task.complete = True
                    db.session.commit()
                else:
                    from sqlalchemy import select, create_engine
                    from sqlalchemy.orm import Session

                    engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
                    with Session(engine) as session:
                        task = session.query(Task).get(job_id)
                        task.complete = True
                        session.commit()
                # current_app.redis.delete(job_id)

        except Exception as e:
            print(f'ERROR in set_task_progress: {e}')
            if current_app:
                current_app.logger.error(e)
                db.session.rollback()


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    predict_id = db.Column(db.Integer, db.ForeignKey('predict.id', ondelete="CASCADE"))
    image_id = db.Column(db.Integer, db.ForeignKey('images.id', ondelete="CASCADE"))
    complete = db.Column(db.Boolean, default=False)

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


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    predict_id = db.Column(db.Integer, db.ForeignKey('predict.id', ondelete="CASCADE"))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
