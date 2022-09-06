import os
import shutil

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.models import Config


def img_cutt(**kwargs):
    from app.utils.cutting.cutting_svs import cutting
    from app.utils.create_zip.create_zip import create_zip

    print('kwargs get "path"', kwargs.get('path'))
    path = kwargs.get('path')
    print(path)
    path_cutting_img = cutting(path=path)

    result = create_zip(path_cutting_img)  # Create zip file

    print(result)

    os.remove(kwargs.get('path'))  # Delete download svs
    shutil.rmtree(path_cutting_img)  # Delete cutting folder


def mk_pred(**kwargs):
    from app.utils.prediction.make_predict import make_predict
    from app.utils.create_zip.create_zip import create_zip

    img, predict, medit = kwargs.get('img'), kwargs.get('predict'), kwargs.get('medit')

    predict, path = make_predict(img, predict, medit)
    if predict:
        engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
        with Session(engine) as session:
            session.add(predict)
            session.commit()

        create_zip(path_to_save=path)

        os.remove(img.file_path)
        shutil.rmtree(path)
