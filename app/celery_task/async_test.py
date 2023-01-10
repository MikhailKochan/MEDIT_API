import asyncio
import os
import glob

import cv2
import numpy as np
from sys import platform

if platform == 'win32':
    os.add_dll_directory(os.getcwd() + '/app/static/dll/openslide-win64-20171122/bin')

import openslide
import time
from config import Config

from PIL import Image
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from aiohttp import ClientSession, TCPConnector, FormData

from io import BytesIO
from app.models import Settings

CUT_IMAGE_SIZE = Config.__dict__['_CUT_IMAGE_SIZE']
sem = asyncio.Semaphore(10)


def space_selector(height: int, width: int):
    # start = time.time()
    h_sum = int(height / CUT_IMAGE_SIZE[1])
    w_sum = int(width / CUT_IMAGE_SIZE[0])

    h_rest = height % CUT_IMAGE_SIZE[1]
    w_rest = width % CUT_IMAGE_SIZE[0]

    s_col = int(h_rest / 2)
    s_row = int(w_rest / 2)

    for i in range(0, h_sum):
        for j in range(0, w_sum):
            start_row = j * CUT_IMAGE_SIZE[0] + s_row
            start_col = i * CUT_IMAGE_SIZE[1] + s_col

            filename = f"im_.{str(i)}.{str(j)}"
            # print(f'generator time: {time.time() - start} s')
            yield start_row, start_col, filename


def list_maker(gen):
    lst = [i for i in gen]
    return lst


def list_spliter(lst):
    n = np.array_split(lst, len(lst) // 20)
    return n


def task_maker(height, width):
    gen = space_selector(height, width)
    n = list_spliter(list_maker(gen))
    for i in n:
        yield i


def read_region(file: Image, start_row: int, start_col: int):
    start = time.time()
    img = file.read_region((start_row, start_col), 0, CUT_IMAGE_SIZE)
    img = img.convert('RGB')
    # print(f'read region time: {time.time() - start} s')
    return img


def quality_checking_image(img: np.asarray,
                           quality_black=False,
                           lower=None,
                           upper=None,
                           settings=None):
    """

    Args:
        settings: user settings class Settings in models
        upper: upper range for HSV color
        lower: lower range for HSV color
        img: MUST be BGR
        quality_black: Black mode for images

    Returns:
        True of False
    """
    # print('START QUALITY')
    # start = time.time()
    if settings is None:
        percentage = 30
    else:
        percentage = int(settings.percentage_white)

    if lower is None and upper is None:
        lower = np.array([0, 0, 168], dtype=np.uint8)
        upper = np.array([180, 30, 255], dtype=np.uint8)

    if quality_black:
        if settings is None:
            percentage = 10
        else:
            percentage = int(settings.percentage_black)

        if lower is None and upper is None:
            lower = np.array([0, 0, 0], dtype=np.uint8)
            upper = np.array([180, 255, 68], dtype=np.uint8)

    print('quality black', quality_black)
    print('percentage', percentage)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)

    imgh, imgw = img.shape[:2]

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    summa_S = 0.0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        summa_S += w * h

    if summa_S > imgh * imgw / 100 * percentage:
        quality = False
    else:
        quality = True

    return quality


def resize_image():
    path = glob.glob('./PUT_YOUR_DATASET_HERE/telephon/*.jp*g')
    path_save = './PUT_YOUR_DATASET_HERE/telephon'
    for f in path:
        print(f)
        # f = f.replace("\\", "/")
        # print(f)
        scale_percent = 20  # percent of original size
        img = cv2.imread(f, 1)
        # print(img)

        width = int(img.shape[1] * scale_percent / 100)
        height = int(img.shape[0] * scale_percent / 100)
        dim = (width, height)
        resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        name = os.path.basename(f).split('.')[0]
        cv2.imwrite(f'{path_save}/{name}_resize.jpg', resized)


def save_image(image: Image, filename, f_path, quality=True):
    img_filename = os.path.basename(f_path)
    save_folder = os.path.join(Config.CUTTING_FOLDER, img_filename)

    if not quality:
        save_folder = os.path.join(save_folder, f"not_quality")

    path_to_save = os.path.join(save_folder, f"{filename}.jpg")

    os.makedirs(save_folder, exist_ok=True)

    image.save(path_to_save)
    return path_to_save


def convert_to_np(image: Image) -> np:
    # start = time.time()
    arr = np.asarray(image)
    # print(f'arr time: {time.time() - start} s')
    return arr


def convert_to_bytes(image: Image) -> np:
    image_content = BytesIO()
    image.seek(0)
    image.save(image_content, format='JPEG')
    image_content.seek(0)
    return image_content


async def async_image_process(img: Image, start_row: int, start_col: int, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(read_region, img, start_row, start_col))


async def async_image_save_process(img: Image, loop, filename, f_path, quality):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(save_image, img, filename, f_path, quality))


async def async_convert_process(img: Image, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(convert_to_bytes, img))


async def async_quality_process(img: Image, loop, image_name):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(quality_checking_image, img, image_name))


async def async_open_image(f_path, loop):
    with ThreadPoolExecutor() as thread_pool:
        return await loop.run_in_executor(thread_pool, partial(openslide.OpenSlide, f_path))


async def async_main(session, start_row, start_col, image, loop, filename, f_path, number):
    url = 'http://localhost:8001/uploadfile/'
    try:
        image = await async_image_process(image, start_row, start_col, loop)
        start = time.time()
        data = FormData()
        """bytes block"""
        # data.add_field('file',
        #                await async_convert_process(image, loop),
        #                filename=filename,
        #                content_type='application/image')
        # print(f'convert time: {time.time() - start} s')
        """write read block"""
        start = time.time()
        np_image = np.asarray(image)
        print(f"np.asarray(image) time: {time.time() - start}")
        quality = await async_quality_process(np_image, loop, filename)
        path_save = await async_image_save_process(image, loop, filename, f_path, quality)

        # print(f"Image number: {number} - quality: {quality}")

        """ if quality:
        async with aiofiles.open(path_save, 'rb') as f:
            data.add_field('file',
                           await f.read(),
                           filename=filename,
                           content_type='application/image')
        # print(f'write and read file time: {time.time() - start} s')

        params = {"uploadType": "multipart/form-data"}

        async with session.post(url, data=data, params=params) as resp:
            if resp.status != 200:
                pass
                # print(number, "--ERROR--")
                # print(await resp.text())
            else:
                pass
                # print("RESPONSE:")
                # print(await resp.text())"""

    except Exception as ex:
        print("EXCEPTOIN IN async_main: ", ex)
        return
    else:
        pass
        # os.remove(path_save)
    # finally:
    #     sem.release()


async def bulk_request():
    """Make requests concurrently"""
    loop = asyncio.get_running_loop()

    f_path = glob.glob(f'{Config.UPLOAD_FOLDER}/*.svs')
    if f_path:
        f_path = f_path[0]
        start = time.time()
        image = await async_open_image(f_path, loop)
        width, height = image.level_dimensions[0]
        print(f"height: {height} | width: {width}")
        # print(f'openslide image open time: {time.time() - start} s')
        tasks = []
        number = 0
        connector = TCPConnector(force_close=True)
        # async with ClientSession(connector=connector) as session:
        #     for start_row, start_col, file_name in space_selector(height, width):
        #         await sem.acquire()
        #         tasks.append(async_main(session, start_row, start_col, image, loop, file_name, f_path, number))
        #         if sem.locked():
        #             await asyncio.gather(*tasks)
        #             tasks = []
        #     if len(tasks) > 0:
        #         await asyncio.gather(*tasks)

        async with ClientSession(connector=connector) as session:
            for start_row, start_col, file_name in space_selector(height, width):
                tasks.append(async_main(session, start_row, start_col, image, loop, file_name, f_path, number))
                number += 1
                if number % 20 == 0:
                    await asyncio.gather(*tasks)
                    tasks = []
                    # break
            if tasks:
                await asyncio.gather(*tasks)
    else:
        print("NOT FILE IN DIRECTORY")


class Rec_box:
    """
        Класс прямоугольников
    """

    def __init__(self, x, y, h, w):
        self.x = x
        self.y = y
        self.x1 = x + h
        self.y1 = y + w

    def compare_to_rec(self, B):
        """функция сравнения пересекаются ли прямоугольники"""
        if (self.x1 < B.x or B.x1 < self.x) or (self.y1 < B.y or B.y1 < self.y):
            return f"Прямоугольники не пересекаются"
        pass


def _convert_boxes(boxes):
    from detectron2.structures import Boxes, RotatedBoxes
    """
    Convert different format of boxes to an NxB array, where B = 4 or 5 is the box dimension.
    """
    if isinstance(boxes, Boxes) or isinstance(boxes, RotatedBoxes):
        print('isinstance(boxes, Boxes)')
        return boxes.tensor.detach().numpy()
    else:
        print('NOT isinstance(boxes, Boxes)')
        return np.asarray(boxes)


def _create_text_labels(classes, scores, class_names, is_crowd=None):
    """
    Args:
        classes (list[int] or None):
        scores (list[float] or None):
        class_names (list[str] or None):
        is_crowd (list[bool] or None):

    Returns:
        list[str] or None
    """
    labels = None
    if classes is not None:
        if class_names is not None and len(class_names) > 0:
            labels = [class_names[i] for i in classes]
        else:
            labels = [str(i) for i in classes]
    if scores is not None:
        if labels is None:
            labels = ["{:.0f}%".format(s * 100) for s in scores]
        else:
            labels = ["{} {:.0f}%".format(l, s * 100) for l, s in zip(labels, scores)]
    if labels is not None and is_crowd is not None:
        labels = [l + ("|crowd" if crowd else "") for l, crowd in zip(labels, is_crowd)]
    return labels


def quality_predict_area(image: np.asarray, predictions, metadata, mitoses: int = 0, settings: Settings = None):
    """

    Args:
        settings: user settings
        image: MUST BE IN BGR
        predictions: outputs after predict
        metadata:
        mitoses: index

    Returns:

    """
    request_coord = []
    request_label = []

    classes = predictions.pred_classes.tolist() if predictions.has("pred_classes") else None
    boxes = predictions.pred_boxes if predictions.has("pred_boxes") else None
    scores = predictions.scores if predictions.has("scores") else None
    labels = _create_text_labels(classes, scores, metadata.get("thing_classes", None))

    # print(f"BOXES: {boxes}")
    if mitoses in classes:
        if boxes is not None:
            boxes = _convert_boxes(boxes)
            # print(f"BOXES after convert: {boxes}")
            num_instances = len(boxes)
            if labels is not None:
                assert len(labels) == num_instances
            areas = None
            if boxes is not None:
                areas = np.prod(boxes[:, 2:] - boxes[:, :2], axis=1)
            if areas is not None:
                # print(f"areas: {areas}")
                sorted_idxs = np.argsort(-areas).tolist()
                # Re-order overlapped instances in descending order.
                boxes = boxes[sorted_idxs] if boxes is not None else None
                labels = [labels[k] for k in sorted_idxs] if labels is not None else None
                for i in range(num_instances):
                    if boxes is not None:
                        box_coord = boxes[i]
                        # print(f"BOX COORD: {box_coord}")
                        x, y, x1, y1 = box_coord
                        img = image[int(y): int(y1), int(x): int(x1)]
                        if classes[i] == mitoses:
                            if quality_checking_image(img, settings=settings) \
                                    and quality_checking_image(img, quality_black=True, settings=settings):
                                request_coord.append(box_coord)
                                request_label.append(labels[i])
    return request_coord, request_label


def draw_predict(image: np.asarray, coord: list, labels: list, settings: Settings = None):
    """
    draw Image
    Args:
        settings: user settings
        image: MUST be BGR
        coord: [[x,y,x1,y1], n1, n2... nx]
        labels: lest names

    Returns:
        draw Image: np.assarray
    """
    if settings is not None:
        # users settings
        rectangle_color = settings.get_color_for_rectangle()
        text_color = settings.get_color_for_text()
    else:
        # default settings
        rectangle_color = (2, 202, 244)
        text_color = (0, 0, 0)
    for i in range(len(coord)):
        x, y, x1, y1 = coord[i]
        x, y, x1, y1 = int(x), int(y), int(x1), int(y1)
        cv2.rectangle(image, (x, y), (x1, y1), rectangle_color, 2)
        cv2.rectangle(image, (x - 1, y - 23), (x + 134, y + 1), rectangle_color, -1)
        image = cv2.putText(image, f"{labels[i]}", (x, y - 1), cv2.FONT_HERSHEY_SIMPLEX,
                            .8, text_color, 2, cv2.LINE_AA)
    return image


def alfa():
    x = 215 - 100
    y = 196 - 100
    width = 65
    height = 75
    # x = 198
    # y = 240
    # width = 55
    # height = 75
    photo = 'photo_2022-12-19_22-35-59.jpg'
    photo1 = 'photo_2022-12-19_21-56-12.jpg'

    # image = cv2.imread(f"./PUT_YOUR_DATASET_HERE/{photo}")
    # imgh, imgw = img.shape[:2]
    photo2 = 'photo_2022-12-23_15-14-54.jpg'
    image = cv2.imread(f"C:\\Users\\user\\Downloads\\{photo2}")
    # x = (imgh / 2 - height) / 2
    # y = (imgh / 2 - height) / 2 + height
    cv2.rectangle(image, (x, y), (x + width, y + height), [2, 202, 244], 2)
    cv2.rectangle(image, (x - 1, y - 23), (x + 134, y + 1), [2, 202, 244], -1)
    img = cv2.putText(image, f"mitoz 97%", (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX,
                      .8, (0, 0, 0), 2, cv2.LINE_AA)
    # img = img[y: y + height, x: x + width]
    # print(quality_checking_image(img))
    # lower_white = np.array([0, 0, 168], dtype=np.uint8)
    # upper_white = np.array([180, 30, 255], dtype=np.uint8)
    #
    # # img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    # hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # mask = cv2.inRange(hsv, lower_white, upper_white)
    #
    # # print("filter time:", time.time() - start)
    # contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # summa_S = 0.0
    # for cnt in contours:
    #     x, y, w, h = cv2.boundingRect(cnt)
    #     summa_S += w * h
    #
    # if summa_S > CUT_IMAGE_SIZE[0] * CUT_IMAGE_SIZE[1] / 100 * 30:

    cv2.imshow("result", img)
    cv2.waitKey(0)


if __name__ == "__main__":
    alfa()
    # resize_image()
    # start_t = time.time()
    # asyncio.run(bulk_request())
    # print(f'Finish time: {time.time() - start_t} s')
