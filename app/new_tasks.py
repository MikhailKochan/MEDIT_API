import os
import shutil

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.models import Config


def img_cutt(**kwargs):
    from app.utils.cutting.cutting_svs import cutting
    from app.utils.create_zip.create_zip import create_zip

    print(kwargs)

    path_cutting_img = cutting(path=kwargs.get('path'),
                               CUTTING_FOLDER=kwargs.get('CUTTING_FOLDER'),
                               _CUT_IMAGE_SIZE=kwargs.get('_CUT_IMAGE_SIZE'))

    result = create_zip(path_cutting_img)  # Create zip file

    print(result)

    os.remove(kwargs.get('path'))  # Delete download svs
    shutil.rmtree(path_cutting_img)  # Delete cutting folder


def mk_pred(**kwargs):
    from app.utils.prediction.make_predict import make_predict
    from app.utils.create_zip.create_zip import create_zip

    img = kwargs.get('img')
    print('img', img)

    predict, path = make_predict(img=kwargs.get('img'),
                                 predict=kwargs.get('predict'),
                                 medit=kwargs.get('medit'))
    if predict:
        engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
        with Session(engine) as session:
            session.add(predict)
            session.commit()

        create_zip(path_to_save=path)

        os.remove(img.file_path)
        shutil.rmtree(path)
