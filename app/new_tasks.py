import os
import shutil

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from app.models import Config


def img_cutt(**kwargs):
    from app.utils.cutting.cutting_svs import cutting
    from app.utils.create_zip.create_zip import create_zip

    path_cutting_img = cutting(path=kwargs.get('path'),
                               CUTTING_FOLDER=kwargs.get('CUTTING_FOLDER'),
                               _CUT_IMAGE_SIZE=kwargs.get('_CUT_IMAGE_SIZE'))

    result = create_zip(path_cutting_img)  # Create zip file

    os.remove(kwargs.get('path'))  # Delete download svs
    shutil.rmtree(path_cutting_img)  # Delete cutting folder


def mk_pred(**kwargs):
    from app.utils.prediction.make_predict import make_predict
    from app.utils.create_zip.create_zip import create_zip

    img = kwargs.get('img')

    predict, path = make_predict(image=kwargs.get('img'), predict=kwargs.get('predict'), medit=kwargs.get('medit'))

    try:
        engine = create_engine(Config.__dict__['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
        with Session(engine) as session:
            if predict:
                session.add(predict)
                session.commit()
            result = create_zip(path_to_save=path)
            print(result)
            shutil.rmtree(path)
            os.remove(img.file_path)
    except Exception as e:
        print('ERROR in mk_pred new_tasks', e)


