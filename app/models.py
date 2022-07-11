from app import login, db
from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pathlib
import os
os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')
import openslide
from tqdm import tqdm, trange


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_number = db.Column(db.Integer)
    name = db.Column(db.String(64), index=True, unique=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    img_creation_time = db.Column(db.String(64), index=True)
    img_creation_date = db.Column(db.String(64), index=True)
    predict = db.relationship('Predict', backref='Images', lazy='dynamic')
    filename = db.Column(db.String(128))
    cut_file = db.Column(db.Boolean, default=False, nullable=False)
    format = db.Column(db.String(64))
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    file_path = db.Column(db.String(128), index=True, unique=True)

    def __init__(self, path: str):

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

        elif self.format.lower() == '.jpg':
            pass

        self.cutting()

    def cutting(self):

        h_sum = int(self.height / current_app.config['_CUT_IMAGE_SIZE'][1])
        w_sum = int(self.width / current_app.config['_CUT_IMAGE_SIZE'][0])

        if h_sum and w_sum <= 1:
            text = f"This img less than {current_app.config['CUTTING_FOLDER']}, cutting not need."
            current_app.logger.info(text)
            return text
        if self.format.lower() == '.svs':
            file = openslide.OpenSlide(self.file_path)
        else:
            return f'{self.format} not added'
        # elif self.format.lower() == '.jpg':
        #     return f"jpg format not add"
        h_rest = self.height % current_app.config['_CUT_IMAGE_SIZE'][1]
        w_rest = self.width % current_app.config['_CUT_IMAGE_SIZE'][0]
        s_col = int(h_rest / 2)
        s_row = int(w_rest / 2)
        total = h_sum * w_sum

        if not os.path.exists(os.path.join(current_app.config['CUTTING_FOLDER'], self.filename)):
            os.mkdir(os.path.join(current_app.config['CUTTING_FOLDER'], self.filename))
            current_app.logger.info(f"Directory {self.filename} created")
            with tqdm(total=total, position=0, leave=False) as pbar:
                for i in range(0, w_sum):
                    for j in range(0, h_sum):
                        pbar.set_description(f"Total img: {total}. Start cutting:")
                        start_row = j * current_app.config['_CUT_IMAGE_SIZE'][0] + s_row
                        start_col = i * current_app.config['_CUT_IMAGE_SIZE'][1] + s_col
                        filename = f"{self.filename}_im" + "_." + str(i) + "." + str(j)
                        path_to_save_cut_file = os.path.join(os.path.join(current_app.config['CUTTING_FOLDER'], self.filename), f"{filename}.jpg")
                        self.cut(start_row, start_col, path_to_save_cut_file, file)

                        pbar.update(1)
        else:
            current_app.logger.info(f"folder {self.filename} already exists")
        self.cut_file = True

    def cut(self, start_row: int, start_col: int, path_to_save_cut_file, file):
        if self.format.lower() == '.svs':
            img = file.read_region((start_row, start_col), 0, app.config['_CUT_IMAGE_SIZE'])
            img = img.convert('RGB')
            img.save(path_to_save_cut_file)

    def __repr__(self):
        return f'<Image {self.name} load on server {self.timestamp.strftime("%d/%m/%Y %H:%M:%S")}' \
               f' and create {self.img_creation_date} {self.img_creation_time}>'


class Predict(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    result_all_mitoz = db.Column(db.Integer)
    result_max_mitoz_in_one_img = db.Column(db.String(128))
    count_img = db.Column(db.Integer)
    name_img_have_max_mitoz = db.Column(db.Integer)
    status = db.Column(db.String(128))
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    model = db.Column(db.String(128))

    def __repr__(self):
        return f'<Predict Images {self.Images.filename} create {self.timestamp.strftime("%d/%m/%Y %H:%M:%S")}>'


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# class Status(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(128))
#     predict = db.relationship('Predict', backref='status', lazy='dynamic')
#
#     def __repr__(self):
#         return f'{self.name}'
