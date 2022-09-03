import os
import shutil


def img_cutt(path, CUTTING_FOLDER, _CUT_IMAGE_SIZE):
    from app.utils.cutting.cutting_svs import cutting
    from app.utils.create_zip.create_zip import create_zip

    path_cutting_img = cutting(path)

    os.remove(path)  # Delete download svs

    result = create_zip(path_cutting_img)  # Create zip file

    print(result)

    shutil.rmtree(path_cutting_img)  # Delete cutting folder


