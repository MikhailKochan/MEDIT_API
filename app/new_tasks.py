import os
import shutil

from models import Images
from config import Config

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)


def img_cutt(image_id):
    print(image_id)
    with Session(engine) as session:
        img = session.query(Images).get(image_id)
        # img = Images.query.filter_by(id=image_id).first()
        path_cut_file = f"{Config.CUTTING_FOLDER}/{img.filename}"
        if not img.cut_file:
            img.cutting()

            os.remove(f"{Config.UPLOAD_FOLDER}/{img.filename}")

            result = img.create_zip(path_cut_file)

            print(result)

            shutil.rmtree(path_cut_file)
        else:
            if os.path.exists(path_cut_file):
                pass

